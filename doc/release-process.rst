:orphan:

Release Process
===============

Release tag schema
------------------

Release tags should use the ``vX.Y.Z`` schema, for example ``v7.46.1``.
The leading ``v`` is required for new release tags.

Older releases used ``REL_X_Y_Z``-style tags (for example ``REL_7_45_7``).
These historical tags are kept unchanged and continue to be referenced
from the changelog and from ``git shortlog`` invocations such as the one
in step 3 below.

Pushing a ``vX.Y.Z`` tag triggers the Draft GitHub Release workflow
(``.github/workflows/draft-release.yml``), which creates an empty draft
GitHub Release. Maintainers write the release notes into the draft before
publishing it.

The existing manual Build Wheels workflow
(``.github/workflows/cibuildwheel.yml``) remains the publishing path for
PyPI and TestPyPI. This first step does not make PyPI publishing
tag-driven.

Release checklist
-----------------

1. Ensure changelog is up to date with commits in master.
2. Run ``scripts/update-authors`` and review the updated AUTHORS file.
3. Run ``git shortlog REL_<previous release>...`` and add new contributors
   missed by the authors script to AUTHORS.
4. Run ``check-manifest`` (from PyPI) and check that none of the listed
   files should be in MANIFEST.in.
5. Make sure GitHub Actions is green for master.
6. Create a release branch from master.
7. Update version numbers in:
   - Changelog (also record release date)
   - doc/conf.py
   - setup.py
8. Draft release notes, add to RELEASE-NOTES.rst.
9. Push release branch to GitHub.
10. Test wheel build using GitHub Actions and fix any issues.
11. Tag the new version and push to GitHub.
12. Trigger official wheel build/PyPI push using GitHub Actions.
13. Merge release branch.
14. Generate and upload documentation to web site.
15. Update web site home page.
