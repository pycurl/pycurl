#include "pycurl.h"

/*************************************************************************
// python utility functions
**************************************************************************/

PYCURL_INTERNAL int
PyText_AsStringAndSize(PyObject *obj, char **buffer, Py_ssize_t *length, PyObject **encoded_obj)
{
    if (PyBytes_Check(obj)) {
        *encoded_obj = NULL;
        return PyBytes_AsStringAndSize(obj, buffer, length);
    } else {
        int rv;
        *encoded_obj = PyUnicode_AsEncodedString(obj, "ascii", "strict");
        if (*encoded_obj == NULL) {
            if (PyErr_ExceptionMatches(PyExc_TypeError)) {
                PyErr_Clear();
                PyErr_Format(PyExc_TypeError,
                    "expected bytes or an ASCII string, got %.200s",
                    Py_TYPE(obj)->tp_name);
            }
            return -1;
        }
        rv = PyBytes_AsStringAndSize(*encoded_obj, buffer, length);
        if (rv != 0) {
            /* If we free the object, pointer must be reset to NULL */
            Py_CLEAR(*encoded_obj);
        }
        return rv;
    }
}


/* Like PyBytes_AsString(), but set an exception if the string contains
 * embedded NULs.
 */

PYCURL_INTERNAL char *
PyText_AsString_NoNUL(PyObject *obj, PyObject **encoded_obj)
{
    char *s = NULL;
    Py_ssize_t r;
    r = PyText_AsStringAndSize(obj, &s, NULL, encoded_obj);
    if (r != 0)
        return NULL;    /* exception already set */
    assert(s != NULL);
    return s;
}


/* Returns true if the object is of a type that can be given to
 * curl_easy_setopt and such - either a byte string or a Unicode string
 * with ASCII code points only.
 */
PYCURL_INTERNAL int
PyText_Check(PyObject *o)
{
    return PyUnicode_Check(o) || PyBytes_Check(o);
}

/* Accepts text or any buffer object. On success the caller must release
   *view when *view_active is set, and decref *encoded_obj. */
PYCURL_INTERNAL int
PyText_OrBuffer_AsStringAndSize(PyObject *obj, char **buffer, Py_ssize_t *length,
    PyObject **encoded_obj, Py_buffer *view, int *view_active, const char *what)
{
    if (PyObject_CheckBuffer(obj)) {
        if (PyObject_GetBuffer(obj, view, PyBUF_SIMPLE) != 0) {
            return -1;
        }

        *view_active = 1;
        *buffer = (char *)view->buf;
        *length = view->len;
        return 0;
    }

    if (PyText_Check(obj)) {
        return PyText_AsStringAndSize(obj, buffer, length, encoded_obj);
    }

    PyErr_Format(PyExc_TypeError,
        "%s must be a byte string, ASCII-only Unicode string, or a buffer object",
        what);
    return -1;
}

PYCURL_INTERNAL PyObject *
PyText_FromString_Ignore(const char *string)
{
    PyObject *v;
    PyObject *u;

    v = Py_BuildValue("y", string);
    if (v == NULL) {
        return NULL;
    }

    u = PyUnicode_FromEncodedObject(v, NULL, "replace");
    Py_DECREF(v);
    return u;
}
