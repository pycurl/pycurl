#!/bin/sh

set -e
set -x

if test "$USEPY" = 2.4; then
  # I use "from . import xxx" in test case modules,
  # and I rather keep that.
  # Patch "from ." out for python 2.4
  for file in tests/*.py; do
    sed -i -e 's/^from . import/import/' "$file"
  done

  sed -Ei -e 's/^( +)from . import/\1import/' tests/appmanager.py
fi
