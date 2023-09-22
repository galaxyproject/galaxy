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
        print("using default base_dir:", base_dir)

    loc_out = os.path.join(base_dir, "seq.loc")
    try:
        loc_out = os.path.join(base_dir, sys.argv[2])
    except Exception:
        print("using default seq.loc:", loc_out)

    organisms = {}

    loc_out = open(loc_out, "wb")

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
        try:
            build = org["genome project id"]
        except KeyError:
            continue
        if "build" in org:
            build = org["build"]

        seq_path = os.path.join(org["base_dir"], "seq")

        # create seq dir, if exists go to next org
        # TODO: add better checking, i.e. for updating
        try:
            os.mkdir(seq_path)
        except Exception:
            print("Skipping", build)
            # continue

        loc_out.write(f"seq {build} {seq_path}\n")

        # Print org info

        for chr in org["chrs"]:
            chr = org["chrs"][chr]

            fasta_file = os.path.join(org["base_dir"], "%s.fna" % chr["chromosome"])
            nib_out_file = os.path.join(seq_path, "%s.nib " % chr["chromosome"])
            # create nibs using faToNib binary
            # TODO: when bx supports writing nib, use it here instead
            command = f"faToNib {fasta_file} {nib_out_file}"
            os.system(command)

    loc_out.close()


if __name__ == "__main__":
    __main__()
