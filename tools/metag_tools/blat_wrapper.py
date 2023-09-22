#!/usr/bin/env python

import os
import sys
import tempfile

assert sys.version_info[:2] >= (2, 4)


def stop_err(msg):
    sys.stderr.write("%s\n" % msg)
    sys.exit()


def check_nib_file(dbkey, GALAXY_DATA_INDEX_DIR):
    nib_file = "%s/alignseq.loc" % GALAXY_DATA_INDEX_DIR
    nib_path = ""
    nibs = {}
    for line in open(nib_file):
        line = line.rstrip("\r\n")
        if line and not line.startswith("#"):
            fields = line.split("\t")
            if len(fields) < 3:
                continue
            if fields[0] == "seq":
                nibs[(fields[1])] = fields[2]
    if dbkey in nibs:
        nib_path = nibs[(dbkey)]
    return nib_path


def check_twobit_file(dbkey, GALAXY_DATA_INDEX_DIR):
    twobit_file = "%s/twobit.loc" % GALAXY_DATA_INDEX_DIR
    twobit_path = ""
    twobits = {}
    for line in open(twobit_file):
        line = line.rstrip("\r\n")
        if line and not line.startswith("#"):
            fields = line.split("\t")
            if len(fields) < 2:
                continue
            twobits[(fields[0])] = fields[1]
    if dbkey in twobits:
        twobit_path = twobits[(dbkey)]
    return twobit_path


def __main__():
    # I/O
    source_format = sys.argv[1]  # 0: dbkey; 1: upload file
    target_file = sys.argv[2]
    query_file = sys.argv[3]
    output_file = sys.argv[4]
    min_iden = sys.argv[5]
    tile_size = sys.argv[6]
    one_off = sys.argv[7]

    try:
        float(min_iden)
    except ValueError:
        stop_err("Invalid value for minimal identity.")

    try:
        test = int(tile_size)
        assert test >= 6 and test <= 18
    except Exception:
        stop_err("Invalid value for tile size. DNA word size must be between 6 and 18.")

    try:
        test = int(one_off)
        assert test >= 0 and test <= int(tile_size)
    except Exception:
        stop_err("Invalid value for mismatch numbers in the word")

    GALAXY_DATA_INDEX_DIR = sys.argv[8]

    all_files = []
    if source_format == "0":
        # check target genome
        dbkey = target_file
        nib_path = check_nib_file(dbkey, GALAXY_DATA_INDEX_DIR)
        twobit_path = check_twobit_file(dbkey, GALAXY_DATA_INDEX_DIR)
        if not os.path.exists(nib_path) and not os.path.exists(twobit_path):
            stop_err("No sequences are available for %s, request them by reporting this error." % dbkey)

        # check the query file, see whether all of them are legitimate sequence
        if nib_path and os.path.isdir(nib_path):
            compress_files = os.listdir(nib_path)
            target_path = nib_path
        elif twobit_path:
            compress_files = [twobit_path]
            target_path = ""
        else:
            stop_err("Requested genome build has no available sequence.")

        for file in compress_files:
            file = "%s/%s" % (target_path, file)
            file = os.path.normpath(file)
            all_files.append(file)
    else:
        all_files = [target_file]

    for detail_file_path in all_files:
        output_tempfile = tempfile.NamedTemporaryFile().name
        command = "blat %s %s %s -oneOff=%s -tileSize=%s -minIdentity=%s -mask=lower -noHead -out=pslx 2>&1" % (
            detail_file_path,
            query_file,
            output_tempfile,
            one_off,
            tile_size,
            min_iden,
        )
        os.system(command)
        os.system("cat %s >> %s" % (output_tempfile, output_file))
        os.remove(output_tempfile)


if __name__ == "__main__":
    __main__()
