from __future__ import print_function

import ast
import os
import re
import sys
from distutils.version import LooseVersion

DEV_RELEASE = os.environ.get("DEV_RELEASE", None) == "1"
PROJECT_DIRECTORY = os.getcwd()
PROJECT_DIRECTORY_NAME = os.path.basename(os.path.abspath(PROJECT_DIRECTORY))
PROJECT_MODULE_FILENAME = "project_galaxy_%s.py" % PROJECT_DIRECTORY_NAME

source_dir = sys.argv[1]
PROJECT_MODULE_PATH = os.path.join(PROJECT_DIRECTORY, source_dir, PROJECT_MODULE_FILENAME)

_version_re = re.compile(r'__version__\s+=\s+(.*)')
with open(PROJECT_MODULE_PATH, 'rb') as f:
    version = str(ast.literal_eval(_version_re.search(
        f.read().decode('utf-8')).group(1)))

if not DEV_RELEASE:
    # Strip .devN
    version_tuple = LooseVersion(version).version[0:3]
    print(".".join(map(str, version_tuple)))
else:
    print(version)
