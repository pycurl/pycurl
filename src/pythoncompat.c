#include "pycurl.h"

#if PY_MAJOR_VERSION >= 3

PYCURL_INTERNAL PyObject *
my_getattro(PyObject *co, PyObject *name, PyObject *dict1, PyObject *dict2, PyMethodDef *m)
{
    PyObject *v = NULL;
    if( dict1 != NULL )
        v = PyDict_GetItem(dict1, name);
    if( v == NULL && dict2 != NULL )
        v = PyDict_GetItem(dict2, name);
    if( v != NULL )
    {
        Py_INCREF(v);
        return v;
    }
    PyErr_SetString(PyExc_AttributeError, "trying to obtain a non-existing attribute");
    return NULL;
}

PYCURL_INTERNAL int
my_setattro(PyObject **dict, PyObject *name, PyObject *v)
{
    if( *dict == NULL )
    {
        *dict = PyDict_New();
        if( *dict == NULL )
            return -1;
    }
    if (v != NULL)
        return PyDict_SetItem(*dict, name, v);
    else {
        int v = PyDict_DelItem(*dict, name);
        if (v != 0) {
            /* need to convert KeyError to AttributeError */
            if (PyErr_ExceptionMatches(PyExc_KeyError)) {
                PyErr_SetString(PyExc_AttributeError, "trying to delete a non-existing attribute");
            }
        }
        return v;
    }
}

#else /* PY_MAJOR_VERSION >= 3 */

PYCURL_INTERNAL int
my_setattr(PyObject **dict, char *name, PyObject *v)
{
    if (v == NULL) {
        int rv = -1;
        if (*dict != NULL)
            rv = PyDict_DelItemString(*dict, name);
        if (rv < 0)
            PyErr_SetString(PyExc_AttributeError, "delete non-existing attribute");
        return rv;
    }
    if (*dict == NULL) {
        *dict = PyDict_New();
        if (*dict == NULL)
            return -1;
    }
    return PyDict_SetItemString(*dict, name, v);
}

PYCURL_INTERNAL PyObject *
my_getattr(PyObject *co, char *name, PyObject *dict1, PyObject *dict2, PyMethodDef *m)
{
    PyObject *v = NULL;
    if (v == NULL && dict1 != NULL)
        v = PyDict_GetItemString(dict1, name);
    if (v == NULL && dict2 != NULL)
        v = PyDict_GetItemString(dict2, name);
    if (v != NULL) {
        Py_INCREF(v);
        return v;
    }
    return Py_FindMethod(m, co, name);
}

#endif /* PY_MAJOR_VERSION >= 3 */

/* vi:ts=4:et:nowrap
 */
