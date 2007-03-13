#!/bin/sh

dropdb buildbot_galaxy_functional_tests
createdb buildbot_galaxy_functional_tests

export GALAXY_TEST_DBURI=postgres:///buildbot_galaxy_functional_tests

./nosetests.sh -v -w test \
	--with-nosehtml \
	--html-report-file buildbot_functional_tests.html \
	--exclude="^get" \
	functional
