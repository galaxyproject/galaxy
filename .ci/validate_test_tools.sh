#!/bin/sh

cd "$(dirname "$0")"/.. || exit

xsd_path="lib/galaxy/tool_util/xsd/galaxy.xsd"
# Lint the XSD, failing fast on a bad path or malformed schema
xmllint --noout "$xsd_path" || exit 1

test_tools_path='test/functional/tools'
# test all test tools except *_conf.xml (not tools) and upload.xml, which uses
# a non-standard conditional (without param) that does not survive xsd validation
set --
for tool_file in "$test_tools_path"/*.xml; do
    case "$tool_file" in
        *_conf.xml | */upload.xml) ;;
        *) set -- "$@" "$tool_file" ;;
    esac
done
sh scripts/validate_tools.sh "$@"
