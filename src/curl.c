/* cURL Python module by Kjetil Jacobsen <kjetilja @ cs.uit.no> */

#include "Python.h"
#include <curl/curl.h>
#include <string.h>
#include <stdlib.h>
#include <stdio.h>

static PyObject *ErrorObject;

typedef struct {
    PyObject_HEAD
    CURL *handle;
    char *url;
    struct HttpPost *httppost;
    struct curl_slist *httpheader;
    struct curl_slist *quote;
    struct curl_slist *postquote;
    PyObject *w_cb;
    PyObject *h_cb;
    PyObject *r_cb;
    PyObject *pro_cb;
    PyObject *pwd_cb;
    PyThreadState *state;
    char error[CURL_ERROR_SIZE];
} CurlObject;

staticforward PyTypeObject Curl_Type;

/* --------------------------------------------------------------------- */

static void
self_cleanup(CurlObject *self)
{
    if (self->handle != NULL) {
	curl_easy_cleanup(self->handle);
        self->handle = NULL;
    }
    if (self->url != NULL) {
	free(self->url);
	self->url = NULL;
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
    if (self->httppost != NULL) {
	curl_formfree(self->httppost);
	self->httppost = NULL;
    }
    Py_XDECREF(self->w_cb);
    Py_XDECREF(self->r_cb);
    Py_XDECREF(self->pro_cb);
    Py_XDECREF(self->pwd_cb);
    Py_XDECREF(self->h_cb);
}


static void
curl_dealloc(CurlObject *self)
{
    self_cleanup(self);
    PyObject_Del(self);
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
    arglist = Py_BuildValue("(s#)", (char *)ptr, size*nmemb);

    PyEval_AcquireThread(self->state);
    result = PyEval_CallObject(self->w_cb, arglist);
    Py_DECREF(arglist);
    if (result == NULL) {
	PyErr_Print();
	write_size = -1;
    }
    else
	write_size = (int)PyInt_AsLong(result);
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
    arglist = Py_BuildValue("(s#)", (char *)ptr, size*nmemb);

    PyEval_AcquireThread(self->state);
    result = PyEval_CallObject(self->h_cb, arglist);
    Py_DECREF(arglist);
    if (result == NULL) {
	PyErr_Print();
	write_size = -1;
    }
    else
	write_size = (int)PyInt_AsLong(result);
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
    arglist = Py_BuildValue("(iiii)", dltotal, dlnow, ultotal, ulnow);

    PyEval_AcquireThread(self->state);
    result = PyEval_CallObject(self->pro_cb, arglist);
    Py_DECREF(arglist);
    if (result == NULL) {
	PyErr_Print();
	ret = -1;
    }
    else
	ret = (int)PyInt_AsLong(result);
    Py_XDECREF(result);
    PyEval_ReleaseThread(self->state);
    return ret;
}


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
	    if (strlen(buf) > buflen) {
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
	    PyString_AsStringAndSize(result, &buf, &obj_size);
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
    int option;
    char *stringdata;
    long longdata;
    char *buf;
    PyObject *obj, *listitem;
    FILE *fp;
    int res;
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
	      option == CURLOPT_EGDSOCKET))
	    {
		PyErr_SetString(ErrorObject, "strings are not supported for this option");
		return NULL;
	    }
	if (option == CURLOPT_URL) {
	    /* Need to store uri for later use if the option is OPTCURL_URL */
	    buf = (char *)malloc((strlen(stringdata)*sizeof(char))+sizeof(char));
	    if (buf == NULL) {
		PyErr_SetString(ErrorObject, "unable to allocate memory for url");
		return NULL;
	    }
	    if (self->url != NULL) {
		free(self->url);
	    }
	    strcpy(buf, stringdata);
	    self->url = buf;
	    res = curl_easy_setopt(self->handle, CURLOPT_URL, self->url);
	} 
	else {
	    /* Handle the regular cases of string arguments */
	    res = curl_easy_setopt(self->handle, option, stringdata);
	}
	/* Check for errors */
	if (res == 0) {
	    Py_INCREF(Py_None);
	    return Py_None;
	} 
	else {
	    PyErr_SetString(ErrorObject, self->error);
	    return NULL;
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
	if (res == 0) {
	    Py_INCREF(Py_None);
	    return Py_None;
	} 
	else {
	    PyErr_SetString(ErrorObject, self->error);
	    return NULL;
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
	fp = PyFile_AsFile(obj);
	if (fp == NULL) {
	    PyErr_SetString(PyExc_TypeError, "second argument must be open file");
	    return NULL;
	}
	res = curl_easy_setopt(self->handle, option, fp);
	/* Check for errors */
	if (res == 0) {
	    Py_INCREF(Py_None);
	    return Py_None;
	} 
	else {
	    PyErr_SetString(ErrorObject, self->error);
	    return NULL;
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
		if (buf == NULL) {
		    PyErr_SetString(ErrorObject, "unable to allocate memory for list element");
		    return NULL;
		}
		strcpy(buf, str);
		res = curl_formparse(buf, &self->httppost, &last);
		if (res != 0) {
		    curl_formfree(self->httppost);
		    PyErr_SetString(ErrorObject, self->error);
		    return NULL;
		}
	    }
	    res = curl_easy_setopt(self->handle, CURLOPT_HTTPPOST, self->httppost);
	    /* Check for errors */
	    if (res == 0) {
		Py_INCREF(Py_None);
		return Py_None;
	    } 
	    else {
		curl_formfree(self->httppost);
		PyErr_SetString(ErrorObject, self->error);
		return NULL;
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
	    if (buf == NULL) {
		PyErr_SetString(ErrorObject, "unable to allocate memory for list element");
		return NULL;
	    }
	    strcpy(buf, str);
	    *slist = curl_slist_append(*slist, buf);
	}
	res = curl_easy_setopt(self->handle, option, *slist);
	/* Check for errors */
	if (res == 0) {
	    Py_INCREF(Py_None);
	    return Py_None;
	} 
	else {
	    curl_slist_free_all(*slist);
	    PyErr_SetString(ErrorObject, self->error);
	    return NULL;
	}
    }

    /* Handle the case of function objects for callbacks */
    if (PyArg_ParseTuple(args, "iO!:setopt", &option, &PyFunction_Type, &obj)) {
	switch(option) {
	case CURLOPT_WRITEFUNCTION:
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
	default:
	    /* None of the list options were recognized, throw exception */
	    PyErr_SetString(PyExc_TypeError, "functions are not supported for this option");
	    return NULL;
	}
	Py_INCREF(Py_None);
	return Py_None;
    }

    /* Failed to match any of the function signatures -- return error */
    PyErr_SetString(PyExc_TypeError, "invalid arguments to setopt");
    return NULL;
}


static PyObject *
do_perform(CurlObject *self, PyObject *args)
{
    int res;

    if (!PyArg_ParseTuple(args, ":perform")) {
	return NULL;
    }

    if (self->handle == NULL) {
	PyErr_SetString(ErrorObject, "cannot invoke perform, no curl handle");
	return NULL;
    }

    /* Save handle to current thread (used to run the callbacks in) */
    self->state = PyThreadState_New(PyThreadState_Get()->interp);

    /* Release global lock and start */
    Py_BEGIN_ALLOW_THREADS
    res = curl_easy_perform(self->handle);
    Py_END_ALLOW_THREADS
    
    if (res == 0) {
	Py_INCREF(Py_None);
	return Py_None;
    } 
    else {
	PyErr_SetString(ErrorObject, self->error);
	return NULL;
    }
}


static PyObject *
do_getinfo(CurlObject *self, PyObject *args)
{
    int option;
    int res;
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
		if (res == 0) {
		    return PyLong_FromLong(l_res);
		} 
		else {
		    PyErr_SetString(ErrorObject, self->error);
		    return NULL;
		}
	    }

	if (option == CURLINFO_EFFECTIVE_URL)
	    {
		/* Return string as result */
		res = curl_easy_getinfo(self->handle, option, &s_res);
		/* Check for errors and return result */
		if (res == 0) {
		    return PyString_FromString(s_res);
		} 
		else {
		    PyErr_SetString(ErrorObject, self->error);
		    return NULL;
		}
	    }

	if (option == CURLINFO_TOTAL_TIME ||
	    option == CURLINFO_NAMELOOKUP_TIME ||
	    option == CURLINFO_CONNECT_TIME ||
	    option == CURLINFO_PRETRANSFER_TIME ||
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
		if (res == 0) {
		    return PyFloat_FromDouble(d_res);
		} 
		else {
		    PyErr_SetString(ErrorObject, self->error);
		    return NULL;
		}
	    }
    } 

    /* Got wrong signature on the method call */
    PyErr_SetString(PyExc_TypeError, "invalid arguments to getinfo");
    return NULL;
}


/* --------------------------------------------------------------------- */

static PyMethodDef curlobject_methods[] = {
    {"cleanup", (PyCFunction)do_cleanup, METH_VARARGS, NULL},
    {"setopt", (PyCFunction)do_setopt, METH_VARARGS, NULL},
    {"perform", (PyCFunction)do_perform, METH_VARARGS, NULL},
    {"getinfo", (PyCFunction)do_getinfo, METH_VARARGS, NULL},
    {NULL, NULL}
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
    0,			    /*tp_hash*/
};

/* --------------------------------------------------------------------- */

static CurlObject *
do_init(PyObject *arg)
{
    CURL *curlhandle;
    CurlObject *self;
    int res;

    /* Initialize curl */
    curlhandle = curl_easy_init();
    if (curlhandle == NULL) {
	return NULL;
    }

    /* Allocate python curl object */
    self = PyObject_New(CurlObject, &Curl_Type);
    if (self == NULL) {
	curl_easy_cleanup(curlhandle);
	return NULL;
    }

    /* Set error buffer */
    res = curl_easy_setopt(curlhandle, CURLOPT_ERRORBUFFER, self->error);
    if (res != 0) {
	curl_easy_cleanup(curlhandle);
	return NULL;
    }
    memset(self->error, 0, sizeof(char) * CURL_ERROR_SIZE);

    /* Setup python curl object initial values and return object */
    self->handle = curlhandle;
    self->url = NULL;
    self->httpheader = NULL;
    self->quote = NULL;
    self->postquote = NULL;
    self->httppost = NULL;

    /* Set callback pointers to NULL */
    self->w_cb = NULL;
    self->h_cb = NULL;
    self->r_cb = NULL;
    self->pro_cb = NULL;
    self->pwd_cb = NULL;

    return self;
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
	if (res != 0) {
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


/* List of functions defined in the curl module */
static PyMethodDef curl_methods[] = {
    {"init", (PyCFunction)do_init, METH_VARARGS},
    {"global_cleanup", (PyCFunction)do_global_cleanup, METH_VARARGS},
    {"global_init", (PyCFunction)do_global_init, METH_VARARGS},
    {NULL, NULL}
};


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
    initcurl(void)
{
    PyObject *m, *d;

    /* Initialize the type of the new type object here; doing it here
     * is required for portability to Windows without requiring C++. */
    Curl_Type.ob_type = &PyType_Type;
  
    /* Create the module and add the functions */
    m = Py_InitModule("curl", curl_methods);
  
    /* Add error object to the module */
    d = PyModule_GetDict(m);
    ErrorObject = PyErr_NewException("curl.error", NULL, NULL);
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
    insint(d, "REQUEST_SIZE", CURLINFO_HEADER_SIZE);
    insint(d, "SSL_VERIFYRESULT", CURLINFO_SSL_VERIFYRESULT);
    insint(d, "FILETIME", CURLINFO_FILETIME);
    insint(d, "CONTENT_LENGTH_DOWNLOAD", CURLINFO_CONTENT_LENGTH_DOWNLOAD);
    insint(d, "CONTENT_LENGTH_UPLOAD", CURLINFO_CONTENT_LENGTH_UPLOAD);

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

    /* Initialize global interpreter lock */
    PyEval_InitThreads();
}
