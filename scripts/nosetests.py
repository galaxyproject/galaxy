#!/usr/bin/env python
# EASY-INSTALL-ENTRY-SCRIPT: 'nose','console_scripts','nosetests'
# __requires__ = 'nose'
import sys

from pkg_resources import load_entry_point

assert sys.version_info[:2] >= ( 2, 7 )

nose_core_TestProgram = load_entry_point('nose', 'console_scripts', 'nosetests')
nose_core_TestProgram()
