"""
Bootstrap the Galaxy framework.

This should not be called directly!  Use the run.sh script in Galaxy's
top level directly.
"""
from __future__ import absolute_import

import os
import sys

sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, 'lib')))

from galaxy.util.pastescript import serve
from check_python import check_python  # noqa: I100, I201

# ensure supported version
try:
    check_python()
except Exception:
    sys.exit(1)

if 'LOG_TEMPFILES' in os.environ:
    from log_tempfile import TempFile
    _log_tempfile = TempFile()

serve.run()
