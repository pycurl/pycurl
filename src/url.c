#include "pycurl.h"
#include "docstrings.h"

#ifdef HAVE_CURL_URL

/* The api_lock only exists on free-threaded builds; the GIL serialises
 * curl_url_* on every other build, so the macros compile away there. */
#ifdef Py_GIL_DISABLED
#  define PYCURL_URL_LOCK(u)   PYCURL_MUTEX_LOCK(&(u)->api_lock)
#  define PYCURL_URL_UNLOCK(u) PYCURL_MUTEX_UNLOCK(&(u)->api_lock)
#else
#  define PYCURL_URL_LOCK(u)   ((void)0)
#  define PYCURL_URL_UNLOCK(u) ((void)0)
#endif

/*************************************************************************
// static utility functions
**************************************************************************/

/* Raise pycurl.error from a CURLUcode. curl_url_strerror is 7.80.0+, so
 * older builds fall back to a fixed message. */
static int
check_url_result(CURLUcode res)
{
    const char *msg;
    PyObject *v;

    if (res == CURLUE_OK) {
        return 0;
    }
#if LIBCURL_VERSION_NUM >= MAKE_LIBCURL_VERSION(7, 80, 0)
    msg = curl_url_strerror(res);
#else
    msg = "libcurl URL API error";
#endif
    v = Py_BuildValue("(is)", (int)res, msg);
    if (v != NULL) {
        PyErr_SetObject(ErrorObject, v);
        Py_DECREF(v);
    }
    return -1;
}


/* Free the underlying handle. Nulls the pointer first so re-entry is safe. */
static void
util_url_close(CurlUrlObject *self)
{
    if (self->url_handle != NULL) {
        CURLU *handle = self->url_handle;
        self->url_handle = NULL;
        curl_url_cleanup(handle);
    }
}


/* Read one part. Returns a str, None when the part is absent, or NULL with an
 * exception set on a real error. Shared by getpart() and the property getters. */
static PyObject *
util_url_getpart(CurlUrlObject *self, CURLUPart part, unsigned int flags)
{
    char *out = NULL;
    CURLUcode res;
    PyObject *ret;

    if (self->url_handle == NULL) {
        PyErr_SetString(ErrorObject, "cannot use a CurlUrl without a handle");
        return NULL;
    }

    PYCURL_URL_LOCK(self);
    res = curl_url_get(self->url_handle, part, &out, flags);
    PYCURL_URL_UNLOCK(self);

    if (res == CURLUE_OK) {
        ret = PyText_FromString_Ignore(out);
        curl_free(out);
        return ret;
    }

    /* An absent part is not an error, it maps to None. */
    switch (res) {
    case CURLUE_NO_SCHEME:
    case CURLUE_NO_USER:
    case CURLUE_NO_PASSWORD:
    case CURLUE_NO_OPTIONS:
    case CURLUE_NO_HOST:
    case CURLUE_NO_PORT:
    case CURLUE_NO_QUERY:
    case CURLUE_NO_FRAGMENT:
#if LIBCURL_VERSION_NUM >= MAKE_LIBCURL_VERSION(7, 65, 0)
    case CURLUE_NO_ZONEID:
#endif
        Py_RETURN_NONE;
    default:
        check_url_result(res);
        return NULL;
    }
}


/* Set one part. value may be a str, bytes, None or NULL (the last two remove
 * the part). Shared by setpart() and the property setters and deleters. */
static PyObject *
util_url_setpart(CurlUrlObject *self, CURLUPart part, PyObject *value,
                 unsigned int flags)
{
    CURLUcode res;
    char *cstr = NULL;
    PyObject *encoded = NULL;

    if (self->url_handle == NULL) {
        PyErr_SetString(ErrorObject, "cannot use a CurlUrl without a handle");
        return NULL;
    }

    if (value != NULL && value != Py_None) {
        if (!PyText_Check(value)) {
            PyErr_SetString(PyExc_TypeError,
                "a URL part must be a string, bytes, or None");
            return NULL;
        }
        cstr = PyText_AsString_NoNUL(value, &encoded);
        if (cstr == NULL) {
            return NULL;
        }
    }

    PYCURL_URL_LOCK(self);
    res = curl_url_set(self->url_handle, part, cstr, flags);
    PYCURL_URL_UNLOCK(self);

    Py_XDECREF(encoded);

    if (res != CURLUE_OK) {
        check_url_result(res);
        return NULL;
    }
    Py_RETURN_NONE;
}


/* Clone the underlying handle into a fresh object. Backs __copy__/__deepcopy__. */
static PyObject *
util_url_dup(CurlUrlObject *self)
{
    CurlUrlObject *dup;
    CURLU *newhandle;
    int *ptr;

    if (self->url_handle == NULL) {
        PyErr_SetString(ErrorObject, "cannot copy a CurlUrl without a handle");
        return NULL;
    }

    dup = (CurlUrlObject *)Py_TYPE(self)->tp_alloc(Py_TYPE(self), 0);
    if (dup == NULL) {
        return NULL;
    }

    /* tp_alloc is expected to return zeroed memory */
    for (ptr = (int *) &dup->weakreflist;
        ptr < (int *) (((char *) dup) + sizeof(CurlUrlObject));
        ++ptr)
            assert(*ptr == 0);

    PYCURL_URL_LOCK(self);
    newhandle = curl_url_dup(self->url_handle);
    PYCURL_URL_UNLOCK(self);

    if (newhandle == NULL) {
        Py_DECREF(dup);
        return PyErr_NoMemory();
    }
    dup->url_handle = newhandle;
    return (PyObject *)dup;
}


/*************************************************************************
// constructor / destructor
**************************************************************************/

PYCURL_INTERNAL PyObject *
do_url_new(PyTypeObject *subtype, PyObject *args, PyObject *kwds)
{
    CurlUrlObject *self;
    PyObject *url = NULL;
    unsigned int flags = 0;
    int *ptr;
    static char *kwlist[] = {"url", "flags", NULL};

    if (subtype == p_CurlUrl_Type &&
        !PyArg_ParseTupleAndKeywords(args, kwds, "|OI:CurlUrl", kwlist,
                                     &url, &flags)) {
        return NULL;
    }

    self = (CurlUrlObject *) subtype->tp_alloc(subtype, 0);
    if (self == NULL) {
        return NULL;
    }

    /* tp_alloc is expected to return zeroed memory. On free-threaded builds this
     * leaves api_lock (a PyMutex) in its valid unlocked state. */
    for (ptr = (int *) &self->weakreflist;
        ptr < (int *) (((char *) self) + sizeof(CurlUrlObject));
        ++ptr)
            assert(*ptr == 0);

    self->url_handle = curl_url();
    if (self->url_handle == NULL) {
        Py_DECREF(self);
        return PyErr_NoMemory();
    }

    if (url != NULL && url != Py_None) {
        PyObject *ret = util_url_setpart(self, CURLUPART_URL, url, flags);
        if (ret == NULL) {
            Py_DECREF(self);
            return NULL;
        }
        Py_DECREF(ret);
    }

    return (PyObject *)self;
}


static int
do_url_traverse(CurlUrlObject *Py_UNUSED(self), visitproc Py_UNUSED(visit),
                void *Py_UNUSED(arg))
{
    /* CurlUrl holds no strong Python references, so there is nothing to visit.
     * GC support is kept only so Py_TPFLAGS_BASETYPE subclasses collect cleanly. */
    return 0;
}


static void
do_url_dealloc(CurlUrlObject *self)
{
    PyObject_GC_UnTrack(self);
    Py_TRASHCAN_BEGIN(self, do_url_dealloc);

    util_url_close(self);

    if (self->weakreflist != NULL) {
        PyObject_ClearWeakRefs((PyObject *) self);
    }

    CurlUrl_Type.tp_free(self);
    Py_TRASHCAN_END
}


/*************************************************************************
// methods
**************************************************************************/

static PyObject *
do_url_getpart(CurlUrlObject *self, PyObject *args)
{
    int part;
    unsigned int flags = 0;

    if (!PyArg_ParseTuple(args, "i|I:getpart", &part, &flags)) {
        return NULL;
    }
    return util_url_getpart(self, (CURLUPart)part, flags);
}


static PyObject *
do_url_setpart(CurlUrlObject *self, PyObject *args)
{
    int part;
    PyObject *value;
    unsigned int flags = 0;

    if (!PyArg_ParseTuple(args, "iO|I:setpart", &part, &value, &flags)) {
        return NULL;
    }
    return util_url_setpart(self, (CURLUPart)part, value, flags);
}


static PyObject *
do_url_copy(CurlUrlObject *self, PyObject *Py_UNUSED(ignored))
{
    return util_url_dup(self);
}


static PyObject *
do_url_deepcopy(CurlUrlObject *self, PyObject *Py_UNUSED(memo))
{
    return util_url_dup(self);
}


static PyObject *
do_url_getstate(CurlUrlObject *Py_UNUSED(self), PyObject *Py_UNUSED(ignored))
{
    PyErr_SetString(PyExc_TypeError, "CurlUrl objects do not support serialization");
    return NULL;
}


static PyObject *
do_url_setstate(CurlUrlObject *Py_UNUSED(self), PyObject *Py_UNUSED(args))
{
    PyErr_SetString(PyExc_TypeError, "CurlUrl objects do not support deserialization");
    return NULL;
}


/*************************************************************************
// str / repr
**************************************************************************/

static PyObject *
do_url_str(CurlUrlObject *self)
{
    PyObject *url = util_url_getpart(self, CURLUPART_URL, 0);

    if (url == NULL) {
        return NULL;
    }
    if (url == Py_None) {
        Py_DECREF(url);
        PyErr_SetString(ErrorObject, "cannot serialise an incomplete URL");
        return NULL;
    }
    return url;
}


static PyObject *
do_url_repr(CurlUrlObject *self)
{
    PyObject *url = util_url_getpart(self, CURLUPART_URL, 0);
    PyObject *repr;

    if (url == NULL) {
        PyErr_Clear();
    }
    if (url != NULL && url != Py_None) {
        repr = PyUnicode_FromFormat("<pycurl.CurlUrl \"%U\" at %p>", url, self);
    } else {
        repr = PyUnicode_FromFormat("<pycurl.CurlUrl (incomplete) at %p>", self);
    }
    Py_XDECREF(url);
    return repr;
}


/*************************************************************************
// properties
**************************************************************************/

static PyObject *
do_url_get_part_prop(CurlUrlObject *self, void *closure)
{
    return util_url_getpart(self, (CURLUPart)(size_t)closure, 0);
}


static int
do_url_set_part_prop(CurlUrlObject *self, PyObject *value, void *closure)
{
    PyObject *ret = util_url_setpart(self, (CURLUPart)(size_t)closure, value, 0);

    if (ret == NULL) {
        return -1;
    }
    Py_DECREF(ret);
    return 0;
}


/* Like do_url_set_part_prop, but also accepts an int for convenience. */
static int
do_url_set_port(CurlUrlObject *self, PyObject *value, void *closure)
{
    PyObject *strval = NULL;
    int rv;

    if (value != NULL && PyLong_Check(value)) {
        strval = PyObject_Str(value);
        if (strval == NULL) {
            return -1;
        }
        value = strval;
    }
    rv = do_url_set_part_prop(self, value, closure);
    Py_XDECREF(strval);
    return rv;
}


/*************************************************************************
// type definitions
**************************************************************************/

PYCURL_INTERNAL PyMethodDef curlurlobject_methods[] = {
    {"getpart", (PyCFunction)do_url_getpart, METH_VARARGS, url_getpart_doc},
    {"setpart", (PyCFunction)do_url_setpart, METH_VARARGS, url_setpart_doc},
    {"__copy__", (PyCFunction)do_url_copy, METH_NOARGS, NULL},
    {"__deepcopy__", (PyCFunction)do_url_deepcopy, METH_O, NULL},
    {"__getstate__", (PyCFunction)do_url_getstate, METH_NOARGS, NULL},
    {"__setstate__", (PyCFunction)do_url_setstate, METH_VARARGS, NULL},
    {NULL, NULL, 0, NULL}
};


PYCURL_INTERNAL PyGetSetDef curlurlobject_getsets[] = {
    {"url", (getter)do_url_get_part_prop, (setter)do_url_set_part_prop,
        url_url_doc, (void *)(size_t)CURLUPART_URL},
    {"scheme", (getter)do_url_get_part_prop, (setter)do_url_set_part_prop,
        url_scheme_doc, (void *)(size_t)CURLUPART_SCHEME},
    {"user", (getter)do_url_get_part_prop, (setter)do_url_set_part_prop,
        url_user_doc, (void *)(size_t)CURLUPART_USER},
    {"password", (getter)do_url_get_part_prop, (setter)do_url_set_part_prop,
        url_password_doc, (void *)(size_t)CURLUPART_PASSWORD},
    {"options", (getter)do_url_get_part_prop, (setter)do_url_set_part_prop,
        url_options_doc, (void *)(size_t)CURLUPART_OPTIONS},
    {"host", (getter)do_url_get_part_prop, (setter)do_url_set_part_prop,
        url_host_doc, (void *)(size_t)CURLUPART_HOST},
    {"port", (getter)do_url_get_part_prop, (setter)do_url_set_port,
        url_port_doc, (void *)(size_t)CURLUPART_PORT},
    {"path", (getter)do_url_get_part_prop, (setter)do_url_set_part_prop,
        url_path_doc, (void *)(size_t)CURLUPART_PATH},
    {"query", (getter)do_url_get_part_prop, (setter)do_url_set_part_prop,
        url_query_doc, (void *)(size_t)CURLUPART_QUERY},
    {"fragment", (getter)do_url_get_part_prop, (setter)do_url_set_part_prop,
        url_fragment_doc, (void *)(size_t)CURLUPART_FRAGMENT},
#if LIBCURL_VERSION_NUM >= MAKE_LIBCURL_VERSION(7, 65, 0)
    {"zoneid", (getter)do_url_get_part_prop, (setter)do_url_set_part_prop,
        url_zoneid_doc, (void *)(size_t)CURLUPART_ZONEID},
#endif
    {NULL, NULL, NULL, NULL, NULL}
};


PYCURL_INTERNAL PyTypeObject CurlUrl_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "pycurl.CurlUrl",           /* tp_name */
    sizeof(CurlUrlObject),      /* tp_basicsize */
    0,                          /* tp_itemsize */
    (destructor)do_url_dealloc, /* tp_dealloc */
    0,                          /* tp_print */
    0,                          /* tp_getattr */
    0,                          /* tp_setattr */
    0,                          /* tp_reserved */
    (reprfunc)do_url_repr,      /* tp_repr */
    0,                          /* tp_as_number */
    0,                          /* tp_as_sequence */
    0,                          /* tp_as_mapping */
    0,                          /* tp_hash  */
    0,                          /* tp_call */
    (reprfunc)do_url_str,       /* tp_str */
    0,                          /* tp_getattro */
    0,                          /* tp_setattro */
    0,                          /* tp_as_buffer */
    PYCURL_TYPE_FLAGS,          /* tp_flags */
    url_doc,                    /* tp_doc */
    (traverseproc)do_url_traverse, /* tp_traverse */
    0,                          /* tp_clear */
    0,                          /* tp_richcompare */
    offsetof(CurlUrlObject, weakreflist), /* tp_weaklistoffset */
    0,                          /* tp_iter */
    0,                          /* tp_iternext */
    curlurlobject_methods,      /* tp_methods */
    0,                          /* tp_members */
    curlurlobject_getsets,      /* tp_getset */
    0,                          /* tp_base */
    0,                          /* tp_dict */
    0,                          /* tp_descr_get */
    0,                          /* tp_descr_set */
    0,                          /* tp_dictoffset */
    0,                          /* tp_init */
    PyType_GenericAlloc,        /* tp_alloc */
    (newfunc)do_url_new,        /* tp_new */
    PyObject_GC_Del,            /* tp_free */
};

#endif /* HAVE_CURL_URL */
