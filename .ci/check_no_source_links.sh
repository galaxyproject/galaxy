#!/bin/bash
# Check staged package source/test links against the fixture and asset policy.
set -euo pipefail
cd "$(dirname "$0")/.."

violations=0
while IFS= read -r -d '' entry; do
    read -r mode object stage <<< "${entry%%$'\t'*}"
    [ "$mode" = 120000 ] || continue
    path=${entry#*$'\t'}
    case "$path" in
        packages/*/src/*|packages/*/tests/*) ;;
        *) continue ;;
    esac
    target=$(git cat-file blob "$object")
    destination=$(python -c 'import os, sys; print(os.path.normpath(os.path.join(os.path.dirname(sys.argv[1]), sys.argv[2])))' "$path" "$target")
    expected=
    case "$path" in
        packages/data/src/galaxy/datatypes/test/*|packages/app/src/galaxy/tools/parameters/test/*)
            case "$destination" in test-data/*) continue ;; esac ;;
        packages/app/src/galaxy/tools/util/maf_utilities.py) expected=packages/data/src/galaxy/datatypes/util/maf_utilities.py ;;
        packages/tool_util/src/galaxy/tool_util/unittest_utils/functional_tools) expected=test/functional/tools ;;
        packages/app/src/galaxy/tools/bundled) expected=tools ;;
        packages/web_apps/src/galaxy/webapps/base/static) expected=static ;;
        packages/web_apps/src/galaxy/webapps/base/templates) expected=templates ;;
        packages/navigation/src/galaxy/navigation/navigation.yml) expected=client/src/utils/navigation/navigation.yml ;;
        packages/tool_util/src/galaxy/tool_util/linters/datatypes_conf.xml.sample) expected=packages/config/src/galaxy/config/sample/datatypes_conf.xml.sample ;;
        packages/app/src/galaxy/main/__init__.py) expected=scripts/galaxy-main ;;
        packages/tool_shed/tests/tool_shed/data/toolshed_community_files/database/community_files/000/repo_1/.hg/wcache/checklink)
            expected=${path%/*}/checklink-target ;;
    esac
    if [ -z "$expected" ] || [ "$destination" != "$expected" ]; then
        echo "ERROR: disallowed source link: $path -> $target" >&2
        violations=$((violations + 1))
    fi
done < <(git ls-files -s -z)
[ "$violations" -eq 0 ]
