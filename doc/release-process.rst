Release Process
===============

1. Ensure changelog is up to date with commits in master.
2. Check via tests/matrix.py that test suite passes on the following
   configurations:
  - Python 2.4, 2.5, 2.6, 2.7.
  - Minimum supported libcurl (currently 7.19.0).
  - Most recent available libcurl (currently 7.32.0).
4. Update version numbers in:
  - Changelog
  - setup.py
  - www/htdocs/index.php
5. TODO: update setup_win32_ssl.py.
6. Copy Changelog to www/htdocs.
7. Rsync doc directory to www/htdocs: `rsync doc/*html www/htdocs/doc`
8. python setup.py sdist
9. Manually test install the built package.
10. TODO: build windows packages.
11. Tag the new version.
12. Create new version on pypi: `python setup.py register`
13. Upload source distribution to pypi: `python setup.py sdist upload`
14. Copy built source distribution to downloads repo on github.
15. Rsync downloads repo to sourceforge: `rsync -av * user@web.sourceforge.net:/home/project-web/pycurl/htdocs/download`
16. Rsync www/htdocs to sourceforge: `rsync -av www/htdocs/ user@web.sourceforge.net:/home/project-web/pycurl/htdocs`
17. Announce release on mailing list.
