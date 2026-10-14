#!/bin/sh

# Upgrade dependencies by default, export the existing lock with --export-only,
# or verify the lock and its requirements exports without changes with --check.
set -e

this_directory="$(cd "$(dirname "$0")" > /dev/null && pwd)"
workspace_root="$(cd "$this_directory/../../.." > /dev/null && pwd)"
requirements_dir="$this_directory"
cd "$workspace_root"

usage() {
    printf 'Usage: %s [-p pkg | --export-only | --check]\n' "${0##*/}" >&2
}

mode=upgrade
[ "${UV_CHECK:-0}" = "1" ] && mode=check
pkg=
while [ "$#" -gt 0 ]; do
    case "$1" in
        --check) mode=check ;;
        --export-only) mode=export ;;
        -p)
            [ "$#" -ge 2 ] || { usage; exit 2; }
            pkg="$2"
            shift
            ;;
        -h|--help) usage; exit 0 ;;
        *) usage; exit 2 ;;
    esac
    shift
done
if [ -n "$pkg" ] && [ "$mode" != upgrade ]; then
    usage
    exit 2
fi

temp_dir="$(mktemp -d "${TMPDIR:-/tmp}/galaxy_requirements.XXXXXXXXXX")"
trap 'rm -rf "$temp_dir"' 0
trap 'exit 1' HUP INT TERM

# Match CI's toolchain, including when the caller has another uv installed.
uv_version="$(awk '$1 == "uv" { print $2 }' .tool-versions)"
[ -n "$uv_version" ] || { echo 'Missing uv pin in .tool-versions' >&2; exit 1; }
if command -v uv >/dev/null && [ "$(uv --version | awk '{ print $2 }')" = "$uv_version" ]; then
    uv="$(command -v uv)"
else
    if command -v uv >/dev/null; then
        uv venv "$temp_dir/uv"
        uv pip install --python "$temp_dir/uv/bin/python" "uv==$uv_version"
    else
        python3 -m venv "$temp_dir/uv"
        "$temp_dir/uv/bin/python" -m pip install "uv==$uv_version"
    fi
    uv="$temp_dir/uv/bin/uv"
fi

if [ "$mode" = upgrade ]; then
    if [ -n "$pkg" ]; then
        "$uv" lock --upgrade-package "$pkg"
    else
        "$uv" lock --upgrade
    fi
else
    "$uv" lock --check
fi

export_requirements() {
    destination="$1"
    shift
    file="${destination##*/}"
    "$uv" export --locked --no-annotate --no-hashes "$@" > "$temp_dir/$file"
    if [ "$mode" = check ]; then
        if ! diff -u "$destination" "$temp_dir/$file"; then
            echo 'Requirements exports differ from uv.lock; run lib/galaxy/dependencies/update.sh --export-only.' >&2
            exit 1
        fi
    fi
}

# Generate all files before updating any checked-in export.
export_requirements "$this_directory/pinned-requirements.txt" --no-dev
export_requirements "$requirements_dir/pinned-test-requirements.txt" --only-group=test
export_requirements "$requirements_dir/dev-requirements.txt" --only-group=dev
export_requirements "$requirements_dir/pinned-typecheck-requirements.txt" --only-group=typecheck

if [ "$mode" != check ]; then
    cp "$temp_dir/pinned-requirements.txt" "$this_directory/pinned-requirements.txt"
    for file in pinned-test-requirements.txt dev-requirements.txt pinned-typecheck-requirements.txt; do
        cp "$temp_dir/$file" "$requirements_dir/$file"
    done
fi
