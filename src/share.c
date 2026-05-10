#include "pycurl.h"
#include "docstrings.h"

#define PYCURL_SHARE_API_LOCK(s)   PYCURL_MUTEX_LOCK(&(s)->api_lock)
#define PYCURL_SHARE_API_UNLOCK(s) PYCURL_MUTEX_UNLOCK(&(s)->api_lock)
/*************************************************************************
// static utility functions
**************************************************************************/

PYCURL_INTERNAL int
share_register_easy(CurlShareObject *share, CurlObject *easy)
{
    PyObject *wr;

    assert(share != NULL);
    assert(easy != NULL);

    wr = PyWeakref_NewRef((PyObject *)easy, NULL);
    if (wr == NULL) {
        return -1;
    }

    PYCURL_SHARE_API_LOCK(share);

    if (share->share_handle == NULL || share->easy_weakrefs == NULL) {
        PyErr_SetString(ErrorObject, "CurlShare is closed");
        goto error;
    }

    if (PySet_Add(share->easy_weakrefs, wr) < 0) {
        goto error;
    }

    PYCURL_SHARE_API_UNLOCK(share);
    Py_DECREF(wr);
    return 0;

error:
    PYCURL_SHARE_API_UNLOCK(share);
    Py_DECREF(wr);
    return -1;
}


PYCURL_INTERNAL void
share_unregister_easy(CurlShareObject *share, CurlObject *easy)
{
    PyObject *wr;

    assert(share != NULL);
    assert(easy != NULL);

    wr = PyWeakref_NewRef((PyObject *)easy, NULL);
    if (wr == NULL) {
        PyErr_Clear();
        return;
    }

    PYCURL_SHARE_API_LOCK(share);

    if (share->easy_weakrefs == NULL) {
        PYCURL_SHARE_API_UNLOCK(share);
        Py_DECREF(wr);
        return;
    }

    if (PySet_Discard(share->easy_weakrefs, wr) < 0) {
        PyErr_Clear();
    }

    PYCURL_SHARE_API_UNLOCK(share);
    Py_DECREF(wr);
}


/* assert some CurlShareObject invariants */
static void
assert_share_state(const CurlShareObject *self)
{
    assert(self != NULL);
    assert(PyObject_IsInstance((PyObject *) self, (PyObject *) p_CurlShare_Type) == 1);
    assert(self->lock != NULL);
}


/* check state for methods (mirrors check_curl_state / check_multi_state) */
static int
check_share_state(const CurlShareObject *self, int flags, const char *name)
{
    assert_share_state(self);
    if ((flags & PYCURL_REQUIRE_HANDLE) && self->share_handle == NULL) {
        PyErr_Format(ErrorObject, "cannot invoke %s() - no share handle", name);
        return -1;
    }
    return 0;
}


static int
check_share_setopt_result(CURLSHcode res)
{
    if (res == CURLSHE_OK) {
        return 0;
    }
    PyObject *v = Py_BuildValue("(is)", (int)res, curl_share_strerror(res));
    if (v != NULL) {
        PyErr_SetObject(ErrorObject, v);
        Py_DECREF(v);
    }
    return -1;
}


/* Apply SH_SHARE/SH_UNSHARE for one CURL_LOCK_DATA_* kind; caller holds api_lock. */
static int
share_setopt_one(CurlShareObject *self, int option, long data_kind)
{
    switch (data_kind) {
    case CURL_LOCK_DATA_COOKIE:
    case CURL_LOCK_DATA_DNS:
    case CURL_LOCK_DATA_SSL_SESSION:
#if LIBCURL_VERSION_NUM >= MAKE_LIBCURL_VERSION(7, 57, 0)
    case CURL_LOCK_DATA_CONNECT:
#endif
#if LIBCURL_VERSION_NUM >= MAKE_LIBCURL_VERSION(7, 61, 0)
    case CURL_LOCK_DATA_PSL:
#endif
        break;
    default:
        PyErr_SetString(PyExc_TypeError, "invalid arguments to setopt");
        return -1;
    }
    return check_share_setopt_result(
        curl_share_setopt(self->share_handle, option, data_kind));
}


/* constructor */
PYCURL_INTERNAL CurlShareObject *
do_share_new(PyTypeObject *subtype, PyObject *args, PyObject *kwds)
{
    int res;
    CurlShareObject *self;
    const curl_lock_function lock_cb = share_lock_callback;
    const curl_unlock_function unlock_cb = share_unlock_callback;
    int *ptr;
    static char *kwlist[] = {"detach_on_close", NULL};
    int detach_on_close = 1;
    if (subtype == p_CurlShare_Type && !PyArg_ParseTupleAndKeywords(args, kwds, "|$p", kwlist, &detach_on_close)) {
        return NULL;
    }

    /* Allocate python curl-share object */
    self = (CurlShareObject *) subtype->tp_alloc(subtype, 0);
    if (!self) {
        return NULL;
    }

    /* tp_alloc is expected to return zeroed memory */
    for (ptr = (int *) &self->dict;
        ptr < (int *) (((char *) self) + sizeof(CurlShareObject));
        ++ptr) {
            assert(*ptr == 0);
    }

    self->lock = share_lock_new();
    if (self->lock == NULL) {
        Py_DECREF(self);
        return NULL;
    }
#if PY_VERSION_HEX < 0x030D0000
    self->api_lock = PyThread_allocate_lock();
    if (self->api_lock == NULL) {
        Py_DECREF(self);
        PyErr_NoMemory();
        return NULL;
    }
#endif

    self->easy_weakrefs = PySet_New(NULL);
    if (self->easy_weakrefs == NULL) {
        Py_DECREF(self);
        return NULL;
    }

    /* Allocate libcurl share handle */
    self->share_handle = curl_share_init();
    if (self->share_handle == NULL) {
        Py_DECREF(self);
        PyErr_SetString(ErrorObject, "initializing curl-share failed");
        return NULL;
    }

    /* Set locking functions and data  */
    res = curl_share_setopt(self->share_handle, CURLSHOPT_LOCKFUNC, lock_cb);
    assert(res == CURLE_OK);
    res = curl_share_setopt(self->share_handle, CURLSHOPT_USERDATA, self);
    assert(res == CURLE_OK);
    res = curl_share_setopt(self->share_handle, CURLSHOPT_UNLOCKFUNC, unlock_cb);
    assert(res == CURLE_OK);

    self->detach_on_close = detach_on_close ? 1 : 0;
    return self;
}


PYCURL_INTERNAL int
do_share_traverse(CurlShareObject *self, visitproc visit, void *arg)
{
    int err;
#undef VISIT
#define VISIT(v)    if ((v) != NULL && ((err = visit(v, arg)) != 0)) return err

    VISIT(self->dict);
    VISIT(self->easy_weakrefs);

    return 0;
#undef VISIT
}

static void
util_share_xdecref(CurlShareObject *self)
{
    Py_CLEAR(self->dict);
#if PY_VERSION_HEX >= 0x030D0000
    PYCURL_SHARE_API_LOCK(self);
    Py_CLEAR(self->easy_weakrefs);
    PYCURL_SHARE_API_UNLOCK(self);
#else
    /*
     * api_lock can be NULL for partially-initialized objects or during
     * early destruction paths; guard against acquiring an uninitialized lock.
     */
    if (self->api_lock) {
        PYCURL_SHARE_API_LOCK(self);
    }
    Py_CLEAR(self->easy_weakrefs);
    if (self->api_lock) {
        PYCURL_SHARE_API_UNLOCK(self);
    }
#endif
}


/* Drop references that may have created reference cycles. */
PYCURL_INTERNAL int
do_share_clear(CurlShareObject *self)
{
    util_share_xdecref(self);
    return 0;
}


static void
util_share_close(CurlShareObject *self){
    if (self->share_handle != NULL) {
        CURLSH *share_handle = self->share_handle;
        self->share_handle = NULL;
        curl_share_cleanup(share_handle);
    }
}


PYCURL_INTERNAL void
do_share_dealloc(CurlShareObject *self)
{
    PyObject_GC_UnTrack(self);
    Py_TRASHCAN_BEGIN(self, do_share_dealloc);

    util_share_xdecref(self);
    util_share_close(self);

    if (self->lock) {
        share_lock_destroy(self->lock);
    }
#if PY_VERSION_HEX < 0x030D0000
    if (self->api_lock) {
        PyThread_free_lock(self->api_lock);
        self->api_lock = NULL;
    }
#endif

    if (self->weakreflist != NULL) {
        PyObject_ClearWeakRefs((PyObject *) self);
    }

    CurlShare_Type.tp_free(self);
    Py_TRASHCAN_END
}

static int
share_cleanup_and_count_live_easies(CurlShareObject *self)
{
    int has_live = 0;

    if (self->easy_weakrefs && PySet_Check(self->easy_weakrefs)) {
        PyObject *it = PyObject_GetIter(self->easy_weakrefs);
        PyObject *to_remove = PyList_New(0);

        if (it && to_remove) {
            PyObject *wr;
            PyObject *obj = NULL;

            while ((wr = PyIter_Next(it))) {
#if PY_VERSION_HEX >= 0x030D0000  /* Python 3.13+ */
                int rc = PyWeakref_GetRef(wr, &obj);
                // return -1 on error, 0 on dead object
                // in either case, mark as removable and
                // move to the next reference
                if (rc < 0)  {
                    Py_DECREF(wr);
                    Py_DECREF(it);
                    Py_DECREF(to_remove);
                    return -1;
                } else if (rc == 0 || obj == NULL) {
                    PyList_Append(to_remove, wr);
                    Py_DECREF(wr);
                    continue;
                }

#else
                // will borrowed reference, None if object dead
                obj = PyWeakref_GetObject(wr);
                if (obj != Py_None) {
                    // If not None, real object, INCREF and carry on
                    Py_INCREF(obj);
                } else {
                    // otherwise mark for removal and move to the next ref
                    PyList_Append(to_remove, wr);
                    Py_DECREF(wr);
                    continue;
                }
#endif
                CurlObject *easy = (CurlObject *)obj;

                if (easy && easy->share == self) {
                    int performing = (easy->state != NULL) ||
                                     (easy->multi_stack != NULL && easy->multi_stack->state != NULL);

                    if (self->detach_on_close && !performing) {
                        curl_easy_setopt(easy->handle, CURLOPT_SHARE, NULL);
                        easy->share = NULL;

                        PyList_Append(to_remove, wr);
                    } else {
                        has_live += 1;
                    }
                } else {
                    PyList_Append(to_remove, wr);
                }

                Py_DECREF(wr);
                Py_DECREF(obj);
            }

            Py_ssize_t i, n = PyList_GET_SIZE(to_remove);
            for (i = 0; i < n; i++) {
                PyObject *wr2 = PyList_GET_ITEM(to_remove, i);
                PySet_Discard(self->easy_weakrefs, wr2);
            }

            Py_DECREF(it);
            Py_DECREF(to_remove);

            if (PyErr_Occurred()) {
                PyErr_Clear();
            }
        } else {
            Py_XDECREF(it);
            Py_XDECREF(to_remove);
            PyErr_Clear();
        }
    }

    return has_live;
}


static PyObject *
do_share_close(CurlShareObject *self, PyObject *Py_UNUSED(ignored))
{
    int nlive;

    assert_share_state(self);

    PYCURL_SHARE_API_LOCK(self);
    nlive = share_cleanup_and_count_live_easies(self);
    if (nlive > 0) {
        PYCURL_SHARE_API_UNLOCK(self);
        PyErr_Format(
            ErrorObject,
            "cannot close CurlShare: still in use by %d active Curl object%s",
            nlive,
            (nlive == 1 ? "" : "s")
        );
        return NULL;
    } else if (nlive < 0) {
        PYCURL_SHARE_API_UNLOCK(self);
        return NULL;
    }

    util_share_close(self);
    PYCURL_SHARE_API_UNLOCK(self);
    Py_RETURN_NONE;
}


static PyObject *do_share_get_closed(CurlShareObject *self, void *Py_UNUSED(closure))
{
    /* api_lock prevents a free-threaded data race with util_share_close. */
    int closed;
    PYCURL_SHARE_API_LOCK(self);
    closed = (self->share_handle == NULL);
    PYCURL_SHARE_API_UNLOCK(self);
    if (closed) {
        Py_RETURN_TRUE;
    } else {
        Py_RETURN_FALSE;
    }
}


/* setopt, unsetopt*/
/* --------------- unsetopt/setopt/getinfo --------------- */

static PyObject *
do_share_setopt(CurlShareObject *self, PyObject *args)
{
    int option;
    PyObject *obj;
    long d;

    if (!PyArg_ParseTuple(args, "iO:setopt", &option, &obj))
        return NULL;

    /* early checks of option value */
    if (option <= 0)
        goto error;
    if (option >= (int)CURLOPTTYPE_OFF_T + OPTIONS_SIZE)
        goto error;
    if (option % 10000 >= OPTIONS_SIZE)
        goto error;

    if (!PyLong_Check(obj)) {
        goto error;
    }

    d = PyLong_AsLong(obj);
    if (d == -1 && PyErr_Occurred()) {
        return NULL;
    }

    if (option != CURLSHOPT_SHARE && option != CURLSHOPT_UNSHARE) {
        PyErr_SetString(PyExc_TypeError, "integers are not supported for this option");
        return NULL;
    }

    PYCURL_SHARE_API_LOCK(self);
    if (check_share_state(self, PYCURL_REQUIRE_HANDLE, "setopt") != 0) {
        PYCURL_SHARE_API_UNLOCK(self);
        return NULL;
    }
    if (share_setopt_one(self, option, d) != 0) {
        PYCURL_SHARE_API_UNLOCK(self);
        return NULL;
    }
    PYCURL_SHARE_API_UNLOCK(self);
    Py_RETURN_NONE;

error:
    PyErr_SetString(PyExc_TypeError, "invalid arguments to setopt");
    return NULL;
}


static PyObject *
share_apply_kinds(CurlShareObject *self, PyObject *args, int option, const char *name)
{
    Py_ssize_t n = PyTuple_GET_SIZE(args);
    if (n == 0) {
        PyErr_SetString(PyExc_TypeError,
            "at least one LOCK_DATA_* argument required");
        return NULL;
    }

    PYCURL_SHARE_API_LOCK(self);
    if (check_share_state(self, PYCURL_REQUIRE_HANDLE, name) != 0) {
        PYCURL_SHARE_API_UNLOCK(self);
        return NULL;
    }

    for (Py_ssize_t i = 0; i < n; i++) {
        PyObject *item = PyTuple_GET_ITEM(args, i);
        if (PyList_Check(item) || PyTuple_Check(item)) {
            PyErr_SetString(PyExc_TypeError,
                "list/tuple arguments are not expanded; "
                "pass each LOCK_DATA_* constant individually");
            PYCURL_SHARE_API_UNLOCK(self);
            return NULL;
        }
        if (!PyLong_Check(item)) {
            PyErr_SetString(PyExc_TypeError,
                "arguments must be LOCK_DATA_* integers");
            PYCURL_SHARE_API_UNLOCK(self);
            return NULL;
        }
        long d = PyLong_AsLong(item);
        if (d == -1 && PyErr_Occurred()) {
            PYCURL_SHARE_API_UNLOCK(self);
            return NULL;
        }
        /* sequential, not transactional: a failure leaves prior items applied */
        if (share_setopt_one(self, option, d) != 0) {
            PYCURL_SHARE_API_UNLOCK(self);
            return NULL;
        }
    }
    PYCURL_SHARE_API_UNLOCK(self);
    Py_RETURN_NONE;
}


static PyObject *
do_share_share(CurlShareObject *self, PyObject *args)
{
    return share_apply_kinds(self, args, CURLSHOPT_SHARE, "share");
}


static PyObject *
do_share_unshare(CurlShareObject *self, PyObject *args)
{
    return share_apply_kinds(self, args, CURLSHOPT_UNSHARE, "unshare");
}


static PyObject *do_share_getstate(CurlShareObject *self, PyObject *Py_UNUSED(ignored))
{
    PyErr_SetString(PyExc_TypeError, "CurlShare objects do not support serialization");
    return NULL;
}


static PyObject *do_share_setstate(CurlShareObject *self, PyObject *args)
{
    PyErr_SetString(PyExc_TypeError, "CurlShare objects do not support deserialization");
    return NULL;
}

static PyObject *do_share_enter(CurlShareObject *self, PyObject *Py_UNUSED(ignored))
{
    /* No api_lock: Py_INCREF is GIL-safe and atomic on free-threaded builds (PEP 703). */
    Py_INCREF(self);
    return (PyObject *)self;
}


/*************************************************************************
// type definitions
**************************************************************************/

/* --------------- methods --------------- */

PYCURL_INTERNAL PyMethodDef curlshareobject_methods[] = {
    {"close", (PyCFunction)do_share_close, METH_NOARGS, share_close_doc},
    {"setopt", (PyCFunction)do_share_setopt, METH_VARARGS, share_setopt_doc},
    {"share", (PyCFunction)do_share_share, METH_VARARGS, share_share_doc},
    {"unshare", (PyCFunction)do_share_unshare, METH_VARARGS, share_unshare_doc},
    {"__getstate__", (PyCFunction)do_share_getstate, METH_NOARGS, NULL},
    {"__setstate__", (PyCFunction)do_share_setstate, METH_VARARGS, NULL},
    {"__enter__", (PyCFunction)do_share_enter, METH_NOARGS, NULL},
    {"__exit__", (PyCFunction)do_share_close, METH_VARARGS, NULL},
    {NULL, NULL, 0, 0}
};


/* --------------- getsets --------------- */

PYCURL_INTERNAL PyGetSetDef curlshareobject_getsets[] = {
    {"closed", (getter)do_share_get_closed, NULL, share_closed_doc, NULL},
    {NULL, NULL, NULL, NULL, NULL}
};


/* --------------- setattr/getattr --------------- */


PYCURL_INTERNAL PyObject *
do_share_getattro(PyObject *o, PyObject *n)
{
    PyObject *v;
    assert_share_state((CurlShareObject *)o);
    v = PyObject_GenericGetAttr(o, n);
    if( !v && PyErr_ExceptionMatches(PyExc_AttributeError) )
    {
        PyErr_Clear();
        v = my_getattro(o, n, ((CurlShareObject *)o)->dict,
                        curlshareobject_constants, curlshareobject_methods);
    }
    return v;
}

PYCURL_INTERNAL int
do_share_setattro(PyObject *o, PyObject *n, PyObject *v)
{
    assert_share_state((CurlShareObject *)o);
    return my_setattro(&((CurlShareObject *)o)->dict, n, v);
}

PYCURL_INTERNAL PyTypeObject CurlShare_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "pycurl.CurlShare",         /* tp_name */
    sizeof(CurlShareObject),    /* tp_basicsize */
    0,                          /* tp_itemsize */
    (destructor)do_share_dealloc, /* tp_dealloc */
    0,                          /* tp_print */
    0,                          /* tp_getattr */
    0,                          /* tp_setattr */
    0,                          /* tp_reserved */
    0,                          /* tp_repr */
    0,                          /* tp_as_number */
    0,                          /* tp_as_sequence */
    0,                          /* tp_as_mapping */
    0,                          /* tp_hash  */
    0,                          /* tp_call */
    0,                          /* tp_str */
    (getattrofunc)do_share_getattro, /* tp_getattro */
    (setattrofunc)do_share_setattro, /* tp_setattro */
    0,                          /* tp_as_buffer */
    PYCURL_TYPE_FLAGS,          /* tp_flags */
    share_doc,                  /* tp_doc */
    (traverseproc)do_share_traverse, /* tp_traverse */
    (inquiry)do_share_clear,    /* tp_clear */
    0,                          /* tp_richcompare */
    offsetof(CurlShareObject, weakreflist), /* tp_weaklistoffset */
    0,                          /* tp_iter */
    0,                          /* tp_iternext */
    curlshareobject_methods,    /* tp_methods */
    0,                          /* tp_members */
    curlshareobject_getsets,    /* tp_getset */
    0,                          /* tp_base */
    0,                          /* tp_dict */
    0,                          /* tp_descr_get */
    0,                          /* tp_descr_set */
    0,                          /* tp_dictoffset */
    0,                          /* tp_init */
    PyType_GenericAlloc,        /* tp_alloc */
    (newfunc)do_share_new,      /* tp_new */
    PyObject_GC_Del,            /* tp_free */
};

/* vi:ts=4:et:nowrap
 */
