#!/bin/sh

## Excluding controllers due to the problematic genetrack dependency
## Excluding job runners due to various external dependencies

COVERAGE=`which coverage`
COVERAGE_ARG=""
if [ $COVERAGE ]; then
    COVERAGE_ARG="--with-coverage"
fi

python ./scripts/nosetests.py -v \
    $COVERAGE_ARG \
    --with-nosehtml --html-report-file run_unit_tests.html \
    --with-doctest --exclude=functional --exclude="^get" \
    --exclude=controllers --exclude=runners lib test/unit
