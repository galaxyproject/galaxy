#!/bin/sh
set -e

THIS_DIRECTORY="$(cd "$(dirname "$0")" > /dev/null && pwd)"

LINT_VENV=$(mktemp -d "${TMPDIR:-/tmp}/lint_venv.XXXXXXXXXX")
virtualenv -p python3 "${LINT_VENV}"
. "${LINT_VENV}/bin/activate"
pip install --upgrade pip setuptools
pip install -r "${THIS_DIRECTORY}/lint-requirements.txt"
pip freeze -l > "${THIS_DIRECTORY}/pinned-lint-requirements.txt"
rm -rf "${LINT_VENV}"
