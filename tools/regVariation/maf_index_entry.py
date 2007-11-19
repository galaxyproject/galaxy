#!/usr/bin/env python

import sys, re, os, tempfile

qual_dir = "/depot/data2/galaxy/mm8/align/multiz17way"
fout = open("ploc","w")
os.chdir(qual_dir)

tmpfile = tempfile.NamedTemporaryFile()
cmdline = "ls " + "*.lzo | cat >> " + tmpfile.name
os.system (cmdline)

fstr = "17-way multiZ (mm8)\t17_WAY_MULTIZ_mm8\tmm8\t"

for j,qual_file in enumerate(tmpfile.readlines()):
    if j!=0:
        fstr = fstr + ',' + qual_dir + '/' + qual_file.strip()
    else:
        fstr = fstr + qual_dir + '/' + qual_file.strip()

print >>fout, fstr
print fstr

os.system("echo '%s' | cat >> /depot/data2/galaxy/maf_index.loc" %(fstr))