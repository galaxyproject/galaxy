#!/usr/bin/env python
"""
Connects to the URL specified and outputs builds available at that
DSN in tabular format.  UCSC Main gateway is used as default.
build   description
"""

import sys
import xml.etree.ElementTree as ElementTree

from galaxy.util import requests


def getbuilds(url):
    try:
        text = requests.get(url).text
    except Exception:
        print("#Unable to open " + url)
        print("?\tunspecified (?)")
        sys.exit(1)

    try:
        tree = ElementTree.fromstring(text)
    except Exception:
        print("#Invalid xml passed back from " + url)
        print("?\tunspecified (?)")
        sys.exit(1)

    print("#Harvested from " + url)
    print("?\tunspecified (?)")
    for dsn in tree:
        build = dsn.find("SOURCE").attrib["id"]
        description = dsn.find("DESCRIPTION").text.replace(" - Genome at UCSC", "").replace(" Genome at UCSC", "")

        fields = description.split(" ")
        temp = fields[0]
        for i in range(len(fields) - 1):
            if temp == fields[i + 1]:
                fields.pop(i + 1)
            else:
                temp = fields[i + 1]
        description = " ".join(fields)
        yield [build, description]


if __name__ == "__main__":
    if len(sys.argv) > 1:
        URL = sys.argv[1]
    else:
        URL = "http://genome.cse.ucsc.edu/cgi-bin/das/dsn"
    for build in getbuilds(URL):
        print(build[0] + "\t" + build[1] + " (" + build[0] + ")")
