#!/bin/sh

cd "$(dirname "$0")"/..

DEST_DIR='test/functional/tools/cwl_tools'

VERSIONS="1.0
1.1
1.2"
for version in $VERSIONS; do
    if [ "$version" = '1.0' ]; then
        repo_name=common-workflow-language
        conformance_filepath=v1.0/conformance_test_v1.0.yaml
        tests_dir=v1.0/v1.0
    else
        repo_name=cwl-v$version
        conformance_filepath=conformance_tests.yaml
        tests_dir=tests
    fi
    branch=main
    wget "https://github.com/common-workflow-language/${repo_name}/archive/${branch}.zip"
    unzip ${branch}.zip
    rm -rf "${DEST_DIR}/v${version}"
    mkdir -p "${DEST_DIR}/v${version}"
    cp "${repo_name}-${branch}/${conformance_filepath}" "${DEST_DIR}/v${version}/conformance_tests.yaml"
    cp -r "${repo_name}-${branch}/${tests_dir}" "${DEST_DIR}/v${version}"/
    rm -rf "${repo_name}-${branch}"
    rm -rf ${branch}.zip
    python3 scripts/cwl_conformance_to_test_cases.py "${DEST_DIR}" "v${version}"
done
