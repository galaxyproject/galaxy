#!/usr/bin/env python
"""
Generic POST/create script

usage: create.py key url [key=value ...]
"""
import sys

from common import submit

data = {}
for k, v in [kwarg.split("=", 1) for kwarg in sys.argv[3:]]:
    data[k] = v

submit(sys.argv[1], sys.argv[2], data)
