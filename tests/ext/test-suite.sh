# 

dir=$(dirname "$0")

. "$dir"/test-lib.sh

setup

desc 'setup.py without arguments'
fails 'python setup.py'
succeeds 'python setup.py 2>&1 |grep "usage: setup.py"'

desc 'setup.py --help'
succeeds 'python setup.py --help'
# .* = Unix|Windows
succeeds 'python setup.py --help |grep "PycURL .* options:"'
# distutils help
succeeds 'python setup.py --help |grep "Common commands:"'

desc 'setup.py --help with bogus --curl-config'
succeeds 'python setup.py --help --curl-config=/dev/null'
succeeds 'python setup.py --help --curl-config=/dev/null |grep "PycURL .* options:"'
# this checks that --curl-config is consumed prior to
# distutils processing --help
fails 'python setup.py --help --curl-config=/dev/null 2>&1 |grep "option .* not recognized"'
