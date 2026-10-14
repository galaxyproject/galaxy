#!/bin/bash
# Fail on any tracked symlink under packages/*/src/** or packages/*/tests/**
# that is not one of the documented allowed categories (see
# doc/source/dev/workspace-ownership.md): nested fixture links under */test/
# or */test-data/, and the retained functional_tools/bundled/static/
# templates/maf/navigation/linters/main chains. Everything else must be a
# real file.
set -euo pipefail

project_dir=$(dirname "$0")/..
cd "$project_dir"

violations=0
while read -r path; do
    case "$path" in
        packages/*/src/*|packages/*/tests/*) ;;
        *) continue ;;
    esac
    case "$path" in
        # Nested fixture links pointing at shared test data.
        */test/*|*/test-data/*) continue ;;
        # Mercurial fixture metadata must preserve its tracked probe symlink.
        */tests/tool_shed/data/toolshed_community_files/*/.hg/wcache/checklink) continue ;;
        # Retained chains documented in doc/source/dev/workspace-ownership.md.
        */tools/util/maf_utilities.py|\
        */tool_util/unittest_utils/functional_tools|\
        */tools/bundled|\
        */webapps/base/static|\
        */webapps/base/templates|\
        */navigation/navigation.yml|\
        */tool_util/linters/*.sample|\
        */galaxy/main/__init__.py) continue ;;
    esac
    echo "ERROR: disallowed source link: $path" >&2
    violations=$((violations + 1))
done < <(git ls-files -s | grep '^120000' | cut -f2)

if [ "$violations" -gt 0 ]; then
    echo "$violations disallowed symlink(s) under packages/*/src or packages/*/tests." >&2
    echo "See doc/source/dev/workspace-ownership.md for the allowed categories." >&2
    exit 1
fi
