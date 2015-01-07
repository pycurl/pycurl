#include "pycurl.h"
#include "docstrings.h"

#if defined(WIN32)
# define PYCURL_STRINGIZE_IMP(x) #x
# define PYCURL_STRINGIZE(x) PYCURL_STRINGIZE_IMP(x)
# define PYCURL_VERSION_STRING PYCURL_STRINGIZE(PYCURL_VERSION)
#else
# define PYCURL_VERSION_STRING PYCURL_VERSION
#endif

#define PYCURL_VERSION_PREFIX "PycURL/" PYCURL_VERSION_STRING

PYCURL_INTERNAL char *empty_keywords[] = { NULL };

/* Initialized during module init */
PYCURL_INTERNAL char *g_pycurl_useragent = NULL;

/* Type objects */
PYCURL_INTERNAL PyObject *ErrorObject = NULL;
PYCURL_INTERNAL PyTypeObject *p_Curl_Type = NULL;
PYCURL_INTERNAL PyTypeObject *p_CurlMulti_Type = NULL;
PYCURL_INTERNAL PyTypeObject *p_CurlShare_Type = NULL;

PYCURL_INTERNAL PyObject *curlobject_constants = NULL;
PYCURL_INTERNAL PyObject *curlmultiobject_constants = NULL;
PYCURL_INTERNAL PyObject *curlshareobject_constants = NULL;


/* List of functions defined in this module */
static PyMethodDef curl_methods[] = {
    {"global_init", (PyCFunction)do_global_init, METH_VARARGS, pycurl_global_init_doc},
    {"global_cleanup", (PyCFunction)do_global_cleanup, METH_NOARGS, pycurl_global_cleanup_doc},
    {"version_info", (PyCFunction)do_version_info, METH_VARARGS, pycurl_version_info_doc},
    {NULL, NULL, 0, NULL}
};


/*************************************************************************
// module level
// Note that the object constructors (do_curl_new, do_multi_new)
// are module-level functions as well.
**************************************************************************/

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

PYCURL_INTERNAL PyObject *
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


PYCURL_INTERNAL PyObject *
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
    return PyText_FromString(s);
}

PYCURL_INTERNAL PyObject *
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

    key = PyText_FromString(name);

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
    PyObject *v = PyText_FromString(value);
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


#if PY_MAJOR_VERSION >= 3
/* Used in Python 3 only, and even then this function seems to never get
 * called. Python 2 has no module cleanup:
 * http://stackoverflow.com/questions/20741856/run-a-function-when-a-c-extension-module-is-freed-on-python-2
 */
static void do_curlmod_free(void *unused) {
    PyMem_Free(g_pycurl_useragent);
    g_pycurl_useragent = NULL;
}

static PyModuleDef curlmodule = {
    PyModuleDef_HEAD_INIT,
    "pycurl",           /* m_name */
    pycurl_module_doc,  /* m_doc */
    -1,                 /* m_size */
    curl_methods,       /* m_methods */
    NULL,               /* m_reload */
    NULL,               /* m_traverse */
    NULL,               /* m_clear */
    do_curlmod_free     /* m_free */
};
#endif


#if PY_MAJOR_VERSION >= 3
#define PYCURL_MODINIT_RETURN_NULL return NULL
PyMODINIT_FUNC PyInit_pycurl(void)
#else
#define PYCURL_MODINIT_RETURN_NULL return
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
#endif
{
    PyObject *m, *d;
    const curl_version_info_data *vi;
    const char *libcurl_version, *runtime_ssl_lib;
    int libcurl_version_len, pycurl_version_len;

    /* Check the version, as this has caused nasty problems in
     * some cases. */
    vi = curl_version_info(CURLVERSION_NOW);
    if (vi == NULL) {
        PyErr_SetString(PyExc_ImportError, "pycurl: curl_version_info() failed");
        PYCURL_MODINIT_RETURN_NULL;
    }
    if (vi->version_num < LIBCURL_VERSION_NUM) {
        PyErr_Format(PyExc_ImportError, "pycurl: libcurl link-time version (%s) is older than compile-time version (%s)", vi->version, LIBCURL_VERSION);
        PYCURL_MODINIT_RETURN_NULL;
    }
    
    /* Our compiled crypto locks should correspond to runtime ssl library. */
    if (vi->ssl_version == NULL) {
        runtime_ssl_lib = "none/other";
    } else if (!strncmp(vi->ssl_version, "OpenSSL/", 8)) {
        runtime_ssl_lib = "openssl";
    } else if (!strncmp(vi->ssl_version, "LibreSSL/", 9)) {
        runtime_ssl_lib = "openssl";
    } else if (!strncmp(vi->ssl_version, "GnuTLS/", 7)) {
        runtime_ssl_lib = "gnutls";
    } else if (!strncmp(vi->ssl_version, "NSS/", 4)) {
        runtime_ssl_lib = "nss";
    } else {
        runtime_ssl_lib = "none/other";
    }
    if (strcmp(runtime_ssl_lib, COMPILE_SSL_LIB)) {
        PyErr_Format(PyExc_ImportError, "pycurl: libcurl link-time ssl backend (%s) is different from compile-time ssl backend (%s)", runtime_ssl_lib, COMPILE_SSL_LIB);
        PYCURL_MODINIT_RETURN_NULL;
    }

    /* Initialize the type of the new type objects here; doing it here
     * is required for portability to Windows without requiring C++. */
    p_Curl_Type = &Curl_Type;
    p_CurlMulti_Type = &CurlMulti_Type;
    p_CurlShare_Type = &CurlShare_Type;
    Py_TYPE(&Curl_Type) = &PyType_Type;
    Py_TYPE(&CurlMulti_Type) = &PyType_Type;
    Py_TYPE(&CurlShare_Type) = &PyType_Type;

    /* Create the module and add the functions */
    if (PyType_Ready(&Curl_Type) < 0)
        PYCURL_MODINIT_RETURN_NULL;

    if (PyType_Ready(&CurlMulti_Type) < 0)
        PYCURL_MODINIT_RETURN_NULL;

    if (PyType_Ready(&CurlShare_Type) < 0)
        PYCURL_MODINIT_RETURN_NULL;

#if PY_MAJOR_VERSION >= 3
    m = PyModule_Create(&curlmodule);
    if (m == NULL)
        return NULL;
#else

    m = Py_InitModule3("pycurl", curl_methods, pycurl_module_doc);
    assert(m != NULL && PyModule_Check(m));
#endif

    /* Add error object to the module */
    d = PyModule_GetDict(m);
    assert(d != NULL);
    ErrorObject = PyErr_NewException("pycurl.error", NULL, NULL);
    assert(ErrorObject != NULL);
    PyDict_SetItemString(d, "error", ErrorObject);

    curlobject_constants = PyDict_New();
    assert(curlobject_constants != NULL);

    /* Add version strings to the module */
    libcurl_version = curl_version();
    libcurl_version_len = strlen(libcurl_version);
#define PYCURL_VERSION_PREFIX_SIZE sizeof(PYCURL_VERSION_PREFIX)
    /* PYCURL_VERSION_PREFIX_SIZE includes terminating null which will be
     * replaced with the space; libcurl_version_len does not include
     * terminating null. */
    pycurl_version_len = PYCURL_VERSION_PREFIX_SIZE + libcurl_version_len + 1;
    g_pycurl_useragent = PyMem_Malloc(pycurl_version_len);
    assert(g_pycurl_useragent != NULL);
    memcpy(g_pycurl_useragent, PYCURL_VERSION_PREFIX, PYCURL_VERSION_PREFIX_SIZE);
    g_pycurl_useragent[PYCURL_VERSION_PREFIX_SIZE-1] = ' ';
    memcpy(g_pycurl_useragent + PYCURL_VERSION_PREFIX_SIZE,
        libcurl_version, libcurl_version_len);
    g_pycurl_useragent[pycurl_version_len - 1] = 0;
#undef PYCURL_VERSION_PREFIX_SIZE

    insobj2(d, NULL, "version", PyText_FromString(g_pycurl_useragent));
    insstr(d, "COMPILE_DATE", __DATE__ " " __TIME__);
    insint(d, "COMPILE_PY_VERSION_HEX", PY_VERSION_HEX);
    insint(d, "COMPILE_LIBCURL_VERSION_NUM", LIBCURL_VERSION_NUM);

    /* Types */
    insobj2(d, NULL, "Curl", (PyObject *) p_Curl_Type);
    insobj2(d, NULL, "CurlMulti", (PyObject *) p_CurlMulti_Type);
    insobj2(d, NULL, "CurlShare", (PyObject *) p_CurlShare_Type);
    
    /**
     ** the order of these constants mostly follows <curl/curl.h>
     **/

    /* Abort curl_read_callback(). */
    insint_c(d, "READFUNC_ABORT", CURL_READFUNC_ABORT);
    insint_c(d, "READFUNC_PAUSE", CURL_READFUNC_PAUSE);

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
#ifdef HAVE_CURL_7_21_5
    insint_c(d, "E_NOT_BUILT_IN", CURLE_NOT_BUILT_IN);
#endif
    insint_c(d, "E_COULDNT_RESOLVE_PROXY", CURLE_COULDNT_RESOLVE_PROXY);
    insint_c(d, "E_COULDNT_RESOLVE_HOST", CURLE_COULDNT_RESOLVE_HOST);
    insint_c(d, "E_COULDNT_CONNECT", CURLE_COULDNT_CONNECT);
    insint_c(d, "E_FTP_WEIRD_SERVER_REPLY", CURLE_FTP_WEIRD_SERVER_REPLY);
    insint_c(d, "E_FTP_ACCESS_DENIED", CURLE_FTP_ACCESS_DENIED);
#ifdef HAVE_CURL_7_24_0
    insint_c(d, "E_FTP_ACCEPT_FAILED", CURLE_FTP_ACCEPT_FAILED);
#endif
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
    insint_c(d, "E_OPERATION_TIMEDOUT", CURLE_OPERATION_TIMEDOUT);
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
#ifdef HAVE_CURL_7_21_5
    insint_c(d, "E_UNKNOWN_OPTION", CURLE_UNKNOWN_OPTION);
#endif
    /* same as E_UNKNOWN_OPTION */
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
    insint_c(d, "E_TFTP_DISKFULL", CURLE_TFTP_DISKFULL);
    insint_c(d, "E_TFTP_ILLEGAL", CURLE_TFTP_ILLEGAL);
    insint_c(d, "E_TFTP_UNKNOWNID", CURLE_TFTP_UNKNOWNID);
    insint_c(d, "E_TFTP_EXISTS", CURLE_TFTP_EXISTS);
    insint_c(d, "E_TFTP_NOSUCHUSER", CURLE_TFTP_NOSUCHUSER);
    insint_c(d, "E_CONV_FAILED", CURLE_CONV_FAILED);
    insint_c(d, "E_CONV_REQD", CURLE_CONV_REQD);
    insint_c(d, "E_SSL_CACERT_BADFILE", CURLE_SSL_CACERT_BADFILE);
    insint_c(d, "E_REMOTE_FILE_NOT_FOUND", CURLE_REMOTE_FILE_NOT_FOUND);
    insint_c(d, "E_SSH", CURLE_SSH);
    insint_c(d, "E_SSL_SHUTDOWN_FAILED", CURLE_SSL_SHUTDOWN_FAILED);

    /* curl_proxytype: constants for setopt(PROXYTYPE, x) */
    insint_c(d, "PROXYTYPE_HTTP", CURLPROXY_HTTP);
#ifdef HAVE_CURL_7_19_4_OPTS
    insint_c(d, "PROXYTYPE_HTTP_1_0", CURLPROXY_HTTP_1_0);
#endif
    insint_c(d, "PROXYTYPE_SOCKS4", CURLPROXY_SOCKS4);
    insint_c(d, "PROXYTYPE_SOCKS4A", CURLPROXY_SOCKS4A);
    insint_c(d, "PROXYTYPE_SOCKS5", CURLPROXY_SOCKS5);
    insint_c(d, "PROXYTYPE_SOCKS5_HOSTNAME", CURLPROXY_SOCKS5_HOSTNAME);

    /* curl_httpauth: constants for setopt(HTTPAUTH, x) */
    insint_c(d, "HTTPAUTH_NONE", CURLAUTH_NONE);
    insint_c(d, "HTTPAUTH_BASIC", CURLAUTH_BASIC);
    insint_c(d, "HTTPAUTH_DIGEST", CURLAUTH_DIGEST);
#ifdef HAVE_CURLAUTH_DIGEST_IE
    insint_c(d, "HTTPAUTH_DIGEST_IE", CURLAUTH_DIGEST_IE);
#endif
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
#ifdef HAVE_CURL_7_19_6_OPTS
    insint_c(d, "SSH_KNOWNHOSTS", CURLOPT_SSH_KNOWNHOSTS);
#endif
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
#ifdef HAVE_CURLOPT_POSTREDIR
    insint_c(d, "POSTREDIR", CURLOPT_POSTREDIR);
#endif
#ifdef HAVE_CURLOPT_NOPROXY
    insint_c(d, "NOPROXY", CURLOPT_NOPROXY);
#endif
#ifdef HAVE_CURLOPT_PROTOCOLS
    insint_c(d, "PROTOCOLS", CURLOPT_PROTOCOLS);
    insint_c(d, "REDIR_PROTOCOLS", CURLOPT_REDIR_PROTOCOLS);
    insint_c(d, "PROTO_HTTP", CURLPROTO_HTTP);
    insint_c(d, "PROTO_HTTPS", CURLPROTO_HTTPS);
    insint_c(d, "PROTO_FTP", CURLPROTO_FTP);
    insint_c(d, "PROTO_FTPS", CURLPROTO_FTPS);
    insint_c(d, "PROTO_SCP", CURLPROTO_SCP);
    insint_c(d, "PROTO_SFTP", CURLPROTO_SFTP);
    insint_c(d, "PROTO_TELNET", CURLPROTO_TELNET);
    insint_c(d, "PROTO_LDAP", CURLPROTO_LDAP);
    insint_c(d, "PROTO_LDAPS", CURLPROTO_LDAPS);
    insint_c(d, "PROTO_DICT", CURLPROTO_DICT);
    insint_c(d, "PROTO_FILE", CURLPROTO_FILE);
    insint_c(d, "PROTO_TFTP", CURLPROTO_TFTP);
#ifdef HAVE_CURL_7_20_0_OPTS
    insint_c(d, "PROTO_IMAP", CURLPROTO_IMAP);
    insint_c(d, "PROTO_IMAPS", CURLPROTO_IMAPS);
    insint_c(d, "PROTO_POP3", CURLPROTO_POP3);
    insint_c(d, "PROTO_POP3S", CURLPROTO_POP3S);
    insint_c(d, "PROTO_SMTP", CURLPROTO_SMTP);
    insint_c(d, "PROTO_SMTPS", CURLPROTO_SMTPS);
#endif
#ifdef HAVE_CURL_7_21_0_OPTS
    insint_c(d, "PROTO_RTSP", CURLPROTO_RTSP);
    insint_c(d, "PROTO_RTMP", CURLPROTO_RTMP);
    insint_c(d, "PROTO_RTMPT", CURLPROTO_RTMPT);
    insint_c(d, "PROTO_RTMPE", CURLPROTO_RTMPE);
    insint_c(d, "PROTO_RTMPTE", CURLPROTO_RTMPTE);
    insint_c(d, "PROTO_RTMPS", CURLPROTO_RTMPS);
    insint_c(d, "PROTO_RTMPTS", CURLPROTO_RTMPTS);
#endif
#ifdef HAVE_CURL_7_21_2_OPTS
    insint_c(d, "PROTO_GOPHER", CURLPROTO_GOPHER);
#endif
    insint_c(d, "PROTO_ALL", CURLPROTO_ALL);
#endif
#ifdef HAVE_CURL_7_19_4_OPTS
    insint_c(d, "TFTP_BLKSIZE", CURLOPT_TFTP_BLKSIZE);
    insint_c(d, "SOCKS5_GSSAPI_SERVICE", CURLOPT_SOCKS5_GSSAPI_SERVICE);
    insint_c(d, "SOCKS5_GSSAPI_NEC", CURLOPT_SOCKS5_GSSAPI_NEC);
#endif
#ifdef HAVE_CURL_7_20_0_OPTS
    insint_c(d, "MAIL_FROM", CURLOPT_MAIL_FROM);
    insint_c(d, "MAIL_RCPT", CURLOPT_MAIL_RCPT);
#endif
#ifdef HAVE_CURL_7_25_0_OPTS
    insint_c(d, "MAIL_AUTH", CURLOPT_MAIL_AUTH);
#endif

    insint_c(d, "M_TIMERFUNCTION", CURLMOPT_TIMERFUNCTION);
    insint_c(d, "M_SOCKETFUNCTION", CURLMOPT_SOCKETFUNCTION);
    insint_c(d, "M_PIPELINING", CURLMOPT_PIPELINING);
    insint_c(d, "M_MAXCONNECTS", CURLMOPT_MAXCONNECTS);
#ifdef HAVE_CURL_7_30_0_PIPELINE_OPTS
    insint_c(d, "M_MAX_HOST_CONNECTIONS", CURLMOPT_MAX_HOST_CONNECTIONS);
    insint_c(d, "M_MAX_TOTAL_CONNECTIONS", CURLMOPT_MAX_TOTAL_CONNECTIONS);
    insint_c(d, "M_MAX_PIPELINE_LENGTH", CURLMOPT_MAX_PIPELINE_LENGTH);
    insint_c(d, "M_CONTENT_LENGTH_PENALTY_SIZE", CURLMOPT_CONTENT_LENGTH_PENALTY_SIZE);
    insint_c(d, "M_CHUNK_LENGTH_PENALTY_SIZE", CURLMOPT_CHUNK_LENGTH_PENALTY_SIZE);
#endif

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
#ifdef HAVE_CURLINFO_PRIMARY_PORT
    insint_c(d, "PRIMARY_PORT", CURLINFO_PRIMARY_PORT);
#endif
#ifdef HAVE_CURLINFO_LOCAL_IP
    insint_c(d, "LOCAL_IP", CURLINFO_LOCAL_IP);
#endif
#ifdef HAVE_CURLINFO_LOCAL_PORT
    insint_c(d, "LOCAL_PORT", CURLINFO_LOCAL_PORT);
#endif
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
#ifdef HAVE_CURL_7_19_4_OPTS
    insint_c(d, "CONDITION_UNMET", CURLINFO_CONDITION_UNMET);
#endif

    /* CURLPAUSE: symbolic constants for pause(bitmask) */
    insint_c(d, "PAUSE_RECV", CURLPAUSE_RECV);
    insint_c(d, "PAUSE_SEND", CURLPAUSE_SEND);
    insint_c(d, "PAUSE_ALL",  CURLPAUSE_ALL);
    insint_c(d, "PAUSE_CONT", CURLPAUSE_CONT);

#ifdef HAVE_CURL_7_19_5_OPTS
    /* CURL_SEEKFUNC: return values for seek function */
    insint_c(d, "SEEKFUNC_OK", CURL_SEEKFUNC_OK);
    insint_c(d, "SEEKFUNC_FAIL", CURL_SEEKFUNC_FAIL);
    insint_c(d, "SEEKFUNC_CANTSEEK", CURL_SEEKFUNC_CANTSEEK);
#endif

#ifdef HAVE_CURLOPT_DNS_SERVERS
    insint_c(d, "DNS_SERVERS", CURLOPT_DNS_SERVERS);
#endif

#ifdef HAVE_CURLOPT_POSTREDIR
    insint_c(d, "REDIR_POST_301", CURL_REDIR_POST_301);
    insint_c(d, "REDIR_POST_302", CURL_REDIR_POST_302);
# ifdef HAVE_CURL_REDIR_POST_303
    insint_c(d, "REDIR_POST_303", CURL_REDIR_POST_303);
# endif
    insint_c(d, "REDIR_POST_ALL", CURL_REDIR_POST_ALL);
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
    curlmultiobject_constants = PyDict_New();
    assert(curlmultiobject_constants != NULL);
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
    insint_s(d, "LOCK_DATA_SSL_SESSION", CURL_LOCK_DATA_SSL_SESSION);

    /* Initialize callback locks if ssl is enabled */
#if defined(PYCURL_NEED_SSL_TSL)
    pycurl_ssl_init();
#endif

#ifdef WITH_THREAD
    /* Finally initialize global interpreter lock */
    PyEval_InitThreads();
#endif

#if PY_MAJOR_VERSION >= 3
    return m;
#endif
}
