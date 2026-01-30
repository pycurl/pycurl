#include "pycurl.h"
#include "docstrings.h"

#ifdef WITH_THREAD
#  define EASY_WEAKREFS_LOCK(share)   PyThread_acquire_lock((share)->easy_weakrefs_lock, 1)
#  define EASY_WEAKREFS_UNLOCK(share) PyThread_release_lock((share)->easy_weakrefs_lock)
#else
#  define EASY_WEAKREFS_LOCK(share)   ((void)0)
#  define EASY_WEAKREFS_UNLOCK(share) ((void)0)
#endif

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

    EASY_WEAKREFS_LOCK(share);

    if (share->share_handle == NULL || share->easy_weakrefs == NULL) {
        PyErr_SetString(PyExc_RuntimeError, "CurlShare is closed");
        goto error;
    }

    if (PySet_Add(share->easy_weakrefs, wr) < 0) {
        goto error;
    }

    EASY_WEAKREFS_UNLOCK(share);
    Py_DECREF(wr);
    return 0;

error:
    EASY_WEAKREFS_UNLOCK(share);
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

    EASY_WEAKREFS_LOCK(share);

    if (share->easy_weakrefs == NULL) {
        EASY_WEAKREFS_UNLOCK(share);
        Py_DECREF(wr);
        return;
    }

    if (PySet_Discard(share->easy_weakrefs, wr) < 0) {
        PyErr_Clear();
    }

    EASY_WEAKREFS_UNLOCK(share);
    Py_DECREF(wr);
}


/* assert some CurlShareObject invariants */
static void
assert_share_state(const CurlShareObject *self)
{
    assert(self != NULL);
    assert(PyObject_IsInstance((PyObject *) self, (PyObject *) p_CurlShare_Type) == 1);
#ifdef WITH_THREAD
    assert(self->lock != NULL);
#endif
}


static int
check_share_state(const CurlShareObject *self, int flags, const char *name)
{
    assert_share_state(self);
    return 0;
}


/* constructor */
PYCURL_INTERNAL CurlShareObject *
do_share_new(PyTypeObject *subtype, PyObject *args, PyObject *kwds)
{
    int res;
    CurlShareObject *self;
#ifdef WITH_THREAD
    const curl_lock_function lock_cb = share_lock_callback;
    const curl_unlock_function unlock_cb = share_unlock_callback;
#endif
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

#ifdef WITH_THREAD
    self->lock = share_lock_new();
    assert(self->lock != NULL);
    self->easy_weakrefs_lock = PyThread_allocate_lock();
    if (self->easy_weakrefs_lock == NULL) {
        Py_DECREF(self);
        PyErr_NoMemory();
        return NULL;
    }
#endif

    self->easy_weakrefs = PySet_New(NULL);
    if (self->easy_weakrefs == NULL) {
        Py_DECREF(self);
#ifdef WITH_THREAD
        PyThread_free_lock(self->easy_weakrefs_lock);
        self->easy_weakrefs_lock = NULL;
#endif
        return NULL;
    }

    /* Allocate libcurl share handle */
    self->share_handle = curl_share_init();
    if (self->share_handle == NULL) {
        Py_DECREF(self);
        PyErr_SetString(ErrorObject, "initializing curl-share failed");
        return NULL;
    }

#ifdef WITH_THREAD
    /* Set locking functions and data  */
    res = curl_share_setopt(self->share_handle, CURLSHOPT_LOCKFUNC, lock_cb);
    assert(res == CURLE_OK);
    res = curl_share_setopt(self->share_handle, CURLSHOPT_USERDATA, self);
    assert(res == CURLE_OK);
    res = curl_share_setopt(self->share_handle, CURLSHOPT_UNLOCKFUNC, unlock_cb);
    assert(res == CURLE_OK);
#endif

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
    /*
     * The lock can be NULL for partially-initialized objects or during
     * early destruction paths; guard against acquiring an uninitialized lock.
     */
#ifdef WITH_THREAD
    if (self->easy_weakrefs_lock) EASY_WEAKREFS_LOCK(self);
#endif
    Py_CLEAR(self->easy_weakrefs);
#ifdef WITH_THREAD
    if (self->easy_weakrefs_lock) EASY_WEAKREFS_UNLOCK(self);
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
    CPy_TRASHCAN_BEGIN(self, do_share_dealloc);

    util_share_xdecref(self);
    util_share_close(self);

#ifdef WITH_THREAD
    share_lock_destroy(self->lock);
    if (self->easy_weakrefs_lock) {
        PyThread_free_lock(self->easy_weakrefs_lock);
        self->easy_weakrefs_lock = NULL;
    }
#endif

    if (self->weakreflist != NULL) {
        PyObject_ClearWeakRefs((PyObject *) self);
    }

    CurlShare_Type.tp_free(self);
    CPy_TRASHCAN_END(self);
}

static int
share_cleanup_and_count_live_easies(CurlShareObject *self)
{
    int has_live = 0;

    EASY_WEAKREFS_LOCK(self);

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
                if (rc < 1 || obj == NULL)  {
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
                    if (self->detach_on_close) {
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

    EASY_WEAKREFS_UNLOCK(self);
    return has_live;
}


static PyObject *
do_share_close(CurlShareObject *self, PyObject *Py_UNUSED(ignored))
{
    int nlive;

    if (check_share_state(self, 2, "close") != 0) {
        return NULL;
    }

    nlive = share_cleanup_and_count_live_easies(self);
    if (nlive > 0) {
        PyErr_Format(
            ErrorObject,
            "cannot close CurlShare: still in use by %d active Curl object%s",
            nlive,
            (nlive == 1 ? "" : "s")
        );
        return NULL;
    }

    util_share_close(self);
    Py_RETURN_NONE;
}


static PyObject *do_share_closed(CurlShareObject *self, PyObject *Py_UNUSED(ignored))
{
    if (self->share_handle == NULL) {
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

    if (!PyArg_ParseTuple(args, "iO:setopt", &option, &obj))
        return NULL;
    if (check_share_state(self, 1 | 2, "sharesetopt") != 0)
        return NULL;

    /* early checks of option value */
    if (option <= 0)
        goto error;
    if (option >= (int)CURLOPTTYPE_OFF_T + OPTIONS_SIZE)
        goto error;
    if (option % 10000 >= OPTIONS_SIZE)
        goto error;

#if 0 /* XXX - should we ??? */
    /* Handle the case of None */
    if (obj == Py_None) {
        return util_curl_unsetopt(self, option);
    }
#endif

    /* Handle the case of integer arguments */
    if (PyInt_Check(obj)) {
        long d = PyInt_AsLong(obj);
        switch(d) {
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
            goto error;
        }
        switch(option) {
        case CURLSHOPT_SHARE:
        case CURLSHOPT_UNSHARE:
            curl_share_setopt(self->share_handle, option, d);
            break;
        default:
            PyErr_SetString(PyExc_TypeError, "integers are not supported for this option");
            return NULL;
        }
        Py_RETURN_NONE;
    }
    /* Failed to match any of the function signatures -- return error */
error:
    PyErr_SetString(PyExc_TypeError, "invalid arguments to setopt");
    return NULL;
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
    Py_INCREF(self);
    return (PyObject *)self;
}


/*************************************************************************
// type definitions
**************************************************************************/

/* --------------- methods --------------- */

PYCURL_INTERNAL PyMethodDef curlshareobject_methods[] = {
    {"close", (PyCFunction)do_share_close, METH_NOARGS, share_close_doc},
    {"closed", (PyCFunction)do_share_closed, METH_NOARGS, share_closed_doc},
    {"setopt", (PyCFunction)do_share_setopt, METH_VARARGS, share_setopt_doc},
    {"__getstate__", (PyCFunction)do_share_getstate, METH_NOARGS, NULL},
    {"__setstate__", (PyCFunction)do_share_setstate, METH_VARARGS, NULL},
    {"__enter__", (PyCFunction)do_share_enter, METH_NOARGS, NULL},
    {"__exit__", (PyCFunction)do_share_close, METH_VARARGS, NULL},
    {NULL, NULL, 0, 0}
};


/* --------------- setattr/getattr --------------- */


#if PY_MAJOR_VERSION >= 3

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

#else /* PY_MAJOR_VERSION >= 3 */

PYCURL_INTERNAL PyObject *
do_share_getattr(CurlShareObject *cso, char *name)
{
    assert_share_state(cso);
    return my_getattr((PyObject *)cso, name, cso->dict,
                      curlshareobject_constants, curlshareobject_methods);
}

PYCURL_INTERNAL int
do_share_setattr(CurlShareObject *so, char *name, PyObject *v)
{
    assert_share_state(so);
    return my_setattr(&so->dict, name, v);
}

#endif /* PY_MAJOR_VERSION >= 3 */

PYCURL_INTERNAL PyTypeObject CurlShare_Type = {
#if PY_MAJOR_VERSION >= 3
    PyVarObject_HEAD_INIT(NULL, 0)
#else
    PyObject_HEAD_INIT(NULL)
    0,                          /* ob_size */
#endif
    "pycurl.CurlShare",         /* tp_name */
    sizeof(CurlShareObject),    /* tp_basicsize */
    0,                          /* tp_itemsize */
    (destructor)do_share_dealloc, /* tp_dealloc */
    0,                          /* tp_print */
#if PY_MAJOR_VERSION >= 3
    0,                          /* tp_getattr */
    0,                          /* tp_setattr */
#else
    (getattrfunc)do_share_getattr,  /* tp_getattr */
    (setattrfunc)do_share_setattr,  /* tp_setattr */
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
    (getattrofunc)do_share_getattro, /* tp_getattro */
    (setattrofunc)do_share_setattro, /* tp_setattro */
#else
    0,                          /* tp_getattro */
    0,                          /* tp_setattro */
#endif
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
    0,                          /* tp_getset */
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
