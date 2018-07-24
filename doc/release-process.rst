Release Process
===============

1. Ensure changelog is up to date with commits in master.
2. Run ``python setup.py authors`` and review the updated AUTHORS file.
3. Run ``git shortlog REL_<previous release>...`` and add new contributors
   missed by the authors script to AUTHORS.
4. Run ``python setup.py manifest``, check that none of the listed files
   should be in MANIFEST.in.
5. Check ``get_data_files()`` in ``setup.py`` to see if any new files should
   be included in binary distributions.
6. Make sure Travis and AppVeyor are green for master.
7. Update version numbers in:
   - Changelog (also record release date)
   - doc/conf.py
   - setup.py
   - winbuild.py
8. Update copyright years if necessary.
9. Draft release notes, add to RELEASE-NOTES.rst.
10. ``make gen docs``.
11. ``python setup.py sdist``.
12. Manually test install the built package.
13. Build windows packages using winbuild.py.
14. Add sdist and windows packages to downloads repo on github.
15. Tag the new version.
16. Upload source distribution to pypi using twine.
17. Upload windows wheels to pypi using twine.
18. Upload windows exe installers to pypi using twine.
19. Upload release files to bintray.
20. Push tag to github pycurl repo.
21. Generate and upload documentation to web site.
22. Update web site home page.
23. Announce release on mailing list.
