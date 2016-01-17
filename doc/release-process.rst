Release Process
===============

1. Ensure changelog is up to date with commits in master.
2. Run ``git shortlog REL_<previous release>...`` and add new contributors
   to AUTHORS.
3. Run ``python setup.py manifest``, check that none of the listed files
   should be in MANIFEST.in.
4. Check ``get_data_files()`` in ``setup.py`` to see if any new files should
   be included in binary distributions.
5. Make sure travis is green for master.
6. Update version numbers in:
   - Changelog (also record release date)
   - doc/conf.py
   - setup.py
   - winbuild.py
   - www/htdocs/index.php (also update release date)
7. Draft release notes, add to RELEASE-NOTES.rst.
8. ``make gen docs``.
9. ``python setup.py sdist``.
10. Manually test install the built package.
11. Build windows packages using winbuild.py.
12. Add sdist and windows packages to downloads repo on github.
13. Tag the new version.
14. Register new version with pypi - ``python setup.py register``.
15. Upload source distribution to pypi using twine.
16. Upload windows wheels to pypi using twine.
17. Upload windows exe installers to pypi using twine.
18. Upload release files to bintray.
19. Push tag to github pycurl repo.
20. Announce release on mailing list.
21. Link to announcement from website.
