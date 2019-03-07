#!/bin/bash

DOCKER_RUN_EXTRA_ARGS="--privileged" ./run_tests.sh --dockerize --python3 --db postgres --clean_pyc --integration "$@"
