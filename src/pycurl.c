/* PycURL -- cURL Python module
 *
 * Authors:
 *  Copyright (C) 2001-2008 by Kjetil Jacobsen <kjetilja at gmail.com>
 *  Copyright (C) 2001-2008 by Markus F.X.J. Oberhumer <markus at oberhumer.com>
 *
 *  All rights reserved.
 *
 * Contributions:
 *  Tino Lange <Tino.Lange at gmx.de>
 *  Matt King <matt at gnik.com>
 *  Conrad Steenberg <conrad at hep.caltech.edu>
 *  Amit Mongia <amit_mongia at hotmail.com>
 *  Eric S. Raymond <esr at thyrsus.com>
 *  Martin Muenstermann <mamuema at sourceforge.net>
 *  Domenico Andreoli <cavok at libero.it>
 *  Dominique <curl-and-python at d242.net>
 *  Paul Pacheco
 *  Victor Lascurain <bittor at eleka.net>
 *  K.S.Sreeram <sreeram at tachyontech.net>
 *  Jayne <corvine at gmail.com>
 *  Bastian Kleineidam
 *  Mark Eichin
 *  Aaron Hill <visine19 at hotmail.com>
 *  Daniel Pena Arteaga <dpena at ph.tum.de>
 *  Jim Patterson
 *  Yuhui H <eyecat at gmail.com>
 *  Nick Pilon <npilon at oreilly.com>
 *  Thomas Hunger <teh at camvine.org>
 *  Wim Lewis
 *
 * See file README for license information.
 */

#if (defined(_WIN32) || defined(__WIN32__)) && !defined(WIN32)
#  define WIN32 1
#endif
#if defined(WIN32) && !defined(PYCURL_USE_LIBCURL_DLL)
#  define CURL_STATICLIB 1
#endif
#include <Python.h>
#include <pythread.h>
#include <stddef.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <limits.h>
#include <sys/types.h>

#if !defined(WIN32)
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#endif

#include <curl/curl.h>
#include <curl/easy.h>
#include <curl/multi.h>
#undef NDEBUG
#include <assert.h>

/* The inet_ntop() was added in ws2_32.dll on Windows Vista [1]. Hence the
 * Windows SDK targeting lesser OS'es doesn't provide that prototype.
 * Maybe we should use the local hidden inet_ntop() for all OS'es thus
 * making a pycurl.pyd work across OS'es w/o rebuilding?
 *
 * [1] http://msdn.microsoft.com/en-us/library/windows/desktop/cc805843(v=vs.85).aspx
 */
#if defined(WIN32) && ((_WIN32_WINNT <= 0x0600) || (NTDDI_VERSION < NTDDI_VISTA))
  static const char * pycurl_inet_ntop (int family, void *addr, char *string, size_t string_size);
  #define inet_ntop(fam,addr,string,size) pycurl_inet_ntop(fam,addr,string,size)
#endif

/* Ensure we have updated versions */
#if !defined(PY_VERSION_HEX) || (PY_VERSION_HEX < 0x02040000)
#  error "Need Python version 2.4 or greater to compile pycurl."
#endif
#if !defined(LIBCURL_VERSION_NUM) || (LIBCURL_VERSION_NUM < 0x071300)
#  error "Need libcurl version 7.19.0 or greater to compile pycurl."
#endif

#if LIBCURL_VERSION_MAJOR >= 8 || \
    LIBCURL_VERSION_MAJOR == 7 && LIBCURL_VERSION_MINOR >= 20 || \
    LIBCURL_VERSION_MAJOR == 7 && LIBCURL_VERSION_MINOR == 19 && LIBCURL_VERSION_PATCH >= 1
#define HAVE_CURLOPT_USERNAME
#define HAVE_CURLOPT_PROXYUSERNAME
#define HAVE_CURLOPT_CERTINFO
#endif

#if LIBCURL_VERSION_NUM >= 0x071503 /* check for 7.21.3 or greater */
#define HAVE_CURLOPT_RESOLVE
#endif

/* Python < 2.5 compat for Py_ssize_t */
#if PY_VERSION_HEX < 0x02050000 && !defined(PY_SSIZE_T_MIN)
typedef int Py_ssize_t;
#define PY_SSIZE_T_MAX INT_MAX
#define PY_SSIZE_T_MIN INT_MIN
#endif

/* Py_TYPE is defined by Python 2.6+ */
#if !defined(Py_TYPE)
#  define Py_TYPE(x) (x)->ob_type
#endif

#undef UNUSED
#define UNUSED(var)     ((void)&var)

/* Cruft for thread safe SSL crypto locks, snapped from the PHP curl extension */
#if defined(HAVE_CURL_SSL)
# if defined(HAVE_CURL_OPENSSL)
#   define PYCURL_NEED_SSL_TSL
#   define PYCURL_NEED_OPENSSL_TSL
#   include <openssl/crypto.h>
# elif defined(HAVE_CURL_GNUTLS)
#   include <gnutls/gnutls.h>
#   if GNUTLS_VERSION_NUMBER <= 0x020b00
#     define PYCURL_NEED_SSL_TSL
#     define PYCURL_NEED_GNUTLS_TSL
#     include <gcrypt.h>
#   endif
# elif !defined(HAVE_CURL_NSS)
#  warning \
   "libcurl was compiled with SSL support, but configure could not determine which " \
   "library was used; thus no SSL crypto locking callbacks will be set, which may " \
   "cause random crashes on SSL requests"
# endif /* HAVE_CURL_OPENSSL || HAVE_CURL_GNUTLS || HAVE_CURL_NSS */
#endif /* HAVE_CURL_SSL */

#if defined(PYCURL_NEED_SSL_TSL)
static void pycurl_ssl_init(void);
static void pycurl_ssl_cleanup(void);
#endif

#ifdef WITH_THREAD
#  define PYCURL_DECLARE_THREAD_STATE PyThreadState *tmp_state
#  define PYCURL_ACQUIRE_THREAD() acquire_thread(self, &tmp_state)
#  define PYCURL_ACQUIRE_THREAD_MULTI() acquire_thread_multi(self, &tmp_state)
#  define PYCURL_RELEASE_THREAD() release_thread(tmp_state)
/* Replacement for Py_BEGIN_ALLOW_THREADS/Py_END_ALLOW_THREADS when python
   callbacks are expected during blocking i/o operations: self->state will hold
   the handle to current thread to be used as context */
#  define PYCURL_BEGIN_ALLOW_THREADS \
       self->state = PyThreadState_Get(); \
       assert(self->state != NULL); \
       Py_BEGIN_ALLOW_THREADS
#  define PYCURL_END_ALLOW_THREADS \
       Py_END_ALLOW_THREADS \
       self->state = NULL;
#else
#  define PYCURL_DECLARE_THREAD_STATE
#  define PYCURL_ACQUIRE_THREAD() (1)
#  define PYCURL_ACQUIRE_THREAD_MULTI() (1)
#  define PYCURL_RELEASE_THREAD()
#  define PYCURL_BEGIN_ALLOW_THREADS
#  define PYCURL_END_ALLOW_THREADS
#endif

/* Calculate the number of OBJECTPOINT options we need to store */
#define OPTIONS_SIZE    ((int)CURLOPT_LASTENTRY % 10000)
#define MOPTIONS_SIZE   ((int)CURLMOPT_LASTENTRY % 10000)

/* Memory groups */
/* Attributes dictionary */
#define PYCURL_MEMGROUP_ATTRDICT        1
/* multi_stack */
#define PYCURL_MEMGROUP_MULTI           2
/* Python callbacks */
#define PYCURL_MEMGROUP_CALLBACK        4
/* Python file objects */
#define PYCURL_MEMGROUP_FILE            8
/* Share objects */
#define PYCURL_MEMGROUP_SHARE           16
/* httppost buffer references */
#define PYCURL_MEMGROUP_HTTPPOST        32
/* Postfields object */
#define PYCURL_MEMGROUP_POSTFIELDS      64

#define PYCURL_MEMGROUP_EASY \
    (PYCURL_MEMGROUP_CALLBACK | PYCURL_MEMGROUP_FILE | \
    PYCURL_MEMGROUP_HTTPPOST | PYCURL_MEMGROUP_POSTFIELDS)

#define PYCURL_MEMGROUP_ALL \
    (PYCURL_MEMGROUP_ATTRDICT | PYCURL_MEMGROUP_EASY | \
    PYCURL_MEMGROUP_MULTI | PYCURL_MEMGROUP_SHARE)

/* Keep some default variables around */
static const char g_pycurl_useragent [] =
    "PycURL/" PYCURL_VERSION " libcurl/" LIBCURL_VERSION;

/* Type objects */
static PyObject *ErrorObject = NULL;
static PyTypeObject *p_Curl_Type = NULL;
static PyTypeObject *p_CurlMulti_Type = NULL;
static PyTypeObject *p_CurlShare_Type = NULL;

typedef struct {
    PyThread_type_lock locks[CURL_LOCK_DATA_LAST];
} ShareLock;


typedef struct {
    PyObject_HEAD
    PyObject *dict;                 /* Python attributes dictionary */
    CURLSH *share_handle;
#ifdef WITH_THREAD
    ShareLock *lock;                /* lock object to implement CURLSHOPT_LOCKFUNC */
#endif
} CurlShareObject;

typedef struct {
    PyObject_HEAD
    PyObject *dict;                 /* Python attributes dictionary */
    CURLM *multi_handle;
#ifdef WITH_THREAD
    PyThreadState *state;
#endif
    fd_set read_fd_set;
    fd_set write_fd_set;
    fd_set exc_fd_set;
    /* callbacks */
    PyObject *t_cb;
    PyObject *s_cb;
} CurlMultiObject;

typedef struct {
    PyObject_HEAD
    PyObject *dict;                 /* Python attributes dictionary */
    CURL *handle;
#ifdef WITH_THREAD
    PyThreadState *state;
#endif
    CurlMultiObject *multi_stack;
    CurlShareObject *share;
    struct curl_httppost *httppost;
    /* List of INC'ed references associated with httppost. */
    PyObject *httppost_ref_list;
    struct curl_slist *httpheader;
    struct curl_slist *http200aliases;
    struct curl_slist *quote;
    struct curl_slist *postquote;
    struct curl_slist *prequote;
#ifdef HAVE_CURLOPT_RESOLVE
    struct curl_slist *resolve;
#endif
    /* callbacks */
    PyObject *w_cb;
    PyObject *h_cb;
    PyObject *r_cb;
    PyObject *pro_cb;
    PyObject *debug_cb;
    PyObject *ioctl_cb;
    PyObject *opensocket_cb;
    PyObject *seek_cb;
    /* file objects */
    PyObject *readdata_fp;
    PyObject *writedata_fp;
    PyObject *writeheader_fp;
    /* reference to the object used for CURLOPT_POSTFIELDS */
    PyObject *postfields_obj;
    /* misc */
    char error[CURL_ERROR_SIZE+1];
} CurlObject;

/* Raise exception based on return value `res' and `self->error' */
#define CURLERROR_RETVAL() do {\
    PyObject *v; \
    self->error[sizeof(self->error) - 1] = 0; \
    v = Py_BuildValue("(is)", (int) (res), self->error); \
    if (v != NULL) { PyErr_SetObject(ErrorObject, v); Py_DECREF(v); } \
    return NULL; \
} while (0)

/* Raise exception based on return value `res' and custom message */
#define CURLERROR_MSG(msg) do {\
    PyObject *v; const char *m = (msg); \
    v = Py_BuildValue("(is)", (int) (res), (m)); \
    if (v != NULL) { PyErr_SetObject(ErrorObject, v); Py_DECREF(v); } \
    return NULL; \
} while (0)


/* Safe XDECREF for object states that handles nested deallocations */
#define ZAP(v) do {\
    PyObject *tmp = (PyObject *)(v); \
    (v) = NULL; \
    Py_XDECREF(tmp); \
} while (0)


/*************************************************************************
// python utility functions
**************************************************************************/

#if (PY_VERSION_HEX < 0x02030000) && !defined(PY_LONG_LONG)
#  define PY_LONG_LONG LONG_LONG
#endif

/* Like PyString_AsString(), but set an exception if the string contains
 * embedded NULs. Actually PyString_AsStringAndSize() already does that for
 * us if the `len' parameter is NULL - see Objects/stringobject.c.
 */

static char *PyString_AsString_NoNUL(PyObject *obj)
{
    char *s = NULL;
    Py_ssize_t r;
    r = PyString_AsStringAndSize(obj, &s, NULL);
    if (r != 0)
        return NULL;    /* exception already set */
    assert(s != NULL);
    return s;
}


/* Convert a curl slist (a list of strings) to a Python list.
 * In case of error return NULL with an exception set.
 */
static PyObject *convert_slist(struct curl_slist *slist, int free_flags)
{
    PyObject *ret = NULL;
    struct curl_slist *slist_start = slist;

    ret = PyList_New((Py_ssize_t)0);
    if (ret == NULL) goto error;

    for ( ; slist != NULL; slist = slist->next) {
        PyObject *v = NULL;

        if (slist->data == NULL) {
            v = Py_None; Py_INCREF(v);
        } else {
            v = PyString_FromString(slist->data);
        }
        if (v == NULL || PyList_Append(ret, v) != 0) {
            Py_XDECREF(v);
            goto error;
        }
        Py_DECREF(v);
    }

    if ((free_flags & 1) && slist_start)
        curl_slist_free_all(slist_start);
    return ret;

error:
    Py_XDECREF(ret);
    if ((free_flags & 2) && slist_start)
        curl_slist_free_all(slist_start);
    return NULL;
}

#ifdef HAVE_CURLOPT_CERTINFO
/* Convert a struct curl_certinfo into a Python data structure.
 * In case of error return NULL with an exception set.
 */
static PyObject *convert_certinfo(struct curl_certinfo *cinfo)
{
    PyObject *certs;
    int cert_index;

    if (!cinfo)
        Py_RETURN_NONE;

    certs = PyList_New((Py_ssize_t)(cinfo->num_of_certs));
    if (!certs)
        return NULL;

    for (cert_index = 0; cert_index < cinfo->num_of_certs; cert_index ++) {
        struct curl_slist *fields = cinfo->certinfo[cert_index];
        struct curl_slist *field_cursor;
        int field_count, field_index;
        PyObject *cert;

        field_count = 0;
        field_cursor = fields;
        while (field_cursor != NULL) {
            field_cursor = field_cursor->next;
            field_count ++;
        }

        
        cert = PyTuple_New((Py_ssize_t)field_count);
        if (!cert)
            goto error;
        PyList_SetItem(certs, cert_index, cert); /* Eats the ref from New() */
        
        for(field_index = 0, field_cursor = fields;
            field_cursor != NULL;
            field_index ++, field_cursor = field_cursor->next) {
            const char *field = field_cursor->data;
            PyObject *field_tuple;

            if (!field) {
                field_tuple = Py_None; Py_INCREF(field_tuple);
            } else {
                const char *sep = strchr(field, ':');
                if (!sep) {
                    field_tuple = PyString_FromString(field);
                } else {
                    field_tuple = Py_BuildValue("s#s", field, (int)(sep - field), sep+1);
                }
                if (!field_tuple)
                    goto error;
            }
            PyTuple_SET_ITEM(cert, field_index, field_tuple); /* Eats the ref */
        }
    }

    return certs;
    
 error:
    Py_DECREF(certs);
    return NULL;
}
#endif

#ifdef WITH_THREAD
/*************************************************************************
// static utility functions
**************************************************************************/

static PyThreadState *
get_thread_state(const CurlObject *self)
{
    /* Get the thread state for callbacks to run in.
     * This is either `self->state' when running inside perform() or
     * `self->multi_stack->state' when running inside multi_perform().
     * When the result is != NULL we also implicitly assert
     * a valid `self->handle'.
     */
    if (self == NULL)
        return NULL;
    assert(Py_TYPE(self) == p_Curl_Type);
    if (self->state != NULL)
    {
        /* inside perform() */
        assert(self->handle != NULL);
        if (self->multi_stack != NULL) {
            assert(self->multi_stack->state == NULL);
        }
        return self->state;
    }
    if (self->multi_stack != NULL && self->multi_stack->state != NULL)
    {
        /* inside multi_perform() */
        assert(self->handle != NULL);
        assert(self->multi_stack->multi_handle != NULL);
        assert(self->state == NULL);
        return self->multi_stack->state;
    }
    return NULL;
}


static PyThreadState *
get_thread_state_multi(const CurlMultiObject *self)
{
    /* Get the thread state for callbacks to run in when given
     * multi handles instead of regular handles
     */
    if (self == NULL)
        return NULL;
    assert(Py_TYPE(self) == p_CurlMulti_Type);
    if (self->state != NULL)
    {
        /* inside multi_perform() */
        assert(self->multi_handle != NULL);
        return self->state;
    }
    return NULL;
}


static int acquire_thread(const CurlObject *self, PyThreadState **state)
{
    *state = get_thread_state(self);
    if (*state == NULL)
        return 0;
    PyEval_AcquireThread(*state);
    return 1;
}


static int acquire_thread_multi(const CurlMultiObject *self, PyThreadState **state)
{
    *state = get_thread_state_multi(self);
    if (*state == NULL)
        return 0;
    PyEval_AcquireThread(*state);
    return 1;
}


static void release_thread(PyThreadState *state)
{
    PyEval_ReleaseThread(state);
}
#endif


/* assert some CurlShareObject invariants */
static void
assert_share_state(const CurlShareObject *self)
{
    assert(self != NULL);
    assert(Py_TYPE(self) == p_CurlShare_Type);
#ifdef WITH_THREAD
    assert(self->lock != NULL);
#endif
}


/* assert some CurlObject invariants */
static void
assert_curl_state(const CurlObject *self)
{
    assert(self != NULL);
    assert(Py_TYPE(self) == p_Curl_Type);
#ifdef WITH_THREAD
    (void) get_thread_state(self);
#endif
}


/* assert some CurlMultiObject invariants */
static void
assert_multi_state(const CurlMultiObject *self)
{
    assert(self != NULL);
    assert(Py_TYPE(self) == p_CurlMulti_Type);
#ifdef WITH_THREAD
    if (self->state != NULL) {
        assert(self->multi_handle != NULL);
    }
#endif
}


/* check state for methods */
static int
check_curl_state(const CurlObject *self, int flags, const char *name)
{
    assert_curl_state(self);
    if ((flags & 1) && self->handle == NULL) {
        PyErr_Format(ErrorObject, "cannot invoke %s() - no curl handle", name);
        return -1;
    }
#ifdef WITH_THREAD
    if ((flags & 2) && get_thread_state(self) != NULL) {
        PyErr_Format(ErrorObject, "cannot invoke %s() - perform() is currently running", name);
        return -1;
    }
#endif
    return 0;
}

static int
check_multi_state(const CurlMultiObject *self, int flags, const char *name)
{
    assert_multi_state(self);
    if ((flags & 1) && self->multi_handle == NULL) {
        PyErr_Format(ErrorObject, "cannot invoke %s() - no multi handle", name);
        return -1;
    }
#ifdef WITH_THREAD
    if ((flags & 2) && self->state != NULL) {
        PyErr_Format(ErrorObject, "cannot invoke %s() - multi_perform() is currently running", name);
        return -1;
    }
#endif
    return 0;
}

static int
check_share_state(const CurlShareObject *self, int flags, const char *name)
{
    assert_share_state(self);
    return 0;
}

/*************************************************************************
// SSL TSL
**************************************************************************/

#ifdef WITH_THREAD
#ifdef PYCURL_NEED_OPENSSL_TSL

static PyThread_type_lock *pycurl_openssl_tsl = NULL;

static void pycurl_ssl_lock(int mode, int n, const char * file, int line)
{
    if (mode & CRYPTO_LOCK) {
        PyThread_acquire_lock(pycurl_openssl_tsl[n], 1);
    } else {
        PyThread_release_lock(pycurl_openssl_tsl[n]);
    }
}

static unsigned long pycurl_ssl_id(void)
{
    return (unsigned long) PyThread_get_thread_ident();
}

static void pycurl_ssl_init(void)
{
    int i, c = CRYPTO_num_locks();

    pycurl_openssl_tsl = PyMem_Malloc(c * sizeof(PyThread_type_lock));

    for (i = 0; i < c; ++i) {
        pycurl_openssl_tsl[i] = PyThread_allocate_lock();
    }

    CRYPTO_set_id_callback(pycurl_ssl_id);
    CRYPTO_set_locking_callback(pycurl_ssl_lock);
}

static void pycurl_ssl_cleanup(void)
{
    if (pycurl_openssl_tsl) {
        int i, c = CRYPTO_num_locks();

        CRYPTO_set_id_callback(NULL);
        CRYPTO_set_locking_callback(NULL);

        for (i = 0; i < c; ++i) {
            PyThread_free_lock(pycurl_openssl_tsl[i]);
        }

        PyMem_Free(pycurl_openssl_tsl);
        pycurl_openssl_tsl = NULL;
    }
}
#endif

#ifdef PYCURL_NEED_GNUTLS_TSL
static int pycurl_ssl_mutex_create(void **m)
{
    if ((*((PyThread_type_lock *) m) = PyThread_allocate_lock()) == NULL) {
        return -1;
    } else {
        return 0;
    }
}

static int pycurl_ssl_mutex_destroy(void **m)
{
    PyThread_free_lock(*((PyThread_type_lock *) m));
    return 0;
}

static int pycurl_ssl_mutex_lock(void **m)
{
    return !PyThread_acquire_lock(*((PyThread_type_lock *) m), 1);
}

static int pycurl_ssl_mutex_unlock(void **m)
{
    PyThread_release_lock(*((PyThread_type_lock *) m));
    return 0;
}

static struct gcry_thread_cbs pycurl_gnutls_tsl = {
    GCRY_THREAD_OPTION_USER,
    NULL,
    pycurl_ssl_mutex_create,
    pycurl_ssl_mutex_destroy,
    pycurl_ssl_mutex_lock,
    pycurl_ssl_mutex_unlock
};

static void pycurl_ssl_init(void)
{
    gcry_control(GCRYCTL_SET_THREAD_CBS, &pycurl_gnutls_tsl);
}

static void pycurl_ssl_cleanup(void)
{
    return;
}
#endif

/*************************************************************************
// CurlShareObject
**************************************************************************/

static void
share_lock_lock(ShareLock *lock, curl_lock_data data)
{
    PyThread_acquire_lock(lock->locks[data], 1);
}


static void
share_lock_unlock(ShareLock *lock, curl_lock_data data)
{
    PyThread_release_lock(lock->locks[data]);
}


static
ShareLock *share_lock_new(void)
{
    int i;
    ShareLock *lock = (ShareLock*)PyMem_Malloc(sizeof(ShareLock));

    assert(lock);
    for (i = 0; i < CURL_LOCK_DATA_LAST; ++i) {
        lock->locks[i] = PyThread_allocate_lock();
        if (lock->locks[i] == NULL) {
            goto error;
        }
    }
    return lock;
 error:
    for (--i; i >= 0; --i) {
        PyThread_free_lock(lock->locks[i]);
        lock->locks[i] = NULL;
    }
    PyMem_Free(lock);
    return NULL;
}


static void
share_lock_destroy(ShareLock *lock)
{
    int i;

    assert(lock);
    for (i = 0; i < CURL_LOCK_DATA_LAST; ++i){
        assert(lock->locks[i] != NULL);
        PyThread_free_lock(lock->locks[i]);
    }
    PyMem_Free(lock);
    lock = NULL;
}


static void
share_lock_callback(CURL *handle, curl_lock_data data, curl_lock_access locktype, void *userptr)
{
    CurlShareObject *share = (CurlShareObject*)userptr;
    share_lock_lock(share->lock, data);
}


static void
share_unlock_callback(CURL *handle, curl_lock_data data, void *userptr)
{
    CurlShareObject *share = (CurlShareObject*)userptr;
    share_lock_unlock(share->lock, data);
}

#else /* WITH_THREAD */

static void pycurl_ssl_init(void)
{
    return;
}

static void pycurl_ssl_cleanup(void)
{
    return;
}

#endif /* WITH_THREAD */

/* constructor - this is a module-level function returning a new instance */
static CurlShareObject *
do_share_new(PyObject *dummy)
{
    int res;
    CurlShareObject *self;
#ifdef WITH_THREAD
    const curl_lock_function lock_cb = share_lock_callback;
    const curl_unlock_function unlock_cb = share_unlock_callback;
#endif

    UNUSED(dummy);

    /* Allocate python curl-share object */
    self = (CurlShareObject *) PyObject_GC_New(CurlShareObject, p_CurlShare_Type);
    if (self) {
        PyObject_GC_Track(self);
    }
    else {
        return NULL;
    }

    /* Initialize object attributes */
    self->dict = NULL;
#ifdef WITH_THREAD
    self->lock = share_lock_new();
    assert(self->lock != NULL);
#endif

    /* Allocate libcurl share handle */
    self->share_handle = curl_share_init();
    if (self->share_handle == NULL) {
        Py_DECREF(self);
        PyErr_SetString(ErrorObject, "initializing curl-share failed");
        return NULL;
    }

#ifdef WITH_THREAD
    /* Set locking functions and data  */
    res = curl_share_setopt(self->share_handle, CURLSHOPT_LOCKFUNC, lock_cb);
    assert(res == CURLE_OK);
    res = curl_share_setopt(self->share_handle, CURLSHOPT_USERDATA, self);
    assert(res == CURLE_OK);
    res = curl_share_setopt(self->share_handle, CURLSHOPT_UNLOCKFUNC, unlock_cb);
    assert(res == CURLE_OK);
#endif

    return self;
}


static int
do_share_traverse(CurlShareObject *self, visitproc visit, void *arg)
{
    int err;
#undef VISIT
#define VISIT(v)    if ((v) != NULL && ((err = visit(v, arg)) != 0)) return err

    VISIT(self->dict);

    return 0;
#undef VISIT
}


/* Drop references that may have created reference cycles. */
static int
do_share_clear(CurlShareObject *self)
{
    ZAP(self->dict);
    return 0;
}


static void
util_share_close(CurlShareObject *self){
    curl_share_cleanup(self->share_handle);
#ifdef WITH_THREAD
    share_lock_destroy(self->lock);
#endif
}


static void
do_share_dealloc(CurlShareObject *self){
    PyObject_GC_UnTrack(self);
    Py_TRASHCAN_SAFE_BEGIN(self);

    ZAP(self->dict);
    util_share_close(self);

    PyObject_GC_Del(self);
    Py_TRASHCAN_SAFE_END(self)
}


/* setopt, unsetopt*/
/* --------------- unsetopt/setopt/getinfo --------------- */

static PyObject *
do_curlshare_setopt(CurlShareObject *self, PyObject *args)
{
    int option;
    PyObject *obj;

    if (!PyArg_ParseTuple(args, "iO:setopt", &option, &obj))
        return NULL;
    if (check_share_state(self, 1 | 2, "sharesetopt") != 0)
        return NULL;

    /* early checks of option value */
    if (option <= 0)
        goto error;
    if (option >= (int)CURLOPTTYPE_OFF_T + OPTIONS_SIZE)
        goto error;
    if (option % 10000 >= OPTIONS_SIZE)
        goto error;

#if 0 /* XXX - should we ??? */
    /* Handle the case of None */
    if (obj == Py_None) {
        return util_curl_unsetopt(self, option);
    }
#endif

    /* Handle the case of integer arguments */
    if (PyInt_Check(obj)) {
        long d = PyInt_AsLong(obj);
        if (d != CURL_LOCK_DATA_COOKIE && d != CURL_LOCK_DATA_DNS) {
            goto error;
        }
        switch(option) {
        case CURLSHOPT_SHARE:
        case CURLSHOPT_UNSHARE:
            curl_share_setopt(self->share_handle, option, d);
            break;
        default:
            PyErr_SetString(PyExc_TypeError, "integers are not supported for this option");
            return NULL;
        }
        Py_RETURN_NONE;
    }
    /* Failed to match any of the function signatures -- return error */
error:
    PyErr_SetString(PyExc_TypeError, "invalid arguments to setopt");
    return NULL;
}


/*************************************************************************
// CurlObject
**************************************************************************/

/* --------------- construct/destruct (i.e. open/close) --------------- */

/* Allocate a new python curl object */
static CurlObject *
util_curl_new(void)
{
    CurlObject *self;

    self = (CurlObject *) PyObject_GC_New(CurlObject, p_Curl_Type);
    if (self == NULL)
        return NULL;
    PyObject_GC_Track(self);

    /* Set python curl object initial values */
    self->dict = NULL;
    self->handle = NULL;
#ifdef WITH_THREAD
    self->state = NULL;
#endif
    self->share = NULL;
    self->multi_stack = NULL;
    self->httppost = NULL;
    self->httppost_ref_list = NULL;
    self->httpheader = NULL;
    self->http200aliases = NULL;
    self->quote = NULL;
    self->postquote = NULL;
    self->prequote = NULL;
#ifdef HAVE_CURLOPT_RESOLVE
    self->resolve = NULL;
#endif

    /* Set callback pointers to NULL by default */
    self->w_cb = NULL;
    self->h_cb = NULL;
    self->r_cb = NULL;
    self->pro_cb = NULL;
    self->debug_cb = NULL;
    self->ioctl_cb = NULL;
    self->opensocket_cb = NULL;
    self->seek_cb = NULL;

    /* Set file object pointers to NULL by default */
    self->readdata_fp = NULL;
    self->writedata_fp = NULL;
    self->writeheader_fp = NULL;
    
    /* Set postfields object pointer to NULL by default */
    self->postfields_obj = NULL;

    /* Zero string pointer memory buffer used by setopt */
    memset(self->error, 0, sizeof(self->error));

    return self;
}

/* initializer - used to intialize curl easy handles for use with pycurl */
static int
util_curl_init(CurlObject *self)
{
    int res;

    /* Set curl error buffer and zero it */
    res = curl_easy_setopt(self->handle, CURLOPT_ERRORBUFFER, self->error);
    if (res != CURLE_OK) {
        return (-1);
    }
    memset(self->error, 0, sizeof(self->error));

    /* Set backreference */
    res = curl_easy_setopt(self->handle, CURLOPT_PRIVATE, (char *) self);
    if (res != CURLE_OK) {
        return (-1);
    }

    /* Enable NOPROGRESS by default, i.e. no progress output */
    res = curl_easy_setopt(self->handle, CURLOPT_NOPROGRESS, (long)1);
    if (res != CURLE_OK) {
        return (-1);
    }

    /* Disable VERBOSE by default, i.e. no verbose output */
    res = curl_easy_setopt(self->handle, CURLOPT_VERBOSE, (long)0);
    if (res != CURLE_OK) {
        return (-1);
    }

    /* Set FTP_ACCOUNT to NULL by default */
    res = curl_easy_setopt(self->handle, CURLOPT_FTP_ACCOUNT, NULL);
    if (res != CURLE_OK) {
        return (-1);
    }

    /* Set default USERAGENT */
    res = curl_easy_setopt(self->handle, CURLOPT_USERAGENT, g_pycurl_useragent);
    if (res != CURLE_OK) {
        return (-1);
    }
    return (0);
}

/* constructor - this is a module-level function returning a new instance */
static CurlObject *
do_curl_new(PyObject *dummy)
{
    CurlObject *self = NULL;
    int res;

    UNUSED(dummy);

    /* Allocate python curl object */
    self = util_curl_new();
    if (self == NULL)
        return NULL;

    /* Initialize curl handle */
    self->handle = curl_easy_init();
    if (self->handle == NULL)
        goto error;

    res = util_curl_init(self);
    if (res < 0)
            goto error;
    /* Success - return new object */
    return self;

error:
    Py_DECREF(self);    /* this also closes self->handle */
    PyErr_SetString(ErrorObject, "initializing curl failed");
    return NULL;
}


/* util function shared by close() and clear() */
static void
util_curl_xdecref(CurlObject *self, int flags, CURL *handle)
{
    if (flags & PYCURL_MEMGROUP_ATTRDICT) {
        /* Decrement refcount for attributes dictionary. */
        ZAP(self->dict);
    }

    if (flags & PYCURL_MEMGROUP_MULTI) {
        /* Decrement refcount for multi_stack. */
        if (self->multi_stack != NULL) {
            CurlMultiObject *multi_stack = self->multi_stack;
            self->multi_stack = NULL;
            if (multi_stack->multi_handle != NULL && handle != NULL) {
                (void) curl_multi_remove_handle(multi_stack->multi_handle, handle);
            }
            Py_DECREF(multi_stack);
        }
    }

    if (flags & PYCURL_MEMGROUP_CALLBACK) {
        /* Decrement refcount for python callbacks. */
        ZAP(self->w_cb);
        ZAP(self->h_cb);
        ZAP(self->r_cb);
        ZAP(self->pro_cb);
        ZAP(self->debug_cb);
        ZAP(self->ioctl_cb);
    }

    if (flags & PYCURL_MEMGROUP_FILE) {
        /* Decrement refcount for python file objects. */
        ZAP(self->readdata_fp);
        ZAP(self->writedata_fp);
        ZAP(self->writeheader_fp);
    }

    if (flags & PYCURL_MEMGROUP_POSTFIELDS) {
        /* Decrement refcount for postfields object */
        ZAP(self->postfields_obj);
    }
    
    if (flags & PYCURL_MEMGROUP_SHARE) {
        /* Decrement refcount for share objects. */
        if (self->share != NULL) {
            CurlShareObject *share = self->share;
            self->share = NULL;
            if (share->share_handle != NULL && handle != NULL) {
                curl_easy_setopt(handle, CURLOPT_SHARE, NULL);
            }
            Py_DECREF(share);
        }
    }

    if (flags & PYCURL_MEMGROUP_HTTPPOST) {
        /* Decrement refcounts for httppost related references. */
        ZAP(self->httppost_ref_list);
    }
}


static void
util_curl_close(CurlObject *self)
{
    CURL *handle;

    /* Zero handle and thread-state to disallow any operations to be run
     * from now on */
    assert(self != NULL);
    assert(Py_TYPE(self) == p_Curl_Type);
    handle = self->handle;
    self->handle = NULL;
    if (handle == NULL) {
        /* Some paranoia assertions just to make sure the object
         * deallocation problem is finally really fixed... */
#ifdef WITH_THREAD
        assert(self->state == NULL);
#endif
        assert(self->multi_stack == NULL);
        assert(self->share == NULL);
        return;             /* already closed */
    }
#ifdef WITH_THREAD
    self->state = NULL;
#endif

    /* Decref multi stuff which uses this handle */
    util_curl_xdecref(self, PYCURL_MEMGROUP_MULTI, handle);
    /* Decref share which uses this handle */
    util_curl_xdecref(self, PYCURL_MEMGROUP_SHARE, handle);

    /* Cleanup curl handle - must be done without the gil */
    Py_BEGIN_ALLOW_THREADS
    curl_easy_cleanup(handle);
    Py_END_ALLOW_THREADS
    handle = NULL;

    /* Decref easy related objects */
    util_curl_xdecref(self, PYCURL_MEMGROUP_EASY, handle);

    /* Free all variables allocated by setopt */
#undef SFREE
#define SFREE(v)   if ((v) != NULL) (curl_formfree(v), (v) = NULL)
    SFREE(self->httppost);
#undef SFREE
#define SFREE(v)   if ((v) != NULL) (curl_slist_free_all(v), (v) = NULL)
    SFREE(self->httpheader);
    SFREE(self->http200aliases);
    SFREE(self->quote);
    SFREE(self->postquote);
    SFREE(self->prequote);
#ifdef HAVE_CURLOPT_RESOLVE
    SFREE(self->resolve);
#endif
#undef SFREE
}


static void
do_curl_dealloc(CurlObject *self)
{
    PyObject_GC_UnTrack(self);
    Py_TRASHCAN_SAFE_BEGIN(self)

    ZAP(self->dict);
    util_curl_close(self);

    PyObject_GC_Del(self);
    Py_TRASHCAN_SAFE_END(self)
}


static PyObject *
do_curl_close(CurlObject *self)
{
    if (check_curl_state(self, 2, "close") != 0) {
        return NULL;
    }
    util_curl_close(self);
    Py_RETURN_NONE;
}


static PyObject *
do_curl_errstr(CurlObject *self)
{
    if (check_curl_state(self, 1 | 2, "errstr") != 0) {
        return NULL;
    }
    self->error[sizeof(self->error) - 1] = 0;
    return PyString_FromString(self->error);
}


/* --------------- GC support --------------- */

/* Drop references that may have created reference cycles. */
static int
do_curl_clear(CurlObject *self)
{
#ifdef WITH_THREAD
    assert(get_thread_state(self) == NULL);
#endif
    util_curl_xdecref(self, PYCURL_MEMGROUP_ALL, self->handle);
    return 0;
}

/* Traverse all refcounted objects. */
static int
do_curl_traverse(CurlObject *self, visitproc visit, void *arg)
{
    int err;
#undef VISIT
#define VISIT(v)    if ((v) != NULL && ((err = visit(v, arg)) != 0)) return err

    VISIT(self->dict);
    VISIT((PyObject *) self->multi_stack);

    VISIT(self->w_cb);
    VISIT(self->h_cb);
    VISIT(self->r_cb);
    VISIT(self->pro_cb);
    VISIT(self->debug_cb);
    VISIT(self->ioctl_cb);

    VISIT(self->readdata_fp);
    VISIT(self->writedata_fp);
    VISIT(self->writeheader_fp);

    return 0;
#undef VISIT
}


/* --------------- perform --------------- */

static PyObject *
do_curl_perform(CurlObject *self)
{
    int res;

    if (check_curl_state(self, 1 | 2, "perform") != 0) {
        return NULL;
    }

    PYCURL_BEGIN_ALLOW_THREADS
    res = curl_easy_perform(self->handle);
    PYCURL_END_ALLOW_THREADS

    if (res != CURLE_OK) {
        CURLERROR_RETVAL();
    }
    Py_RETURN_NONE;
}


/* --------------- callback handlers --------------- */

/* IMPORTANT NOTE: due to threading issues, we cannot call _any_ Python
 * function without acquiring the thread state in the callback handlers.
 */

static size_t
util_write_callback(int flags, char *ptr, size_t size, size_t nmemb, void *stream)
{
    CurlObject *self;
    PyObject *arglist;
    PyObject *result = NULL;
    size_t ret = 0;     /* assume error */
    PyObject *cb;
    int total_size;
    PYCURL_DECLARE_THREAD_STATE;

    /* acquire thread */
    self = (CurlObject *)stream;
    if (!PYCURL_ACQUIRE_THREAD())
        return ret;

    /* check args */
    cb = flags ? self->h_cb : self->w_cb;
    if (cb == NULL)
        goto silent_error;
    if (size <= 0 || nmemb <= 0)
        goto done;
    total_size = (int)(size * nmemb);
    if (total_size < 0 || (size_t)total_size / size != nmemb) {
        PyErr_SetString(ErrorObject, "integer overflow in write callback");
        goto verbose_error;
    }

    /* run callback */
    arglist = Py_BuildValue("(s#)", ptr, total_size);
    if (arglist == NULL)
        goto verbose_error;
    result = PyEval_CallObject(cb, arglist);
    Py_DECREF(arglist);
    if (result == NULL)
        goto verbose_error;

    /* handle result */
    if (result == Py_None) {
        ret = total_size;           /* None means success */
    }
    else if (PyInt_Check(result) || PyLong_Check(result)) {
        /* if the cast to long fails, PyLong_AsLong() returns -1L */
        ret = (size_t) PyLong_AsLong(result);
    }
    else {
        PyErr_SetString(ErrorObject, "write callback must return int or None");
        goto verbose_error;
    }

done:
silent_error:
    Py_XDECREF(result);
    PYCURL_RELEASE_THREAD();
    return ret;
verbose_error:
    PyErr_Print();
    goto silent_error;
}


static size_t
write_callback(char *ptr, size_t size, size_t nmemb, void *stream)
{
    return util_write_callback(0, ptr, size, nmemb, stream);
}

static size_t
header_callback(char *ptr, size_t size, size_t nmemb, void *stream)
{
    return util_write_callback(1, ptr, size, nmemb, stream);
}

/* convert protocol address from C to python, returns a tuple of protocol
   specific values */
static PyObject *
convert_protocol_address(struct sockaddr* saddr, unsigned int saddrlen)
{
    PyObject *res_obj = NULL;
    
    switch (saddr->sa_family)
    {
    case AF_INET:
        {
            struct sockaddr_in* sin = (struct sockaddr_in*)saddr;
            char *addr_str = (char *)PyMem_Malloc(INET_ADDRSTRLEN);
            
            if (addr_str == NULL) {
                PyErr_SetString(ErrorObject, "Out of memory");
                goto error;
            }
            
            if (inet_ntop(saddr->sa_family, &sin->sin_addr, addr_str, INET_ADDRSTRLEN) == NULL) {
                PyErr_SetFromErrno(ErrorObject);
                PyMem_Free(addr_str);
                goto error;
            }
            res_obj = Py_BuildValue("(si)", addr_str, ntohs(sin->sin_port));
            PyMem_Free(addr_str);
       }
        break;
    case AF_INET6:
        {
            struct sockaddr_in6* sin6 = (struct sockaddr_in6*)saddr;
            char *addr_str = (char *)PyMem_Malloc(INET6_ADDRSTRLEN);
            
            if (addr_str == NULL) {
                PyErr_SetString(ErrorObject, "Out of memory");
                goto error;
            }
            
            if (inet_ntop(saddr->sa_family, &sin6->sin6_addr, addr_str, INET6_ADDRSTRLEN) == NULL) {
                PyErr_SetFromErrno(ErrorObject);
                PyMem_Free(addr_str);
                goto error;
            }
            res_obj = Py_BuildValue("(si)", addr_str, ntohs(sin6->sin6_port));
            PyMem_Free(addr_str);
        }
        break;
    default:
        /* We (currently) only support IPv4/6 addresses.  Can curl even be used
           with anything else? */
	PyErr_SetString(ErrorObject, "Unsupported address family.");
    }
    
error:
    return res_obj;
}

/* curl_socket_t is just an int on unix/windows (with limitations that
 * are not important here) */
static curl_socket_t
opensocket_callback(void *clientp, curlsocktype purpose,
		    struct curl_sockaddr *address)
{
    PyObject *arglist;
    PyObject *result = NULL;
    PyObject *fileno_result = NULL;
    CurlObject *self;
    int ret = CURL_SOCKET_BAD;
    PYCURL_DECLARE_THREAD_STATE;

    self = (CurlObject *)clientp;
    PYCURL_ACQUIRE_THREAD();
    
    arglist = Py_BuildValue("(iiiN)", address->family, address->socktype, address->protocol, convert_protocol_address(&address->addr, address->addrlen));
    if (arglist == NULL)
        goto verbose_error;

    result = PyEval_CallObject(self->opensocket_cb, arglist);

    Py_DECREF(arglist);
    if (result == NULL) {
        goto verbose_error;
    }

    if (PyObject_HasAttrString(result, "fileno")) {
	fileno_result = PyObject_CallMethod(result, "fileno", NULL);

	if (fileno_result == NULL) {
	    ret = CURL_SOCKET_BAD;
	    goto verbose_error;
	}
	// normal operation:
	if (PyInt_Check(fileno_result)) {
	    ret = dup(PyInt_AsLong(fileno_result));
	    goto done;
	}
    } else {
	PyErr_SetString(ErrorObject, "Return value must be a socket.");
	ret = CURL_SOCKET_BAD;
	goto verbose_error;
    }

silent_error:
done:
    Py_XDECREF(result);
    Py_XDECREF(fileno_result);
    PYCURL_RELEASE_THREAD();
    return ret;
verbose_error:
    PyErr_Print();
    goto silent_error;
}

static int
seek_callback(void *stream, curl_off_t offset, int origin)
{
    CurlObject *self;
    PyObject *arglist;
    PyObject *result = NULL;
    int ret = 2;     /* assume error 2 (can't seek, libcurl free to work around). */
    PyObject *cb;
    int source = 0;     /* assume beginning */
    PYCURL_DECLARE_THREAD_STATE;

    /* acquire thread */
    self = (CurlObject *)stream;
    if (!PYCURL_ACQUIRE_THREAD())
        return ret;

    /* check arguments */
    switch (origin)
    {
      case SEEK_SET:
          source = 0;
          break;
      case SEEK_CUR:
          source = 1;
          break;
      case SEEK_END:
          source = 2;
          break;
      default:
          source = origin;
          break;
    }
    
    /* run callback */
    cb = self->seek_cb;
    if (cb == NULL)
        goto silent_error;
    arglist = Py_BuildValue("(i,i)", offset, source);
    if (arglist == NULL)
        goto verbose_error;
    result = PyEval_CallObject(cb, arglist);
    Py_DECREF(arglist);
    if (result == NULL)
        goto verbose_error;

    /* handle result */
    if (result == Py_None) {
        ret = 0;           /* None means success */
    }
    else if (PyInt_Check(result)) {
        int ret_code = PyInt_AsLong(result);
        if (ret_code < 0 || ret_code > 2) {
            PyErr_Format(ErrorObject, "invalid return value for seek callback %d not in (0, 1, 2)", ret_code);
            goto verbose_error;
        }
        ret = ret_code;    /* pass the return code from the callback */
    }
    else {
        PyErr_SetString(ErrorObject, "seek callback must return 0 (CURL_SEEKFUNC_OK), 1 (CURL_SEEKFUNC_FAIL), 2 (CURL_SEEKFUNC_CANTSEEK) or None");
        goto verbose_error;
    }

silent_error:
    Py_XDECREF(result);
    PYCURL_RELEASE_THREAD();
    return ret;
verbose_error:
    PyErr_Print();
    goto silent_error;
}




static size_t
read_callback(char *ptr, size_t size, size_t nmemb, void *stream)
{
    CurlObject *self;
    PyObject *arglist;
    PyObject *result = NULL;

    size_t ret = CURL_READFUNC_ABORT;     /* assume error, this actually works */
    int total_size;

    PYCURL_DECLARE_THREAD_STATE;
    
    /* acquire thread */
    self = (CurlObject *)stream;
    if (!PYCURL_ACQUIRE_THREAD())
        return ret;

    /* check args */
    if (self->r_cb == NULL)
        goto silent_error;
    if (size <= 0 || nmemb <= 0)
        goto done;
    total_size = (int)(size * nmemb);
    if (total_size < 0 || (size_t)total_size / size != nmemb) {
        PyErr_SetString(ErrorObject, "integer overflow in read callback");
        goto verbose_error;
    }

    /* run callback */
    arglist = Py_BuildValue("(i)", total_size);
    if (arglist == NULL)
        goto verbose_error;
    result = PyEval_CallObject(self->r_cb, arglist);
    Py_DECREF(arglist);
    if (result == NULL)
        goto verbose_error;

    /* handle result */
    if (PyString_Check(result)) {
        char *buf = NULL;
        Py_ssize_t obj_size = -1;
        Py_ssize_t r;
        r = PyString_AsStringAndSize(result, &buf, &obj_size);
        if (r != 0 || obj_size < 0 || obj_size > total_size) {
            PyErr_Format(ErrorObject, "invalid return value for read callback %ld %ld", (long)obj_size, (long)total_size);
            goto verbose_error;
        }
        memcpy(ptr, buf, obj_size);
        ret = obj_size;             /* success */
    }
    else if (PyInt_Check(result)) {
        long r = PyInt_AsLong(result);
        if (r != CURL_READFUNC_ABORT
#if LIBCURL_VERSION_NUM >= 0x071200  /* CURL_READFUNC_PAUSE appeared in libcurl 7.18.0 */
            && r != CURL_READFUNC_PAUSE
#endif
            ) {
            goto type_error;
        }
        ret = r; /* either CURL_READFUNC_ABORT or CURL_READFUNC_PAUSE */
    }
    else if (PyLong_Check(result)) {
        long r = PyLong_AsLong(result);
        if (r != CURL_READFUNC_ABORT
#if LIBCURL_VERSION_NUM >= 0x071200  /* CURL_READFUNC_PAUSE appeared in libcurl 7.18.0 */
            && r != CURL_READFUNC_PAUSE
#endif
            ) {
            goto type_error;
        }
        ret = r; /* either CURL_READFUNC_ABORT or CURL_READFUNC_PAUSE */
    }
    else {
    type_error:
        PyErr_SetString(ErrorObject, "read callback must return string");
        goto verbose_error;
    }
    
done:
silent_error:
    Py_XDECREF(result);
    PYCURL_RELEASE_THREAD();
    return ret;
verbose_error:
    PyErr_Print();
    goto silent_error;
}


static int
progress_callback(void *stream,
                  double dltotal, double dlnow, double ultotal, double ulnow)
{
    CurlObject *self;
    PyObject *arglist;
    PyObject *result = NULL;
    int ret = 1;       /* assume error */
    PYCURL_DECLARE_THREAD_STATE;

    /* acquire thread */
    self = (CurlObject *)stream;
    if (!PYCURL_ACQUIRE_THREAD())
        return ret;

    /* check args */
    if (self->pro_cb == NULL)
        goto silent_error;

    /* run callback */
    arglist = Py_BuildValue("(dddd)", dltotal, dlnow, ultotal, ulnow);
    if (arglist == NULL)
        goto verbose_error;
    result = PyEval_CallObject(self->pro_cb, arglist);
    Py_DECREF(arglist);
    if (result == NULL)
        goto verbose_error;

    /* handle result */
    if (result == Py_None) {
        ret = 0;        /* None means success */
    }
    else if (PyInt_Check(result)) {
        ret = (int) PyInt_AsLong(result);
    }
    else {
        ret = PyObject_IsTrue(result);  /* FIXME ??? */
    }

silent_error:
    Py_XDECREF(result);
    PYCURL_RELEASE_THREAD();
    return ret;
verbose_error:
    PyErr_Print();
    goto silent_error;
}


static int
debug_callback(CURL *curlobj, curl_infotype type,
               char *buffer, size_t total_size, void *stream)
{
    CurlObject *self;
    PyObject *arglist;
    PyObject *result = NULL;
    int ret = 0;       /* always success */
    PYCURL_DECLARE_THREAD_STATE;

    UNUSED(curlobj);

    /* acquire thread */
    self = (CurlObject *)stream;
    if (!PYCURL_ACQUIRE_THREAD())
        return ret;

    /* check args */
    if (self->debug_cb == NULL)
        goto silent_error;
    if ((int)total_size < 0 || (size_t)((int)total_size) != total_size) {
        PyErr_SetString(ErrorObject, "integer overflow in debug callback");
        goto verbose_error;
    }

    /* run callback */
    arglist = Py_BuildValue("(is#)", (int)type, buffer, (int)total_size);
    if (arglist == NULL)
        goto verbose_error;
    result = PyEval_CallObject(self->debug_cb, arglist);
    Py_DECREF(arglist);
    if (result == NULL)
        goto verbose_error;

    /* return values from debug callbacks should be ignored */

silent_error:
    Py_XDECREF(result);
    PYCURL_RELEASE_THREAD();
    return ret;
verbose_error:
    PyErr_Print();
    goto silent_error;
}


static curlioerr
ioctl_callback(CURL *curlobj, int cmd, void *stream)
{
    CurlObject *self;
    PyObject *arglist;
    PyObject *result = NULL;
    int ret = CURLIOE_FAILRESTART;       /* assume error */
    PYCURL_DECLARE_THREAD_STATE;

    UNUSED(curlobj);

    /* acquire thread */
    self = (CurlObject *)stream;
    if (!PYCURL_ACQUIRE_THREAD())
        return (curlioerr) ret;

    /* check args */
    if (self->ioctl_cb == NULL)
        goto silent_error;

    /* run callback */
    arglist = Py_BuildValue("(i)", cmd);
    if (arglist == NULL)
        goto verbose_error;
    result = PyEval_CallObject(self->ioctl_cb, arglist);
    Py_DECREF(arglist);
    if (result == NULL)
        goto verbose_error;

    /* handle result */
    if (result == Py_None) {
        ret = CURLIOE_OK;        /* None means success */
    }
    else if (PyInt_Check(result)) {
        ret = (int) PyInt_AsLong(result);
        if (ret >= CURLIOE_LAST || ret < 0) {
            PyErr_SetString(ErrorObject, "ioctl callback returned invalid value");
            goto verbose_error;
        }
    }

silent_error:
    Py_XDECREF(result);
    PYCURL_RELEASE_THREAD();
    return (curlioerr) ret;
verbose_error:
    PyErr_Print();
    goto silent_error;
}


/* ------------------------ reset ------------------------ */

static PyObject*
do_curl_reset(CurlObject *self)
{
    int res;

    curl_easy_reset(self->handle);

    /* Decref easy interface related objects */
    util_curl_xdecref(self, PYCURL_MEMGROUP_EASY, self->handle);

    /* Free all variables allocated by setopt */
#undef SFREE
#define SFREE(v)   if ((v) != NULL) (curl_formfree(v), (v) = NULL)
    SFREE(self->httppost);
#undef SFREE
#define SFREE(v)   if ((v) != NULL) (curl_slist_free_all(v), (v) = NULL)
    SFREE(self->httpheader);
    SFREE(self->http200aliases);
    SFREE(self->quote);
    SFREE(self->postquote);
    SFREE(self->prequote);
#ifdef HAVE_CURLOPT_RESOLVE
    SFREE(self->resolve);
#endif
#undef SFREE
    res = util_curl_init(self);
    if (res < 0) {
        Py_DECREF(self);    /* this also closes self->handle */
        PyErr_SetString(ErrorObject, "resetting curl failed");
        return NULL;
    }

    Py_RETURN_NONE;
}

/* --------------- unsetopt/setopt/getinfo --------------- */

static PyObject *
util_curl_unsetopt(CurlObject *self, int option)
{
    int res;

#define SETOPT2(o,x) \
    if ((res = curl_easy_setopt(self->handle, (o), (x))) != CURLE_OK) goto error
#define SETOPT(x)   SETOPT2((CURLoption)option, (x))

    /* FIXME: implement more options. Have to carefully check lib/url.c in the
     *   libcurl source code to see if it's actually safe to simply
     *   unset the option. */
    switch (option)
    {
    case CURLOPT_SHARE:
        SETOPT((CURLSH *) NULL);
        Py_XDECREF(self->share);
        self->share = NULL;
        break;
    case CURLOPT_HTTPPOST:
        SETOPT((void *) 0);
        curl_formfree(self->httppost);
        util_curl_xdecref(self, PYCURL_MEMGROUP_HTTPPOST, self->handle);
        self->httppost = NULL;
        /* FIXME: what about data->set.httpreq ?? */
        break;
    case CURLOPT_INFILESIZE:
        SETOPT((long) -1);
        break;
    case CURLOPT_WRITEHEADER:
        SETOPT((void *) 0);
        ZAP(self->writeheader_fp);
        break;
    case CURLOPT_CAINFO:
    case CURLOPT_CAPATH:
    case CURLOPT_COOKIE:
    case CURLOPT_COOKIEJAR:
    case CURLOPT_CUSTOMREQUEST:
    case CURLOPT_EGDSOCKET:
    case CURLOPT_FTPPORT:
    case CURLOPT_PROXYUSERPWD:
#ifdef HAVE_CURLOPT_PROXYUSERNAME
    case CURLOPT_PROXYUSERNAME:
    case CURLOPT_PROXYPASSWORD:
#endif
    case CURLOPT_RANDOM_FILE:
    case CURLOPT_SSL_CIPHER_LIST:
    case CURLOPT_USERPWD:
#ifdef HAVE_CURLOPT_USERNAME
    case CURLOPT_USERNAME:
    case CURLOPT_PASSWORD:
#endif
    case CURLOPT_RANGE:
        SETOPT((char *) 0);
        break;

#ifdef HAVE_CURLOPT_CERTINFO
    case CURLOPT_CERTINFO:
        SETOPT((long) 0);
        break;
#endif

    /* info: we explicitly list unsupported options here */
    case CURLOPT_COOKIEFILE:
    default:
        PyErr_SetString(PyExc_TypeError, "unsetopt() is not supported for this option");
        return NULL;
    }

    Py_RETURN_NONE;

error:
    CURLERROR_RETVAL();

#undef SETOPT
#undef SETOPT2
}


static PyObject *
do_curl_unsetopt(CurlObject *self, PyObject *args)
{
    int option;

    if (!PyArg_ParseTuple(args, "i:unsetopt", &option)) {
        return NULL;
    }
    if (check_curl_state(self, 1 | 2, "unsetopt") != 0) {
        return NULL;
    }

    /* early checks of option value */
    if (option <= 0)
        goto error;
    if (option >= (int)CURLOPTTYPE_OFF_T + OPTIONS_SIZE)
        goto error;
    if (option % 10000 >= OPTIONS_SIZE)
        goto error;

    return util_curl_unsetopt(self, option);

error:
    PyErr_SetString(PyExc_TypeError, "invalid arguments to unsetopt");
    return NULL;
}


static PyObject *
do_curl_setopt(CurlObject *self, PyObject *args)
{
    int option;
    PyObject *obj;
    int res;

    if (!PyArg_ParseTuple(args, "iO:setopt", &option, &obj))
        return NULL;
    if (check_curl_state(self, 1 | 2, "setopt") != 0)
        return NULL;

    /* early checks of option value */
    if (option <= 0)
        goto error;
    if (option >= (int)CURLOPTTYPE_OFF_T + OPTIONS_SIZE)
        goto error;
    if (option % 10000 >= OPTIONS_SIZE)
        goto error;

    /* Handle the case of None as the call of unsetopt() */
    if (obj == Py_None) {
        return util_curl_unsetopt(self, option);
    }

    /* Handle the case of string arguments */
    if (PyString_Check(obj)) {
        char *str = NULL;
        Py_ssize_t len = -1;

        /* Check that the option specified a string as well as the input */
        switch (option) {
        case CURLOPT_CAINFO:
        case CURLOPT_CAPATH:
        case CURLOPT_COOKIE:
        case CURLOPT_COOKIEFILE:
        case CURLOPT_COOKIELIST:
        case CURLOPT_COOKIEJAR:
        case CURLOPT_CUSTOMREQUEST:
        case CURLOPT_EGDSOCKET:
        case CURLOPT_ENCODING:
        case CURLOPT_FTPPORT:
        case CURLOPT_INTERFACE:
        case CURLOPT_KRB4LEVEL:
        case CURLOPT_NETRC_FILE:
        case CURLOPT_PROXY:
        case CURLOPT_PROXYUSERPWD:
#ifdef HAVE_CURLOPT_PROXYUSERNAME
        case CURLOPT_PROXYUSERNAME:
        case CURLOPT_PROXYPASSWORD:
#endif
        case CURLOPT_RANDOM_FILE:
        case CURLOPT_RANGE:
        case CURLOPT_REFERER:
        case CURLOPT_SSLCERT:
        case CURLOPT_SSLCERTTYPE:
        case CURLOPT_SSLENGINE:
        case CURLOPT_SSLKEY:
        case CURLOPT_SSLKEYPASSWD:
        case CURLOPT_SSLKEYTYPE:
        case CURLOPT_SSL_CIPHER_LIST:
        case CURLOPT_URL:
        case CURLOPT_USERAGENT:
        case CURLOPT_USERPWD:
#ifdef HAVE_CURLOPT_USERNAME
        case CURLOPT_USERNAME:
        case CURLOPT_PASSWORD:
#endif
        case CURLOPT_FTP_ALTERNATIVE_TO_USER:
        case CURLOPT_SSH_PUBLIC_KEYFILE:
        case CURLOPT_SSH_PRIVATE_KEYFILE:
        case CURLOPT_COPYPOSTFIELDS:
        case CURLOPT_SSH_HOST_PUBLIC_KEY_MD5:
        case CURLOPT_CRLFILE:
        case CURLOPT_ISSUERCERT:
#if LIBCURL_VERSION_NUM >= 0x071800
        case CURLOPT_DNS_SERVERS:
#endif
/* FIXME: check if more of these options allow binary data */
            str = PyString_AsString_NoNUL(obj);
            if (str == NULL)
                return NULL;
            break;
        case CURLOPT_POSTFIELDS:
            if (PyString_AsStringAndSize(obj, &str, &len) != 0)
                return NULL;
            /* automatically set POSTFIELDSIZE */
            if (len <= INT_MAX) {
                res = curl_easy_setopt(self->handle, CURLOPT_POSTFIELDSIZE, (long)len);
            } else {
                res = curl_easy_setopt(self->handle, CURLOPT_POSTFIELDSIZE_LARGE, (curl_off_t)len);
            }
            if (res != CURLE_OK) {
                CURLERROR_RETVAL();
            }
            break;
        default:
            PyErr_SetString(PyExc_TypeError, "strings are not supported for this option");
            return NULL;
        }
        assert(str != NULL);
        /* Call setopt */
        res = curl_easy_setopt(self->handle, (CURLoption)option, str);
        /* Check for errors */
        if (res != CURLE_OK) {
            CURLERROR_RETVAL();
        }
        /* libcurl does not copy the value of CURLOPT_POSTFIELDS */
        if (option == CURLOPT_POSTFIELDS) {
            Py_INCREF(obj);
            util_curl_xdecref(self, PYCURL_MEMGROUP_POSTFIELDS, self->handle);
            self->postfields_obj = obj;
        }
        Py_RETURN_NONE;
    }

#define IS_LONG_OPTION(o)   (o < CURLOPTTYPE_OBJECTPOINT)
#define IS_OFF_T_OPTION(o)  (o >= CURLOPTTYPE_OFF_T)

    /* Handle the case of integer arguments */
    if (PyInt_Check(obj)) {
        long d = PyInt_AsLong(obj);

        if (IS_LONG_OPTION(option))
            res = curl_easy_setopt(self->handle, (CURLoption)option, (long)d);
        else if (IS_OFF_T_OPTION(option))
            res = curl_easy_setopt(self->handle, (CURLoption)option, (curl_off_t)d);
        else {
            PyErr_SetString(PyExc_TypeError, "integers are not supported for this option");
            return NULL;
        }
        if (res != CURLE_OK) {
            CURLERROR_RETVAL();
        }
        Py_RETURN_NONE;
    }

    /* Handle the case of long arguments (used by *_LARGE options) */
    if (PyLong_Check(obj)) {
        PY_LONG_LONG d = PyLong_AsLongLong(obj);
        if (d == -1 && PyErr_Occurred())
            return NULL;

        if (IS_LONG_OPTION(option) && (long)d == d)
            res = curl_easy_setopt(self->handle, (CURLoption)option, (long)d);
        else if (IS_OFF_T_OPTION(option) && (curl_off_t)d == d)
            res = curl_easy_setopt(self->handle, (CURLoption)option, (curl_off_t)d);
        else {
            PyErr_SetString(PyExc_TypeError, "longs are not supported for this option");
            return NULL;
        }
        if (res != CURLE_OK) {
            CURLERROR_RETVAL();
        }
        Py_RETURN_NONE;
    }

#undef IS_LONG_OPTION
#undef IS_OFF_T_OPTION

    /* Handle the case of file objects */
    if (PyFile_Check(obj)) {
        FILE *fp;

        /* Ensure the option specified a file as well as the input */
        switch (option) {
        case CURLOPT_READDATA:
        case CURLOPT_WRITEDATA:
            break;
        case CURLOPT_WRITEHEADER:
            if (self->w_cb != NULL) {
                PyErr_SetString(ErrorObject, "cannot combine WRITEHEADER with WRITEFUNCTION.");
                return NULL;
            }
            break;
        default:
            PyErr_SetString(PyExc_TypeError, "files are not supported for this option");
            return NULL;
        }

        fp = PyFile_AsFile(obj);
        if (fp == NULL) {
            PyErr_SetString(PyExc_TypeError, "second argument must be open file");
            return NULL;
        }
        res = curl_easy_setopt(self->handle, (CURLoption)option, fp);
        if (res != CURLE_OK) {
            CURLERROR_RETVAL();
        }
        Py_INCREF(obj);

        switch (option) {
        case CURLOPT_READDATA:
            ZAP(self->readdata_fp);
            self->readdata_fp = obj;
            break;
        case CURLOPT_WRITEDATA:
            ZAP(self->writedata_fp);
            self->writedata_fp = obj;
            break;
        case CURLOPT_WRITEHEADER:
            ZAP(self->writeheader_fp);
            self->writeheader_fp = obj;
            break;
        default:
            assert(0);
            break;
        }
        /* Return success */
        Py_RETURN_NONE;
    }

    /* Handle the case of list objects */
    if (PyList_Check(obj)) {
        struct curl_slist **old_slist = NULL;
        struct curl_slist *slist = NULL;
        Py_ssize_t i, len;

        switch (option) {
        case CURLOPT_HTTP200ALIASES:
            old_slist = &self->http200aliases;
            break;
        case CURLOPT_HTTPHEADER:
            old_slist = &self->httpheader;
            break;
        case CURLOPT_QUOTE:
            old_slist = &self->quote;
            break;
        case CURLOPT_POSTQUOTE:
            old_slist = &self->postquote;
            break;
        case CURLOPT_PREQUOTE:
            old_slist = &self->prequote;
            break;
#ifdef HAVE_CURLOPT_RESOLVE
        case CURLOPT_RESOLVE:
            old_slist = &self->resolve;
            break;
#endif
        case CURLOPT_HTTPPOST:
            break;
        default:
            /* None of the list options were recognized, raise exception */
            PyErr_SetString(PyExc_TypeError, "lists are not supported for this option");
            return NULL;
        }

        len = PyList_Size(obj);
        if (len == 0)
            Py_RETURN_NONE;

        /* Handle HTTPPOST different since we construct a HttpPost form struct */
        if (option == CURLOPT_HTTPPOST) {
            struct curl_httppost *post = NULL;
            struct curl_httppost *last = NULL;
            /* List of all references that have been INCed as a result of
             * this operation */
            PyObject *ref_params = NULL;

            for (i = 0; i < len; i++) {
                char *nstr = NULL, *cstr = NULL;
                Py_ssize_t nlen = -1, clen = -1;
                PyObject *listitem = PyList_GetItem(obj, i);

                if (!PyTuple_Check(listitem)) {
                    curl_formfree(post);
                    Py_XDECREF(ref_params);
                    PyErr_SetString(PyExc_TypeError, "list items must be tuple objects");
                    return NULL;
                }
                if (PyTuple_GET_SIZE(listitem) != 2) {
                    curl_formfree(post);
                    Py_XDECREF(ref_params);
                    PyErr_SetString(PyExc_TypeError, "tuple must contain two elements (name, value)");
                    return NULL;
                }
                if (PyString_AsStringAndSize(PyTuple_GET_ITEM(listitem, 0), &nstr, &nlen) != 0) {
                    curl_formfree(post);
                    Py_XDECREF(ref_params);
                    PyErr_SetString(PyExc_TypeError, "tuple must contain string as first element");
                    return NULL;
                }
                if (PyString_Check(PyTuple_GET_ITEM(listitem, 1))) {
                    /* Handle strings as second argument for backwards compatibility */
                    PyString_AsStringAndSize(PyTuple_GET_ITEM(listitem, 1), &cstr, &clen);
                    /* INFO: curl_formadd() internally does memdup() the data, so
                     * embedded NUL characters _are_ allowed here. */
                    res = curl_formadd(&post, &last,
                                       CURLFORM_COPYNAME, nstr,
                                       CURLFORM_NAMELENGTH, (long) nlen,
                                       CURLFORM_COPYCONTENTS, cstr,
                                       CURLFORM_CONTENTSLENGTH, (long) clen,
                                       CURLFORM_END);
                    if (res != CURLE_OK) {
                        curl_formfree(post);
                        Py_XDECREF(ref_params);
                        CURLERROR_RETVAL();
                    }
                }
                else if (PyTuple_Check(PyTuple_GET_ITEM(listitem, 1))) {
                    /* Supports content, file and content-type */
                    PyObject *t = PyTuple_GET_ITEM(listitem, 1);
                    Py_ssize_t tlen = PyTuple_Size(t);
                    int j, k, l;
                    struct curl_forms *forms = NULL;

                    /* Sanity check that there are at least two tuple items */
                    if (tlen < 2) {
                        curl_formfree(post);
                        Py_XDECREF(ref_params);
                        PyErr_SetString(PyExc_TypeError, "tuple must contain at least one option and one value");
                        return NULL;
                    }

                    /* Allocate enough space to accommodate length options for content or buffers, plus a terminator. */
                    forms = PyMem_Malloc(sizeof(struct curl_forms) * ((tlen*2) + 1));
                    if (forms == NULL) {
                        curl_formfree(post);
                        Py_XDECREF(ref_params);
                        PyErr_NoMemory();
                        return NULL;
                    }

                    /* Iterate all the tuple members pairwise */
                    for (j = 0, k = 0, l = 0; j < tlen; j += 2, l++) {
                        char *ostr;
                        Py_ssize_t olen;
                        int val;

                        if (j == (tlen-1)) {
                            PyErr_SetString(PyExc_TypeError, "expected value");
                            PyMem_Free(forms);
                            curl_formfree(post);
                            Py_XDECREF(ref_params);
                            return NULL;
                        }
                        if (!PyInt_Check(PyTuple_GET_ITEM(t, j))) {
                            PyErr_SetString(PyExc_TypeError, "option must be long");
                            PyMem_Free(forms);
                            curl_formfree(post);
                            Py_XDECREF(ref_params);
                            return NULL;
                        }
                        if (!PyString_Check(PyTuple_GET_ITEM(t, j+1))) {
                            PyErr_SetString(PyExc_TypeError, "value must be string");
                            PyMem_Free(forms);
                            curl_formfree(post);
                            Py_XDECREF(ref_params);
                            return NULL;
                        }

                        val = PyLong_AsLong(PyTuple_GET_ITEM(t, j));
                        if (val != CURLFORM_COPYCONTENTS &&
                            val != CURLFORM_FILE &&
                            val != CURLFORM_FILENAME &&
                            val != CURLFORM_CONTENTTYPE &&
                            val != CURLFORM_BUFFER &&
                            val != CURLFORM_BUFFERPTR)
                        {
                            PyErr_SetString(PyExc_TypeError, "unsupported option");
                            PyMem_Free(forms);
                            curl_formfree(post);
                            Py_XDECREF(ref_params);
                            return NULL;
                        }
                        PyString_AsStringAndSize(PyTuple_GET_ITEM(t, j+1), &ostr, &olen);
                        forms[k].option = val;
                        forms[k].value = ostr;
                        ++k;
                        if (val == CURLFORM_COPYCONTENTS) {
                            /* Contents can contain \0 bytes so we specify the length */
                            forms[k].option = CURLFORM_CONTENTSLENGTH;
                            forms[k].value = (const char *)olen;
                            ++k;
                        }
                        else if (val == CURLFORM_BUFFERPTR) {
                            PyObject *obj = PyTuple_GET_ITEM(t, j+1);

                            ref_params = PyList_New((Py_ssize_t)0);
                            if (ref_params == NULL) {
                                PyMem_Free(forms);
                                curl_formfree(post);
                                return NULL;
                            }
                            
                            /* Ensure that the buffer remains alive until curl_easy_cleanup() */
                            if (PyList_Append(ref_params, obj) != 0) {
                                PyMem_Free(forms);
                                curl_formfree(post);
                                Py_DECREF(ref_params);
                                return NULL;
                            }

                            /* As with CURLFORM_COPYCONTENTS, specify the length. */
                            forms[k].option = CURLFORM_BUFFERLENGTH;
                            forms[k].value = (const char *)olen;
                            ++k;
                        }
                    }
                    forms[k].option = CURLFORM_END;
                    res = curl_formadd(&post, &last,
                                       CURLFORM_COPYNAME, nstr,
                                       CURLFORM_NAMELENGTH, (long) nlen,
                                       CURLFORM_ARRAY, forms,
                                       CURLFORM_END);
                    PyMem_Free(forms);
                    if (res != CURLE_OK) {
                        curl_formfree(post);
                        Py_XDECREF(ref_params);
                        CURLERROR_RETVAL();
                    }
                } else {
                    /* Some other type was given, ignore */
                    curl_formfree(post);
                    Py_XDECREF(ref_params);
                    PyErr_SetString(PyExc_TypeError, "unsupported second type in tuple");
                    return NULL;
                }
            }
            res = curl_easy_setopt(self->handle, CURLOPT_HTTPPOST, post);
            /* Check for errors */
            if (res != CURLE_OK) {
                curl_formfree(post);
                Py_XDECREF(ref_params);
                CURLERROR_RETVAL();
            }
            /* Finally, free previously allocated httppost, ZAP any
             * buffer references, and update */
            curl_formfree(self->httppost);
            util_curl_xdecref(self, PYCURL_MEMGROUP_HTTPPOST, self->handle);
            self->httppost = post;

            /* The previous list of INCed references was ZAPed above; save
             * the new one so that we can clean it up on the next
             * self->httppost free. */
            self->httppost_ref_list = ref_params;

            Py_RETURN_NONE;
        }

        /* Just to be sure we do not bug off here */
        assert(old_slist != NULL && slist == NULL);

        /* Handle regular list operations on the other options */
        for (i = 0; i < len; i++) {
            PyObject *listitem = PyList_GetItem(obj, i);
            struct curl_slist *nlist;
            char *str;

            if (!PyString_Check(listitem)) {
                curl_slist_free_all(slist);
                PyErr_SetString(PyExc_TypeError, "list items must be string objects");
                return NULL;
            }
            /* INFO: curl_slist_append() internally does strdup() the data, so
             * no embedded NUL characters allowed here. */
            str = PyString_AsString_NoNUL(listitem);
            if (str == NULL) {
                curl_slist_free_all(slist);
                return NULL;
            }
            nlist = curl_slist_append(slist, str);
            if (nlist == NULL || nlist->data == NULL) {
                curl_slist_free_all(slist);
                return PyErr_NoMemory();
            }
            slist = nlist;
        }
        res = curl_easy_setopt(self->handle, (CURLoption)option, slist);
        /* Check for errors */
        if (res != CURLE_OK) {
            curl_slist_free_all(slist);
            CURLERROR_RETVAL();
        }
        /* Finally, free previously allocated list and update */
        curl_slist_free_all(*old_slist);
        *old_slist = slist;

        Py_RETURN_NONE;
    }

    /* Handle the case of function objects for callbacks */
    if (PyFunction_Check(obj) || PyCFunction_Check(obj) ||
        PyCallable_Check(obj) || PyMethod_Check(obj)) {
        /* We use function types here to make sure that our callback
         * definitions exactly match the <curl/curl.h> interface.
         */
        const curl_write_callback w_cb = write_callback;
        const curl_write_callback h_cb = header_callback;
        const curl_read_callback r_cb = read_callback;
        const curl_progress_callback pro_cb = progress_callback;
        const curl_debug_callback debug_cb = debug_callback;
        const curl_ioctl_callback ioctl_cb = ioctl_callback;
        const curl_opensocket_callback opensocket_cb = opensocket_callback;
        const curl_seek_callback seek_cb = seek_callback;

        switch(option) {
        case CURLOPT_WRITEFUNCTION:
            if (self->writeheader_fp != NULL) {
                PyErr_SetString(ErrorObject, "cannot combine WRITEFUNCTION with WRITEHEADER option.");
                return NULL;
            }
            Py_INCREF(obj);
            ZAP(self->writedata_fp);
            ZAP(self->w_cb);
            self->w_cb = obj;
            curl_easy_setopt(self->handle, CURLOPT_WRITEFUNCTION, w_cb);
            curl_easy_setopt(self->handle, CURLOPT_WRITEDATA, self);
            break;
        case CURLOPT_HEADERFUNCTION:
            Py_INCREF(obj);
            ZAP(self->h_cb);
            self->h_cb = obj;
            curl_easy_setopt(self->handle, CURLOPT_HEADERFUNCTION, h_cb);
            curl_easy_setopt(self->handle, CURLOPT_WRITEHEADER, self);
            break;
        case CURLOPT_READFUNCTION:
            Py_INCREF(obj);
            ZAP(self->readdata_fp);
            ZAP(self->r_cb);
            self->r_cb = obj;
            curl_easy_setopt(self->handle, CURLOPT_READFUNCTION, r_cb);
            curl_easy_setopt(self->handle, CURLOPT_READDATA, self);
            break;
        case CURLOPT_PROGRESSFUNCTION:
            Py_INCREF(obj);
            ZAP(self->pro_cb);
            self->pro_cb = obj;
            curl_easy_setopt(self->handle, CURLOPT_PROGRESSFUNCTION, pro_cb);
            curl_easy_setopt(self->handle, CURLOPT_PROGRESSDATA, self);
            break;
        case CURLOPT_DEBUGFUNCTION:
            Py_INCREF(obj);
            ZAP(self->debug_cb);
            self->debug_cb = obj;
            curl_easy_setopt(self->handle, CURLOPT_DEBUGFUNCTION, debug_cb);
            curl_easy_setopt(self->handle, CURLOPT_DEBUGDATA, self);
            break;
        case CURLOPT_IOCTLFUNCTION:
            Py_INCREF(obj);
            ZAP(self->ioctl_cb);
            self->ioctl_cb = obj;
            curl_easy_setopt(self->handle, CURLOPT_IOCTLFUNCTION, ioctl_cb);
            curl_easy_setopt(self->handle, CURLOPT_IOCTLDATA, self);
            break;
        case CURLOPT_OPENSOCKETFUNCTION:
            Py_INCREF(obj);
            ZAP(self->opensocket_cb);
            self->opensocket_cb = obj;
            curl_easy_setopt(self->handle, CURLOPT_OPENSOCKETFUNCTION, opensocket_cb);
            curl_easy_setopt(self->handle, CURLOPT_OPENSOCKETDATA, self);
            break;
        case CURLOPT_SEEKFUNCTION:
            Py_INCREF(obj);
            ZAP(self->seek_cb);
            self->seek_cb = obj;
            curl_easy_setopt(self->handle, CURLOPT_SEEKFUNCTION, seek_cb);
            curl_easy_setopt(self->handle, CURLOPT_SEEKDATA, self);
            break;

        default:
            /* None of the function options were recognized, raise exception */
            PyErr_SetString(PyExc_TypeError, "functions are not supported for this option");
            return NULL;
        }
        Py_RETURN_NONE;
    }
    /* handle the SHARE case */
    if (option == CURLOPT_SHARE) {
        CurlShareObject *share;

        if (self->share == NULL && (obj == NULL || obj == Py_None))
            Py_RETURN_NONE;

        if (self->share) {
            if (obj != Py_None) {
                PyErr_SetString(ErrorObject, "Curl object already sharing. Unshare first.");
                return NULL;
            }
            else {
                share = self->share;
                res = curl_easy_setopt(self->handle, CURLOPT_SHARE, NULL);
                if (res != CURLE_OK) {
                    CURLERROR_RETVAL();
                }
                self->share = NULL;
                Py_DECREF(share);
                Py_RETURN_NONE;
            }
        }
        if (Py_TYPE(obj) != p_CurlShare_Type) {
            PyErr_SetString(PyExc_TypeError, "invalid arguments to setopt");
            return NULL;
        }
        share = (CurlShareObject*)obj;
        res = curl_easy_setopt(self->handle, CURLOPT_SHARE, share->share_handle);
        if (res != CURLE_OK) {
            CURLERROR_RETVAL();
        }
        self->share = share;
        Py_INCREF(share);
        Py_RETURN_NONE;
    }

    /* Failed to match any of the function signatures -- return error */
error:
    PyErr_SetString(PyExc_TypeError, "invalid arguments to setopt");
    return NULL;
}


static PyObject *
do_curl_getinfo(CurlObject *self, PyObject *args)
{
    int option;
    int res;

    if (!PyArg_ParseTuple(args, "i:getinfo", &option)) {
        return NULL;
    }
    if (check_curl_state(self, 1 | 2, "getinfo") != 0) {
        return NULL;
    }

    switch (option) {
    case CURLINFO_FILETIME:
    case CURLINFO_HEADER_SIZE:
    case CURLINFO_HTTP_CODE:
    case CURLINFO_REDIRECT_COUNT:
    case CURLINFO_REQUEST_SIZE:
    case CURLINFO_SSL_VERIFYRESULT:
    case CURLINFO_HTTP_CONNECTCODE:
    case CURLINFO_HTTPAUTH_AVAIL:
    case CURLINFO_PROXYAUTH_AVAIL:
    case CURLINFO_OS_ERRNO:
    case CURLINFO_NUM_CONNECTS:
    case CURLINFO_LASTSOCKET:
        {
            /* Return PyInt as result */
            long l_res = -1;

            res = curl_easy_getinfo(self->handle, (CURLINFO)option, &l_res);
            /* Check for errors and return result */
            if (res != CURLE_OK) {
                CURLERROR_RETVAL();
            }
            return PyInt_FromLong(l_res);
        }

    case CURLINFO_CONTENT_TYPE:
    case CURLINFO_EFFECTIVE_URL:
    case CURLINFO_FTP_ENTRY_PATH:
    case CURLINFO_REDIRECT_URL:
    case CURLINFO_PRIMARY_IP:
        {
            /* Return PyString as result */
            char *s_res = NULL;

            res = curl_easy_getinfo(self->handle, (CURLINFO)option, &s_res);
            if (res != CURLE_OK) {
                CURLERROR_RETVAL();
            }
            /* If the resulting string is NULL, return None */
            if (s_res == NULL)
                Py_RETURN_NONE;
            return PyString_FromString(s_res);
        }

    case CURLINFO_CONNECT_TIME:
    case CURLINFO_APPCONNECT_TIME:
    case CURLINFO_CONTENT_LENGTH_DOWNLOAD:
    case CURLINFO_CONTENT_LENGTH_UPLOAD:
    case CURLINFO_NAMELOOKUP_TIME:
    case CURLINFO_PRETRANSFER_TIME:
    case CURLINFO_REDIRECT_TIME:
    case CURLINFO_SIZE_DOWNLOAD:
    case CURLINFO_SIZE_UPLOAD:
    case CURLINFO_SPEED_DOWNLOAD:
    case CURLINFO_SPEED_UPLOAD:
    case CURLINFO_STARTTRANSFER_TIME:
    case CURLINFO_TOTAL_TIME:
        {
            /* Return PyFloat as result */
            double d_res = 0.0;

            res = curl_easy_getinfo(self->handle, (CURLINFO)option, &d_res);
            if (res != CURLE_OK) {
                CURLERROR_RETVAL();
            }
            return PyFloat_FromDouble(d_res);
        }

    case CURLINFO_SSL_ENGINES:
    case CURLINFO_COOKIELIST:
        {
            /* Return a list of strings */
            struct curl_slist *slist = NULL;

            res = curl_easy_getinfo(self->handle, (CURLINFO)option, &slist);
            if (res != CURLE_OK) {
                CURLERROR_RETVAL();
            }
            return convert_slist(slist, 1 | 2);
        }

#ifdef HAVE_CURLOPT_CERTINFO
    case CURLINFO_CERTINFO:
        {
            /* Return a list of lists of 2-tuples */
            struct curl_certinfo *clist = NULL;
            res = curl_easy_getinfo(self->handle, CURLINFO_CERTINFO, &clist);
            if (res != CURLE_OK) {
                CURLERROR_RETVAL();
            } else {
                return convert_certinfo(clist);
            }
        }
#endif
    }

    /* Got wrong option on the method call */
    PyErr_SetString(PyExc_ValueError, "invalid argument to getinfo");
    return NULL;
}

#if LIBCURL_VERSION_NUM >= 0x071200  /* curl_easy_pause() appeared in libcurl 7.18.0 */

/* curl_easy_pause() can be called from inside a callback or outside */
static PyObject *
do_curl_pause(CurlObject *self, PyObject *args)
{
    int bitmask;
    CURLcode res;
#ifdef WITH_THREAD
    PyThreadState *saved_state;
#endif

    if (!PyArg_ParseTuple(args, "i:pause", &bitmask)) {
        return NULL;
    }
    if (check_curl_state(self, 1, "pause") != 0) {
        return NULL;
    }

#ifdef WITH_THREAD
    /* Save handle to current thread (used as context for python callbacks) */
    saved_state = self->state;
    PYCURL_BEGIN_ALLOW_THREADS

    /* We must allow threads here because unpausing a handle can cause
       some of its callbacks to be invoked immediately, from inside
       curl_easy_pause() */
#endif

    res = curl_easy_pause(self->handle, bitmask);

#ifdef WITH_THREAD
    PYCURL_END_ALLOW_THREADS

    /* Restore the thread-state to whatever it was on entry */
    self->state = saved_state;
#endif

    if (res != CURLE_OK) {
        CURLERROR_MSG("pause/unpause failed");
    } else {
        Py_INCREF(Py_None);
        return Py_None;
    }
}

static const char co_pause_doc [] =
    "pause(bitmask) -> None.  "
    "Pauses or unpauses a curl handle. Bitmask should be a value such as PAUSE_RECV or PAUSE_CONT.  "
    "Raises pycurl.error exception upon failure.\n";

#endif

/*************************************************************************
// CurlMultiObject
**************************************************************************/

/* --------------- construct/destruct (i.e. open/close) --------------- */

/* constructor - this is a module-level function returning a new instance */
static CurlMultiObject *
do_multi_new(PyObject *dummy)
{
    CurlMultiObject *self;

    UNUSED(dummy);

    /* Allocate python curl-multi object */
    self = (CurlMultiObject *) PyObject_GC_New(CurlMultiObject, p_CurlMulti_Type);
    if (self) {
        PyObject_GC_Track(self);
    }
    else {
        return NULL;
    }

    /* Initialize object attributes */
    self->dict = NULL;
#ifdef WITH_THREAD
    self->state = NULL;
#endif
    self->t_cb = NULL;
    self->s_cb = NULL;

    /* Allocate libcurl multi handle */
    self->multi_handle = curl_multi_init();
    if (self->multi_handle == NULL) {
        Py_DECREF(self);
        PyErr_SetString(ErrorObject, "initializing curl-multi failed");
        return NULL;
    }
    return self;
}

static void
util_multi_close(CurlMultiObject *self)
{
    assert(self != NULL);
#ifdef WITH_THREAD
    self->state = NULL;
#endif
    if (self->multi_handle != NULL) {
        CURLM *multi_handle = self->multi_handle;
        self->multi_handle = NULL;
        curl_multi_cleanup(multi_handle);
    }
}


static void
do_multi_dealloc(CurlMultiObject *self)
{
    PyObject_GC_UnTrack(self);
    Py_TRASHCAN_SAFE_BEGIN(self)

    ZAP(self->dict);
    util_multi_close(self);

    PyObject_GC_Del(self);
    Py_TRASHCAN_SAFE_END(self)
}


static PyObject *
do_multi_close(CurlMultiObject *self)
{
    if (check_multi_state(self, 2, "close") != 0) {
        return NULL;
    }
    util_multi_close(self);
    Py_RETURN_NONE;
}


/* --------------- GC support --------------- */

/* Drop references that may have created reference cycles. */
static int
do_multi_clear(CurlMultiObject *self)
{
    ZAP(self->dict);
    return 0;
}

static int
do_multi_traverse(CurlMultiObject *self, visitproc visit, void *arg)
{
    int err;
#undef VISIT
#define VISIT(v)    if ((v) != NULL && ((err = visit(v, arg)) != 0)) return err

    VISIT(self->dict);

    return 0;
#undef VISIT
}


/* --------------- setopt --------------- */

static int
multi_socket_callback(CURL *easy,
                      curl_socket_t s,
                      int what,
                      void *userp,
                      void *socketp)
{
    CurlMultiObject *self;
    PyObject *arglist;
    PyObject *result = NULL;
    PYCURL_DECLARE_THREAD_STATE;

    /* acquire thread */
    self = (CurlMultiObject *)userp;
    if (!PYCURL_ACQUIRE_THREAD_MULTI())
        return 0;

    /* check args */
    if (self->s_cb == NULL)
        goto silent_error;

    if (socketp == NULL) {
        Py_INCREF(Py_None);
        socketp = Py_None;
    }

    /* run callback */
    arglist = Py_BuildValue("(iiOO)", what, s, userp, (PyObject *)socketp);
    if (arglist == NULL)
        goto verbose_error;
    result = PyEval_CallObject(self->s_cb, arglist);
    Py_DECREF(arglist);
    if (result == NULL)
        goto verbose_error;

    /* return values from socket callbacks should be ignored */

silent_error:
    Py_XDECREF(result);
    PYCURL_RELEASE_THREAD();
    return 0;
verbose_error:
    PyErr_Print();
    goto silent_error;
    return 0;
}


static int
multi_timer_callback(CURLM *multi,
                     long timeout_ms,
                     void *userp)
{
    CurlMultiObject *self;
    PyObject *arglist;
    PyObject *result = NULL;
    int ret = 0;       /* always success */
    PYCURL_DECLARE_THREAD_STATE;

    UNUSED(multi);

    /* acquire thread */
    self = (CurlMultiObject *)userp;
    if (!PYCURL_ACQUIRE_THREAD_MULTI())
        return ret;

    /* check args */
    if (self->t_cb == NULL)
        goto silent_error;

    /* run callback */
    arglist = Py_BuildValue("(i)", timeout_ms);
    if (arglist == NULL)
        goto verbose_error;
    result = PyEval_CallObject(self->t_cb, arglist);
    Py_DECREF(arglist);
    if (result == NULL)
        goto verbose_error;

    /* return values from timer callbacks should be ignored */

silent_error:
    Py_XDECREF(result);
    PYCURL_RELEASE_THREAD();
    return ret;
verbose_error:
    PyErr_Print();
    goto silent_error;

    return 0;
}


static PyObject *
do_multi_setopt(CurlMultiObject *self, PyObject *args)
{
    int option;
    PyObject *obj;

    if (!PyArg_ParseTuple(args, "iO:setopt", &option, &obj))
        return NULL;
    if (check_multi_state(self, 1 | 2, "setopt") != 0)
        return NULL;

    /* Early checks of option value */
    if (option <= 0)
        goto error;
    if (option >= (int)CURLOPTTYPE_OFF_T + MOPTIONS_SIZE)
        goto error;
    if (option % 10000 >= MOPTIONS_SIZE)
        goto error;

    /* Handle the case of integer arguments */
    if (PyInt_Check(obj)) {
        long d = PyInt_AsLong(obj);
        switch(option) {
        case CURLMOPT_PIPELINING:
            curl_multi_setopt(self->multi_handle, option, d);
            break;
        case CURLMOPT_MAXCONNECTS:
            curl_multi_setopt(self->multi_handle, option, d);
            break;
        default:
            PyErr_SetString(PyExc_TypeError, "integers are not supported for this option");
            return NULL;
        }
        Py_RETURN_NONE;
    }
    if (PyFunction_Check(obj) || PyCFunction_Check(obj) ||
        PyCallable_Check(obj) || PyMethod_Check(obj)) {
        /* We use function types here to make sure that our callback
         * definitions exactly match the <curl/multi.h> interface.
         */
        const curl_multi_timer_callback t_cb = multi_timer_callback;
        const curl_socket_callback s_cb = multi_socket_callback;

        switch(option) {
        case CURLMOPT_SOCKETFUNCTION:
            curl_multi_setopt(self->multi_handle, CURLMOPT_SOCKETFUNCTION, s_cb);
            curl_multi_setopt(self->multi_handle, CURLMOPT_SOCKETDATA, self);
            Py_INCREF(obj);
            self->s_cb = obj;
            break;
        case CURLMOPT_TIMERFUNCTION:
            curl_multi_setopt(self->multi_handle, CURLMOPT_TIMERFUNCTION, t_cb);
            curl_multi_setopt(self->multi_handle, CURLMOPT_TIMERDATA, self);
            Py_INCREF(obj);
            self->t_cb = obj;
            break;
        default:
            PyErr_SetString(PyExc_TypeError, "callables are not supported for this option");
            return NULL;
        }
        Py_RETURN_NONE;
    }
    /* Failed to match any of the function signatures -- return error */
error:
    PyErr_SetString(PyExc_TypeError, "invalid arguments to setopt");
    return NULL;
}


/* --------------- timeout --------------- */

static PyObject *
do_multi_timeout(CurlMultiObject *self)
{
    CURLMcode res;
    long timeout;

    if (check_multi_state(self, 1 | 2, "timeout") != 0) {
        return NULL;
    }

    res = curl_multi_timeout(self->multi_handle, &timeout);
    if (res != CURLM_OK) {
        CURLERROR_MSG("timeout failed");
    }

    /* Return number of millisecs until timeout */
    return Py_BuildValue("l", timeout);
}


/* --------------- assign --------------- */

static PyObject *
do_multi_assign(CurlMultiObject *self, PyObject *args)
{
    CURLMcode res;
    curl_socket_t socket;
    PyObject *obj;

    if (!PyArg_ParseTuple(args, "iO:assign", &socket, &obj))
        return NULL;
    if (check_multi_state(self, 1 | 2, "assign") != 0) {
        return NULL;
    }
    Py_INCREF(obj);

    res = curl_multi_assign(self->multi_handle, socket, obj);
    if (res != CURLM_OK) {
        CURLERROR_MSG("assign failed");
    }

    Py_RETURN_NONE;
}


/* --------------- socket_action --------------- */
static PyObject *
do_multi_socket_action(CurlMultiObject *self, PyObject *args)
{
    CURLMcode res;
    curl_socket_t socket;
    int ev_bitmask;
    int running = -1;
    
    if (!PyArg_ParseTuple(args, "ii:socket_action", &socket, &ev_bitmask))
        return NULL;
    if (check_multi_state(self, 1 | 2, "socket_action") != 0) {
        return NULL;
    }

    PYCURL_BEGIN_ALLOW_THREADS
    res = curl_multi_socket_action(self->multi_handle, socket, ev_bitmask, &running);
    PYCURL_END_ALLOW_THREADS

    if (res != CURLM_OK) {
        CURLERROR_MSG("multi_socket_action failed");
    }
    /* Return a tuple with the result and the number of running handles */
    return Py_BuildValue("(ii)", (int)res, running);
}

/* --------------- socket_all --------------- */

static PyObject *
do_multi_socket_all(CurlMultiObject *self)
{
    CURLMcode res;
    int running = -1;

    if (check_multi_state(self, 1 | 2, "socket_all") != 0) {
        return NULL;
    }

    PYCURL_BEGIN_ALLOW_THREADS
    res = curl_multi_socket_all(self->multi_handle, &running);
    PYCURL_END_ALLOW_THREADS

    /* We assume these errors are ok, otherwise raise exception */
    if (res != CURLM_OK && res != CURLM_CALL_MULTI_PERFORM) {
        CURLERROR_MSG("perform failed");
    }

    /* Return a tuple with the result and the number of running handles */
    return Py_BuildValue("(ii)", (int)res, running);
}


/* --------------- perform --------------- */

static PyObject *
do_multi_perform(CurlMultiObject *self)
{
    CURLMcode res;
    int running = -1;

    if (check_multi_state(self, 1 | 2, "perform") != 0) {
        return NULL;
    }

    PYCURL_BEGIN_ALLOW_THREADS
    res = curl_multi_perform(self->multi_handle, &running);
    PYCURL_END_ALLOW_THREADS

    /* We assume these errors are ok, otherwise raise exception */
    if (res != CURLM_OK && res != CURLM_CALL_MULTI_PERFORM) {
        CURLERROR_MSG("perform failed");
    }

    /* Return a tuple with the result and the number of running handles */
    return Py_BuildValue("(ii)", (int)res, running);
}


/* --------------- add_handle/remove_handle --------------- */

/* static utility function */
static int
check_multi_add_remove(const CurlMultiObject *self, const CurlObject *obj)
{
    /* check CurlMultiObject status */
    assert_multi_state(self);
    if (self->multi_handle == NULL) {
        PyErr_SetString(ErrorObject, "cannot add/remove handle - multi-stack is closed");
        return -1;
    }
#ifdef WITH_THREAD
    if (self->state != NULL) {
        PyErr_SetString(ErrorObject, "cannot add/remove handle - multi_perform() already running");
        return -1;
    }
#endif
    /* check CurlObject status */
    assert_curl_state(obj);
#ifdef WITH_THREAD
    if (obj->state != NULL) {
        PyErr_SetString(ErrorObject, "cannot add/remove handle - perform() of curl object already running");
        return -1;
    }
#endif
    if (obj->multi_stack != NULL && obj->multi_stack != self) {
        PyErr_SetString(ErrorObject, "cannot add/remove handle - curl object already on another multi-stack");
        return -1;
    }
    return 0;
}


static PyObject *
do_multi_add_handle(CurlMultiObject *self, PyObject *args)
{
    CurlObject *obj;
    CURLMcode res;

    if (!PyArg_ParseTuple(args, "O!:add_handle", p_Curl_Type, &obj)) {
        return NULL;
    }
    if (check_multi_add_remove(self, obj) != 0) {
        return NULL;
    }
    if (obj->handle == NULL) {
        PyErr_SetString(ErrorObject, "curl object already closed");
        return NULL;
    }
    if (obj->multi_stack == self) {
        PyErr_SetString(ErrorObject, "curl object already on this multi-stack");
        return NULL;
    }
    assert(obj->multi_stack == NULL);
    res = curl_multi_add_handle(self->multi_handle, obj->handle);
    if (res != CURLM_OK) {
        CURLERROR_MSG("curl_multi_add_handle() failed due to internal errors");
    }
    obj->multi_stack = self;
    Py_INCREF(self);
    Py_RETURN_NONE;
}


static PyObject *
do_multi_remove_handle(CurlMultiObject *self, PyObject *args)
{
    CurlObject *obj;
    CURLMcode res;

    if (!PyArg_ParseTuple(args, "O!:remove_handle", p_Curl_Type, &obj)) {
        return NULL;
    }
    if (check_multi_add_remove(self, obj) != 0) {
        return NULL;
    }
    if (obj->handle == NULL) {
        /* CurlObject handle already closed -- ignore */
        goto done;
    }
    if (obj->multi_stack != self) {
        PyErr_SetString(ErrorObject, "curl object not on this multi-stack");
        return NULL;
    }
    res = curl_multi_remove_handle(self->multi_handle, obj->handle);
    if (res != CURLM_OK) {
        CURLERROR_MSG("curl_multi_remove_handle() failed due to internal errors");
    }
    assert(obj->multi_stack == self);
    obj->multi_stack = NULL;
    Py_DECREF(self);
done:
    Py_RETURN_NONE;
}


/* --------------- fdset ---------------------- */

static PyObject *
do_multi_fdset(CurlMultiObject *self)
{
    CURLMcode res;
    int max_fd = -1, fd;
    PyObject *ret = NULL;
    PyObject *read_list = NULL, *write_list = NULL, *except_list = NULL;
    PyObject *py_fd = NULL;

    if (check_multi_state(self, 1 | 2, "fdset") != 0) {
        return NULL;
    }

    /* Clear file descriptor sets */
    FD_ZERO(&self->read_fd_set);
    FD_ZERO(&self->write_fd_set);
    FD_ZERO(&self->exc_fd_set);

    /* Don't bother releasing the gil as this is just a data structure operation */
    res = curl_multi_fdset(self->multi_handle, &self->read_fd_set,
                           &self->write_fd_set, &self->exc_fd_set, &max_fd);
    if (res != CURLM_OK) {
        CURLERROR_MSG("curl_multi_fdset() failed due to internal errors");
    }

    /* Allocate lists. */
    if ((read_list = PyList_New((Py_ssize_t)0)) == NULL) goto error;
    if ((write_list = PyList_New((Py_ssize_t)0)) == NULL) goto error;
    if ((except_list = PyList_New((Py_ssize_t)0)) == NULL) goto error;

    /* Populate lists */
    for (fd = 0; fd < max_fd + 1; fd++) {
        if (FD_ISSET(fd, &self->read_fd_set)) {
            if ((py_fd = PyInt_FromLong((long)fd)) == NULL) goto error;
            if (PyList_Append(read_list, py_fd) != 0) goto error;
            Py_DECREF(py_fd);
            py_fd = NULL;
        }
        if (FD_ISSET(fd, &self->write_fd_set)) {
            if ((py_fd = PyInt_FromLong((long)fd)) == NULL) goto error;
            if (PyList_Append(write_list, py_fd) != 0) goto error;
            Py_DECREF(py_fd);
            py_fd = NULL;
        }
        if (FD_ISSET(fd, &self->exc_fd_set)) {
            if ((py_fd = PyInt_FromLong((long)fd)) == NULL) goto error;
            if (PyList_Append(except_list, py_fd) != 0) goto error;
            Py_DECREF(py_fd);
            py_fd = NULL;
        }
    }

    /* Return a tuple with the 3 lists */
    ret = Py_BuildValue("(OOO)", read_list, write_list, except_list);
error:
    Py_XDECREF(py_fd);
    Py_XDECREF(except_list);
    Py_XDECREF(write_list);
    Py_XDECREF(read_list);
    return ret;
}


/* --------------- info_read --------------- */

static PyObject *
do_multi_info_read(CurlMultiObject *self, PyObject *args)
{
    PyObject *ret = NULL;
    PyObject *ok_list = NULL, *err_list = NULL;
    CURLMsg *msg;
    int in_queue = 0, num_results = INT_MAX;

    /* Sanity checks */
    if (!PyArg_ParseTuple(args, "|i:info_read", &num_results)) {
        return NULL;
    }
    if (num_results <= 0) {
        PyErr_SetString(ErrorObject, "argument to info_read must be greater than zero");
        return NULL;
    }
    if (check_multi_state(self, 1 | 2, "info_read") != 0) {
        return NULL;
    }

    if ((ok_list = PyList_New((Py_ssize_t)0)) == NULL) goto error;
    if ((err_list = PyList_New((Py_ssize_t)0)) == NULL) goto error;

    /* Loop through all messages */
    while ((msg = curl_multi_info_read(self->multi_handle, &in_queue)) != NULL) {
        CURLcode res;
        CurlObject *co = NULL;

        /* Check for termination as specified by the user */
        if (num_results-- <= 0) {
            break;
        }

        /* Fetch the curl object that corresponds to the curl handle in the message */
        res = curl_easy_getinfo(msg->easy_handle, CURLINFO_PRIVATE, &co);
        if (res != CURLE_OK || co == NULL) {
            Py_DECREF(err_list);
            Py_DECREF(ok_list);
            CURLERROR_MSG("Unable to fetch curl handle from curl object");
        }
        assert(Py_TYPE(co) == p_Curl_Type);
        if (msg->msg != CURLMSG_DONE) {
            /* FIXME: what does this mean ??? */
        }
        if (msg->data.result == CURLE_OK) {
            /* Append curl object to list of objects which succeeded */
            if (PyList_Append(ok_list, (PyObject *)co) != 0) {
                goto error;
            }
        }
        else {
            /* Create a result tuple that will get added to err_list. */
            PyObject *v = Py_BuildValue("(Ois)", (PyObject *)co, (int)msg->data.result, co->error);
            /* Append curl object to list of objects which failed */
            if (v == NULL || PyList_Append(err_list, v) != 0) {
                Py_XDECREF(v);
                goto error;
            }
            Py_DECREF(v);
        }
    }
    /* Return (number of queued messages, [ok_objects], [error_objects]) */
    ret = Py_BuildValue("(iOO)", in_queue, ok_list, err_list);
error:
    Py_XDECREF(err_list);
    Py_XDECREF(ok_list);
    return ret;
}


/* --------------- select --------------- */

static PyObject *
do_multi_select(CurlMultiObject *self, PyObject *args)
{
    int max_fd = -1, n;
    double timeout = -1.0;
    struct timeval tv, *tvp;
    CURLMcode res;

    if (!PyArg_ParseTuple(args, "d:select", &timeout)) {
        return NULL;
    }
    if (check_multi_state(self, 1 | 2, "select") != 0) {
        return NULL;
    }

    if (timeout < 0 || timeout >= 365 * 24 * 60 * 60) {
        PyErr_SetString(PyExc_OverflowError, "invalid timeout period");
        return NULL;
    } else {
        long seconds = (long)timeout;
        timeout = timeout - (double)seconds;
        assert(timeout >= 0.0); assert(timeout < 1.0);
        tv.tv_sec = seconds;
        tv.tv_usec = (long)(timeout*1000000.0);
        tvp = &tv;
    }

    FD_ZERO(&self->read_fd_set);
    FD_ZERO(&self->write_fd_set);
    FD_ZERO(&self->exc_fd_set);

    res = curl_multi_fdset(self->multi_handle, &self->read_fd_set,
                           &self->write_fd_set, &self->exc_fd_set, &max_fd);
    if (res != CURLM_OK) {
        CURLERROR_MSG("multi_fdset failed");
    }

    if (max_fd < 0) {
        n = 0;
    }
    else {
        Py_BEGIN_ALLOW_THREADS
        n = select(max_fd + 1, &self->read_fd_set, &self->write_fd_set, &self->exc_fd_set, tvp);
        Py_END_ALLOW_THREADS
        /* info: like Python's socketmodule.c we do not raise an exception
         *       if select() fails - we'll leave it to the actual libcurl
         *       socket code to report any errors.
         */
    }

    return PyInt_FromLong(n);
}


/*************************************************************************
// type definitions
**************************************************************************/

/* --------------- methods --------------- */

static const char cso_setopt_doc [] =
    "setopt(option, parameter) -> None.  "
    "Set curl share option.  Raises pycurl.error exception upon failure.\n";
static const char co_close_doc [] =
    "close() -> None.  "
    "Close handle and end curl session.\n";
static const char co_errstr_doc [] =
    "errstr() -> String.  "
    "Return the internal libcurl error buffer string.\n";
static const char co_getinfo_doc [] =
    "getinfo(info) -> Res.  "
    "Extract and return information from a curl session.  Raises pycurl.error exception upon failure.\n";
static const char co_perform_doc [] =
    "perform() -> None.  "
    "Perform a file transfer.  Raises pycurl.error exception upon failure.\n";
static const char co_setopt_doc [] =
    "setopt(option, parameter) -> None.  "
    "Set curl session option.  Raises pycurl.error exception upon failure.\n";
static const char co_unsetopt_doc [] =
    "unsetopt(option) -> None.  "
    "Reset curl session option to default value.  Raises pycurl.error exception upon failure.\n";
static const char co_reset_doc [] =
    "reset() -> None. "
    "Reset all options set on curl handle to default values, but preserves live connections, session ID cache, DNS cache, cookies, and shares.\n";

static const char co_multi_fdset_doc [] =
    "fdset() -> Tuple.  "
    "Returns a tuple of three lists that can be passed to the select.select() method .\n";
static const char co_multi_info_read_doc [] =
    "info_read([max_objects]) -> Tuple. "
    "Returns a tuple (number of queued handles, [curl objects]).\n";
static const char co_multi_select_doc [] =
    "select([timeout]) -> Int.  "
    "Returns result from doing a select() on the curl multi file descriptor with the given timeout.\n";
static const char co_multi_socket_action_doc [] =
    "socket_action(sockfd, ev_bitmask) -> Tuple.  "
    "Returns result from doing a socket_action() on the curl multi file descriptor with the given timeout.\n";
static const char co_multi_socket_all_doc [] =
    "socket_all() -> Tuple.  "
    "Returns result from doing a socket_all() on the curl multi file descriptor with the given timeout.\n";

static PyMethodDef curlshareobject_methods[] = {
    {"setopt", (PyCFunction)do_curlshare_setopt, METH_VARARGS, cso_setopt_doc},
    {NULL, NULL, 0, 0}
};

static PyMethodDef curlobject_methods[] = {
    {"close", (PyCFunction)do_curl_close, METH_NOARGS, co_close_doc},
    {"errstr", (PyCFunction)do_curl_errstr, METH_NOARGS, co_errstr_doc},
    {"getinfo", (PyCFunction)do_curl_getinfo, METH_VARARGS, co_getinfo_doc},
#if LIBCURL_VERSION_NUM >= 0x071200  /* curl_easy_pause() appeared in libcurl 7.18.0 */
    {"pause", (PyCFunction)do_curl_pause, METH_VARARGS, co_pause_doc},
#endif
    {"perform", (PyCFunction)do_curl_perform, METH_NOARGS, co_perform_doc},
    {"setopt", (PyCFunction)do_curl_setopt, METH_VARARGS, co_setopt_doc},
    {"unsetopt", (PyCFunction)do_curl_unsetopt, METH_VARARGS, co_unsetopt_doc},
    {"reset", (PyCFunction)do_curl_reset, METH_NOARGS, co_reset_doc},
    {NULL, NULL, 0, NULL}
};

static PyMethodDef curlmultiobject_methods[] = {
    {"add_handle", (PyCFunction)do_multi_add_handle, METH_VARARGS, NULL},
    {"close", (PyCFunction)do_multi_close, METH_NOARGS, NULL},
    {"fdset", (PyCFunction)do_multi_fdset, METH_NOARGS, co_multi_fdset_doc},
    {"info_read", (PyCFunction)do_multi_info_read, METH_VARARGS, co_multi_info_read_doc},
    {"perform", (PyCFunction)do_multi_perform, METH_NOARGS, NULL},
    {"socket_action", (PyCFunction)do_multi_socket_action, METH_VARARGS, co_multi_socket_action_doc},
    {"socket_all", (PyCFunction)do_multi_socket_all, METH_NOARGS, co_multi_socket_all_doc},
    {"setopt", (PyCFunction)do_multi_setopt, METH_VARARGS, NULL},
    {"timeout", (PyCFunction)do_multi_timeout, METH_NOARGS, NULL},
    {"assign", (PyCFunction)do_multi_assign, METH_VARARGS, NULL},
    {"remove_handle", (PyCFunction)do_multi_remove_handle, METH_VARARGS, NULL},
    {"select", (PyCFunction)do_multi_select, METH_VARARGS, co_multi_select_doc},
    {NULL, NULL, 0, NULL}
};


/* --------------- setattr/getattr --------------- */

static PyObject *curlobject_constants = NULL;
static PyObject *curlmultiobject_constants = NULL;
static PyObject *curlshareobject_constants = NULL;

static int
my_setattr(PyObject **dict, char *name, PyObject *v)
{
    if (v == NULL) {
        int rv = -1;
        if (*dict != NULL)
            rv = PyDict_DelItemString(*dict, name);
        if (rv < 0)
            PyErr_SetString(PyExc_AttributeError, "delete non-existing attribute");
        return rv;
    }
    if (*dict == NULL) {
        *dict = PyDict_New();
        if (*dict == NULL)
            return -1;
    }
    return PyDict_SetItemString(*dict, name, v);
}

static PyObject *
my_getattr(PyObject *co, char *name, PyObject *dict1, PyObject *dict2, PyMethodDef *m)
{
    PyObject *v = NULL;
    if (v == NULL && dict1 != NULL)
        v = PyDict_GetItemString(dict1, name);
    if (v == NULL && dict2 != NULL)
        v = PyDict_GetItemString(dict2, name);
    if (v != NULL) {
        Py_INCREF(v);
        return v;
    }
    return Py_FindMethod(m, co, name);
}

static int
do_share_setattr(CurlShareObject *so, char *name, PyObject *v)
{
    assert_share_state(so);
    return my_setattr(&so->dict, name, v);
}

static int
do_curl_setattr(CurlObject *co, char *name, PyObject *v)
{
    assert_curl_state(co);
    return my_setattr(&co->dict, name, v);
}

static int
do_multi_setattr(CurlMultiObject *co, char *name, PyObject *v)
{
    assert_multi_state(co);
    return my_setattr(&co->dict, name, v);
}

static PyObject *
do_share_getattr(CurlShareObject *cso, char *name)
{
    assert_share_state(cso);
    return my_getattr((PyObject *)cso, name, cso->dict,
                      curlshareobject_constants, curlshareobject_methods);
}

static PyObject *
do_curl_getattr(CurlObject *co, char *name)
{
    assert_curl_state(co);
    return my_getattr((PyObject *)co, name, co->dict,
                      curlobject_constants, curlobject_methods);
}

static PyObject *
do_multi_getattr(CurlMultiObject *co, char *name)
{
    assert_multi_state(co);
    return my_getattr((PyObject *)co, name, co->dict,
                      curlmultiobject_constants, curlmultiobject_methods);
}


/* --------------- actual type definitions --------------- */

static PyTypeObject CurlShare_Type = {
    PyObject_HEAD_INIT(NULL)
    0,                          /* ob_size */
    "pycurl.CurlShare",         /* tp_name */
    sizeof(CurlMultiObject),    /* tp_basicsize */
    0,                          /* tp_itemsize */
    /* Methods */
    (destructor)do_share_dealloc,   /* tp_dealloc */
    0,                          /* tp_print */
    (getattrfunc)do_share_getattr,  /* tp_getattr */
    (setattrfunc)do_share_setattr,  /* tp_setattr */
    0,                          /* tp_compare */
    0,                          /* tp_repr */
    0,                          /* tp_as_number */
    0,                          /* tp_as_sequence */
    0,                          /* tp_as_mapping */
    0,                          /* tp_hash */
    0,                          /* tp_call */
    0,                          /* tp_str */
    0,                          /* tp_getattro */
    0,                          /* tp_setattro */
    0,                          /* tp_as_buffer */
    Py_TPFLAGS_HAVE_GC,         /* tp_flags */
    0,                          /* tp_doc */
    (traverseproc)do_share_traverse, /* tp_traverse */
    (inquiry)do_share_clear     /* tp_clear */
    /* More fields follow here, depending on your Python version. You can
     * safely ignore any compiler warnings about missing initializers.
     */
};

static PyTypeObject Curl_Type = {
    PyObject_HEAD_INIT(NULL)
    0,                          /* ob_size */
    "pycurl.Curl",              /* tp_name */
    sizeof(CurlObject),         /* tp_basicsize */
    0,                          /* tp_itemsize */
    /* Methods */
    (destructor)do_curl_dealloc,   /* tp_dealloc */
    0,                          /* tp_print */
    (getattrfunc)do_curl_getattr,  /* tp_getattr */
    (setattrfunc)do_curl_setattr,  /* tp_setattr */
    0,                          /* tp_compare */
    0,                          /* tp_repr */
    0,                          /* tp_as_number */
    0,                          /* tp_as_sequence */
    0,                          /* tp_as_mapping */
    0,                          /* tp_hash */
    0,                          /* tp_call */
    0,                          /* tp_str */
    0,                          /* tp_getattro */
    0,                          /* tp_setattro */
    0,                          /* tp_as_buffer */
    Py_TPFLAGS_HAVE_GC,         /* tp_flags */
    0,                          /* tp_doc */
    (traverseproc)do_curl_traverse, /* tp_traverse */
    (inquiry)do_curl_clear      /* tp_clear */
    /* More fields follow here, depending on your Python version. You can
     * safely ignore any compiler warnings about missing initializers.
     */
};

static PyTypeObject CurlMulti_Type = {
    PyObject_HEAD_INIT(NULL)
    0,                          /* ob_size */
    "pycurl.CurlMulti",         /* tp_name */
    sizeof(CurlMultiObject),    /* tp_basicsize */
    0,                          /* tp_itemsize */
    /* Methods */
    (destructor)do_multi_dealloc,   /* tp_dealloc */
    0,                          /* tp_print */
    (getattrfunc)do_multi_getattr,  /* tp_getattr */
    (setattrfunc)do_multi_setattr,  /* tp_setattr */
    0,                          /* tp_compare */
    0,                          /* tp_repr */
    0,                          /* tp_as_number */
    0,                          /* tp_as_sequence */
    0,                          /* tp_as_mapping */
    0,                          /* tp_hash */
    0,                          /* tp_call */
    0,                          /* tp_str */
    0,                          /* tp_getattro */
    0,                          /* tp_setattro */
    0,                          /* tp_as_buffer */
    Py_TPFLAGS_HAVE_GC,         /* tp_flags */
    0,                          /* tp_doc */
    (traverseproc)do_multi_traverse, /* tp_traverse */
    (inquiry)do_multi_clear     /* tp_clear */
    /* More fields follow here, depending on your Python version. You can
     * safely ignore any compiler warnings about missing initializers.
     */
};

static int
are_global_init_flags_valid(int flags)
{
#ifdef CURL_GLOBAL_ACK_EINTR
    /* CURL_GLOBAL_ACK_EINTR was introduced in libcurl-7.30.0 */
    return !(flags & ~(CURL_GLOBAL_ALL | CURL_GLOBAL_ACK_EINTR));
#else
    return !(flags & ~(CURL_GLOBAL_ALL));
#endif
}

/*************************************************************************
// module level
// Note that the object constructors (do_curl_new, do_multi_new)
// are module-level functions as well.
**************************************************************************/

static PyObject *
do_global_init(PyObject *dummy, PyObject *args)
{
    int res, option;

    UNUSED(dummy);
    if (!PyArg_ParseTuple(args, "i:global_init", &option)) {
        return NULL;
    }

    if (!are_global_init_flags_valid(option)) {
        PyErr_SetString(PyExc_ValueError, "invalid option to global_init");
        return NULL;
    }

    res = curl_global_init(option);
    if (res != CURLE_OK) {
        PyErr_SetString(ErrorObject, "unable to set global option");
        return NULL;
    }

    Py_RETURN_NONE;
}


static PyObject *
do_global_cleanup(PyObject *dummy)
{
    UNUSED(dummy);
    curl_global_cleanup();
#ifdef PYCURL_NEED_SSL_TSL
    pycurl_ssl_cleanup();
#endif
    Py_RETURN_NONE;
}


static PyObject *vi_str(const char *s)
{
    if (s == NULL)
        Py_RETURN_NONE;
    while (*s == ' ' || *s == '\t')
        s++;
    return PyString_FromString(s);
}

static PyObject *
do_version_info(PyObject *dummy, PyObject *args)
{
    const curl_version_info_data *vi;
    PyObject *ret = NULL;
    PyObject *protocols = NULL;
    PyObject *tmp;
    Py_ssize_t i;
    int stamp = CURLVERSION_NOW;

    UNUSED(dummy);
    if (!PyArg_ParseTuple(args, "|i:version_info", &stamp)) {
        return NULL;
    }
    vi = curl_version_info((CURLversion) stamp);
    if (vi == NULL) {
        PyErr_SetString(ErrorObject, "unable to get version info");
        return NULL;
    }

    /* INFO: actually libcurl in lib/version.c does ignore
     * the "stamp" parameter, and so do we. */

    for (i = 0; vi->protocols[i] != NULL; )
        i++;
    protocols = PyTuple_New(i);
    if (protocols == NULL)
        goto error;
    for (i = 0; vi->protocols[i] != NULL; i++) {
        tmp = vi_str(vi->protocols[i]);
        if (tmp == NULL)
            goto error;
        PyTuple_SET_ITEM(protocols, i, tmp);
    }
    ret = PyTuple_New((Py_ssize_t)12);
    if (ret == NULL)
        goto error;

#define SET(i, v) \
        tmp = (v); if (tmp == NULL) goto error; PyTuple_SET_ITEM(ret, i, tmp)
    SET(0, PyInt_FromLong((long) vi->age));
    SET(1, vi_str(vi->version));
    SET(2, PyInt_FromLong(vi->version_num));
    SET(3, vi_str(vi->host));
    SET(4, PyInt_FromLong(vi->features));
    SET(5, vi_str(vi->ssl_version));
    SET(6, PyInt_FromLong(vi->ssl_version_num));
    SET(7, vi_str(vi->libz_version));
    SET(8, protocols);
    SET(9, vi_str(vi->ares));
    SET(10, PyInt_FromLong(vi->ares_num));
    SET(11, vi_str(vi->libidn));
#undef SET
    return ret;

error:
    Py_XDECREF(ret);
    Py_XDECREF(protocols);
    return NULL;
}


/* Per function docstrings */
static const char pycurl_global_init_doc[] =
    "global_init(option) -> None.  "
    "Initialize curl environment.\n";

static const char pycurl_global_cleanup_doc[] =
    "global_cleanup() -> None.  "
    "Cleanup curl environment.\n";

static const char pycurl_version_info_doc[] =
    "version_info() -> tuple.  "
    "Returns a 12-tuple with the version info.\n";

static const char pycurl_share_new_doc[] =
    "CurlShare() -> New CurlShare object.";

static const char pycurl_curl_new_doc[] =
    "Curl() -> New curl object.  "
    "Implicitly calls global_init() if not called.\n";

static const char pycurl_multi_new_doc[] =
    "CurlMulti() -> New curl multi-object.\n";


/* List of functions defined in this module */
static PyMethodDef curl_methods[] = {
    {"global_init", (PyCFunction)do_global_init, METH_VARARGS, pycurl_global_init_doc},
    {"global_cleanup", (PyCFunction)do_global_cleanup, METH_NOARGS, pycurl_global_cleanup_doc},
    {"version_info", (PyCFunction)do_version_info, METH_VARARGS, pycurl_version_info_doc},
    {"Curl", (PyCFunction)do_curl_new, METH_NOARGS, pycurl_curl_new_doc},
    {"CurlMulti", (PyCFunction)do_multi_new, METH_NOARGS, pycurl_multi_new_doc},
    {"CurlShare", (PyCFunction)do_share_new, METH_NOARGS, pycurl_share_new_doc},
    {NULL, NULL, 0, NULL}
};


/* Module docstring */
static const char module_doc [] =
"This module implements an interface to the cURL library.\n"
"\n"
"Types:\n"
"\n"
"Curl() -> New object.  Create a new curl object.\n"
"CurlMulti() -> New object.  Create a new curl multi-object.\n"
"\n"
"Functions:\n"
"\n"
"global_init(option) -> None.  Initialize curl environment.\n"
"global_cleanup() -> None.  Cleanup curl environment.\n"
"version_info() -> tuple.  Return version information.\n"
;


/* Helper functions for inserting constants into the module namespace */

static void
insobj2(PyObject *dict1, PyObject *dict2, char *name, PyObject *value)
{
    /* Insert an object into one or two dicts. Eats a reference to value.
     * See also the implementation of PyDict_SetItemString(). */
    PyObject *key = NULL;

    if (dict1 == NULL && dict2 == NULL)
        goto error;
    if (value == NULL)
        goto error;
    key = PyString_FromString(name);
    if (key == NULL)
        goto error;
#if 0
    PyString_InternInPlace(&key);   /* XXX Should we really? */
#endif
    if (dict1 != NULL) {
        assert(PyDict_GetItem(dict1, key) == NULL);
        if (PyDict_SetItem(dict1, key, value) != 0)
            goto error;
    }
    if (dict2 != NULL && dict2 != dict1) {
        assert(PyDict_GetItem(dict2, key) == NULL);
        if (PyDict_SetItem(dict2, key, value) != 0)
            goto error;
    }
    Py_DECREF(key);
    Py_DECREF(value);
    return;
error:
    Py_FatalError("pycurl: insobj2() failed");
    assert(0);
}

static void
insstr(PyObject *d, char *name, char *value)
{
    PyObject *v = PyString_FromString(value);
    insobj2(d, NULL, name, v);
}

static void
insint(PyObject *d, char *name, long value)
{
    PyObject *v = PyInt_FromLong(value);
    insobj2(d, NULL, name, v);
}

static void
insint_s(PyObject *d, char *name, long value)
{
    PyObject *v = PyInt_FromLong(value);
    insobj2(d, curlshareobject_constants, name, v);
}

static void
insint_c(PyObject *d, char *name, long value)
{
    PyObject *v = PyInt_FromLong(value);
    insobj2(d, curlobject_constants, name, v);
}

static void
insint_m(PyObject *d, char *name, long value)
{
    PyObject *v = PyInt_FromLong(value);
    insobj2(d, curlmultiobject_constants, name, v);
}


/* Initialization function for the module */
#if defined(PyMODINIT_FUNC)
PyMODINIT_FUNC
#else
#if defined(__cplusplus)
extern "C"
#endif
DL_EXPORT(void)
#endif
initpycurl(void)
{
    PyObject *m, *d;
    const curl_version_info_data *vi;

    /* Initialize the type of the new type objects here; doing it here
     * is required for portability to Windows without requiring C++. */
    p_Curl_Type = &Curl_Type;
    p_CurlMulti_Type = &CurlMulti_Type;
    p_CurlShare_Type = &CurlShare_Type;
    Py_TYPE(&Curl_Type) = &PyType_Type;
    Py_TYPE(&CurlMulti_Type) = &PyType_Type;
    Py_TYPE(&CurlShare_Type) = &PyType_Type;

    /* Create the module and add the functions */
    m = Py_InitModule3("pycurl", curl_methods, module_doc);
    assert(m != NULL && PyModule_Check(m));

    /* Add error object to the module */
    d = PyModule_GetDict(m);
    assert(d != NULL);
    ErrorObject = PyErr_NewException("pycurl.error", NULL, NULL);
    assert(ErrorObject != NULL);
    PyDict_SetItemString(d, "error", ErrorObject);

    curlobject_constants = PyDict_New();
    assert(curlobject_constants != NULL);

    /* Add version strings to the module */
    insobj2(d, NULL, "version",
            PyString_FromFormat("PycURL/" PYCURL_VERSION " %s", curl_version()));
    insstr(d, "COMPILE_DATE", __DATE__ " " __TIME__);
    insint(d, "COMPILE_PY_VERSION_HEX", PY_VERSION_HEX);
    insint(d, "COMPILE_LIBCURL_VERSION_NUM", LIBCURL_VERSION_NUM);

    /**
     ** the order of these constants mostly follows <curl/curl.h>
     **/

    /* Abort curl_read_callback(). */
    insint_c(d, "READFUNC_ABORT", CURL_READFUNC_ABORT);
#if LIBCURL_VERSION_NUM >= 0x071200  /* CURL_READFUNC_PAUSE appeared in libcurl 7.18.0 */
    insint_c(d, "READFUNC_PAUSE", CURL_READFUNC_PAUSE);
#endif

    /* Pause curl_write_callback(). */
    insint_c(d, "WRITEFUNC_PAUSE", CURL_WRITEFUNC_PAUSE);

    /* constants for ioctl callback return values */
    insint_c(d, "IOE_OK", CURLIOE_OK);
    insint_c(d, "IOE_UNKNOWNCMD", CURLIOE_UNKNOWNCMD);
    insint_c(d, "IOE_FAILRESTART", CURLIOE_FAILRESTART);

    /* constants for ioctl callback argument values */
    insint_c(d, "IOCMD_NOP", CURLIOCMD_NOP);
    insint_c(d, "IOCMD_RESTARTREAD", CURLIOCMD_RESTARTREAD);

    /* curl_infotype: the kind of data that is passed to information_callback */
/* XXX do we actually need curl_infotype in pycurl ??? */
    insint_c(d, "INFOTYPE_TEXT", CURLINFO_TEXT);
    insint_c(d, "INFOTYPE_HEADER_IN", CURLINFO_HEADER_IN);
    insint_c(d, "INFOTYPE_HEADER_OUT", CURLINFO_HEADER_OUT);
    insint_c(d, "INFOTYPE_DATA_IN", CURLINFO_DATA_IN);
    insint_c(d, "INFOTYPE_DATA_OUT", CURLINFO_DATA_OUT);
    insint_c(d, "INFOTYPE_SSL_DATA_IN", CURLINFO_SSL_DATA_IN);
    insint_c(d, "INFOTYPE_SSL_DATA_OUT", CURLINFO_SSL_DATA_OUT);

    /* CURLcode: error codes */
    insint_c(d, "E_OK", CURLE_OK);
    insint_c(d, "E_UNSUPPORTED_PROTOCOL", CURLE_UNSUPPORTED_PROTOCOL);
    insint_c(d, "E_FAILED_INIT", CURLE_FAILED_INIT);
    insint_c(d, "E_URL_MALFORMAT", CURLE_URL_MALFORMAT);
    insint_c(d, "E_COULDNT_RESOLVE_PROXY", CURLE_COULDNT_RESOLVE_PROXY);
    insint_c(d, "E_COULDNT_RESOLVE_HOST", CURLE_COULDNT_RESOLVE_HOST);
    insint_c(d, "E_COULDNT_CONNECT", CURLE_COULDNT_CONNECT);
    insint_c(d, "E_FTP_WEIRD_SERVER_REPLY", CURLE_FTP_WEIRD_SERVER_REPLY);
    insint_c(d, "E_FTP_ACCESS_DENIED", CURLE_FTP_ACCESS_DENIED);
    insint_c(d, "E_FTP_WEIRD_PASS_REPLY", CURLE_FTP_WEIRD_PASS_REPLY);
    insint_c(d, "E_FTP_WEIRD_USER_REPLY", CURLE_FTP_WEIRD_USER_REPLY);
    insint_c(d, "E_FTP_WEIRD_PASV_REPLY", CURLE_FTP_WEIRD_PASV_REPLY);
    insint_c(d, "E_FTP_WEIRD_227_FORMAT", CURLE_FTP_WEIRD_227_FORMAT);
    insint_c(d, "E_FTP_CANT_GET_HOST", CURLE_FTP_CANT_GET_HOST);
    insint_c(d, "E_FTP_CANT_RECONNECT", CURLE_FTP_CANT_RECONNECT);
    insint_c(d, "E_FTP_COULDNT_SET_BINARY", CURLE_FTP_COULDNT_SET_BINARY);
    insint_c(d, "E_PARTIAL_FILE", CURLE_PARTIAL_FILE);
    insint_c(d, "E_FTP_COULDNT_RETR_FILE", CURLE_FTP_COULDNT_RETR_FILE);
    insint_c(d, "E_FTP_WRITE_ERROR", CURLE_FTP_WRITE_ERROR);
    insint_c(d, "E_FTP_QUOTE_ERROR", CURLE_FTP_QUOTE_ERROR);
    insint_c(d, "E_HTTP_RETURNED_ERROR", CURLE_HTTP_RETURNED_ERROR);
    insint_c(d, "E_WRITE_ERROR", CURLE_WRITE_ERROR);
    insint_c(d, "E_FTP_COULDNT_STOR_FILE", CURLE_FTP_COULDNT_STOR_FILE);
    insint_c(d, "E_READ_ERROR", CURLE_READ_ERROR);
    insint_c(d, "E_OUT_OF_MEMORY", CURLE_OUT_OF_MEMORY);
    insint_c(d, "E_OPERATION_TIMEOUTED", CURLE_OPERATION_TIMEOUTED);
    insint_c(d, "E_FTP_COULDNT_SET_ASCII", CURLE_FTP_COULDNT_SET_ASCII);
    insint_c(d, "E_FTP_PORT_FAILED", CURLE_FTP_PORT_FAILED);
    insint_c(d, "E_FTP_COULDNT_USE_REST", CURLE_FTP_COULDNT_USE_REST);
    insint_c(d, "E_FTP_COULDNT_GET_SIZE", CURLE_FTP_COULDNT_GET_SIZE);
    insint_c(d, "E_HTTP_RANGE_ERROR", CURLE_HTTP_RANGE_ERROR);
    insint_c(d, "E_HTTP_POST_ERROR", CURLE_HTTP_POST_ERROR);
    insint_c(d, "E_SSL_CONNECT_ERROR", CURLE_SSL_CONNECT_ERROR);
    insint_c(d, "E_BAD_DOWNLOAD_RESUME", CURLE_BAD_DOWNLOAD_RESUME);
    insint_c(d, "E_FILE_COULDNT_READ_FILE", CURLE_FILE_COULDNT_READ_FILE);
    insint_c(d, "E_LDAP_CANNOT_BIND", CURLE_LDAP_CANNOT_BIND);
    insint_c(d, "E_LDAP_SEARCH_FAILED", CURLE_LDAP_SEARCH_FAILED);
    insint_c(d, "E_LIBRARY_NOT_FOUND", CURLE_LIBRARY_NOT_FOUND);
    insint_c(d, "E_FUNCTION_NOT_FOUND", CURLE_FUNCTION_NOT_FOUND);
    insint_c(d, "E_ABORTED_BY_CALLBACK", CURLE_ABORTED_BY_CALLBACK);
    insint_c(d, "E_BAD_FUNCTION_ARGUMENT", CURLE_BAD_FUNCTION_ARGUMENT);
    insint_c(d, "E_INTERFACE_FAILED", CURLE_INTERFACE_FAILED);
    insint_c(d, "E_TOO_MANY_REDIRECTS", CURLE_TOO_MANY_REDIRECTS);
    insint_c(d, "E_UNKNOWN_TELNET_OPTION", CURLE_UNKNOWN_TELNET_OPTION);
    insint_c(d, "E_TELNET_OPTION_SYNTAX", CURLE_TELNET_OPTION_SYNTAX);
    insint_c(d, "E_SSL_PEER_CERTIFICATE", CURLE_SSL_PEER_CERTIFICATE);
    insint_c(d, "E_GOT_NOTHING", CURLE_GOT_NOTHING);
    insint_c(d, "E_SSL_ENGINE_NOTFOUND", CURLE_SSL_ENGINE_NOTFOUND);
    insint_c(d, "E_SSL_ENGINE_SETFAILED", CURLE_SSL_ENGINE_SETFAILED);
    insint_c(d, "E_SEND_ERROR", CURLE_SEND_ERROR);
    insint_c(d, "E_RECV_ERROR", CURLE_RECV_ERROR);
    insint_c(d, "E_SHARE_IN_USE", CURLE_SHARE_IN_USE);
    insint_c(d, "E_SSL_CERTPROBLEM", CURLE_SSL_CERTPROBLEM);
    insint_c(d, "E_SSL_CIPHER", CURLE_SSL_CIPHER);
    insint_c(d, "E_SSL_CACERT", CURLE_SSL_CACERT);
    insint_c(d, "E_BAD_CONTENT_ENCODING", CURLE_BAD_CONTENT_ENCODING);
    insint_c(d, "E_LDAP_INVALID_URL", CURLE_LDAP_INVALID_URL);
    insint_c(d, "E_FILESIZE_EXCEEDED", CURLE_FILESIZE_EXCEEDED);
    insint_c(d, "E_FTP_SSL_FAILED", CURLE_FTP_SSL_FAILED);
    insint_c(d, "E_SEND_FAIL_REWIND", CURLE_SEND_FAIL_REWIND);
    insint_c(d, "E_SSL_ENGINE_INITFAILED", CURLE_SSL_ENGINE_INITFAILED);
    insint_c(d, "E_LOGIN_DENIED", CURLE_LOGIN_DENIED);
    insint_c(d, "E_TFTP_NOTFOUND", CURLE_TFTP_NOTFOUND);
    insint_c(d, "E_TFTP_PERM", CURLE_TFTP_PERM);
    insint_c(d, "E_TFTP_DISKFULL",CURLE_TFTP_DISKFULL );
    insint_c(d, "E_TFTP_ILLEGAL",CURLE_TFTP_ILLEGAL );
    insint_c(d, "E_TFTP_UNKNOWNID",CURLE_TFTP_UNKNOWNID );
    insint_c(d, "E_TFTP_EXISTS", CURLE_TFTP_EXISTS);
    insint_c(d, "E_TFTP_NOSUCHUSER",CURLE_TFTP_NOSUCHUSER );
    insint_c(d, "E_CONV_FAILED",CURLE_CONV_FAILED );
    insint_c(d, "E_CONV_REQD",CURLE_CONV_REQD );
    insint_c(d, "E_SSL_CACERT_BADFILE", CURLE_SSL_CACERT_BADFILE);
    insint_c(d, "E_REMOTE_FILE_NOT_FOUND",CURLE_REMOTE_FILE_NOT_FOUND );
    insint_c(d, "E_SSH",CURLE_SSH );
    insint_c(d, "E_SSL_SHUTDOWN_FAILED",CURLE_SSL_SHUTDOWN_FAILED );

    /* curl_proxytype: constants for setopt(PROXYTYPE, x) */
    insint_c(d, "PROXYTYPE_HTTP", CURLPROXY_HTTP);
    insint_c(d, "PROXYTYPE_SOCKS4", CURLPROXY_SOCKS4);
    insint_c(d, "PROXYTYPE_SOCKS5", CURLPROXY_SOCKS5);

    /* curl_httpauth: constants for setopt(HTTPAUTH, x) */
    insint_c(d, "HTTPAUTH_NONE", CURLAUTH_NONE);
    insint_c(d, "HTTPAUTH_BASIC", CURLAUTH_BASIC);
    insint_c(d, "HTTPAUTH_DIGEST", CURLAUTH_DIGEST);
    insint_c(d, "HTTPAUTH_GSSNEGOTIATE", CURLAUTH_GSSNEGOTIATE);
    insint_c(d, "HTTPAUTH_NTLM", CURLAUTH_NTLM);
    insint_c(d, "HTTPAUTH_ANY", CURLAUTH_ANY);
    insint_c(d, "HTTPAUTH_ANYSAFE", CURLAUTH_ANYSAFE);

    /* curl_ftpssl: constants for setopt(FTP_SSL, x) */
    insint_c(d, "FTPSSL_NONE", CURLFTPSSL_NONE);
    insint_c(d, "FTPSSL_TRY", CURLFTPSSL_TRY);
    insint_c(d, "FTPSSL_CONTROL", CURLFTPSSL_CONTROL);
    insint_c(d, "FTPSSL_ALL", CURLFTPSSL_ALL);

    /* curl_ftpauth: constants for setopt(FTPSSLAUTH, x) */
    insint_c(d, "FTPAUTH_DEFAULT", CURLFTPAUTH_DEFAULT);
    insint_c(d, "FTPAUTH_SSL", CURLFTPAUTH_SSL);
    insint_c(d, "FTPAUTH_TLS", CURLFTPAUTH_TLS);

    /* curl_ftpauth: constants for setopt(FTPSSLAUTH, x) */
    insint_c(d, "FORM_BUFFER", CURLFORM_BUFFER);
    insint_c(d, "FORM_BUFFERPTR", CURLFORM_BUFFERPTR);
    insint_c(d, "FORM_CONTENTS", CURLFORM_COPYCONTENTS);
    insint_c(d, "FORM_FILE", CURLFORM_FILE);
    insint_c(d, "FORM_CONTENTTYPE", CURLFORM_CONTENTTYPE);
    insint_c(d, "FORM_FILENAME", CURLFORM_FILENAME);

    /* FTP_FILEMETHOD options */
    insint_c(d, "FTPMETHOD_DEFAULT", CURLFTPMETHOD_DEFAULT);
    insint_c(d, "FTPMETHOD_MULTICWD", CURLFTPMETHOD_MULTICWD);
    insint_c(d, "FTPMETHOD_NOCWD", CURLFTPMETHOD_NOCWD);
    insint_c(d, "FTPMETHOD_SINGLECWD", CURLFTPMETHOD_SINGLECWD);

    /* CURLoption: symbolic constants for setopt() */
    /* FIXME: reorder these to match <curl/curl.h> */
    insint_c(d, "FILE", CURLOPT_WRITEDATA);
    insint_c(d, "URL", CURLOPT_URL);
    insint_c(d, "PORT", CURLOPT_PORT);
    insint_c(d, "PROXY", CURLOPT_PROXY);
    insint_c(d, "USERPWD", CURLOPT_USERPWD);
#ifdef HAVE_CURLOPT_USERNAME
    insint_c(d, "USERNAME", CURLOPT_USERNAME);
    insint_c(d, "PASSWORD", CURLOPT_PASSWORD);
#endif
    insint_c(d, "PROXYUSERPWD", CURLOPT_PROXYUSERPWD);
#ifdef HAVE_CURLOPT_PROXYUSERNAME
    insint_c(d, "PROXYUSERNAME", CURLOPT_PROXYUSERNAME);
    insint_c(d, "PROXYPASSWORD", CURLOPT_PROXYPASSWORD);
#endif
    insint_c(d, "RANGE", CURLOPT_RANGE);
    insint_c(d, "INFILE", CURLOPT_READDATA);
    /* ERRORBUFFER is not supported */
    insint_c(d, "WRITEFUNCTION", CURLOPT_WRITEFUNCTION);
    insint_c(d, "READFUNCTION", CURLOPT_READFUNCTION);
    insint_c(d, "TIMEOUT", CURLOPT_TIMEOUT);
    insint_c(d, "INFILESIZE", CURLOPT_INFILESIZE_LARGE);    /* _LARGE ! */
    insint_c(d, "POSTFIELDS", CURLOPT_POSTFIELDS);
    insint_c(d, "REFERER", CURLOPT_REFERER);
    insint_c(d, "FTPPORT", CURLOPT_FTPPORT);
    insint_c(d, "USERAGENT", CURLOPT_USERAGENT);
    insint_c(d, "LOW_SPEED_LIMIT", CURLOPT_LOW_SPEED_LIMIT);
    insint_c(d, "LOW_SPEED_TIME", CURLOPT_LOW_SPEED_TIME);
    insint_c(d, "RESUME_FROM", CURLOPT_RESUME_FROM_LARGE);  /* _LARGE ! */
    insint_c(d, "WRITEDATA", CURLOPT_WRITEDATA);
    insint_c(d, "READDATA", CURLOPT_READDATA);
    insint_c(d, "PROXYPORT", CURLOPT_PROXYPORT);
    insint_c(d, "HTTPPROXYTUNNEL", CURLOPT_HTTPPROXYTUNNEL);
    insint_c(d, "VERBOSE", CURLOPT_VERBOSE);
    insint_c(d, "HEADER", CURLOPT_HEADER);
    insint_c(d, "NOPROGRESS", CURLOPT_NOPROGRESS);
    insint_c(d, "NOBODY", CURLOPT_NOBODY);
    insint_c(d, "FAILONERROR", CURLOPT_FAILONERROR);
    insint_c(d, "UPLOAD", CURLOPT_UPLOAD);
    insint_c(d, "POST", CURLOPT_POST);
    insint_c(d, "FTPLISTONLY", CURLOPT_FTPLISTONLY);
    insint_c(d, "FTPAPPEND", CURLOPT_FTPAPPEND);
    insint_c(d, "NETRC", CURLOPT_NETRC);
    insint_c(d, "FOLLOWLOCATION", CURLOPT_FOLLOWLOCATION);
    insint_c(d, "TRANSFERTEXT", CURLOPT_TRANSFERTEXT);
    insint_c(d, "PUT", CURLOPT_PUT);
    insint_c(d, "POSTFIELDSIZE", CURLOPT_POSTFIELDSIZE_LARGE);  /* _LARGE ! */
    insint_c(d, "COOKIE", CURLOPT_COOKIE);
    insint_c(d, "HTTPHEADER", CURLOPT_HTTPHEADER);
    insint_c(d, "HTTPPOST", CURLOPT_HTTPPOST);
    insint_c(d, "SSLCERT", CURLOPT_SSLCERT);
    insint_c(d, "SSLCERTPASSWD", CURLOPT_SSLCERTPASSWD);
    insint_c(d, "CRLF", CURLOPT_CRLF);
    insint_c(d, "QUOTE", CURLOPT_QUOTE);
    insint_c(d, "POSTQUOTE", CURLOPT_POSTQUOTE);
    insint_c(d, "PREQUOTE", CURLOPT_PREQUOTE);
    insint_c(d, "WRITEHEADER", CURLOPT_WRITEHEADER);
    insint_c(d, "HEADERFUNCTION", CURLOPT_HEADERFUNCTION);
    insint_c(d, "SEEKFUNCTION", CURLOPT_SEEKFUNCTION);
    insint_c(d, "COOKIEFILE", CURLOPT_COOKIEFILE);
    insint_c(d, "SSLVERSION", CURLOPT_SSLVERSION);
    insint_c(d, "TIMECONDITION", CURLOPT_TIMECONDITION);
    insint_c(d, "TIMEVALUE", CURLOPT_TIMEVALUE);
    insint_c(d, "CUSTOMREQUEST", CURLOPT_CUSTOMREQUEST);
    insint_c(d, "STDERR", CURLOPT_STDERR);
    insint_c(d, "INTERFACE", CURLOPT_INTERFACE);
    insint_c(d, "KRB4LEVEL", CURLOPT_KRB4LEVEL);
    insint_c(d, "PROGRESSFUNCTION", CURLOPT_PROGRESSFUNCTION);
    insint_c(d, "SSL_VERIFYPEER", CURLOPT_SSL_VERIFYPEER);
    insint_c(d, "CAPATH", CURLOPT_CAPATH);
    insint_c(d, "CAINFO", CURLOPT_CAINFO);
    insint_c(d, "OPT_FILETIME", CURLOPT_FILETIME);
    insint_c(d, "MAXREDIRS", CURLOPT_MAXREDIRS);
    insint_c(d, "MAXCONNECTS", CURLOPT_MAXCONNECTS);
    insint_c(d, "FRESH_CONNECT", CURLOPT_FRESH_CONNECT);
    insint_c(d, "FORBID_REUSE", CURLOPT_FORBID_REUSE);
    insint_c(d, "RANDOM_FILE", CURLOPT_RANDOM_FILE);
    insint_c(d, "EGDSOCKET", CURLOPT_EGDSOCKET);
    insint_c(d, "CONNECTTIMEOUT", CURLOPT_CONNECTTIMEOUT);
    insint_c(d, "HTTPGET", CURLOPT_HTTPGET);
    insint_c(d, "SSL_VERIFYHOST", CURLOPT_SSL_VERIFYHOST);
    insint_c(d, "COOKIEJAR", CURLOPT_COOKIEJAR);
    insint_c(d, "SSL_CIPHER_LIST", CURLOPT_SSL_CIPHER_LIST);
    insint_c(d, "HTTP_VERSION", CURLOPT_HTTP_VERSION);
    insint_c(d, "FTP_USE_EPSV", CURLOPT_FTP_USE_EPSV);
    insint_c(d, "SSLCERTTYPE", CURLOPT_SSLCERTTYPE);
    insint_c(d, "SSLKEY", CURLOPT_SSLKEY);
    insint_c(d, "SSLKEYTYPE", CURLOPT_SSLKEYTYPE);
    insint_c(d, "SSLKEYPASSWD", CURLOPT_SSLKEYPASSWD);
    insint_c(d, "SSLENGINE", CURLOPT_SSLENGINE);
    insint_c(d, "SSLENGINE_DEFAULT", CURLOPT_SSLENGINE_DEFAULT);
    insint_c(d, "DNS_CACHE_TIMEOUT", CURLOPT_DNS_CACHE_TIMEOUT);
    insint_c(d, "DNS_USE_GLOBAL_CACHE", CURLOPT_DNS_USE_GLOBAL_CACHE);
    insint_c(d, "DEBUGFUNCTION", CURLOPT_DEBUGFUNCTION);
    insint_c(d, "BUFFERSIZE", CURLOPT_BUFFERSIZE);
    insint_c(d, "NOSIGNAL", CURLOPT_NOSIGNAL);
    insint_c(d, "SHARE", CURLOPT_SHARE);
    insint_c(d, "PROXYTYPE", CURLOPT_PROXYTYPE);
    insint_c(d, "ENCODING", CURLOPT_ENCODING);
    insint_c(d, "HTTP200ALIASES", CURLOPT_HTTP200ALIASES);
    insint_c(d, "UNRESTRICTED_AUTH", CURLOPT_UNRESTRICTED_AUTH);
    insint_c(d, "FTP_USE_EPRT", CURLOPT_FTP_USE_EPRT);
    insint_c(d, "HTTPAUTH", CURLOPT_HTTPAUTH);
    insint_c(d, "FTP_CREATE_MISSING_DIRS", CURLOPT_FTP_CREATE_MISSING_DIRS);
    insint_c(d, "PROXYAUTH", CURLOPT_PROXYAUTH);
    insint_c(d, "FTP_RESPONSE_TIMEOUT", CURLOPT_FTP_RESPONSE_TIMEOUT);
    insint_c(d, "IPRESOLVE", CURLOPT_IPRESOLVE);
    insint_c(d, "MAXFILESIZE", CURLOPT_MAXFILESIZE_LARGE);  /* _LARGE ! */
    insint_c(d, "INFILESIZE_LARGE", CURLOPT_INFILESIZE_LARGE);
    insint_c(d, "RESUME_FROM_LARGE", CURLOPT_RESUME_FROM_LARGE);
    insint_c(d, "MAXFILESIZE_LARGE", CURLOPT_MAXFILESIZE_LARGE);
    insint_c(d, "NETRC_FILE", CURLOPT_NETRC_FILE);
    insint_c(d, "FTP_SSL", CURLOPT_FTP_SSL);
    insint_c(d, "POSTFIELDSIZE_LARGE", CURLOPT_POSTFIELDSIZE_LARGE);
    insint_c(d, "TCP_NODELAY", CURLOPT_TCP_NODELAY);
    insint_c(d, "FTPSSLAUTH", CURLOPT_FTPSSLAUTH);
    insint_c(d, "IOCTLFUNCTION", CURLOPT_IOCTLFUNCTION);
    insint_c(d, "IOCTLDATA", CURLOPT_IOCTLDATA);
    insint_c(d, "OPENSOCKETFUNCTION", CURLOPT_OPENSOCKETFUNCTION);
    insint_c(d, "FTP_ACCOUNT", CURLOPT_FTP_ACCOUNT);
    insint_c(d, "IGNORE_CONTENT_LENGTH", CURLOPT_IGNORE_CONTENT_LENGTH);
    insint_c(d, "COOKIELIST", CURLOPT_COOKIELIST);
    insint_c(d, "FTP_SKIP_PASV_IP", CURLOPT_FTP_SKIP_PASV_IP);
    insint_c(d, "FTP_FILEMETHOD", CURLOPT_FTP_FILEMETHOD);
    insint_c(d, "CONNECT_ONLY", CURLOPT_CONNECT_ONLY);
    insint_c(d, "LOCALPORT", CURLOPT_LOCALPORT);
    insint_c(d, "LOCALPORTRANGE", CURLOPT_LOCALPORTRANGE);
    insint_c(d, "FTP_ALTERNATIVE_TO_USER", CURLOPT_FTP_ALTERNATIVE_TO_USER);
    insint_c(d, "MAX_SEND_SPEED_LARGE", CURLOPT_MAX_SEND_SPEED_LARGE);
    insint_c(d, "MAX_RECV_SPEED_LARGE", CURLOPT_MAX_RECV_SPEED_LARGE);
    insint_c(d, "SSL_SESSIONID_CACHE", CURLOPT_SSL_SESSIONID_CACHE);
    insint_c(d, "SSH_AUTH_TYPES", CURLOPT_SSH_AUTH_TYPES);
    insint_c(d, "SSH_PUBLIC_KEYFILE", CURLOPT_SSH_PUBLIC_KEYFILE);
    insint_c(d, "SSH_PRIVATE_KEYFILE", CURLOPT_SSH_PRIVATE_KEYFILE);
    insint_c(d, "FTP_SSL_CCC", CURLOPT_FTP_SSL_CCC);
    insint_c(d, "TIMEOUT_MS", CURLOPT_TIMEOUT_MS);
    insint_c(d, "CONNECTTIMEOUT_MS", CURLOPT_CONNECTTIMEOUT_MS);
    insint_c(d, "HTTP_TRANSFER_DECODING", CURLOPT_HTTP_TRANSFER_DECODING);
    insint_c(d, "HTTP_CONTENT_DECODING", CURLOPT_HTTP_CONTENT_DECODING);
    insint_c(d, "NEW_FILE_PERMS", CURLOPT_NEW_FILE_PERMS);
    insint_c(d, "NEW_DIRECTORY_PERMS", CURLOPT_NEW_DIRECTORY_PERMS);
    insint_c(d, "POST301", CURLOPT_POST301);
    insint_c(d, "PROXY_TRANSFER_MODE", CURLOPT_PROXY_TRANSFER_MODE);
    insint_c(d, "COPYPOSTFIELDS", CURLOPT_COPYPOSTFIELDS);
    insint_c(d, "SSH_HOST_PUBLIC_KEY_MD5", CURLOPT_SSH_HOST_PUBLIC_KEY_MD5);
    insint_c(d, "AUTOREFERER", CURLOPT_AUTOREFERER);
    insint_c(d, "CRLFILE", CURLOPT_CRLFILE);
    insint_c(d, "ISSUERCERT", CURLOPT_ISSUERCERT);
    insint_c(d, "ADDRESS_SCOPE", CURLOPT_ADDRESS_SCOPE);
#ifdef HAVE_CURLOPT_RESOLVE
    insint_c(d, "RESOLVE", CURLOPT_RESOLVE);
#endif
#ifdef HAVE_CURLOPT_CERTINFO
    insint_c(d, "OPT_CERTINFO", CURLOPT_CERTINFO);
#endif

    insint_c(d, "M_TIMERFUNCTION", CURLMOPT_TIMERFUNCTION);
    insint_c(d, "M_SOCKETFUNCTION", CURLMOPT_SOCKETFUNCTION);
    insint_c(d, "M_PIPELINING", CURLMOPT_PIPELINING);
    insint_c(d, "M_MAXCONNECTS", CURLMOPT_MAXCONNECTS);

    /* constants for setopt(IPRESOLVE, x) */
    insint_c(d, "IPRESOLVE_WHATEVER", CURL_IPRESOLVE_WHATEVER);
    insint_c(d, "IPRESOLVE_V4", CURL_IPRESOLVE_V4);
    insint_c(d, "IPRESOLVE_V6", CURL_IPRESOLVE_V6);

    /* constants for setopt(HTTP_VERSION, x) */
    insint_c(d, "CURL_HTTP_VERSION_NONE", CURL_HTTP_VERSION_NONE);
    insint_c(d, "CURL_HTTP_VERSION_1_0", CURL_HTTP_VERSION_1_0);
    insint_c(d, "CURL_HTTP_VERSION_1_1", CURL_HTTP_VERSION_1_1);
    insint_c(d, "CURL_HTTP_VERSION_LAST", CURL_HTTP_VERSION_LAST);

    /* CURL_NETRC_OPTION: constants for setopt(NETRC, x) */
    insint_c(d, "NETRC_OPTIONAL", CURL_NETRC_OPTIONAL);
    insint_c(d, "NETRC_IGNORED", CURL_NETRC_IGNORED);
    insint_c(d, "NETRC_REQUIRED", CURL_NETRC_REQUIRED);

    /* constants for setopt(SSLVERSION, x) */
    insint_c(d, "SSLVERSION_DEFAULT", CURL_SSLVERSION_DEFAULT);
    insint_c(d, "SSLVERSION_TLSv1", CURL_SSLVERSION_TLSv1);
    insint_c(d, "SSLVERSION_SSLv2", CURL_SSLVERSION_SSLv2);
    insint_c(d, "SSLVERSION_SSLv3", CURL_SSLVERSION_SSLv3);

    /* curl_TimeCond: constants for setopt(TIMECONDITION, x) */
    insint_c(d, "TIMECONDITION_NONE", CURL_TIMECOND_NONE);
    insint_c(d, "TIMECONDITION_IFMODSINCE", CURL_TIMECOND_IFMODSINCE);
    insint_c(d, "TIMECONDITION_IFUNMODSINCE", CURL_TIMECOND_IFUNMODSINCE);
    insint_c(d, "TIMECONDITION_LASTMOD", CURL_TIMECOND_LASTMOD);

    /* constants for setopt(CURLOPT_SSH_AUTH_TYPES, x) */
    insint_c(d, "SSH_AUTH_ANY", CURLSSH_AUTH_ANY);
    insint_c(d, "SSH_AUTH_NONE", CURLSSH_AUTH_NONE);
    insint_c(d, "SSH_AUTH_PUBLICKEY", CURLSSH_AUTH_PUBLICKEY);
    insint_c(d, "SSH_AUTH_PASSWORD", CURLSSH_AUTH_PASSWORD);
    insint_c(d, "SSH_AUTH_HOST", CURLSSH_AUTH_HOST);
    insint_c(d, "SSH_AUTH_KEYBOARD", CURLSSH_AUTH_KEYBOARD);
    insint_c(d, "SSH_AUTH_DEFAULT", CURLSSH_AUTH_DEFAULT);

    /* CURLINFO: symbolic constants for getinfo(x) */
    insint_c(d, "EFFECTIVE_URL", CURLINFO_EFFECTIVE_URL);
    insint_c(d, "HTTP_CODE", CURLINFO_HTTP_CODE);
    insint_c(d, "RESPONSE_CODE", CURLINFO_HTTP_CODE);
    insint_c(d, "TOTAL_TIME", CURLINFO_TOTAL_TIME);
    insint_c(d, "NAMELOOKUP_TIME", CURLINFO_NAMELOOKUP_TIME);
    insint_c(d, "CONNECT_TIME", CURLINFO_CONNECT_TIME);
    insint_c(d, "APPCONNECT_TIME", CURLINFO_APPCONNECT_TIME);
    insint_c(d, "PRETRANSFER_TIME", CURLINFO_PRETRANSFER_TIME);
    insint_c(d, "SIZE_UPLOAD", CURLINFO_SIZE_UPLOAD);
    insint_c(d, "SIZE_DOWNLOAD", CURLINFO_SIZE_DOWNLOAD);
    insint_c(d, "SPEED_DOWNLOAD", CURLINFO_SPEED_DOWNLOAD);
    insint_c(d, "SPEED_UPLOAD", CURLINFO_SPEED_UPLOAD);
    insint_c(d, "HEADER_SIZE", CURLINFO_HEADER_SIZE);
    insint_c(d, "REQUEST_SIZE", CURLINFO_REQUEST_SIZE);
    insint_c(d, "SSL_VERIFYRESULT", CURLINFO_SSL_VERIFYRESULT);
    insint_c(d, "INFO_FILETIME", CURLINFO_FILETIME);
    insint_c(d, "CONTENT_LENGTH_DOWNLOAD", CURLINFO_CONTENT_LENGTH_DOWNLOAD);
    insint_c(d, "CONTENT_LENGTH_UPLOAD", CURLINFO_CONTENT_LENGTH_UPLOAD);
    insint_c(d, "STARTTRANSFER_TIME", CURLINFO_STARTTRANSFER_TIME);
    insint_c(d, "CONTENT_TYPE", CURLINFO_CONTENT_TYPE);
    insint_c(d, "REDIRECT_TIME", CURLINFO_REDIRECT_TIME);
    insint_c(d, "REDIRECT_COUNT", CURLINFO_REDIRECT_COUNT);
    insint_c(d, "REDIRECT_URL", CURLINFO_REDIRECT_URL);
    insint_c(d, "PRIMARY_IP", CURLINFO_PRIMARY_IP);
    insint_c(d, "HTTP_CONNECTCODE", CURLINFO_HTTP_CONNECTCODE);
    insint_c(d, "HTTPAUTH_AVAIL", CURLINFO_HTTPAUTH_AVAIL);
    insint_c(d, "PROXYAUTH_AVAIL", CURLINFO_PROXYAUTH_AVAIL);
    insint_c(d, "OS_ERRNO", CURLINFO_OS_ERRNO);
    insint_c(d, "NUM_CONNECTS", CURLINFO_NUM_CONNECTS);
    insint_c(d, "SSL_ENGINES", CURLINFO_SSL_ENGINES);
    insint_c(d, "INFO_COOKIELIST", CURLINFO_COOKIELIST);
    insint_c(d, "LASTSOCKET", CURLINFO_LASTSOCKET);
    insint_c(d, "FTP_ENTRY_PATH", CURLINFO_FTP_ENTRY_PATH);
#ifdef HAVE_CURLOPT_CERTINFO
    insint_c(d, "INFO_CERTINFO", CURLINFO_CERTINFO);
#endif

#if LIBCURL_VERSION_NUM >= 0x071200  /* curl_easy_pause() appeared in libcurl 7.18.0 */
    /* CURLPAUSE: symbolic constants for pause(bitmask) */
    insint_c(d, "PAUSE_RECV", CURLPAUSE_RECV);
    insint_c(d, "PAUSE_SEND", CURLPAUSE_SEND);
    insint_c(d, "PAUSE_ALL",  CURLPAUSE_ALL);
    insint_c(d, "PAUSE_CONT", CURLPAUSE_CONT);
#endif

#if LIBCURL_VERSION_NUM >= 0x071800
    insint_c(d, "DNS_SERVERS", CURLOPT_DNS_SERVERS);
#endif

    /* options for global_init() */
    insint(d, "GLOBAL_SSL", CURL_GLOBAL_SSL);
    insint(d, "GLOBAL_WIN32", CURL_GLOBAL_WIN32);
    insint(d, "GLOBAL_ALL", CURL_GLOBAL_ALL);
    insint(d, "GLOBAL_NOTHING", CURL_GLOBAL_NOTHING);
    insint(d, "GLOBAL_DEFAULT", CURL_GLOBAL_DEFAULT);
#ifdef CURL_GLOBAL_ACK_EINTR
    /* CURL_GLOBAL_ACK_EINTR was introduced in libcurl-7.30.0 */
    insint(d, "GLOBAL_ACK_EINTR", CURL_GLOBAL_ACK_EINTR);
#endif


    /* constants for curl_multi_socket interface */
    insint(d, "CSELECT_IN", CURL_CSELECT_IN);
    insint(d, "CSELECT_OUT", CURL_CSELECT_OUT);
    insint(d, "CSELECT_ERR", CURL_CSELECT_ERR);
    insint(d, "SOCKET_TIMEOUT", CURL_SOCKET_TIMEOUT);
    insint(d, "POLL_NONE", CURL_POLL_NONE);
    insint(d, "POLL_IN", CURL_POLL_IN);
    insint(d, "POLL_OUT", CURL_POLL_OUT);
    insint(d, "POLL_INOUT", CURL_POLL_INOUT);
    insint(d, "POLL_REMOVE", CURL_POLL_REMOVE);

    /* curl_lock_data: XXX do we need this in pycurl ??? */
    /* curl_lock_access: XXX do we need this in pycurl ??? */
    /* CURLSHcode: XXX do we need this in pycurl ??? */
    /* CURLSHoption: XXX do we need this in pycurl ??? */

    /* CURLversion: constants for curl_version_info(x) */
#if 0
    /* XXX - do we need these ?? */
    insint(d, "VERSION_FIRST", CURLVERSION_FIRST);
    insint(d, "VERSION_SECOND", CURLVERSION_SECOND);
    insint(d, "VERSION_THIRD", CURLVERSION_THIRD);
    insint(d, "VERSION_NOW", CURLVERSION_NOW);
#endif

    /* version features - bitmasks for curl_version_info_data.features */
#if 0
    /* XXX - do we need these ?? */
    /* XXX - should we really rename these ?? */
    insint(d, "VERSION_FEATURE_IPV6", CURL_VERSION_IPV6);
    insint(d, "VERSION_FEATURE_KERBEROS4", CURL_VERSION_KERBEROS4);
    insint(d, "VERSION_FEATURE_SSL", CURL_VERSION_SSL);
    insint(d, "VERSION_FEATURE_LIBZ", CURL_VERSION_LIBZ);
    insint(d, "VERSION_FEATURE_NTLM", CURL_VERSION_NTLM);
    insint(d, "VERSION_FEATURE_GSSNEGOTIATE", CURL_VERSION_GSSNEGOTIATE);
    insint(d, "VERSION_FEATURE_DEBUG", CURL_VERSION_DEBUG);
    insint(d, "VERSION_FEATURE_ASYNCHDNS", CURL_VERSION_ASYNCHDNS);
    insint(d, "VERSION_FEATURE_SPNEGO", CURL_VERSION_SPNEGO);
    insint(d, "VERSION_FEATURE_LARGEFILE", CURL_VERSION_LARGEFILE);
    insint(d, "VERSION_FEATURE_IDN", CURL_VERSION_IDN);
#endif

    /**
     ** the order of these constants mostly follows <curl/multi.h>
     **/

    /* CURLMcode: multi error codes */
    insint_m(d, "E_CALL_MULTI_PERFORM", CURLM_CALL_MULTI_PERFORM);
    insint_m(d, "E_MULTI_OK", CURLM_OK);
    insint_m(d, "E_MULTI_BAD_HANDLE", CURLM_BAD_HANDLE);
    insint_m(d, "E_MULTI_BAD_EASY_HANDLE", CURLM_BAD_EASY_HANDLE);
    insint_m(d, "E_MULTI_OUT_OF_MEMORY", CURLM_OUT_OF_MEMORY);
    insint_m(d, "E_MULTI_INTERNAL_ERROR", CURLM_INTERNAL_ERROR);

    /* curl shared constants */
    curlshareobject_constants = PyDict_New();
    assert(curlshareobject_constants != NULL);
    insint_s(d, "SH_SHARE", CURLSHOPT_SHARE);
    insint_s(d, "SH_UNSHARE", CURLSHOPT_UNSHARE);
    insint_s(d, "LOCK_DATA_COOKIE", CURL_LOCK_DATA_COOKIE);
    insint_s(d, "LOCK_DATA_DNS", CURL_LOCK_DATA_DNS);

    /* Check the version, as this has caused nasty problems in
     * some cases. */
    vi = curl_version_info(CURLVERSION_NOW);
    if (vi == NULL) {
        Py_FatalError("pycurl: curl_version_info() failed");
        assert(0);
    }
    if (vi->version_num < LIBCURL_VERSION_NUM) {
        Py_FatalError("pycurl: libcurl link-time version is older than compile-time version");
        assert(0);
    }

    /* Initialize callback locks if ssl is enabled */
#if defined(PYCURL_NEED_SSL_TSL)
    pycurl_ssl_init();
#endif

#ifdef WITH_THREAD
    /* Finally initialize global interpreter lock */
    PyEval_InitThreads();
#endif

}

#if defined(WIN32) && ((_WIN32_WINNT <= 0x0600) || (NTDDI_VERSION < NTDDI_VISTA))
/*
 * Only Winsock on Vista+ has inet_ntop().
 */
static const char * pycurl_inet_ntop (int family, void *addr, char *string, size_t string_size)
{
  SOCKADDR *sa;
  int       sa_len;

  if (family == AF_INET6) {
    struct sockaddr_in6 sa6;
    memcpy (&sa6.sin6_addr, addr, sizeof(sa6.sin6_addr));
    sa = (SOCKADDR*)&sa6;
    sa_len = sizeof(sa6);
  }
  else {
    struct sockaddr_in sa4;
    memcpy (&sa4.sin_addr, addr, sizeof(sa4.sin_addr));
    sa = (SOCKADDR*)&sa4;
    sa_len = sizeof(sa4);
  }
  if (WSAAddressToString(sa, sa_len, NULL, string, &string_size))
     return (NULL);
  return (string);
}
#endif

/* vi:ts=4:et:nowrap
 */
