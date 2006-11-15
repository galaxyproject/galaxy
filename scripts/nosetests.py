#!/usr/bin/env python2.4
# EASY-INSTALL-ENTRY-SCRIPT: 'nose','console_scripts','nosetests'
__requires__ = 'nose'
import sys
from pkg_resources import load_entry_point

sys.exit(
   load_entry_point('nose', 'console_scripts', 'nosetests')()
)
