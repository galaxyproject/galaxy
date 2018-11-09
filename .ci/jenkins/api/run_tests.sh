#!/bin/bash

./run_tests.sh --dockerize --db postgres --clean_pyc --skip_flakey_fails -api "$@"
