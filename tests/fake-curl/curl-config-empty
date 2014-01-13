#!/bin/sh

# A curl-config that returns empty responses as much as possible

output=

while test -n "$1"; do
  case "$1" in
  --libs)
    # --libs or --static-libs must succeed and produce output
    echo '-lcurl'
    ;;
  esac
  shift
done
