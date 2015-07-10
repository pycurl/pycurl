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

if test -n "$USEPY"; then
  # need to launch tests.appmanager with a more modern python.
  # doing this for 2.4 and 2.5 now.
  pip install -r requirements-dev.txt
  
  # https://launchpad.net/~fkrull/+archive/deadsnakes
  # http://askubuntu.com/questions/304178/how-do-i-add-a-ppa-in-a-shell-script-without-user-input
  sudo add-apt-repository -y ppa:fkrull/deadsnakes
  sudo apt-get update
  sudo apt-get install python$USEPY-dev
  mkdir archives && (
    cd archives &&
    wget_once https://pypi.python.org/packages/source/v/virtualenv/virtualenv-1.7.1.2.tar.gz &&
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
  pip install -r requirements-dev-$USEPY.txt
else
  pip install -r requirements-dev.txt
fi

if test "$USEPY" = 2.4; then
  # patch nose
  sed -i -e s/BaseException/Exception/ ~/virtualenv/python2.4/lib/python2.4/site-packages/nose/failure.py
fi

if test -n "$USECURL"; then
  curl_version=`echo "$USECURL" |awk -F- '{print $1}'`
  wget_once "http://curl.haxx.se/download/curl-$curl_version.tar.gz" ||
    wget_once "http://curl.haxx.se/download/archeology/curl-$curl_version.tar.gz"
  if test -n "$USESSL"; then
    sudo apt-get update
    case "$USESSL" in
    openssl)
      sudo apt-get install libssl-dev
      configure_flags="--with-ssl --without-gnutls --without-nss"
      ;;
    libressl)
      wget_once http://ftp.openbsd.org/pub/OpenBSD/LibreSSL/libressl-$USELIBRESSL.tar.gz
      tar xfz libressl-$USELIBRESSL.tar.gz
      (cd libressl-$USELIBRESSL &&
        ./configure --prefix=/opt/libressl-$USELIBRESSL &&
        make &&
        sudo make install)
      configure_flags="--with-ssl=/opt/libressl-$USELIBRESSL --without-gnutls --without-nss"
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
  curl_flavor=`echo "$USECURL" |awk -F- '{print $2}'`
  if test "$curl_flavor" = gssapi; then
    sudo apt-get install libkrb5-dev
    configure_flags="$configure_flags --with-gssapi"
  fi
  tar zxf "curl-$curl_version.tar.gz"
  (cd "curl-$curl_version" &&
    if test "$curl_version" = 7.19.0; then
      patch -p1 <"$TRAVIS_BUILD_DIR"/tests/matrix/curl-7.19.0-sslv2-c66b0b32fba-modified.patch
    fi &&
    ./configure --prefix="$HOME"/i/curl-"$USECURL" $configure_flags &&
    if test "$curl_flavor" = gssapi; then
      if ! egrep -q 'GSS-?API support:.*enabled' config.log; then
        echo 'GSSAPI support not enabled despite being requested' 1>&2
	exit 11
      fi
    fi &&
    make &&
    make install
  )
  "$HOME"/i/curl-"$USECURL"/bin/curl -V
else
  curl -V
fi

sudo apt-get install vsftpd realpath

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
