#!/usr/bin/env python
# Dan Blankenberg

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
                info_file = open(os.path.join(this_base_dir, file))
                info = info_file.readlines()
                info_file.close()
                for line in info:
                    fields = line.replace("\n", "").split("=")
                    tmp_dict[fields[0]] = "=".join(fields[1:])
                if "genome project id" in tmp_dict.keys():
                    name = tmp_dict["genome project id"]
                    if "build" in tmp_dict.keys():
                        name = tmp_dict["build"]
                    if name not in organisms.keys():
                        organisms[name] = {"chrs": {}, "base_dir": this_base_dir}
                    for key in tmp_dict.keys():
                        organisms[name][key] = tmp_dict[key]
                else:
                    if tmp_dict["organism"] not in organisms.keys():
                        organisms[tmp_dict["organism"]] = {"chrs": {}, "base_dir": this_base_dir}
                    organisms[tmp_dict["organism"]]["chrs"][tmp_dict["chromosome"]] = tmp_dict

    for org_name, org in list(organisms.items()):
        if "name" not in org:
            del organisms[org_name]

    orgs = list(organisms.keys())
    # need to sort by name
    swap_test = False
    for i in range(0, len(orgs) - 1):
        for j in range(0, len(orgs) - i - 1):
            if organisms[orgs[j]]["name"] > organisms[orgs[j + 1]]["name"]:
                orgs[j], orgs[j + 1] = orgs[j + 1], orgs[j]
            swap_test = True
        if swap_test is False:
            break

    print("||'''Organism'''||'''Kingdom'''||'''Group'''||'''Links to UCSC Archaea Browser'''||")

    for org in organisms.values():
        at_ucsc = False
        # if no gpi, then must be a ncbi chr which corresponds to a UCSC org, w/o matching UCSC designation
        try:
            org["genome project id"]
        except KeyError:
            continue
        if "build" in org:
            at_ucsc = True

        out_str = "||" + org["name"] + "||" + org["kingdom"] + "||" + org["group"] + "||"
        if at_ucsc:
            out_str = out_str + "Yes"
        out_str = out_str + "||"
        print(out_str)


if __name__ == "__main__":
    __main__()
