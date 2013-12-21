#!/bin/sh

set -e
set -x

if test -n "$USEPY"; then
  # need to launch tests.appmanager with a more modern python.
  # doing this for 2.4 and 2.5 now.
  pip install -r requirements-dev.txt --use-mirrors
  
  # https://launchpad.net/~fkrull/+archive/deadsnakes
  # http://askubuntu.com/questions/304178/how-do-i-add-a-ppa-in-a-shell-script-without-user-input
  sudo add-apt-repository -y ppa:fkrull/deadsnakes
  sudo apt-get update
  sudo apt-get install python$USEPY-dev
  mkdir archives && (
    cd archives &&
    wget https://pypi.python.org/packages/source/v/virtualenv/virtualenv-1.7.1.2.tar.gz &&
    tar zxf virtualenv-1.7.1.2.tar.gz &&
    cd virtualenv-1.7.1.2 &&
    sudo python$USEPY setup.py install
  )
  virtualenv --version
  which virtualenv
  # travis places its virtualenv in /usr/local/bin.
  # virtualenv 1.7 installed above goes in /usr/bin.
  # /usr/local/bin is earlier in path and takes precedence.
  # manually invoke the 1.7 version here
  /usr/bin/virtualenv ~/virtualenv/python$USEPY -p python$USEPY
  . ~/virtualenv/python$USEPY/bin/activate
  python -V
  which pip
  pip --version
fi

if test -e requirements-dev-$USEPY.txt; then
  pip install -r requirements-dev-$USEPY.txt --use-mirrors
else
  pip install -r requirements-dev.txt --use-mirrors
fi

if test "$USEPY" = 2.4; then
  # patch nose
  sed -i -e s/BaseException/Exception/ ~/virtualenv/python2.4/lib/python2.4/site-packages/nose/failure.py
fi

if test -n "$USECURL"; then
  wget "http://curl.haxx.se/download/curl-$USECURL.tar.gz"
  tar zxf "curl-$USECURL.tar.gz"
  (cd "curl-$USECURL" &&
    if test "$USECURL" = 7.19.0; then
      patch -p1 <"$TRAVIS_BUILD_DIR"/tests/matrix/curl-7.19.0-sslv2-patch-c66b0b32fba-modified.diff
    fi &&
    ./configure --prefix="$HOME"/i/curl-"$USECURL" &&
    make &&
    make install
  )
fi

sudo apt-get install vsftpd
