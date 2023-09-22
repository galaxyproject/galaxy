#!/bin/sh

set -e

# This script updates the pinned requirements for both linting and typechecking.
# The requirements are split into two parts due to incompatible dependencies:
# flake8 requires importlib-metadata 4.2; typecheck requirements do not
# depende on importlib-metadata; however, they must be installed into the same
# virtual environment as Galaxy's core dependencies, which depend on
# importlib-metadata 4.13.

THIS_DIRECTORY="$(cd "$(dirname "$0")" > /dev/null && pwd)"

update_pinned_reqs() {
    VENV=$(mktemp -d "${TMPDIR:-/tmp}/$1_venv.XXXXXXXXXX")
    python3.7 -m venv "${VENV}"
    . "${VENV}/bin/activate"
    pip install --upgrade pip setuptools
    pip install -r "${THIS_DIRECTORY}/$1-requirements.txt"
    # The grep below is needed to workaround https://github.com/pypa/pip/issues/8331
    pip freeze -l | grep -v 'pkg_resources==0.0.0' > "${THIS_DIRECTORY}/pinned-$1-requirements.txt"
    rm -rf "${VENV}"
}

update_pinned_reqs lint
update_pinned_reqs typecheck
