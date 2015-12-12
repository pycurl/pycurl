#!/bin/sh

set -e
set -x

export PATH=$HOME/opt/bin:$PATH

# bottle does not support python 2.4, so for that
# we have to run the app using system python (2.7) in a separate process.
# bottle supports python 2.5, but apparently the dead snakes ppa
# does not include ssl in their python, which makes ssl tests fail.
# so, use system python for the test app when testing against 2.5 as well.
if test -n "$USEPY"; then
  ~/virtualenv/python2.7/bin/python2.7 -m tests.appmanager &
  export PYCURL_STANDALONE_APP=yes
fi

export PYCURL_VSFTPD_PATH=$HOME/opt/bin/vsftpd

if test -n "$USEPY"; then
  . ~/virtualenv/python$USEPY/bin/activate
else
  export USEPY=$TRAVIS_PYTHON_VERSION
fi

if test -n "$USECURL"; then
  if echo "$USECURL" |grep -q -- "-libssh2\$"; then
    curl_suffix=-libssh2
    USECURL=$(echo "$USECURL" |sed -e s/-libssh2//)
  else
    curl_suffix=
  fi
  if echo "$USECURL" |grep -q -- "-gssapi\$"; then
    curl_suffix=-gssapi$curl_suffix
    USECURL=$(echo "$USECURL" |sed -e s/-gssapi//)
  fi
  
  if test -n "$USESSL"; then
    if test "$USESSL" != none; then
      curldirname=curl-"$USECURL"-"$USESSL"$curl_suffix
    else
      curldirname=curl-"$USECURL"-none$curl_suffix
    fi
  else
    curldirname=curl-"$USECURL"$curl_suffix
  fi
  export PYCURL_CURL_CONFIG="$HOME"/opt/$curldirname/bin/curl-config
  $PYCURL_CURL_CONFIG --features
  export LD_LIBRARY_PATH="$HOME"/opt/$curldirname/lib
fi

setup_args=
if test -n "$USESSL"; then
  if test "$USESSL" = libressl; then
    export PYCURL_SSL_LIBRARY=openssl
    export LD_LIBRARY_PATH="$LD_LIBRARY_PATH:$HOME/opt/libressl-$USELIBRESSL/lib"
    setup_args="$setup_args --openssl-dir=$HOME/opt/libressl-$USELIBRESSL"
  elif test "$USESSL" != none; then
    export PYCURL_SSL_LIBRARY="$USESSL"
    if test -n "$USEOPENSSL"; then
      export LD_LIBRARY_PATH="$LD_LIBRARY_PATH:$HOME/opt/openssl-$USEOPENSSL/lib"
      setup_args="$setup_args --openssl-dir=$HOME/opt/openssl-$USEOPENSSL"
    fi
    if test -n "$USELIBRESSL"; then
      export LD_LIBRARY_PATH="$LD_LIBRARY_PATH:$HOME/opt/libressl-$USELIBRESSL/lib"
    fi
  fi
elif test -z "$USECURL"; then
  # default for ubuntu 12 which is what travis currently uses is openssl
  export PYCURL_SSL_LIBRARY=openssl
fi

if test -n "$AVOIDSTDIO"; then
  export PYCURL_SETUP_OPTIONS=--avoid-stdio
fi

make gen
python setup.py build $setup_args

(cd tests/fake-curl/libcurl && make)

ldd build/lib*/pycurl*.so

./tests/run.sh
./tests/ext/test-suite.sh

if test -n "$TESTDOCSEXAMPLES"; then
  which pyflakes
  pyflakes python examples tests setup.py winbuild.py
  ./tests/run-quickstart.sh

  # sphinx requires python 2.6+ or 3.3+
  case "$USEPY" in
    2.[45])
      ;;
    3.[12])
      ;;
    *)
      make docs
      ;;
  esac
fi
