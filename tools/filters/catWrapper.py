#!/usr/bin/env python
# By Guruprasad Ananda.
import os
import shutil
import sys


def stop_err(msg):
    sys.stderr.write(msg)
    sys.exit()


def main():
    outfile = sys.argv[1]
    infile = sys.argv[2]

    if len(sys.argv) < 4:
        shutil.copyfile(infile, outfile)
        sys.exit()

    cmdline = "cat %s " % (infile)
    for inp in sys.argv[3:]:
        cmdline = cmdline + inp + " "
    cmdline = cmdline + ">" + outfile
    try:
        os.system(cmdline)
    except:
        stop_err("Error encountered with cat.")


if __name__ == "__main__":
    main()
