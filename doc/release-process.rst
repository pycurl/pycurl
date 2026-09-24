:orphan:

Release Process
===============

Release tag schema
------------------

Release tags should use the ``vX.Y.Z`` schema, for example ``v7.46.1``.
The leading ``v`` is required for new release tags.

Older releases used ``REL_X_Y_Z``-style tags (for example ``REL_7_45_7``).
These historical tags are kept unchanged and continue to be referenced
from the changelog. New releases no longer get a ``REL_X_Y_Z`` tag.

Release workflow
----------------

Releases are made by the Release workflow
(``.github/workflows/cibuildwheel.yml``), run manually from the Actions tab
with one of these modes:

``build-only``
    Build the sdist and wheels, nothing else.

``testpypi``
    Build, then publish to TestPyPI.

``release``
    Check that the version in ``setup.py``, ``doc/conf.py``, ``ChangeLog``
    and ``RELEASE-NOTES.rst`` agree and that the release does not exist yet,
    then create a draft GitHub Release whose notes are the summary from
    ``RELEASE-NOTES.rst`` followed by the ``ChangeLog`` entries. The sdist,
    wheels and documentation are built in parallel, and the documentation
    tarball is attached to the draft.

    The run then waits for approval of the ``pypi`` environment. Review the
    draft release and the build artifacts, then approve the deployment:
    the wheels and sdist are published to PyPI and the GitHub Release is
    published, which creates the ``vX.Y.Z`` tag at the commit that was built.
    If the run is rejected instead, delete the draft release by hand.

The release notes can be previewed locally with ``scripts/release-notes``.

Release checklist
-----------------

1. Ensure changelog is up to date with commits in master.
2. Run ``scripts/update-authors`` and review the updated AUTHORS file.
3. Run ``git shortlog v<previous release>...`` and add new contributors
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
10. Run the Release workflow on the release branch in ``build-only`` or
    ``testpypi`` mode and fix any issues.
11. Run the Release workflow on the release branch in ``release`` mode,
    review the draft release, and approve the deployment.
12. Merge release branch.
13. Upload documentation to web site.
14. Update web site home page.
