#include "pycurl.h"

/*************************************************************************
// static utility functions
**************************************************************************/


/* assert some CurlShareObject invariants */
static void
assert_share_state(const CurlShareObject *self)
{
    assert(self != NULL);
    assert(Py_TYPE(self) == p_CurlShare_Type);
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


/* constructor - this is a module-level function returning a new instance */
PYCURL_INTERNAL CurlShareObject *
do_share_new(PyObject *dummy)
{
    int res;
    CurlShareObject *self;
#ifdef WITH_THREAD
    const curl_lock_function lock_cb = share_lock_callback;
    const curl_unlock_function unlock_cb = share_unlock_callback;
#endif

    UNUSED(dummy);

    /* Allocate python curl-share object */
    self = (CurlShareObject *) PyObject_GC_New(CurlShareObject, p_CurlShare_Type);
    if (self) {
        PyObject_GC_Track(self);
    }
    else {
        return NULL;
    }

    /* Initialize object attributes */
    self->dict = NULL;
#ifdef WITH_THREAD
    self->lock = share_lock_new();
    assert(self->lock != NULL);
#endif

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

    return self;
}


PYCURL_INTERNAL int
do_share_traverse(CurlShareObject *self, visitproc visit, void *arg)
{
    int err;
#undef VISIT
#define VISIT(v)    if ((v) != NULL && ((err = visit(v, arg)) != 0)) return err

    VISIT(self->dict);

    return 0;
#undef VISIT
}


/* Drop references that may have created reference cycles. */
PYCURL_INTERNAL int
do_share_clear(CurlShareObject *self)
{
    Py_CLEAR(self->dict);
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
    Py_TRASHCAN_SAFE_BEGIN(self);

    Py_CLEAR(self->dict);
    util_share_close(self);

#ifdef WITH_THREAD
    share_lock_destroy(self->lock);
#endif

    PyObject_GC_Del(self);
    Py_TRASHCAN_SAFE_END(self)
}


static PyObject *
do_share_close(CurlShareObject *self)
{
    if (check_share_state(self, 2, "close") != 0) {
        return NULL;
    }
    util_share_close(self);
    Py_RETURN_NONE;
}


/* setopt, unsetopt*/
/* --------------- unsetopt/setopt/getinfo --------------- */

static PyObject *
do_curlshare_setopt(CurlShareObject *self, PyObject *args)
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
        if (d != CURL_LOCK_DATA_COOKIE && d != CURL_LOCK_DATA_DNS && d != CURL_LOCK_DATA_SSL_SESSION) {
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


/*************************************************************************
// type definitions
**************************************************************************/

/* --------------- methods --------------- */

static const char cso_close_doc [] =
    "close() -> None.  "
    "Close shared handle.\n";
static const char cso_setopt_doc [] =
    "setopt(option, parameter) -> None.  "
    "Set curl share option.  Raises pycurl.error exception upon failure.\n";

PYCURL_INTERNAL PyMethodDef curlshareobject_methods[] = {
    {"close", (PyCFunction)do_share_close, METH_NOARGS, cso_close_doc},
    {"setopt", (PyCFunction)do_curlshare_setopt, METH_VARARGS, cso_setopt_doc},
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

/* vi:ts=4:et:nowrap
 */
