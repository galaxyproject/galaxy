#!/bin/bash

set -e

while read p; do
    flake8 $(eval echo "$p")
done <.ci/pep8_sources.txt
