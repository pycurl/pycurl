#!/bin/sh

# A curl-config that returns -lssl in --static-libs but not in --libs

output=

while test -n "$1"; do
  case "$1" in
  --libs)
    echo '-lcurl'
    ;;
  --static-libs)
    echo '-lssl'
    ;;
  --features)
    echo 'SSL'
    ;;
  esac
  shift
done
