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
  set +e
  (cd "$tmpdir" && python "$file" >output)
  rv=$?
  set -e
  if test "$rv" != 0; then
    echo "$file failed, standard error contents (if any) is above"
    if test -n "`cat output`"; then
      echo "Standard output contents:"
      cat "$tmpdir"/output
    fi
    exit $rv
  fi
done

echo 'All ok'
