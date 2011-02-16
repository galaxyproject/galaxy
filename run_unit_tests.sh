#!/bin/sh

## Excluding controllers due to the problematic genetrack dependency
## Excluding job runners due to various external dependencies

python ./scripts/nosetests.py -v -w lib \
    --with-nosehtml --html-report-file run_unit_tests.html \
    --with-doctest --exclude=functional --exclude="^get" \
    --exclude=controllers --exclude=runners
