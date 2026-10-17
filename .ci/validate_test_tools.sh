#!/bin/sh

cd "$(dirname "$0")"/.. || exit

xsd_path="lib/galaxy/tool_util/xsd/galaxy.xsd"
# Lint the XSD, failing fast on a bad path or malformed schema
xmllint --noout "$xsd_path" || exit 1

test_tools_path='test/functional/tools'
# XSD-validate every test tool at the top level and one subdirectory down.
# Skip *_conf.xml and macro files (not tools) and upload.xml (its
# param-less conditional is not XSD-valid).
set --
for tool_file in "$test_tools_path"/*.xml "$test_tools_path"/*/*.xml; do
    case "$tool_file" in
        *_conf.xml | */upload.xml | */macros.xml | *_macros.xml) ;;
        *) set -- "$@" "$tool_file" ;;
    esac
done
sh scripts/validate_tools.sh "$@"
