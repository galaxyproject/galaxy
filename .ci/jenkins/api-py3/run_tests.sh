#!/bin/bash

./run_tests.sh --dockerize --python3 --db postgres --clean_pyc --skip_flakey_fails -api "$@"
