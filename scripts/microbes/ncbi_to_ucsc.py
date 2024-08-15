#!/usr/bin/env python
"""
Walk downloaded Genome Projects and Convert, in place, IDs to match the UCSC Archaea browser, where applicable.
Uses UCSC Archaea DSN.
"""

import os
import sys
from shutil import move
from urllib.request import urlopen
from xml.etree import ElementTree


def __main__():
    base_dir = os.path.join(os.getcwd(), "bacteria")
    try:
        base_dir = sys.argv[1]
    except IndexError:
        print("using default base_dir:", base_dir)

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
                    if tmp_dict["genome project id"] not in organisms.keys():
                        organisms[tmp_dict["genome project id"]] = {"chrs": {}, "base_dir": this_base_dir}
                    for key in tmp_dict.keys():
                        organisms[tmp_dict["genome project id"]][key] = tmp_dict[key]
                else:
                    if tmp_dict["organism"] not in organisms.keys():
                        organisms[tmp_dict["organism"]] = {"chrs": {}, "base_dir": this_base_dir}
                    organisms[tmp_dict["organism"]]["chrs"][tmp_dict["chromosome"]] = tmp_dict

    # get UCSC data

    URL = "http://archaea.ucsc.edu/cgi-bin/das/dsn"

    try:
        page = urlopen(URL)
    except Exception:
        print("#Unable to open " + URL)
        print("?\tunspecified (?)")
        sys.exit(1)

    text = page.read()
    try:
        tree = ElementTree.fromstring(text)
    except Exception:
        print("#Invalid xml passed back from " + URL)
        print("?\tunspecified (?)")
        sys.exit(1)

    builds = {}

    for dsn in tree:
        build = dsn.find("SOURCE").attrib["id"]
        try:
            org_page = (
                urlopen("http://archaea.ucsc.edu/cgi-bin/hgGateway?db=" + build)
                .read()
                .replace("\n", "")
                .split("<table border=2 cellspacing=2 cellpadding=2>")[1]
                .split("</table>")[0]
                .split("</tr>")
            )
        except Exception:
            print("NO CHROMS FOR", build)
            continue
        org_page.pop(0)
        if org_page[-1] == "":
            org_page.pop(-1)

        for row in org_page:
            chr = row.split("</a>")[0].split(">")[-1]
            refseq = row.split("</a>")[-2].split(">")[-1]
            for org in organisms:
                for org_chr in organisms[org]["chrs"]:
                    if organisms[org]["chrs"][org_chr]["chromosome"] == refseq:
                        if org not in builds:
                            builds[org] = {"chrs": {}, "build": build}
                        builds[org]["chrs"][refseq] = chr

    print()
    ext_to_edit = [
        "bed",
        "info",
    ]
    for org in builds:
        print(org, "changed to", builds[org]["build"])

        # org info file
        info_file_old = os.path.join(base_dir + org, org + ".info")
        info_file_new = os.path.join(base_dir + org, builds[org]["build"] + ".info")

        old_dir = base_dir + org
        new_dir = base_dir + builds[org]["build"]

        # open and edit org info file
        info_file_contents = open(info_file_old).read()
        info_file_contents = info_file_contents + "build=" + builds[org]["build"] + "\n"
        for chrom in builds[org]["chrs"]:
            info_file_contents = info_file_contents.replace(chrom, builds[org]["chrs"][chrom])
            for result in os.walk(base_dir + org):
                this_base_dir, sub_dirs, files = result
                for file in files:
                    if file[0 : len(chrom)] == chrom:
                        # rename file
                        old_name = os.path.join(this_base_dir, file)
                        new_name = os.path.join(this_base_dir, builds[org]["chrs"][chrom] + file[len(chrom) :])
                        move(old_name, new_name)

                        # edit contents of file, skiping those in list
                        if file.split(".")[-1] not in ext_to_edit:
                            continue

                        file_contents = open(new_name).read()
                        file_contents = file_contents.replace(chrom, builds[org]["chrs"][chrom])

                        # special case fixes...
                        if file[-5:] == ".info":
                            file_contents = file_contents.replace("organism=" + org, "organism=" + builds[org]["build"])
                            file_contents = file_contents.replace(
                                "refseq=" + builds[org]["chrs"][chrom], "refseq=" + chrom
                            )

                        # write out new file
                        file_out = open(new_name, "w")
                        file_out.write(file_contents)
                        file_out.close()

        # write out org info file and remove old file
        org_info_out = open(info_file_new, "w")
        org_info_out.write(info_file_contents)
        org_info_out.close()
        os.unlink(info_file_old)

        # change org directory name
        move(old_dir, new_dir)


if __name__ == "__main__":
    __main__()
