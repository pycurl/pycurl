# On recent windowses there is no localhost entry in hosts file,
# hence localhost resolves fail. https://github.com/c-ares/c-ares/issues/85
# FTP tests also seem to want the numeric IP address rather than localhost.
localhost = '127.0.0.1'

def setup_package():
    # import here, not globally, so that running
    # python -m tests.appmanager
    # to launch the app manager is possible without having pycurl installed
    # (as the test app does not depend on pycurl)
    import pycurl
    
    print('Testing %s' % pycurl.version)
