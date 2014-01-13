#!/bin/sh

# A curl-config that indicates SSL is supported but does not say
# which SSL library is being used

output=

while test -n "$1"; do
  case "$1" in
  --libs)
    echo '-lcurl'
    ;;
  --features)
    echo 'SSL'
    ;;
  esac
  shift
done
