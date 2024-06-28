Creating Galaxy Releases
========================

The "main" release process is an interactive checklist with instructions (see `Publication of Galaxy Release v 23.2 <https://github.com/galaxyproject/galaxy/issues/16742>`_ for an example).
This issue is generated via `make release-issue`.
The final result of the release process are

- a new branch (release_YY.N) from which point releases are created
- a tag pointing at the first commit of the branch (vYY.N)

Python packages are not published by this process, but are instead published by creating point releases where the first point release should be `vYY.N.0`.

Creating Galaxy Point Releases
==============================

The process is currently a mix of the `galaxy-release-util create-release` command that is run locally and creating a (pre-)release in the GitHub interface (or using the GitHub API).
The command is shipped with the `galaxy-release-util <https://pypi.org/project/galaxy-release-util/>`_ python package.

`galaxy-release-util create-release` will:

 - update lib/galaxy/version.py
 - create HISTORY.rst entries for all packages
 - build all packages
 - stage and commit all changes
 - create a new tag,
 - (intelligently) merge forward changes to newer release branches and dev
 - push changes to the repo identified by `--upstream` (defaults to https://github.com/galaxyproject/galaxy.git/)

The script has 2 important arguments:

    - `--new-version` is the new version as it will appear for PyPI packages and in lib/galaxy/version.py
    - `--last-commit` indicates the first commit from which changes are to be included in the changelog.

Before starting make sure local branches (all release branches and dev) are up to date and clean, and all release branches have been merged forward,
and that you have configured your remotes so that you can push to the configured upstream (https://github.com/galaxyproject/galaxy by default).
The script should abort gracefully if that is not the case.

Follow these steps:
    0. Enable the push URL of the galaxyproject git remote if you have disabled it (e.g. `git remote set-url --push upstream git@github.com:galaxyproject/galaxy.git`) and disable any pre-commit hooks you might have
    1. Check out the branch from which you want to create a release, e.g. release_23.0: `git checkout release_23.0`
    2. Activate your local virtualenv with Galaxy's dev requirements: `. .venv/bin/activate`
    3. Update Galaxy's dev dependencies (if you haven't done this in a while): `pip install -r lib/galaxy/dependencies/dev-requirements.txt`
    4. You need a personal access token from github (only needs public read permissions).
    5. `GITHUB_AUTH=$YOUR_PAT_FROM_STEP_4 galaxy-release-util create-release --new-version 23.0.1 --last-commit v23.0`
    6. Follow along the prompts and make sure the proposed changes look correct

When the script is finished you should find a new tag in the GitHub interface, as well as updated release and dev branches.
From the `Releases Interface on GitHub <https://github.com/galaxyproject/galaxy/releases>`_ you can create a new pre-release
associated with the newly created tag. The pre-release event will trigger a github workflow that uploads packages to the `test PyPI instance <https://test.pypi.org/>`_.
If this all looks good you can promote the pre-release to a release and that will trigger the upload to the `main PyPI instance <https://pypi.org/>`_.
