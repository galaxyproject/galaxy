#!/bin/bash

set -e

make node-deps
# run eslint against args passed to this scriptA
# "eslint": "eslint -c .eslintrc.json --ext .js,.vue src"
NODE_PATH=src/ node client/node_modules/eslint/bin/eslint.js -c client/.eslintrc.json "$@"