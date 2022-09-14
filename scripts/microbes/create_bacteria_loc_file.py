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
    for org in organisms:
        org = organisms[org]
        # if no gpi, then must be a ncbi chr which corresponds to a UCSC org, w/o matching UCSC designation
        try:
            build = org["genome project id"]
        except KeyError:
            continue
        if "build" in org:
            build = org["build"]
            print(
                "ORG\t{}\t{}\t{}\t{}\t{}\t{}\tUCSC".format(
                    build, org["name"], org["kingdom"], org["group"], org["chromosomes"], org["info url"]
                )
            )
        else:
            print(
                "ORG\t{}\t{}\t{}\t{}\t{}\t{}\tNone".format(
                    build, org["name"], org["kingdom"], org["group"], org["chromosomes"], org["info url"]
                )
            )

        for chr in org["chrs"]:
            chr = org["chrs"][chr]
            print(
                "CHR\t{}\t{}\t{}\t{}\t{}\t{}\t{}".format(
                    build,
                    chr["chromosome"],
                    chr["name"],
                    chr["length"],
                    chr["gi"],
                    chr["gb"],
                    "http://www.ncbi.nlm.nih.gov/entrez/viewer.fcgi?db=nucleotide&val=" + chr["refseq"],
                )
            )
            for feature in ["CDS", "tRNA", "rRNA"]:
                print(
                    "DATA\t{}_{}_{}\t{}\t{}\t{}\t{}\t{}".format(
                        build,
                        chr["chromosome"],
                        feature,
                        build,
                        chr["chromosome"],
                        feature,
                        "bed",
                        os.path.join(org["base_dir"], "{}.{}.bed".format(chr["chromosome"], feature)),
                    )
                )
            # FASTA
            print(
                "DATA\t{}_{}_{}\t{}\t{}\t{}\t{}\t{}".format(
                    build,
                    chr["chromosome"],
                    "seq",
                    build,
                    chr["chromosome"],
                    "sequence",
                    "fasta",
                    os.path.join(org["base_dir"], "%s.fna" % chr["chromosome"]),
                )
            )
            # GeneMark
            if os.path.exists(os.path.join(org["base_dir"], "%s.GeneMark.bed" % chr["chromosome"])):
                print(
                    "DATA\t{}_{}_{}\t{}\t{}\t{}\t{}\t{}".format(
                        build,
                        chr["chromosome"],
                        "GeneMark",
                        build,
                        chr["chromosome"],
                        "GeneMark",
                        "bed",
                        os.path.join(org["base_dir"], "%s.GeneMark.bed" % chr["chromosome"]),
                    )
                )
            # GenMarkHMM
            if os.path.exists(os.path.join(org["base_dir"], "%s.GeneMarkHMM.bed" % chr["chromosome"])):
                print(
                    "DATA\t{}_{}_{}\t{}\t{}\t{}\t{}\t{}".format(
                        build,
                        chr["chromosome"],
                        "GeneMarkHMM",
                        build,
                        chr["chromosome"],
                        "GeneMarkHMM",
                        "bed",
                        os.path.join(org["base_dir"], "%s.GeneMarkHMM.bed" % chr["chromosome"]),
                    )
                )
            # Glimmer3
            if os.path.exists(os.path.join(org["base_dir"], "%s.Glimmer3.bed" % chr["chromosome"])):
                print(
                    "DATA\t{}_{}_{}\t{}\t{}\t{}\t{}\t{}".format(
                        build,
                        chr["chromosome"],
                        "Glimmer3",
                        build,
                        chr["chromosome"],
                        "Glimmer3",
                        "bed",
                        os.path.join(org["base_dir"], "%s.Glimmer3.bed" % chr["chromosome"]),
                    )
                )


if __name__ == "__main__":
    __main__()
