#!/bin/sh

set -e
set -x

# bottle does not support python 2.4, so for that
# we have to run the app using system python (2.7) in a separate process.
# bottle supports python 2.5, but apparently the dead snakes ppa
# does not include ssl in their python, which makes ssl tests fail.
# so, use system python for the test app when testing against 2.5 as well.
if test -n "$USEPY"; then
  ~/virtualenv/python2.7/bin/python2.7 -m tests.appmanager &
  export PYCURL_STANDALONE_APP=yes
fi

export PYCURL_VSFTPD_PATH=/usr/sbin/vsftpd

if test -n "$USEPY"; then
  . ~/virtualenv/python$USEPY/bin/activate
else
  export USEPY=$TRAVIS_PYTHON_VERSION
fi

if test -n "$USECURL"; then
  export PYCURL_CURL_CONFIG="$HOME"/i/curl-"$USECURL"/bin/curl-config
  export LD_LIBRARY_PATH="$HOME"/i/curl-"$USECURL"/lib
fi

if test -n "$USESSL"; then
  if test "$USESSL" = libressl; then
    export PYCURL_SSL_LIBRARY=openssl
  elif test "$USESSL" != none; then
    export PYCURL_SSL_LIBRARY="$USESSL"
  fi
else
  # default for ubuntu 12 which is what travis currently uses is openssl
  export PYCURL_SSL_LIBRARY=openssl
fi

export VSFTPD_PATH=vsftpd

if test -n "$AVOIDSTDIO"; then
  export PYCURL_SETUP_OPTIONS=--avoid-stdio
fi

make test docs
