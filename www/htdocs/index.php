<?php // vi:ts=4:et
echo "<?xml version=\"1.0\" encoding=\"iso-8859-1\"?>\n";
$version = "7.10.6";
$version_date = "Aug 16 2003";
?>

<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">

<html xmlns="http://www.w3.org/1999/xhtml">

<head>
  <title>PycURL Home Page</title>
  <meta http-equiv="Content-Type" content="text/html; charset=iso-8859-1" />
  <meta name="author" content="Kjetil Jacobsen, Markus F.X.J. Oberhumer" />
  <meta name="description" content="PycURL Homepage" />
  <meta name="keywords" content="pycurl, curl, libcurl, python, wget, file transfer, urllib" />
  <meta name="revisit-after" content="30 days" />
  <meta name="robots" content="archive, index, follow" />
</head>


<body text="#000000" bgcolor="#ffffff" link="#0000ee" vlink="#551a8b" alink="#0000ee">

<center>
  <a href="http://curl.haxx.se/libcurl/"><img src="http://curl.haxx.se/libcurl/big.jpg" width="416" height="115" border="0" alt="libcurl"></img></a>
</center>

<center>
  <br />
  <b><font size="+3" face="Courier New, Courier, mono">PYCURL <?php echo $version; ?></font></b><br />
  <?php echo $version_date; ?><br />
</center>


<p>
&gt;&gt;&gt; import pycurl<br />
&gt;&gt;&gt; print pycurl.__doc__
</p>

<p>
PycURL is a
<a href="http://www.python.org/">Python</a> interface to
<a href="http://curl.haxx.se/libcurl/">libcurl</a>.
PycURL can be used to fetch objects identified by a URL
from a Python program, similar to the
<a href="http://www.python.org/doc/current/lib/module-urllib.html">urllib</a> Python module.
</p>


<h2>Overview</h2>

<ul>
  <li>
    libcurl is a free and easy-to-use client-side URL transfer library,
    supporting FTP, FTPS, HTTP, HTTPS, GOPHER, TELNET, DICT, FILE and LDAP.
    libcurl supports HTTPS certificates, HTTP POST, HTTP PUT, FTP uploading,
    kerberos, HTTP form based upload, proxies, cookies, user+password
    authentication, file transfer resume, http proxy tunneling and more!
    <br />
    <br />
  </li>
  <li>
    libcurl is highly portable, it builds and works identically on numerous
    platforms, including Solaris, Net/Free/Open BSD, Darwin, HPUX, IRIX,
    AIX, Tru64, Linux, Windows, Amiga, OS/2, BeOs, Mac OS X, Ultrix,
    QNX, OpenVMS, RISC OS and more...
    <br />
    <br />
  </li>
  <li>
    libcurl is
    <a href="http://curl.haxx.se/libcurl/threadsafe.html">thread-safe</a>,
    <a href="http://curl.haxx.se/libcurl/ipv6.html">IPv6 compatible</a> and
    <a href="http://curl.haxx.se/libcurl/fast.html">fast</a>.
  </li>
</ul>


<h2>Intended Audience</h2>

<p>
PycURL is targeted at the advanced developer - if you need dozens of
concurrent reliable connections or any of the sophisiticated
features as listed above then PycURL is for you.
</p>

<p>
The main drawback with PycURL is that it is a relative thin layer over
libcurl without any of those nice Pythonic class hierarchies.
This means it has a somewhat steep learning curve unless you
are already familiar with libcurl's C API.
</p>

<p>
For a quick start have a look at the high-performance URL downloader
<a href="http://cvs.sourceforge.net/cgi-bin/viewcvs.cgi/pycurl/pycurl/examples/retriever-multi.py?rev=HEAD&amp;content-type=text/vnd.viewcvs-markup">retriever-multi.py</a>.
</p>


<h2>Documentation</h2>

<p>
PycURL now includes API documentation in the <i><a href="doc/pycurl.html">doc</a></i> directory of the distribution,
as well as a number of test and example scripts in the <i><a href="http://cvs.sourceforge.net/cgi-bin/viewcvs.cgi/pycurl/pycurl/tests/">tests</a></i>
and <i><a href="http://cvs.sourceforge.net/cgi-bin/viewcvs.cgi/pycurl/pycurl/examples/">examples</a></i>
directories of the distribution.
</p>

<p>
The real info, though, is located in the
<a href="http://curl.haxx.se/libcurl/c/">libcurl documentation</a>,
most important being
<a href="http://curl.haxx.se/libcurl/c/curl_easy_setopt.html">curl_easy_setopt</a>.
</p>

<p>
Also have a look at the <a href="ChangeLog">PycURL ChangeLog</a>.
</p>

<h2>Download</h2>

<p>
<a href="download/pycurl-7.10.6.tar.gz">Download</a>
PycURL sources version <?php echo "$version ($version_date)"; ?> or try
the code from
<a href="http://sourceforge.net/cvs/?group_id=28236">the CVS repository</a>.
</p>

<p>
You can get prebuilt Win32 modules as well as older versions from the
<a href="download/">download area</a>.
Please note that the prebuilt versions are provided for your
convenience only and are completely <b>unsupported</b> - use them
at your own risk.
</p>

Also, official PycURL packages are available for
<ul>
  <li><a href="http://packages.debian.org/python2.2-pycurl">Debian GNU/Linux</a></li>
  <li><a href="http://www.freebsd.org/cgi/ports.cgi?query=curl">FreeBSD</a></li>
  <li><a href="http://www.gentoo.org/dyn/pkgs/dev-python/pycurl.xml">Gentoo Linux</a></li>
  <li><a href="ftp://ftp.netbsd.org/pub/NetBSD/packages/pkgsrc/www/py-curl/README.html">NetBSD</a></li>
  <li><a href="http://www.openbsd.org/cgi-bin/cvsweb/ports/net/py-curl/">OpenBSD</a></li>
</ul>


<h2>License</h2>

Copyright (C) 2001-2003 Kjetil Jacobsen<br />
Copyright (C) 2001-2003 Markus F.X.J. Oberhumer<br />
<br />
PycURL is free software; you can redistribute it and/or
modify it under the terms of the GNU Lesser General Public
License as published by the Free Software Foundation; either
version 2.1 of the License, or (at your option) any later version.

<hr />
<div align="right">
  <table align="right">
    <tr align="right">
      <td><a href="http://curl.haxx.se/"><img
      src="http://curl.haxx.se/pix/powered_by_curl.gif"
      width="88" height="31" border="0" alt="" /></a>
      </td>

      <td><a href="http://sourceforge.net/projects/pycurl/"><img
      src="http://sourceforge.net/sflogo.php?group_id=28236&amp;type=1"
      width="88" height="31" border="0" alt="" /></a>
      </td>

      <td><a href="http://validator.w3.org/check/referer"><img
      src="http://www.w3.org/Icons/valid-xhtml10" alt="Valid XHTML 1.0!"
      width="88" height="31" border="0" /></a>
      </td>
    </tr>
  </table>
</div>

<font size="-1"><i>
  <?php echo 'Last modified ' . date('D M d H:i:s T Y', getlastmod()) . '.'; ?>
</i></font>

</body>
</html>
