<?php // vi:ts=4:et
$version = "7.10.1";
?>

<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
<html>

<head>
  <meta http-equiv="content-type" content="text/html; charset=ISO-8859-1" />
  <title>PycURL Home Page</title>
  <meta name="author" content="Kjetil Jacobsen" />
  <meta name="description" content="PycURL Homepage" />
</head>

<body bgcolor="#ffffff" link="#0000ee" vlink="#551a8b" alink="#0000ee">

<h1><font face="Courier New, Courier, mono">PYCURL <?php echo $version ?></font></h1>

<p>
&gt;&gt;&gt; import pycurl<br />
&gt;&gt;&gt; print pycurl.__doc__
</p>

<p>
PycURL is a Python module interface to the
<a href="http://curl.haxx.se/">cURL</a> library.
<br />
PycURL can be used to fetch documents identified by a URI
from within a Python program.
</p>

<p>
<a href="download/pycurl-7.10.1.tar.gz">Download</a>
PycURL sources version <?php echo $version ?> (Oct 16 2002)
or try the code from
<a href="http://sourceforge.net/cvs/?group_id=28236">the CVS repository</a>.
</p>

<p>
You can get older versions as well as prebuilt Win32 modules from the
<a href="download/?M=D">download area</a>.
Please note that the prebuilt versions are provided for your convenience
and do not contain extras like
<a href="http://www.openssl.org/">SSL</a> and
<a href="http://www.gzip.org/zlib/">zlib</a> support - you have to grab
all relevant sources and compile them by yourself if you have such special
requirements.
</p>

<p>
Official packages are available for
<a href="http://packages.debian.org/python2.2-pycurl">Debian</a>,
and PycURL is also in the
<a href="http://www.freebsd.org/ports/">ports</a>
collection for FreeBSD and in the
<a href="http://www.netbsd.org/Documentation/software/packages.html">packages</a>
collection for NetBSD.
</p>

<p>
<pre>

LICENSE
-------
Copyright (c) 2001-2002 by Kjetil Jacobsen
Copyright (c) 2001-2002 by Markus F.X.J. Oberhumer

PycURL is free software; you can redistribute it and/or
modify it under the terms of the GNU Lesser General Public
License as published by the Free Software Foundation; either
version 2.1 of the License, or (at your option) any later version.
</pre>
</p>


<hr />
<div align="right">
  <table align="right">
    <tr align="right">
      <td><a href="http://curl.haxx.se/"><img
      src="http://curl.haxx.se/pix/powered_by_curl.gif"
      width="88" height="31" border="0" alt="" /></a>
      </td>

      <td><a href="http://sourceforge.net/"><img
      src="http://sourceforge.net/sflogo.php?group_id=28236&amp;type=1"
      width="88" height="31" border="0" alt="" /></a>
      </td>
    </tr>
  </table>
</div>

<font size="-1"><i>
  <?php echo 'Last modified ' . date('D M d H:i:s T Y', getlastmod()) . '.'; ?>
</i></font>

</body>
</html>
