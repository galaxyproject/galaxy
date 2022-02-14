#!/usr/bin/env python
"""
Connects to sites and determines which builds are available at each.
"""

import xml.etree.ElementTree as ElementTree

import requests

sites = [
    "http://genome.ucsc.edu/cgi-bin/",
    "http://archaea.ucsc.edu/cgi-bin/",
    "http://genome-test.gi.ucsc.edu/cgi-bin/",
]
names = ["main", "archaea", "test"]


def main():
    for i in range(len(sites)):
        site = sites[i] + "das/dsn"
        trackurl = sites[i] + "hgTracks?"
        builds = []
        try:
            text = requests.get(site).text
        except Exception:
            print("#Unable to connect to " + site)
            continue

        try:
            tree = ElementTree.fromstring(text)
        except Exception:
            print("#Invalid xml passed back from " + site)
            continue
        print("#Harvested from", site)

        for dsn in tree:
            build = dsn.find("SOURCE").attrib["id"]
            builds.append(build)
            build_dict = {}
        for build in builds:
            build_dict[build] = 0
            builds = list(build_dict.keys())
        yield [names[i], trackurl, builds]


if __name__ == "__main__":
    for site in main():
        print(site[0] + "\t" + site[1] + "\t" + ",".join(site[2]))
