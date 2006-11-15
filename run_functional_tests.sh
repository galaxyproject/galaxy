#!/bin/sh

rm -f run_functional_tests.log
./nosetests.sh -v -w test \
    --with-nosehtml --html-report-file run_functional_tests.html \
    --exclude="^get" functional
