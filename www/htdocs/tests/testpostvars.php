<?php
set_magic_quotes_runtime(0);

// send the result back as text/plain, so that we don't have to care
// about html entities and such
header("Content-type: text/plain");

echo "[info: this is Content-type: text/plain, so you should get\n";
echo "       back exactly what I have received]\n\n";
echo "POST vars from HTTP request:\n\n";

if (is_array($HTTP_POST_VARS))
{
	while (list($k, $v) = each($HTTP_POST_VARS))
	{
		printf("  '%s': '%s'\n", $k, $v);
	}
}

echo "\n[end of file]\n";

?>
