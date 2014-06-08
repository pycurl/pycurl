<?php // vi:ts=4:et
set_magic_quotes_runtime(0);

// send the result back as text/plain, so that we don't have to care
// about html entities and such
header("Content-type: text/plain");

if (is_array($_GET))
{
    while (list($k, $v) = each($_))
    {
        printf("  '%s': '%s'\n", $k, $v);
    }
}
