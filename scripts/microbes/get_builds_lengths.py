#!/usr/bin/env python
# Dan Blankenberg
from __future__ import print_function

import os
import sys

assert sys.version_info[:2] >= (2, 6)


def __main__():
    base_dir = os.path.join(os.getcwd(), "bacteria")
    try:
        base_dir = sys.argv[1]
    except IndexError:
        pass

    organisms = {}
    for result in os.walk(base_dir):
        this_base_dir, sub_dirs, files = result
        for file in files:
            if file[-5:] == ".info":
                tmp_dict = {}
                info_file = open(os.path.join(this_base_dir, file), 'r')
                info = info_file.readlines()
                info_file.close()
                for line in info:
                    fields = line.replace("\n", "").split("=")
                    tmp_dict[fields[0]] = "=".join(fields[1:])
                if 'genome project id' in tmp_dict.keys():
                    name = tmp_dict['genome project id']
                    if 'build' in tmp_dict.keys():
                        name = tmp_dict['build']
                    if name not in organisms.keys():
                        organisms[name] = {'chrs': {}, 'base_dir': this_base_dir}
                    for key in tmp_dict.keys():
                        organisms[name][key] = tmp_dict[key]
                else:
                    if tmp_dict['organism'] not in organisms.keys():
                        organisms[tmp_dict['organism']] = {'chrs': {}, 'base_dir': this_base_dir}
                    organisms[tmp_dict['organism']]['chrs'][tmp_dict['chromosome']] = tmp_dict
    for org in organisms:
        org = organisms[org]
        # if no gpi, then must be a ncbi chr which corresponds to a UCSC org, w/o matching UCSC designation
        try:
            build = org['genome project id']
        except KeyError:
            continue

        if 'build' in org:
            build = org['build']

        chrs = []
        for chrom in org['chrs']:
            chrom = org['chrs'][chrom]
            chrs.append("%s=%s" % (chrom['chromosome'], chrom['length']))
        print("%s\t%s\t%s" % (build, org['name'], ",".join(chrs)))


if __name__ == "__main__":
    __main__()
