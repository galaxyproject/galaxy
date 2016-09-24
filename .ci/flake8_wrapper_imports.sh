#!/bin/bash

set -e

flake8 `paste .ci/flake8_lint_include_list.txt`
