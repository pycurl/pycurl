#!/bin/sh

set -e
set -x

wget_once() {
  url="$1"
  if ! test -f `basename "$url"`; then
    wget -O `basename "$url"`.part "$url"
    rv=$?
    if test $rv = 0; then
      mv `basename "$url"`.part `basename "$url"`
    else
      rm -f `basename "$url"`.part
      return $rv
    fi
  fi
}

(cd &&
  mkdir -p opt &&
  cd opt &&
  wget http://pycurl.sourceforge.net/travis-deps/bin-precise-64.tar.xz &&
  tar xfJ bin-precise-64.tar.xz)

export PATH=~/opt/bin:$PATH

if test -n "$USEPY"; then
  # need to launch tests.appmanager with a more modern python.
  # doing this for 2.4 and 2.5 now.
  pip install -r requirements-dev.txt
  
  (cd && mkdir -p opt && cd opt &&
    wget http://pycurl.sourceforge.net/travis-deps/python-"$USEPY"-precise-64.tar.xz &&
    tar xfJ python-"$USEPY"-precise-64.tar.xz)
  export PATH=$HOME/opt/python-$USEPY/bin:$PATH
  
  mkdir archives && (
    cd archives &&
    wget_once https://pypi.python.org/packages/source/v/virtualenv/virtualenv-1.7.1.2.tar.gz &&
    tar zxf virtualenv-1.7.1.2.tar.gz &&
    cd virtualenv-1.7.1.2 &&
    ~/opt/python-$USEPY/bin/python$USEPY setup.py install
  )
  
  virtualenv --version
  which virtualenv
  # travis places its virtualenv in /usr/local/bin.
  # virtualenv 1.7 installed above for python 2.x goes in /usr/bin.
  # /usr/local/bin is earlier in path and takes precedence.
  # manually invoke the 1.7 version here.
  # however, when installed for 2.x our virtualenv 1.7 goes in /usr/local/bin.
  if test "$USEPY" = 3.1; then
    virtualenv=$HOME/opt/python-$USEPY/bin/virtualenv
  else
    virtualenv=/usr/bin/virtualenv
  fi
  $virtualenv --version
  $virtualenv ~/virtualenv/python$USEPY -p python$USEPY
  . ~/virtualenv/python$USEPY/bin/activate
  python -V
  which pip
  pip --version
fi

if test -e requirements-dev-$USEPY.txt; then
  pip install -r requirements-dev-$USEPY.txt
else
  pip install -r requirements-dev.txt
fi

if test "$USEPY" = 2.4; then
  # patch nose
  sed -i -e s/BaseException/Exception/ ~/virtualenv/python2.4/lib/python2.4/site-packages/nose/failure.py
fi

if test "$USEPY" = 3.1; then
  # install flaky since pip/tarfile barfs on it
  wget_once https://pypi.python.org/packages/source/f/flaky/flaky-2.2.0.tar.gz
  tar xfz flaky-2.2.0.tar.gz
  cd flaky-2.2.0
  python setup.py install
  cd ..
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
  
  if test -n "$USEOPENSSL"; then
    (cd && mkdir -p opt && cd opt &&
      wget http://pycurl.sourceforge.net/travis-deps/openssl-"$USEOPENSSL"-precise-64.tar.xz &&
      tar xfJ openssl-"$USEOPENSSL"-precise-64.tar.xz)
  fi
  if test -n "$USELIBRESSL"; then
    (cd && mkdir -p opt && cd opt &&
      wget http://pycurl.sourceforge.net/travis-deps/libressl-"$USELIBRESSL"-precise-64.tar.xz &&
      tar xfJ libressl-"$USELIBRESSL"-precise-64.tar.xz)
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
  export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$HOME/opt/$curldirname/lib
  name=$curldirname-precise-64.tar.xz
  (cd &&
    mkdir -p opt &&
    cd opt &&
    wget http://pycurl.sourceforge.net/travis-deps/"$name" &&
    tar xfJ "$name")
  curl_flavor=`echo "$USECURL" |awk -F- '{print $2}'`
  "$HOME"/opt/$curldirname/bin/curl -V
else
  curl -V
fi

# for building documentation.
# this must be done after python is installed so that we install sphinx
# into the correct python version.
# sphinx requires python 2.6+ or 3.3+
case "$USEPY" in
  2.[45])
    ;;
  3.[12])
    ;;
  *)
    pip install sphinx
    ;;
esac
