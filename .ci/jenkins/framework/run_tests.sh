#!/bin/bash

./run_tests.sh --dockerize --db postgres --clean_pyc --framework "$@"
