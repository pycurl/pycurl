<?php
set_magic_quotes_runtime(0);

// send the result back as text/plain, so that we don't have to care
// about html entities and such
header("Content-type: text/plain");

if (is_array($HTTP_GET_VARS))
{
	while (list($k, $v) = each($HTTP_GET_VARS))
	{
		printf("  '%s': '%s'\n", $k, $v);
	}
}

?>
