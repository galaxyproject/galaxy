#!/bin/sh
TEST=$(mktemp)
TEST_EXTRA_CLASSES=$(mktemp)

pytest --collect-only --ignore=test/functional lib/galaxy_test/ test/ > "$TEST"
pytest -o python_classes='Test* *Test *TestCase' --collect-only --ignore=test/functional lib/galaxy_test/ test/ > "$TEST_EXTRA_CLASSES"

n_tests=$(grep 'tests collected' "$TEST" | sed -e 's/[^0-9]*\([0-9]*\) tests collected.*/\1/')
n_tests_extra_classes=$(grep 'tests collected' "$TEST_EXTRA_CLASSES" | sed -e 's/[^0-9]*\([0-9]*\) tests collected.*/\1/')

if [ "$n_tests_extra_classes" -gt "$n_tests" ]; then
    echo "New test class with name not starting with Test introduced, change it to have tests collected by pytest"
    diff "$TEST" "$TEST_EXTRA_CLASSES"
    exit 1
fi
