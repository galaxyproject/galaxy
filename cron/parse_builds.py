#!/usr/bin/env python

"""
Connects to the URL specified and outputs builds available at that
DSN in tabular format.  USCS Test gateway is used as default.
build   description
"""

import sys
import urllib
if sys.version_info[:2] >= ( 2, 5 ):
    import xml.etree.ElementTree as ElementTree
else:
    from galaxy import eggs
    import pkg_resources; pkg_resources.require( "elementtree" )
    from elementtree import ElementTree

URL = "http://genome.cse.ucsc.edu/cgi-bin/das/dsn"

def getbuilds(url):
    try:
        page = urllib.urlopen(URL)
    except:
        print "#Unable to open " + URL
        print "?\tunspecified (?)"
        sys.exit(1)

    text = page.read()
    try:
        tree = ElementTree.fromstring(text)
    except:
        print "#Invalid xml passed back from " + URL
        print "?\tunspecified (?)"
        sys.exit(1)

    print "#Harvested from http://genome.cse.ucsc.edu/cgi-bin/das/dsn"
    print "?\tunspecified (?)"
    for dsn in tree:
        build = dsn.find("SOURCE").attrib['id']
        description = dsn.find("DESCRIPTION").text.replace(" - Genome at UCSC","").replace(" Genome at UCSC","")
        
        fields = description.split(" ")
        temp = fields[0]
        for i in range(len(fields)-1):
            if temp == fields[i+1]:
                fields.pop(i+1)
            else:
                temp = fields[i+1]
        description = " ".join(fields)
        yield [build,description]

if __name__ == "__main__":
    if len(sys.argv) > 1:
        URL = sys.argv[1]
    for build in getbuilds(URL):
        print build[0]+"\t"+build[1]+" ("+build[0]+")"

