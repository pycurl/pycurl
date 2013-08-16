Release Process
===============

1. Ensure changelog is up to date with commits in master.
2. Check that test suite passes on the following configurations:
  - Python 2.5, 2.6, 2.7.
  - Minimum supported libcurl (currently 7.19.0).
  - Most recent available libcurl (currently 7.32.0).
3. Test suite does not work with Python 2.4; check that pycurl builds
   and examples/basicfirst.py works.
4. Update version numbers in:
  - Changelog
  - setup.py
  - www/htdocs/index.php
5. TODO: update setup_win32_ssl.py.
6. Copy Changelog to www/htdocs.
7. Tag the new version.
8. python setup.py sdist
9. TODO: build windows packages.
10. Copy sdist to downloads repo on github.
11. Rsync downloads repo to sourceforge.
12. Rsync www/htdocs to sourceforge.
13. Announce release on mailing list.
