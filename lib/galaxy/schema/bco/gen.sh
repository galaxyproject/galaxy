#!/bin/bash

# must be run from a virtualenv with...
# https://github.com/koxudaxi/datamodel-code-generator
base_url="https://opensource.ieee.org/2791-object/ieee-2791-schema/-/raw/master"
for domain in description_domain error_domain execution_domain io_domain parametric_domain provenance_domain usability_domain
do
    datamodel-codegen --field-constraints --url "${base_url}/${domain}.json" --output "${domain}.py"
done

# base object doesn't compile with latest datamodel-codegen as of 2022/09/13
# datamodel-codegen --url "${base_url}/2791object.json" --output output.py
