#!/bin/sh
n_tests=$(pytest --collect-only --ignore=test/functional lib/galaxy_test/ test/ | grep 'tests collected' | sed -e 's/[^0-9]*\([0-9]*\) tests collected.*/\1/')
n_tests_extra_classes=$(pytest -o python_classes='Test* *Test *TestCase' --collect-only --ignore=test/functional lib/galaxy_test/ test/ | grep 'tests collected' | sed -e 's/[^0-9]*\([0-9]*\) tests collected.*/\1/')
if [ "$n_tests_extra_classes" -gt "$n_tests" ]; then
    echo "New test class with name not starting with Test introduced, change it to have tests collected by pytest"
    exit 1
fi
