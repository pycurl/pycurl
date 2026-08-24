#include "pycurl.h"

PYCURL_INTERNAL int
check_pending_python_signal(void)
{
    if (PyErr_CheckSignals() != 0) {
        return -1;
    }
    return 0;
}

PYCURL_INTERNAL int
check_pending_python_exception_or_signal(void)
{
    if (PyErr_Occurred()) {
        return -1;
    }
    return check_pending_python_signal();
}

PYCURL_INTERNAL void
warn_failed_to_acquire_thread(const char *warning_message)
{
    PyGILState_STATE tmp_warn_state = PyGILState_Ensure();
    PyErr_WarnEx(PyExc_RuntimeWarning, warning_message, 1);
    PyGILState_Release(tmp_warn_state);
}

PYCURL_INTERNAL void
print_callback_error_if_regular_exception(void)
{
    if (PyErr_ExceptionMatches(PyExc_Exception)) {
        PyErr_Print();
    }
}

/* Stash the pending exception on the *storage list; also print it when
   print_traceback is set. A BaseException is left set to keep propagating. */
static void
capture_callback_exception(PyObject **storage, int print_traceback)
{
    PyObject *type = NULL, *value = NULL, *tb = NULL, *list;

    if (!PyErr_Occurred() || !PyErr_ExceptionMatches(PyExc_Exception)) {
        return;
    }
    PyErr_Fetch(&type, &value, &tb);
    PyErr_NormalizeException(&type, &value, &tb);
    if (value == NULL) {
        Py_XDECREF(type);
        Py_XDECREF(tb);
        return;
    }
    if (tb != NULL) {
        PyException_SetTraceback(value, tb);
    }

    list = *storage;
    if (list == NULL) {
        list = PyList_New(0);
        if (list != NULL) {
            *storage = list;
        }
    }
    if (list != NULL) {
        (void) PyList_Append(list, value);
    }

    if (print_traceback) {
        PyErr_Restore(type, value, tb);
        PyErr_Print();
    } else {
        Py_DECREF(value);
        Py_XDECREF(type);
        Py_XDECREF(tb);
    }
}

PYCURL_INTERNAL void
pycurl_capture_callback_exception(PyObject **storage)
{
    capture_callback_exception(storage, 1);
}

PYCURL_INTERNAL void
pycurl_stash_callback_exception(PyObject **storage)
{
    capture_callback_exception(storage, 0);
}

PYCURL_INTERNAL void
pycurl_attach_callback_cause(PyObject **storage)
{
    PyObject *list = *storage;
    PyObject *cause = NULL;
    PyObject *type = NULL, *value = NULL, *tb = NULL;
    Py_ssize_t n;

    *storage = NULL;
    if (list == NULL) {
        return;
    }
    n = PyList_GET_SIZE(list);
    if (n == 0) {
        Py_DECREF(list);
        return;
    }
    /* No pending error: the libcurl call succeeded despite the callback
       raising (e.g. DEBUGFUNCTION). Drop the captures. */
    if (!PyErr_Occurred()) {
        Py_DECREF(list);
        return;
    }

    PyErr_Fetch(&type, &value, &tb);
    PyErr_NormalizeException(&type, &value, &tb);
    if (value == NULL) {
        PyErr_Restore(type, value, tb);
        Py_DECREF(list);
        return;
    }

#if PY_VERSION_HEX >= 0x030B0000
    /* Several captures wrap in an ExceptionGroup (all leaves are Exception). */
    if (n > 1) {
        cause = PyObject_CallFunction(PyExc_BaseExceptionGroup, "sO",
                                      "PycURL callback exceptions", list);
    } else
#endif
    {
        cause = Py_NewRef(PyList_GET_ITEM(list, 0));
    }
    Py_DECREF(list);
    if (cause == NULL) {
        PyErr_Clear();
        PyErr_Restore(type, value, tb);
        return;
    }

    PyException_SetCause(value, cause); /* steals cause */
    PyErr_Restore(type, value, tb);     /* steals type/value/tb */
}

PYCURL_INTERNAL void
pycurl_easy_clear_callback_state(CurlObject *self)
{
    Py_CLEAR(self->callback_exception);
}

PYCURL_INTERNAL void
pycurl_easy_attach_callback_cause(CurlObject *self)
{
    pycurl_attach_callback_cause(&self->callback_exception);
}

PYCURL_INTERNAL PyObject *
PyLong_FromCurlSocket(curl_socket_t sockfd)
{
#if defined(WIN32)
    if (sockfd == CURL_SOCKET_BAD) {
        return PyLong_FromLong(-1);
    }
    return PyLong_FromUnsignedLongLong((unsigned long long) sockfd);
#else
    return PyLong_FromLongLong((long long) sockfd);
#endif
}

PYCURL_INTERNAL int
PyLong_AsCurlSocket(PyObject *obj, curl_socket_t *sockfd)
{
#if defined(WIN32)
    const unsigned long long max_socket =
        (unsigned long long) ((curl_socket_t) ~(curl_socket_t) 0);
    long long ll;
    unsigned long long ull;
#else
    long long ll;
#endif

    assert(sockfd != NULL);

#if defined(WIN32)
    ll = PyLong_AsLongLong(obj);
    if (!PyErr_Occurred()) {
        if (ll == -1) {
            *sockfd = CURL_SOCKET_BAD;
            return 0;
        }
        if (ll < 0) {
            PyErr_SetString(PyExc_OverflowError,
                "socket value must be -1 or non-negative");
            return -1;
        }
        if ((unsigned long long) ll > max_socket) {
            PyErr_SetString(PyExc_OverflowError, "socket value is out of range");
            return -1;
        }
        *sockfd = (curl_socket_t) ll;
        return 0;
    }

    if (!PyErr_ExceptionMatches(PyExc_OverflowError)) {
        return -1;
    }
    PyErr_Clear();

    ull = PyLong_AsUnsignedLongLong(obj);
    if (PyErr_Occurred()) {
        return -1;
    }
    if (ull > max_socket) {
        PyErr_SetString(PyExc_OverflowError, "socket value is out of range");
        return -1;
    }
    *sockfd = (curl_socket_t) ull;
    return 0;
#else
    ll = PyLong_AsLongLong(obj);
    if (PyErr_Occurred()) {
        return -1;
    }
    if (ll < (long long) CURL_SOCKET_BAD || ll > INT_MAX) {
        PyErr_SetString(PyExc_OverflowError, "socket value is out of range");
        return -1;
    }
    *sockfd = (curl_socket_t) ll;
    return 0;
#endif
}

/* Returns -1 with the OverflowError PyLong_AsInt raises, so that callers see the
   same contract before and after it became available in 3.13. */
PYCURL_INTERNAL int
pycurl_long_as_int(PyObject *obj, int *ret_out)
{
#if PY_VERSION_HEX >= 0x030D0000
    int value = PyLong_AsInt(obj);

    if (value == -1 && PyErr_Occurred()) {
        return -1;
    }
#else
    int overflow;
    long value = PyLong_AsLongAndOverflow(obj, &overflow);

    if (value == -1 && PyErr_Occurred()) {
        return -1;
    }
    if (overflow || value > INT_MAX || value < INT_MIN) {
        PyErr_SetString(PyExc_OverflowError,
                        "Python int too large to convert to C int");
        return -1;
    }
#endif
    *ret_out = (int) value;
    return 0;
}

static PyObject *
create_error_object(CurlObject *self, int code)
{
    PyObject *s, *v;

    if (strlen(self->error)) {
        s = PyText_FromString_Ignore(self->error);
        if (s == NULL) {
            return NULL;
        }
    } else {
        s = PyText_FromString_Ignore(curl_easy_strerror(code));
        if (s == NULL) {
            return NULL;
        }
    }
    v = Py_BuildValue("(iO)", code, s);
    Py_DECREF(s);
    return v;
}

PYCURL_INTERNAL void
create_and_set_error_object(CurlObject *self, int code)
{
    PyObject *e;
    
    self->error[sizeof(self->error) - 1] = 0;
    e = create_error_object(self, code);
    if (e != NULL) {
        PyErr_SetObject(ErrorObject, e);
        Py_DECREF(e);
    }
}
