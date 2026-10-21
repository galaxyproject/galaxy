#!/bin/bash

set -e

flake8 --exclude $(paste -sd, .ci/flake8_ignorelist.txt) .

# Apply stricter rules for the directories shared with Pulsar
flake8 --ignore=E203,D --max-line-length=150 packages/app/src/galaxy/jobs/runners/util/
