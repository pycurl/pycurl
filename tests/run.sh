#!/bin/sh

set -e
set -x

test -n "$PYTHON" || PYTHON=python
test -n "$NOSETESTS" || NOSETESTS=nosetests

mkdir -p tests/tmp
export PYTHONSUFFIX=$($PYTHON -V 2>&1 |awk '{print $2}' |awk -F. '{print $1 "." $2}')
export PYTHONPATH=$(ls -d build/lib.*$PYTHONSUFFIX):$PYTHONPATH

extra_attrs=
if test "$CI" = true; then
  if test -n "$USECURL" && echo "$USECURL" |grep -q gssapi; then
    :
  else
    extra_attrs="$extra_attrs",\!gssapi
  fi
fi

$PYTHON -c 'import pycurl; print(pycurl.version)'
$NOSETESTS -a \!standalone"$extra_attrs" --with-flaky "$@"
$NOSETESTS -a standalone --with-flaky "$@"
