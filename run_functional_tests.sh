#!/bin/sh

rm -f run_functional_tests.log
./nosetests.sh -v --with-nosehtml --html-report-file run_functional_tests.html --with-doctest --exclude="^get" galaxy.test.functional
