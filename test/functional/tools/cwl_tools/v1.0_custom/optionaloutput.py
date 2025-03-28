#!/usr/bin/env python

import sys

if sys.argv[1] == "do_write":
    open("bumble.txt", "w").write("bees\n")
