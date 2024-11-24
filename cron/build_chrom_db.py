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

import fileinput
import os
import sys
from urllib.parse import urlencode

import parse_builds  # noqa: I100,I202

from galaxy.util import requests


def getchrominfo(url, db):
    tableURL = "http://genome-test.gi.ucsc.edu/cgi-bin/hgTables?"
    URL = tableURL + urlencode(
        {
            "clade": "",
            "org": "",
            "db": db,
            "hgta_outputType": "primaryTable",
            "hgta_group": "allTables",
            "hgta_table": "chromInfo",
            "hgta_track": db,
            "hgta_regionType": "",
            "position": "",
            "hgta_doTopSubmit": "get info",
        }
    )
    page = requests.get(URL).text
    for i, line in enumerate(page.splitlines()):
        line = line.rstrip("\r\n")
        if line.startswith("#"):
            continue
        fields = line.split("\t")
        if len(fields) > 1 and len(fields[0]) > 0 and int(fields[1]) > 0:
            yield [fields[0], fields[1]]
        else:
            raise Exception(f"Problem parsing line {i} '{line}' in page '{page}'")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        sys.exit("Path to place chromInfo tables must be specified.")
    dbpath = sys.argv[1]
    builds = []
    if len(sys.argv) > 2:
        try:
            buildfile = fileinput.FileInput(sys.argv[2])
            for line in buildfile:
                if line.startswith("#"):
                    continue
                builds.append(line.split("\t")[0])
        except Exception:
            sys.exit("Bad input file.")
    else:
        try:
            for build in parse_builds.getbuilds("http://genome.cse.ucsc.edu/cgi-bin/das/dsn"):
                builds.append(build[0])
        except Exception:
            sys.exit("Unable to retrieve builds.")
    for build in builds:
        if build == "?":
            continue  # no lengths for unspecified chrom
        print("Retrieving " + build)
        outfile_name = dbpath + build + ".len"
        try:
            with open(outfile_name, "w") as outfile:
                for chrominfo in getchrominfo("http://genome-test.gi.ucsc.edu/cgi-bin/hgTables?", build):
                    print("\t".join(chrominfo), file=outfile)
        except Exception as e:
            print(f"Failed to retrieve {build}: {e}")
            os.remove(outfile_name)
