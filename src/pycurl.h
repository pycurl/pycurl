#if (defined(_WIN32) || defined(__WIN32__)) && !defined(WIN32)
#  define WIN32 1
#endif
#define PY_SSIZE_T_CLEAN
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
#include <sys/un.h>
#endif

#if defined(WIN32)
/*
 * Since setup.py uses a '-WX' in the CFLAGS (treat warnings as errors),
 * the below will turn off some warnings when using MS-SDK 8.1+.
 * This MUST be defined before including <winsock2.h> via the libcurl
 * headers.
 */
# if !defined(_WINSOCK_DEPRECATED_NO_WARNINGS)
#  define _WINSOCK_DEPRECATED_NO_WARNINGS
# endif
#endif

#include <curl/curl.h>
#include <curl/easy.h>
#include <curl/multi.h>
#undef NDEBUG
#include <assert.h>

/* Use for ignoring libcurl deprecation warnings */
#if defined(__clang__) || defined(__GNUC__)
  #define PYCURL_IGNORE_DEPRECATED_BEGIN \
    _Pragma("GCC diagnostic push") \
    _Pragma("GCC diagnostic ignored \"-Wdeprecated-declarations\"")
  #define PYCURL_IGNORE_DEPRECATED_END \
    _Pragma("GCC diagnostic pop")
#else
#  define PYCURL_IGNORE_DEPRECATED_BEGIN
#  define PYCURL_IGNORE_DEPRECATED_END
#endif

#define MAKE_LIBCURL_VERSION(major, minor, patch) \
    ((major) * 0x10000 + (minor) * 0x100 + (patch))

/* spot check */
#if MAKE_LIBCURL_VERSION(7, 21, 16) != 0x071510
# error MAKE_LIBCURL_VERSION is not working correctly
#endif

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

PYCURL_INTERNAL curl_socket_t
dup_winsock(curl_socket_t sock, const struct curl_sockaddr *address);
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

#if LIBCURL_VERSION_NUM >= 0x071305 /* check for 7.19.5 or greater */
#define HAVE_CURL_7_19_5_OPTS
#endif

#if LIBCURL_VERSION_NUM >= 0x071306 /* check for 7.19.6 or greater */
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

#if LIBCURL_VERSION_NUM >= 0x071600 /* check for 7.22.0 or greater */
#define HAVE_CURL_7_22_0_OPTS
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

#if LIBCURL_VERSION_NUM >= 0x073100 /* check for 7.49.0 or greater */
#define HAVE_CURLOPT_CONNECT_TO
#endif

#if LIBCURL_VERSION_NUM >= 0x073200 /* check for 7.50.0 or greater */
#define HAVE_CURLINFO_HTTP_VERSION
#endif

#if LIBCURL_VERSION_NUM >= 0x073C00 /* check for 7.60.0 or greater */
#define HAVE_CURLOPT_HAPROXYPROTOCOL
#endif

/* curl_global_sslset() was added in 7.56.0 but was buggy until 7.63.0 */
#if LIBCURL_VERSION_NUM >= 0x073F00 /* check for 7.63.0 or greater */
#define HAVE_CURL_GLOBAL_SSLSET
#endif

#if LIBCURL_VERSION_NUM >= MAKE_LIBCURL_VERSION(7, 56, 0)
#define HAVE_CURL_MIME
#endif

#if LIBCURL_VERSION_NUM >= 0x074300 /* check for 7.67.0 or greater */
#define HAVE_CURL_7_67_0_MULTI_STREAMS
#endif

#if LIBCURL_VERSION_NUM >= MAKE_LIBCURL_VERSION(7, 86, 0)
#define HAVE_CURL_WEBSOCKETS
#include <curl/websockets.h>
#endif

#undef UNUSED
#define UNUSED(var)     ((void)&var)

/* Cruft for thread safe SSL crypto locks, snapped from the PHP curl extension */
#if defined(HAVE_CURL_SSL)
# if defined(HAVE_CURL_OPENSSL)
#   define PYCURL_NEED_SSL_TSL
#   define PYCURL_NEED_OPENSSL_TSL
#   include <openssl/ssl.h>
#   include <openssl/err.h>
#   define COMPILE_SSL_LIB "openssl"
#   define COMPILE_SUPPORTED_SSL_BACKEND_FOUND 1
# elif defined(HAVE_CURL_WOLFSSL)
#   include <wolfssl/options.h>
#   if defined(OPENSSL_EXTRA)
#     define HAVE_CURL_OPENSSL
#     define PYCURL_NEED_SSL_TSL
#     define PYCURL_NEED_OPENSSL_TSL
#     include <wolfssl/openssl/ssl.h>
#     include <wolfssl/openssl/err.h>
#   else
#    ifdef _MSC_VER
#     pragma message(\
       "libcurl was compiled with wolfSSL, but the library was built without " \
       "--enable-opensslextra; thus no SSL crypto locking callbacks will be set, " \
       "which may cause random crashes on SSL requests")
#    else
#     warning \
       "libcurl was compiled with wolfSSL, but the library was built without " \
       "--enable-opensslextra; thus no SSL crypto locking callbacks will be set, " \
       "which may cause random crashes on SSL requests"
#    endif
#   endif
#   define COMPILE_SSL_LIB "wolfssl"
#   define COMPILE_SUPPORTED_SSL_BACKEND_FOUND 1
# elif defined(HAVE_CURL_GNUTLS)
#   include <gnutls/gnutls.h>
#   if GNUTLS_VERSION_NUMBER <= 0x020b00
#     define PYCURL_NEED_SSL_TSL
#     define PYCURL_NEED_GNUTLS_TSL
#     include <gcrypt.h>
#   endif
#   define COMPILE_SSL_LIB "gnutls"
#   define COMPILE_SUPPORTED_SSL_BACKEND_FOUND 1
# elif defined(HAVE_CURL_NSS)
#   define COMPILE_SSL_LIB "nss"
#   define COMPILE_SUPPORTED_SSL_BACKEND_FOUND 1
# elif defined(HAVE_CURL_MBEDTLS)
#   include <mbedtls/ssl.h>
#   define PYCURL_NEED_SSL_TSL
#   define PYCURL_NEED_MBEDTLS_TSL
#   define COMPILE_SSL_LIB "mbedtls"
#   define COMPILE_SUPPORTED_SSL_BACKEND_FOUND 1
# elif defined(HAVE_CURL_SECTRANSP)
#   define COMPILE_SSL_LIB "secure-transport"
#   define COMPILE_SUPPORTED_SSL_BACKEND_FOUND 1
# elif defined(HAVE_CURL_SCHANNEL)
#   define COMPILE_SSL_LIB "schannel"
#   define COMPILE_SUPPORTED_SSL_BACKEND_FOUND 1
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
#  define COMPILE_SUPPORTED_SSL_BACKEND_FOUND 0
# endif /* HAVE_CURL_OPENSSL || HAVE_CURL_WOLFSSL || HAVE_CURL_GNUTLS || HAVE_CURL_NSS || HAVE_CURL_MBEDTLS || HAVE_CURL_SECTRANSP || HAVE_CURL_SCHANNEL */
#else
# define COMPILE_SSL_LIB "none/other"
# define COMPILE_SUPPORTED_SSL_BACKEND_FOUND 0
#endif /* HAVE_CURL_SSL */

#if defined(PYCURL_NEED_SSL_TSL)
PYCURL_INTERNAL int pycurl_ssl_init(void);
PYCURL_INTERNAL void pycurl_ssl_cleanup(void);
#endif

#  define PYCURL_DECLARE_THREAD_STATE PyThreadState *tmp_state
#  define PYCURL_ACQUIRE_THREAD() pycurl_acquire_thread(self, &tmp_state)
#  define PYCURL_ACQUIRE_THREAD_MULTI() pycurl_acquire_thread_multi(self, &tmp_state)
#  define PYCURL_RELEASE_THREAD() pycurl_release_thread(tmp_state)
#  define PYCURL_END_CALLBACK(retval) \
       PYCURL_RELEASE_THREAD(); \
       return (retval)
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
#  define PYCURL_BEGIN_ALLOW_THREADS_EASY \
       if (self->multi_stack == NULL) { \
           self->state = PyThreadState_Get(); \
           assert(self->state != NULL); \
       } else { \
           self->multi_stack->state = PyThreadState_Get(); \
           assert(self->multi_stack->state != NULL); \
       } \
       Py_BEGIN_ALLOW_THREADS
#  define PYCURL_END_ALLOW_THREADS_EASY \
       PYCURL_END_ALLOW_THREADS \
       if (self->multi_stack != NULL) \
           self->multi_stack->state = NULL;

#if PY_VERSION_HEX < 0x030D0000  /* Python 3.13 */
#  define Py_IsFinalizing _Py_IsFinalizing
#endif

#define PYCURL_BEGIN_CALLBACK_COMMON(acquire_expr, retval, callback_name) \
    if (Py_IsFinalizing()) { \
        return (retval); \
    } \
    if (!(acquire_expr)) { \
        warn_failed_to_acquire_thread(#callback_name " failed to acquire thread"); \
        return (retval); \
    }

/* Convert socket values without truncation on Win64 where curl_socket_t is SOCKET. */
PYCURL_INTERNAL PyObject *
PyLong_FromCurlSocket(curl_socket_t sockfd);
PYCURL_INTERNAL int
PyLong_AsCurlSocket(PyObject *obj, curl_socket_t *sockfd);

#define PYLISTORTUPLE_LIST 1
#define PYLISTORTUPLE_TUPLE 2
#define PYLISTORTUPLE_OTHER 0

PYCURL_INTERNAL int
PyListOrTuple_Check(PyObject *v);
PYCURL_INTERNAL Py_ssize_t
PyListOrTuple_Size(PyObject *v, int which);
PYCURL_INTERNAL PyObject *
PyListOrTuple_GetItem(PyObject *v, Py_ssize_t i, int which);

/*************************************************************************
// string helpers
**************************************************************************/

PYCURL_INTERNAL int
PyText_AsStringAndSize(PyObject *obj, char **buffer, Py_ssize_t *length, PyObject **encoded_obj);
PYCURL_INTERNAL char *
PyText_AsString_NoNUL(PyObject *obj, PyObject **encoded_obj);
PYCURL_INTERNAL int
PyText_Check(PyObject *o);
PYCURL_INTERNAL PyObject *
PyText_FromString_Ignore(const char *string);

PYCURL_INTERNAL int
callback_return_value_to_int(PyObject *ret_obj, const char *callback_name, int *ret_out);

struct CurlObject;

PYCURL_INTERNAL void
create_and_set_error_object(struct CurlObject *self, int code);


/* Raise exception based on return value `res' and `self->error' */
#define CURLERROR_RETVAL() do {\
    create_and_set_error_object((self), (int) (res)); \
    return NULL; \
} while (0)

#define CURLERROR_SET_RETVAL() \
    create_and_set_error_object((self), (int) (res));

#define CURLERROR_RETVAL_MULTI_DONE() do {\
    PyObject *v; \
    v = Py_BuildValue("(i)", (int) (res)); \
    if (v != NULL) { PyErr_SetObject(ErrorObject, v); Py_DECREF(v); } \
    goto done; \
} while (0)

/* Raise exception based on return value `res' and custom message */
/* msg should be ASCII */
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
/* CA certs object */
#define PYCURL_MEMGROUP_CACERTS         128
/* Curl slist objects */
#define PYCURL_MEMGROUP_SLIST           256
/* CurlMime object pinned via CURLOPT_MIMEPOST */
#define PYCURL_MEMGROUP_MIMEPOST        512

#define PYCURL_MEMGROUP_EASY \
    (PYCURL_MEMGROUP_CALLBACK | PYCURL_MEMGROUP_FILE | \
    PYCURL_MEMGROUP_HTTPPOST | PYCURL_MEMGROUP_POSTFIELDS | \
    PYCURL_MEMGROUP_CACERTS | PYCURL_MEMGROUP_SLIST | \
    PYCURL_MEMGROUP_MIMEPOST)

#define PYCURL_MEMGROUP_ALL \
    (PYCURL_MEMGROUP_ATTRDICT | PYCURL_MEMGROUP_EASY | \
    PYCURL_MEMGROUP_MULTI | PYCURL_MEMGROUP_SHARE)

typedef struct CurlSlistObject {
    PyObject_HEAD
    struct curl_slist *slist;
} CurlSlistObject;

typedef struct CurlHttppostObject {
    PyObject_HEAD
    struct curl_httppost *httppost;
    /* List of INC'ed references associated with httppost. */
    PyObject *reflist;
} CurlHttppostObject;

typedef struct CurlObject {
    PyObject_HEAD
    PyObject *dict;                 /* Python attributes dictionary */
    // https://docs.python.org/3/extending/newtypes.html
    PyObject *weakreflist;
    CURL *handle;
    PyThreadState *state;
    PyObject *multi_weakref;
    struct CurlMultiObject *multi_stack;
    struct CurlShareObject *share;
    struct CurlHttppostObject *httppost;
#ifdef HAVE_CURL_MIME
    PyObject *mimepost_obj;
#endif
    struct CurlSlistObject *httpheader;
#if LIBCURL_VERSION_NUM >= MAKE_LIBCURL_VERSION(7, 37, 0)
    struct CurlSlistObject *proxyheader;
#endif
    struct CurlSlistObject *http200aliases;
    struct CurlSlistObject *quote;
    struct CurlSlistObject *postquote;
    struct CurlSlistObject *prequote;
    struct CurlSlistObject *telnetoptions;
#ifdef HAVE_CURLOPT_RESOLVE
    struct CurlSlistObject *resolve;
#endif
#ifdef HAVE_CURL_7_20_0_OPTS
    struct CurlSlistObject *mail_rcpt;
#endif
#ifdef HAVE_CURLOPT_CONNECT_TO
    struct CurlSlistObject *connect_to;
#endif
    /* callbacks */
    PyObject *w_cb;
    PyObject *h_cb;
    PyObject *r_cb;
    PyObject *pro_cb;
#if LIBCURL_VERSION_NUM >= MAKE_LIBCURL_VERSION(7, 32, 0)
    PyObject *xferinfo_cb;
#endif
    PyObject *debug_cb;
    PyObject *ioctl_cb;
    PyObject *opensocket_cb;
#if LIBCURL_VERSION_NUM >= 0x071507 /* check for 7.21.7 or greater */
    PyObject *closesocket_cb;
#endif
    PyObject *seek_cb;
    PyObject *sockopt_cb;
    PyObject *ssh_key_cb;
#if LIBCURL_VERSION_NUM >= MAKE_LIBCURL_VERSION(7, 80, 0)
    PyObject *prereq_cb;
#endif
#if LIBCURL_VERSION_NUM >= MAKE_LIBCURL_VERSION(7, 21, 0)
    PyObject *fnmatch_cb;
#endif
#if LIBCURL_VERSION_NUM >= MAKE_LIBCURL_VERSION(7, 59, 0)
    PyObject *resolver_start_cb;
#endif
#if LIBCURL_VERSION_NUM >= MAKE_LIBCURL_VERSION(7, 64, 0)
    PyObject *trailer_cb;
#endif
#if LIBCURL_VERSION_NUM >= MAKE_LIBCURL_VERSION(7, 74, 0)
    PyObject *hstsread_cb;
    PyObject *hstswrite_cb;
#endif
    /* file objects */
    PyObject *readdata_fp;
    PyObject *writedata_fp;
    PyObject *writeheader_fp;
    /* reference to the object used for CURLOPT_POSTFIELDS */
    PyObject *postfields_obj;
    /* reference to the object containing ca certs */
    PyObject *ca_certs_obj;
    /* true while executing WRITEFUNCTION for this handle */
    int ws_write_cb_running;
    /* misc */
    char error[CURL_ERROR_SIZE+1];
} CurlObject;

typedef struct CurlMultiObject {
    PyObject_HEAD
    PyObject *dict;                 /* Python attributes dictionary */
    // https://docs.python.org/3/extending/newtypes.html
    PyObject *weakreflist;
    CURLM *multi_handle;
    PyThreadState *state;
    fd_set read_fd_set;
    fd_set write_fd_set;
    fd_set exc_fd_set;
    /* callbacks */
    PyObject *t_cb;
    PyObject *s_cb;

    /* socket-to-object mappings for curl_multi_assign */
    PyObject *socket_object_dict;

    PyObject *easy_object_dict;
    int close_handles; /* boolean: False by default */
} CurlMultiObject;

typedef struct {
    PyThread_type_lock locks[CURL_LOCK_DATA_LAST];
} ShareLock;

typedef struct CurlShareObject {
    PyObject_HEAD
    PyObject *dict;                 /* Python attributes dictionary */
    // https://docs.python.org/3/extending/newtypes.html
    PyObject *weakreflist;
    CURLSH *share_handle;
    ShareLock *lock;                /* lock object to implement CURLSHOPT_LOCKFUNC */
    PyThread_type_lock easy_weakrefs_lock;  /* protects easy_weakrefs map */
    /* Set of weakref.ref(CurlObject) */
    PyObject *easy_weakrefs;
    int detach_on_close; /* boolean: True by default */
} CurlShareObject;

#ifdef HAVE_CURL_MIME
typedef struct CurlMimeObject {
    PyObject_HEAD
    struct CurlObject *curl;
    curl_mime *mime;
    PyObject *parts;
    PyObject *submimes;
    PyObject *data_cb_owners;
    int owns_mime;
} CurlMimeObject;

typedef struct CurlMimePartObject {
    PyObject_HEAD
    CurlMimeObject *mime;
    curl_mimepart *part;
    PyObject *data_cb_owner;
} CurlMimePartObject;

PYCURL_INTERNAL void
curlmime_duphandle_incref_data_cb_owners(PyObject *mime_obj);
#endif

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

PYCURL_INTERNAL PyObject *
my_getattro(PyObject *co, PyObject *name, PyObject *dict1, PyObject *dict2, PyMethodDef *m);
PYCURL_INTERNAL int
my_setattro(PyObject **dict, PyObject *name, PyObject *v);

/* used by multi object */
PYCURL_INTERNAL void
assert_curl_state(const CurlObject *self);

PYCURL_INTERNAL int
check_pending_python_signal(void);

PYCURL_INTERNAL int
check_pending_python_exception_or_signal(void);

PYCURL_INTERNAL void
warn_failed_to_acquire_thread(const char *warning_message);

PYCURL_INTERNAL void
print_callback_error_if_regular_exception(void);

PYCURL_INTERNAL PyObject *
do_global_init(PyObject *dummy, PyObject *args);
PYCURL_INTERNAL PyObject *
do_global_cleanup(PyObject *dummy, PyObject *Py_UNUSED(ignored));
PYCURL_INTERNAL PyObject *
do_version_info(PyObject *dummy, PyObject *args);

PYCURL_INTERNAL PyObject *
do_curl_setopt(CurlObject *self, PyObject *args);
PYCURL_INTERNAL PyObject *
do_curl_setopt_string(CurlObject *self, PyObject *args);
PYCURL_INTERNAL PyObject *
do_curl_unsetopt(CurlObject *self, PyObject *args);
#if defined(HAVE_CURL_OPENSSL)
PYCURL_INTERNAL PyObject *
do_curl_set_ca_certs(CurlObject *self, PyObject *args);
#endif
PYCURL_INTERNAL PyObject *
do_curl_perform(CurlObject *self, PyObject *Py_UNUSED(ignored));
PYCURL_INTERNAL PyObject *
do_curl_perform_rb(CurlObject *self, PyObject *Py_UNUSED(ignored));
PYCURL_INTERNAL PyObject *
do_curl_perform_rs(CurlObject *self, PyObject *Py_UNUSED(ignored));

PYCURL_INTERNAL PyObject *
do_curl_pause(CurlObject *self, PyObject *args);
PYCURL_INTERNAL PyObject *
do_curl_unpause(CurlObject *self, PyObject *Py_UNUSED(ignored));
PYCURL_INTERNAL PyObject *
do_curl_send(CurlObject *self, PyObject *args);
PYCURL_INTERNAL PyObject *
do_curl_recv(CurlObject *self, PyObject *args);
PYCURL_INTERNAL PyObject *
do_curl_recv_into(CurlObject *self, PyObject *args, PyObject *kwds);

PYCURL_INTERNAL PyObject *set_would_block_error(void);
PYCURL_INTERNAL int
check_easy_recv_send_result(CurlObject *self, CURLcode res);

#ifdef HAVE_CURL_WEBSOCKETS
PYCURL_INTERNAL PyObject *
do_curl_ws_send(CurlObject *self, PyObject *args, PyObject *kwds);
PYCURL_INTERNAL PyObject *
do_curl_ws_recv(CurlObject *self, PyObject *args);
PYCURL_INTERNAL PyObject *
do_curl_ws_recv_into(CurlObject *self, PyObject *args, PyObject *kwds);
PYCURL_INTERNAL PyObject *
do_curl_ws_meta(CurlObject *self, PyObject *Py_UNUSED(ignored));
PYCURL_INTERNAL PyObject *
do_curl_ws_close(CurlObject *self, PyObject *args, PyObject *kwds);
#endif

PYCURL_INTERNAL int
check_curl_state(const CurlObject *self, int flags, const char *name);
PYCURL_INTERNAL void
util_curl_xdecref(CurlObject *self, int flags, CURL *handle);
PYCURL_INTERNAL PyObject *
do_curl_setopt_filelike(CurlObject *self, int option, PyObject *obj);

PYCURL_INTERNAL int
util_curlslist_update(CurlSlistObject **old, struct curl_slist *slist);
PYCURL_INTERNAL int
util_curlhttppost_update(CurlObject *obj, struct curl_httppost *httppost, PyObject *reflist);

PYCURL_INTERNAL PyObject *
do_curl_getinfo_raw(CurlObject *self, PyObject *args);
PYCURL_INTERNAL PyObject *
do_curl_getinfo(CurlObject *self, PyObject *args);
PYCURL_INTERNAL PyObject *
do_curl_errstr(CurlObject *self, PyObject *Py_UNUSED(ignored));
PYCURL_INTERNAL PyObject *
do_curl_errstr_raw(CurlObject *self, PyObject *Py_UNUSED(ignored));

PYCURL_INTERNAL size_t
write_callback(char *ptr, size_t size, size_t nmemb, void *stream);
PYCURL_INTERNAL size_t
header_callback(char *ptr, size_t size, size_t nmemb, void *stream);
PYCURL_INTERNAL curl_socket_t
opensocket_callback(void *clientp, curlsocktype purpose,
                    struct curl_sockaddr *address);
PYCURL_INTERNAL int
sockopt_cb(void *clientp, curl_socket_t curlfd, curlsocktype purpose);
#if LIBCURL_VERSION_NUM >= MAKE_LIBCURL_VERSION(7, 21, 7)
PYCURL_INTERNAL int
closesocket_callback(void *clientp, curl_socket_t curlfd);
#endif
#ifdef HAVE_CURL_7_19_6_OPTS
PYCURL_INTERNAL int
ssh_key_cb(CURL *easy, const struct curl_khkey *knownkey,
           const struct curl_khkey *foundkey, enum curl_khmatch khmatch,
           void *clientp);
#endif
PYCURL_INTERNAL int
seek_callback(void *stream, curl_off_t offset, int origin);
PYCURL_INTERNAL size_t
read_callback(char *ptr, size_t size, size_t nmemb, void *stream);
PYCURL_INTERNAL int
progress_callback(void *stream,
                  double dltotal, double dlnow, double ultotal, double ulnow);
#if LIBCURL_VERSION_NUM >= MAKE_LIBCURL_VERSION(7, 32, 0)
PYCURL_INTERNAL int
xferinfo_callback(void *stream,
    curl_off_t dltotal, curl_off_t dlnow,
    curl_off_t ultotal, curl_off_t ulnow);
#endif
PYCURL_INTERNAL int
debug_callback(CURL *curlobj, curl_infotype type,
               char *buffer, size_t total_size, void *stream);
PYCURL_INTERNAL curlioerr
ioctl_callback(CURL *curlobj, int cmd, void *stream);
#if defined(HAVE_CURL_OPENSSL)
PYCURL_INTERNAL CURLcode
ssl_ctx_callback(CURL *curl, void *ssl_ctx, void *ptr);
#endif
#if LIBCURL_VERSION_NUM >= MAKE_LIBCURL_VERSION(7, 80, 0)
PYCURL_INTERNAL int
prereq_callback(void *clientp, char *conn_primary_ip, char *conn_local_ip,
                int conn_primary_port, int conn_local_port);
#endif
#if LIBCURL_VERSION_NUM >= MAKE_LIBCURL_VERSION(7, 21, 0)
PYCURL_INTERNAL int
fnmatch_callback(void *clientp, const char *pattern, const char *string);
#endif
#if LIBCURL_VERSION_NUM >= MAKE_LIBCURL_VERSION(7, 59, 0)
PYCURL_INTERNAL int
resolver_start_callback(void *resolver_state, void *reserved, void *clientp);
#endif
#if LIBCURL_VERSION_NUM >= MAKE_LIBCURL_VERSION(7, 64, 0)
PYCURL_INTERNAL int
trailer_callback(struct curl_slist **list, void *clientp);
#endif
#if LIBCURL_VERSION_NUM >= MAKE_LIBCURL_VERSION(7, 74, 0)
PYCURL_INTERNAL CURLSTScode
hstsread_callback(CURL *easy, struct curl_hstsentry *e, void *clientp);
PYCURL_INTERNAL CURLSTScode
hstswrite_callback(CURL *easy, struct curl_hstsentry *e,
                   struct curl_index *i, void *clientp);
#endif

PYCURL_INTERNAL struct curl_slist *
pycurl_list_or_tuple_to_slist(int which, PyObject *obj, Py_ssize_t len);

PYCURL_INTERNAL int share_register_easy(struct CurlShareObject *share, struct CurlObject *easy);
PYCURL_INTERNAL void share_unregister_easy(struct CurlShareObject *share, struct CurlObject *easy);

#if !defined(PYCURL_SINGLE_FILE)
/* Type objects */
extern PyTypeObject Curl_Type;
extern PyTypeObject CurlSlist_Type;
extern PyTypeObject CurlHttppost_Type;
extern PyTypeObject CurlMulti_Type;
extern PyTypeObject CurlShare_Type;
#ifdef HAVE_CURL_MIME
extern PyTypeObject CurlMime_Type;
extern PyTypeObject CurlMimePart_Type;
#endif

extern PyObject *ErrorObject;
extern PyTypeObject *p_Curl_Type;
extern PyTypeObject *p_CurlSlist_Type;
extern PyTypeObject *p_CurlHttppost_Type;
extern PyTypeObject *p_CurlMulti_Type;
extern PyTypeObject *p_CurlShare_Type;
#ifdef HAVE_CURL_MIME
extern PyTypeObject *p_CurlMime_Type;
extern PyTypeObject *p_CurlMimePart_Type;
#endif
extern PyObject *khkey_type;
extern PyObject *curl_sockaddr_type;
#if LIBCURL_VERSION_NUM >= MAKE_LIBCURL_VERSION(7, 74, 0)
extern PyObject *hsts_entry_type;
extern PyObject *hsts_index_type;
extern PyObject *datetime_type;
extern PyObject *utc_tz;
#endif
#ifdef HAVE_CURL_WEBSOCKETS
extern PyObject *ws_frame_type;
#endif

extern PyObject *curlobject_constants;
extern PyObject *curlmultiobject_constants;
extern PyObject *curlshareobject_constants;

extern char *g_pycurl_useragent;

extern PYCURL_INTERNAL char *empty_keywords[];
extern PYCURL_INTERNAL PyObject *bytesio;
extern PYCURL_INTERNAL PyObject *stringio;

extern PyMethodDef curlobject_methods[];
extern PyMethodDef curlshareobject_methods[];
extern PyMethodDef curlmultiobject_methods[];
#endif /* !PYCURL_SINGLE_FILE */

#define PYCURL_TYPE_FLAGS Py_TPFLAGS_HAVE_GC | Py_TPFLAGS_BASETYPE


#ifdef PYCURL_AUTODETECT_CA
extern char *g_pycurl_autodetected_cainfo;
extern char *g_pycurl_autodetected_capath;
#endif

/* vi:ts=4:et:nowrap
 */
