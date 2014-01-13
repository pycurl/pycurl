Release Process
===============

1. Ensure changelog is up to date with commits in master.
2. Run ``python setup.py manifest``, check that none of the listed files
   should be in MANIFEST.in.
3. Check ``get_data_files()`` in ``setup.py`` to see if any new files should
   be included in binary distributions.
4. Make sure travis is green for master.
5. Update version numbers in:
   - Changelog
   - setup.py
   - winbuild.py
   - www/htdocs/index.php
6. Copy Changelog to www/htdocs.
7. Draft release notes.
8. ``make docs``.
9. ``python setup.py sdist``.
10. Manually test install the built package.
11. Build windows packages using winbuild.py.
12. Add windows packages to downloads repo on github.
13. Tag the new version.
14. Register new version with pypi - ``python setup.py register``.
15. Upload source distribution to pypi - ``python setup.py sdist upload``.
    This recreates the source distribution.
16. Add the source distribution to downloads repo on github.
17. Rsync downloads repo to sourceforge.
18. Rsync www/htdocs to sourceforge.
19. Push tag to github pycurl repo.
20. Announce release on mailing list.
21. Link to announcement from website.
