/* $Id$ */

/* cURL Python module by Kjetil Jacobsen <kjetilja @ cs.uit.no> */

#include "Python.h"
#include <curl/curl.h>
#include <string.h>
#include <stdlib.h>
#include <stdio.h>
#include <assert.h>

/* Ensure we have an updated libcurl */
#if LIBCURL_VERSION_NUM < 0x070906
  #error "Need libcurl version 7.9.6 or greater to compile pycurl."
#endif

static PyObject *ErrorObject;

typedef struct {
    PyObject_HEAD
    CURL *handle;
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
    PyThreadState *state;
    int writeheader_set;
    char error[CURL_ERROR_SIZE];
    void *options[CURLOPT_LASTENTRY];
} CurlObject;

#if !defined(__cplusplus)
staticforward PyTypeObject Curl_Type;
#endif

#define CURLERROR() \
{\
    PyObject *v; \
    v = Py_BuildValue("(is)", res, self->error); \
    PyErr_SetObject(ErrorObject, v); \
    Py_DECREF(v); \
    return NULL; \
}

/* --------------------------------------------------------------------- */

static void
self_cleanup(CurlObject *self)
{
    int i;

    if (self->handle == NULL) {
        return;
    }
    if (self->handle != NULL) {
        CURL *handle = self->handle;
        self->handle = NULL;
        Py_BEGIN_ALLOW_THREADS
	curl_easy_cleanup(handle);
        Py_END_ALLOW_THREADS
    }
    if (self->httpheader != NULL) {
	curl_slist_free_all(self->httpheader);
	self->httpheader = NULL;
    }
    if (self->quote != NULL) {
	curl_slist_free_all(self->quote);
	self->quote = NULL;
    }
    if (self->postquote != NULL) {
	curl_slist_free_all(self->postquote);
	self->postquote = NULL;
    }
    if (self->prequote != NULL) {
	curl_slist_free_all(self->prequote);
	self->prequote = NULL;
    }
    if (self->httppost != NULL) {
	curl_formfree(self->httppost);
	self->httppost = NULL;
    }
    for (i = 0; i < CURLOPT_LASTENTRY; i++) {
	if (self->options[i] != NULL) {
	    free(self->options[i]);
	    self->options[i] = NULL;
	}
    }
    self->state = NULL;
    Py_XDECREF(self->w_cb);
    Py_XDECREF(self->r_cb);
    Py_XDECREF(self->pro_cb);
    Py_XDECREF(self->pwd_cb);
    Py_XDECREF(self->h_cb);
    Py_XDECREF(self->d_cb);
}


static void
curl_dealloc(CurlObject *self)
{
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
    self_cleanup(self);
    Py_INCREF(Py_None);
    return Py_None;
}

/* --------------------------------------------------------------------- */

static int
write_callback(void *ptr,
	       size_t size,
	       size_t nmemb,
	       FILE  *stream)
{
    PyObject *arglist;
    PyObject *result;
    CurlObject *self;
    int write_size;

    self = (CurlObject *)stream;

    /* Check whether we got a file object or a curl object */
    if (self->state == NULL) {
	return -1;
    }

    arglist = Py_BuildValue("(s#)", (char *)ptr, size*nmemb);
    PyEval_AcquireThread(self->state);
    result = PyEval_CallObject(self->w_cb, arglist);
    Py_DECREF(arglist);
    if (result == NULL) {
	PyErr_Print();
	write_size = -1;
    }
    else if (result == Py_None) {               /* None means success */
        write_size = (int)(size * nmemb);
    }
    else {
        write_size = (int)PyInt_AsLong(result);
    }
    Py_XDECREF(result);
    PyEval_ReleaseThread(self->state);
    return write_size;
}


static int
header_callback(void *ptr,
		size_t size,
		size_t nmemb,
		FILE  *stream)
{
    PyObject *arglist;
    PyObject *result;
    CurlObject *self;
    int write_size;

    self = (CurlObject *)stream;

    /* Check whether we got a file object or a curl object */
    if (self->state == NULL) {
	return -1;
    }

    arglist = Py_BuildValue("(s#)", (char *)ptr, size*nmemb);
    PyEval_AcquireThread(self->state);
    result = PyEval_CallObject(self->h_cb, arglist);
    Py_DECREF(arglist);
    if (result == NULL) {
	PyErr_Print();
	write_size = -1;
    }
    else if (result == Py_None) {               /* None means success */
        write_size = (int)(size * nmemb);
    }
    else {
        write_size = (int)PyInt_AsLong(result);
    }
    Py_XDECREF(result);
    PyEval_ReleaseThread(self->state);
    return write_size;
}


static int
progress_callback(void *client,
		  size_t dltotal,
		  size_t dlnow,
		  size_t ultotal,
		  size_t ulnow)
{
    PyObject *arglist;
    PyObject *result;
    CurlObject *self;
    int ret;

    self = (CurlObject *)client;

    /* Check whether we got a file object or a curl object */
    if (self->state == NULL) {
	return -1;
    }

    arglist = Py_BuildValue("(iiii)", dltotal, dlnow, ultotal, ulnow);
    PyEval_AcquireThread(self->state);
    result = PyEval_CallObject(self->pro_cb, arglist);
    Py_DECREF(arglist);
    if (result == NULL) {
	PyErr_Print();
	ret = -1;
    }
    else if (result == Py_None) {               /* None means success */
        ret = 0;
    }
    else {
	ret = (int)PyInt_AsLong(result);
    }
    Py_XDECREF(result);
    PyEval_ReleaseThread(self->state);
    return ret;
}


static
int password_callback(void *client,
		      char *prompt,
		      char* buffer,
		      int buflen)
{
    PyObject *arglist;
    PyObject *result;
    CurlObject *self;
    char *buf;
    int ret;

    self = (CurlObject *)client;

    /* Check whether we got a file object or a curl object */
    if (self->state == NULL) {
	return -1;
    }

    arglist = Py_BuildValue("(si)", prompt, buflen);
    PyEval_AcquireThread(self->state);
    result = PyEval_CallObject(self->pwd_cb, arglist);
    Py_DECREF(arglist);
    if (result == NULL) {
	PyErr_Print();
	ret = -1;
    }
    else {
	if (!PyString_Check(result)) {
	    PyErr_SetString(ErrorObject, "callback for PASSWDFUNCTION must return string");
	    PyErr_Print();
	    ret = -1;
	}
	else {
	    buf = PyString_AsString(result);
	    if ((int)strlen(buf) > buflen) {
		PyErr_SetString(ErrorObject, "string from PASSWDFUNCTION callback is too long");
		PyErr_Print();
		ret = -1;
	    }
	    else {
		strcpy(buffer, buf);
		ret = 0;
	    }
	}
    }
    Py_XDECREF(result);
    PyEval_ReleaseThread(self->state);
    return ret;
}


static
int debug_callback(CURL *curlobj,
		   curl_infotype type,
		   char *buffer,
		   int size,
		   void *data)
{
    PyObject *arglist;
    PyObject *result;
    CurlObject *self;

    self = (CurlObject *)data;

    /* Check whether we got a file object or a curl object */
    if (self->state == NULL) {
	return 0;
    }

    arglist = Py_BuildValue("(is#)", type, buffer, size);
    PyEval_AcquireThread(self->state);
    result = PyEval_CallObject(self->d_cb, arglist);
    Py_DECREF(arglist);
    if (result == NULL) {
	PyErr_Print();
    }
    PyEval_ReleaseThread(self->state);
    return 0;
}


static
int read_callback(void *ptr,
		  size_t size,
		  size_t nmemb,
		  void  *stream)
{
    PyObject *arglist;
    PyObject *result;
    CurlObject *self;
    char *buf;
    int obj_size, read_size;
    int ret;

    self = (CurlObject *)stream;

    /* Check whether we got a file object or a curl object */
    if (self->state == NULL) {
	return -1;
    }

    read_size = size*nmemb;
    arglist = Py_BuildValue("(i)", read_size);
    PyEval_AcquireThread(self->state);
    result = PyEval_CallObject(self->r_cb, arglist);
    Py_DECREF(arglist);
    if (result == NULL) {
	PyErr_Print();
	ret = -1;
    }
    else {
	if (!PyString_Check(result)) {
	    PyErr_SetString(ErrorObject, "callback for READFUNCTION must return string");
	    PyErr_Print();
	    ret = -1;
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
		ret = -1;
	    }
	    else {
		memcpy(ptr, buf, obj_size);
		ret = obj_size;
	    }
	}
    }
    Py_XDECREF(result);
    PyEval_ReleaseThread(self->state);
    return ret;
}


/* --------------------------------------------------------------------- */

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
    int len;
    char *str;
    int i;
    struct HttpPost *last;

    /* Check that we have a valid curl handle for the object */
    if (self->handle == NULL) {
	PyErr_SetString(ErrorObject, "cannot invoke setopt, no curl handle");
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
		PyErr_SetString(ErrorObject, "strings are not supported for this option");
		return NULL;
	    }
	/* Free previously allocated memory to option */
	opt_masked = option % CURLOPTTYPE_OBJECTPOINT;
	if (self->options[opt_masked] != NULL) {
	    free(self->options[opt_masked]);
	}
	/* Allocate memory to hold the string */
	buf = (char *)malloc((strlen(stringdata)*sizeof(char))+sizeof(char));
	if (buf == NULL) {
	    return PyErr_NoMemory();
	}
	strcpy(buf, stringdata);
	self->options[opt_masked] = buf;
	/* Call setopt */
	res = curl_easy_setopt(self->handle, option,
			       (char *)self->options[opt_masked]);
	/* Check for errors */
	if (res == CURLE_OK) {
	    Py_INCREF(Py_None);
	    return Py_None;
	}
	else {
	    CURLERROR();
	}
    }

    PyErr_Clear();

    /* Handle the case of integer arguments */
    if (PyArg_ParseTuple(args, "il:setopt", &option, &longdata)) {
	/* Check that option is integer as well as the input data */
	if (option >= CURLOPTTYPE_OBJECTPOINT) {
	    PyErr_SetString(ErrorObject, "integers are not supported for this option");
	    return NULL;
	}
	res = curl_easy_setopt(self->handle, option, longdata);
	/* Check for errors */
	if (res == CURLE_OK) {
	    Py_INCREF(Py_None);
	    return Py_None;
	}
	else {
	    CURLERROR();
	}
    }

    PyErr_Clear();

    /* Handle the case of file objects */
    if (PyArg_ParseTuple(args, "iO!:setopt", &option, &PyFile_Type, &obj)) {
	/* Ensure the option specified a file as well as the input */
	if (!(option == CURLOPT_FILE ||
	      option == CURLOPT_INFILE ||
	      option == CURLOPT_WRITEHEADER ||
	      option == CURLOPT_PROGRESSDATA ||
	      option == CURLOPT_PASSWDDATA))
	    {
		PyErr_SetString(PyExc_TypeError, "files are not supported for this option");
		return NULL;
	    }
        if (option == CURLOPT_WRITEHEADER) {
	    self->writeheader_set = 1;
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
	if (res == CURLE_OK) {
	    Py_INCREF(Py_None);
	    return Py_None;
	}
	else {
  	    CURLERROR();
	}
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

	/* Handle HTTPPOST different since we construct a HttpPost form struct */
	if (option == CURLOPT_HTTPPOST) {
	    if (self->httppost != NULL) {
		curl_formfree(self->httppost);
		self->httppost = NULL;
	    }
	    len = PyList_Size(obj);
	    last = NULL;
	    for (i = 0; i < len; i++) {
		listitem = PyList_GetItem(obj, i);
		if (!PyString_Check(listitem)) {
		    PyErr_SetString(PyExc_TypeError, "list items must be string objects");
		    curl_formfree(self->httppost);
		    return NULL;
		}
		str = PyString_AsString(listitem);
		buf = (char *)malloc((sizeof(char)*strlen(str)) + sizeof(char));
		if (buf == NULL)
		    return PyErr_NoMemory();
		strcpy(buf, str);
		res = curl_formparse(buf, &self->httppost, &last);
		if (res != CURLE_OK) {
		    curl_formfree(self->httppost);
                    CURLERROR();
		}
	    }
	    res = curl_easy_setopt(self->handle, CURLOPT_HTTPPOST, self->httppost);
	    /* Check for errors */
	    if (res == CURLE_OK) {
		Py_INCREF(Py_None);
		return Py_None;
	    }
	    else {
		curl_formfree(self->httppost);
		CURLERROR();
	    }
	}

	/* Just to be sure we do not bug off here */
	assert(slist != NULL);

	/* Handle regular list operations on the other options */
	if (*slist != NULL) {
	    /* Free previously allocated list */
	    curl_slist_free_all(*slist);
	    *slist = NULL;
	}
	len = PyList_Size(obj);
	for (i = 0; i < len; i++) {
	    listitem = PyList_GetItem(obj, i);
	    if (!PyString_Check(listitem)) {
		curl_slist_free_all(*slist);
		PyErr_SetString(PyExc_TypeError, "list items must be string objects");
		return NULL;
	    }
	    str = PyString_AsString(listitem);
	    buf = (char *)malloc((sizeof(char)*strlen(str)) + sizeof(char));
	    if (buf == NULL)
	        return PyErr_NoMemory();
	    strcpy(buf, str);
	    *slist = curl_slist_append(*slist, buf);
	}
	res = curl_easy_setopt(self->handle, option, *slist);
	/* Check for errors */
	if (res == CURLE_OK) {
	    Py_INCREF(Py_None);
	    return Py_None;
	}
	else {
	    curl_slist_free_all(*slist);
	    CURLERROR();
	}
    }

    PyErr_Clear();

    /* Handle the case of function objects for callbacks */
    if (PyArg_ParseTuple(args, "iO!:setopt", &option, &PyFunction_Type, &obj) ||
	PyArg_ParseTuple(args, "iO!:setopt", &option, &PyCFunction_Type, &obj) ||
	PyArg_ParseTuple(args, "iO!:setopt", &option, &PyMethod_Type, &obj))
      {
	PyErr_Clear();

	switch(option) {
	case CURLOPT_WRITEFUNCTION:
	    if (self->writeheader_set == 1) {
	        PyErr_SetString(ErrorObject, "cannot combine WRITEFUNCTION with WRITEHEADER option.");
	        return NULL;
	    }
	    Py_INCREF(obj);
	    Py_XDECREF(self->w_cb);
	    self->w_cb = obj;
	    curl_easy_setopt(self->handle, CURLOPT_WRITEFUNCTION, write_callback);
	    curl_easy_setopt(self->handle, CURLOPT_FILE, self);
	    break;
	case CURLOPT_READFUNCTION:
	    Py_INCREF(obj);
	    Py_XDECREF(self->r_cb);
	    self->r_cb = obj;
	    curl_easy_setopt(self->handle, CURLOPT_READFUNCTION, read_callback);
	    curl_easy_setopt(self->handle, CURLOPT_INFILE, self);
	    break;
	case CURLOPT_HEADERFUNCTION:
	    Py_INCREF(obj);
	    Py_XDECREF(self->h_cb);
	    self->h_cb = obj;
	    curl_easy_setopt(self->handle, CURLOPT_HEADERFUNCTION, header_callback);
	    curl_easy_setopt(self->handle, CURLOPT_WRITEHEADER, self);
	    break;
	case CURLOPT_PROGRESSFUNCTION:
	    Py_INCREF(obj);
	    Py_XDECREF(self->pro_cb);
	    self->pro_cb = obj;
	    curl_easy_setopt(self->handle, CURLOPT_PROGRESSFUNCTION, progress_callback);
	    curl_easy_setopt(self->handle, CURLOPT_PROGRESSDATA, self);
	    break;
	case CURLOPT_PASSWDFUNCTION:
	    Py_INCREF(obj);
	    Py_XDECREF(self->pwd_cb);
	    self->pwd_cb = obj;
	    curl_easy_setopt(self->handle, CURLOPT_PASSWDFUNCTION, password_callback);
	    curl_easy_setopt(self->handle, CURLOPT_PASSWDDATA, self);
	    break;
	case CURLOPT_DEBUGFUNCTION:
	    Py_INCREF(obj);
	    Py_XDECREF(self->d_cb);
	    self->d_cb = obj;
	    curl_easy_setopt(self->handle, CURLOPT_DEBUGFUNCTION, debug_callback);
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

    /* Save handle to current thread (used to run the callbacks in) */
    self->state = PyThreadState_Get();

    /* Release global lock and start */
    Py_BEGIN_ALLOW_THREADS
    res = curl_easy_perform(self->handle);
    Py_END_ALLOW_THREADS

    if (res == CURLE_OK) {
	Py_INCREF(Py_None);
	return Py_None;
    }
    else {
        CURLERROR();
    }
}


static PyObject *
do_getinfo(CurlObject *self, PyObject *args)
{
    int option;
    int res = -1;
    double d_res;
    long l_res;
    char *s_res;

    /* Check that we have a valid curl handle for the object */
    if (self->handle == NULL) {
	PyErr_SetString(ErrorObject, "cannot invoke getinfo, no curl handle");
	return NULL;
    }

    /* Parse option */
    if (PyArg_ParseTuple(args, "i:getinfo", &option)) {
	if (option == CURLINFO_HEADER_SIZE ||
	    option == CURLINFO_REQUEST_SIZE ||
	    option == CURLINFO_SSL_VERIFYRESULT ||
	    option == CURLINFO_FILETIME ||
	    option == CURLINFO_HTTP_CODE)
	    {
		/* Return long as result */
		res = curl_easy_getinfo(self->handle, option, &l_res);
		/* Check for errors and return result */
		if (res == CURLE_OK) {
		    return PyLong_FromLong(l_res);
		}
		else {
		    CURLERROR();
		}
	    }

	if (option == CURLINFO_EFFECTIVE_URL ||
            option == CURLINFO_CONTENT_TYPE)
	    {
		/* Return string as result */
		res = curl_easy_getinfo(self->handle, option, &s_res);
		/* Check for errors and return result */
		if (res == CURLE_OK) {
		    return PyString_FromString(s_res);
		}
		else {
		    CURLERROR();
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
	    option == CURLINFO_CONTENT_LENGTH_UPLOAD)
	    {
		/* Return float as result */
		res = curl_easy_getinfo(self->handle, option, &d_res);
		/* Check for errors and return result */
		if (res == CURLE_OK) {
		    return PyFloat_FromDouble(d_res);
		}
		else {
		    CURLERROR();
		}
	    }
    }

    /* Got wrong signature on the method call */
    PyErr_SetString(PyExc_TypeError, "invalid arguments to getinfo");
    return NULL;
}

/* --------------------------------------------------------------------- */

static char co_cleanup_doc [] = "cleanup() -> None.  End curl session.\n";
static char co_setopt_doc [] = "setopt(option, parameter) -> None.  Set curl session options.  Throws pycurl.error exception upon failure.\n";
static char co_perform_doc [] = "perform() -> None.  Perform a file transfer.  Throws pycurl.error exception upon failure.\n";
static char co_getinfo_doc [] = "getinfo(info, parameter) -> res.  Extract and return information from a curl session.  Throws pycurl.error exception upon failure.\n";


static PyMethodDef curlobject_methods[] = {
    {"cleanup", (PyCFunction)do_cleanup, METH_VARARGS, co_cleanup_doc},
    {"setopt", (PyCFunction)do_setopt, METH_VARARGS, co_setopt_doc},
    {"perform", (PyCFunction)do_perform, METH_VARARGS, co_perform_doc},
    {"getinfo", (PyCFunction)do_getinfo, METH_VARARGS, co_getinfo_doc},
    {NULL, NULL, 0, NULL}
};


static PyObject *
curl_getattr(CurlObject *co, char *name)
{
    return Py_FindMethod(curlobject_methods, (PyObject *)co, name);
}


statichere PyTypeObject Curl_Type = {
    PyObject_HEAD_INIT(NULL)
    0,			/*ob_size*/
    "Curl",	        /*tp_name*/
    sizeof(CurlObject),	/*tp_basicsize*/
    0,			/*tp_itemsize*/
    /* Methods */
    (destructor)curl_dealloc, /*dealloc*/
    0,   	              /*tp_print*/
    (getattrfunc)curl_getattr,/*getattr*/
    0,                        /*setattr*/
    0,			    /*tp_compare*/
    0,			    /*tp_repr*/
    0,			    /*tp_as_number*/
    0,			    /*tp_as_sequence*/
    0,			    /*tp_as_mapping*/
    0			    /*tp_hash*/
    /* More fields follow here, depending on your Python version.
     * You can safely ignore any compiler warnings.
     */
};

/* --------------------------------------------------------------------- */

static CurlObject *
do_init(PyObject *arg)
{
    CurlObject *self;
    int res;

    /* Allocate python curl object */
#if (PY_VERSION_HEX < 0x01060000)
    self = (CurlObject *) PyObject_NEW(CurlObject, &Curl_Type);
#else
    self = (CurlObject *) PyObject_New(CurlObject, &Curl_Type);
#endif
    if (self == NULL)
	return NULL;

    /* Setup python curl object initial values */
    self->handle = NULL;
    self->httpheader = NULL;
    self->quote = NULL;
    self->postquote = NULL;
    self->prequote = NULL;
    self->httppost = NULL;
    self->state = NULL;
    self->writeheader_set = 0;

    /* Set callback pointers to NULL */
    self->w_cb = NULL;
    self->h_cb = NULL;
    self->r_cb = NULL;
    self->pro_cb = NULL;
    self->pwd_cb = NULL;
    self->d_cb = NULL;

    /* Initialize curl */
    self->handle = curl_easy_init();
    if (self->handle == NULL)
        goto error;

    /* Set error buffer */
    res = curl_easy_setopt(self->handle, CURLOPT_ERRORBUFFER, self->error);
    if (res != CURLE_OK)
        goto error;
    memset(self->error, 0, sizeof(char) * CURL_ERROR_SIZE);

    /* Zero memory buffer for setopt */
    memset(self->options, 0, sizeof(void *) * CURLOPT_LASTENTRY);

    /* Enable NOPROGRESS by default */
    res = curl_easy_setopt(self->handle, CURLOPT_NOPROGRESS, 1);
    if (res != CURLE_OK)
        goto error;

    /* Disable VERBOSE by default */
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


static PyObject *
do_global_cleanup(PyObject *arg)
{
    curl_global_cleanup();
    Py_INCREF(Py_None);
    return Py_None;
}


static PyObject *
do_global_init(PyObject *self, PyObject *args)
{
    int res, option;

    if (PyArg_ParseTuple(args, "i:global_init", &option)) {
	if (!(option == CURL_GLOBAL_ALL ||
	      option == CURL_GLOBAL_SSL ||
	      option == CURL_GLOBAL_NOTHING)) {
	    PyErr_SetString(ErrorObject, "invalid option to global_init");
	    return NULL;
	}

	res = curl_global_init(option);
	if (res != CURLE_OK) {
	    PyErr_SetString(ErrorObject, "unable to set global option");
	    return NULL;
	}
	else {
	    Py_INCREF(Py_None);
	    return Py_None;
	}
    }
    PyErr_SetString(ErrorObject, "invalid option to global_init");
    return NULL;
}


/* Per function docstrings */
static char pycurl_init_doc [] =
"init() -> New curl object.  Implicitly calls global_init() if not called.\n";

static char pycurl_global_init_doc [] =
"global_init(GLOBAL_ALL | GLOBAL_SSL | GLOBAL_NOTHING) -> None.  Initialize curl environment.\n";

static char pycurl_global_cleanup_doc [] =
"global_cleanup() -> None.  Cleanup curl environment.\n";


/* List of functions defined in the curl module */
static PyMethodDef curl_methods[] = {
    {"init", (PyCFunction)do_init, METH_VARARGS, pycurl_init_doc},
    {"global_cleanup", (PyCFunction)do_global_cleanup, METH_VARARGS, pycurl_global_cleanup_doc},
    {"global_init", (PyCFunction)do_global_init, METH_VARARGS, pycurl_global_init_doc},
    {NULL, NULL, 0, NULL}
};


/* Module docstring */
static char module_doc [] =
"This module implements an interface to the cURL library.\n\
\n\
Functions:\n\
\n\
global_init(option) -> None.  Initialize curl environment.\n\
global_cleanup() -> None.  Cleanup curl environment.\n\
init() -> New curl object.  Create a new curl object.\n\
";


/* Helper function for inserting constants into the module namespace */
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

    /* Create the module and add the functions */
    m = Py_InitModule3("pycurl", curl_methods, module_doc);

    /* Add error object to the module */
    d = PyModule_GetDict(m);
    ErrorObject = PyErr_NewException("pycurl.error", NULL, NULL);
    PyDict_SetItemString(d, "error", ErrorObject);

    /* Add version string to the module */
    PyDict_SetItemString(d, "version", PyString_FromString(curl_version()));

    /* Symbolic constants for setopt */
    insint(d, "FILE", CURLOPT_FILE);
    insint(d, "WRITEFUNCTION", CURLOPT_WRITEFUNCTION);
    insint(d, "INFILE", CURLOPT_INFILE);
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
    insint(d, "CAINFO", CURLOPT_CAINFO);
    insint(d, "PASSWDFUNCTION", CURLOPT_PASSWDFUNCTION);
    insint(d, "PASSWDDATA", CURLOPT_PASSWDDATA);
    insint(d, "FILETIME", CURLOPT_FILETIME);
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
    insint(d, "FILETIME", CURLINFO_FILETIME);
    insint(d, "CONTENT_LENGTH_DOWNLOAD", CURLINFO_CONTENT_LENGTH_DOWNLOAD);
    insint(d, "CONTENT_LENGTH_UPLOAD", CURLINFO_CONTENT_LENGTH_UPLOAD);
    insint(d, "STARTTRANSFER_TIME", CURLINFO_STARTTRANSFER_TIME);
    insint(d, "CONTENT_TYPE", CURLINFO_CONTENT_TYPE);

    /* CLOSEPOLICY constants for setopt */
    insint(d, "CLOSEPOLICY_LEAST_RECENTLY_USED", CURLCLOSEPOLICY_LEAST_RECENTLY_USED);
    insint(d, "CLOSEPOLICY_OLDEST", CURLCLOSEPOLICY_OLDEST);
    insint(d, "CLOSEPOLICY_LEAST_TRAFFIC", CURLCLOSEPOLICY_LEAST_TRAFFIC);
    insint(d, "CLOSEPOLICY_SLOWEST", CURLCLOSEPOLICY_SLOWEST);
    insint(d, "CLOSEPOLICY_CALLBACK", CURLCLOSEPOLICY_CALLBACK);

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

/*
vi:ts=8
*/
