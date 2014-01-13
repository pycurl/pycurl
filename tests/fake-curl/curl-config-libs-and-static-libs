#!/bin/sh

# A curl-config that returns different libraries in --libs and --static-libs

output=

while test -n "$1"; do
  case "$1" in
  --libs)
    echo '-lcurl -lflurby'
    ;;
  --static-libs)
    echo '-lkzzert'
    ;;
  esac
  shift
done
