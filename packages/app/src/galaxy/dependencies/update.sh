#!/bin/sh

# This script installs uv if it's not already installed in the user account.
# It then runs uv inside Galaxy's root directory, potentially updating
# pyproject.toml and uv.lock, and the pinned requirements files.

set -e

this_directory="$(cd "$(dirname "$0")" > /dev/null && pwd)"

usage() {
    printf "Usage: %s: [-p pkg]\n" "${0##*/}" >&2
}

pkg=
while getopts 'p:h' OPTION
do
    case $OPTION in
        p) pkg="$OPTARG"
           ;;
        h) usage
           exit 0
           ;;
        ?) usage
           exit 2
           ;;
    esac
done
shift $((OPTIND - 1))

# The workspace root (containing pyproject.toml and uv.lock) is five
# directories above this script; uv must run there regardless of the
# caller's working directory.
workspace_root="$(cd "${this_directory}/../../../../.." > /dev/null && pwd)"
cd "$workspace_root"
# Tooling-only exports (test, dev, typecheck) are regenerated into the
# repository-level requirements/ directory; the runtime export
# (pinned-requirements.txt) ships with the wheel and stays next to this script.
requirements_dir="$workspace_root/requirements"

# Create a virtual environment in a tmp directory and install uv into it
# Use the repository uv version pinned in .uv-version.
uv_version="$(cat "$workspace_root/.uv-version" 2>/dev/null || echo "")"
if command -v uv >/dev/null; then
    uv="$(command -v uv)"
    if [ -n "$uv_version" ]; then
        installed_version="$($uv --version 2>/dev/null | awk '{print $2}')"
        if [ "$installed_version" != "$uv_version" ]; then
            echo "WARNING: uv $installed_version != pinned $uv_version (.uv-version); proceeding with installed version" >&2
        fi
    fi
else
    uv_venv=$(mktemp -d "${TMPDIR:-/tmp}/uv_venv.XXXXXXXXXX")
    python3 -m venv "${uv_venv}"
    if [ -n "$uv_version" ]; then
        "${uv_venv}/bin/python" -m pip install "uv==$uv_version"
    else
        "${uv_venv}/bin/python" -m pip install uv
    fi
    uv="${uv_venv}/bin/uv"
fi

# Run uv (this may update pyproject.toml and uv.lock).
# Use --check mode (UV_CHECK=1) for non-upgrading regeneration verification in CI:
#   UV_CHECK=1 ./update.sh  -> uv lock --check + export --frozen without --upgrade
if [ -n "$UV_CHECK" ]; then
    ${uv} lock --check
    check_export_suffix="--check"
else
    check_export_suffix=""
fi
if [ -z "$UV_CHECK" ]; then
    if [ -n "$pkg" ]; then
        ${uv} lock --upgrade-package "$pkg"
    else
        ${uv} lock --upgrade
    fi
fi

# Update pinned requirements files.
UV_EXPORT_OPTIONS='--frozen --no-annotate --no-hashes'
if [ -n "$UV_CHECK" ]; then
    # Non-upgrading regeneration check: exports must already be up to date.
    tmpdir="$(mktemp -d "${TMPDIR:-/tmp}/gx_export_check.XXXXXXXXXX")"
    # shellcheck disable=SC2086
    ${uv} export ${UV_EXPORT_OPTIONS} --no-dev > "$tmpdir/pinned-requirements.txt"
    # shellcheck disable=SC2086
    ${uv} export ${UV_EXPORT_OPTIONS} --only-group=test > "$tmpdir/pinned-test-requirements.txt"
    # shellcheck disable=SC2086
    ${uv} export ${UV_EXPORT_OPTIONS} --only-group=dev > "$tmpdir/dev-requirements.txt"
    # shellcheck disable=SC2086
    ${uv} export ${UV_EXPORT_OPTIONS} --only-group=typecheck > "$tmpdir/pinned-typecheck-requirements.txt"
    for f in pinned-requirements.txt; do
        if ! diff -u "$this_directory/$f" "$tmpdir/$f"; then
            echo "ERROR: $f is not up to date; run packages/app/src/galaxy/dependencies/update.sh to regenerate" >&2
            rm -rf "$tmpdir"
            exit 1
        fi
    done
    for f in pinned-test-requirements.txt dev-requirements.txt pinned-typecheck-requirements.txt; do
        if ! diff -u "$requirements_dir/$f" "$tmpdir/$f"; then
            echo "ERROR: requirements/$f is not up to date; run packages/app/src/galaxy/dependencies/update.sh to regenerate" >&2
            rm -rf "$tmpdir"
            exit 1
        fi
    done
    rm -rf "$tmpdir"
    echo "Export check passed: all pinned requirements up to date."
else
    # shellcheck disable=SC2086
    ${uv} export ${UV_EXPORT_OPTIONS} --no-dev > "$this_directory/pinned-requirements.txt"
    # shellcheck disable=SC2086
    ${uv} export ${UV_EXPORT_OPTIONS} --only-group=test > "$requirements_dir/pinned-test-requirements.txt"
    # shellcheck disable=SC2086
    ${uv} export ${UV_EXPORT_OPTIONS} --only-group=dev > "$requirements_dir/dev-requirements.txt"
    # shellcheck disable=SC2086
    ${uv} export ${UV_EXPORT_OPTIONS} --only-group=typecheck > "$requirements_dir/pinned-typecheck-requirements.txt"
fi
