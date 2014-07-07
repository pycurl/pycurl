Release Process
===============

1. Ensure changelog is up to date with commits in master.
2. Run ``git shortlog REL_<previous release>...`` and add new contributors
   to AUTHORS.
2. Run ``python setup.py manifest``, check that none of the listed files
   should be in MANIFEST.in.
3. Check ``get_data_files()`` in ``setup.py`` to see if any new files should
   be included in binary distributions.
4. Make sure travis is green for master.
5. Update version numbers in:
   - Changelog (also record release date)
   - doc/conf.py
   - setup.py
   - winbuild.py
   - www/htdocs/index.php (also update release date)
6. Draft release notes, add to RELEASE-NOTES.rst.
7. ``make gen docs``.
8. ``python setup.py sdist``.
9. Manually test install the built package.
10. Build windows packages using winbuild.py.
11. Add windows packages to downloads repo on github.
12. Tag the new version.
13. Register new version with pypi - ``python setup.py register``.
14. Upload source distribution to pypi - ``python setup.py sdist upload``.
    This recreates the source distribution.
15. Add the source distribution to downloads repo on github.
16. Rsync downloads repo to sourceforge.
17. Rsync build/www/htdocs to sourceforge.
18. Push tag to github pycurl repo.
19. Announce release on mailing list.
20. Link to announcement from website.
