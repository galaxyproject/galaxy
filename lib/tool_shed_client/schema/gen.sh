#!/bin/bash

# must be run from a virtualenv with...
# https://github.com/koxudaxi/datamodel-code-generator
#for model in AccessMethod Checksum DrsObject Error AccessURL ContentsObject DrsService
#do
#    datamodel-codegen --url "https://raw.githubusercontent.com/ga4gh/tool-registry-service-schemas/develop/openapi/ga4gh-tool-discovery.yaml" --output "$model.py"
#one

#datamodel-codegen --url "https://raw.githubusercontent.com/ga4gh-discovery/ga4gh-service-info/v1.0.0/service-info.yaml#/components/schemas/Service" --output Service.py

datamodel-codegen --url "https://raw.githubusercontent.com/ga4gh-discovery/ga4gh-service-info/v1.0.0/service-info.yaml#/paths/~1service-info" --output trs_service_info.py
datamodel-codegen --url "https://raw.githubusercontent.com/ga4gh/tool-registry-service-schemas/develop/openapi/openapi.yaml" --output trs.py
