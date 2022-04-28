#!/bin/bash

set -e

# Setting NODE_PATH and config appropriately, using dependencies from
# client/node_modules, run eslint against args passed to this script.
# Primary use case here is for a pre-commit check.
NODE_PATH=src/ node client/node_modules/eslint/bin/eslint.js -c client/.eslintrc.json "$@"
