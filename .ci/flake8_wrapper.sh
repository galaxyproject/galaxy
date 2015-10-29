#!/bin/bash

set -e

flake8 --exclude `paste -sd, .ci/flake8_blacklist.txt` .

# Look for obviously broken stuff lots more places.
flake8 --select=E901,E902,F821,F822,F823,F831 --exclude lib/pkg_resources.py contrib/ lib/
