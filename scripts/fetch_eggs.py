#!/usr/bin/env python
from __future__ import print_function
from os import pardir
from os.path import join, abspath, dirname
from sys import exit

msg = """
Eggs in this release of Galaxy have been replaced by Python's newer packaging
format, wheels. Please use scripts/common_startup.sh to set up your
environment:

cd {dir} && ./scripts/common_startup.sh

This will create a Python virtualenv and install Galaxy's dependencies into it.

If you start Galaxy using means other than run.sh (as you probably do if you
are seeing this message), be sure to activate the virtualenv before starting,
using:

. {venv}/bin/activate

If you already run Galaxy in its own virtualenv, you can reuse your existing
virtualenv with:

cd {dir} && ./scripts/common_startup.sh --skip-venv
"""

galaxy = abspath(join(dirname(__file__), pardir))
venv = join(galaxy, '.venv')
print(msg.format(dir=abspath(join(dirname(__file__), pardir)),
                 venv=venv))
exit(1)
