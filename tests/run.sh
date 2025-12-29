#!/bin/sh

set -e
set -x

test -n "$PYTHON" || PYTHON=python
test -n "$PYTEST" || PYTEST=pytest

mkdir -p tests/tmp
export PYTHONMAJOR=$($PYTHON -V 2>&1 |awk '{print $2}' |awk -F. '{print $1}')
export PYTHONMINOR=$($PYTHON -V 2>&1 |awk '{print $2}' |awk -F. '{print $2}')
export PYTHONPATH=$(ls -d build/lib.*$PYTHONMAJOR*$PYTHONMINOR):$PYTHONPATH

$PYTHON -c 'import pycurl; print(pycurl.version)'

# If VALGRIND=1, run tests under Valgrind, else run normally
if [ "$VALGRIND" = "1" ]; then
  PYTHONMALLOC=malloc
  valgrind --tool=memcheck \
    --leak-check=full --track-origins=yes --suppressions=tests/valgrind.supp \
    ${VALGRIND_OPTS} $PYTEST -v -ra "$@"
else
  $PYTEST -v -ra "$@"
fi
