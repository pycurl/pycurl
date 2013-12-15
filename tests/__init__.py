def setup_package():
    # import here, not globally, so that running
    # python -m tests.appmanager
    # to launch the app manager is possible without having pycurl installed
    # (as the test app does not depend on pycurl)
    import pycurl
    
    print('Testing %s' % pycurl.version)
