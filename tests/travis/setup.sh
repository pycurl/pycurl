#!/bin/sh

set -e
set -x

# for building documentation
pip install sphinx

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
  # virtualenv 1.7 installed above for python 2.x goes in /usr/bin.
  # /usr/local/bin is earlier in path and takes precedence.
  # manually invoke the 1.7 version here.
  # however, when installed for 2.x our virtualenv 1.7 goes in /usr/local/bin.
  if test "$USEPY" = 3.1; then
    virtualenv=/usr/local/bin/virtualenv
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
  if test -n "$USESSL"; then
    sudo apt-get update
    case "$USESSL" in
    openssl)
      sudo apt-get install libssl-dev
      configure_flags="--with-ssl --without-gnutls --without-nss"
      ;;
    gnutls)
      sudo apt-get install libgnutls-dev
      configure_flags="--without-ssl --with-gnutls --without-nss"
      ;;
    nss)
      sudo apt-get install libnss3-dev
      configure_flags="--without-ssl --without-gnutls --with-nss"
      ;;
    none)
      configure_flags="--without-ssl --without-gnutls --without-nss"
      ;;
    *)
      echo "Bogus USESSL=$USESSL" 1>&2
      exit 10
      ;;
    esac
  else
    configure_flags=
  fi
  tar zxf "curl-$USECURL.tar.gz"
  (cd "curl-$USECURL" &&
    if test "$USECURL" = 7.19.0; then
      patch -p1 <"$TRAVIS_BUILD_DIR"/tests/matrix/curl-7.19.0-sslv2-c66b0b32fba-modified.patch
    fi &&
    ./configure --prefix="$HOME"/i/curl-"$USECURL" $configure_flags &&
    make &&
    make install
  )
  "$HOME"/i/curl-"$USECURL"/bin/curl -V
else
  curl -V
fi

sudo apt-get install vsftpd realpath
