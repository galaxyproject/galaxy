#!/bin/bash

set -e

# Run broad range of checks over specific white-listed files, this uses
# the default checks defined in setup.cfg.
while read p; do
    flake8 $(eval echo "$p")
done <.ci/pep8_sources.txt

# Look for obviously broken stuff lots more places.
flake8 --select=E901,E902,F821,F822,F823,F831 --exclude lib/galaxy/util/pastescript/serve.py,lib/pkg_resources.py lib/ test/{api,unit}
