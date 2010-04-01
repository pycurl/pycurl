<?php // vi:ts=4:et
echo "<?xml version=\"1.0\" encoding=\"iso-8859-1\"?>\n";
$version = "7.19.0";
$version_date = "Sep 9 2008"
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
  <a href="http://curl.haxx.se/libcurl/"><img src="http://curl.haxx.se/ds-libcurl.jpg" width="466" height="181" border="0" alt="libcurl"></img></a>
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
PycURL is mature, very fast, and supports a lot of features.
</p>


<h2>Overview</h2>

<ul>
  <li>
    libcurl is a free and easy-to-use
    client-side URL transfer library, supporting FTP, FTPS, HTTP, HTTPS, GOPHER,
    TELNET, DICT, FILE and LDAP.  libcurl supports HTTPS certificates, HTTP POST,
    HTTP PUT, FTP uploading, kerberos, HTTP form based upload, proxies, cookies,
    user+password authentication, file transfer resume, http proxy tunneling and
    more!
    <br />
    <br />
  </li>
  <li>
    libcurl is highly portable, it builds and works identically on numerous
    platforms, including Solaris, NetBSD, FreeBSD, OpenBSD, Darwin, HPUX, IRIX,
    AIX, Tru64, Linux, Windows, Amiga, OS/2, BeOs, Mac OS X, Ultrix, QNX,
    OpenVMS, RISC OS, Novell NetWare, DOS and more...
    <br />
    <br />
  </li>
  <li>
    libcurl is
    <a href="http://curl.haxx.se/docs/copyright.html">free</a>,
    <a href="http://curl.haxx.se/libcurl/threadsafe.html">thread-safe</a>,
    <a href="http://curl.haxx.se/libcurl/ipv6.html">IPv6 compatible</a>,
    <a href="http://curl.haxx.se/libcurl/features.html">feature rich</a>,
    <a href="http://curl.haxx.se/libcurl/support.html">well supported</a> and
    <a href="http://curl.haxx.se/libcurl/fast.html">fast</a>.
  </li>
</ul>


<h2>Intended Audience</h2>

<p>
PycURL is targeted at the advanced developer - if you need dozens of
concurrent fast and reliable connections or any of the sophisticated
features as listed above then PycURL is for you.
</p>

<p>
The main drawback with PycURL is that it is a relative thin layer over
libcurl without any of those nice Pythonic class hierarchies.
This means it has a somewhat steep learning curve unless you
are already familiar with libcurl's C API.
</p>

<p>
To sum up, PycURL is very fast (esp. for multiple concurrent operations)
and very feature complete, but has a somewhat complex interface.
If you need something simpler or prefer a pure Python
module you might want to check out
<a href="http://www.python.org/doc/current/lib/module-urllib2.html">urllib2</a>
and
<a href="http://linux.duke.edu/projects/urlgrabber/">urlgrabber</a>.
</p>


<h2>Documentation</h2>

<p>
PycURL now includes API documentation in the <i><a href="doc/pycurl.html">doc</a></i> directory of the distribution,
as well as a number of test and example scripts in the <i><a href="http://pycurl.cvs.sourceforge.net/pycurl/pycurl/tests/">tests</a></i>
and <i><a href="http://pycurl.cvs.sourceforge.net/pycurl/pycurl/examples/">examples</a></i>
directories of the distribution.
</p>

<p>
The real info, though, is located in the
<a href="http://curl.haxx.se/libcurl/c/">libcurl documentation</a>,
most important being
<a href="http://curl.haxx.se/libcurl/c/curl_easy_setopt.html">curl_easy_setopt</a>.
The
<a href="http://curl.haxx.se/libcurl/c/libcurl-tutorial.html">libcurl tutorial</a>
also provides a lot of useful information.
</p>

<p>
For a quick start have a look at the high-performance URL downloader
<a href="http://pycurl.cvs.sourceforge.net/pycurl/pycurl/examples/retriever-multi.py?view=markup">retriever-multi.py</a>.
</p>

<p>
For a list of changes consult the <a href="ChangeLog">PycURL ChangeLog</a>.
</p>


<h2>Download</h2>

<p>
<a href="download/pycurl-7.19.0.tar.gz">Download</a>
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

Also, official PycURL packages are available for <a href="http://ubuntulinux.org">Ubuntu</A>,
<a href="http://debian.org">Debian GNU/Linux</a>, <a href="http://freebsd.org">FreeBSD</a>,
<a href="http://gentoo.org">Gentoo Linux</a>, <a href="http://netbsd.org">NetBSD</a>,
and <a href="http://openbsd.org">OpenBSD</a>.


<h2>Community</h2>

<p>
If you want to ask questions or discuss PycURL related issues, our
<a href="http://cool.haxx.se/mailman/listinfo/curl-and-python">mailing list</a>
is the place to be.
</p>

<p>
The
<a href="http://sourceforge.net/projects/pycurl/">PycURL SourceForge</a>
project page provides bug- and patch tracking systems.
</p>

<p>
And the libcurl library also has it's own
<a href="http://curl.haxx.se/mail/">mailing lists</a>.
</p>


<h2>License</h2>

Copyright (C) 2001-2008 Kjetil Jacobsen<br />
Copyright (C) 2001-2008 Markus F.X.J. Oberhumer<br />
<br />
PycURL is dual licensed under the LGPL and an MIT/X derivative license
based on the cURL license. You can redistribute and/or modify PycURL
according to the terms of either license.

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
