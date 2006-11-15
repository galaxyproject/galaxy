#!/bin/sh

./nosetests.sh -v -w lib \
    --with-nosehtml --html-report-file run_unit_tests.html \
    --with-doctest --exclude=functional --exclude="^get"
