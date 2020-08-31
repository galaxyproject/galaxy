#!/bin/sh

cd "$(dirname "$0")"/..

xsd_path="lib/galaxy/tools/xsd/galaxy.xsd"
# Lint the XSD
xmllint --noout "$xsd_path"

test_tools_path='test/functional/tools'
tool_files_list=$(ls "$test_tools_path"/*.xml | grep -v '_conf.xml$')
sh scripts/validate_tools.sh $tool_files_list
