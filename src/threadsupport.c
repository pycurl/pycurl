#include "pycurl.h"

PYCURL_INTERNAL PyThreadState *
pycurl_get_thread_state(const CurlObject *self)
{
    /* Get the thread state for callbacks to run in.
     * This is either `self->state' when running inside perform() or
     * `self->multi_stack->state' when running inside multi_perform().
     * When the result is != NULL we also implicitly assert
     * a valid `self->handle'.
     */
    if (self == NULL)
        return NULL;
    assert(PyObject_IsInstance((PyObject *) self, (PyObject *) p_Curl_Type) == 1);
    if (self->state != NULL)
    {
        /* inside perform() */
        assert(self->handle != NULL);
        if (self->multi_stack != NULL) {
            assert(self->multi_stack->state == NULL);
        }
        return self->state;
    }
    if (self->multi_stack != NULL && self->multi_stack->state != NULL)
    {
        /* inside multi_perform() */
        assert(self->handle != NULL);
        assert(self->multi_stack->multi_handle != NULL);
        assert(self->state == NULL);
        return self->multi_stack->state;
    }
    return NULL;
}


PYCURL_INTERNAL PyThreadState *
pycurl_get_thread_state_multi(const CurlMultiObject *self)
{
    /* Get the thread state for callbacks to run in when given
     * multi handles instead of regular handles
     */
    if (self == NULL)
        return NULL;
    assert(PyObject_IsInstance((PyObject *) self, (PyObject *) p_CurlMulti_Type) == 1);
    if (self->state != NULL)
    {
        /* inside multi_perform() */
        assert(self->multi_handle != NULL);
        return self->state;
    }
    return NULL;
}


PYCURL_INTERNAL int
pycurl_acquire_thread(const CurlObject *self, PyThreadState **state)
{
    *state = pycurl_get_thread_state(self);
    if (*state == NULL)
        return 0;
    PyEval_AcquireThread(*state);
    return 1;
}


PYCURL_INTERNAL int
pycurl_acquire_thread_multi(const CurlMultiObject *self, PyThreadState **state)
{
    *state = pycurl_get_thread_state_multi(self);
    if (*state == NULL)
        return 0;
    PyEval_AcquireThread(*state);
    return 1;
}


PYCURL_INTERNAL void
pycurl_release_thread(PyThreadState *state)
{
    PyEval_ReleaseThread(state);
}

/*************************************************************************
// SSL TSL
**************************************************************************/

#ifdef PYCURL_NEED_OPENSSL_TSL

#if OPENSSL_VERSION_NUMBER < 0x10100000
static pycurl_mutex_t *pycurl_openssl_tsl = NULL;

static void
pycurl_ssl_lock(int mode, int n, const char * file, int line)
{
    if (mode & CRYPTO_LOCK) {
        PYCURL_MUTEX_LOCK(&pycurl_openssl_tsl[n]);
    } else {
        PYCURL_MUTEX_UNLOCK(&pycurl_openssl_tsl[n]);
    }
}

#if OPENSSL_VERSION_NUMBER >= 0x10000000
/* use new CRYPTO_THREADID API. */
static void
pycurl_ssl_threadid_callback(CRYPTO_THREADID *id)
{
    CRYPTO_THREADID_set_numeric(id, (unsigned long)PyThread_get_thread_ident());
}
#else
/* deprecated CRYPTO_set_id_callback() API. */
static unsigned long
pycurl_ssl_id(void)
{
    return (unsigned long) PyThread_get_thread_ident();
}
#endif
#endif

PYCURL_INTERNAL int
pycurl_ssl_init(void)
{
#if OPENSSL_VERSION_NUMBER < 0x10100000
    int c = CRYPTO_num_locks();

#if PY_VERSION_HEX >= 0x030D0000
    pycurl_openssl_tsl = PyMem_Calloc(c, sizeof(pycurl_mutex_t));
    if (pycurl_openssl_tsl == NULL) {
        PyErr_NoMemory();
        return -1;
    }
#else
    int i;
    pycurl_openssl_tsl = PyMem_New(pycurl_mutex_t, c);
    if (pycurl_openssl_tsl == NULL) {
        PyErr_NoMemory();
        return -1;
    }
    memset(pycurl_openssl_tsl, 0, sizeof(pycurl_mutex_t) * c);

    for (i = 0; i < c; ++i) {
        pycurl_openssl_tsl[i] = PyThread_allocate_lock();
        if (pycurl_openssl_tsl[i] == NULL) {
            for (--i; i >= 0; --i) {
                PyThread_free_lock(pycurl_openssl_tsl[i]);
            }
            PyMem_Free(pycurl_openssl_tsl);
            pycurl_openssl_tsl = NULL;
            PyErr_NoMemory();
            return -1;
        }
    }
#endif

#if OPENSSL_VERSION_NUMBER >= 0x10000000
    CRYPTO_THREADID_set_callback(pycurl_ssl_threadid_callback);
#else
    CRYPTO_set_id_callback(pycurl_ssl_id);
#endif
    CRYPTO_set_locking_callback(pycurl_ssl_lock);
#endif
    return 0;
}

PYCURL_INTERNAL void
pycurl_ssl_cleanup(void)
{
#if OPENSSL_VERSION_NUMBER < 0x10100000
    if (pycurl_openssl_tsl) {
#if OPENSSL_VERSION_NUMBER >= 0x10000000
        CRYPTO_THREADID_set_callback(NULL);
#else
        CRYPTO_set_id_callback(NULL);
#endif
        CRYPTO_set_locking_callback(NULL);

#if PY_VERSION_HEX < 0x030D0000
        {
            int i, c = CRYPTO_num_locks();
            for (i = 0; i < c; ++i) {
                PyThread_free_lock(pycurl_openssl_tsl[i]);
            }
        }
#endif

        PyMem_Free(pycurl_openssl_tsl);
        pycurl_openssl_tsl = NULL;
    }
#endif
}
#endif

#ifdef PYCURL_NEED_GNUTLS_TSL
static int
pycurl_ssl_mutex_create(void **m)
{
    if ((*((PyThread_type_lock *) m) = PyThread_allocate_lock()) == NULL) {
        return -1;
    } else {
        return 0;
    }
}

static int
pycurl_ssl_mutex_destroy(void **m)
{
    PyThread_free_lock(*((PyThread_type_lock *) m));
    return 0;
}

static int
pycurl_ssl_mutex_lock(void **m)
{
    return !PyThread_acquire_lock(*((PyThread_type_lock *) m), 1);
}

static int
pycurl_ssl_mutex_unlock(void **m)
{
    PyThread_release_lock(*((PyThread_type_lock *) m));
    return 0;
}

static struct gcry_thread_cbs pycurl_gnutls_tsl = {
    GCRY_THREAD_OPTION_USER,
    NULL,
    pycurl_ssl_mutex_create,
    pycurl_ssl_mutex_destroy,
    pycurl_ssl_mutex_lock,
    pycurl_ssl_mutex_unlock
};

PYCURL_INTERNAL int
pycurl_ssl_init(void)
{
    gcry_control(GCRYCTL_SET_THREAD_CBS, &pycurl_gnutls_tsl);
    return 0;
}

PYCURL_INTERNAL void
pycurl_ssl_cleanup(void)
{
    return;
}
#endif

/* mbedTLS */

#ifdef PYCURL_NEED_MBEDTLS_TSL
static int
pycurl_ssl_mutex_create(void **m)
{
    if ((*((PyThread_type_lock *) m) = PyThread_allocate_lock()) == NULL) {
        return -1;
    } else {
        return 0;
    }
}

static int
pycurl_ssl_mutex_destroy(void **m)
{
    PyThread_free_lock(*((PyThread_type_lock *) m));
    return 0;
}

static int
pycurl_ssl_mutex_lock(void **m)
{
    return !PyThread_acquire_lock(*((PyThread_type_lock *) m), 1);
}

PYCURL_INTERNAL int
pycurl_ssl_init(void)
{
    return 0;
}

PYCURL_INTERNAL void
pycurl_ssl_cleanup(void)
{
    return;
}
#endif

/*************************************************************************
// CurlShareObject
**************************************************************************/

PYCURL_INTERNAL void
share_lock_lock(ShareLock *lock, curl_lock_data data)
{
    PYCURL_MUTEX_LOCK(&lock->locks[data]);
}

PYCURL_INTERNAL void
share_lock_unlock(ShareLock *lock, curl_lock_data data)
{
    PYCURL_MUTEX_UNLOCK(&lock->locks[data]);
}

PYCURL_INTERNAL ShareLock *
share_lock_new(void)
{
#if PY_VERSION_HEX >= 0x030D0000
    ShareLock *lock = PyMem_Calloc(1, sizeof(ShareLock));
    if (lock == NULL) {
        PyErr_NoMemory();
        return NULL;
    }
    return lock;
#else
    int i;
    ShareLock *lock = PyMem_New(ShareLock, 1);
    if (lock == NULL) {
        PyErr_NoMemory();
        return NULL;
    }

    for (i = 0; i < CURL_LOCK_DATA_LAST; ++i) {
        lock->locks[i] = PyThread_allocate_lock();
        if (lock->locks[i] == NULL) {
            PyErr_NoMemory();
            goto error;
        }
    }
    return lock;

error:
    for (--i; i >= 0; --i) {
        PyThread_free_lock(lock->locks[i]);
        lock->locks[i] = NULL;
    }
    PyMem_Free(lock);
    return NULL;
#endif
}

PYCURL_INTERNAL void
share_lock_destroy(ShareLock *lock)
{
    assert(lock);
#if PY_VERSION_HEX < 0x030D0000
    int i;
    for (i = 0; i < CURL_LOCK_DATA_LAST; ++i) {
        assert(lock->locks[i] != NULL);
        PyThread_free_lock(lock->locks[i]);
    }
#endif
    PyMem_Free(lock);
}

PYCURL_INTERNAL void
share_lock_callback(CURL *handle, curl_lock_data data, curl_lock_access locktype, void *userptr)
{
    CurlShareObject *share = (CurlShareObject*)userptr;
    share_lock_lock(share->lock, data);
}

PYCURL_INTERNAL void
share_unlock_callback(CURL *handle, curl_lock_data data, void *userptr)
{
    CurlShareObject *share = (CurlShareObject*)userptr;
    share_lock_unlock(share->lock, data);
}


/* vi:ts=4:et:nowrap
 */
