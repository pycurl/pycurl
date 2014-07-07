<?php // vi:ts=4:et
echo "<?xml version=\"1.0\" encoding=\"iso-8859-1\"?>\n";
$version = "7.19.5";
$version_date = "Jul 12 2014"
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
  <?php echo $version_date; ?> -
  <a href='doc/release-notes.html'>Release Notes</a>
  <br />
</center>

<h2>Quick Links</h2>

<ul>
  <li><a href="/doc/index.html">PycURL documentation</a></li>
  <li><a href="http://curl.haxx.se/libcurl/c/">libcurl documentation</a></li>
  <li><a href="http://cool.haxx.se/mailman/listinfo/curl-and-python">Mailing list</a></li>
  <li><a href="http://curl.haxx.se/mail/list.cgi?list=curl-and-python">Mailing list archives</a></li>
</ul>


<h2>Overview</h2>

<p>
PycURL is a
<a href="http://www.python.org/">Python</a> interface to
<a href="http://curl.haxx.se/libcurl/">libcurl</a>.
PycURL can be used to fetch objects identified by a URL
from a Python program, similar to the
<a href="http://www.python.org/doc/current/lib/module-urllib.html">urllib</a> Python module.
PycURL is mature, very fast, and supports a lot of features.
</p>


<ul>
  <li>
	libcurl is a free and easy-to-use client-side URL transfer library, supporting FTP, FTPS, HTTP, HTTPS, SCP, SFTP, TFTP, TELNET, DICT, LDAP, LDAPS, FILE, IMAP, SMTP, POP3 and RTSP. libcurl supports SSL certificates, HTTP POST, HTTP PUT, FTP uploading, HTTP form based upload, proxies, cookies, user+password authentication (Basic, Digest, NTLM, Negotiate, Kerberos4), file transfer resume, http proxy tunneling and more! 	
    <br />
    <br />
  </li>
  <li>
	libcurl is highly portable, it builds and works identically on numerous platforms, including Solaris, NetBSD, FreeBSD, OpenBSD, Darwin, HPUX, IRIX, AIX, Tru64, Linux, UnixWare, HURD, Windows, Amiga, OS/2, BeOs, Mac OS X, Ultrix, QNX, OpenVMS, RISC OS, Novell NetWare, DOS and more...
    <br />
    <br />
  </li>
  <li>
    libcurl is
    <a href="http://curl.haxx.se/docs/copyright.html">free</a>,
    <a href="http://curl.haxx.se/libcurl/features.html#thread">thread-safe</a>,
    <a href="http://curl.haxx.se/libcurl/features.html#ipv6">IPv6 compatible</a>,
    <a href="http://curl.haxx.se/libcurl/features.html#features">feature rich</a>,
    <a href="http://curl.haxx.se/libcurl/features.html#support">well supported</a>,
    <a href="http://curl.haxx.se/libcurl/features.html#fast">fast</a>,
    <a href="http://curl.haxx.se/libcurl/features.html#docs">thoroughly documented</a>
	and is already used by many known, big and successful <a href="http://curl.haxx.se/docs/companies.html">companies</a>
	and numerous <a href="http://curl.haxx.se/libcurl/using/apps.html">applications</a>.
  </li>
	
</ul>


<h2>Intended Audience</h2>

<p>
PycURL is targeted at an advanced developer - if you need dozens of
concurrent, fast and reliable connections or any of the sophisticated
features listed above then PycURL is for you.
</p>

<p>
The main drawback of PycURL is that it is a relatively thin layer over
libcurl without any of those nice Pythonic class hierarchies.
This means it has a somewhat steep learning curve unless you
are already familiar with libcurl's C API.
</p>

<p>
To sum up, PycURL is very fast (especially for multiple concurrent operations)
and very feature rich, but has a somewhat complex interface.
If you need something simpler or prefer a pure Python
module you might want to check out
<a href="http://www.python.org/doc/current/lib/module-urllib2.html">urllib2</a>
and
<a href="http://urlgrabber.baseurl.org/">urlgrabber</a>.
</p>


<h2>Documentation</h2>

<p>
PycURL includes API documentation in the <i><a href="doc/index.html">doc</a></i> directory of the distribution,
as well as a number of test and example scripts in the <i><a href="https://github.com/pycurl/pycurl/tree/master/tests">tests</a></i>
and <i><a href="https://github.com/pycurl/pycurl/tree/master/examples">examples</a></i>
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
<a href="https://github.com/pycurl/pycurl/blob/master/examples/retriever-multi.py">retriever-multi.py</a>.
</p>

<p>
For a list of changes consult the <a href="ChangeLog">PycURL ChangeLog</a>.
</p>


<h2>Download</h2>

<p>
<a href="download/pycurl-<?php echo $version; ?>.tar.gz">Download</a>
PycURL sources version <?php echo "$version ($version_date)"; ?> or try
the code from
<a href="https://github.com/pycurl/pycurl">the Git repository</a>.
</p>

<p>
You can get prebuilt Win32 modules as well as older versions from the
<a href="download/">download area</a>.
Please note that the prebuilt versions are provided for your
convenience only and are completely <b>unsupported</b> - use them
at your own risk.
</p>

<p>
Also, official PycURL packages are available for <a href="http://ubuntulinux.org">Ubuntu</a>,
<a href="http://debian.org">Debian GNU/Linux</a>, <a href="http://freebsd.org">FreeBSD</a>,
<a href="http://gentoo.org">Gentoo Linux</a>, <a href="http://netbsd.org">NetBSD</a>,
and <a href="http://openbsd.org">OpenBSD</a>.
</p>


<h2>Community</h2>

<p>
If you want to ask questions or discuss PycURL related issues, our
<a href="http://cool.haxx.se/mailman/listinfo/curl-and-python">mailing list</a>
is the place to be.
<a href="http://curl.haxx.se/mail/list.cgi?list=curl-and-python">Mailing list
archives</a> are available for your perusal.
</p>

<p>
<a href="https://github.com/pycurl/pycurl/issues">Bugs</a> and
<a href="https://github.com/pycurl/pycurl/pulls">patches</a> are tracked
on GitHub.
If your patch or proposal is non-trivial, please discuss it on
the mailing list before submitting code.
Older bugs and patches can be found on the
<a href="https://github.com/p/pycurl-archived/issues">issues</a> and
<a href="https://github.com/p/pycurl-archived/pulls">pull requests</a> pages
for the temporary Git import repository on Github, and on the
<a href="http://sourceforge.net/projects/pycurl/">PycURL SourceForge</a>
project page.
</p>

<p>
The libcurl library also has its own
<a href="http://curl.haxx.se/mail/">mailing lists</a>.
</p>


<h2>License</h2>

Copyright (C) 2001-2008 Kjetil Jacobsen<br />
Copyright (C) 2001-2008 Markus F.X.J. Oberhumer<br />
Copyright (C) 2013-2014 Oleg Pudeyev<br />
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
  <?php echo 'Last modified ' . @date('D M d H:i:s T Y', getlastmod()) . '.'; ?>
</i></font>

</body>
</html>
