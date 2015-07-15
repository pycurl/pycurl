#!/bin/sh

set -e
set -x

mkdir -p tests/tmp
export PYTHONSUFFIX=$(python -V 2>&1 |awk '{print $2}' |awk -F. '{print $1 "." $2}')
export PYTHONPATH=$(ls -d build/lib.*$PYTHONSUFFIX):$PYTHONPATH

extra_attrs=
if test "$CI" = true; then
  if test -n "$USECURL" && echo "$USECURL" |grep -q gssapi; then
    :
  else
    extra_attrs="$extra_attrs",\!gssapi
  fi
fi

python -c 'import pycurl; print(pycurl.version)'
nosetests -a \!standalone"$extra_attrs" "$@"
nosetests -a standalone "$@"
