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
6. Make sure GitHub Actions is green for master.
7. Create a release branch from master.
8. Update version numbers in:
   - Changelog (also record release date)
   - doc/conf.py
   - setup.py
9. Draft release notes, add to RELEASE-NOTES.rst.
10. Push release branch to GitHub.
11. Test wheel build using GitHub Actions and fix any issues.
12. Tag the new version and push to GitHub.
13. Trigger official wheel build/PyPI push using GitHub Actions.
14. Merge release branch.
15. Generate and upload documentation to web site.
16. Update web site home page.
