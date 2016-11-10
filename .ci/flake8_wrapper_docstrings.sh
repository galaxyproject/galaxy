#!/bin/bash

set -e

# D100 - Missing docstring in public module.
# D2XX - Whitespace issues.
# D3XX - Quoting issues.
# D401 - First line should be in imperative mood 
# D403 - First word of the first line should be properly capitalized
args="--ignore=D --select=D100,D201,D202,D206,D207,D208,D209,D211,D3,D401,D403"

# If the first argument is --include, lint the modules expected to pass. If
# the first argument is --exclude, lint all modules the full Galaxy linter lints
# (this will fail).

if [ "$1" = "--include" ];
then
    flake8 $args `paste .ci/flake8_docstrings_include_list.txt`
else
    flake8 $args --exclude `paste -sd, .ci/flake8_blacklist.txt` .
fi
