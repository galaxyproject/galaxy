#!/bin/bash

# must be run from a virtualenv with...
# https://github.com/koxudaxi/datamodel-code-generator

# Use the installed datamodel-codegen
CODEGEN="datamodel-codegen"

# Base URL for WES OpenAPI spec
WES_SPEC_URL="https://raw.githubusercontent.com/ga4gh/workflow-execution-service-schemas/develop/openapi/workflow_execution_service.openapi.yaml"

# Generate models from full OpenAPI spec
$CODEGEN --input-file-type openapi --output-model-type pydantic_v2.BaseModel --url "$WES_SPEC_URL" --output "__init__.py"
