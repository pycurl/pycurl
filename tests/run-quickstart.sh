#!/bin/sh

set -e

export PYTHONSUFFIX=$(python -V 2>&1 |awk '{print $2}' |awk -F. '{print $1 "." $2}')
export PYTHONPATH="`pwd`"/$(ls -d build/lib.*$PYTHONSUFFIX):$PYTHONPATH

tmpdir=`mktemp -d`

finish() {
  rm -rf "$tmpdir"
}

trap finish EXIT

for file in "`pwd`"/examples/quickstart/*.py; do \
  # skip Python 2-only examples on Python 3
  if echo "$file" |grep -q python2 &&
    python -V 2>&1 |grep -q 'Python 3'
  then
    continue
  fi
  
  set +e
  (cd "$tmpdir" && python "$file" >output)
  rv=$?
  set -e
  if test "$rv" != 0; then
    echo "$file failed, standard error contents (if any) is above"
    if test -n "`cat "$tmpdir"/output`"; then
      echo "Standard output contents:"
      cat "$tmpdir"/output
    fi
    exit $rv
  fi
done

echo 'All ok'
