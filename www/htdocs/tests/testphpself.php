<?php // vi:ts=4:et
header("Content-type: text/plain");

echo "request: ${_SERVER['PHP_SELF']}";
if ($_SERVER['QUERY_STRING'])
    echo "?${_SERVER['QUERY_STRING']}";
echo "\n";
