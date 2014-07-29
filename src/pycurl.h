#if (defined(_WIN32) || defined(__WIN32__)) && !defined(WIN32)
#  define WIN32 1
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

#if defined(PYCURL_SINGLE_FILE)
# define PYCURL_INTERNAL static
#else
# define PYCURL_INTERNAL
#endif

#if defined(WIN32)
/* supposedly not present in errno.h provided with VC */
# if !defined(EAFNOSUPPORT)
#  define EAFNOSUPPORT 97
# endif

PYCURL_INTERNAL SOCKET
dup_winsock(SOCKET sock, const struct curl_sockaddr *address);
#endif

/* The inet_ntop() was added in ws2_32.dll on Windows Vista [1]. Hence the
 * Windows SDK targeting lesser OS'es doesn't provide that prototype.
 * Maybe we should use the local hidden inet_ntop() for all OS'es thus
 * making a pycurl.pyd work across OS'es w/o rebuilding?
 *
 * [1] http://msdn.microsoft.com/en-us/library/windows/desktop/cc805843(v=vs.85).aspx
 */
#if defined(WIN32) && ((_WIN32_WINNT < 0x0600) || (NTDDI_VERSION < NTDDI_VISTA))
PYCURL_INTERNAL const char *
pycurl_inet_ntop (int family, void *addr, char *string, size_t string_size);
#define inet_ntop(fam,addr,string,size) pycurl_inet_ntop(fam,addr,string,size)
#endif

/* Ensure we have updated versions */
#if !defined(PY_VERSION_HEX) || (PY_VERSION_HEX < 0x02040000)
#  error "Need Python version 2.4 or greater to compile pycurl."
#endif
#if !defined(LIBCURL_VERSION_NUM) || (LIBCURL_VERSION_NUM < 0x071300)
#  error "Need libcurl version 7.19.0 or greater to compile pycurl."
#endif

#if LIBCURL_VERSION_NUM >= 0x071301 /* check for 7.19.1 or greater */
#define HAVE_CURLOPT_USERNAME
#define HAVE_CURLOPT_PROXYUSERNAME
#define HAVE_CURLOPT_CERTINFO
#define HAVE_CURLOPT_POSTREDIR
#endif

#if LIBCURL_VERSION_NUM >= 0x071303 /* check for 7.19.3 or greater */
#define HAVE_CURLAUTH_DIGEST_IE
#endif

#if LIBCURL_VERSION_NUM >= 0x071304 /* check for 7.19.4 or greater */
#define HAVE_CURLOPT_NOPROXY
#define HAVE_CURLOPT_PROTOCOLS
#define HAVE_CURL_7_19_4_OPTS
#endif

#if LIBCURL_VERSION_NUM >= 0x071304 /* check for 7.19.5 or greater */
#define HAVE_CURL_7_19_5_OPTS
#endif

#if LIBCURL_VERSION_NUM >= 0x071304 /* check for 7.19.6 or greater */
#define HAVE_CURL_7_19_6_OPTS
#endif

#if LIBCURL_VERSION_NUM >= 0x071400 /* check for 7.20.0 or greater */
#define HAVE_CURL_7_20_0_OPTS
#endif

#if LIBCURL_VERSION_NUM >= 0x071500 /* check for 7.21.0 or greater */
#define HAVE_CURLINFO_LOCAL_PORT
#define HAVE_CURLINFO_PRIMARY_PORT
#define HAVE_CURLINFO_LOCAL_IP
#define HAVE_CURL_7_21_0_OPTS
#endif

#if LIBCURL_VERSION_NUM >= 0x071502 /* check for 7.21.2 or greater */
#define HAVE_CURL_7_21_2_OPTS
#endif

#if LIBCURL_VERSION_NUM >= 0x071503 /* check for 7.21.3 or greater */
#define HAVE_CURLOPT_RESOLVE
#endif

#if LIBCURL_VERSION_NUM >= 0x071505 /* check for 7.21.5 or greater */
#define HAVE_CURL_7_21_5
#endif

#if LIBCURL_VERSION_NUM >= 0x071800 /* check for 7.24.0 or greater */
#define HAVE_CURLOPT_DNS_SERVERS
#define HAVE_CURL_7_24_0
#endif

#if LIBCURL_VERSION_NUM >= 0x071900 /* check for 7.25.0 or greater */
#define HAVE_CURL_7_25_0_OPTS
#endif

#if LIBCURL_VERSION_NUM >= 0x071A00 /* check for 7.26.0 or greater */
#define HAVE_CURL_REDIR_POST_303
#endif

#if LIBCURL_VERSION_NUM >= 0x071E00 /* check for 7.30.0 or greater */
#define HAVE_CURL_7_30_0_PIPELINE_OPTS
#endif

/* Python < 2.5 compat for Py_ssize_t */
#if PY_VERSION_HEX < 0x02050000
typedef int Py_ssize_t;
#endif

/* Py_TYPE is defined by Python 2.6+ */
#if PY_VERSION_HEX < 0x02060000 && !defined(Py_TYPE)
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
#   define COMPILE_SSL_LIB "openssl"
# elif defined(HAVE_CURL_GNUTLS)
#   include <gnutls/gnutls.h>
#   if GNUTLS_VERSION_NUMBER <= 0x020b00
#     define PYCURL_NEED_SSL_TSL
#     define PYCURL_NEED_GNUTLS_TSL
#     include <gcrypt.h>
#   endif
#   define COMPILE_SSL_LIB "gnutls"
# elif defined(HAVE_CURL_NSS)
#   define COMPILE_SSL_LIB "nss"
# else
#  ifdef _MSC_VER
    /* sigh */
#   pragma message(\
     "libcurl was compiled with SSL support, but configure could not determine which " \
     "library was used; thus no SSL crypto locking callbacks will be set, which may " \
     "cause random crashes on SSL requests")
#  else
#   warning \
     "libcurl was compiled with SSL support, but configure could not determine which " \
     "library was used; thus no SSL crypto locking callbacks will be set, which may " \
     "cause random crashes on SSL requests"
#  endif
   /* since we have no crypto callbacks for other ssl backends,
    * no reason to require users match those */
#  define COMPILE_SSL_LIB "none/other"
# endif /* HAVE_CURL_OPENSSL || HAVE_CURL_GNUTLS || HAVE_CURL_NSS */
#else
# define COMPILE_SSL_LIB "none/other"
#endif /* HAVE_CURL_SSL */

#if defined(PYCURL_NEED_SSL_TSL)
PYCURL_INTERNAL void pycurl_ssl_init(void);
PYCURL_INTERNAL void pycurl_ssl_cleanup(void);
#endif

#ifdef WITH_THREAD
#  define PYCURL_DECLARE_THREAD_STATE PyThreadState *tmp_state
#  define PYCURL_ACQUIRE_THREAD() pycurl_acquire_thread(self, &tmp_state)
#  define PYCURL_ACQUIRE_THREAD_MULTI() pycurl_acquire_thread_multi(self, &tmp_state)
#  define PYCURL_RELEASE_THREAD() pycurl_release_thread(tmp_state)
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

#if PY_MAJOR_VERSION >= 3
  #define PyInt_Type                   PyLong_Type
  #define PyInt_Check(op)              PyLong_Check(op)
  #define PyInt_FromLong               PyLong_FromLong
  #define PyInt_AsLong                 PyLong_AsLong
#endif

/*************************************************************************
// python 2/3 compatibility
**************************************************************************/

#if PY_MAJOR_VERSION >= 3
# define PyText_FromFormat(format, str) PyUnicode_FromFormat((format), (str))
# define PyText_FromString(str) PyUnicode_FromString(str)
# define PyByteStr_Check(obj) PyBytes_Check(obj)
# define PyByteStr_AsStringAndSize(obj, buffer, length) PyBytes_AsStringAndSize((obj), (buffer), (length))
#else
# define PyText_FromFormat(format, str) PyString_FromFormat((format), (str))
# define PyText_FromString(str) PyString_FromString(str)
# define PyByteStr_Check(obj) PyString_Check(obj)
# define PyByteStr_AsStringAndSize(obj, buffer, length) PyString_AsStringAndSize((obj), (buffer), (length))
#endif
#define PyText_EncodedDecref(encoded) Py_XDECREF(encoded)

PYCURL_INTERNAL int
PyText_AsStringAndSize(PyObject *obj, char **buffer, Py_ssize_t *length, PyObject **encoded_obj);
PYCURL_INTERNAL char *
PyText_AsString_NoNUL(PyObject *obj, PyObject **encoded_obj);
PYCURL_INTERNAL int
PyText_Check(PyObject *o);


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

typedef struct CurlObject {
    PyObject_HEAD
    PyObject *dict;                 /* Python attributes dictionary */
    CURL *handle;
#ifdef WITH_THREAD
    PyThreadState *state;
#endif
    struct CurlMultiObject *multi_stack;
    struct CurlShareObject *share;
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
#ifdef HAVE_CURL_7_20_0_OPTS
    struct curl_slist *mail_rcpt;
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

typedef struct CurlMultiObject {
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
    PyThread_type_lock locks[CURL_LOCK_DATA_LAST];
} ShareLock;

typedef struct CurlShareObject {
    PyObject_HEAD
    PyObject *dict;                 /* Python attributes dictionary */
    CURLSH *share_handle;
#ifdef WITH_THREAD
    ShareLock *lock;                /* lock object to implement CURLSHOPT_LOCKFUNC */
#endif
} CurlShareObject;

#ifdef WITH_THREAD

PYCURL_INTERNAL PyThreadState *
pycurl_get_thread_state(const CurlObject *self);
PYCURL_INTERNAL PyThreadState *
pycurl_get_thread_state_multi(const CurlMultiObject *self);
PYCURL_INTERNAL int
pycurl_acquire_thread(const CurlObject *self, PyThreadState **state);
PYCURL_INTERNAL int
pycurl_acquire_thread_multi(const CurlMultiObject *self, PyThreadState **state);
PYCURL_INTERNAL void
pycurl_release_thread(PyThreadState *state);

PYCURL_INTERNAL void
share_lock_lock(ShareLock *lock, curl_lock_data data);
PYCURL_INTERNAL void
share_lock_unlock(ShareLock *lock, curl_lock_data data);
PYCURL_INTERNAL ShareLock *
share_lock_new(void);
PYCURL_INTERNAL void
share_lock_destroy(ShareLock *lock);
PYCURL_INTERNAL void
share_lock_callback(CURL *handle, curl_lock_data data, curl_lock_access locktype, void *userptr);
PYCURL_INTERNAL void
share_unlock_callback(CURL *handle, curl_lock_data data, void *userptr);

#endif /* WITH_THREAD */

#if defined(PYCURL_NEED_SSL_TSL)
PYCURL_INTERNAL void
pycurl_ssl_init(void);
PYCURL_INTERNAL void
pycurl_ssl_cleanup(void);
#endif

#if PY_MAJOR_VERSION >= 3
PYCURL_INTERNAL PyObject *
my_getattro(PyObject *co, PyObject *name, PyObject *dict1, PyObject *dict2, PyMethodDef *m);
PYCURL_INTERNAL int
my_setattro(PyObject **dict, PyObject *name, PyObject *v);
#else /* PY_MAJOR_VERSION >= 3 */
PYCURL_INTERNAL int
my_setattr(PyObject **dict, char *name, PyObject *v);
PYCURL_INTERNAL PyObject *
my_getattr(PyObject *co, char *name, PyObject *dict1, PyObject *dict2, PyMethodDef *m);
#endif /* PY_MAJOR_VERSION >= 3 */

/* used by multi object */
PYCURL_INTERNAL void
assert_curl_state(const CurlObject *self);

PYCURL_INTERNAL PyObject *
do_global_init(PyObject *dummy, PyObject *args);
PYCURL_INTERNAL PyObject *
do_global_cleanup(PyObject *dummy);
PYCURL_INTERNAL PyObject *
do_version_info(PyObject *dummy, PyObject *args);

#if !defined(PYCURL_SINGLE_FILE)
/* Type objects */
extern PyTypeObject Curl_Type;
extern PyTypeObject CurlMulti_Type;
extern PyTypeObject CurlShare_Type;

extern PyObject *ErrorObject;
extern PyTypeObject *p_Curl_Type;
extern PyTypeObject *p_CurlMulti_Type;
extern PyTypeObject *p_CurlShare_Type;

extern PyObject *curlobject_constants;
extern PyObject *curlmultiobject_constants;
extern PyObject *curlshareobject_constants;

extern char *g_pycurl_useragent;

extern PYCURL_INTERNAL char *empty_keywords[];

#if PY_MAJOR_VERSION >= 3
extern PyMethodDef curlobject_methods[];
extern PyMethodDef curlshareobject_methods[];
extern PyMethodDef curlmultiobject_methods[];
#endif
#endif /* !PYCURL_SINGLE_FILE */

/* vi:ts=4:et:nowrap
 */
