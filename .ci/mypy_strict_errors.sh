#!/bin/sh
#
# Print the mypy errors that the current checkout would have if most
# green-list flags (see mypy.ini) were forced on for the whole codebase, one
# sorted, normalised (no "severity" key) JSON object per line, excluding
# lib/galaxy_test/ and test/. Must be run from the repository root, with mypy
# and its dependencies already installed.
#
# --disallow-untyped-calls is deliberately left out: unlike the other flags,
# it isn't local to the function being checked, it also fires when new,
# fully-annotated code calls into an existing untyped function elsewhere.
# Counting it here would force contributors adding new code to also annotate
# unrelated legacy code they merely call into, or add a `type: ignore` for
# it, which isn't what this check is meant to enforce.
#
# Used by .github/workflows/mypy_strict_ratchet.yaml to compare a pull
# request's head against its target branch, and to report which new errors it
# introduces.

set -e

output=$(mktemp)
trap 'rm -f "$output"' EXIT

set +e
(cd lib && mypy \
    --output json \
    --disallow-any-generics \
    --disallow-untyped-decorators \
    --disallow-untyped-defs \
    --warn-return-any \
    .) > "$output" 2>&1
mypy_exit_code=$?
set -e

# mypy exits 0 (no errors) or 1 (errors found) on a normal run; anything else
# is a crash or config problem, and $output can't be trusted to contain only
# well-formed JSON error records.
if [ "$mypy_exit_code" -gt 1 ]; then
    cat "$output" >&2
    echo "mypy exited with status $mypy_exit_code, see output above" >&2
    exit 1
fi

jq -c 'select(.file | startswith("galaxy_test/") | not) | del(.severity)' "$output" | sort
