#include "pycurl.h"

#ifdef HAVE_CURL_MIME

/*
 * Shared userdata passed to curl_mime_data_cb callbacks.
 * One owner can be referenced by multiple duplicated easy handles.
 */
typedef struct CurlMimeDataCbOwner {
    PyObject_HEAD
    PyObject *read_cb;
    PyObject *seek_cb;
    PyObject *free_cb;
    PyObject *userdata;
    Py_ssize_t shared_refcount;
    int free_called;
} CurlMimeDataCbOwner;

static PyTypeObject CurlMimeDataCbOwner_Type;

static int
curlmime_check_state(CurlMimeObject *self, const char *name)
{
    if (self->mime == NULL) {
        PyErr_Format(ErrorObject, "cannot invoke %s() - no mime handle", name);
        return -1;
    }
    if (self->curl == NULL) {
        PyErr_Format(ErrorObject, "cannot invoke %s() - no curl handle", name);
        return -1;
    }
    return check_curl_state(self->curl, 1 | 2, name);
}

static int
curlmimepart_check_state(CurlMimePartObject *self, const char *name)
{
    CurlMimeObject *mime = self->mime;

    if (mime == NULL || mime->mime == NULL) {
        PyErr_Format(ErrorObject, "cannot invoke %s() - no mime handle", name);
        return -1;
    }
    if (self->part == NULL) {
        PyErr_Format(ErrorObject, "cannot invoke %s() - no mime part", name);
        return -1;
    }
    if (mime->curl == NULL) {
        PyErr_Format(ErrorObject, "cannot invoke %s() - no curl handle", name);
        return -1;
    }
    return check_curl_state(mime->curl, 1 | 2, name);
}

static void
curlmime_set_error(CurlObject *curl, int code)
{
    if (curl != NULL) {
        create_and_set_error_object(curl, code);
        return;
    }

    {
        PyObject *v = Py_BuildValue("(is)", code, curl_easy_strerror((CURLcode)code));
        if (v != NULL) {
            PyErr_SetObject(ErrorObject, v);
            Py_DECREF(v);
        }
    }
}

static int
curlmime_data_cb_owner_traverse(CurlMimeDataCbOwner *self, visitproc visit, void *arg)
{
    int err;
#undef VISIT
#define VISIT(v)    if ((v) != NULL && ((err = visit(v, arg)) != 0)) return err

    VISIT(self->read_cb);
    VISIT(self->seek_cb);
    VISIT(self->free_cb);
    VISIT(self->userdata);

    return 0;
#undef VISIT
}

static int
curlmime_data_cb_owner_clear(CurlMimeDataCbOwner *self)
{
    Py_CLEAR(self->read_cb);
    Py_CLEAR(self->seek_cb);
    Py_CLEAR(self->free_cb);
    Py_CLEAR(self->userdata);
    return 0;
}

static void
curlmime_data_cb_owner_dealloc(CurlMimeDataCbOwner *self)
{
    PyObject_GC_UnTrack(self);
    Py_TRASHCAN_BEGIN(self, curlmime_data_cb_owner_dealloc);
    curlmime_data_cb_owner_clear(self);
    Py_TYPE(self)->tp_free((PyObject *)self);
    Py_TRASHCAN_END;
}

static CurlMimeDataCbOwner *
curlmime_data_cb_owner_new(PyObject *read_cb, PyObject *seek_cb, PyObject *free_cb, PyObject *userdata)
{
    CurlMimeDataCbOwner *owner;

    if (!(CurlMimeDataCbOwner_Type.tp_flags & Py_TPFLAGS_READY)) {
        if (PyType_Ready(&CurlMimeDataCbOwner_Type) != 0) {
            return NULL;
        }
    }

    owner = (CurlMimeDataCbOwner *)CurlMimeDataCbOwner_Type.tp_alloc(
        &CurlMimeDataCbOwner_Type, 0
    );
    if (owner == NULL) {
        return NULL;
    }

    owner->read_cb = NULL;
    owner->seek_cb = NULL;
    owner->free_cb = NULL;
    owner->userdata = NULL;
    owner->shared_refcount = 0;
    owner->free_called = 0;

    Py_INCREF(read_cb);
    owner->read_cb = read_cb;

    if (seek_cb != Py_None) {
        Py_INCREF(seek_cb);
        owner->seek_cb = seek_cb;
    }
    if (free_cb != Py_None) {
        Py_INCREF(free_cb);
        owner->free_cb = free_cb;
    }
    Py_INCREF(userdata);
    owner->userdata = userdata;

    return owner;
}

static void
curlmime_data_cb_owner_add_libcurl_ref(CurlMimeDataCbOwner *owner)
{
    if (owner == NULL) {
        return;
    }

    /*
     * Track one logical reference per easy handle that may invoke libcurl's
     * freefunc for this owner.
     */
    owner->shared_refcount += 1;
    Py_INCREF(owner);
}

static void
curlmime_data_cb_owner_release_libcurl_ref(CurlMimeDataCbOwner *owner, int invoke_user_free)
{
    PyObject *free_result = NULL;

    if (owner == NULL) {
        return;
    }

    if (owner->shared_refcount <= 0) {
        /*
         * Defensive: do not decref without a matching logical libcurl ref.
         * This avoids crashing on unexpected extra freefunc invocations.
         */
        PyErr_SetString(ErrorObject, "internal error: mime data_cb owner libcurl refcount underflow");
        PyErr_WriteUnraisable((PyObject *)owner);
        return;
    }
    owner->shared_refcount -= 1;

    if (invoke_user_free && owner->shared_refcount == 0 && !owner->free_called) {
        owner->free_called = 1;

        if (owner->free_cb != NULL) {
            free_result = PyObject_CallFunctionObjArgs(owner->free_cb, owner->userdata, NULL);
            if (free_result == NULL) {
                PyErr_WriteUnraisable(owner->free_cb);
            } else {
                Py_DECREF(free_result);
            }
        }
    }

    Py_DECREF(owner);
}

static int
curlmime_owner_list_remove_ptr(PyObject *owners, PyObject *owner_obj)
{
    Py_ssize_t i;
    Py_ssize_t len;

    if (owners == NULL || owner_obj == NULL) {
        return 0;
    }
    if (!PyList_Check(owners)) {
        PyErr_SetString(ErrorObject, "internal error: owner list is not a list");
        return -1;
    }

    assert(PyList_Check(owners));
    len = PyList_GET_SIZE(owners);
    for (i = 0; i < len; i++) {
        if (PyList_GET_ITEM(owners, i) == owner_obj) {
            if (PySequence_DelItem(owners, i) != 0) {
                return -1;
            }
            break;
        }
    }
    return 0;
}

static int
curlmimepart_drop_data_cb_owner(CurlMimePartObject *self)
{
    PyObject *owners;

    if (self->data_cb_owner == NULL) {
        return 0;
    }

    owners = (self->mime != NULL) ? self->mime->data_cb_owners : NULL;
    if (owners != NULL &&
        curlmime_owner_list_remove_ptr(owners, self->data_cb_owner) != 0)
    {
        PyErr_Clear();
    }

    Py_CLEAR(self->data_cb_owner);
    return 0;
}

static size_t
curlmimepart_read_callback(char *ptr, size_t size, size_t nmemb, void *arg)
{
    CurlMimeDataCbOwner *owner = (CurlMimeDataCbOwner *)arg;
    PyObject *arglist = NULL;
    PyObject *result = NULL;
    Py_buffer view;
    size_t ret = CURL_READFUNC_ABORT;
    int total_size;
    PyGILState_STATE gil_state;

    if (owner == NULL || owner->read_cb == NULL) {
        return ret;
    }
    if (!Py_IsInitialized()) {
        return ret;
    }

    /*
     * Use GIL-state API instead of callback thread-state helpers because
     * mime data callbacks can run for duplicated easy handles and are not
     * tied to a single CurlObject callback state owner.
     */
    gil_state = PyGILState_Ensure();

    if (size <= 0 || nmemb <= 0) {
        goto done;
    }
    total_size = (int)(size * nmemb);
    if (total_size < 0 || (size_t)total_size / size != nmemb) {
        PyErr_SetString(ErrorObject, "integer overflow in mime read callback");
        goto verbose_error;
    }

    arglist = Py_BuildValue("(Oi)", owner->userdata, total_size);
    if (arglist == NULL) {
        goto verbose_error;
    }
    result = PyObject_Call(owner->read_cb, arglist, NULL);
    Py_DECREF(arglist);
    arglist = NULL;
    if (result == NULL) {
        goto verbose_error;
    }

    if (PyObject_CheckBuffer(result)) {
        if (PyObject_GetBuffer(result, &view, PyBUF_SIMPLE) != 0) {
            goto verbose_error;
        }
        if (view.len < 0 || view.len > total_size) {
            PyErr_Format(ErrorObject, "invalid return value for mime read callback (%ld bytes returned when at most %ld bytes were wanted)", (long)view.len, (long)total_size);
            PyBuffer_Release(&view);
            goto verbose_error;
        }
        memcpy(ptr, view.buf, (size_t)view.len);
        ret = (size_t)view.len;
        PyBuffer_Release(&view);
    }
    else if (PyUnicode_Check(result)) {
        char *buf = NULL;
        Py_ssize_t obj_size = -1;
        Py_ssize_t conv_res;
        PyObject *encoded = PyUnicode_AsEncodedString(result, "ascii", "strict");

        if (encoded == NULL) {
            goto verbose_error;
        }
        conv_res = PyByteStr_AsStringAndSize(encoded, &buf, &obj_size);
        if (conv_res != 0 || obj_size < 0 || obj_size > total_size) {
            Py_DECREF(encoded);
            PyErr_Format(ErrorObject, "invalid return value for mime read callback (%ld bytes returned after ASCII encoding when at most %ld bytes were wanted)", (long)obj_size, (long)total_size);
            goto verbose_error;
        }
        memcpy(ptr, buf, obj_size);
        Py_DECREF(encoded);
        ret = (size_t)obj_size;
    }
    else if (PyLong_Check(result)) {
        long long_res = PyLong_AsLong(result);
        if (long_res != CURL_READFUNC_ABORT && long_res != CURL_READFUNC_PAUSE) {
            PyErr_SetString(ErrorObject, "mime read callback must return a buffer object, an ASCII-only Unicode string, READFUNC_ABORT, or READFUNC_PAUSE");
            goto verbose_error;
        }
        ret = (size_t)long_res;
    }
    else {
        PyErr_SetString(ErrorObject, "mime read callback must return an object supporting the buffer protocol, an ASCII-only Unicode string, READFUNC_ABORT, or READFUNC_PAUSE");
        goto verbose_error;
    }

done:
    Py_XDECREF(result);
    PyGILState_Release(gil_state);
    return ret;

verbose_error:
    print_callback_error_if_regular_exception();
    goto done;
}

static int
curlmimepart_seek_callback(void *arg, curl_off_t offset, int origin)
{
    CurlMimeDataCbOwner *owner = (CurlMimeDataCbOwner *)arg;
    PyObject *arglist = NULL;
    PyObject *result = NULL;
    int ret = CURL_SEEKFUNC_FAIL; /* Fail by default; user callback can return CANTSEEK explicitly. */
    int source = 0;
    PyGILState_STATE gil_state;

    if (owner == NULL || owner->seek_cb == NULL) {
        return ret;
    }
    if (!Py_IsInitialized()) {
        return ret;
    }

    /*
     * Use GIL-state API instead of callback thread-state helpers because
     * mime data callbacks can run for duplicated easy handles and are not
     * tied to a single CurlObject callback state owner.
     */
    gil_state = PyGILState_Ensure();

    /* Match existing SEEKFUNCTION callback behavior: pass origin as 0/1/2. */
    switch (origin)
    {
      case SEEK_SET:
          source = 0;
          break;
      case SEEK_CUR:
          source = 1;
          break;
      case SEEK_END:
          source = 2;
          break;
      default:
          source = origin;
          break;
    }

    arglist = Py_BuildValue("(OLi)", owner->userdata, (PY_LONG_LONG)offset, source);
    if (arglist == NULL) {
        goto verbose_error;
    }
    result = PyObject_Call(owner->seek_cb, arglist, NULL);
    Py_DECREF(arglist);
    arglist = NULL;
    if (result == NULL) {
        goto verbose_error;
    }

    if (result == Py_None) {
        ret = CURL_SEEKFUNC_OK;
    }
    else if (PyLong_Check(result)) {
        int ret_code = (int)PyLong_AsLong(result);
        if (PyErr_Occurred()) {
            goto verbose_error;
        }
        if (ret_code < CURL_SEEKFUNC_OK || ret_code > CURL_SEEKFUNC_CANTSEEK) {
            PyErr_Format(ErrorObject, "invalid return value for mime seek callback %d not in (0, 1, 2)", ret_code);
            goto verbose_error;
        }
        ret = ret_code;
    }
    else {
        PyErr_SetString(ErrorObject, "mime seek callback must return 0 (SEEKFUNC_OK), 1 (SEEKFUNC_FAIL), 2 (SEEKFUNC_CANTSEEK) or None");
        goto verbose_error;
    }

done:
    Py_XDECREF(result);
    PyGILState_Release(gil_state);
    return ret;

verbose_error:
    print_callback_error_if_regular_exception();
    goto done;
}

static void
curlmimepart_free_callback(void *arg)
{
    CurlMimeDataCbOwner *owner = (CurlMimeDataCbOwner *)arg;
    PyGILState_STATE gil_state;

    if (owner == NULL || !Py_IsInitialized()) {
        return;
    }

    /*
     * libcurl may invoke freefunc from non-Python threads, and duplicated easy
     * handles can invoke it multiple times for the same owner pointer.
     */
    gil_state = PyGILState_Ensure();
    curlmime_data_cb_owner_release_libcurl_ref(owner, 1);
    PyGILState_Release(gil_state);
}

static int
curlmime_detach_if_pinned(CurlMimeObject *self, int report_error)
{
    int res;

    if (self == NULL || self->curl == NULL ||
        self->curl->mimepost_obj != (PyObject *)self)
    {
        return 0;
    }

    if (self->curl->handle != NULL) {
        res = (int)curl_easy_setopt(self->curl->handle, CURLOPT_MIMEPOST, NULL);
        if (res != CURLE_OK) {
            if (report_error) {
                curlmime_set_error(self->curl, res);
            }
            return -1;
        }
    }

    Py_CLEAR(self->curl->mimepost_obj);
    return 0;
}

static struct curl_slist *
curlmime_headers_to_slist(PyObject *obj)
{
    struct curl_slist *slist = NULL;
    Py_ssize_t i;
    int which;
    Py_ssize_t len;

    if (obj == Py_None) {
        return NULL;
    }

    which = PyListOrTuple_Check(obj);
    if (!which) {
        PyErr_SetString(PyExc_TypeError, "headers must be a list or tuple of strings");
        return NULL;
    }

    len = PyListOrTuple_Size(obj, which);
    for (i = 0; i < len; i++) {
        PyObject *header_obj = PyListOrTuple_GetItem(obj, i, which);
        struct curl_slist *next;
        char *header;
        PyObject *encoded_obj = NULL;

        if (!PyText_Check(header_obj)) {
            curl_slist_free_all(slist);
            PyErr_SetString(PyExc_TypeError, "headers must contain only byte or ascii-unicode strings");
            return NULL;
        }

        header = PyText_AsString_NoNUL(header_obj, &encoded_obj);
        if (header == NULL) {
            curl_slist_free_all(slist);
            return NULL;
        }

        next = curl_slist_append(slist, header);
        PyText_EncodedDecref(encoded_obj);
        if (next == NULL) {
            curl_slist_free_all(slist);
            PyErr_NoMemory();
            return NULL;
        }
        slist = next;
    }

    return slist;
}

static PyObject *
curlmime_make_part(CurlMimeObject *mime, curl_mimepart *part)
{
    CurlMimePartObject *part_obj;

    part_obj = (CurlMimePartObject *)p_CurlMimePart_Type->tp_alloc(p_CurlMimePart_Type, 0);
    if (part_obj == NULL) {
        return NULL;
    }

    part_obj->part = part;
    part_obj->mime = (CurlMimeObject *)Py_NewRef((PyObject *)mime);
    part_obj->data_cb_owner = NULL;

    return (PyObject *)part_obj;
}

static int
curlmime_invalidate_parts(CurlMimeObject *self)
{
    Py_ssize_t i;
    Py_ssize_t len;

    if (self->parts == NULL) {
        return 0;
    }

    len = PyList_GET_SIZE(self->parts);
    for (i = 0; i < len; i++) {
        PyObject *part_obj = PyList_GET_ITEM(self->parts, i);
        if (PyObject_TypeCheck(part_obj, p_CurlMimePart_Type)) {
            CurlMimePartObject *part = (CurlMimePartObject *)part_obj;
            if (part->mime == self) {
                part->part = NULL;
                Py_CLEAR(part->mime);
            }
            Py_CLEAR(part->data_cb_owner);
        }
    }

    return 0;
}

static void
curlmime_invalidate_wrappers(CurlMimeObject *self)
{
    Py_ssize_t i;
    Py_ssize_t len;

    if (self == NULL) {
        return;
    }

    if (self->mime == NULL && self->curl == NULL &&
        self->parts == NULL && self->submimes == NULL &&
        self->data_cb_owners == NULL)
    {
        return;
    }

    /* Mark this wrapper as invalid first to avoid recursive cycles. */
    self->mime = NULL;
    self->owns_mime = 0;

    (void)curlmime_invalidate_parts(self);

    if (self->submimes != NULL) {
        len = PyList_GET_SIZE(self->submimes);
        for (i = 0; i < len; i++) {
            PyObject *submime_obj = PyList_GET_ITEM(self->submimes, i);
            if (PyObject_TypeCheck(submime_obj, p_CurlMime_Type)) {
                curlmime_invalidate_wrappers((CurlMimeObject *)submime_obj);
            }
        }
    }

    Py_CLEAR(self->parts);
    Py_CLEAR(self->submimes);
    Py_CLEAR(self->data_cb_owners);
    Py_CLEAR(self->curl);
}

static PyObject *
do_curlmime_new(PyTypeObject *subtype, PyObject *args, PyObject *kwds)
{
    CurlMimeObject *self;
    CurlObject *curl;
    static char *kwlist[] = {"curl", NULL};

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "O!", kwlist, p_Curl_Type, &curl)) {
        return NULL;
    }
    if (check_curl_state(curl, 1 | 2, "CurlMime") != 0) {
        return NULL;
    }

    self = (CurlMimeObject *)subtype->tp_alloc(subtype, 0);
    if (self == NULL) {
        return NULL;
    }

    self->owns_mime = 1;
    self->curl = (CurlObject *)Py_NewRef((PyObject *)curl);
    self->parts = PyList_New((Py_ssize_t)0);
    if (self->parts == NULL) {
        Py_DECREF(self);
        return NULL;
    }
    self->submimes = PyList_New((Py_ssize_t)0);
    if (self->submimes == NULL) {
        Py_DECREF(self);
        return NULL;
    }
    self->data_cb_owners = PyList_New((Py_ssize_t)0);
    if (self->data_cb_owners == NULL) {
        Py_DECREF(self);
        return NULL;
    }

    self->mime = curl_mime_init(curl->handle);
    if (self->mime == NULL) {
        Py_DECREF(self);
        PyErr_NoMemory();
        return NULL;
    }

    return (PyObject *)self;
}

static int
do_curlmime_traverse(CurlMimeObject *self, visitproc visit, void *arg)
{
    int err;
#undef VISIT
#define VISIT(v)    if ((v) != NULL && ((err = visit(v, arg)) != 0)) return err

    VISIT((PyObject *)self->curl);
    VISIT(self->parts);
    VISIT(self->submimes);
    VISIT(self->data_cb_owners);

    return 0;
#undef VISIT
}

static int
do_curlmime_clear(CurlMimeObject *self)
{
    curl_mime *mime = self->mime;
    int owns_mime = self->owns_mime;

    if (curlmime_detach_if_pinned(self, 0) != 0) {
        PyErr_Clear();
        return 0;
    }

    curlmime_invalidate_wrappers(self);

    if (owns_mime && mime != NULL) {
        curl_mime_free(mime);
    }
    return 0;
}

static void
do_curlmime_dealloc(CurlMimeObject *self)
{
    PyObject_GC_UnTrack(self);
    Py_TRASHCAN_BEGIN(self, do_curlmime_dealloc);
    do_curlmime_clear(self);
    CurlMime_Type.tp_free(self);
    Py_TRASHCAN_END;
}

static PyObject *
do_curlmime_close(CurlMimeObject *self, PyObject *Py_UNUSED(ignored))
{
    if (self->curl != NULL && check_curl_state(self->curl, 2, "close") != 0) {
        return NULL;
    }
    if (curlmime_detach_if_pinned(self, 1) != 0) {
        return NULL;
    }

    do_curlmime_clear(self);
    Py_RETURN_NONE;
}

static PyObject *
do_curlmime_closed(CurlMimeObject *self, PyObject *Py_UNUSED(ignored))
{
    if (self->mime == NULL) {
        Py_RETURN_TRUE;
    } else {
        Py_RETURN_FALSE;
    }
}

static PyObject *
do_curlmime_addpart(CurlMimeObject *self, PyObject *Py_UNUSED(ignored))
{
    curl_mimepart *part;
    PyObject *part_obj;

    if (curlmime_check_state(self, "addpart") != 0) {
        return NULL;
    }

    part = curl_mime_addpart(self->mime);
    if (part == NULL) {
        PyErr_NoMemory();
        return NULL;
    }

    part_obj = curlmime_make_part(self, part);
    if (part_obj == NULL) {
        return NULL;
    }

    if (PyList_Append(self->parts, part_obj) != 0) {
        Py_DECREF(part_obj);
        return NULL;
    }

    return part_obj;
}

static PyObject *
do_curlmime_enter(CurlMimeObject *self, PyObject *Py_UNUSED(ignored))
{
    if (curlmime_check_state(self, "__enter__") != 0) {
        return NULL;
    }

    Py_INCREF(self);
    return (PyObject *)self;
}

static PyObject *
do_curlmime_exit(CurlMimeObject *self, PyObject *args)
{
    PyObject *exc_type;
    PyObject *exc;
    PyObject *tb;

    if (!PyArg_ParseTuple(args, "OOO:__exit__", &exc_type, &exc, &tb)) {
        return NULL;
    }

    return do_curlmime_close(self, NULL);
}

static PyObject *do_curlmimepart_name(CurlMimePartObject *self, PyObject *arg);
static PyObject *do_curlmimepart_data(CurlMimePartObject *self, PyObject *arg);
static PyObject *do_curlmimepart_filedata(CurlMimePartObject *self, PyObject *arg);
static PyObject *do_curlmimepart_filename(CurlMimePartObject *self, PyObject *arg);
static PyObject *do_curlmimepart_type(CurlMimePartObject *self, PyObject *arg);
static PyObject *do_curlmimepart_encoder(CurlMimePartObject *self, PyObject *arg);
static PyObject *do_curlmimepart_data_cb(CurlMimePartObject *self, PyObject *args, PyObject *kwds);
static PyObject *do_curlmimepart_headers(CurlMimePartObject *self, PyObject *arg);
static PyObject *do_curlmimepart_subparts(CurlMimePartObject *self, PyObject *arg);

static int
curlmimepart_data_as_string_or_buffer(PyObject *arg,
    char **data,
    Py_ssize_t *data_len,
    PyObject **encoded_obj,
    Py_buffer *view,
    int *view_active)
{
    if (PyObject_CheckBuffer(arg)) {
        if (PyObject_GetBuffer(arg, view, PyBUF_SIMPLE) != 0) {
            return -1;
        }

        *view_active = 1;
        *data = (char *)view->buf;
        *data_len = view->len;
        return 0;
    }

    if (PyByteStr_Check(arg) || PyUnicode_Check(arg)) {
        return PyText_AsStringAndSize(arg, data, data_len, encoded_obj);
    }

    PyErr_SetString(PyExc_TypeError,
        "data() argument must be a byte string, ASCII-only Unicode string, or a buffer object");
    return -1;
}

static int
curlmime_validate_text_arg(PyObject *obj, const char *name)
{
    char *value;
    PyObject *encoded_obj = NULL;

    if (obj == NULL || obj == Py_None) {
        return 0;
    }

    if (!PyText_Check(obj)) {
        PyErr_Format(PyExc_TypeError, "%s must be a byte string or ascii-unicode string", name);
        return -1;
    }

    value = PyText_AsString_NoNUL(obj, &encoded_obj);
    PyText_EncodedDecref(encoded_obj);
    if (value == NULL) {
        return -1;
    }

    return 0;
}

static int
curlmime_validate_data_arg(PyObject *obj)
{
    Py_buffer view;
    PyObject *encoded_obj = NULL;
    char *data;
    Py_ssize_t data_len = 0;
    int view_active = 0;

    if (obj == NULL || obj == Py_None) {
        return 0;
    }

    if (curlmimepart_data_as_string_or_buffer(obj, &data, &data_len,
            &encoded_obj, &view, &view_active) != 0)
    {
        return -1;
    }

    if (view_active) {
        PyBuffer_Release(&view);
    }
    PyText_EncodedDecref(encoded_obj);

    return 0;
}

static int
curlmime_validate_file_arg(CurlMimeObject *self, PyObject *obj, const char *name)
{
    FILE *fp;
    char *path;
    PyObject *encoded_obj = NULL;

    if (obj == NULL || obj == Py_None) {
        return 0;
    }

    if (curlmime_validate_text_arg(obj, name) != 0) {
        return -1;
    }

    path = PyText_AsString_NoNUL(obj, &encoded_obj);
    if (path == NULL) {
        return -1;
    }

    fp = fopen(path, "rb");
    PyText_EncodedDecref(encoded_obj);
    if (fp == NULL) {
        curlmime_set_error(self != NULL ? self->curl : NULL, CURLE_READ_ERROR);
        return -1;
    }
    fclose(fp);
    return 0;
}

static int
curlmime_validate_headers_arg(PyObject *obj)
{
    struct curl_slist *slist;

    if (obj == NULL || obj == Py_None) {
        return 0;
    }

    slist = curlmime_headers_to_slist(obj);
    if (slist == NULL) {
        return PyErr_Occurred() ? -1 : 0;
    }

    curl_slist_free_all(slist);
    return 0;
}

static int
curlmime_validate_builder_args(CurlMimeObject *self,
    PyObject *name_obj,
    PyObject *data_obj,
    PyObject *file_obj,
    PyObject *filename_obj,
    PyObject *content_type_obj,
    PyObject *headers_obj,
    PyObject *encoder_obj)
{
    if (data_obj != NULL && data_obj != Py_None &&
        file_obj != NULL && file_obj != Py_None)
    {
        PyErr_SetString(PyExc_ValueError, "add() accepts at most one of data or file");
        return -1;
    }
    if (curlmime_validate_text_arg(name_obj, "name") != 0) {
        return -1;
    }
    if (curlmime_validate_data_arg(data_obj) != 0) {
        return -1;
    }
    if (curlmime_validate_file_arg(self, file_obj, "file") != 0) {
        return -1;
    }
    if (curlmime_validate_text_arg(filename_obj, "filename") != 0) {
        return -1;
    }
    if (curlmime_validate_text_arg(content_type_obj, "content_type") != 0) {
        return -1;
    }
    if (curlmime_validate_headers_arg(headers_obj) != 0) {
        return -1;
    }
    if (curlmime_validate_text_arg(encoder_obj, "encoder") != 0) {
        return -1;
    }
    return 0;
}

static int
curlmime_add_apply(CurlMimePartObject *part,
    PyObject *name_obj,
    PyObject *data_obj,
    PyObject *file_obj,
    PyObject *filename_obj,
    PyObject *content_type_obj,
    PyObject *headers_obj,
    PyObject *encoder_obj)
{
    PyObject *rv;

    if (name_obj != NULL && name_obj != Py_None) {
        rv = do_curlmimepart_name(part, name_obj);
        if (rv == NULL) {
            return -1;
        }
        Py_DECREF(rv);
    }

    if (data_obj != NULL && data_obj != Py_None) {
        rv = do_curlmimepart_data(part, data_obj);
        if (rv == NULL) {
            return -1;
        }
        Py_DECREF(rv);
    } else if (file_obj != NULL && file_obj != Py_None) {
        rv = do_curlmimepart_filedata(part, file_obj);
        if (rv == NULL) {
            return -1;
        }
        Py_DECREF(rv);
    }

    if (filename_obj != NULL && filename_obj != Py_None) {
        rv = do_curlmimepart_filename(part, filename_obj);
        if (rv == NULL) {
            return -1;
        }
        Py_DECREF(rv);
    }

    if (content_type_obj != NULL && content_type_obj != Py_None) {
        rv = do_curlmimepart_type(part, content_type_obj);
        if (rv == NULL) {
            return -1;
        }
        Py_DECREF(rv);
    }

    if (headers_obj != NULL && headers_obj != Py_None) {
        rv = do_curlmimepart_headers(part, headers_obj);
        if (rv == NULL) {
            return -1;
        }
        Py_DECREF(rv);
    }

    if (encoder_obj != NULL && encoder_obj != Py_None) {
        rv = do_curlmimepart_encoder(part, encoder_obj);
        if (rv == NULL) {
            return -1;
        }
        Py_DECREF(rv);
    }

    return 0;
}

static PyObject *
do_curlmime_add(CurlMimeObject *self, PyObject *args, PyObject *kwds)
{
    PyObject *name_obj = NULL;
    PyObject *data_obj = NULL;
    PyObject *file_obj = NULL;
    PyObject *filename_obj = NULL;
    PyObject *content_type_obj = NULL;
    PyObject *headers_obj = NULL;
    PyObject *encoder_obj = NULL;
    PyObject *part_obj;
    static char *kwlist[] = {
        "name", "data", "file", "filename", "content_type", "headers", "encoder", NULL
    };

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "|OOOOOOO:add", kwlist,
            &name_obj, &data_obj, &file_obj, &filename_obj,
            &content_type_obj, &headers_obj, &encoder_obj))
    {
        return NULL;
    }

    if (curlmime_validate_builder_args(self, name_obj, data_obj, file_obj, filename_obj,
            content_type_obj, headers_obj, encoder_obj) != 0)
    {
        return NULL;
    }

    part_obj = do_curlmime_addpart(self, NULL);
    if (part_obj == NULL) {
        return NULL;
    }

    if (curlmime_add_apply((CurlMimePartObject *)part_obj,
            name_obj, data_obj, file_obj, filename_obj,
            content_type_obj, headers_obj, encoder_obj) != 0)
    {
        Py_DECREF(part_obj);
        return NULL;
    }

    return part_obj;
}

static PyObject *
do_curlmime_add_field(CurlMimeObject *self, PyObject *args, PyObject *kwds)
{
    PyObject *name_obj;
    PyObject *value_obj;
    PyObject *content_type_obj = NULL;
    PyObject *encoder_obj = NULL;
    PyObject *headers_obj = NULL;
    PyObject *part_obj;
    static char *kwlist[] = {"name", "value", "content_type", "encoder", "headers", NULL};

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "OO|OOO:add_field", kwlist,
            &name_obj, &value_obj, &content_type_obj, &encoder_obj, &headers_obj))
    {
        return NULL;
    }

    if (curlmime_validate_builder_args(self, name_obj, value_obj, NULL, NULL,
            content_type_obj, headers_obj, encoder_obj) != 0)
    {
        return NULL;
    }

    part_obj = do_curlmime_addpart(self, NULL);
    if (part_obj == NULL) {
        return NULL;
    }

    if (curlmime_add_apply((CurlMimePartObject *)part_obj,
            name_obj, value_obj, NULL, NULL,
            content_type_obj, headers_obj, encoder_obj) != 0)
    {
        Py_DECREF(part_obj);
        return NULL;
    }

    return part_obj;
}

static PyObject *
do_curlmime_add_file(CurlMimeObject *self, PyObject *args, PyObject *kwds)
{
    PyObject *name_obj;
    PyObject *path_obj;
    PyObject *filename_obj = NULL;
    PyObject *content_type_obj = NULL;
    PyObject *headers_obj = NULL;
    PyObject *encoder_obj = NULL;
    PyObject *part_obj;
    static char *kwlist[] = {"name", "path", "filename", "content_type", "headers", "encoder", NULL};

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "OO|OOOO:add_file", kwlist,
            &name_obj, &path_obj, &filename_obj, &content_type_obj, &headers_obj, &encoder_obj))
    {
        return NULL;
    }

    if (curlmime_validate_builder_args(self, name_obj, NULL, path_obj, filename_obj,
            content_type_obj, headers_obj, encoder_obj) != 0)
    {
        return NULL;
    }

    part_obj = do_curlmime_addpart(self, NULL);
    if (part_obj == NULL) {
        return NULL;
    }

    if (curlmime_add_apply((CurlMimePartObject *)part_obj,
            name_obj, NULL, path_obj, filename_obj,
            content_type_obj, headers_obj, encoder_obj) != 0)
    {
        Py_DECREF(part_obj);
        return NULL;
    }

    return part_obj;
}

static PyObject *
do_curlmime_add_multipart(CurlMimeObject *self, PyObject *args, PyObject *kwds)
{
    PyObject *name_obj = NULL;
    PyObject *subtype_obj = NULL;
    PyObject *subtype_ref = NULL;
    PyObject *child_obj = NULL;
    PyObject *part_obj = NULL;
    PyObject *rv = NULL;
    PyObject *content_type_obj = NULL;
    PyObject *encoded_obj = NULL;
    char *subtype = NULL;
    static char *kwlist[] = {"name", "subtype", NULL};

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "|OO:add_multipart", kwlist, &name_obj, &subtype_obj)) {
        return NULL;
    }

    if (curlmime_validate_text_arg(name_obj, "name") != 0) {
        return NULL;
    }
    if (subtype_obj != NULL && subtype_obj != Py_None &&
        curlmime_validate_text_arg(subtype_obj, "subtype") != 0)
    {
        return NULL;
    }

    if (subtype_obj == NULL) {
        subtype_ref = PyText_FromString("mixed");
        if (subtype_ref == NULL) {
            return NULL;
        }
    } else {
        subtype_ref = Py_NewRef(subtype_obj);
    }

    if (subtype_ref != Py_None) {
        subtype = PyText_AsString_NoNUL(subtype_ref, &encoded_obj);
        if (subtype == NULL) {
            goto error;
        }

        content_type_obj = PyText_FromFormat("multipart/%s", subtype);
        PyText_EncodedDecref(encoded_obj);
        encoded_obj = NULL;
        if (content_type_obj == NULL) {
            goto error;
        }
    }

    child_obj = PyObject_CallFunctionObjArgs((PyObject *)p_CurlMime_Type, (PyObject *)self->curl, NULL);
    if (child_obj == NULL) {
        goto error;
    }

    part_obj = do_curlmime_addpart(self, NULL);
    if (part_obj == NULL) {
        goto error;
    }

    if (name_obj != NULL && name_obj != Py_None) {
        rv = do_curlmimepart_name((CurlMimePartObject *)part_obj, name_obj);
        if (rv == NULL) {
            goto error;
        }
        Py_CLEAR(rv);
    }

    rv = do_curlmimepart_subparts((CurlMimePartObject *)part_obj, child_obj);
    if (rv == NULL) {
        goto error;
    }
    Py_CLEAR(rv);

    if (content_type_obj != NULL) {
        rv = do_curlmimepart_type((CurlMimePartObject *)part_obj, content_type_obj);
        if (rv == NULL) {
            goto error;
        }
        Py_CLEAR(rv);
    }

    Py_CLEAR(content_type_obj);
    Py_CLEAR(subtype_ref);
    Py_CLEAR(part_obj);
    return child_obj;

error:
    Py_XDECREF(rv);
    PyText_EncodedDecref(encoded_obj);
    Py_XDECREF(content_type_obj);
    Py_XDECREF(subtype_ref);
    Py_XDECREF(child_obj);
    Py_XDECREF(part_obj);
    return NULL;
}

static void
curlmime_duphandle_incref_data_cb_owners_recursive(CurlMimeObject *mime)
{
    Py_ssize_t i;
    Py_ssize_t len;

    if (mime == NULL) {
        return;
    }

    if (mime->data_cb_owners != NULL) {
        len = PyList_GET_SIZE(mime->data_cb_owners);
        for (i = 0; i < len; i++) {
            PyObject *owner_obj = PyList_GET_ITEM(mime->data_cb_owners, i);
            if (PyObject_TypeCheck(owner_obj, &CurlMimeDataCbOwner_Type)) {
                curlmime_data_cb_owner_add_libcurl_ref((CurlMimeDataCbOwner *)owner_obj);
            }
        }
    }

    if (mime->submimes != NULL) {
        len = PyList_GET_SIZE(mime->submimes);
        for (i = 0; i < len; i++) {
            PyObject *submime_obj = PyList_GET_ITEM(mime->submimes, i);
            if (PyObject_TypeCheck(submime_obj, p_CurlMime_Type)) {
                curlmime_duphandle_incref_data_cb_owners_recursive((CurlMimeObject *)submime_obj);
            }
        }
    }
}

PYCURL_INTERNAL void
curlmime_duphandle_incref_data_cb_owners(PyObject *mime_obj)
{
    if (mime_obj == NULL || !PyObject_TypeCheck(mime_obj, p_CurlMime_Type)) {
        return;
    }

    curlmime_duphandle_incref_data_cb_owners_recursive((CurlMimeObject *)mime_obj);
}

static PyMethodDef curlmimeobject_methods[] = {
    {"add", (PyCFunction)do_curlmime_add, METH_VARARGS | METH_KEYWORDS, "Add a part using a keyword-oriented builder API."},
    {"add_field", (PyCFunction)do_curlmime_add_field, METH_VARARGS | METH_KEYWORDS, "Add a simple form field part."},
    {"add_file", (PyCFunction)do_curlmime_add_file, METH_VARARGS | METH_KEYWORDS, "Add a file upload part."},
    {"add_multipart", (PyCFunction)do_curlmime_add_multipart, METH_VARARGS | METH_KEYWORDS, "Add and attach a nested multipart CurlMime."},
    {"close", (PyCFunction)do_curlmime_close, METH_NOARGS, "Release the underlying curl_mime handle."},
    {"closed", (PyCFunction)do_curlmime_closed, METH_NOARGS, "Return whether this CurlMime object is closed."},
    {"addpart", (PyCFunction)do_curlmime_addpart, METH_NOARGS, "Create and return a new MIME part."},
    {"__enter__", (PyCFunction)do_curlmime_enter, METH_NOARGS, NULL},
    {"__exit__", (PyCFunction)do_curlmime_exit, METH_VARARGS, NULL},
    {NULL, NULL, 0, NULL}
};

static PyTypeObject CurlMimeDataCbOwner_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "pycurl._MimeDataCbOwner",            /* tp_name */
    sizeof(CurlMimeDataCbOwner),          /* tp_basicsize */
    0,                                    /* tp_itemsize */
    (destructor)curlmime_data_cb_owner_dealloc, /* tp_dealloc */
    0,                                    /* tp_print / tp_vectorcall_offset */
    0,                                    /* tp_getattr */
    0,                                    /* tp_setattr */
    0,                                    /* tp_reserved / tp_as_async */
    0,                                    /* tp_repr */
    0,                                    /* tp_as_number */
    0,                                    /* tp_as_sequence */
    0,                                    /* tp_as_mapping */
    0,                                    /* tp_hash */
    0,                                    /* tp_call */
    0,                                    /* tp_str */
    0,                                    /* tp_getattro */
    0,                                    /* tp_setattro */
    0,                                    /* tp_as_buffer */
    PYCURL_TYPE_FLAGS,                    /* tp_flags */
    "Internal owner for curl_mime_data_cb callbacks.", /* tp_doc */
    (traverseproc)curlmime_data_cb_owner_traverse, /* tp_traverse */
    (inquiry)curlmime_data_cb_owner_clear, /* tp_clear */
    0,                                    /* tp_richcompare */
    0,                                    /* tp_weaklistoffset */
    0,                                    /* tp_iter */
    0,                                    /* tp_iternext */
    0,                                    /* tp_methods */
    0,                                    /* tp_members */
    0,                                    /* tp_getset */
    0,                                    /* tp_base */
    0,                                    /* tp_dict */
    0,                                    /* tp_descr_get */
    0,                                    /* tp_descr_set */
    0,                                    /* tp_dictoffset */
    0,                                    /* tp_init */
    PyType_GenericAlloc,                  /* tp_alloc */
    0,                                    /* tp_new */
    PyObject_GC_Del,                      /* tp_free */
};

PYCURL_INTERNAL PyTypeObject CurlMime_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "pycurl.CurlMime",             /* tp_name */
    sizeof(CurlMimeObject),     /* tp_basicsize */
    0,                          /* tp_itemsize */
    (destructor)do_curlmime_dealloc, /* tp_dealloc */
    0,                          /* tp_print / tp_vectorcall_offset */
    0,                          /* tp_getattr */
    0,                          /* tp_setattr */
    0,                          /* tp_reserved / tp_as_async */
    0,                          /* tp_repr */
    0,                          /* tp_as_number */
    0,                          /* tp_as_sequence */
    0,                          /* tp_as_mapping */
    0,                          /* tp_hash */
    0,                          /* tp_call */
    0,                          /* tp_str */
    0,                          /* tp_getattro */
    0,                          /* tp_setattro */
    0,                          /* tp_as_buffer */
    PYCURL_TYPE_FLAGS,          /* tp_flags */
    "Python wrapper for libcurl MIME API.", /* tp_doc */
    (traverseproc)do_curlmime_traverse, /* tp_traverse */
    (inquiry)do_curlmime_clear, /* tp_clear */
    0,                          /* tp_richcompare */
    0,                          /* tp_weaklistoffset */
    0,                          /* tp_iter */
    0,                          /* tp_iternext */
    curlmimeobject_methods,     /* tp_methods */
    0,                          /* tp_members */
    0,                          /* tp_getset */
    0,                          /* tp_base */
    0,                          /* tp_dict */
    0,                          /* tp_descr_get */
    0,                          /* tp_descr_set */
    0,                          /* tp_dictoffset */
    0,                          /* tp_init */
    PyType_GenericAlloc,        /* tp_alloc */
    (newfunc)do_curlmime_new,   /* tp_new */
    PyObject_GC_Del,            /* tp_free */
};

static int
do_curlmimepart_traverse(CurlMimePartObject *self, visitproc visit, void *arg)
{
    int err;
#undef VISIT
#define VISIT(v)    if ((v) != NULL && ((err = visit(v, arg)) != 0)) return err

    VISIT((PyObject *)self->mime);
    VISIT(self->data_cb_owner);

    return 0;
#undef VISIT
}

static int
do_curlmimepart_clear(CurlMimePartObject *self)
{
    Py_CLEAR(self->data_cb_owner);
    Py_CLEAR(self->mime);
    self->part = NULL;
    return 0;
}

static void
do_curlmimepart_dealloc(CurlMimePartObject *self)
{
    PyObject_GC_UnTrack(self);
    Py_TRASHCAN_BEGIN(self, do_curlmimepart_dealloc);
    do_curlmimepart_clear(self);
    CurlMimePart_Type.tp_free(self);
    Py_TRASHCAN_END;
}

static PyObject *
do_curlmimepart_name(CurlMimePartObject *self, PyObject *arg)
{
    PyObject *encoded_obj = NULL;
    char *name;
    int res;

    if (curlmimepart_check_state(self, "name") != 0) {
        return NULL;
    }

    name = PyText_AsString_NoNUL(arg, &encoded_obj);
    if (name == NULL) {
        return NULL;
    }

    res = (int)curl_mime_name(self->part, name);
    PyText_EncodedDecref(encoded_obj);
    if (res != CURLE_OK) {
        curlmime_set_error(self->mime != NULL ? self->mime->curl : NULL, res);
        return NULL;
    }

    Py_RETURN_NONE;
}

static PyObject *
do_curlmimepart_data(CurlMimePartObject *self, PyObject *arg)
{
    Py_buffer view;
    PyObject *encoded_obj = NULL;
    char *data;
    Py_ssize_t data_len = 0;
    int view_active = 0;
    int res;

    if (curlmimepart_check_state(self, "data") != 0) {
        return NULL;
    }

    if (curlmimepart_data_as_string_or_buffer(arg, &data, &data_len,
            &encoded_obj, &view, &view_active) != 0)
    {
        return NULL;
    }

    res = (int)curl_mime_data(self->part, data, (size_t)data_len);
    if (view_active) {
        PyBuffer_Release(&view);
    }
    PyText_EncodedDecref(encoded_obj);
    if (res != CURLE_OK) {
        curlmime_set_error(self->mime != NULL ? self->mime->curl : NULL, res);
        return NULL;
    }
    if (curlmimepart_drop_data_cb_owner(self) != 0) {
        return NULL;
    }

    Py_RETURN_NONE;
}

static int
curlmimepart_parse_datasize(PyObject *datasize_obj, curl_off_t *datasize)
{
    PY_LONG_LONG value;

    if (datasize_obj == Py_None) {
        *datasize = (curl_off_t)-1;
        return 0;
    }

    value = PyLong_AsLongLong(datasize_obj);
    if (value == -1 && PyErr_Occurred()) {
        if (PyErr_ExceptionMatches(PyExc_TypeError)) {
            PyErr_SetString(PyExc_TypeError, "datasize must be an integer >= -1 or None");
        }
        return -1;
    }
    if ((curl_off_t)value != value) {
        PyErr_SetString(PyExc_OverflowError, "datasize does not fit into curl_off_t");
        return -1;
    }
    if (value < -1) {
        PyErr_SetString(PyExc_ValueError, "datasize must be >= -1");
        return -1;
    }

    *datasize = (curl_off_t)value;
    return 0;
}

static PyObject *
do_curlmimepart_data_cb(CurlMimePartObject *self, PyObject *args, PyObject *kwds)
{
    PyObject *datasize_obj;
    PyObject *read_cb;
    PyObject *seek_cb = Py_None;
    PyObject *free_cb = Py_None;
    PyObject *userdata = Py_None;
    CurlMimeDataCbOwner *owner = NULL;
    PyObject *owners = NULL;
    PyObject *old_owner_obj;
    curl_read_callback readfunc = curlmimepart_read_callback;
    curl_seek_callback seekfunc = NULL;
    curl_off_t datasize;
    int res;
    static char *kwlist[] = {"datasize", "read", "seek", "free", "userdata", NULL};

    if (!PyArg_ParseTupleAndKeywords(args, kwds, "OO|OOO:data_cb", kwlist,
            &datasize_obj, &read_cb, &seek_cb, &free_cb, &userdata))
    {
        return NULL;
    }

    if (curlmimepart_check_state(self, "data_cb") != 0) {
        return NULL;
    }
    if (curlmimepart_parse_datasize(datasize_obj, &datasize) != 0) {
        return NULL;
    }
    if (!PyCallable_Check(read_cb)) {
        PyErr_SetString(PyExc_TypeError, "read must be callable");
        return NULL;
    }
    if (seek_cb != Py_None && !PyCallable_Check(seek_cb)) {
        PyErr_SetString(PyExc_TypeError, "seek must be callable or None");
        return NULL;
    }
    if (free_cb != Py_None && !PyCallable_Check(free_cb)) {
        PyErr_SetString(PyExc_TypeError, "free must be callable or None");
        return NULL;
    }
    if (self->mime->data_cb_owners == NULL) {
        PyErr_SetString(ErrorObject, "data_cb() cannot attach to a closed mime object");
        return NULL;
    }

    owner = curlmime_data_cb_owner_new(read_cb, seek_cb, free_cb, userdata);
    if (owner == NULL) {
        return NULL;
    }
    if (seek_cb != Py_None) {
        seekfunc = curlmimepart_seek_callback;
    }

    owners = self->mime->data_cb_owners;
    if (PyList_Append(owners, (PyObject *)owner) != 0) {
        Py_DECREF(owner);
        return NULL;
    }

    /* Keep one reference per libcurl owner that can invoke freefunc. */
    curlmime_data_cb_owner_add_libcurl_ref(owner);

    res = (int)curl_mime_data_cb(self->part, datasize, readfunc, seekfunc,
        curlmimepart_free_callback, owner);
    if (res != CURLE_OK) {
        if (curlmime_owner_list_remove_ptr(owners, (PyObject *)owner) != 0) {
            PyErr_Clear();
        }
        curlmime_data_cb_owner_release_libcurl_ref(owner, 0);
        Py_DECREF(owner);
        curlmime_set_error(self->mime != NULL ? self->mime->curl : NULL, res);
        return NULL;
    }

    old_owner_obj = self->data_cb_owner;
    if (old_owner_obj != NULL) {
        if (curlmime_owner_list_remove_ptr(owners, old_owner_obj) != 0) {
            PyErr_Clear();
        }
    }
    Py_INCREF(owner);
    self->data_cb_owner = (PyObject *)owner;
    Py_XDECREF(old_owner_obj);
    Py_DECREF(owner);

    Py_RETURN_NONE;
}

static PyObject *
do_curlmimepart_filedata(CurlMimePartObject *self, PyObject *arg)
{
    PyObject *encoded_obj = NULL;
    char *path;
    int res;

    if (curlmimepart_check_state(self, "filedata") != 0) {
        return NULL;
    }

    path = PyText_AsString_NoNUL(arg, &encoded_obj);
    if (path == NULL) {
        return NULL;
    }

    res = (int)curl_mime_filedata(self->part, path);
    PyText_EncodedDecref(encoded_obj);
    if (res != CURLE_OK) {
        curlmime_set_error(self->mime != NULL ? self->mime->curl : NULL, res);
        return NULL;
    }
    if (curlmimepart_drop_data_cb_owner(self) != 0) {
        return NULL;
    }

    Py_RETURN_NONE;
}

static PyObject *
do_curlmimepart_filename(CurlMimePartObject *self, PyObject *arg)
{
    PyObject *encoded_obj = NULL;
    char *name;
    int res;

    if (curlmimepart_check_state(self, "filename") != 0) {
        return NULL;
    }

    name = PyText_AsString_NoNUL(arg, &encoded_obj);
    if (name == NULL) {
        return NULL;
    }

    res = (int)curl_mime_filename(self->part, name);
    PyText_EncodedDecref(encoded_obj);
    if (res != CURLE_OK) {
        curlmime_set_error(self->mime != NULL ? self->mime->curl : NULL, res);
        return NULL;
    }

    Py_RETURN_NONE;
}

static PyObject *
do_curlmimepart_type(CurlMimePartObject *self, PyObject *arg)
{
    PyObject *encoded_obj = NULL;
    char *type;
    int res;

    if (curlmimepart_check_state(self, "type") != 0) {
        return NULL;
    }

    type = PyText_AsString_NoNUL(arg, &encoded_obj);
    if (type == NULL) {
        return NULL;
    }

    res = (int)curl_mime_type(self->part, type);
    PyText_EncodedDecref(encoded_obj);
    if (res != CURLE_OK) {
        curlmime_set_error(self->mime != NULL ? self->mime->curl : NULL, res);
        return NULL;
    }

    Py_RETURN_NONE;
}

static PyObject *
do_curlmimepart_encoder(CurlMimePartObject *self, PyObject *arg)
{
    PyObject *encoded_obj = NULL;
    char *encoding;
    int res;

    if (curlmimepart_check_state(self, "encoder") != 0) {
        return NULL;
    }

    encoding = PyText_AsString_NoNUL(arg, &encoded_obj);
    if (encoding == NULL) {
        return NULL;
    }

    res = (int)curl_mime_encoder(self->part, encoding);
    PyText_EncodedDecref(encoded_obj);
    if (res != CURLE_OK) {
        curlmime_set_error(self->mime != NULL ? self->mime->curl : NULL, res);
        return NULL;
    }

    Py_RETURN_NONE;
}

static PyObject *
do_curlmimepart_headers(CurlMimePartObject *self, PyObject *arg)
{
    struct curl_slist *slist;
    int res;

    if (curlmimepart_check_state(self, "headers") != 0) {
        return NULL;
    }

    slist = curlmime_headers_to_slist(arg);
    if (slist == NULL && arg != Py_None && PyErr_Occurred()) {
        return NULL;
    }

    res = (int)curl_mime_headers(self->part, slist, 1);
    if (res != CURLE_OK) {
        if (slist != NULL) {
            curl_slist_free_all(slist);
        }
        curlmime_set_error(self->mime != NULL ? self->mime->curl : NULL, res);
        return NULL;
    }

    Py_RETURN_NONE;
}

static PyObject *
do_curlmimepart_subparts(CurlMimePartObject *self, PyObject *arg)
{
    CurlMimeObject *submime;
    Py_ssize_t item_index;
    int res;

    if (!PyObject_TypeCheck(arg, p_CurlMime_Type)) {
        PyErr_SetString(PyExc_TypeError, "subparts() expects a CurlMime object");
        return NULL;
    }

    submime = (CurlMimeObject *)arg;

    if (curlmimepart_check_state(self, "subparts") != 0) {
        return NULL;
    }
    if (submime->mime == NULL) {
        PyErr_SetString(PyExc_ValueError, "subparts() received a closed mime object");
        return NULL;
    }
    if (submime->curl != self->mime->curl) {
        PyErr_SetString(PyExc_ValueError, "subparts() requires both mime objects to use the same Curl handle");
        return NULL;
    }
    if (submime == self->mime) {
        PyErr_SetString(PyExc_ValueError, "subparts() does not accept the parent mime object");
        return NULL;
    }
    if (!submime->owns_mime) {
        PyErr_SetString(PyExc_ValueError, "subparts() received a mime object already attached as subparts");
        return NULL;
    }
    if (submime->curl != NULL && submime->curl->mimepost_obj == (PyObject *)submime) {
        PyErr_SetString(PyExc_ValueError, "subparts() received a mime object currently set as MIMEPOST");
        return NULL;
    }
    if (self->mime->submimes == NULL) {
        PyErr_SetString(ErrorObject, "subparts() cannot attach to a closed mime object");
        return NULL;
    }
    if (PyList_Append(self->mime->submimes, (PyObject *)submime) != 0) {
        return NULL;
    }

    res = (int)curl_mime_subparts(self->part, submime->mime);
    if (res != CURLE_OK) {
        item_index = PyList_GET_SIZE(self->mime->submimes) - 1;
        if (item_index >= 0) {
            (void)PySequence_DelItem(self->mime->submimes, item_index);
            PyErr_Clear();
        }
        curlmime_set_error(self->mime != NULL ? self->mime->curl : NULL, res);
        return NULL;
    }
    submime->owns_mime = 0;
    if (curlmimepart_drop_data_cb_owner(self) != 0) {
        return NULL;
    }

    Py_RETURN_NONE;
}

static PyMethodDef curlmimepartobject_methods[] = {
    {"name", (PyCFunction)do_curlmimepart_name, METH_O, "Set the name of this MIME part."},
    {"data", (PyCFunction)do_curlmimepart_data, METH_O, "Set in-memory data for this MIME part."},
    {"data_cb", (PyCFunction)do_curlmimepart_data_cb, METH_VARARGS | METH_KEYWORDS, "Set callback-based data for this MIME part."},
    {"filedata", (PyCFunction)do_curlmimepart_filedata, METH_O, "Set on-disk file data for this MIME part."},
    {"filename", (PyCFunction)do_curlmimepart_filename, METH_O, "Set the remote filename for this MIME part."},
    {"type", (PyCFunction)do_curlmimepart_type, METH_O, "Set content type for this MIME part."},
    {"encoder", (PyCFunction)do_curlmimepart_encoder, METH_O, "Set content transfer encoding for this MIME part."},
    {"headers", (PyCFunction)do_curlmimepart_headers, METH_O, "Set custom headers for this MIME part."},
    {"subparts", (PyCFunction)do_curlmimepart_subparts, METH_O, "Attach a child CurlMime object as multipart data."},
    {NULL, NULL, 0, NULL}
};

PYCURL_INTERNAL PyTypeObject CurlMimePart_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "pycurl.CurlMimePart",         /* tp_name */
    sizeof(CurlMimePartObject), /* tp_basicsize */
    0,                          /* tp_itemsize */
    (destructor)do_curlmimepart_dealloc, /* tp_dealloc */
    0,                          /* tp_print / tp_vectorcall_offset */
    0,                          /* tp_getattr */
    0,                          /* tp_setattr */
    0,                          /* tp_reserved / tp_as_async */
    0,                          /* tp_repr */
    0,                          /* tp_as_number */
    0,                          /* tp_as_sequence */
    0,                          /* tp_as_mapping */
    0,                          /* tp_hash */
    0,                          /* tp_call */
    0,                          /* tp_str */
    0,                          /* tp_getattro */
    0,                          /* tp_setattro */
    0,                          /* tp_as_buffer */
    PYCURL_TYPE_FLAGS,          /* tp_flags */
    "A MIME part belonging to a CurlMime object.", /* tp_doc */
    (traverseproc)do_curlmimepart_traverse, /* tp_traverse */
    (inquiry)do_curlmimepart_clear, /* tp_clear */
    0,                          /* tp_richcompare */
    0,                          /* tp_weaklistoffset */
    0,                          /* tp_iter */
    0,                          /* tp_iternext */
    curlmimepartobject_methods, /* tp_methods */
    0,                          /* tp_members */
    0,                          /* tp_getset */
    0,                          /* tp_base */
    0,                          /* tp_dict */
    0,                          /* tp_descr_get */
    0,                          /* tp_descr_set */
    0,                          /* tp_dictoffset */
    0,                          /* tp_init */
    PyType_GenericAlloc,        /* tp_alloc */
    0,                          /* tp_new */
    PyObject_GC_Del,            /* tp_free */
};

#endif /* HAVE_CURL_MIME */
