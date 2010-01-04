#!/bin/sh

## Excluding controllers due to the problematic genetrack dependency

`python ./scripts/check_python.py` ./scripts/nosetests.py -v -w lib \
    --with-nosehtml --html-report-file run_unit_tests.html \
    --with-doctest --exclude=functional --exclude="^get" --exclude=controllers
