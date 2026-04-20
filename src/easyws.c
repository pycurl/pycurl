#include "pycurl.h"

#ifdef HAVE_CURL_WEBSOCKETS

#include <errno.h>

/* Build a WsFrame namedtuple snapshot from a libcurl frame struct.
   Returns None if meta is NULL, a new reference to a WsFrame otherwise.
   The libcurl-owned pointer is never stored past this call. */
static PyObject *
build_ws_frame(const struct curl_ws_frame *meta)
{
    if (meta == NULL) {
        Py_RETURN_NONE;
    }
    return PyObject_CallFunction(ws_frame_type, "iiKKK",
        meta->age,
        meta->flags,
        (unsigned long long)meta->offset,
        (unsigned long long)meta->bytesleft,
        (unsigned long long)meta->len);
}

static int
check_ws_curl_state(const CurlObject *self, int allow_write_callback,
                    const char *name)
{
    PyThreadState *callback_state;

    assert_curl_state(self);
    if (self->handle == NULL) {
        PyErr_Format(ErrorObject, "cannot invoke %s() - no curl handle", name);
        return -1;
    }
    callback_state = pycurl_get_thread_state(self);
    if (callback_state != NULL) {
        if (allow_write_callback
            && self->ws_write_cb_running
            && PyThreadState_Get() == callback_state) {
            return 0;
        }
        if (allow_write_callback) {
            PyErr_Format(ErrorObject,
                "cannot invoke %s() - perform() is currently running "
                "outside WRITEFUNCTION callback", name);
        } else {
            PyErr_Format(ErrorObject,
                "cannot invoke %s() - perform() is currently running", name);
        }
        return -1;
    }
    return 0;
}

static int
is_valid_ws_close_code(long code)
{
    switch (code) {
    case 1000:
    case 1001:
    case 1002:
    case 1003:
    case 1007:
    case 1008:
    case 1009:
    case 1010:
    case 1011:
    case 1012:
    case 1013:
    case 1014:
        return 1;
    default:
        return code >= 3000 && code <= 4999;
    }
}

static int
validate_ws_close_reason_utf8(const char *reason_ptr, Py_ssize_t reason_len)
{
    PyObject *decoded;

    if (reason_len == 0) {
        return 0;
    }
    decoded = PyUnicode_DecodeUTF8(reason_ptr, reason_len, "strict");
    if (decoded == NULL) {
        return -1;
    }
    Py_DECREF(decoded);
    return 0;
}

/* --------------- ws_send --------------- */

PYCURL_INTERNAL PyObject *
do_curl_ws_send(CurlObject *self, PyObject *args, PyObject *kwds)
{
    static char *kwlist[] = {"data", "flags", "fragsize", "encoding", NULL};
    PyObject *data_obj = NULL;
    PyObject *flags_obj = Py_None;
    Py_ssize_t fragsize = 0;
    const char *encoding = "utf-8";
    unsigned int flags;
    int flags_explicit;
    int data_is_str;
    PyObject *encoded_bytes = NULL;  /* owned if we UTF-8 encoded */
    Py_buffer sendbuf;
    int have_buffer = 0;
    size_t sent = 0;
    CURLcode res;
    PyObject *result = NULL;
    PyThreadState *saved_state;

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "O|Ons:ws_send", kwlist,
                                     &data_obj, &flags_obj, &fragsize, &encoding)) {
        return NULL;
    }
    if (fragsize < 0) {
        PyErr_SetString(PyExc_ValueError, "negative fragsize in ws_send");
        return NULL;
    }

    flags_explicit = (flags_obj != Py_None);
    if (flags_explicit) {
        long long f = PyLong_AsLongLong(flags_obj);
        if (f == -1 && PyErr_Occurred()) {
            return NULL;
        }
        if (f < 0) {
            PyErr_SetString(PyExc_ValueError, "flags must be non-negative");
            return NULL;
        }
        if ((unsigned long long)f > (unsigned long long)UINT_MAX) {
            PyErr_SetString(PyExc_OverflowError,
                "flags out of range for curl_ws_send");
            return NULL;
        }
        flags = (unsigned int)f;
    } else {
        flags = 0;
    }

    if (flags_explicit
        && (flags & CURLWS_TEXT)
        && (flags & CURLWS_BINARY)) {
        PyErr_SetString(PyExc_ValueError,
            "ws_send: cannot set both WS_TEXT and WS_BINARY");
        return NULL;
    }

    if (flags_explicit) {
        unsigned int control_bits =
            flags & (CURLWS_PING | CURLWS_PONG | CURLWS_CLOSE);
        if (control_bits && (flags & CURLWS_CONT)) {
            PyErr_SetString(PyExc_ValueError,
                "ws_send: control frames cannot be fragmented "
                "(WS_CONT forbidden with WS_PING/WS_PONG/WS_CLOSE)");
            return NULL;
        }
        if (control_bits & (control_bits - 1)) {
            PyErr_SetString(PyExc_ValueError,
                "ws_send: only one of WS_PING / WS_PONG / WS_CLOSE may be set");
            return NULL;
        }
    }

    if (data_obj == Py_None) {
        PyErr_SetString(PyExc_TypeError,
            "ws_send: data must be str or bytes-like, not NoneType "
            "(use b\"\" for an empty payload)");
        return NULL;
    }

    data_is_str = PyUnicode_Check(data_obj);
    if (data_is_str) {
        if (flags_explicit && (flags & CURLWS_BINARY)) {
            PyErr_SetString(PyExc_TypeError,
                "ws_send: str data is incompatible with WS_BINARY; "
                "pass bytes-like data for binary frames");
            return NULL;
        }
        if (flags_explicit && (flags & CURLWS_CLOSE)) {
            PyErr_SetString(PyExc_TypeError,
                "ws_send: str data is incompatible with WS_CLOSE; "
                "use ws_close() or pass a bytes-like payload");
            return NULL;
        }
        if (!flags_explicit) {
            flags = CURLWS_TEXT;
        }
        encoded_bytes = PyUnicode_AsEncodedString(data_obj, encoding, "strict");
        if (encoded_bytes == NULL) {
            return NULL;
        }
        if (PyObject_GetBuffer(encoded_bytes, &sendbuf, PyBUF_SIMPLE) != 0) {
            Py_DECREF(encoded_bytes);
            return NULL;
        }
        have_buffer = 1;
    } else {
        /* bytes-like */
        if (PyObject_GetBuffer(data_obj, &sendbuf, PyBUF_SIMPLE) != 0) {
            return NULL;
        }
        have_buffer = 1;
        if (!flags_explicit) {
            flags = CURLWS_BINARY;
        }
    }

    if (check_ws_curl_state(self, 1, "ws_send") != 0) {
        goto cleanup;
    }

    /* Preserve the thread state across the libcurl call so nested
     * Python callbacks (e.g. if we're already inside WRITEFUNCTION)
     * retain their thread context. Mirrors do_curl_pause. */
    if (self->multi_stack != NULL) {
        saved_state = self->multi_stack->state;
    } else {
        saved_state = self->state;
    }

    PYCURL_BEGIN_ALLOW_THREADS_EASY
    res = curl_ws_send(self->handle, sendbuf.buf, (size_t)sendbuf.len,
                       &sent, (curl_off_t)fragsize, flags);
    PYCURL_END_ALLOW_THREADS_EASY

    if (self->multi_stack != NULL) {
        self->multi_stack->state = saved_state;
    } else {
        self->state = saved_state;
    }

    if (check_pending_python_exception_or_signal() != 0) {
        goto cleanup;
    }
    if (check_easy_recv_send_result(self, res) != 0) {
        goto cleanup;
    }
    result = PyLong_FromSsize_t((Py_ssize_t)sent);

cleanup:
    if (have_buffer) {
        PyBuffer_Release(&sendbuf);
    }
    Py_XDECREF(encoded_bytes);
    return result;
}

/* --------------- ws_recv --------------- */

PYCURL_INTERNAL PyObject *
do_curl_ws_recv(CurlObject *self, PyObject *args)
{
    Py_ssize_t buflen;
    size_t recvd = 0;
    const struct curl_ws_frame *meta = NULL;
    CURLcode res;
    PyObject *data = NULL, *frame = NULL, *tuple = NULL;
#if PY_VERSION_HEX >= 0x030F0000
    PyBytesWriter *writer = NULL;
    void *buf = NULL;
#else
    PyObject *bytes_obj = NULL;
    char *buf = NULL;
#endif

    if (!PyArg_ParseTuple(args, "n:ws_recv", &buflen)) {
        return NULL;
    }
    if (buflen < 0) {
        PyErr_SetString(PyExc_ValueError, "negative buffersize in ws_recv");
        return NULL;
    }
    if (check_curl_state(self, 1 | 2, "ws_recv") != 0) {
        return NULL;
    }
#if PY_VERSION_HEX >= 0x030F0000
    if (buflen > 0) {
        writer = PyBytesWriter_Create(buflen);
        if (writer == NULL) return NULL;
        buf = PyBytesWriter_GetData(writer);
    }
#else
    if (buflen > 0) {
        bytes_obj = PyBytes_FromStringAndSize(NULL, buflen);
        if (bytes_obj == NULL) return NULL;
        buf = PyBytes_AS_STRING(bytes_obj);
    }
#endif

    PYCURL_BEGIN_ALLOW_THREADS
    res = curl_ws_recv(self->handle, buf, (size_t)buflen, &recvd, &meta);
    PYCURL_END_ALLOW_THREADS

    if (check_pending_python_exception_or_signal() != 0) {
#if PY_VERSION_HEX >= 0x030F0000
        if (writer != NULL) {
            PyBytesWriter_Discard(writer);
        }
#else
        Py_XDECREF(bytes_obj);
#endif
        return NULL;
    }
    if (check_easy_recv_send_result(self, res) != 0) {
#if PY_VERSION_HEX >= 0x030F0000
        if (writer != NULL) {
            PyBytesWriter_Discard(writer);
        }
#else
        Py_XDECREF(bytes_obj);
#endif
        return NULL;
    }

#if PY_VERSION_HEX >= 0x030F0000
    if (writer != NULL) {
        data = PyBytesWriter_FinishWithSize(writer, (Py_ssize_t)recvd);
        if (data == NULL) return NULL;
    } else {
        data = PyBytes_FromStringAndSize("", 0);
        if (data == NULL) return NULL;
    }
#else
    if (bytes_obj == NULL) {
        data = PyBytes_FromStringAndSize("", 0);
        if (data == NULL) return NULL;
    } else if ((Py_ssize_t)recvd == buflen) {
        data = bytes_obj;
    } else {
        data = PyBytes_FromStringAndSize(buf, (Py_ssize_t)recvd);
        Py_DECREF(bytes_obj);
        if (data == NULL) return NULL;
    }
#endif

    frame = build_ws_frame(meta);
    if (frame == NULL) { Py_DECREF(data); return NULL; }
    tuple = PyTuple_Pack(2, data, frame);
    Py_DECREF(data); Py_DECREF(frame);
    return tuple;
}

/* --------------- ws_recv_into --------------- */

PYCURL_INTERNAL PyObject *
do_curl_ws_recv_into(CurlObject *self, PyObject *args, PyObject *kwds)
{
    static char *kwlist[] = {"buffer", "nbytes", NULL};
    Py_buffer recvbuf;
    Py_ssize_t buflen;
    Py_ssize_t recvlen = 0;
    size_t recvd = 0;
    const struct curl_ws_frame *meta = NULL;
    CURLcode res;
    PyObject *frame, *tuple;

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "w*|n:ws_recv_into", kwlist,
                                     &recvbuf, &recvlen)) {
        return NULL;
    }
    buflen = recvbuf.len;
    if (recvlen < 0) {
        PyBuffer_Release(&recvbuf);
        PyErr_SetString(PyExc_ValueError, "negative buffersize in ws_recv_into");
        return NULL;
    }
    /* nbytes=0 (the default) means "use the full buffer". Either way,
     * recvlen must not exceed the buffer itself. */
    if (recvlen == 0) {
        recvlen = buflen;
    }
    if (recvlen > buflen) {
        PyBuffer_Release(&recvbuf);
        PyErr_SetString(PyExc_ValueError, "buffer too small for requested bytes");
        return NULL;
    }
    if (check_curl_state(self, 1 | 2, "ws_recv_into") != 0) {
        PyBuffer_Release(&recvbuf);
        return NULL;
    }
    PYCURL_BEGIN_ALLOW_THREADS
    res = curl_ws_recv(self->handle,
                       recvlen > 0 ? recvbuf.buf : NULL,
                       (size_t)recvlen, &recvd, &meta);
    PYCURL_END_ALLOW_THREADS

    PyBuffer_Release(&recvbuf);

    if (check_pending_python_exception_or_signal() != 0) {
        return NULL;
    }
    if (check_easy_recv_send_result(self, res) != 0) {
        return NULL;
    }

    frame = build_ws_frame(meta);
    if (frame == NULL) return NULL;
    tuple = Py_BuildValue("(nN)", (Py_ssize_t)recvd, frame);
    return tuple;
}

/* --------------- ws_meta --------------- */

PYCURL_INTERNAL PyObject *
do_curl_ws_meta(CurlObject *self, PyObject *Py_UNUSED(ignored))
{
    const struct curl_ws_frame *meta;

    if (check_curl_state(self, 1, "ws_meta") != 0) {
        return NULL;
    }
    meta = curl_ws_meta(self->handle);
    return build_ws_frame(meta);
}

/* --------------- ws_close --------------- */

PYCURL_INTERNAL PyObject *
do_curl_ws_close(CurlObject *self, PyObject *args, PyObject *kwds)
{
    static char *kwlist[] = {"code", "reason", "encoding", NULL};
    PyObject *code_obj = Py_None;
    PyObject *reason_obj = Py_None;
    const char *encoding = "utf-8";
    int code = 0;
    int have_code = 0;
    PyObject *encoded_reason = NULL;  /* owned if we UTF-8 encoded */
    Py_buffer reason_buf;
    int have_reason_buf = 0;
    const char *reason_ptr = NULL;
    Py_ssize_t reason_len = 0;
    unsigned char payload[125];
    Py_ssize_t payload_len = 0;
    size_t sent = 0;
    CURLcode res;
    PyObject *result = NULL;
    PyThreadState *saved_state;

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "|OOs:ws_close", kwlist,
                                     &code_obj, &reason_obj, &encoding)) {
        return NULL;
    }

    if (code_obj != Py_None) {
        long c = PyLong_AsLong(code_obj);
        if (c == -1 && PyErr_Occurred()) {
            return NULL;
        }
        if (!is_valid_ws_close_code(c)) {
            PyErr_SetString(PyExc_ValueError,
                "ws_close: code must be a valid wire close status code");
            return NULL;
        }
        code = (int)c;
        have_code = 1;
    }

    if (reason_obj != Py_None) {
        if (!have_code) {
            PyErr_SetString(PyExc_ValueError,
                "ws_close: reason requires code (RFC 6455 §5.5.1)");
            return NULL;
        }
        if (PyUnicode_Check(reason_obj)) {
            encoded_reason = PyUnicode_AsEncodedString(
                reason_obj, encoding, "strict");
            if (encoded_reason == NULL) {
                return NULL;
            }
            if (PyObject_GetBuffer(encoded_reason, &reason_buf,
                                   PyBUF_SIMPLE) != 0) {
                Py_DECREF(encoded_reason);
                return NULL;
            }
        } else {
            if (PyObject_GetBuffer(reason_obj, &reason_buf,
                                   PyBUF_SIMPLE) != 0) {
                return NULL;
            }
        }
        have_reason_buf = 1;
        reason_ptr = (const char *)reason_buf.buf;
        reason_len = reason_buf.len;
    }

    if (validate_ws_close_reason_utf8(reason_ptr, reason_len) != 0) {
        goto cleanup;
    }

    /* Total payload: 2 bytes for code (if any) + reason bytes.
     * RFC 6455 §5.5 caps control-frame payloads at 125 bytes. */
    if (have_code) {
        payload_len = 2 + reason_len;
    } else {
        payload_len = 0;  /* empty close */
    }
    if (payload_len > (Py_ssize_t)sizeof(payload)) {
        PyErr_Format(PyExc_ValueError,
            "ws_close: payload too large (%zd bytes, max 125 including "
            "2-byte status code)", payload_len);
        goto cleanup;
    }

    if (have_code) {
        payload[0] = (unsigned char)((code >> 8) & 0xff);
        payload[1] = (unsigned char)(code & 0xff);
        if (reason_len > 0) {
            memcpy(payload + 2, reason_ptr, (size_t)reason_len);
        }
    }

    if (check_ws_curl_state(self, 1, "ws_close") != 0) {
        goto cleanup;
    }

    if (self->multi_stack != NULL) {
        saved_state = self->multi_stack->state;
    } else {
        saved_state = self->state;
    }

    PYCURL_BEGIN_ALLOW_THREADS_EASY
    res = curl_ws_send(self->handle, payload, (size_t)payload_len,
                       &sent, (curl_off_t)0, CURLWS_CLOSE);
    PYCURL_END_ALLOW_THREADS_EASY

    if (self->multi_stack != NULL) {
        self->multi_stack->state = saved_state;
    } else {
        self->state = saved_state;
    }

    if (check_pending_python_exception_or_signal() != 0) {
        goto cleanup;
    }
    if (check_easy_recv_send_result(self, res) != 0) {
        goto cleanup;
    }
    result = PyLong_FromSsize_t((Py_ssize_t)sent);

cleanup:
    if (have_reason_buf) {
        PyBuffer_Release(&reason_buf);
    }
    Py_XDECREF(encoded_reason);
    return result;
}

#endif /* HAVE_CURL_WEBSOCKETS */
