#!/usr/bin/env python2.4

import sys

if sys.maxunicode > 65535:
    print "UCS4"
else:
    print "UCS2"
