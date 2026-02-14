#include "pycurl.h"
#include <errno.h>


/* --------------- perform --------------- */

PYCURL_INTERNAL PyObject *
do_curl_perform(CurlObject *self, PyObject *Py_UNUSED(ignored))
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


PYCURL_INTERNAL PyObject *
do_curl_perform_rb(CurlObject *self, PyObject *Py_UNUSED(ignored))
{
    PyObject *v, *io;
    
    /* NOTE: this tuple is never freed. */
    static PyObject *empty_tuple = NULL;
    
    if (empty_tuple == NULL) {
        empty_tuple = PyTuple_New(0);
        if (empty_tuple == NULL) {
            return NULL;
        }
    }
    
    io = PyObject_Call(bytesio, empty_tuple, NULL);
    if (io == NULL) {
        return NULL;
    }
    
    v = do_curl_setopt_filelike(self, CURLOPT_WRITEDATA, io);
    if (v == NULL) {
        Py_DECREF(io);
        return NULL;
    }
    
    v = do_curl_perform(self, NULL);
    if (v == NULL) {
        return NULL;
    }
    
    v = PyObject_CallMethod(io, "getvalue", NULL);
    Py_DECREF(io);
    return v;
}

#if PY_MAJOR_VERSION >= 3
PYCURL_INTERNAL PyObject *
do_curl_perform_rs(CurlObject *self, PyObject *Py_UNUSED(ignored))
{
    PyObject *v, *decoded;
    
    v = do_curl_perform_rb(self, NULL);
    if (v == NULL) {
        return NULL;
    }
    
    decoded = PyUnicode_FromEncodedObject(v, NULL, NULL);
    Py_DECREF(v);
    return decoded;
}
#endif


/* --------------- send/recv --------------- */

static PyObject *
set_would_block_error(void)
{
    errno = EAGAIN;
    PyErr_SetFromErrno(PyExc_BlockingIOError);
    return NULL;
}

static int
check_easy_recv_send_result(CurlObject *self, CURLcode res)
{
    if (res == CURLE_OK) {
        return 0;
    }
    if (res == CURLE_AGAIN) {
        set_would_block_error();
        return -1;
    }
    create_and_set_error_object(self, (int)res);
    return -1;
}

static int
perform_easy_send(CurlObject *self, const void *buf, size_t len, size_t *sent)
{
    CURLcode res;

    PYCURL_BEGIN_ALLOW_THREADS
    res = curl_easy_send(self->handle, buf, len, sent);
    PYCURL_END_ALLOW_THREADS

    return check_easy_recv_send_result(self, res);
}

static int
perform_easy_recv(CurlObject *self, void *buf, size_t len, size_t *recvd)
{
    CURLcode res;

    PYCURL_BEGIN_ALLOW_THREADS
    res = curl_easy_recv(self->handle, buf, len, recvd);
    PYCURL_END_ALLOW_THREADS

    return check_easy_recv_send_result(self, res);
}

PYCURL_INTERNAL PyObject *
do_curl_send(CurlObject *self, PyObject *args)
{
    Py_buffer sendbuf;
    size_t sent = 0;

    if (!PyArg_ParseTuple(args, "y*:send", &sendbuf)) {
        return NULL;
    }
    if (check_curl_state(self, 1 | 2, "send") != 0) {
        PyBuffer_Release(&sendbuf);
        return NULL;
    }

    if (perform_easy_send(self, sendbuf.buf, (size_t)sendbuf.len, &sent) != 0) {
        PyBuffer_Release(&sendbuf);
        return NULL;
    }
    PyBuffer_Release(&sendbuf);

    return PyLong_FromSsize_t((Py_ssize_t)sent);
}

PYCURL_INTERNAL PyObject *
do_curl_recv(CurlObject *self, PyObject *args)
{
    Py_ssize_t buflen;
    size_t recvd = 0;
#if PY_VERSION_HEX >= 0x030F0000
    /* PyBytesWriter is part of the public C API starting with Python 3.15. */
    PyBytesWriter *writer;
#else
    PyObject *bytes_obj;
    char *buf = NULL;
    PyObject *result = NULL;
#endif

    if (!PyArg_ParseTuple(args, "n:recv", &buflen)) {
        return NULL;
    }
    if (buflen < 0) {
        PyErr_SetString(PyExc_ValueError, "negative buffersize in recv");
        return NULL;
    }
    if (check_curl_state(self, 1 | 2, "recv") != 0) {
        return NULL;
    }
    if (buflen == 0) {
        return PyBytes_FromStringAndSize("", 0);
    }

#if PY_VERSION_HEX >= 0x030F0000
    writer = PyBytesWriter_Create(buflen);
    if (writer == NULL) {
        return NULL;
    }

    if (perform_easy_recv(self, PyBytesWriter_GetData(writer), (size_t)buflen, &recvd) != 0) {
        PyBytesWriter_Discard(writer);
        return NULL;
    }

    return PyBytesWriter_FinishWithSize(writer, (Py_ssize_t)recvd);
#else
    bytes_obj = PyBytes_FromStringAndSize(NULL, buflen);
    if (bytes_obj == NULL) {
        return NULL;
    }
    buf = PyBytes_AS_STRING(bytes_obj);

    if (perform_easy_recv(self, buf, (size_t)buflen, &recvd) != 0) {
        Py_DECREF(bytes_obj);
        return NULL;
    }

    if ((Py_ssize_t)recvd == buflen) {
        return bytes_obj;
    }

    result = PyBytes_FromStringAndSize(buf, (Py_ssize_t)recvd);
    Py_DECREF(bytes_obj);
    return result;
#endif
}

PYCURL_INTERNAL PyObject *
do_curl_recv_into(CurlObject *self, PyObject *args, PyObject *kwds)
{
    static char *kwlist[] = {"buffer", "nbytes", NULL};
    Py_buffer recvbuf;
    Py_ssize_t buflen;
    Py_ssize_t recvlen = 0;
    size_t recvd = 0;

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "w*|n:recv_into", kwlist,
                                     &recvbuf, &recvlen)) {
        return NULL;
    }
    buflen = recvbuf.len;
    if (recvlen < 0) {
        PyBuffer_Release(&recvbuf);
        PyErr_SetString(PyExc_ValueError, "negative buffersize in recv_into");
        return NULL;
    }
    if (recvlen == 0) {
        recvlen = buflen;
    }
    if (recvlen > buflen) {
        PyBuffer_Release(&recvbuf);
        PyErr_SetString(PyExc_ValueError, "buffer too small for requested bytes");
        return NULL;
    }
    if (check_curl_state(self, 1 | 2, "recv_into") != 0) {
        PyBuffer_Release(&recvbuf);
        return NULL;
    }
    if (recvlen == 0) {
        PyBuffer_Release(&recvbuf);
        return PyLong_FromLong(0);
    }

    if (perform_easy_recv(self, recvbuf.buf, (size_t)recvlen, &recvd) != 0) {
        PyBuffer_Release(&recvbuf);
        return NULL;
    }
    PyBuffer_Release(&recvbuf);

    return PyLong_FromSize_t(recvd);
}


/* --------------- pause --------------- */


/* curl_easy_pause() can be called from inside a callback or outside */
PYCURL_INTERNAL PyObject *
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
    if (self->multi_stack != NULL) {
        saved_state = self->multi_stack->state;
    } else {
        saved_state = self->state;
    }
    
    /* We must allow threads here because unpausing a handle can cause
       some of its callbacks to be invoked immediately, from inside
       curl_easy_pause() */
#endif
    
    PYCURL_BEGIN_ALLOW_THREADS_EASY
    res = curl_easy_pause(self->handle, bitmask);
    PYCURL_END_ALLOW_THREADS_EASY

#ifdef WITH_THREAD
    /* Restore the thread-state to whatever it was on entry */
    if (self->multi_stack != NULL) {
        self->multi_stack->state = saved_state;
    } else {
        self->state = saved_state;
    }
#endif

    if (res != CURLE_OK) {
        CURLERROR_MSG("pause/unpause failed");
    } else {
        Py_RETURN_NONE;
    }
}
