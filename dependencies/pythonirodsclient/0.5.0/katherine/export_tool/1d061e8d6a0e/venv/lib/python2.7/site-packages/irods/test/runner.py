#!/usr/bin/env python

import os
import sys
from unittest import TestLoader
from unittest import TextTestRunner, TestSuite


"""
NOTE: "If a test package name (directory with __init__.py) matches the pattern
       then the package will be checked for a load_tests function. If this
       exists then it will be called with loader, tests, pattern."
"""

"""
Load all tests in the current directory and run them
"""
if __name__ == "__main__":
    # must set the path for the imported tests
    sys.path.insert(0, os.path.abspath('../..'))

    loader = TestLoader()
    suite = TestSuite(loader.discover(start_dir='.', pattern='*_test.py',
                                      top_level_dir="."))

    result = TextTestRunner(verbosity=2).run(suite)
    if result.wasSuccessful():
        sys.exit(0)

    sys.exit(1)
