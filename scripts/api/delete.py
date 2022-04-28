#!/usr/bin/env python
"""
Generic DELETE/delete script

usage: delete.py key url
"""
import sys

from common import delete

data = {}
for k, v in [kwarg.split("=", 1) for kwarg in sys.argv[3:]]:
    data[k] = v

delete(sys.argv[1], sys.argv[2], data)
