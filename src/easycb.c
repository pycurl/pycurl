#include "pycurl.h"


/* IMPORTANT NOTE: due to threading issues, we cannot call _any_ Python
 * function without acquiring the thread state in the callback handlers.
 */

#define PYCURL_BEGIN_CALLBACK(callback_name, retval) \
    PYCURL_BEGIN_CALLBACK_COMMON(PYCURL_ACQUIRE_THREAD(), retval, callback_name)

static int
callback_return_value_to_int(PyObject *ret_obj, const char *callback_name, int *ret_out)
{
    if (ret_obj == NULL) {
        return -1;
    }
    if (!PyLong_Check(ret_obj)) {
        PyObject *ret_repr = PyObject_Repr(ret_obj);
        if (ret_repr) {
            PyObject *encoded_obj;
            char *str = PyText_AsString_NoNUL(ret_repr, &encoded_obj);
            fprintf(stderr, "%s callback returned %s which is not an integer\n", callback_name, str);
            Py_XDECREF(encoded_obj);
            Py_DECREF(ret_repr);
        }
        return -1;
    }
    *ret_out = (int) PyLong_AsLong(ret_obj);
    return 0;
}


static size_t
util_write_callback(int flags, char *ptr, size_t size, size_t nmemb, void *stream)
{
    CurlObject *self;
    PyObject *arglist;
    PyObject *result = NULL;
    size_t ret = 0;     /* assume error */
    PyObject *cb;
    Py_ssize_t total_size;
    int track_ws_write_callback;
    int prev_ws_write_callback = 0;
    PYCURL_DECLARE_THREAD_STATE;

    /* acquire thread */
    self = (CurlObject *)stream;

    PYCURL_BEGIN_CALLBACK(util_write_callback, ret);

    /* check args */
    cb = flags ? self->h_cb : self->w_cb;
    if (cb == NULL)
        goto silent_error;
    if (size <= 0 || nmemb <= 0)
        goto done;
    total_size = (Py_ssize_t)(size * nmemb);
    if (total_size < 0 || (size_t)total_size / size != nmemb) {
        PyErr_SetString(ErrorObject, "integer overflow in write callback");
        goto verbose_error;
    }

    /* run callback */
    arglist = Py_BuildValue("(y#)", ptr, total_size);
    if (arglist == NULL)
        goto verbose_error;
    track_ws_write_callback = (flags == 0);
    if (track_ws_write_callback) {
        prev_ws_write_callback = self->ws_write_cb_running;
        self->ws_write_cb_running = 1;
    }
    result = PyObject_Call(cb, arglist, NULL);
    if (track_ws_write_callback) {
        self->ws_write_cb_running = prev_ws_write_callback;
    }
    Py_DECREF(arglist);
    if (result == NULL)
        goto verbose_error;

    /* handle result */
    if (result == Py_None) {
        ret = total_size;           /* None means success */
    }
    else if (PyLong_Check(result)) {
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
    PYCURL_END_CALLBACK(ret);
verbose_error:
    print_callback_error_if_regular_exception();
    goto silent_error;
}


PYCURL_INTERNAL size_t
write_callback(char *ptr, size_t size, size_t nmemb, void *stream)
{
    return util_write_callback(0, ptr, size, nmemb, stream);
}

PYCURL_INTERNAL size_t
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
            char *addr_str = PyMem_New(char, INET_ADDRSTRLEN);

            if (addr_str == NULL) {
                PyErr_NoMemory();
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
            char *addr_str = PyMem_New(char, INET6_ADDRSTRLEN);

            if (addr_str == NULL) {
                PyErr_NoMemory();
                goto error;
            }

            if (inet_ntop(saddr->sa_family, &sin6->sin6_addr, addr_str, INET6_ADDRSTRLEN) == NULL) {
                PyErr_SetFromErrno(ErrorObject);
                PyMem_Free(addr_str);
                goto error;
            }
            res_obj = Py_BuildValue("(siii)", addr_str, (int) ntohs(sin6->sin6_port),
                (int) ntohl(sin6->sin6_flowinfo), (int) ntohl(sin6->sin6_scope_id));
            PyMem_Free(addr_str);
        }
        break;
#if !defined(WIN32)
    case AF_UNIX:
        {
            struct sockaddr_un* s_un = (struct sockaddr_un*)saddr;

            res_obj = Py_BuildValue("y", s_un->sun_path);
        }
        break;
#endif
    default:
        /* We (currently) only support IPv4/6 addresses.  Can curl even be used
           with anything else? */
        PyErr_SetString(ErrorObject, "Unsupported address family");
    }

error:
    return res_obj;
}


/* curl_socket_t is not always an int (e.g. SOCKET on Win64), so keep
 * conversions explicit to avoid truncation. */
PYCURL_INTERNAL curl_socket_t
opensocket_callback(void *clientp, curlsocktype purpose,
                    struct curl_sockaddr *address)
{
    PyObject *arglist;
    PyObject *result = NULL;
    PyObject *fileno_result = NULL;
    CurlObject *self;
    curl_socket_t ret = CURL_SOCKET_BAD;
    PyObject *converted_address;
    PyObject *python_address;
    PYCURL_DECLARE_THREAD_STATE;

    self = (CurlObject *)clientp;
    
    PYCURL_BEGIN_CALLBACK(opensocket_callback, ret);

    converted_address = convert_protocol_address(&address->addr, address->addrlen);
    if (converted_address == NULL) {
        goto verbose_error;
    }

    arglist = Py_BuildValue("(iiiN)", address->family, address->socktype, address->protocol, converted_address);
    if (arglist == NULL) {
        Py_DECREF(converted_address);
        goto verbose_error;
    }
    python_address = PyObject_Call(curl_sockaddr_type, arglist, NULL);
    Py_DECREF(arglist);
    if (python_address == NULL) {
        goto verbose_error;
    }

    arglist = Py_BuildValue("(iN)", purpose, python_address);
    if (arglist == NULL) {
        Py_DECREF(python_address);
        goto verbose_error;
    }
    result = PyObject_Call(self->opensocket_cb, arglist, NULL);
    Py_DECREF(arglist);
    if (result == NULL) {
        goto verbose_error;
    }

    if (PyLong_Check(result)) {
        curl_socket_t sock_fd;
        if (PyLong_AsCurlSocket(result, &sock_fd) == 0) {
            ret = sock_fd;
            goto done;
        }
        /* PyLong_AsCurlSocket sets an exception on failure */
        ret = CURL_SOCKET_BAD;
        goto verbose_error;
    } else {
        PyObject *fileno_method = PyObject_GetAttrString(result, "fileno");
        if (fileno_method == NULL) {
            if (PyErr_ExceptionMatches(PyExc_AttributeError)) {
                PyErr_Clear();
                PyErr_SetString(ErrorObject, "Open socket callback's return value must be a socket");
            }
            ret = CURL_SOCKET_BAD;
            goto verbose_error;
        }
        Py_DECREF(fileno_method);

        fileno_result = PyObject_CallMethod(result, "fileno", NULL);

        if (fileno_result == NULL) {
            ret = CURL_SOCKET_BAD;
            goto verbose_error;
        }
        if (PyLong_Check(fileno_result)) {
            curl_socket_t sock_fd;
            if (PyLong_AsCurlSocket(fileno_result, &sock_fd) != 0) {
                ret = CURL_SOCKET_BAD;
                goto verbose_error;
            }
#if defined(WIN32)
            ret = dup_winsock(sock_fd, address);
#else
            ret = dup((int) sock_fd);
#endif
            goto done;
        } else {
            PyErr_SetString(ErrorObject, "Open socket callback returned an object whose fileno method did not return an integer");
            ret = CURL_SOCKET_BAD;
        }
    }

silent_error:
done:
    Py_XDECREF(result);
    Py_XDECREF(fileno_result);
    PYCURL_END_CALLBACK(ret);
verbose_error:
    print_callback_error_if_regular_exception();
    goto silent_error;
}


PYCURL_INTERNAL int
sockopt_cb(void *clientp, curl_socket_t curlfd, curlsocktype purpose)
{
    PyObject *arglist;
    PyObject *py_curlfd = NULL;
    CurlObject *self;
    int ret = CURL_SOCKOPT_ERROR;
    PyObject *ret_obj = NULL;
    PYCURL_DECLARE_THREAD_STATE;

    self = (CurlObject *)clientp;

    PYCURL_BEGIN_CALLBACK(sockopt_cb, ret);

    py_curlfd = PyLong_FromCurlSocket(curlfd);
    if (py_curlfd == NULL) {
        goto verbose_error;
    }
    arglist = Py_BuildValue("(Oi)", py_curlfd, (int) purpose);
    Py_DECREF(py_curlfd);
    if (arglist == NULL) {
        goto verbose_error;
    }

    ret_obj = PyObject_Call(self->sockopt_cb, arglist, NULL);
    Py_DECREF(arglist);
    if (callback_return_value_to_int(ret_obj, "sockopt", &ret) != 0) {
        goto silent_error;
    }
    goto done;

silent_error:
    ret = -1;
done:
    Py_XDECREF(ret_obj);
    PYCURL_END_CALLBACK(ret);
verbose_error:
    print_callback_error_if_regular_exception();
    goto silent_error;
}


#if LIBCURL_VERSION_NUM >= MAKE_LIBCURL_VERSION(7, 21, 7)
PYCURL_INTERNAL int
closesocket_callback(void *clientp, curl_socket_t curlfd)
{
    PyObject *arglist;
    PyObject *py_curlfd = NULL;
    CurlObject *self;
    int ret = 1;
    PyObject *ret_obj = NULL;
    PYCURL_DECLARE_THREAD_STATE;

    self = (CurlObject *)clientp;

    PYCURL_BEGIN_CALLBACK(closesocket_callback, ret);

    py_curlfd = PyLong_FromCurlSocket(curlfd);
    if (py_curlfd == NULL) {
        goto verbose_error;
    }
    arglist = Py_BuildValue("(O)", py_curlfd);
    Py_DECREF(py_curlfd);
    if (arglist == NULL) {
        goto verbose_error;
    }

    ret_obj = PyObject_Call(self->closesocket_cb, arglist, NULL);
    Py_DECREF(arglist);
    if (callback_return_value_to_int(ret_obj, "closesocket", &ret) != 0) {
        goto silent_error;
    }
    goto done;

silent_error:
    ret = -1;
done:
    Py_XDECREF(ret_obj);
    PYCURL_END_CALLBACK(ret);
verbose_error:
    print_callback_error_if_regular_exception();
    goto silent_error;
}
#endif


#ifdef HAVE_CURL_7_19_6_OPTS
static PyObject *
khkey_to_object(const struct curl_khkey *khkey)
{
    PyObject *arglist, *ret;

    if (khkey == NULL) {
        Py_INCREF(Py_None);
        return Py_None;
    }

    if (khkey->len) {
        arglist = Py_BuildValue("(y#i)", khkey->key, khkey->len, khkey->keytype);
    } else {
        arglist = Py_BuildValue("(yi)", khkey->key, khkey->keytype);
    }

    if (arglist == NULL) {
        return NULL;
    }

    ret = PyObject_Call(khkey_type, arglist, NULL);
    Py_DECREF(arglist);
    return ret;
}


PYCURL_INTERNAL int
ssh_key_cb(CURL *easy, const struct curl_khkey *knownkey,
           const struct curl_khkey *foundkey, enum curl_khmatch khmatch,
           void *clientp)
{
    PyObject *arglist;
    CurlObject *self;
    int ret = CURLKHSTAT_REJECT;
    PyObject *knownkey_obj = NULL;
    PyObject *foundkey_obj = NULL;
    PyObject *ret_obj = NULL;
    PYCURL_DECLARE_THREAD_STATE;

    self = (CurlObject *)clientp;

    PYCURL_BEGIN_CALLBACK(ssh_key_cb, ret);

    knownkey_obj = khkey_to_object(knownkey);
    if (knownkey_obj == NULL) {
        goto silent_error;
    }
    foundkey_obj = khkey_to_object(foundkey);
    if (foundkey_obj == NULL) {
        goto silent_error;
    }

    arglist = Py_BuildValue("(OOi)", knownkey_obj, foundkey_obj, khmatch);
    if (arglist == NULL)
        goto verbose_error;

    ret_obj = PyObject_Call(self->ssh_key_cb, arglist, NULL);
    Py_DECREF(arglist);
    if (callback_return_value_to_int(ret_obj, "ssh key", &ret) != 0) {
        goto silent_error;
    }
    goto done;

silent_error:
    ret = -1;
done:
    Py_XDECREF(knownkey_obj);
    Py_XDECREF(foundkey_obj);
    Py_XDECREF(ret_obj);
    PYCURL_END_CALLBACK(ret);
verbose_error:
    print_callback_error_if_regular_exception();
    goto silent_error;
}
#endif


PYCURL_INTERNAL int
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

    PYCURL_BEGIN_CALLBACK(seek_callback, ret);

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
    arglist = Py_BuildValue("(L,i)", (PY_LONG_LONG) offset, source);
    if (arglist == NULL)
        goto verbose_error;
    result = PyObject_Call(cb, arglist, NULL);
    Py_DECREF(arglist);
    if (result == NULL)
        goto verbose_error;

    /* handle result */
    if (result == Py_None) {
        ret = 0;           /* None means success */
    }
    else if (PyLong_Check(result)) {
        int ret_code = PyLong_AsLong(result);
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
    PYCURL_END_CALLBACK(ret);
verbose_error:
    print_callback_error_if_regular_exception();
    goto silent_error;
}




PYCURL_INTERNAL size_t
read_callback(char *ptr, size_t size, size_t nmemb, void *stream)
{
    CurlObject *self;
    PyObject *arglist;
    PyObject *result = NULL;
    Py_buffer buf;

    size_t ret = CURL_READFUNC_ABORT;     /* assume error, this actually works */
    Py_ssize_t total_size;

    PYCURL_DECLARE_THREAD_STATE;

    /* acquire thread */
    self = (CurlObject *)stream;

    PYCURL_BEGIN_CALLBACK(read_callback, ret);

    /* check args */
    if (self->r_cb == NULL)
        goto silent_error;
    if (size <= 0 || nmemb <= 0)
        goto done;
    total_size = (Py_ssize_t)(size * nmemb);
    if (total_size < 0 || (size_t)total_size / size != nmemb) {
        PyErr_SetString(ErrorObject, "integer overflow in read callback");
        goto verbose_error;
    }

    /* run callback */
    arglist = Py_BuildValue("(i)", total_size);
    if (arglist == NULL)
        goto verbose_error;
    result = PyObject_Call(self->r_cb, arglist, NULL);
    Py_DECREF(arglist);
    if (result == NULL)
        goto verbose_error;

    /* handle result */
    if (PyUnicode_Check(result)) {
        char *buf = NULL;
        Py_ssize_t obj_size = -1;
        Py_ssize_t r;
        /*
        Encode with ascii codec.

        HTTP requires sending content-length for request body to the server
        before the request body is sent, therefore typically content length
        is given via POSTFIELDSIZE before read function is invoked to
        provide the data.

        However, if we encode the string using any encoding other than ascii,
        the length of encoded string may not match the length of unicode
        string we are encoding. Therefore, if client code does a simple
        len(source_string) to determine the value to supply in content-length,
        the length of bytes read may be different.

        To avoid this situation, we only accept ascii bytes in the string here.

        Encode data yourself to bytes when dealing with non-ascii data.
        */
        PyObject *encoded = PyUnicode_AsEncodedString(result, "ascii", "strict");
        if (encoded == NULL) {
            goto verbose_error;
        }
        r = PyBytes_AsStringAndSize(encoded, &buf, &obj_size);
        if (r != 0 || obj_size < 0 || obj_size > total_size) {
            Py_DECREF(encoded);
            PyErr_Format(ErrorObject, "invalid return value for read callback (%ld bytes returned after encoding to ascii when at most %ld bytes were wanted)", (long)obj_size, (long)total_size);
            goto verbose_error;
        }
        memcpy(ptr, buf, obj_size);
        Py_DECREF(encoded);
        ret = obj_size;             /* success */
    }
    else if (PyObject_CheckBuffer(result)) {
        if (PyObject_GetBuffer(result, &buf, PyBUF_SIMPLE) != 0) {
            goto verbose_error;
        }
        if (buf.len < 0 || buf.len > total_size) {
            PyErr_Format(ErrorObject, "invalid return value for read callback (%ld bytes returned when at most %ld bytes were wanted)", (long)buf.len, (long)total_size);
            PyBuffer_Release(&buf);
            goto verbose_error;
        }
        memcpy(ptr, buf.buf, (size_t)buf.len);
        ret = buf.len;              /* success */
        PyBuffer_Release(&buf);
    }
    else if (PyLong_Check(result)) {
        long r = PyLong_AsLong(result);
        if (r != CURL_READFUNC_ABORT && r != CURL_READFUNC_PAUSE)
            goto type_error;
        ret = r; /* either CURL_READFUNC_ABORT or CURL_READFUNC_PAUSE */
    }
    else {
    type_error:
        PyErr_SetString(ErrorObject, "read callback must return an object supporting the buffer protocol (e.g. a byte string) or an ASCII-only Unicode string");
        goto verbose_error;
    }

done:
silent_error:
    Py_XDECREF(result);
    PYCURL_END_CALLBACK(ret);
verbose_error:
    print_callback_error_if_regular_exception();
    goto silent_error;
}


PYCURL_INTERNAL int
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

    PYCURL_BEGIN_CALLBACK(progress_callback, ret);

    /* check args */
    if (self->pro_cb == NULL)
        goto silent_error;

    /* run callback */
    arglist = Py_BuildValue("(dddd)", dltotal, dlnow, ultotal, ulnow);
    if (arglist == NULL)
        goto verbose_error;
    result = PyObject_Call(self->pro_cb, arglist, NULL);
    Py_DECREF(arglist);
    if (result == NULL)
        goto verbose_error;

    /* handle result */
    if (result == Py_None) {
        ret = 0;        /* None means success */
    }
    else if (PyLong_Check(result)) {
        ret = (int) PyLong_AsLong(result);
    }
    else {
        ret = PyObject_IsTrue(result);  /* FIXME ??? */
    }

silent_error:
    Py_XDECREF(result);
    PYCURL_END_CALLBACK(ret);
verbose_error:
    print_callback_error_if_regular_exception();
    goto silent_error;
}


#if LIBCURL_VERSION_NUM >= MAKE_LIBCURL_VERSION(7, 32, 0)
PYCURL_INTERNAL int
xferinfo_callback(void *stream,
    curl_off_t dltotal, curl_off_t dlnow,
    curl_off_t ultotal, curl_off_t ulnow)
{
    CurlObject *self;
    PyObject *arglist;
    PyObject *result = NULL;
    int ret = 1;       /* assume error */
    PYCURL_DECLARE_THREAD_STATE;

    /* acquire thread */
    self = (CurlObject *)stream;

    PYCURL_BEGIN_CALLBACK(xferinfo_callback, ret);

    /* check args */
    if (self->xferinfo_cb == NULL)
        goto silent_error;

    /* run callback */
    arglist = Py_BuildValue("(LLLL)",
        (PY_LONG_LONG) dltotal, (PY_LONG_LONG) dlnow,
        (PY_LONG_LONG) ultotal, (PY_LONG_LONG) ulnow);
    if (arglist == NULL)
        goto verbose_error;
    result = PyObject_Call(self->xferinfo_cb, arglist, NULL);
    Py_DECREF(arglist);
    if (result == NULL)
        goto verbose_error;

    /* handle result */
    if (result == Py_None) {
        ret = 0;        /* None means success */
    }
    else if (PyLong_Check(result)) {
        ret = (int) PyLong_AsLong(result);
    }
    else {
        ret = PyObject_IsTrue(result);  /* FIXME ??? */
    }

silent_error:
    Py_XDECREF(result);
    PYCURL_END_CALLBACK(ret);
verbose_error:
    print_callback_error_if_regular_exception();
    goto silent_error;
}
#endif


PYCURL_INTERNAL int
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

    PYCURL_BEGIN_CALLBACK(debug_callback, ret);

    /* check args */
    if (self->debug_cb == NULL)
        goto silent_error;
    if ((int)total_size < 0 || (size_t)((int)total_size) != total_size) {
        PyErr_SetString(ErrorObject, "integer overflow in debug callback");
        goto verbose_error;
    }

    /* run callback */
    arglist = Py_BuildValue("(iy#)", (int)type, buffer, (int)total_size);
    if (arglist == NULL)
        goto verbose_error;
    result = PyObject_Call(self->debug_cb, arglist, NULL);
    Py_DECREF(arglist);
    if (result == NULL)
        goto verbose_error;

    /* return values from debug callbacks should be ignored */

silent_error:
    Py_XDECREF(result);
    PYCURL_END_CALLBACK(ret);
verbose_error:
    print_callback_error_if_regular_exception();
    goto silent_error;
}


PYCURL_INTERNAL curlioerr
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

    PYCURL_BEGIN_CALLBACK(ioctl_callback, (curlioerr)ret);

    /* check args */
    if (self->ioctl_cb == NULL)
        goto silent_error;

    /* run callback */
    arglist = Py_BuildValue("(i)", cmd);
    if (arglist == NULL)
        goto verbose_error;
    result = PyObject_Call(self->ioctl_cb, arglist, NULL);
    Py_DECREF(arglist);
    if (result == NULL)
        goto verbose_error;

    /* handle result */
    if (result == Py_None) {
        ret = CURLIOE_OK;        /* None means success */
    }
    else if (PyLong_Check(result)) {
        ret = (int) PyLong_AsLong(result);
        if (ret >= CURLIOE_LAST || ret < 0) {
            PyErr_SetString(ErrorObject, "ioctl callback returned invalid value");
            goto verbose_error;
        }
    }

silent_error:
    Py_XDECREF(result);
    PYCURL_END_CALLBACK((curlioerr) ret);
verbose_error:
    print_callback_error_if_regular_exception();
    goto silent_error;
}


#if defined(HAVE_CURL_OPENSSL)
/* internal helper that load certificates from buffer, returns -1 on error  */
static int
add_ca_certs(SSL_CTX *context, void *data, Py_ssize_t len)
{
    // this code was copied from _ssl module
    BIO *biobuf = NULL;
    X509_STORE *store;
    int retval = 0, err, loaded = 0;

    if (len <= 0) {
        PyErr_SetString(PyExc_ValueError,
                        "Empty certificate data");
        return -1;
    } else if (len > INT_MAX) {
        PyErr_SetString(PyExc_OverflowError,
                        "Certificate data is too long.");
        return -1;
    }

    biobuf = BIO_new_mem_buf(data, (int)len);
    if (biobuf == NULL) {
        PyErr_SetString(PyExc_MemoryError, "Can't allocate buffer");
        ERR_clear_error();
        return -1;
    }

    store = SSL_CTX_get_cert_store(context);
    assert(store != NULL);

    while (1) {
        X509 *cert = NULL;
        int r;

        cert = PEM_read_bio_X509(biobuf, NULL, 0, NULL);
        if (cert == NULL) {
            break;
        }
        r = X509_STORE_add_cert(store, cert);
        X509_free(cert);
        if (!r) {
            err = ERR_peek_last_error();
            if ((ERR_GET_LIB(err) == ERR_LIB_X509) &&
                (ERR_GET_REASON(err) == X509_R_CERT_ALREADY_IN_HASH_TABLE)) {
                /* cert already in hash table, not an error */
                ERR_clear_error();
            } else {
                break;
            }
        }
        loaded++;
    }

    err = ERR_peek_last_error();
    if ((loaded > 0) &&
            (ERR_GET_LIB(err) == ERR_LIB_PEM) &&
            (ERR_GET_REASON(err) == PEM_R_NO_START_LINE)) {
        /* EOF PEM file, not an error */
        ERR_clear_error();
        retval = 0;
    } else {
        PyErr_SetString(ErrorObject, ERR_reason_error_string(err));
        ERR_clear_error();
        retval = -1;
    }

    BIO_free(biobuf);
    return retval;
}


PYCURL_INTERNAL CURLcode
ssl_ctx_callback(CURL *curl, void *ssl_ctx, void *ptr)
{
    CurlObject *self;
    PYCURL_DECLARE_THREAD_STATE;
    int r;

    UNUSED(curl);

    /* acquire thread */
    self = (CurlObject *)ptr;

    PYCURL_BEGIN_CALLBACK(ssl_ctx_callback, CURLE_FAILED_INIT);

    r = add_ca_certs((SSL_CTX*)ssl_ctx,
                         PyBytes_AS_STRING(self->ca_certs_obj),
                         PyBytes_GET_SIZE(self->ca_certs_obj));

    if (r != 0)
        print_callback_error_if_regular_exception();

    PYCURL_END_CALLBACK(r == 0 ? CURLE_OK : CURLE_FAILED_INIT);
}
#endif


#if LIBCURL_VERSION_NUM >= MAKE_LIBCURL_VERSION(7, 80, 0)
PYCURL_INTERNAL int
prereq_callback(void *clientp, char *conn_primary_ip, char *conn_local_ip,
                int conn_primary_port, int conn_local_port)
{
    PyObject *arglist;
    CurlObject *self;
    int ret = CURL_PREREQFUNC_ABORT;
    PyObject *ret_obj = NULL;
    PYCURL_DECLARE_THREAD_STATE;

    self = (CurlObject *)clientp;

    PYCURL_BEGIN_CALLBACK(prereq_callback, ret);

    arglist = Py_BuildValue("(ssii)", conn_primary_ip, conn_local_ip, conn_primary_port, conn_local_port);
    if (arglist == NULL)
        goto verbose_error;

    ret_obj = PyObject_Call(self->prereq_cb, arglist, NULL);
    Py_DECREF(arglist);
    if (callback_return_value_to_int(ret_obj, "prereq", &ret) != 0) {
        goto silent_error;
    }
    goto done;

silent_error:
    ret = -1;
done:
    Py_XDECREF(ret_obj);
    PYCURL_END_CALLBACK(ret);
verbose_error:
    print_callback_error_if_regular_exception();
    goto silent_error;
}
#endif


#if LIBCURL_VERSION_NUM >= MAKE_LIBCURL_VERSION(7, 21, 0)
PYCURL_INTERNAL int
fnmatch_callback(void *clientp, const char *pattern, const char *string)
{
    PyObject *arglist;
    CurlObject *self;
    int ret = CURL_FNMATCHFUNC_FAIL;
    PyObject *ret_obj = NULL;
    PYCURL_DECLARE_THREAD_STATE;

    self = (CurlObject *)clientp;

    PYCURL_BEGIN_CALLBACK(fnmatch_callback, ret);

    arglist = Py_BuildValue("(yy)", pattern, string);
    if (arglist == NULL) {
        goto verbose_error;
    }

    ret_obj = PyObject_Call(self->fnmatch_cb, arglist, NULL);
    Py_DECREF(arglist);
    if (callback_return_value_to_int(ret_obj, "fnmatch", &ret) != 0) {
        goto silent_error;
    }
    goto done;

silent_error:
    ret = CURL_FNMATCHFUNC_FAIL;
done:
    Py_XDECREF(ret_obj);
    PYCURL_END_CALLBACK(ret);
verbose_error:
    print_callback_error_if_regular_exception();
    goto silent_error;
}
#endif


#if LIBCURL_VERSION_NUM >= MAKE_LIBCURL_VERSION(7, 59, 0)
PYCURL_INTERNAL int
resolver_start_callback(void *resolver_state, void *reserved, void *clientp)
{
    CurlObject *self;
    int ret = 1;  /* non-zero aborts */
    PyObject *ret_obj = NULL;
    PYCURL_DECLARE_THREAD_STATE;

    UNUSED(resolver_state);
    UNUSED(reserved);

    self = (CurlObject *)clientp;

    PYCURL_BEGIN_CALLBACK(resolver_start_callback, ret);

    ret_obj = PyObject_CallNoArgs(self->resolver_start_cb);
    if (ret_obj == NULL) {
        goto verbose_error;
    }
    if (ret_obj == Py_None) {
        ret = 0;
    } else if (callback_return_value_to_int(ret_obj, "resolver_start", &ret) != 0) {
        goto silent_error;
    }
    goto done;

silent_error:
    ret = 1;
done:
    Py_XDECREF(ret_obj);
    PYCURL_END_CALLBACK(ret);
verbose_error:
    print_callback_error_if_regular_exception();
    goto silent_error;
}
#endif


#if LIBCURL_VERSION_NUM >= MAKE_LIBCURL_VERSION(7, 64, 0)
PYCURL_INTERNAL int
trailer_callback(struct curl_slist **list, void *clientp)
{
    CurlObject *self;
    int ret = CURL_TRAILERFUNC_ABORT;
    PyObject *ret_obj = NULL;
    PYCURL_DECLARE_THREAD_STATE;

    self = (CurlObject *)clientp;

    /* Initialise early: libcurl passes an uninitialised pointer on entry. */
    *list = NULL;

    PYCURL_BEGIN_CALLBACK(trailer_callback, ret);

    ret_obj = PyObject_CallNoArgs(self->trailer_cb);
    if (ret_obj == NULL) {
        goto verbose_error;
    }

    if (ret_obj == Py_None) {
        ret = CURL_TRAILERFUNC_OK;
        goto done;
    }

    if (PyList_Check(ret_obj) || PyTuple_Check(ret_obj)) {
        int which = PyList_Check(ret_obj) ? PYLISTORTUPLE_LIST : PYLISTORTUPLE_TUPLE;
        Py_ssize_t len = PyListOrTuple_Size(ret_obj, which);
        /* pycurl_list_or_tuple_to_slist frees any partial slist on error,
         * so we never own a non-NULL slist once it returns. An empty
         * list yields a NULL slist with no error set. */
        *list = pycurl_list_or_tuple_to_slist(which, ret_obj, len);
        if (*list == NULL && PyErr_Occurred()) {
            goto verbose_error;
        }
        ret = CURL_TRAILERFUNC_OK;
        goto done;
    }

    PyErr_SetString(ErrorObject, "trailer callback must return None or a list/tuple of header strings");
    goto verbose_error;

silent_error:
    ret = CURL_TRAILERFUNC_ABORT;
done:
    Py_XDECREF(ret_obj);
    PYCURL_END_CALLBACK(ret);
verbose_error:
    *list = NULL;
    print_callback_error_if_regular_exception();
    goto silent_error;
}
#endif


#if LIBCURL_VERSION_NUM >= MAKE_LIBCURL_VERSION(7, 74, 0)

/* Parse libcurl's "YYYYMMDD HH:MM:SS" stamp into a tz-aware
 * datetime(UTC). The sentinel values "" and "unlimited" (used by
 * libcurl for never-expires entries) map to Py_None. Returns a new
 * reference, or NULL with a Python exception set. Parsing is delegated
 * to datetime.strptime with an appended "+0000" so the result is an
 * aware UTC datetime in a single call. */
static PyObject *
expire_c_str_to_datetime(const char *stamp)
{
    char buf[32];
    int written;

    if (stamp[0] == '\0' || strcmp(stamp, "unlimited") == 0) {
        Py_RETURN_NONE;
    }
    written = snprintf(buf, sizeof(buf), "%s+0000", stamp);
    if (written < 0 || (size_t)written >= sizeof(buf)) {
        PyErr_Format(ErrorObject,
            "libcurl returned an unparsable HSTS expire stamp: %s", stamp);
        return NULL;
    }
    return PyObject_CallMethod(datetime_type, "strptime", "ss",
                               buf, "%Y%m%d %H:%M:%S%z");
}


/* Convert a Python value (None or datetime) to libcurl's fixed-size
 * expire buffer. Aware datetimes are normalised to UTC; naive datetimes
 * are interpreted as UTC (documented). Returns 0 on success, -1 with a
 * Python exception set. */
static int
expire_obj_to_c_str(PyObject *obj, char *buf, size_t buf_size)
{
    PyObject *utc_obj = NULL;
    PyObject *tzinfo = NULL;
    PyObject *formatted = NULL;
    Py_ssize_t str_len;
    const char *str;
    int is_datetime;
    int rc = -1;

    if (obj == Py_None) {
        /* Empty stamp = never expires, per libcurl docs. */
        buf[0] = '\0';
        return 0;
    }

    is_datetime = PyObject_IsInstance(obj, datetime_type);
    if (is_datetime < 0) {
        return -1;
    }
    if (!is_datetime) {
        PyErr_SetString(ErrorObject,
            "hstsread callback: expire must be a datetime or None");
        return -1;
    }

    tzinfo = PyObject_GetAttrString(obj, "tzinfo");
    if (tzinfo == NULL) {
        goto cleanup;
    }
    if (tzinfo != Py_None) {
        utc_obj = PyObject_CallMethod(obj, "astimezone", "O", utc_tz);
        if (utc_obj == NULL) {
            goto cleanup;
        }
        obj = utc_obj;
    }

    formatted = PyObject_CallMethod(obj, "strftime", "s", "%Y%m%d %H:%M:%S");
    if (formatted == NULL) {
        goto cleanup;
    }
    str = PyUnicode_AsUTF8AndSize(formatted, &str_len);
    if (str == NULL) {
        goto cleanup;
    }
    if ((size_t)str_len >= buf_size) {
        PyErr_SetString(ErrorObject,
            "hstsread callback: formatted expire does not fit in libcurl's buffer");
        goto cleanup;
    }
    memcpy(buf, str, (size_t)str_len);
    buf[str_len] = '\0';
    rc = 0;

cleanup:
    Py_XDECREF(tzinfo);
    Py_XDECREF(utc_obj);
    Py_XDECREF(formatted);
    return rc;
}


PYCURL_INTERNAL CURLSTScode
hstswrite_callback(CURL *easy, struct curl_hstsentry *e,
                   struct curl_index *i, void *clientp)
{
    CurlObject *self;
    CURLSTScode ret = CURLSTS_FAIL;
    PyObject *expire_obj = NULL;
    PyObject *entry = NULL;
    PyObject *index = NULL;
    PyObject *arglist = NULL;
    PyObject *ret_obj = NULL;
    int raw_ret;
    PYCURL_DECLARE_THREAD_STATE;

    UNUSED(easy);

    self = (CurlObject *)clientp;

    PYCURL_BEGIN_CALLBACK(hstswrite_callback, ret);

    expire_obj = expire_c_str_to_datetime(e->expire);
    if (expire_obj == NULL) {
        goto verbose_error;
    }

    /* HstsEntry(host=bytes, expire=datetime|None, include_subdomains=bool) */
    entry = PyObject_CallFunction(hsts_entry_type, "y#OO",
                                  e->name, (Py_ssize_t)e->namelen,
                                  expire_obj,
                                  e->includeSubDomains ? Py_True : Py_False);
    Py_DECREF(expire_obj);
    expire_obj = NULL;
    if (entry == NULL) {
        goto verbose_error;
    }

    /* HstsIndex(index=int, total=int) */
    index = PyObject_CallFunction(hsts_index_type, "nn",
                                  (Py_ssize_t)i->index, (Py_ssize_t)i->total);
    if (index == NULL) {
        goto verbose_error;
    }

    arglist = PyTuple_Pack(2, entry, index);
    if (arglist == NULL) {
        goto verbose_error;
    }

    ret_obj = PyObject_Call(self->hstswrite_cb, arglist, NULL);
    Py_CLEAR(arglist);
    if (ret_obj == NULL) {
        goto verbose_error;
    }
    if (ret_obj == Py_None) {
        ret = CURLSTS_OK;
        goto done;
    }
    if (callback_return_value_to_int(ret_obj, "hstswrite", &raw_ret) != 0) {
        goto silent_error;
    }
    if (raw_ret < 0 || raw_ret > CURLSTS_FAIL) {
        PyErr_SetString(ErrorObject, "hstswrite callback returned an invalid CURLSTScode");
        goto verbose_error;
    }
    ret = (CURLSTScode)raw_ret;
    goto done;

silent_error:
    ret = CURLSTS_FAIL;
done:
    Py_XDECREF(entry);
    Py_XDECREF(index);
    Py_XDECREF(ret_obj);
    PYCURL_END_CALLBACK(ret);
verbose_error:
    Py_XDECREF(expire_obj);
    Py_XDECREF(arglist);
    print_callback_error_if_regular_exception();
    goto silent_error;
}


PYCURL_INTERNAL CURLSTScode
hstsread_callback(CURL *easy, struct curl_hstsentry *e, void *clientp)
{
    CurlObject *self;
    CURLSTScode ret = CURLSTS_FAIL;
    PyObject *ret_obj = NULL;
    PyObject *host_obj = NULL;
    PyObject *expire_obj = NULL;
    PyObject *include_obj = NULL;
    PyObject *host_encoded = NULL;
    char *host_buf = NULL;
    Py_ssize_t host_len = 0;
    int include_subdomains;
    PYCURL_DECLARE_THREAD_STATE;

    UNUSED(easy);

    self = (CurlObject *)clientp;

    PYCURL_BEGIN_CALLBACK(hstsread_callback, ret);

    ret_obj = PyObject_CallNoArgs(self->hstsread_cb);
    if (ret_obj == NULL) {
        goto verbose_error;
    }

    if (ret_obj == Py_None) {
        ret = CURLSTS_DONE;
        goto done;
    }

    /* Accept HstsEntry (namedtuple) or any 3-tuple. */
    if (!PyTuple_Check(ret_obj) || PyTuple_GET_SIZE(ret_obj) != 3) {
        PyErr_SetString(ErrorObject,
            "hstsread callback must return None or a 3-tuple (host, expire, include_subdomains)");
        goto verbose_error;
    }

    host_obj = PyTuple_GET_ITEM(ret_obj, 0);
    expire_obj = PyTuple_GET_ITEM(ret_obj, 1);
    include_obj = PyTuple_GET_ITEM(ret_obj, 2);

    if (PyText_AsStringAndSize(host_obj, &host_buf, &host_len, &host_encoded) != 0) {
        goto verbose_error;
    }

    /* e->namelen is the max hostname length libcurl accepts (the
     * backing buffer is e->namelen + 1 bytes, leaving room for the
     * null terminator we write at position host_len). */
    if ((size_t)host_len > e->namelen) {
        PyErr_Format(ErrorObject,
            "hstsread callback: host length %zd exceeds libcurl maximum %zu",
            host_len, (size_t)e->namelen);
        goto verbose_error;
    }

    if (expire_obj_to_c_str(expire_obj, e->expire, sizeof(e->expire)) != 0) {
        goto verbose_error;
    }

    include_subdomains = PyObject_IsTrue(include_obj);
    if (include_subdomains < 0) {
        goto verbose_error;
    }

    memcpy(e->name, host_buf, (size_t)host_len);
    e->name[host_len] = '\0';
    e->namelen = (size_t)host_len;
    e->includeSubDomains = include_subdomains ? 1 : 0;

    ret = CURLSTS_OK;
    goto done;

silent_error:
    ret = CURLSTS_FAIL;
done:
    Py_XDECREF(host_encoded);
    Py_XDECREF(ret_obj);
    PYCURL_END_CALLBACK(ret);
verbose_error:
    print_callback_error_if_regular_exception();
    goto silent_error;
}
#endif

#undef PYCURL_BEGIN_CALLBACK
