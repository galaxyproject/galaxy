#!/bin/bash

./run_tests.sh --dockerize --db postgres --external_tmp --clean_pyc --integration "$@"
