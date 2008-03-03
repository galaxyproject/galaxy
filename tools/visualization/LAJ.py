#!/usr/bin/env python2.4

"""
Copies LAV file over to new file for use with LAJ
"""
import sys, shutil
shutil.copyfile(sys.argv[1],sys.argv[2])
