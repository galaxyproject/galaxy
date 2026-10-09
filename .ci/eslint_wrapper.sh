#!/bin/bash

set -e

# Using dependencies from client/node_modules, run eslint against args passed
# to this script. Primary use case here is for a pre-commit check. ESLint finds
# client/eslint.config.mjs by looking up from each file, so this can run from
# the repository root.
node client/node_modules/eslint/bin/eslint.js --no-warn-ignored "$@"
