#!/bin/bash

# must be run from a virtualenv with...
# https://github.com/koxudaxi/datamodel-code-generator
for model in AccessMethod Checksum DrsObject Error AccessURL ContentsObject DrsService
do
    datamodel-codegen --input-file-type openapi --output-model-type pydantic_v2.BaseModel --url "https://raw.githubusercontent.com/ga4gh/data-repository-service-schemas/master/openapi/components/schemas/${model}.yaml" --output "$model.py"
done

datamodel-codegen --input-file-type openapi --output-model-type pydantic_v2.BaseModel --url "https://raw.githubusercontent.com/ga4gh-discovery/ga4gh-service-info/v1.0.0/service-info.yaml#/components/schemas/Service" --output Service.py
