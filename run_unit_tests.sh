#!/bin/sh

## Excluding controllers due to the problematic genetrack dependency

python -ES ./scripts/nosetests.py -v -w lib \
    --with-nosehtml --html-report-file run_unit_tests.html \
    --with-doctest --exclude=functional --exclude="^get" --exclude=controllers
