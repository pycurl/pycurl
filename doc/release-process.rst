Release Process
===============

1. Ensure changelog is up to date with commits in master.
2. Run `python setup.py manifest`, check that none of the listed files
   should be in MANIFEST.in.
3. Make sure travis is green for master.
4. Update version numbers in:
   - Changelog
   - setup.py
   - www/htdocs/index.php
5. Copy Changelog to www/htdocs.
6. Rsync doc directory to www/htdocs.
7. `python setup.py sdist`.
8. Manually test install the built package.
9. Build windows packages using winbuild.py.
10. Add windows packages to downloads repo on github.
11. Tag the new version.
12. Register new version with pypi - `python setup.py register`.
13. Upload source distribution to pypi - `python setup.py sdist upload`.
    This recreates the source distribution.
14. Add the source distribution to downloads repo on github.
15. Rsync downloads repo to sourceforge.
16. Rsync www/htdocs to sourceforge.
17. Push tag to github pycurl repo.
18. Announce release on mailing list.
19. Link to announcement from website.
