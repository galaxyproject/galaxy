"""
Bootstrap the Galaxy framework.

This should not be called directly!  Use the run.sh script in Galaxy's
top level directly.
"""

import os
import sys

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, "lib")))

from check_python import check_python  # noqa: I100, I201

from galaxy.util.pastescript import serve

# ensure supported version
try:
    check_python()
except Exception:
    sys.exit(1)

serve.run()
