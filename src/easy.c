#include "pycurl.h"
#include "docstrings.h"

/*************************************************************************
// static utility functions
**************************************************************************/


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
            v = PyText_FromString(slist->data);
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


static struct curl_slist *
pycurl_list_or_tuple_to_slist(int which, PyObject *obj, Py_ssize_t len)
{
    struct curl_slist *slist = NULL;
    Py_ssize_t i;

    for (i = 0; i < len; i++) {
        PyObject *listitem = PyListOrTuple_GetItem(obj, i, which);
        struct curl_slist *nlist;
        char *str;
        PyObject *sencoded_obj;

        if (!PyText_Check(listitem)) {
            curl_slist_free_all(slist);
            PyErr_SetString(PyExc_TypeError, "list items must be byte strings or Unicode strings with ASCII code points only");
            return NULL;
        }
        /* INFO: curl_slist_append() internally does strdup() the data, so
         * no embedded NUL characters allowed here. */
        str = PyText_AsString_NoNUL(listitem, &sencoded_obj);
        if (str == NULL) {
            curl_slist_free_all(slist);
            return NULL;
        }
        nlist = curl_slist_append(slist, str);
        PyText_EncodedDecref(sencoded_obj);
        if (nlist == NULL || nlist->data == NULL) {
            curl_slist_free_all(slist);
            PyErr_NoMemory();
            return NULL;
        }
        slist = nlist;
    }
    return slist;
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
                    field_tuple = PyText_FromString(field);
                } else {
                    /* XXX check */
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

/* assert some CurlObject invariants */
PYCURL_INTERNAL void
assert_curl_state(const CurlObject *self)
{
    assert(self != NULL);
    assert(Py_TYPE(self) == p_Curl_Type);
#ifdef WITH_THREAD
    (void) pycurl_get_thread_state(self);
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
    if ((flags & 2) && pycurl_get_thread_state(self) != NULL) {
        PyErr_Format(ErrorObject, "cannot invoke %s() - perform() is currently running", name);
        return -1;
    }
#endif
    return 0;
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
#endif


/*************************************************************************
// CurlObject
**************************************************************************/

/* --------------- construct/destruct (i.e. open/close) --------------- */

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
    assert(g_pycurl_useragent);
    res = curl_easy_setopt(self->handle, CURLOPT_USERAGENT, g_pycurl_useragent);
    if (res != CURLE_OK) {
        return (-1);
    }
    return (0);
}

/* constructor */
PYCURL_INTERNAL CurlObject *
do_curl_new(PyTypeObject *subtype, PyObject *args, PyObject *kwds)
{
    CurlObject *self;
    int res;
    int *ptr;

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "", empty_keywords)) {
        return NULL;
    }

    /* Allocate python curl object */
    self = (CurlObject *) p_Curl_Type->tp_alloc(p_Curl_Type, 0);
    if (self == NULL)
        return NULL;

    /* tp_alloc is expected to return zeroed memory */
    for (ptr = (int *) &self->dict;
        ptr < (int *) (((char *) self) + sizeof(CurlObject));
        ++ptr)
            assert(*ptr == 0);

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
        Py_CLEAR(self->dict);
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
        Py_CLEAR(self->w_cb);
        Py_CLEAR(self->h_cb);
        Py_CLEAR(self->r_cb);
        Py_CLEAR(self->pro_cb);
#if LIBCURL_VERSION_NUM >= MAKE_LIBCURL_VERSION(7, 32, 0)
        Py_CLEAR(self->xferinfo_cb);
#endif
        Py_CLEAR(self->debug_cb);
        Py_CLEAR(self->ioctl_cb);
        Py_CLEAR(self->seek_cb);
        Py_CLEAR(self->opensocket_cb);
#if LIBCURL_VERSION_NUM >= MAKE_LIBCURL_VERSION(7, 21, 7)
        Py_CLEAR(self->closesocket_cb);
#endif
        Py_CLEAR(self->sockopt_cb);
        Py_CLEAR(self->ssh_key_cb);
    }

    if (flags & PYCURL_MEMGROUP_FILE) {
        /* Decrement refcount for python file objects. */
        Py_CLEAR(self->readdata_fp);
        Py_CLEAR(self->writedata_fp);
        Py_CLEAR(self->writeheader_fp);
    }

    if (flags & PYCURL_MEMGROUP_POSTFIELDS) {
        /* Decrement refcount for postfields object */
        Py_CLEAR(self->postfields_obj);
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
        Py_CLEAR(self->httppost_ref_list);
    }

    if (flags & PYCURL_MEMGROUP_CACERTS) {
        /* Decrement refcounts for ca certs related references. */
        Py_CLEAR(self->ca_certs_obj);
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
#if LIBCURL_VERSION_NUM >= MAKE_LIBCURL_VERSION(7, 37, 0)
    SFREE(self->proxyheader);
#endif
    SFREE(self->http200aliases);
    SFREE(self->quote);
    SFREE(self->postquote);
    SFREE(self->prequote);
    SFREE(self->telnetoptions);
#ifdef HAVE_CURLOPT_RESOLVE
    SFREE(self->resolve);
#endif
#ifdef HAVE_CURL_7_20_0_OPTS
    SFREE(self->mail_rcpt);
#endif
#ifdef HAVE_CURLOPT_CONNECT_TO
    SFREE(self->connect_to);
#endif
#undef SFREE
}


PYCURL_INTERNAL void
do_curl_dealloc(CurlObject *self)
{
    PyObject_GC_UnTrack(self);
    Py_TRASHCAN_SAFE_BEGIN(self);

    Py_CLEAR(self->dict);
    util_curl_close(self);

    Curl_Type.tp_free(self);
    Py_TRASHCAN_SAFE_END(self);
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

    return PyText_FromString(self->error);
}


/* --------------- GC support --------------- */

/* Drop references that may have created reference cycles. */
PYCURL_INTERNAL int
do_curl_clear(CurlObject *self)
{
#ifdef WITH_THREAD
    assert(pycurl_get_thread_state(self) == NULL);
#endif
    util_curl_xdecref(self, PYCURL_MEMGROUP_ALL, self->handle);
    return 0;
}

/* Traverse all refcounted objects. */
PYCURL_INTERNAL int
do_curl_traverse(CurlObject *self, visitproc visit, void *arg)
{
    int err;
#undef VISIT
#define VISIT(v)    if ((v) != NULL && ((err = visit(v, arg)) != 0)) return err

    VISIT(self->dict);
    VISIT((PyObject *) self->multi_stack);
    VISIT((PyObject *) self->share);

    VISIT(self->w_cb);
    VISIT(self->h_cb);
    VISIT(self->r_cb);
    VISIT(self->pro_cb);
#if LIBCURL_VERSION_NUM >= MAKE_LIBCURL_VERSION(7, 32, 0)
    VISIT(self->xferinfo_cb);
#endif
    VISIT(self->debug_cb);
    VISIT(self->ioctl_cb);
    VISIT(self->seek_cb);
    VISIT(self->opensocket_cb);
#if LIBCURL_VERSION_NUM >= MAKE_LIBCURL_VERSION(7, 21, 7)
    VISIT(self->closesocket_cb);
#endif
    VISIT(self->sockopt_cb);
    VISIT(self->ssh_key_cb);

    VISIT(self->readdata_fp);
    VISIT(self->writedata_fp);
    VISIT(self->writeheader_fp);

    VISIT(self->postfields_obj);

    VISIT(self->ca_certs_obj);

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
#if PY_MAJOR_VERSION >= 3
    arglist = Py_BuildValue("(y#)", ptr, total_size);
#else
    arglist = Py_BuildValue("(s#)", ptr, total_size);
#endif
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

#if PY_MAJOR_VERSION >= 3
            res_obj = Py_BuildValue("y", s_un->sun_path);
#else
            res_obj = Py_BuildValue("s", s_un->sun_path);
#endif
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
    PyObject *converted_address;
    PyObject *python_address;
    PYCURL_DECLARE_THREAD_STATE;

    self = (CurlObject *)clientp;
    PYCURL_ACQUIRE_THREAD();

    converted_address = convert_protocol_address(&address->addr, address->addrlen);
    if (converted_address == NULL) {
        goto verbose_error;
    }

    arglist = Py_BuildValue("(iiiN)", address->family, address->socktype, address->protocol, converted_address);
    if (arglist == NULL) {
        Py_DECREF(converted_address);
        goto verbose_error;
    }
    python_address = PyEval_CallObject(curl_sockaddr_type, arglist);
    Py_DECREF(arglist);
    if (python_address == NULL) {
        goto verbose_error;
    }

    arglist = Py_BuildValue("(iN)", purpose, python_address);
    if (arglist == NULL) {
        Py_DECREF(python_address);
        goto verbose_error;
    }
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
            int sockfd = PyInt_AsLong(fileno_result);
#if defined(WIN32)
            ret = dup_winsock(sockfd, address);
#else
            ret = dup(sockfd);
#endif
            goto done;
        } else {
            PyErr_SetString(ErrorObject, "Open socket callback returned an object whose fileno method did not return an integer");
            ret = CURL_SOCKET_BAD;
        }
    } else {
        PyErr_SetString(ErrorObject, "Open socket callback's return value must be a socket");
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
sockopt_cb(void *clientp, curl_socket_t curlfd, curlsocktype purpose)
{
    PyObject *arglist;
    CurlObject *self;
    int ret = -1;
    PyObject *ret_obj = NULL;
    PYCURL_DECLARE_THREAD_STATE;

    self = (CurlObject *)clientp;
    PYCURL_ACQUIRE_THREAD();

    arglist = Py_BuildValue("(ii)", (int) curlfd, (int) purpose);
    if (arglist == NULL)
        goto verbose_error;

    ret_obj = PyEval_CallObject(self->sockopt_cb, arglist);
    Py_DECREF(arglist);
    if (!PyInt_Check(ret_obj) && !PyLong_Check(ret_obj)) {
        PyObject *ret_repr = PyObject_Repr(ret_obj);
        if (ret_repr) {
            PyObject *encoded_obj;
            char *str = PyText_AsString_NoNUL(ret_repr, &encoded_obj);
            fprintf(stderr, "sockopt callback returned %s which is not an integer\n", str);
            /* PyErr_Format(PyExc_TypeError, "sockopt callback returned %s which is not an integer", str); */
            Py_XDECREF(encoded_obj);
            Py_DECREF(ret_repr);
        }
        goto silent_error;
    }
    if (PyInt_Check(ret_obj)) {
        /* long to int cast */
        ret = (int) PyInt_AsLong(ret_obj);
    } else {
        /* long to int cast */
        ret = (int) PyLong_AsLong(ret_obj);
    }
    goto done;

silent_error:
    ret = -1;
done:
    Py_XDECREF(ret_obj);
    PYCURL_RELEASE_THREAD();
    return ret;
verbose_error:
    PyErr_Print();
    goto silent_error;
}


#if LIBCURL_VERSION_NUM >= MAKE_LIBCURL_VERSION(7, 21, 7)
static int
closesocket_callback(void *clientp, curl_socket_t curlfd)
{
    PyObject *arglist;
    CurlObject *self;
    int ret = -1;
    PyObject *ret_obj = NULL;
    PYCURL_DECLARE_THREAD_STATE;

    self = (CurlObject *)clientp;
    PYCURL_ACQUIRE_THREAD();

    arglist = Py_BuildValue("(i)", (int) curlfd);
    if (arglist == NULL)
        goto verbose_error;

    ret_obj = PyEval_CallObject(self->closesocket_cb, arglist);
    Py_DECREF(arglist);
    if (!PyInt_Check(ret_obj) && !PyLong_Check(ret_obj)) {
        PyObject *ret_repr = PyObject_Repr(ret_obj);
        if (ret_repr) {
            PyObject *encoded_obj;
            char *str = PyText_AsString_NoNUL(ret_repr, &encoded_obj);
            fprintf(stderr, "closesocket callback returned %s which is not an integer\n", str);
            /* PyErr_Format(PyExc_TypeError, "closesocket callback returned %s which is not an integer", str); */
            Py_XDECREF(encoded_obj);
            Py_DECREF(ret_repr);
        }
        goto silent_error;
    }
    if (PyInt_Check(ret_obj)) {
        /* long to int cast */
        ret = (int) PyInt_AsLong(ret_obj);
    } else {
        /* long to int cast */
        ret = (int) PyLong_AsLong(ret_obj);
    }
    goto done;

silent_error:
    ret = -1;
done:
    Py_XDECREF(ret_obj);
    PYCURL_RELEASE_THREAD();
    return ret;
verbose_error:
    PyErr_Print();
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
#if PY_MAJOR_VERSION >= 3
        arglist = Py_BuildValue("(y#i)", khkey->key, khkey->len, khkey->keytype);
#else
        arglist = Py_BuildValue("(s#i)", khkey->key, khkey->len, khkey->keytype);
#endif
    } else {
#if PY_MAJOR_VERSION >= 3
        arglist = Py_BuildValue("(yi)", khkey->key, khkey->keytype);
#else
        arglist = Py_BuildValue("(si)", khkey->key, khkey->keytype);
#endif
    }

    if (arglist == NULL) {
        return NULL;
    }

    ret = PyObject_Call(khkey_type, arglist, NULL);
    Py_DECREF(arglist);
    return ret;
}


static int
ssh_key_cb(CURL *easy, const struct curl_khkey *knownkey,
    const struct curl_khkey *foundkey, int khmatch, void *clientp)
{
    PyObject *arglist;
    CurlObject *self;
    int ret = -1;
    PyObject *knownkey_obj = NULL;
    PyObject *foundkey_obj = NULL;
    PyObject *ret_obj = NULL;
    PYCURL_DECLARE_THREAD_STATE;

    self = (CurlObject *)clientp;
    PYCURL_ACQUIRE_THREAD();

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

    ret_obj = PyEval_CallObject(self->ssh_key_cb, arglist);
    Py_DECREF(arglist);
    if (!PyInt_Check(ret_obj) && !PyLong_Check(ret_obj)) {
        PyObject *ret_repr = PyObject_Repr(ret_obj);
        if (ret_repr) {
            PyObject *encoded_obj;
            char *str = PyText_AsString_NoNUL(ret_repr, &encoded_obj);
            fprintf(stderr, "ssh key callback returned %s which is not an integer\n", str);
            /* PyErr_Format(PyExc_TypeError, "ssh key callback returned %s which is not an integer", str); */
            Py_XDECREF(encoded_obj);
            Py_DECREF(ret_repr);
        }
        goto silent_error;
    }
    if (PyInt_Check(ret_obj)) {
        /* long to int cast */
        ret = (int) PyInt_AsLong(ret_obj);
    } else {
        /* long to int cast */
        ret = (int) PyLong_AsLong(ret_obj);
    }
    goto done;

silent_error:
    ret = -1;
done:
    Py_XDECREF(knownkey_obj);
    Py_XDECREF(foundkey_obj);
    Py_XDECREF(ret_obj);
    PYCURL_RELEASE_THREAD();
    return ret;
verbose_error:
    PyErr_Print();
    goto silent_error;
}
#endif


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
    if (PyByteStr_Check(result)) {
        char *buf = NULL;
        Py_ssize_t obj_size = -1;
        Py_ssize_t r;
        r = PyByteStr_AsStringAndSize(result, &buf, &obj_size);
        if (r != 0 || obj_size < 0 || obj_size > total_size) {
            PyErr_Format(ErrorObject, "invalid return value for read callback (%ld bytes returned when at most %ld bytes were wanted)", (long)obj_size, (long)total_size);
            goto verbose_error;
        }
        memcpy(ptr, buf, obj_size);
        ret = obj_size;             /* success */
    }
    else if (PyUnicode_Check(result)) {
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
        r = PyByteStr_AsStringAndSize(encoded, &buf, &obj_size);
        if (r != 0 || obj_size < 0 || obj_size > total_size) {
            Py_DECREF(encoded);
            PyErr_Format(ErrorObject, "invalid return value for read callback (%ld bytes returned after encoding to utf-8 when at most %ld bytes were wanted)", (long)obj_size, (long)total_size);
            goto verbose_error;
        }
        memcpy(ptr, buf, obj_size);
        Py_DECREF(encoded);
        ret = obj_size;             /* success */
    }
#if PY_MAJOR_VERSION < 3
    else if (PyInt_Check(result)) {
        long r = PyInt_AsLong(result);
        if (r != CURL_READFUNC_ABORT && r != CURL_READFUNC_PAUSE)
            goto type_error;
        ret = r; /* either CURL_READFUNC_ABORT or CURL_READFUNC_PAUSE */
    }
#endif
    else if (PyLong_Check(result)) {
        long r = PyLong_AsLong(result);
        if (r != CURL_READFUNC_ABORT && r != CURL_READFUNC_PAUSE)
            goto type_error;
        ret = r; /* either CURL_READFUNC_ABORT or CURL_READFUNC_PAUSE */
    }
    else {
    type_error:
        PyErr_SetString(ErrorObject, "read callback must return a byte string or Unicode string with ASCII code points only");
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


#if LIBCURL_VERSION_NUM >= MAKE_LIBCURL_VERSION(7, 32, 0)
static int
xferinfo_callback(void *stream,
                  curl_off_t dltotal, curl_off_t dlnow, curl_off_t ultotal, curl_off_t ulnow)
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
    if (self->xferinfo_cb == NULL)
        goto silent_error;

    /* run callback */
    arglist = Py_BuildValue("(LLLL)",
        (PY_LONG_LONG) dltotal, (PY_LONG_LONG) dlnow,
        (PY_LONG_LONG) ultotal, (PY_LONG_LONG) ulnow);
    if (arglist == NULL)
        goto verbose_error;
    result = PyEval_CallObject(self->xferinfo_cb, arglist);
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
#endif


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
#if PY_MAJOR_VERSION >= 3
    arglist = Py_BuildValue("(iy#)", (int)type, buffer, (int)total_size);
#else
    arglist = Py_BuildValue("(is#)", (int)type, buffer, (int)total_size);
#endif
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


#if defined(HAVE_CURL_OPENSSL)
static CURLcode
ssl_ctx_callback(CURL *curl, void *ssl_ctx, void *ptr)
{
    CurlObject *self;
    PYCURL_DECLARE_THREAD_STATE;
    int r;

    UNUSED(curl);

    /* acquire thread */
    self = (CurlObject *)ptr;
    if (!PYCURL_ACQUIRE_THREAD())
        return CURLE_FAILED_INIT;

    r = add_ca_certs((SSL_CTX*)ssl_ctx,
                         PyBytes_AS_STRING(self->ca_certs_obj),
                         PyBytes_GET_SIZE(self->ca_certs_obj));

    if (r != 0)
        PyErr_Print();

    PYCURL_RELEASE_THREAD();
    return r == 0 ? CURLE_OK : CURLE_FAILED_INIT;
}
#endif


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
#if LIBCURL_VERSION_NUM >= MAKE_LIBCURL_VERSION(7, 37, 0)
    SFREE(self->proxyheader);
#endif
    SFREE(self->http200aliases);
    SFREE(self->quote);
    SFREE(self->postquote);
    SFREE(self->prequote);
    SFREE(self->telnetoptions);
#ifdef HAVE_CURLOPT_RESOLVE
    SFREE(self->resolve);
#endif
#ifdef HAVE_CURL_7_20_0_OPTS
    SFREE(self->mail_rcpt);
#endif
#ifdef HAVE_CURLOPT_CONNECT_TO
    SFREE(self->connect_to);
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
#define CLEAR_CALLBACK(callback_option, data_option, callback_field) \
    case callback_option: \
        if ((res = curl_easy_setopt(self->handle, callback_option, NULL)) != CURLE_OK) \
            goto error; \
        if ((res = curl_easy_setopt(self->handle, data_option, NULL)) != CURLE_OK) \
            goto error; \
        Py_CLEAR(callback_field); \
        break

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
        Py_CLEAR(self->writeheader_fp);
        break;
    case CURLOPT_CAINFO:
    case CURLOPT_CAPATH:
    case CURLOPT_COOKIE:
    case CURLOPT_COOKIEJAR:
    case CURLOPT_CUSTOMREQUEST:
    case CURLOPT_EGDSOCKET:
    case CURLOPT_ENCODING:
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
#if LIBCURL_VERSION_NUM >= MAKE_LIBCURL_VERSION(7, 43, 0)
    case CURLOPT_SERVICE_NAME:
    case CURLOPT_PROXY_SERVICE_NAME:
#endif
    case CURLOPT_HTTPHEADER:
#if LIBCURL_VERSION_NUM >= MAKE_LIBCURL_VERSION(7, 37, 0)
    case CURLOPT_PROXYHEADER:
#endif
#if LIBCURL_VERSION_NUM >= MAKE_LIBCURL_VERSION(7, 52, 0)
    case CURLOPT_PROXY_CAPATH:
    case CURLOPT_PROXY_CAINFO:
#endif
        SETOPT((char *) NULL);
        break;

#ifdef HAVE_CURLOPT_CERTINFO
    case CURLOPT_CERTINFO:
        SETOPT((long) 0);
        break;
#endif

    CLEAR_CALLBACK(CURLOPT_OPENSOCKETFUNCTION, CURLOPT_OPENSOCKETDATA, self->opensocket_cb);
#if LIBCURL_VERSION_NUM >= MAKE_LIBCURL_VERSION(7, 21, 7)
    CLEAR_CALLBACK(CURLOPT_CLOSESOCKETFUNCTION, CURLOPT_CLOSESOCKETDATA, self->closesocket_cb);
#endif
    CLEAR_CALLBACK(CURLOPT_SOCKOPTFUNCTION, CURLOPT_SOCKOPTDATA, self->sockopt_cb);
#ifdef HAVE_CURL_7_19_6_OPTS
    CLEAR_CALLBACK(CURLOPT_SSH_KEYFUNCTION, CURLOPT_SSH_KEYDATA, self->ssh_key_cb);
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
#undef CLEAR_CALLBACK
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
do_curl_setopt_string_impl(CurlObject *self, int option, PyObject *obj)
{
    char *str = NULL;
    Py_ssize_t len = -1;
    PyObject *encoded_obj;
    int res;

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
    /* use CURLOPT_ENCODING instead of CURLOPT_ACCEPT_ENCODING
    for compatibility with older libcurls */
    case CURLOPT_ENCODING:
    case CURLOPT_FTPPORT:
    case CURLOPT_INTERFACE:
    case CURLOPT_KEYPASSWD:
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
#if LIBCURL_VERSION_NUM >= MAKE_LIBCURL_VERSION(7, 20, 0)
    case CURLOPT_RTSP_STREAM_URI:
    case CURLOPT_RTSP_SESSION_ID:
    case CURLOPT_RTSP_TRANSPORT:
#endif
#ifdef HAVE_CURLOPT_DNS_SERVERS
    case CURLOPT_DNS_SERVERS:
#endif
#ifdef HAVE_CURLOPT_NOPROXY
    case CURLOPT_NOPROXY:
#endif
#ifdef HAVE_CURL_7_19_4_OPTS
    case CURLOPT_SOCKS5_GSSAPI_SERVICE:
#endif
#ifdef HAVE_CURL_7_19_6_OPTS
    case CURLOPT_SSH_KNOWNHOSTS:
#endif
#ifdef HAVE_CURL_7_20_0_OPTS
    case CURLOPT_MAIL_FROM:
#endif
#ifdef HAVE_CURL_7_25_0_OPTS
    case CURLOPT_MAIL_AUTH:
#endif
#if LIBCURL_VERSION_NUM >= MAKE_LIBCURL_VERSION(7, 39, 0)
    case CURLOPT_PINNEDPUBLICKEY:
#endif
#if LIBCURL_VERSION_NUM >= MAKE_LIBCURL_VERSION(7, 43, 0)
    case CURLOPT_SERVICE_NAME:
    case CURLOPT_PROXY_SERVICE_NAME:
#endif
#if LIBCURL_VERSION_NUM >= MAKE_LIBCURL_VERSION(7, 21, 0)
    case CURLOPT_WILDCARDMATCH:
#endif
#if LIBCURL_VERSION_NUM >= MAKE_LIBCURL_VERSION(7, 40, 0)
    case CURLOPT_UNIX_SOCKET_PATH:
#endif
#if LIBCURL_VERSION_NUM >= MAKE_LIBCURL_VERSION(7, 21, 4)
    case CURLOPT_TLSAUTH_TYPE:
    case CURLOPT_TLSAUTH_USERNAME:
    case CURLOPT_TLSAUTH_PASSWORD:
#endif
#if LIBCURL_VERSION_NUM >= MAKE_LIBCURL_VERSION(7, 45, 0)
    case CURLOPT_DEFAULT_PROTOCOL:
#endif
#if LIBCURL_VERSION_NUM >= MAKE_LIBCURL_VERSION(7, 34, 0)
    case CURLOPT_LOGIN_OPTIONS:
#endif
#if LIBCURL_VERSION_NUM >= MAKE_LIBCURL_VERSION(7, 33, 0)
    case CURLOPT_XOAUTH2_BEARER:
#endif
#if LIBCURL_VERSION_NUM >= MAKE_LIBCURL_VERSION(7, 52, 0)
    case CURLOPT_PROXY_CAPATH:
    case CURLOPT_PROXY_CAINFO:
#endif
    case CURLOPT_KRBLEVEL:
        str = PyText_AsString_NoNUL(obj, &encoded_obj);
        if (str == NULL)
            return NULL;
        break;
    case CURLOPT_POSTFIELDS:
        if (PyText_AsStringAndSize(obj, &str, &len, &encoded_obj) != 0)
            return NULL;
        /* automatically set POSTFIELDSIZE */
        if (len <= INT_MAX) {
            res = curl_easy_setopt(self->handle, CURLOPT_POSTFIELDSIZE, (long)len);
        } else {
            res = curl_easy_setopt(self->handle, CURLOPT_POSTFIELDSIZE_LARGE, (curl_off_t)len);
        }
        if (res != CURLE_OK) {
            PyText_EncodedDecref(encoded_obj);
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
        PyText_EncodedDecref(encoded_obj);
        CURLERROR_RETVAL();
    }
    /* libcurl does not copy the value of CURLOPT_POSTFIELDS */
    if (option == CURLOPT_POSTFIELDS) {
        PyObject *store_obj;

        /* if obj was bytes, it was not encoded, and we need to incref obj.
         * if obj was unicode, it was encoded, and we need to incref
         * encoded_obj - except we can simply transfer ownership.
         */
        if (encoded_obj) {
            store_obj = encoded_obj;
        } else {
            /* no encoding is performed, incref the original object. */
            store_obj = obj;
            Py_INCREF(store_obj);
        }

        util_curl_xdecref(self, PYCURL_MEMGROUP_POSTFIELDS, self->handle);
        self->postfields_obj = store_obj;
    } else {
        PyText_EncodedDecref(encoded_obj);
    }
    Py_RETURN_NONE;
}


#define IS_LONG_OPTION(o)   (o < CURLOPTTYPE_OBJECTPOINT)
#define IS_OFF_T_OPTION(o)  (o >= CURLOPTTYPE_OFF_T)


static PyObject *
do_curl_setopt_int(CurlObject *self, int option, PyObject *obj)
{
    long d;
    PY_LONG_LONG ld;
    int res;

    if (IS_LONG_OPTION(option)) {
        d = PyInt_AsLong(obj);
        res = curl_easy_setopt(self->handle, (CURLoption)option, (long)d);
    } else if (IS_OFF_T_OPTION(option)) {
        /* this path should only be taken in Python 3 */
        ld = PyLong_AsLongLong(obj);
        res = curl_easy_setopt(self->handle, (CURLoption)option, (curl_off_t)ld);
    } else {
        PyErr_SetString(PyExc_TypeError, "integers are not supported for this option");
        return NULL;
    }
    if (res != CURLE_OK) {
        CURLERROR_RETVAL();
    }
    Py_RETURN_NONE;
}


static PyObject *
do_curl_setopt_long(CurlObject *self, int option, PyObject *obj)
{
    int res;
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


#if PY_MAJOR_VERSION < 3 && !defined(PYCURL_AVOID_STDIO)
static PyObject *
do_curl_setopt_file_passthrough(CurlObject *self, int option, PyObject *obj)
{
    FILE *fp;
    int res;

    fp = PyFile_AsFile(obj);
    if (fp == NULL) {
        PyErr_SetString(PyExc_TypeError, "second argument must be open file");
        return NULL;
    }
    
    switch (option) {
    case CURLOPT_READDATA:
        res = curl_easy_setopt(self->handle, CURLOPT_READFUNCTION, fread);
        if (res != CURLE_OK) {
            CURLERROR_RETVAL();
        }
        break;
    case CURLOPT_WRITEDATA:
        res = curl_easy_setopt(self->handle, CURLOPT_WRITEFUNCTION, fwrite);
        if (res != CURLE_OK) {
            CURLERROR_RETVAL();
        }
        break;
    case CURLOPT_WRITEHEADER:
        res = curl_easy_setopt(self->handle, CURLOPT_HEADERFUNCTION, fwrite);
        if (res != CURLE_OK) {
            CURLERROR_RETVAL();
        }
        break;
    default:
        PyErr_SetString(PyExc_TypeError, "files are not supported for this option");
        return NULL;
    }

    res = curl_easy_setopt(self->handle, (CURLoption)option, fp);
    if (res != CURLE_OK) {
        /*
        If we get here fread/fwrite are set as callbacks but the file pointer
        is not set, program will crash if it does not reset read/write
        callback. Also, we won't do the memory management later in this
        function.
        */
        CURLERROR_RETVAL();
    }
    Py_INCREF(obj);

    switch (option) {
    case CURLOPT_READDATA:
        Py_CLEAR(self->readdata_fp);
        self->readdata_fp = obj;
        break;
    case CURLOPT_WRITEDATA:
        Py_CLEAR(self->writedata_fp);
        self->writedata_fp = obj;
        break;
    case CURLOPT_WRITEHEADER:
        Py_CLEAR(self->writeheader_fp);
        self->writeheader_fp = obj;
        break;
    default:
        assert(0);
        break;
    }
    /* Return success */
    Py_RETURN_NONE;
}
#endif


static PyObject *
do_curl_setopt_httppost(CurlObject *self, int option, int which, PyObject *obj)
{
    struct curl_httppost *post = NULL;
    struct curl_httppost *last = NULL;
    /* List of all references that have been INCed as a result of
     * this operation */
    PyObject *ref_params = NULL;
    PyObject *nencoded_obj, *cencoded_obj, *oencoded_obj;
    int which_httppost_item, which_httppost_option;
    PyObject *httppost_option;
    Py_ssize_t i, len;
    int res;

    len = PyListOrTuple_Size(obj, which);
    if (len == 0)
        Py_RETURN_NONE;

    for (i = 0; i < len; i++) {
        char *nstr = NULL, *cstr = NULL;
        Py_ssize_t nlen = -1, clen = -1;
        PyObject *listitem = PyListOrTuple_GetItem(obj, i, which);

        which_httppost_item = PyListOrTuple_Check(listitem);
        if (!which_httppost_item) {
            PyErr_SetString(PyExc_TypeError, "list items must be list or tuple objects");
            goto error;
        }
        if (PyListOrTuple_Size(listitem, which_httppost_item) != 2) {
            PyErr_SetString(PyExc_TypeError, "list or tuple must contain two elements (name, value)");
            goto error;
        }
        if (PyText_AsStringAndSize(PyListOrTuple_GetItem(listitem, 0, which_httppost_item),
                &nstr, &nlen, &nencoded_obj) != 0) {
            PyErr_SetString(PyExc_TypeError, "list or tuple must contain a byte string or Unicode string with ASCII code points only as first element");
            goto error;
        }
        httppost_option = PyListOrTuple_GetItem(listitem, 1, which_httppost_item);
        if (PyText_Check(httppost_option)) {
            /* Handle strings as second argument for backwards compatibility */

            if (PyText_AsStringAndSize(httppost_option, &cstr, &clen, &cencoded_obj)) {
                PyText_EncodedDecref(nencoded_obj);
                CURLERROR_SET_RETVAL();
                goto error;
            }
            /* INFO: curl_formadd() internally does memdup() the data, so
             * embedded NUL characters _are_ allowed here. */
            res = curl_formadd(&post, &last,
                               CURLFORM_COPYNAME, nstr,
                               CURLFORM_NAMELENGTH, (long) nlen,
                               CURLFORM_COPYCONTENTS, cstr,
                               CURLFORM_CONTENTSLENGTH, (long) clen,
                               CURLFORM_END);
            PyText_EncodedDecref(cencoded_obj);
            if (res != CURLE_OK) {
                PyText_EncodedDecref(nencoded_obj);
                CURLERROR_SET_RETVAL();
                goto error;
            }
        }
        /* assignment is intended */
        else if ((which_httppost_option = PyListOrTuple_Check(httppost_option))) {
            /* Supports content, file and content-type */
            Py_ssize_t tlen = PyListOrTuple_Size(httppost_option, which_httppost_option);
            int j, k, l;
            struct curl_forms *forms = NULL;

            /* Sanity check that there are at least two tuple items */
            if (tlen < 2) {
                PyText_EncodedDecref(nencoded_obj);
                PyErr_SetString(PyExc_TypeError, "list or tuple must contain at least one option and one value");
                goto error;
            }

            if (tlen % 2 == 1) {
                PyText_EncodedDecref(nencoded_obj);
                PyErr_SetString(PyExc_TypeError, "list or tuple must contain an even number of items");
                goto error;
            }

            /* Allocate enough space to accommodate length options for content or buffers, plus a terminator. */
            forms = PyMem_New(struct curl_forms, (tlen*2) + 1);
            if (forms == NULL) {
                PyText_EncodedDecref(nencoded_obj);
                PyErr_NoMemory();
                goto error;
            }

            /* Iterate all the tuple members pairwise */
            for (j = 0, k = 0, l = 0; j < tlen; j += 2, l++) {
                char *ostr;
                Py_ssize_t olen;
                int val;

                if (j == (tlen-1)) {
                    PyErr_SetString(PyExc_TypeError, "expected value");
                    PyMem_Free(forms);
                    PyText_EncodedDecref(nencoded_obj);
                    goto error;
                }
                if (!PyInt_Check(PyListOrTuple_GetItem(httppost_option, j, which_httppost_option))) {
                    PyErr_SetString(PyExc_TypeError, "option must be an integer");
                    PyMem_Free(forms);
                    PyText_EncodedDecref(nencoded_obj);
                    goto error;
                }
                if (!PyText_Check(PyListOrTuple_GetItem(httppost_option, j+1, which_httppost_option))) {
                    PyErr_SetString(PyExc_TypeError, "value must be a byte string or a Unicode string with ASCII code points only");
                    PyMem_Free(forms);
                    PyText_EncodedDecref(nencoded_obj);
                    goto error;
                }

                val = PyLong_AsLong(PyListOrTuple_GetItem(httppost_option, j, which_httppost_option));
                if (val != CURLFORM_COPYCONTENTS &&
                    val != CURLFORM_FILE &&
                    val != CURLFORM_FILENAME &&
                    val != CURLFORM_CONTENTTYPE &&
                    val != CURLFORM_BUFFER &&
                    val != CURLFORM_BUFFERPTR)
                {
                    PyErr_SetString(PyExc_TypeError, "unsupported option");
                    PyMem_Free(forms);
                    PyText_EncodedDecref(nencoded_obj);
                    goto error;
                }

                if (PyText_AsStringAndSize(PyListOrTuple_GetItem(httppost_option, j+1, which_httppost_option), &ostr, &olen, &oencoded_obj)) {
                    /* exception should be already set */
                    PyMem_Free(forms);
                    PyText_EncodedDecref(nencoded_obj);
                    goto error;
                }
                forms[k].option = val;
                forms[k].value = ostr;
                ++k;

                if (val == CURLFORM_COPYCONTENTS) {
                    /* Contents can contain \0 bytes so we specify the length */
                    forms[k].option = CURLFORM_CONTENTSLENGTH;
                    forms[k].value = (const char *)olen;
                    ++k;
                } else if (val == CURLFORM_BUFFERPTR) {
                    PyObject *obj = NULL;

                    if (ref_params == NULL) {
                        ref_params = PyList_New((Py_ssize_t)0);
                        if (ref_params == NULL) {
                            PyText_EncodedDecref(oencoded_obj);
                            PyMem_Free(forms);
                            PyText_EncodedDecref(nencoded_obj);
                            goto error;
                        }
                    }

                    /* Keep a reference to the object that holds the ostr buffer. */
                    if (oencoded_obj == NULL) {
                        obj = PyListOrTuple_GetItem(httppost_option, j+1, which_httppost_option);
                    }
                    else {
                        obj = oencoded_obj;
                    }

                    /* Ensure that the buffer remains alive until curl_easy_cleanup() */
                    if (PyList_Append(ref_params, obj) != 0) {
                        PyText_EncodedDecref(oencoded_obj);
                        PyMem_Free(forms);
                        PyText_EncodedDecref(nencoded_obj);
                        goto error;
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
            PyText_EncodedDecref(oencoded_obj);
            PyMem_Free(forms);
            if (res != CURLE_OK) {
                PyText_EncodedDecref(nencoded_obj);
                CURLERROR_SET_RETVAL();
                goto error;
            }
        } else {
            /* Some other type was given, ignore */
            PyText_EncodedDecref(nencoded_obj);
            PyErr_SetString(PyExc_TypeError, "unsupported second type in tuple");
            goto error;
        }
        PyText_EncodedDecref(nencoded_obj);
    }
    res = curl_easy_setopt(self->handle, CURLOPT_HTTPPOST, post);
    /* Check for errors */
    if (res != CURLE_OK) {
        CURLERROR_SET_RETVAL();
        goto error;
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

error:
    curl_formfree(post);
    Py_XDECREF(ref_params);
    return NULL;
}


static PyObject *
do_curl_setopt_list(CurlObject *self, int option, int which, PyObject *obj)
{
    struct curl_slist **old_slist = NULL;
    struct curl_slist *slist = NULL;
    Py_ssize_t len;
    int res;

    switch (option) {
    case CURLOPT_HTTP200ALIASES:
        old_slist = &self->http200aliases;
        break;
    case CURLOPT_HTTPHEADER:
        old_slist = &self->httpheader;
        break;
#if LIBCURL_VERSION_NUM >= MAKE_LIBCURL_VERSION(7, 37, 0)
    case CURLOPT_PROXYHEADER:
        old_slist = &self->proxyheader;
        break;
#endif
    case CURLOPT_POSTQUOTE:
        old_slist = &self->postquote;
        break;
    case CURLOPT_PREQUOTE:
        old_slist = &self->prequote;
        break;
    case CURLOPT_QUOTE:
        old_slist = &self->quote;
        break;
    case CURLOPT_TELNETOPTIONS:
        old_slist = &self->telnetoptions;
        break;
#ifdef HAVE_CURLOPT_RESOLVE
    case CURLOPT_RESOLVE:
        old_slist = &self->resolve;
        break;
#endif
#ifdef HAVE_CURL_7_20_0_OPTS
    case CURLOPT_MAIL_RCPT:
        old_slist = &self->mail_rcpt;
        break;
#endif
#ifdef HAVE_CURLOPT_CONNECT_TO
    case CURLOPT_CONNECT_TO:
        old_slist = &self->connect_to;
        break;
#endif
    default:
        /* None of the list options were recognized, raise exception */
        PyErr_SetString(PyExc_TypeError, "lists are not supported for this option");
        return NULL;
    }

    len = PyListOrTuple_Size(obj, which);
    if (len == 0)
        Py_RETURN_NONE;

    /* Just to be sure we do not bug off here */
    assert(old_slist != NULL && slist == NULL);

    /* Handle regular list operations on the other options */
    slist = pycurl_list_or_tuple_to_slist(which, obj, len);
    if (slist == NULL) {
        return NULL;
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


static PyObject *
do_curl_setopt_callable(CurlObject *self, int option, PyObject *obj)
{
    /* We use function types here to make sure that our callback
     * definitions exactly match the <curl/curl.h> interface.
     */
    const curl_write_callback w_cb = write_callback;
    const curl_write_callback h_cb = header_callback;
    const curl_read_callback r_cb = read_callback;
    const curl_progress_callback pro_cb = progress_callback;
#if LIBCURL_VERSION_NUM >= MAKE_LIBCURL_VERSION(7, 32, 0)
    const curl_xferinfo_callback xferinfo_cb = xferinfo_callback;
#endif
    const curl_debug_callback debug_cb = debug_callback;
    const curl_ioctl_callback ioctl_cb = ioctl_callback;
    const curl_opensocket_callback opensocket_cb = opensocket_callback;
#if LIBCURL_VERSION_NUM >= MAKE_LIBCURL_VERSION(7, 21, 7)
    const curl_closesocket_callback closesocket_cb = closesocket_callback;
#endif
    const curl_seek_callback seek_cb = seek_callback;

    switch(option) {
    case CURLOPT_WRITEFUNCTION:
        Py_INCREF(obj);
        Py_CLEAR(self->writedata_fp);
        Py_CLEAR(self->w_cb);
        self->w_cb = obj;
        curl_easy_setopt(self->handle, CURLOPT_WRITEFUNCTION, w_cb);
        curl_easy_setopt(self->handle, CURLOPT_WRITEDATA, self);
        break;
    case CURLOPT_HEADERFUNCTION:
        Py_INCREF(obj);
        Py_CLEAR(self->writeheader_fp);
        Py_CLEAR(self->h_cb);
        self->h_cb = obj;
        curl_easy_setopt(self->handle, CURLOPT_HEADERFUNCTION, h_cb);
        curl_easy_setopt(self->handle, CURLOPT_WRITEHEADER, self);
        break;
    case CURLOPT_READFUNCTION:
        Py_INCREF(obj);
        Py_CLEAR(self->readdata_fp);
        Py_CLEAR(self->r_cb);
        self->r_cb = obj;
        curl_easy_setopt(self->handle, CURLOPT_READFUNCTION, r_cb);
        curl_easy_setopt(self->handle, CURLOPT_READDATA, self);
        break;
    case CURLOPT_PROGRESSFUNCTION:
        Py_INCREF(obj);
        Py_CLEAR(self->pro_cb);
        self->pro_cb = obj;
        curl_easy_setopt(self->handle, CURLOPT_PROGRESSFUNCTION, pro_cb);
        curl_easy_setopt(self->handle, CURLOPT_PROGRESSDATA, self);
        break;
#if LIBCURL_VERSION_NUM >= MAKE_LIBCURL_VERSION(7, 32, 0)
    case CURLOPT_XFERINFOFUNCTION:
        Py_INCREF(obj);
        Py_CLEAR(self->xferinfo_cb);
        self->xferinfo_cb = obj;
        curl_easy_setopt(self->handle, CURLOPT_XFERINFOFUNCTION, xferinfo_cb);
        curl_easy_setopt(self->handle, CURLOPT_XFERINFODATA, self);
        break;
#endif
    case CURLOPT_DEBUGFUNCTION:
        Py_INCREF(obj);
        Py_CLEAR(self->debug_cb);
        self->debug_cb = obj;
        curl_easy_setopt(self->handle, CURLOPT_DEBUGFUNCTION, debug_cb);
        curl_easy_setopt(self->handle, CURLOPT_DEBUGDATA, self);
        break;
    case CURLOPT_IOCTLFUNCTION:
        Py_INCREF(obj);
        Py_CLEAR(self->ioctl_cb);
        self->ioctl_cb = obj;
        curl_easy_setopt(self->handle, CURLOPT_IOCTLFUNCTION, ioctl_cb);
        curl_easy_setopt(self->handle, CURLOPT_IOCTLDATA, self);
        break;
    case CURLOPT_OPENSOCKETFUNCTION:
        Py_INCREF(obj);
        Py_CLEAR(self->opensocket_cb);
        self->opensocket_cb = obj;
        curl_easy_setopt(self->handle, CURLOPT_OPENSOCKETFUNCTION, opensocket_cb);
        curl_easy_setopt(self->handle, CURLOPT_OPENSOCKETDATA, self);
        break;
#if LIBCURL_VERSION_NUM >= MAKE_LIBCURL_VERSION(7, 21, 7)
    case CURLOPT_CLOSESOCKETFUNCTION:
        Py_INCREF(obj);
        Py_CLEAR(self->closesocket_cb);
        self->closesocket_cb = obj;
        curl_easy_setopt(self->handle, CURLOPT_CLOSESOCKETFUNCTION, closesocket_cb);
        curl_easy_setopt(self->handle, CURLOPT_CLOSESOCKETDATA, self);
        break;
#endif
    case CURLOPT_SOCKOPTFUNCTION:
        Py_INCREF(obj);
        Py_CLEAR(self->sockopt_cb);
        self->sockopt_cb = obj;
        curl_easy_setopt(self->handle, CURLOPT_SOCKOPTFUNCTION, sockopt_cb);
        curl_easy_setopt(self->handle, CURLOPT_SOCKOPTDATA, self);
        break;
#ifdef HAVE_CURL_7_19_6_OPTS
    case CURLOPT_SSH_KEYFUNCTION:
        Py_INCREF(obj);
        Py_CLEAR(self->ssh_key_cb);
        self->ssh_key_cb = obj;
        curl_easy_setopt(self->handle, CURLOPT_SSH_KEYFUNCTION, ssh_key_cb);
        curl_easy_setopt(self->handle, CURLOPT_SSH_KEYDATA, self);
        break;
#endif
    case CURLOPT_SEEKFUNCTION:
        Py_INCREF(obj);
        Py_CLEAR(self->seek_cb);
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


static PyObject *
do_curl_setopt_share(CurlObject *self, PyObject *obj)
{
    CurlShareObject *share;
    int res;

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


/* prototype for do_curl_setopt_filelike */
static PyObject *
do_curl_setopt(CurlObject *self, PyObject *args);


static PyObject *
do_curl_setopt_filelike(CurlObject *self, int option, PyObject *obj)
{
    const char *method_name;
    PyObject *method;

    if (option == CURLOPT_READDATA) {
        method_name = "read";
    } else {
        method_name = "write";
    }
    method = PyObject_GetAttrString(obj, method_name);
    if (method) {
        PyObject *arglist;
        PyObject *rv;

        switch (option) {
            case CURLOPT_READDATA:
                option = CURLOPT_READFUNCTION;
                break;
            case CURLOPT_WRITEDATA:
                option = CURLOPT_WRITEFUNCTION;
                break;
            case CURLOPT_WRITEHEADER:
                option = CURLOPT_HEADERFUNCTION;
                break;
            default:
                PyErr_SetString(PyExc_TypeError, "objects are not supported for this option");
                Py_DECREF(method);
                return NULL;
        }

        arglist = Py_BuildValue("(iO)", option, method);
        /* reference is now in arglist */
        Py_DECREF(method);
        if (arglist == NULL) {
            return NULL;
        }
        rv = do_curl_setopt(self, arglist);
        Py_DECREF(arglist);
        return rv;
    } else {
        if (option == CURLOPT_READDATA) {
            PyErr_SetString(PyExc_TypeError, "object given without a read method");
        } else {
            PyErr_SetString(PyExc_TypeError, "object given without a write method");
        }
        return NULL;
    }
}


static PyObject *
do_curl_setopt(CurlObject *self, PyObject *args)
{
    int option;
    PyObject *obj;
    int which;

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
    if (PyText_Check(obj)) {
        return do_curl_setopt_string_impl(self, option, obj);
    }

    /* Handle the case of integer arguments */
    if (PyInt_Check(obj)) {
        return do_curl_setopt_int(self, option, obj);
    }

    /* Handle the case of long arguments (used by *_LARGE options) */
    if (PyLong_Check(obj)) {
        return do_curl_setopt_long(self, option, obj);
    }

#if PY_MAJOR_VERSION < 3 && !defined(PYCURL_AVOID_STDIO)
    /* Handle the case of file objects */
    if (PyFile_Check(obj)) {
        return do_curl_setopt_file_passthrough(self, option, obj);
    }
#endif

    /* Handle the case of list or tuple objects */
    which = PyListOrTuple_Check(obj);
    if (which) {
        if (option == CURLOPT_HTTPPOST) {
            return do_curl_setopt_httppost(self, option, which, obj);
        } else {
            return do_curl_setopt_list(self, option, which, obj);
        }
    }

    /* Handle the case of function objects for callbacks */
    if (PyFunction_Check(obj) || PyCFunction_Check(obj) ||
        PyCallable_Check(obj) || PyMethod_Check(obj)) {
        return do_curl_setopt_callable(self, option, obj);
    }
    /* handle the SHARE case */
    if (option == CURLOPT_SHARE) {
        return do_curl_setopt_share(self, obj);
    }

    /*
    Handle the case of file-like objects.

    Given an object with a write method, we will call the write method
    from the appropriate callback.

    Files in Python 3 are no longer FILE * instances and therefore cannot
    be directly given to curl, therefore this method handles all I/O to
    Python objects.
    
    In Python 2 true file objects are FILE * instances and will be handled
    by stdio passthrough code invoked above, and file-like objects will
    be handled by this method.
    */
    if (option == CURLOPT_READDATA ||
        option == CURLOPT_WRITEDATA ||
        option == CURLOPT_WRITEHEADER)
    {
        return do_curl_setopt_filelike(self, option, obj);
    }

    /* Failed to match any of the function signatures -- return error */
error:
    PyErr_SetString(PyExc_TypeError, "invalid arguments to setopt");
    return NULL;
}


static PyObject *
do_curl_setopt_string(CurlObject *self, PyObject *args)
{
    int option;
    PyObject *obj;

    if (!PyArg_ParseTuple(args, "iO:setopt", &option, &obj))
        return NULL;
    if (check_curl_state(self, 1 | 2, "setopt") != 0)
        return NULL;

    /* Handle the case of string arguments */
    if (PyText_Check(obj)) {
        return do_curl_setopt_string_impl(self, option, obj);
    }

    /* Failed to match any of the function signatures -- return error */
    PyErr_SetString(PyExc_TypeError, "invalid arguments to setopt_string");
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
    case CURLINFO_RESPONSE_CODE:
    case CURLINFO_REDIRECT_COUNT:
    case CURLINFO_REQUEST_SIZE:
    case CURLINFO_SSL_VERIFYRESULT:
    case CURLINFO_HTTP_CONNECTCODE:
    case CURLINFO_HTTPAUTH_AVAIL:
    case CURLINFO_PROXYAUTH_AVAIL:
    case CURLINFO_OS_ERRNO:
    case CURLINFO_NUM_CONNECTS:
    case CURLINFO_LASTSOCKET:
#ifdef HAVE_CURLINFO_LOCAL_PORT
    case CURLINFO_LOCAL_PORT:
#endif
#ifdef HAVE_CURLINFO_PRIMARY_PORT
    case CURLINFO_PRIMARY_PORT:
#endif
#if LIBCURL_VERSION_NUM >= MAKE_LIBCURL_VERSION(7, 20, 0)
    case CURLINFO_RTSP_CLIENT_CSEQ:
    case CURLINFO_RTSP_SERVER_CSEQ:
    case CURLINFO_RTSP_CSEQ_RECV:
#endif
#ifdef HAVE_CURLINFO_HTTP_VERSION
    case CURLINFO_HTTP_VERSION:
#endif

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
#ifdef HAVE_CURLINFO_LOCAL_IP
    case CURLINFO_LOCAL_IP:
#endif
#if LIBCURL_VERSION_NUM >= MAKE_LIBCURL_VERSION(7, 20, 0)
    case CURLINFO_RTSP_SESSION_ID:
#endif
        {
            /* Return PyString as result */
            char *s_res = NULL;

            res = curl_easy_getinfo(self->handle, (CURLINFO)option, &s_res);
            if (res != CURLE_OK) {
                CURLERROR_RETVAL();
            }
            /* If the resulting string is NULL, return None */
            if (s_res == NULL) {
                Py_RETURN_NONE;
            }
            return PyText_FromString(s_res);

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


#if defined(HAVE_CURL_OPENSSL)
/* load ca certs from string */
static PyObject *
do_curl_set_ca_certs(CurlObject *self, PyObject *args)
{
    PyObject *cadata, *cadata_ascii;
    int res;

    if (!PyArg_ParseTuple(args, "O:cadata", &cadata))
        return NULL;

    cadata_ascii = PyUnicode_AsASCIIString(cadata);
    if (cadata_ascii == NULL) {
        PyErr_SetString(PyExc_TypeError,
                        "cadata should be an ASCII string or a "
                        "bytes-like object");
        return NULL;
    }

    Py_CLEAR(self->ca_certs_obj);
    self->ca_certs_obj = cadata_ascii;

    res = curl_easy_setopt(self->handle, CURLOPT_SSL_CTX_FUNCTION, (curl_ssl_ctx_callback) ssl_ctx_callback);
    if (res != CURLE_OK) {
        CURLERROR_RETVAL();
    }

    res = curl_easy_setopt(self->handle, CURLOPT_SSL_CTX_DATA, self);
    if (res != CURLE_OK) {
        CURLERROR_RETVAL();
    }

    Py_RETURN_NONE;
}
#endif


static PyObject *do_curl_getstate(CurlObject *self)
{
    PyErr_SetString(PyExc_TypeError, "Curl objects do not support serialization");
    return NULL;
}


static PyObject *do_curl_setstate(CurlObject *self, PyObject *args)
{
    PyErr_SetString(PyExc_TypeError, "Curl objects do not support deserialization");
    return NULL;
}


/*************************************************************************
// type definitions
**************************************************************************/

/* --------------- methods --------------- */

PYCURL_INTERNAL PyMethodDef curlobject_methods[] = {
    {"close", (PyCFunction)do_curl_close, METH_NOARGS, curl_close_doc},
    {"errstr", (PyCFunction)do_curl_errstr, METH_NOARGS, curl_errstr_doc},
    {"getinfo", (PyCFunction)do_curl_getinfo, METH_VARARGS, curl_getinfo_doc},
    {"pause", (PyCFunction)do_curl_pause, METH_VARARGS, curl_pause_doc},
    {"perform", (PyCFunction)do_curl_perform, METH_NOARGS, curl_perform_doc},
    {"setopt", (PyCFunction)do_curl_setopt, METH_VARARGS, curl_setopt_doc},
    {"setopt_string", (PyCFunction)do_curl_setopt_string, METH_VARARGS, curl_setopt_string_doc},
    {"unsetopt", (PyCFunction)do_curl_unsetopt, METH_VARARGS, curl_unsetopt_doc},
    {"reset", (PyCFunction)do_curl_reset, METH_NOARGS, curl_reset_doc},
#if defined(HAVE_CURL_OPENSSL)
    {"set_ca_certs", (PyCFunction)do_curl_set_ca_certs, METH_VARARGS, curl_set_ca_certs_doc},
#endif
    {"__getstate__", (PyCFunction)do_curl_getstate, METH_NOARGS, NULL},
    {"__setstate__", (PyCFunction)do_curl_setstate, METH_VARARGS, NULL},
    {NULL, NULL, 0, NULL}
};


/* --------------- setattr/getattr --------------- */


#if PY_MAJOR_VERSION >= 3

PYCURL_INTERNAL PyObject *
do_curl_getattro(PyObject *o, PyObject *n)
{
    PyObject *v = PyObject_GenericGetAttr(o, n);
    if( !v && PyErr_ExceptionMatches(PyExc_AttributeError) )
    {
        PyErr_Clear();
        v = my_getattro(o, n, ((CurlObject *)o)->dict,
                        curlobject_constants, curlobject_methods);
    }
    return v;
}

PYCURL_INTERNAL int
do_curl_setattro(PyObject *o, PyObject *name, PyObject *v)
{
    assert_curl_state((CurlObject *)o);
    return my_setattro(&((CurlObject *)o)->dict, name, v);
}

#else /* PY_MAJOR_VERSION >= 3 */

PYCURL_INTERNAL PyObject *
do_curl_getattr(CurlObject *co, char *name)
{
    assert_curl_state(co);
    return my_getattr((PyObject *)co, name, co->dict,
                      curlobject_constants, curlobject_methods);
}

PYCURL_INTERNAL int
do_curl_setattr(CurlObject *co, char *name, PyObject *v)
{
    assert_curl_state(co);
    return my_setattr(&co->dict, name, v);
}

#endif /* PY_MAJOR_VERSION >= 3 */

PYCURL_INTERNAL PyTypeObject Curl_Type = {
#if PY_MAJOR_VERSION >= 3
    PyVarObject_HEAD_INIT(NULL, 0)
#else
    PyObject_HEAD_INIT(NULL)
    0,                          /* ob_size */
#endif
    "pycurl.Curl",              /* tp_name */
    sizeof(CurlObject),         /* tp_basicsize */
    0,                          /* tp_itemsize */
    (destructor)do_curl_dealloc, /* tp_dealloc */
    0,                          /* tp_print */
#if PY_MAJOR_VERSION >= 3
    0,                          /* tp_getattr */
    0,                          /* tp_setattr */
#else
    (getattrfunc)do_curl_getattr,  /* tp_getattr */
    (setattrfunc)do_curl_setattr,  /* tp_setattr */
#endif
    0,                          /* tp_reserved */
    0,                          /* tp_repr */
    0,                          /* tp_as_number */
    0,                          /* tp_as_sequence */
    0,                          /* tp_as_mapping */
    0,                          /* tp_hash  */
    0,                          /* tp_call */
    0,                          /* tp_str */
#if PY_MAJOR_VERSION >= 3
    (getattrofunc)do_curl_getattro, /* tp_getattro */
    (setattrofunc)do_curl_setattro, /* tp_setattro */
#else
    0,                          /* tp_getattro */
    0,                          /* tp_setattro */
#endif
    0,                          /* tp_as_buffer */
    Py_TPFLAGS_HAVE_GC,         /* tp_flags */
    curl_doc,                   /* tp_doc */
    (traverseproc)do_curl_traverse, /* tp_traverse */
    (inquiry)do_curl_clear,     /* tp_clear */
    0,                          /* tp_richcompare */
    0,                          /* tp_weaklistoffset */
    0,                          /* tp_iter */
    0,                          /* tp_iternext */
    curlobject_methods,         /* tp_methods */
    0,                          /* tp_members */
    0,                          /* tp_getset */
    0,                          /* tp_base */
    0,                          /* tp_dict */
    0,                          /* tp_descr_get */
    0,                          /* tp_descr_set */
    0,                          /* tp_dictoffset */
    0,                          /* tp_init */
    PyType_GenericAlloc,        /* tp_alloc */
    (newfunc)do_curl_new,       /* tp_new */
    PyObject_GC_Del,            /* tp_free */
};

/* vi:ts=4:et:nowrap
 */
