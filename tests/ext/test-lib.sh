# shell test framework based on test framework in rpg:
# https://github.com/rtomayko/rpg
#
# Copyright (c) 2010 Ryan Tomayko <http://tomayko.com/about>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER 
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

: ${VERBOSE:=false}

unset CDPATH

#cd "$(dirname $0)"
if test -z "$TESTDIR"; then
  TESTDIR=$(realpath $(pwd))
fi

test_count=0
successes=0
failures=0

output="$TESTDIR/$(basename "$0" .sh).out"
trap "rm -f $output" 0

succeeds () {
  test_count=$(( test_count + 1 ))
  echo "\$ ${2:-$1}" > "$output"
  eval "( ${2:-$1} )" 1>>"$output" 2>&1
  ec=$?
  if test $ec -eq 0
  then successes=$(( successes + 1 ))
     printf 'ok %d - %s\n' $test_count "$1"
  else failures=$(( failures + 1 ))
     printf 'not ok %d - %s [%d]\n' $test_count "$1" "$ec"
  fi

  $VERBOSE && dcat $output
  return 0
}

fails () {
  if test $# -eq 1
  then succeeds "! $1"
  else succeeds "$1" "! $2"
  fi
}

diag () { echo "$@" | sed 's/^/# /'; }
dcat () { cat "$@"  | sed 's/^/# /'; }
desc () { diag "$@"; }

setup () {
  rm -rf "$TESTDIR/trash"
  return 0
}
