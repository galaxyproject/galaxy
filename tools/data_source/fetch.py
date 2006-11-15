#!/usr/bin/env python2.4

"""
Script that just echos the command line.
"""

import sys, os, urllib

BUFFER = 1048576

url      = sys.argv[1]
out_name = sys.argv[2]

out = open(out_name, 'wt')
try:
    page = urllib.urlopen(url)
    while 1:
        data = page.read(BUFFER)
        if not data:
            break
        out.write(data)
except Exception, e:
    print 'Error getting the data -> %s' % e
out.close()
