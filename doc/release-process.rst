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
7. Rsync doc directory to www/htdocs.
8. python setup.py sdist
9. Manually test install the built package.
10. TODO: build windows packages.
11. Tag the new version.
12. Copy built source distribution to downloads repo on github.
13. Rsync downloads repo to sourceforge.
14. Rsync www/htdocs to sourceforge.
15. Announce release on mailing list.
