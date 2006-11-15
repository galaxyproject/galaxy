#!/usr/bin/env python

"""
Connects to a UCSC table browser and scrapes chrominfo for every build
specified by an input file (such as one output by parse_builds.py).
If not input file specified, it will connect using parse_builds.py to
retrieve a list of available builds.

All chromInfo is placed in a path with the convention
{dbpath}/buildname.len

Usage:
python build_chrom_db.py dbpath/ [builds_file]
"""

import sys
import parse_builds
import urllib
import fileinput

def getchrominfo(url, db):
    tableURL = "http://genome-test.cse.ucsc.edu/cgi-bin/hgTables?"
    URL = tableURL + urllib.urlencode({
        "clade" : "",
        "org" : "",
        "db" : db,
        "hgta_outputType": "primaryTable",
        "hgta_group" : "allTables",
        "hgta_table" : "chromInfo",
        "hgta_track" : db,
        "hgta_regionType":"",
        "position":"",
        "hgta_doTopSubmit" : "get info"})
    page = urllib.urlopen(URL)
    for line in page:
        line = line.rstrip( "\r\n" )
        if line.startswith("#"): continue
        fields = line.split("\t")
        if len(fields) > 1:
            yield [fields[0], fields[1]]

if __name__ == "__main__":
    if len(sys.argv) == 1:
        print "Path to place chromInfo tables must be specified."
        sys.exit(1)
    dbpath = sys.argv[1]
    builds = []
    if len(sys.argv) > 2:
        try:
            buildfile = fileinput.FileInput(sys.argv[2])
            for line in buildfile:
                if line.startswith("#"): continue
                builds.append(line.split("\t")[0])
        except:
            print "Bad input file."
            sys.exit(1)
    else:
        try:
            for build in parse_builds.getbuilds("http://genome-test.cse.ucsc.edu/cgi-bin/das/dsn"):
                builds.append(build[0])
        except:
            print "Unable to retrieve builds."
            sys.exit(1)
    for build in builds:
        if build == "?":continue # no lengths for unspecified chrom
        outfile = open(dbpath + build + ".len", "w")
        print "Retrieving "+build
        for chrominfo in getchrominfo("http://genome-test.cse.ucsc.edu/cgi-bin/hgTables?",build):
            print >> outfile,"\t".join(chrominfo)
        outfile.close()
