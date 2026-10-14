#!/bin/sh

set -e

# This script updates the pinned requirements for linting.
# The lint requirements are split from the other ones since they often have
# incompatible dependencies. They live in the repository-level requirements/
# directory rather than in this package, since they are tooling-only and are
# not part of the workspace resolution.

THIS_DIRECTORY="$(cd "$(dirname "$0")" > /dev/null && pwd)"
REQUIREMENTS_DIRECTORY="$(cd "${THIS_DIRECTORY}/../../../../../requirements" > /dev/null && pwd)"

if command -v uv >/dev/null; then
    VENV_CMD="$(command -v uv) venv --python python3.10"
    PIP_CMD="$(command -v uv) pip"
    FREEZE_OPTIONS=''
else
    VENV_CMD='python3.10 -m venv'
    PIP_CMD='python -m pip'
    FREEZE_OPTIONS='-l'
fi

update_pinned_reqs() {
    VENV=$(mktemp -d "${TMPDIR:-/tmp}/$1_venv.XXXXXXXXXX")
    ${VENV_CMD} "${VENV}"
    . "${VENV}/bin/activate"
    if [ "${PIP_CMD}" = 'python -m pip' ]; then
        ${PIP_CMD} install --upgrade pip setuptools
    fi
    ${PIP_CMD} install -r "${REQUIREMENTS_DIRECTORY}/$1-requirements.txt"
    # The grep below is needed to workaround https://github.com/pypa/pip/issues/8331
    ${PIP_CMD} freeze ${FREEZE_OPTIONS} | grep -v 'pkg_resources==0.0.0' > "${REQUIREMENTS_DIRECTORY}/pinned-$1-requirements.txt"
    rm -rf "${VENV}"
}

update_pinned_reqs lint
