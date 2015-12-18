#!/bin/bash

set -e

flake8 --exclude `paste -sd, .ci/flake8_blacklist.txt` `paste -s .ci/py3_sources.txt`
