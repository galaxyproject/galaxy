#!/bin/sh
set -e

THIS_DIRECTORY="$(cd "$(dirname "$0")" > /dev/null && pwd)"

TYPECHECK_VENV=$(mktemp -d "${TMPDIR:-/tmp}/typecheck_venv.XXXXXXXXXX")
python3.7 -m venv "${TYPECHECK_VENV}"
. "${TYPECHECK_VENV}/bin/activate"
pip install --upgrade pip setuptools
pip install -r "${THIS_DIRECTORY}/typecheck-requirements.txt"
# The grep below is needed to workaround https://github.com/pypa/pip/issues/8331
pip freeze -l | grep -v 'pkg_resources==0.0.0' > "${THIS_DIRECTORY}/pinned-typecheck-requirements.txt"
rm -rf "${TYPECHECK_VENV}"
