/* $Id$ */

/* PycURL -- cURL Python module
 *
 * Authors:
 *  Kjetil Jacobsen <kjetilja at cs.uit.no>
 *  Markus F.X.J. Oberhumer <markus at oberhumer.com>
 *
 * Contributions:
 *  Tino Lange <Tino.Lange at gmx.de>
 *  Matt King <matt at gnik.com>
 *  Conrad Steenberg <conrad at hep.caltech.edu>
 *  Amit Mongia <amit_mongia at hotmail.com>
 *
 * See file COPYING for license information.
 *
 */

/*
    TODO for the multi interface:
    - add interface to the multi_read method, otherwise it's hard to use this
      for anything
    - how do we best interface with the fd_set stuff?
*/

#undef NDEBUG
#include <assert.h>
#include <stddef.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#if (defined(_WIN32) || defined(__WIN32__)) && !defined(WIN32)
#  define WIN32 1
#endif
#include <Python.h>
#include <curl/curl.h>
#include <curl/multi.h>


/* Ensure we have an updated libcurl */
#if !defined(LIBCURL_VERSION_NUM) || (LIBCURL_VERSION_NUM < 0x070908)
#  error "Need libcurl version 7.9.8 or greater to compile pycurl."
#endif

static PyObject *ErrorObject;

typedef struct {
    PyObject_HEAD
    PyObject *dict;                 /* Python attributes dictionary */
    CURLM *multi_handle;
    PyThreadState *state;
} CurlMultiObject;

typedef struct {
    PyObject_HEAD
    PyObject *dict;                 /* Python attributes dictionary */
    CURL *handle;
    PyThreadState *state;
    CurlMultiObject *multi_stack;   /* refcounted Python object */
    struct HttpPost *httppost;
    struct curl_slist *httpheader;
    struct curl_slist *quote;
    struct curl_slist *postquote;
    struct curl_slist *prequote;
    PyObject *w_cb;
    PyObject *h_cb;
    PyObject *r_cb;
    PyObject *pro_cb;
    PyObject *pwd_cb;
    PyObject *d_cb;
    PyObject *readdata;
    PyObject *writedata;
    PyObject *writeheader;
    int writeheader_set;
    char error[CURL_ERROR_SIZE];
    void *options[CURLOPT_LASTENTRY];
} CurlObject;

#if !defined(__cplusplus)
staticforward PyTypeObject Curl_Type;
staticforward PyTypeObject CurlMulti_Type;
#endif

#define CURLERROR() do {\
    PyObject *v; \
    v = Py_BuildValue("(is)", (int) (res), self->error); \
    PyErr_SetObject(ErrorObject, v); \
    Py_DECREF(v); \
    return NULL; \
} while (0)

#define CURLERROR2(msg) do {\
    PyObject *v; \
    v = Py_BuildValue("(is)", (int) (res), msg); \
    PyErr_SetObject(ErrorObject, v); \
    Py_DECREF(v); \
    return NULL; \
} while (0)


#undef UNUSED
#define UNUSED(var)     ((void)&var)


/*************************************************************************
// static utility functions
**************************************************************************/

static PyThreadState *
get_thread_state(const CurlObject *self)
{
    /* Get the thread state for callbacks to run in.
     * This is either `self->state' when running inside perform() or
     * `self->multi_stack->state' when running inside multi_perform().
     * This also implicitly asserts a valid `self->handle'.
     */
    if (self == NULL)
        return NULL;
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


/* assert some CurlObject invariants */
static void
assert_curl_object(const CurlObject *self)
{
    assert(self != NULL);
    assert(self->ob_type == &Curl_Type);
    (void) get_thread_state(self);
}


/* assert some CurlMultiObject invariants */
static void
assert_curl_multi_object(const CurlMultiObject *self)
{
    assert(self != NULL);
    assert(self->ob_type == &CurlMulti_Type);
    if (self->state != NULL) {
        assert(self->multi_handle != NULL);
    }
}


/*************************************************************************
// CurlObject
**************************************************************************/

/* --------------- construct/destruct (i.e. open/close) --------------- */

/* constructor - this is a module-level function returning a new instance */
static CurlObject *
do_init(PyObject *dummy, PyObject *args)
{
    CurlObject *self;
    int res;

    UNUSED(dummy);
    if (!PyArg_ParseTuple(args, ":do_init")) {
        return NULL;
    }

    /* Allocate python curl object */
#if (PY_VERSION_HEX < 0x01060000)
    self = (CurlObject *) PyObject_NEW(CurlObject, &Curl_Type);
#else
    self = (CurlObject *) PyObject_New(CurlObject, &Curl_Type);
#endif
    if (self == NULL)
        return NULL;

    /* Set python curl object initial values */
    self->dict = NULL;
    self->handle = NULL;
    self->state = NULL;
    self->multi_stack = NULL;
    self->httppost = NULL;
    self->httpheader = NULL;
    self->quote = NULL;
    self->postquote = NULL;
    self->prequote = NULL;

    /* Set callback pointers to NULL by default */
    self->w_cb = NULL;
    self->h_cb = NULL;
    self->r_cb = NULL;
    self->pro_cb = NULL;
    self->pwd_cb = NULL;
    self->d_cb = NULL;

    /* Set file object pointers to NULL by default */
    self->readdata = NULL;
    self->writedata = NULL;
    self->writeheader = NULL;
    self->writeheader_set = 0;

    /* Zero string pointer memory buffer used by setopt */
    memset(self->options, 0, sizeof(void *) * CURLOPT_LASTENTRY);

    /* Initialize curl handle */
    self->handle = curl_easy_init();
    if (self->handle == NULL)
        goto error;

    /* Set curl error buffer and zero it */
    res = curl_easy_setopt(self->handle, CURLOPT_ERRORBUFFER, self->error);
    if (res != CURLE_OK)
        goto error;
    memset(self->error, 0, sizeof(char) * CURL_ERROR_SIZE);

    /* Enable NOPROGRESS by default, i.e. no progress output */
    res = curl_easy_setopt(self->handle, CURLOPT_NOPROGRESS, 1);
    if (res != CURLE_OK)
        goto error;

    /* Disable VERBOSE by default, i.e. no verbose output */
    res = curl_easy_setopt(self->handle, CURLOPT_VERBOSE, 0);
    if (res != CURLE_OK)
        goto error;

    /* Success - return new object */
    return self;

error:
    Py_DECREF(self);    /* this also closes self->handle */
    PyErr_SetString(ErrorObject, "initializing curl failed");
    return NULL;
}


static void
self_cleanup(CurlObject *self)
{
    CURL *handle;
    int i;

    /* Zero handle and thread-state to disallow any operations to be run
     * from now on */
    assert(self != NULL);
    assert(self->ob_type == &Curl_Type);
    handle = self->handle;
    self->handle = NULL;
    if (handle == NULL) {
        /* Some paranoia assertions just to make sure the object
         * deallocation problem is finally really fixed... */
        assert(self->state == NULL);
        assert(self->multi_stack == NULL);
        return;             /* already closed */
    }
    self->state = NULL;

    /* Disconnect from multi_stack, remove_handle in any case */
    if (self->multi_stack != NULL) {
        CurlMultiObject *multi_stack = self->multi_stack;
        self->multi_stack = NULL;
        if (multi_stack->multi_handle != NULL && handle != NULL) {
            (void) curl_multi_remove_handle(multi_stack->multi_handle, handle);
        }
        Py_DECREF(multi_stack);
    }

    /* Free all variables allocated by setopt */
#undef SFREE
#define SFREE(v)   if (v != NULL) (curl_formfree(v), v = NULL)
    SFREE(self->httppost);
#undef SFREE
#define SFREE(v)   if (v != NULL) (curl_slist_free_all(v), v = NULL)
    SFREE(self->httpheader);
    SFREE(self->quote);
    SFREE(self->postquote);
    SFREE(self->prequote);
#undef SFREE
    for (i = 0; i < CURLOPT_LASTENTRY; i++) {
        if (self->options[i] != NULL) {
            free(self->options[i]);
            self->options[i] = NULL;
        }
    }

#undef XDECREF
#define XDECREF(v)  Py_XDECREF(v); v = NULL
    /* Decrement refcount for python callbacks */
    XDECREF(self->w_cb);
    XDECREF(self->r_cb);
    XDECREF(self->pro_cb);
    XDECREF(self->pwd_cb);
    XDECREF(self->h_cb);
    XDECREF(self->d_cb);
    /* Decrement refcount for python file objects */
    XDECREF(self->readdata);
    XDECREF(self->writedata);
    XDECREF(self->writeheader);
    self->writeheader_set = 0;
#undef XDECREF

    /* Finally free the curl handle */
    if (handle != NULL) {
        /* Must be done without the gil */
        Py_BEGIN_ALLOW_THREADS
        curl_easy_cleanup(handle);
        Py_END_ALLOW_THREADS
    }
}


static void
curl_dealloc(CurlObject *self)
{
    Py_XDECREF(self->dict);
    self_cleanup(self);
#if (PY_VERSION_HEX < 0x01060000)
    PyMem_DEL(self);
#else
    PyObject_Del(self);
#endif
}


static PyObject *
do_cleanup(CurlObject *self, PyObject *args)
{
    if (!PyArg_ParseTuple(args, ":cleanup")) {
        return NULL;
    }
    if (get_thread_state(self) != NULL) {
        PyErr_SetString(ErrorObject, "cannot invoke cleanup, perform() is running");
        return NULL;
    }
    self_cleanup(self);
    Py_INCREF(Py_None);
    return Py_None;
}


/* --------------- perform --------------- */

static PyObject *
do_perform(CurlObject *self, PyObject *args)
{
    int res;

    /* Sanity checks */
    if (!PyArg_ParseTuple(args, ":perform")) {
        return NULL;
    }

    if (self->handle == NULL) {
        PyErr_SetString(ErrorObject, "cannot invoke perform, no curl handle");
        return NULL;
    }
    if (get_thread_state(self) != NULL) {
        PyErr_SetString(ErrorObject, "cannot invoke perform - already running");
        return NULL;
    }

    /* Save handle to current thread (used as context for python callbacks) */
    self->state = PyThreadState_Get();
    assert(self->state != NULL);

    /* Release global lock and start */
    Py_BEGIN_ALLOW_THREADS
    res = curl_easy_perform(self->handle);
    Py_END_ALLOW_THREADS

    /* Zero thread-state to disallow callbacks to be run from now on */
    self->state = NULL;

    if (res != CURLE_OK) {
        CURLERROR();
    }
    Py_INCREF(Py_None);
    return Py_None;
}


/* --------------- callback handlers --------------- */

static size_t
do_write_callback(int flags,
                  char *ptr,
                  size_t size,
                  size_t nmemb,
                  void *stream)
{
    PyObject *arglist;
    PyObject *result;
    PyObject *cb;
    CurlObject *self;
    PyThreadState *tmp_state;
    int write_size;
    size_t ret = 0;     /* assume error */

    self = (CurlObject *)stream;
    tmp_state = get_thread_state(self);
    if (tmp_state == NULL) {
        return ret;
    }
    write_size = (int)(size * nmemb);
    if (write_size <= 0) {
        return ret;
    }
    cb = flags ? self->h_cb : self->w_cb;
    if (cb == NULL) {
        return ret;
    }

    PyEval_AcquireThread(tmp_state);
    arglist = Py_BuildValue("(s#)", ptr, write_size);
    result = PyEval_CallObject(cb, arglist);
    Py_DECREF(arglist);
    if (result == NULL) {
        PyErr_Print();
    }
    else if (result == Py_None) {               /* None means success */
        ret = write_size;
    }
    else {
        write_size = (int)PyInt_AsLong(result);
        if (write_size >= 0)
            ret = (size_t)write_size;                   /* success */
    }
    Py_XDECREF(result);
    PyEval_ReleaseThread(tmp_state);
    return ret;
}


static size_t
write_callback(char *ptr, size_t size, size_t nmemb, void *stream)
{
    return do_write_callback(0, ptr, size, nmemb, stream);
}

static size_t
header_callback(char *ptr, size_t size, size_t nmemb, void *stream)
{
    return do_write_callback(1, ptr, size, nmemb, stream);
}


static
size_t read_callback(char *ptr,
                  size_t size,
                  size_t nmemb,
                  void  *stream)
{
    PyObject *arglist;
    PyObject *result;
    CurlObject *self;
    PyThreadState *tmp_state;
    char *buf;
    int obj_size, read_size;
    size_t ret = 0;     /* assume error */

    self = (CurlObject *)stream;
    tmp_state = get_thread_state(self);
    if (tmp_state == NULL || self->r_cb == NULL) {
        return ret;
    }
    read_size = (int)(size * nmemb);
    if (read_size <= 0) {
        return ret;
    }

    PyEval_AcquireThread(tmp_state);
    arglist = Py_BuildValue("(i)", read_size);
    result = PyEval_CallObject(self->r_cb, arglist);
    Py_DECREF(arglist);
    if (result == NULL) {
        PyErr_Print();
    }
    else {
        if (!PyString_Check(result)) {
            PyErr_SetString(ErrorObject, "callback for READFUNCTION must return string");
            PyErr_Print();
        }
        else {
#if (PY_VERSION_HEX < 0x02000000)
            buf = PyString_AS_STRING(result);
            obj_size = PyString_GET_SIZE(result);
#else
            PyString_AsStringAndSize(result, &buf, &obj_size);
#endif
            if (obj_size > read_size) {
                PyErr_SetString(ErrorObject, "string from READFUNCTION callback is too long");
                PyErr_Print();
            }
            else {
                memcpy(ptr, buf, obj_size);
                ret = (size_t)obj_size;         /* success */
            }
        }
    }
    Py_XDECREF(result);
    PyEval_ReleaseThread(tmp_state);
    return ret;
}


static int
progress_callback(void *client,
                  double dltotal,
                  double dlnow,
                  double ultotal,
                  double ulnow)
{
    PyObject *arglist;
    PyObject *result;
    CurlObject *self;
    PyThreadState *tmp_state;
    int ret = 1;       /* assume error */

    self = (CurlObject *)client;
    tmp_state = get_thread_state(self);
    if (tmp_state == NULL || self->pro_cb == NULL) {
        return ret;
    }

    PyEval_AcquireThread(tmp_state);
    arglist = Py_BuildValue("(dddd)", dltotal, dlnow, ultotal, ulnow);
    result = PyEval_CallObject(self->pro_cb, arglist);
    Py_DECREF(arglist);
    if (result == NULL) {
        PyErr_Print();
    }
    else if (result == Py_None) {               /* None means success */
        ret = 0;
    }
    else {
        ret = (int)PyInt_AsLong(result);
    }
    Py_XDECREF(result);
    PyEval_ReleaseThread(tmp_state);
    return ret;
}


static
int password_callback(void *client,
                      const char *prompt,
                      char* buffer,
                      int buflen)
{
    PyObject *arglist;
    PyObject *result;
    CurlObject *self;
    PyThreadState *tmp_state;
    char *buf;
    int ret = 1;       /* assume error */

    self = (CurlObject *)client;
    tmp_state = get_thread_state(self);
    if (tmp_state == NULL || self->pwd_cb == NULL) {
        return ret;
    }

    PyEval_AcquireThread(tmp_state);
    arglist = Py_BuildValue("(si)", prompt, buflen);
    result = PyEval_CallObject(self->pwd_cb, arglist);
    Py_DECREF(arglist);
    if (result == NULL) {
        PyErr_Print();
    }
    else {
        if (!PyString_Check(result)) {
            PyErr_SetString(ErrorObject, "callback for PASSWDFUNCTION must return string");
            PyErr_Print();
        }
        else {
            buf = PyString_AsString(result);
            if ((int)strlen(buf) > buflen) {
                PyErr_SetString(ErrorObject, "string from PASSWDFUNCTION callback is too long");
                PyErr_Print();
            }
            else {
                strcpy(buffer, buf);
                ret = 0;        /* success */
            }
        }
    }
    Py_XDECREF(result);
    PyEval_ReleaseThread(tmp_state);
    return ret;
}


static
int debug_callback(CURL *curlobj,
                   curl_infotype type,
                   char *buffer,
                   size_t size,
                   void *data)
{
    PyObject *arglist;
    PyObject *result;
    CurlObject *self;
    PyThreadState *tmp_state;
    int ret = 0;       /* always success */

    UNUSED(curlobj);
    self = (CurlObject *)data;
    tmp_state = get_thread_state(self);
    if (tmp_state == NULL || self->d_cb == NULL) {
        return ret;
    }
    if ((int)size < 0) {
        return ret;
    }

    PyEval_AcquireThread(tmp_state);
    arglist = Py_BuildValue("(is#)", (int)type, buffer, (int)size);
    result = PyEval_CallObject(self->d_cb, arglist);
    Py_DECREF(arglist);
    if (result == NULL) {
        PyErr_Print();
    }
    PyEval_ReleaseThread(tmp_state);
    return ret;
}


/* --------------- setopt/getinfo --------------- */

static PyObject *
do_setopt(CurlObject *self, PyObject *args)
{
    int option, opt_masked;
    char *stringdata;
    long longdata;
    char *buf;
    PyObject *obj, *listitem;
    FILE *fp;
    int res = -1;
    struct curl_slist **slist;
    struct curl_slist *nlist;
    int len;
    char *str;
    int i;
    struct HttpPost *last;

    /* Check that we have a valid curl handle for the object */
    if (self->handle == NULL) {
        PyErr_SetString(ErrorObject, "cannot invoke setopt, no curl handle");
        return NULL;
    }
    if (get_thread_state(self) != NULL) {
        PyErr_SetString(ErrorObject, "cannot invoke setopt, perform() is running");
        return NULL;
    }

    /* Handle the case of string arguments */
    if (PyArg_ParseTuple(args, "is:setopt", &option, &stringdata)) {
        /* Check that the option specified a string as well as the input */
        if (!(option == CURLOPT_URL ||
              option == CURLOPT_PROXY ||
              option == CURLOPT_USERPWD ||
              option == CURLOPT_PROXYUSERPWD ||
              option == CURLOPT_RANGE ||
              option == CURLOPT_POSTFIELDS ||
              option == CURLOPT_REFERER ||
              option == CURLOPT_USERAGENT ||
              option == CURLOPT_FTPPORT ||
              option == CURLOPT_COOKIE ||
              option == CURLOPT_SSLCERT ||
              option == CURLOPT_SSLCERTPASSWD ||
              option == CURLOPT_COOKIEFILE ||
              option == CURLOPT_CUSTOMREQUEST ||
              option == CURLOPT_INTERFACE ||
              option == CURLOPT_KRB4LEVEL ||
              option == CURLOPT_CAINFO ||
              option == CURLOPT_CAPATH ||
              option == CURLOPT_RANDOM_FILE ||
              option == CURLOPT_COOKIEJAR ||
              option == CURLOPT_SSL_CIPHER_LIST ||
              option == CURLOPT_EGDSOCKET ||
              option == CURLOPT_SSLCERTTYPE ||
              option == CURLOPT_SSLKEY ||
              option == CURLOPT_SSLKEYTYPE ||
              option == CURLOPT_SSLKEYPASSWD ||
              option == CURLOPT_SSLENGINE))
            {
                PyErr_SetString(PyExc_TypeError, "strings are not supported for this option");
                return NULL;
            }
        /* Free previously allocated memory to option */
        opt_masked = option % CURLOPTTYPE_OBJECTPOINT;
        if (self->options[opt_masked] != NULL) {
            free(self->options[opt_masked]);
            self->options[opt_masked] = NULL;
        }
        /* Allocate memory to hold the string */
        buf = strdup(stringdata);
        if (buf == NULL) {
            return PyErr_NoMemory();
        }
        /* Call setopt */
        res = curl_easy_setopt(self->handle, option, buf);
        /* Check for errors */
        if (res != CURLE_OK) {
            free(buf);
            CURLERROR();
        }
        self->options[opt_masked] = buf;
        Py_INCREF(Py_None);
        return Py_None;
    }

    PyErr_Clear();

    /* Handle the case of integer arguments */
    if (PyArg_ParseTuple(args, "il:setopt", &option, &longdata)) {
        /* Check that option is integer as well as the input data */
        if (option >= CURLOPTTYPE_OBJECTPOINT && option != CURLOPT_FILETIME) {
            PyErr_SetString(PyExc_TypeError, "integers are not supported for this option");
            return NULL;
        }
        res = curl_easy_setopt(self->handle, option, longdata);
        /* Check for errors */
        if (res != CURLE_OK) {
            CURLERROR();
        }
        Py_INCREF(Py_None);
        return Py_None;
    }

    PyErr_Clear();

    /* Handle the case of file objects */
    if (PyArg_ParseTuple(args, "iO!:setopt", &option, &PyFile_Type, &obj)) {
        /* Ensure the option specified a file as well as the input */
        if (!(option == CURLOPT_WRITEDATA ||
              option == CURLOPT_READDATA ||
              option == CURLOPT_WRITEHEADER ||
              option == CURLOPT_PROGRESSDATA ||
              option == CURLOPT_PASSWDDATA))
            {
                PyErr_SetString(PyExc_TypeError, "files are not supported for this option");
                return NULL;
            }
        if (option == CURLOPT_WRITEHEADER) {
            if (self->w_cb != NULL) {
                PyErr_SetString(ErrorObject, "cannot combine WRITEHEADER with WRITEFUNCTION.");
                return NULL;
            }
        }
        fp = PyFile_AsFile(obj);
        if (fp == NULL) {
            PyErr_SetString(PyExc_TypeError, "second argument must be open file");
            return NULL;
        }
        res = curl_easy_setopt(self->handle, option, fp);
        /* Check for errors */
        if (res != CURLE_OK) {
            CURLERROR();
        }
        /* Increment reference to file object and register reference in curl object */
        Py_INCREF(obj);
        if (option == CURLOPT_WRITEDATA) {
            Py_XDECREF(self->writedata);
            self->writedata = obj;
        }
        if (option == CURLOPT_READDATA) {
            Py_XDECREF(self->readdata);
            self->readdata = obj;
        }
        if (option == CURLOPT_WRITEHEADER) {
            Py_XDECREF(self->writeheader);
            self->writeheader = obj;
            self->writeheader_set = 1;
        }
        /* Return success */
        Py_INCREF(Py_None);
        return Py_None;
    }

    PyErr_Clear();

    /* Handle the case of list objects */
    if (PyArg_ParseTuple(args, "iO!:setopt", &option, &PyList_Type, &obj)) {
        switch (option) {
        case CURLOPT_HTTPHEADER:
            slist = &self->httpheader;
            break;
        case CURLOPT_QUOTE:
            slist = &self->quote;
            break;
        case CURLOPT_POSTQUOTE:
            slist = &self->postquote;
            break;
        case CURLOPT_PREQUOTE:
            slist = &self->prequote;
            break;
        case CURLOPT_HTTPPOST:
            slist = NULL;
            break;
        default:
            /* None of the list options were recognized, throw exception */
            PyErr_SetString(PyExc_TypeError, "lists are not supported for this option");
            return NULL;
        }

        len = PyList_Size(obj);
        if (len == 0) {
            /* Empty list - do nothing */
            Py_INCREF(Py_None);
            return Py_None;
        }

        /* Handle HTTPPOST different since we construct a HttpPost form struct */
        if (option == CURLOPT_HTTPPOST) {
            /* Free previously allocated httppost */
            curl_formfree(self->httppost);
            self->httppost = NULL;

            last = NULL;
            for (i = 0; i < len; i++) {
                listitem = PyList_GetItem(obj, i);
                if (!PyString_Check(listitem)) {
                    curl_formfree(self->httppost);
                    self->httppost = NULL;
                    PyErr_SetString(PyExc_TypeError, "list items must be string objects");
                    return NULL;
                }
                str = PyString_AsString(listitem);
                res = curl_formparse(str, &self->httppost, &last);
                if (res != CURLE_OK) {
                    curl_formfree(self->httppost);
                    self->httppost = NULL;
                    CURLERROR();
                }
            }
            res = curl_easy_setopt(self->handle, CURLOPT_HTTPPOST, self->httppost);
            /* Check for errors */
            if (res != CURLE_OK) {
                curl_formfree(self->httppost);
                self->httppost = NULL;
                CURLERROR();
            }
            Py_INCREF(Py_None);
            return Py_None;
        }

        /* Just to be sure we do not bug off here */
        assert(slist != NULL);

        /* Free previously allocated list */
        curl_slist_free_all(*slist);
        *slist = NULL;

        /* Handle regular list operations on the other options */
        for (i = 0; i < len; i++) {
            listitem = PyList_GetItem(obj, i);
            if (!PyString_Check(listitem)) {
                curl_slist_free_all(*slist);
                *slist = NULL;
                PyErr_SetString(PyExc_TypeError, "list items must be string objects");
                return NULL;
            }
            /* INFO: curl_slist_append() internally does strdup() the data */
            str = PyString_AsString(listitem);
            nlist = curl_slist_append(*slist, str);
            if (nlist == NULL || nlist->data == NULL) {
                curl_slist_free_all(*slist);
                *slist = NULL;
                return PyErr_NoMemory();
            }
            *slist = nlist;
        }
        res = curl_easy_setopt(self->handle, option, *slist);
        /* Check for errors */
        if (res != CURLE_OK) {
            curl_slist_free_all(*slist);
            *slist = NULL;
            CURLERROR();
        }
        Py_INCREF(Py_None);
        return Py_None;
    }

    PyErr_Clear();

    /* Handle the case of function objects for callbacks */
    if (PyArg_ParseTuple(args, "iO!:setopt", &option, &PyFunction_Type, &obj) ||
        PyArg_ParseTuple(args, "iO!:setopt", &option, &PyCFunction_Type, &obj) ||
        PyArg_ParseTuple(args, "iO!:setopt", &option, &PyMethod_Type, &obj))
      {
        /* We use function types here to make sure that our callback
         * definitions exactly match the <curl/curl.h> interface.
         */
        const curl_write_callback w_cb = write_callback;
        const curl_read_callback r_cb = read_callback;
        const curl_write_callback h_cb = header_callback;
        const curl_progress_callback pro_cb = progress_callback;
        const curl_passwd_callback pwd_cb = password_callback;
        const curl_debug_callback d_cb = debug_callback;

        PyErr_Clear();

        switch(option) {
        case CURLOPT_WRITEFUNCTION:
            if (self->writeheader_set == 1) {
                PyErr_SetString(ErrorObject, "cannot combine WRITEFUNCTION with WRITEHEADER option.");
                return NULL;
            }
            Py_INCREF(obj);
            Py_XDECREF(self->writedata);
            Py_XDECREF(self->w_cb);
            self->w_cb = obj;
            curl_easy_setopt(self->handle, CURLOPT_WRITEFUNCTION, w_cb);
            curl_easy_setopt(self->handle, CURLOPT_WRITEDATA, self);
            break;
        case CURLOPT_READFUNCTION:
            Py_INCREF(obj);
            Py_XDECREF(self->readdata);
            Py_XDECREF(self->r_cb);
            self->r_cb = obj;
            curl_easy_setopt(self->handle, CURLOPT_READFUNCTION, r_cb);
            curl_easy_setopt(self->handle, CURLOPT_READDATA, self);
            break;
        case CURLOPT_HEADERFUNCTION:
            Py_INCREF(obj);
            Py_XDECREF(self->h_cb);
            self->h_cb = obj;
            curl_easy_setopt(self->handle, CURLOPT_HEADERFUNCTION, h_cb);
            curl_easy_setopt(self->handle, CURLOPT_WRITEHEADER, self);
            break;
        case CURLOPT_PROGRESSFUNCTION:
            Py_INCREF(obj);
            Py_XDECREF(self->pro_cb);
            self->pro_cb = obj;
            curl_easy_setopt(self->handle, CURLOPT_PROGRESSFUNCTION, pro_cb);
            curl_easy_setopt(self->handle, CURLOPT_PROGRESSDATA, self);
            break;
        case CURLOPT_PASSWDFUNCTION:
            Py_INCREF(obj);
            Py_XDECREF(self->pwd_cb);
            self->pwd_cb = obj;
            curl_easy_setopt(self->handle, CURLOPT_PASSWDFUNCTION, pwd_cb);
            curl_easy_setopt(self->handle, CURLOPT_PASSWDDATA, self);
            break;
        case CURLOPT_DEBUGFUNCTION:
            Py_INCREF(obj);
            Py_XDECREF(self->d_cb);
            self->d_cb = obj;
            curl_easy_setopt(self->handle, CURLOPT_DEBUGFUNCTION, d_cb);
            curl_easy_setopt(self->handle, CURLOPT_DEBUGDATA, self);
            break;
        default:
            /* None of the list options were recognized, throw exception */
            PyErr_SetString(PyExc_TypeError, "functions are not supported for this option");
            return NULL;
        }
        Py_INCREF(Py_None);
        return Py_None;
    }

    PyErr_Clear();

    /* Failed to match any of the function signatures -- return error */
    PyErr_SetString(PyExc_TypeError, "invalid arguments to setopt");
    return NULL;
}


static PyObject *
do_getinfo(CurlObject *self, PyObject *args)
{
    int option;
    int res;

    /* Check that we have a valid curl handle for the object */
    if (self->handle == NULL) {
        PyErr_SetString(ErrorObject, "cannot invoke getinfo, no curl handle");
        return NULL;
    }
    if (get_thread_state(self) != NULL) {
        PyErr_SetString(ErrorObject, "cannot invoke getinfo, perform() is running");
        return NULL;
    }

    /* Parse option */
    if (!PyArg_ParseTuple(args, "i:getinfo", &option)) {
        return NULL;
    }

    if (option == CURLINFO_HEADER_SIZE ||
        option == CURLINFO_REQUEST_SIZE ||
        option == CURLINFO_SSL_VERIFYRESULT ||
        option == CURLINFO_FILETIME ||
        option == CURLINFO_REDIRECT_COUNT ||
        option == CURLINFO_HTTP_CODE)
    {
        long l_res = -1;

        /* Return long as result */
        res = curl_easy_getinfo(self->handle, option, &l_res);
        /* Check for errors and return result */
        if (res != CURLE_OK) {
            CURLERROR();
        }
        return PyLong_FromLong(l_res);
    }

    if (option == CURLINFO_EFFECTIVE_URL ||
        option == CURLINFO_CONTENT_TYPE)
    {
        char *s_res = NULL;

        /* Return string as result */
        res = curl_easy_getinfo(self->handle, option, &s_res);
        /* Check for errors and return result */
        if (res != CURLE_OK) {
            CURLERROR();
        }
        /* If the resulting string is NULL, return None */
        if (s_res == NULL) {
            Py_INCREF(Py_None);
            return Py_None;
        }
        else {
            return PyString_FromString(s_res);
        }
    }

    if (option == CURLINFO_TOTAL_TIME ||
        option == CURLINFO_NAMELOOKUP_TIME ||
        option == CURLINFO_CONNECT_TIME ||
        option == CURLINFO_PRETRANSFER_TIME ||
        option == CURLINFO_STARTTRANSFER_TIME ||
        option == CURLINFO_SIZE_UPLOAD ||
        option == CURLINFO_SIZE_DOWNLOAD ||
        option == CURLINFO_SPEED_DOWNLOAD ||
        option == CURLINFO_SPEED_UPLOAD ||
        option == CURLINFO_CONTENT_LENGTH_DOWNLOAD ||
        option == CURLINFO_REDIRECT_TIME ||
        option == CURLINFO_CONTENT_LENGTH_UPLOAD)
    {
        double d_res = 0.0;

        /* Return float as result */
        res = curl_easy_getinfo(self->handle, option, &d_res);
        /* Check for errors and return result */
        if (res != CURLE_OK) {
            CURLERROR();
        }
        return PyFloat_FromDouble(d_res);
    }

    /* Got wrong option on the method call */
    PyErr_SetString(PyExc_ValueError, "invalid argument to getinfo");
    return NULL;
}


/*************************************************************************
// CurlMultiObject
**************************************************************************/

/* --------------- construct/destruct (i.e. open/close) --------------- */

/* constructor - this is a module-level function returning a new instance */
static CurlMultiObject *
do_multi_init(PyObject *dummy, PyObject *args)
{
    CurlMultiObject *self;

    UNUSED(dummy);
    if (!PyArg_ParseTuple(args, ":do_multi_init")) {
        return NULL;
    }

    /* Allocate python curl-multi object */
#if (PY_VERSION_HEX < 0x01060000)
    self = (CurlMultiObject *) PyObject_NEW(CurlMultiObject, &CurlMulti_Type);
#else
    self = (CurlMultiObject *) PyObject_New(CurlMultiObject, &CurlMulti_Type);
#endif
    if (self == NULL)
        return NULL;

    /* Initialize object attributes */
    self->dict = NULL;
    self->state = NULL;

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
self_multi_cleanup(CurlMultiObject *self)
{
    assert(self != NULL);
    self->state = NULL;
    if (self->multi_handle != NULL) {
        CURLM *multi_handle = self->multi_handle;
        self->multi_handle = NULL;
        curl_multi_cleanup(multi_handle);
    }
}

static void
curl_multi_dealloc(CurlMultiObject *self)
{
    Py_XDECREF(self->dict);
    self_multi_cleanup(self);
#if (PY_VERSION_HEX < 0x01060000)
    PyMem_DEL(self);
#else
    PyObject_Del(self);
#endif
}

static PyObject *
do_multi_cleanup(CurlMultiObject *self, PyObject *args)
{
    if (!PyArg_ParseTuple(args, ":cleanup")) {
        return NULL;
    }
    if (self->state != NULL) {
        PyErr_SetString(ErrorObject, "cannot invoke cleanup, perform() is running");
        return NULL;
    }
    self_multi_cleanup(self);
    Py_INCREF(Py_None);
    return Py_None;
}


/* --------------- perform --------------- */

static PyObject *
do_multi_perform(CurlMultiObject *self, PyObject *args)
{
    int res, running = -1;

    /* Sanity checks */
    if (!PyArg_ParseTuple(args, ":perform")) {
        return NULL;
    }

    if (self->multi_handle == NULL) {
        PyErr_SetString(ErrorObject, "cannot invoke perform, no curl-multi handle");
        return NULL;
    }
    if (self->state != NULL) {
        PyErr_SetString(ErrorObject, "cannot invoke perform - already running");
        return NULL;
    }

    /* Release global lock and start */
    self->state = PyThreadState_Get();
    assert(self->state != NULL);
    Py_BEGIN_ALLOW_THREADS
    res = curl_multi_perform(self->multi_handle, &running);
    Py_END_ALLOW_THREADS
    self->state = NULL;

    /* We assume these errors are ok, otherwise throw exception */
    if (res != CURLM_OK && res != CURLM_CALL_MULTI_PERFORM) {
        CURLERROR2("perform failed");
    }
    return PyInt_FromLong((long)running);
}


/* --------------- add_handle/remove_handle --------------- */

/* static utility function */
static int
check_curl_object(const CurlMultiObject *self, const CurlObject *obj)
{
    /* check CurlMultiObject status */
    assert_curl_multi_object(self);
    if (self->multi_handle == NULL) {
        PyErr_SetString(ErrorObject, "cannot add/remove handle - multi-stack is closed");
        return -1;
    }
    if (self->state != NULL) {
        PyErr_SetString(ErrorObject, "cannot add/remove handle - multi_perform() already running");
        return -1;
    }
    /* check CurlObject status */
    assert_curl_object(obj);
    if (obj->state != NULL) {
        PyErr_SetString(ErrorObject, "cannot add/remove handle - perform() of curl object already running");
        return -1;
    }
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
    int res;

    if (!PyArg_ParseTuple(args, "O!:add_handle", &Curl_Type, &obj)) {
        return NULL;
    }
    if (check_curl_object(self, obj) != 0) {
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
    if (res != CURLM_CALL_MULTI_PERFORM) {
        CURLERROR2("add_handle failed");
    }
    obj->multi_stack = self;
    Py_INCREF(self);
    Py_INCREF(Py_None);
    return Py_None;
}

static PyObject *
do_multi_remove_handle(CurlMultiObject *self, PyObject *args)
{
    CurlObject *obj;
    int res;

    if (!PyArg_ParseTuple(args, "O!:remove_handle", &Curl_Type, &obj)) {
        return NULL;
    }
    if (check_curl_object(self, obj) != 0) {
        return NULL;
    }
    if (obj->handle == NULL) {
        /* handle already closed -- ignore */
        goto done;
    }
    if (obj->multi_stack != self) {
        PyErr_SetString(ErrorObject, "curl object not on this multi-stack");
        return NULL;
    }
    res = curl_multi_remove_handle(self->multi_handle, obj->handle);
    if (res != CURLM_OK) {
        CURLERROR2("remove_handle failed");
    }
    assert(obj->multi_stack == self);
    obj->multi_stack = NULL;
    Py_DECREF(self);
done:
    Py_INCREF(Py_None);
    return Py_None;
}


/*************************************************************************
// type definitions
**************************************************************************/

/* --------------- methods --------------- */

static char co_cleanup_doc [] = "cleanup() -> None.  End curl session.\n";
static char co_perform_doc [] = "perform() -> None.  Perform a file transfer.  Throws pycurl.error exception upon failure.\n";
static char co_setopt_doc [] = "setopt(option, parameter) -> None.  Set curl session options.  Throws pycurl.error exception upon failure.\n";
static char co_getinfo_doc [] = "getinfo(info) -> res.  Extract and return information from a curl session.  Throws pycurl.error exception upon failure.\n";


static PyMethodDef curlobject_methods[] = {
    {"cleanup", (PyCFunction)do_cleanup, METH_VARARGS, co_cleanup_doc},
    {"perform", (PyCFunction)do_perform, METH_VARARGS, co_perform_doc},
    {"setopt", (PyCFunction)do_setopt, METH_VARARGS, co_setopt_doc},
    {"getinfo", (PyCFunction)do_getinfo, METH_VARARGS, co_getinfo_doc},
    {NULL, NULL, 0, NULL}
};

static PyMethodDef curlmultiobject_methods[] = {
    {"cleanup", (PyCFunction)do_multi_cleanup, METH_VARARGS, NULL},
    {"perform", (PyCFunction)do_multi_perform, METH_VARARGS, NULL},
    {"add_handle", (PyCFunction)do_multi_add_handle, METH_VARARGS, NULL},
    {"remove_handle", (PyCFunction)do_multi_remove_handle, METH_VARARGS, NULL},
    {NULL, NULL, 0, NULL}
};


/* --------------- setattr/getattr --------------- */

static int
my_setattr(PyObject **dict, char *name, PyObject *v)
{
    if (*dict == NULL) {
        *dict = PyDict_New();
        if (*dict == NULL)
            return -1;
    }
    if (v == NULL) {
        int rv = PyDict_DelItemString(*dict, name);
        if (rv < 0)
            PyErr_SetString(PyExc_AttributeError, "delete non-existing attribute");
        return rv;
    }
    return PyDict_SetItemString(*dict, name, v);
}

static PyObject *
my_getattr(PyObject *co, char *name, PyObject *dict, PyMethodDef *m)
{
    if (dict != NULL) {
        PyObject *v = PyDict_GetItemString(dict, name);
        if (v != NULL) {
            Py_INCREF(v);
            return v;
        }
    }
    return Py_FindMethod(m, co, name);
}

static int
curl_setattr(CurlObject *co, char *name, PyObject *v)
{
    assert_curl_object(co);
    return my_setattr(&co->dict, name, v);
}

static int
curl_multi_setattr(CurlMultiObject *co, char *name, PyObject *v)
{
    assert_curl_multi_object(co);
    return my_setattr(&co->dict, name, v);
}

static PyObject *
curl_getattr(CurlObject *co, char *name)
{
    assert_curl_object(co);
    return my_getattr((PyObject *)co, name, co->dict, curlobject_methods);
}

static PyObject *
curl_multi_getattr(CurlMultiObject *co, char *name)
{
    assert_curl_multi_object(co);
    return my_getattr((PyObject *)co, name, co->dict, curlmultiobject_methods);
}


/* --------------- actual type definitions --------------- */

statichere PyTypeObject Curl_Type = {
    PyObject_HEAD_INIT(NULL)
    0,                          /* ob_size */
    "Curl",                     /* tp_name */
    sizeof(CurlObject),         /* tp_basicsize */
    0,                          /* tp_itemsize */
    /* Methods */
    (destructor)curl_dealloc,   /* tp_dealloc */
    0,                          /* tp_print */
    (getattrfunc)curl_getattr,  /* tp_getattr */
    (setattrfunc)curl_setattr,  /* tp_setattr */
    0,                          /* tp_compare */
    0,                          /* tp_repr */
    0,                          /* tp_as_number */
    0,                          /* tp_as_sequence */
    0,                          /* tp_as_mapping */
    0                           /* tp_hash */
    /* More fields follow here, depending on your Python version.
     * You can safely ignore any compiler warnings.
     */
};

statichere PyTypeObject CurlMulti_Type = {
    PyObject_HEAD_INIT(NULL)
    0,                          /* ob_size */
    "CurlMulti",                /* tp_name */
    sizeof(CurlMultiObject),    /* tp_basicsize */
    0,                          /* tp_itemsize */
    /* Methods */
    (destructor)curl_multi_dealloc,   /* tp_dealloc */
    0,                          /* tp_print */
    (getattrfunc)curl_multi_getattr,  /* tp_getattr */
    (setattrfunc)curl_multi_setattr,  /* tp_setattr */
    0,                          /* tp_compare */
    0,                          /* tp_repr */
    0,                          /* tp_as_number */
    0,                          /* tp_as_sequence */
    0,                          /* tp_as_mapping */
    0                           /* tp_hash */
    /* More fields follow here, depending on your Python version.
     * You can safely ignore any compiler warnings.
     */
};


/*************************************************************************
// module level
// Note that the constructors are implemented as module-level functions.
**************************************************************************/

static PyObject *
do_global_init(PyObject *dummy, PyObject *args)
{
    int res, option;

    UNUSED(dummy);
    if (!PyArg_ParseTuple(args, "i:global_init", &option)) {
        return NULL;
    }

    if (!(option == CURL_GLOBAL_ALL ||
          option == CURL_GLOBAL_SSL ||
          option == CURL_GLOBAL_NOTHING)) {
        PyErr_SetString(PyExc_ValueError, "invalid option to global_init");
        return NULL;
    }

    res = curl_global_init(option);
    if (res != CURLE_OK) {
        PyErr_SetString(ErrorObject, "unable to set global option");
        return NULL;
    }

    Py_INCREF(Py_None);
    return Py_None;
}


static PyObject *
do_global_cleanup(PyObject *dummy, PyObject *args)
{
    UNUSED(dummy);
    if (!PyArg_ParseTuple(args, ":do_global_cleanup")) {
        return NULL;
    }

    curl_global_cleanup();
    Py_INCREF(Py_None);
    return Py_None;
}


/* Per function docstrings */
static char pycurl_global_init_doc [] =
"global_init(GLOBAL_ALL | GLOBAL_SSL | GLOBAL_NOTHING) -> None.  Initialize curl environment.\n";

static char pycurl_global_cleanup_doc [] =
"global_cleanup() -> None.  Cleanup curl environment.\n";

static char pycurl_init_doc [] =
"init() -> New curl object.  Implicitly calls global_init() if not called.\n";

static char pycurl_multi_init_doc [] =
"multi_init() -> New curl multi-object.\n";


/* List of functions defined in the curl module */
static PyMethodDef curl_methods[] = {
    {"global_init", (PyCFunction)do_global_init, METH_VARARGS, pycurl_global_init_doc},
    {"global_cleanup", (PyCFunction)do_global_cleanup, METH_VARARGS, pycurl_global_cleanup_doc},
    {"init", (PyCFunction)do_init, METH_VARARGS, pycurl_init_doc},
    {"multi_init", (PyCFunction)do_multi_init, METH_VARARGS, pycurl_multi_init_doc},
    {NULL, NULL, 0, NULL}
};


/* Module docstring */
static char module_doc [] =
"This module implements an interface to the cURL library.\n"
"\n"
"Functions:\n"
"\n"
"global_init(option) -> None.  Initialize curl environment.\n"
"global_cleanup() -> None.  Cleanup curl environment.\n"
"init() -> New curl object.  Create a new curl object.\n"
"multi_init() -> New curl multi-object.  Create a new curl multi-object.\n"
;


/* Helper function for inserting constants into the module namespace */
static void
insstr(PyObject *d, char *name, char *value)
{
    PyObject *v = PyString_FromString(value);
    if (!v || PyDict_SetItemString(d, name, v))
        PyErr_Clear();
    Py_XDECREF(v);
}

static void
insint(PyObject *d, char *name, int value)
{
    PyObject *v = PyInt_FromLong((long) value);
    if (!v || PyDict_SetItemString(d, name, v))
        PyErr_Clear();
    Py_XDECREF(v);
}


/* Initialization function for the module */
DL_EXPORT(void)
    initpycurl(void)
{
    PyObject *m, *d;

    /* Initialize the type of the new type object here; doing it here
     * is required for portability to Windows without requiring C++. */
    Curl_Type.ob_type = &PyType_Type;
    CurlMulti_Type.ob_type = &PyType_Type;

    /* Create the module and add the functions */
    m = Py_InitModule3("pycurl", curl_methods, module_doc);
    assert(m != NULL && PyModule_Check(m));

    /* Add error object to the module */
    d = PyModule_GetDict(m);
    assert(d != NULL);
    ErrorObject = PyErr_NewException("pycurl.error", NULL, NULL);
    PyDict_SetItemString(d, "error", ErrorObject);

    /* Add version string to the module */
    insstr(d, "version", curl_version());
    insstr(d, "__COMPILE_DATE__", __DATE__ " " __TIME__);

    /* Symbolic constants for setopt */
    insint(d, "FILE", CURLOPT_WRITEDATA);
    insint(d, "INFILE", CURLOPT_READDATA);
    insint(d, "WRITEDATA", CURLOPT_WRITEDATA);
    insint(d, "WRITEFUNCTION", CURLOPT_WRITEFUNCTION);
    insint(d, "READDATA", CURLOPT_READDATA);
    insint(d, "READFUNCTION", CURLOPT_READFUNCTION);
    insint(d, "INFILESIZE", CURLOPT_INFILESIZE);
    insint(d, "URL", CURLOPT_URL);
    insint(d, "PROXY", CURLOPT_PROXY);
    insint(d, "PROXYPORT", CURLOPT_PROXYPORT);
    insint(d, "HTTPPROXYTUNNEL", CURLOPT_HTTPPROXYTUNNEL);
    insint(d, "VERBOSE", CURLOPT_VERBOSE);
    insint(d, "HEADER", CURLOPT_HEADER);
    insint(d, "NOPROGRESS", CURLOPT_NOPROGRESS);
    insint(d, "NOBODY", CURLOPT_NOBODY);
    insint(d, "FAILNOERROR", CURLOPT_FAILONERROR);
    insint(d, "UPLOAD", CURLOPT_UPLOAD);
    insint(d, "POST", CURLOPT_POST);
    insint(d, "FTPLISTONLY", CURLOPT_FTPLISTONLY);
    insint(d, "FTPAPPEND", CURLOPT_FTPAPPEND);
    insint(d, "NETRC", CURLOPT_NETRC);
    insint(d, "FOLLOWLOCATION", CURLOPT_FOLLOWLOCATION);
    insint(d, "TRANSFERTEXT", CURLOPT_TRANSFERTEXT);
    insint(d, "PUT", CURLOPT_PUT);
    insint(d, "MUTE", CURLOPT_MUTE);
    insint(d, "USERPWD", CURLOPT_USERPWD);
    insint(d, "PROXYUSERPWD", CURLOPT_PROXYUSERPWD);
    insint(d, "RANGE", CURLOPT_RANGE);
    insint(d, "TIMEOUT", CURLOPT_TIMEOUT);
    insint(d, "POSTFIELDS", CURLOPT_POSTFIELDS);
    insint(d, "POSTFIELDSIZE", CURLOPT_POSTFIELDSIZE);
    insint(d, "REFERER", CURLOPT_REFERER);
    insint(d, "USERAGENT", CURLOPT_USERAGENT);
    insint(d, "FTPPORT", CURLOPT_FTPPORT);
    insint(d, "LOW_SPEED_LIMIT", CURLOPT_LOW_SPEED_LIMIT);
    insint(d, "LOW_SPEED_TIME", CURLOPT_LOW_SPEED_TIME);
    insint(d, "CURLOPT_RESUME_FROM", CURLOPT_RESUME_FROM);
    insint(d, "COOKIE", CURLOPT_COOKIE);
    insint(d, "HTTPHEADER", CURLOPT_HTTPHEADER);
    insint(d, "HTTPPOST", CURLOPT_HTTPPOST);
    insint(d, "SSLCERT", CURLOPT_SSLCERT);
    insint(d, "SSLCERTPASSWD", CURLOPT_SSLCERTPASSWD);
    insint(d, "CRLF", CURLOPT_CRLF);
    insint(d, "QUOTE", CURLOPT_QUOTE);
    insint(d, "POSTQUOTE", CURLOPT_POSTQUOTE);
    insint(d, "PREQUOTE", CURLOPT_PREQUOTE);
    insint(d, "WRITEHEADER", CURLOPT_WRITEHEADER);
    insint(d, "HEADERFUNCTION", CURLOPT_HEADERFUNCTION);
    insint(d, "COOKIEFILE", CURLOPT_COOKIEFILE);
    insint(d, "SSLVERSION", CURLOPT_SSLVERSION);
    insint(d, "TIMECONDITION", CURLOPT_TIMECONDITION);
    insint(d, "TIMEVALUE", CURLOPT_TIMEVALUE);
    insint(d, "CUSTOMREQUEST", CURLOPT_CUSTOMREQUEST);
    insint(d, "STDERR", CURLOPT_STDERR);
    insint(d, "INTERFACE", CURLOPT_INTERFACE);
    insint(d, "KRB4LEVEL", CURLOPT_KRB4LEVEL);
    insint(d, "PROGRESSFUNCTION", CURLOPT_PROGRESSFUNCTION);
    insint(d, "PROGRESSDATA", CURLOPT_PROGRESSDATA);
    insint(d, "SSL_VERIFYPEER", CURLOPT_SSL_VERIFYPEER);
    insint(d, "CAPATH", CURLOPT_CAINFO);
    insint(d, "CAINFO", CURLOPT_CAINFO);
    insint(d, "PASSWDFUNCTION", CURLOPT_PASSWDFUNCTION);
    insint(d, "PASSWDDATA", CURLOPT_PASSWDDATA);
    insint(d, "OPT_FILETIME", CURLOPT_FILETIME);
    insint(d, "MAXREDIRS", CURLOPT_MAXREDIRS);
    insint(d, "MAXCONNECTS", CURLOPT_MAXCONNECTS);
    insint(d, "CLOSEPOLICY", CURLOPT_CLOSEPOLICY);
    insint(d, "FRESH_CONNECT", CURLOPT_FRESH_CONNECT);
    insint(d, "FORBID_REUSE", CURLOPT_FORBID_REUSE);
    insint(d, "RANDOM_FILE", CURLOPT_RANDOM_FILE);
    insint(d, "EGDSOCKET", CURLOPT_EGDSOCKET);
    insint(d, "CONNECTTIMEOUT", CURLOPT_CONNECTTIMEOUT);

    insint(d, "HTTPGET", CURLOPT_HTTPGET);
    insint(d, "SSL_VERIFYHOST", CURLOPT_SSL_VERIFYHOST);
    insint(d, "COOKIEJAR", CURLOPT_COOKIEJAR);
    insint(d, "SSL_CIPHER_LIST", CURLOPT_SSL_CIPHER_LIST);
    insint(d, "HTTP_VERSION", CURLOPT_HTTP_VERSION);
    insint(d, "HTTP_VERSION_1_0", CURL_HTTP_VERSION_1_0);
    insint(d, "HTTP_VERSION_1_1", CURL_HTTP_VERSION_1_1);
    insint(d, "FTP_USE_EPSV", CURLOPT_FTP_USE_EPSV);

    insint(d, "SSLCERTTYPE", CURLOPT_SSLCERTTYPE);
    insint(d, "SSLKEY", CURLOPT_SSLKEY);
    insint(d, "SSLKEYTYPE", CURLOPT_SSLKEYTYPE);
    insint(d, "SSLKEYPASSWD", CURLOPT_SSLKEYPASSWD);
    insint(d, "SSLENGINE", CURLOPT_SSLENGINE);
    insint(d, "SSLENGINE_DEFAULT", CURLOPT_SSLENGINE_DEFAULT);

    insint(d, "DNS_CACHE_TIMEOUT", CURLOPT_DNS_CACHE_TIMEOUT);
    insint(d, "DNS_USE_GLOBAL_CACHE", CURLOPT_DNS_USE_GLOBAL_CACHE);

    insint(d, "DEBUGFUNCTION", CURLOPT_DEBUGFUNCTION);

    /* Symbolic constants for getinfo */
    insint(d, "EFFECTIVE_URL", CURLINFO_EFFECTIVE_URL);
    insint(d, "HTTP_CODE", CURLINFO_HTTP_CODE);
    insint(d, "TOTAL_TIME", CURLINFO_TOTAL_TIME);
    insint(d, "NAMELOOKUP_TIME", CURLINFO_NAMELOOKUP_TIME);
    insint(d, "CONNECT_TIME", CURLINFO_CONNECT_TIME);
    insint(d, "PRETRANSFER_TIME", CURLINFO_PRETRANSFER_TIME);
    insint(d, "SIZE_UPLOAD", CURLINFO_SIZE_UPLOAD);
    insint(d, "SIZE_DOWNLOAD", CURLINFO_SIZE_DOWNLOAD);
    insint(d, "SPEED_DOWNLOAD", CURLINFO_SPEED_DOWNLOAD);
    insint(d, "SPEED_UPLOAD", CURLINFO_SPEED_UPLOAD);
    insint(d, "REQUEST_SIZE", CURLINFO_REQUEST_SIZE);
    insint(d, "HEADER_SIZE", CURLINFO_HEADER_SIZE);
    insint(d, "SSL_VERIFYRESULT", CURLINFO_SSL_VERIFYRESULT);
    insint(d, "INFO_FILETIME", CURLINFO_FILETIME);
    insint(d, "CONTENT_LENGTH_DOWNLOAD", CURLINFO_CONTENT_LENGTH_DOWNLOAD);
    insint(d, "CONTENT_LENGTH_UPLOAD", CURLINFO_CONTENT_LENGTH_UPLOAD);
    insint(d, "STARTTRANSFER_TIME", CURLINFO_STARTTRANSFER_TIME);
    insint(d, "CONTENT_TYPE", CURLINFO_CONTENT_TYPE);
    insint(d, "REDIRECT_TIME", CURLINFO_REDIRECT_TIME);
    insint(d, "REDIRECT_COUNT", CURLINFO_REDIRECT_COUNT);

    /* CLOSEPOLICY constants for setopt */
    insint(d, "CLOSEPOLICY_LEAST_RECENTLY_USED", CURLCLOSEPOLICY_LEAST_RECENTLY_USED);
    insint(d, "CLOSEPOLICY_OLDEST", CURLCLOSEPOLICY_OLDEST);
    insint(d, "CLOSEPOLICY_LEAST_TRAFFIC", CURLCLOSEPOLICY_LEAST_TRAFFIC);
    insint(d, "CLOSEPOLICY_SLOWEST", CURLCLOSEPOLICY_SLOWEST);
    insint(d, "CLOSEPOLICY_CALLBACK", CURLCLOSEPOLICY_CALLBACK);

    /* NETRC constants for setopt */
    insint(d, "NETRC_OPTIONAL", CURL_NETRC_OPTIONAL);
    insint(d, "NETRC_IGNORED", CURL_NETRC_IGNORED);
    insint(d, "NETRC_REQUIRED", CURL_NETRC_REQUIRED);

    /* TIMECONDITION constants for setopt */
    insint(d, "TIMECOND_IFMODSINCE", TIMECOND_IFMODSINCE);
    insint(d, "TIMECOND_IFUNMODSINCE", TIMECOND_IFUNMODSINCE);

    /* global_init options */
    insint(d, "GLOBAL_ALL", CURL_GLOBAL_ALL);
    insint(d, "GLOBAL_NOTHING", CURL_GLOBAL_NOTHING);
    insint(d, "GLOBAL_SSL", CURL_GLOBAL_SSL);

    /* Debug callback types */
    insint(d, "TEXT", CURLINFO_TEXT);
    insint(d, "HEADER_IN", CURLINFO_HEADER_IN);
    insint(d, "HEADER_OUT", CURLINFO_HEADER_OUT);
    insint(d, "DATA_IN", CURLINFO_DATA_IN);
    insint(d, "DATA_OUT", CURLINFO_DATA_OUT);

    /* Initialize global interpreter lock */
    PyEval_InitThreads();
}

/* vi:ts=4:et
 */
