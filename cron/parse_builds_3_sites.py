#!/usr/bin/env python
"""
Connects to sites and determines which builds are available at each.
"""

import sys
import urllib
if sys.version_info[:2] >= ( 2, 5 ):
    import xml.etree.ElementTree as ElementTree
else:
    from galaxy import eggs
    import pkg_resources; pkg_resources.require( "elementtree" )
    from elementtree import ElementTree

sites = ['http://genome.ucsc.edu/cgi-bin/',
        'http://archaea.ucsc.edu/cgi-bin/',
        'http://genome-test.cse.ucsc.edu/cgi-bin/'
]
names = ['main',
        'archaea',
        'test'
]

def main():
    for i in range(len(sites)):
        site = sites[i]+"das/dsn"
        trackurl = sites[i]+"hgTracks?"
        builds = []
        try:
            page = urllib.urlopen(site)
        except:
            print "#Unable to connect to " + site
            continue
        text = page.read()
        try:
            tree = ElementTree.fromstring(text)
        except:
            print "#Invalid xml passed back from " + site
            continue
        print "#Harvested from",site
        
        for dsn in tree:
            build = dsn.find("SOURCE").attrib['id']
            builds.append(build)
            build_dict = {}
        for build in builds:
            build_dict[build]=0
            builds = build_dict.keys()
        yield [names[i],trackurl,builds]

if __name__ == "__main__":
    for site in main():
        print site[0]+"\t"+site[1]+"\t"+",".join(site[2])
