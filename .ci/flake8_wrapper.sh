#!/bin/bash

set -e

flake8 --exclude `paste -sd, .ci/flake8_blacklist.txt` .

# Apply stricter rules for the directories shared with Pulsar
flake8 --ignore=D --max-line-length=150 lib/galaxy/jobs/runners/util/
