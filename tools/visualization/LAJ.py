#!/usr/bin/env python

"""
Copies LAV file over to new file for use with LAJ
"""
import sys, shutil

assert sys.version_info[:2] >= ( 2, 4 )

shutil.copyfile(sys.argv[1],sys.argv[2])
