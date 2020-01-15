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

file_host=https://github.com/pycurl/deps/raw/master
distro=bionic
ldlp=$LD_LIBRARY_PATH

ldlp_exec() {
  env LD_LIBRARY_PATH=$ldlp "$@"
}

(cd &&
  mkdir -p opt &&
  cd opt &&
  wget $file_host/travis-$distro/bin-$distro-64.tar.xz &&
  tar xfJ bin-$distro-64.tar.xz)

export PATH=~/opt/bin:$PATH

pip install -r requirements-dev.txt

if test -n "$USECURL"; then
  if test -n "$USEOPENSSL"; then
    (cd && mkdir -p opt && cd opt &&
      wget $file_host/travis-$distro/openssl-"$USEOPENSSL"-$distro-64.tar.xz &&
      tar xfJ openssl-"$USEOPENSSL"-$distro-64.tar.xz)
    ldlp=$ldlp:$HOME/opt/openssl-$USEOPENSSL/lib
  fi
  if test -n "$USELIBRESSL"; then
    (cd && mkdir -p opt && cd opt &&
      wget $file_host/travis-$distro/libressl-"$USELIBRESSL"-$distro-64.tar.xz &&
      tar xfJ libressl-"$USELIBRESSL"-$distro-64.tar.xz)
    ldlp=$ldlp:$HOME/opt/libressl-$USELIBRESSL/lib
  fi

  curldirname=curl-"$USECURL"
  ldlp=$ldlp:$HOME/opt/$curldirname/lib
  name=$curldirname-$distro-64.tar.xz
  (cd &&
    mkdir -p opt &&
    cd opt &&
    wget $file_host/travis-$distro/"$name" &&
    tar xfJ "$name")
  ldlp_exec "$HOME"/opt/$curldirname/bin/curl -V
else
  curl -V
fi
