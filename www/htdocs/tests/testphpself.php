<?php // vi:ts=4:et
header("Content-type: text/plain");

echo "request: $PHP_SELF";
if ($QUERY_STRING)
    echo "?$QUERY_STRING";
echo "\n";
?>
