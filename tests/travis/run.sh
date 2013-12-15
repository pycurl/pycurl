#!/bin/sh

set -e
set -x

if test "$USEPY" = 2.4; then
  ~/virtualenv/python2.7/bin/python2.7 -m tests.appmanager &
  export PYCURL_STANDALONE_APP=yes
fi

export PYCURL_VSFTPD_PATH=/usr/sbin/vsftpd

if test -n "$USEPY"; then
  . ~/virtualenv/python$USEPY/bin/activate
else
  export USEPY=$TRAVIS_PYTHON_VERSION
fi

make test
