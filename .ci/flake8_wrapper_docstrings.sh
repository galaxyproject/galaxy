#!/bin/bash

set -e

flake8 `paste .ci/flake8_docstrings_include_list.txt`
