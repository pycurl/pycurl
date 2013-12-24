Release Process
===============

1. Ensure changelog is up to date with commits in master.
2. Make sure travis is green for master.
3. Update version numbers in:
  - Changelog
  - setup.py
  - www/htdocs/index.php
4. Copy Changelog to www/htdocs.
5. Rsync doc directory to www/htdocs.
6. `python setup.py sdist`.
7. Manually test install the built package.
8. Build windows packages using winbuild.py.
9. Add windows packages to downloads repo on github.
10. Tag the new version.
11. Register new version with pypi - `python setup.py register`.
12. Upload source distribution to pypi - `python setup.py sdist upload`.
  This recreates the source distribution.
13. Add the source distribution to downloads repo on github.
14. Rsync downloads repo to sourceforge.
15. Rsync www/htdocs to sourceforge.
16. Push tag to github pycurl repo.
17. Announce release on mailing list.
18. Link to announcement from website.
