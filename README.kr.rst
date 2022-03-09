PycURL -- cURL 라이브러리에 대한 파이썬 인터페이스
================================================

.. image:: https://api.travis-ci.org/pycurl/pycurl.png
	   :target: https://travis-ci.org/pycurl/pycurl

.. image:: https://ci.appveyor.com/api/projects/status/q40v2q8r5d06bu92/branch/master?svg=true
	   :target: https://ci.appveyor.com/project/p/pycurl/branch/master

PycURL은 멀티 프로토콜 파일 전송 라이브러리인 `libcurl`_, 에 대한 Python 인터페이스 입니다.
urllib_ Python 모듈과 마찬가지로, PycURL 을 사용하여 Python프로그램에서 URL로 식별되는 객체를 가져올 수 있습니다.
그러나 단순한 페치외에도 PycURL은 다음을 포함하여 libural의 기능을 대부분 보여줍니다.:

- 속도 - libcurl은 매우 빠르며 libcurl보다 얇은 래퍼인 PycURL도 매우 빠릅니다.
  PycURL은 요청_ 보다 몇 배 빠르다는`벤치마킹`_ 을 했습니다.
-	여러 프로토콜 지원, SSL, 인증 및 프록시 옵션을 포함한 기능. PycURL은 대부분의 libcurl 콜백을 지원합니다.
- 멀티_ 및 공유_ 인터페이스.
- 네트워크 작업에 사용되는 소켓으로 PycURL을 응용 프로그램의 I / O 루프에 통합 할 수 있습니다 (e.g., Tornado_ 사용).

.. _벤치마킹: http://stackoverflow.com/questions/15461995/python-requests-vs-pycurl-performance
.. _요청: http://python-requests.org/
.. _멀티: https://curl.haxx.se/libcurl/c/libcurl-multi.html
.. _공유: https://curl.haxx.se/libcurl/c/libcurl-share.html
.. _Tornado: http://www.tornadoweb.org/


요구 사항
---------

- Python 3.5-3.10.
- libcurl 7.19.0 이상.


설치
----

`PyPI`_ 에서 소스 및 바이너리 배포판을 다운로드 하십시오.
이제 바이너리 휘을 32 비트 및 64 비트 Windows 버전에서 사용할 수 있습니다.

설치 지침은 `INSTALL.rst`_ 를 참조하십시오. Git checkout에서 설치하는 경우, INSTALL.rst 의 `Git Checkout`_ 섹션의 지침을 따르십시오.

.. _PyPI: https://pypi.python.org/pypi/pycurl
.. _INSTALL.rst: http://pycurl.io/docs/latest/install.html
.. _Git Checkout: http://pycurl.io/docs/latest/install.html#git-checkout


문서
----

최신 PycURL 릴리즈에 대한 설명서는 `PycURL 웹사이트 <http://pycurl.io/docs/latest/>`_ 에서 구할 수 있습니다.

PycURL 개발 버전에 대한 설명서는 `여기 <http://pycurl.io/docs/dev/>`_ 에서 볼 수 있습니다.

소스에서 문서를 작성하려면 ``make docs``문서를 실행하십시오.
작성하려면 `Sphinx <http://sphinx-doc.org/>`_ 를 설치해야하며 문서 문자열로 작성된 pycurl 확장 모듈도 설치해야 합니다.
빌드된 문서는 ``build/doc`` 서브 디렉터리에 저장됩니다.


지원
----

지원 질문은 `curl-and-python 메일링 목록`_을 사용 하십시오.
`메일링 목록 보관소`_ 도 사용자의 사용을 위해 제공됩니다.

공식 지원 장소는 아니지만, `Stack Overflow`_ 는 일부 PycURL 사용자에게 인기가 있습니다.

버그는 `GitHub`_를 통해 보고될 수 있습니다. 버그 보고서와 GitHub는 메일링 목록에 직접 문의하십시오.

.. _curl-and-python 메일링 목록: http://cool.haxx.se/mailman/listinfo/curl-and-python
.. _Stack Overflow: http://stackoverflow.com/questions/tagged/pycurl
.. _메일링 목록 보관소: https://curl.haxx.se/mail/list.cgi?list=curl-and-python
.. _GitHub: https://github.com/pycurl/pycurl/issues


Automated Tests
---------------

PycURL comes with an automated test suite. To run the tests, execute::

    make test

The suite depends on packages `nose`_ and `bottle`_, as well as `vsftpd`_.

Some tests use vsftpd configured to accept anonymous uploads. These tests
are not run by default. As configured, vsftpd will allow reads and writes to
anything the user running the tests has read and write access. To run
vsftpd tests you must explicitly set PYCURL_VSFTPD_PATH variable like so::

    # use vsftpd in PATH
    export PYCURL_VSFTPD_PATH=vsftpd

    # specify full path to vsftpd
    export PYCURL_VSFTPD_PATH=/usr/local/libexec/vsftpd

.. _nose: https://nose.readthedocs.org/
.. _bottle: http://bottlepy.org/
.. _vsftpd: http://vsftpd.beasts.org/


Test Matrix
-----------

The test matrix is a separate framework that runs tests on more esoteric
configurations. It supports:

- Testing against Python 2.4, which bottle does not support.
- Testing against Python compiled without threads, which requires an out of
  process test server.
- Testing against locally compiled libcurl with arbitrary options.

To use the test matrix, first start the test server from Python 2.5+ by
running::

    python -m tests.appmanager

Then in a different shell, and preferably in a separate user account,
run the test matrix::

    # run ftp tests, etc.
    export PYCURL_VSFTPD_PATH=vsftpd
    # create a new work directory, preferably not under pycurl tree
    mkdir testmatrix
    cd testmatrix
    # run the matrix specifying absolute path
    python /path/to/pycurl/tests/matrix.py

The test matrix will download, build and install supported Python versions
and supported libcurl versions, then run pycurl tests against each combination.
To see what the combinations are, look in
`tests/matrix.py <tests/matrix.py>`_.


Contribute
----------

For smaller changes:

#. Fork `the repository`_ on Github.
#. Create a branch off **master**.
#. Make your changes.
#. Write a test which shows that the bug was fixed or that the feature
   works as expected.
#. Send a pull request.
#. Check back after 10-15 minutes to see if tests passed on Travis CI.
   PycURL supports old Python and libcurl releases and their support is tested
   on Travis.

For larger changes:

#. Join the `mailing list`_.
#. Discuss your proposal on the mailing list.
#. When consensus is reached, implement it as described above.

Please contribute binary distributions for your system to the
`downloads repository`_.


License
-------

::

    Copyright (C) 2001-2008 by Kjetil Jacobsen <kjetilja at gmail.com>
    Copyright (C) 2001-2008 by Markus F.X.J. Oberhumer <markus at oberhumer.com>
    Copyright (C) 2013-2022 by Oleg Pudeyev <code at olegp.name>

    All rights reserved.

    PycURL is dual licensed under the LGPL and an MIT/X derivative license
    based on the cURL license.  A full copy of the LGPL license is included
    in the file COPYING-LGPL.  A full copy of the MIT/X derivative license is
    included in the file COPYING-MIT.  You can redistribute and/or modify PycURL
    according to the terms of either license.

.. _PycURL: http://pycurl.io/
.. _libcurl: https://curl.haxx.se/libcurl/
.. _urllib: http://docs.python.org/library/urllib.html
.. _`the repository`: https://github.com/pycurl/pycurl
.. _`mailing list`: http://cool.haxx.se/mailman/listinfo/curl-and-python
.. _`downloads repository`: https://github.com/pycurl/downloads
