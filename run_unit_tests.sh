#!/bin/sh

./nosetests.sh -v --with-nosehtml --html-report-file run_unit_tests.html --with-doctest --exclude=functional --exclude="^get" galaxy
