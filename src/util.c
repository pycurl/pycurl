#include "pycurl.h"

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
    if (v == NULL) {
        Py_DECREF(s);
        return NULL;
    }
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
