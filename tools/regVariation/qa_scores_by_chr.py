#!/usr/bin/env python

import sys, re, os, tempfile

qual_dir = "/home/gua110/Desktop/rhesus_quality_scores/chr"
qual_file= open("/home/gua110/Desktop/rhesus_quality_scores/rheMac2.qual.qa", "r")

qual_file_contents = qual_file.read(1000000000)

while qual_file_contents != "":
    contents_list = qual_file_contents.split(">")
    os.chdir(qual_dir)
    print "len_contents_list", len(contents_list)
    if len(contents_list) == 1:
        os.system("echo %s | cat >> %s.qa" %(contents_list, prev_file))
    else:
        #print len(contents_list[0])
        #print len(contents_list[1])
        for elem in contents_list:
            if elem == '':
                continue
            if elem.startswith("chr"):
                elems = elem.replace("\r","\n").split("\n")
                cmdline = "echo %s | cat >> %s.qa" %(elems[1:], elems[0])
                os.system("echo >%s\n%s | cat >> %s.qa" %(elems[0], elems[1:], elems[0]))
            else:
                os.system("echo %s | cat >> %s.qa" %(elem, prev_file))
        prev_file = elems[0]
    qual_file_contents = qual_file.read(1000000000)
    