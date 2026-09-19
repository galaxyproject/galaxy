#!/bin/sh

cd "$(dirname "$0")"/..

xsd_path="lib/galaxy/tools/xsd/galaxy.xsd"
# Lint the XSD
xmllint --noout "$xsd_path"

test_tools_path='test/functional/tools'
# test all test tools except upload.xml which uses a non-standard conditional
# (without param) which does not survive xsd validation
tool_files_list=$(ls "$test_tools_path"/*.xml | grep -v '_conf.xml$' | grep -v upload.xml)
sh scripts/validate_tools.sh $tool_files_list
