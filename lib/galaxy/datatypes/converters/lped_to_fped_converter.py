# for rgenetics - lped to fbat
# recode to numeric fbat version
# much slower so best to always
# use numeric alleles internally

import os
import sys
import time

prog = os.path.split(sys.argv[0])[-1]
myversion = "Oct 10 2009"

galhtmlprefix = """<?xml version="1.0" encoding="utf-8" ?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
<meta name="generator" content="Galaxy %s tool output - see http://getgalaxy.org" />
<title></title>
<link rel="stylesheet" href="/static/style/base.css" type="text/css" />
</head>
<body>
<div class="document">
"""


def timenow():
    """return current time as a string"""
    return time.strftime("%d/%m/%Y %H:%M:%S", time.localtime(time.time()))


def rgConv(inpedfilepath, outhtmlname, outfilepath):
    """convert linkage ped/map to fbat"""
    recode = {"A": "1", "C": "2", "G": "3", "T": "4", "N": "0", "0": "0", "1": "1", "2": "2", "3": "3", "4": "4"}
    basename = os.path.split(inpedfilepath)[-1]  # get basename
    inmap = f"{inpedfilepath}.map"
    inped = f"{inpedfilepath}.ped"
    outf = f"{basename}.ped"  # note the fbat exe insists that this is the extension for the ped data
    outfpath = os.path.join(outfilepath, outf)  # where to write the fbat format file to
    try:
        mf = open(inmap)
    except Exception:
        sys.exit(f"{prog} cannot open inmap file {inmap} - do you have permission?\n")
    try:
        rsl = [x.split()[1] for x in mf]
    except Exception:
        sys.exit(f"## cannot parse {inmap}")
    try:
        os.makedirs(outfilepath)
    except Exception:
        pass  # already exists
    head = " ".join(rsl)  # list of rs numbers
    # TODO add anno to rs but fbat will prolly barf?
    with open(inped) as pedf, open(outfpath, "w", 2**20) as o:
        o.write(head)
        o.write("\n")
        for i, row in enumerate(pedf):
            if i == 0:
                lrow = row.split()
                try:
                    [int(x) for x in lrow[10:50]]  # look for non numeric codes
                except Exception:
                    dorecode = 1
            if dorecode:
                lrow = row.strip().split()
                p = lrow[:6]
                g = lrow[6:]
                gc = [recode.get(z, "0") for z in g]
                lrow = p + gc
                row = f"{' '.join(lrow)}\n"
            o.write(row)


def main():
    """call fbater
    need to work with rgenetics composite datatypes
    so in and out are html files with data in extrafiles path
    <command>python '$__tool_directory__/rg_convert_lped_fped.py' '$input1/$input1.metadata.base_name'
    '$output1' '$output1.extra_files_path'
    </command>
    """
    nparm = 3
    if len(sys.argv) < nparm:
        sys.exit("## %s called with %s - needs %d parameters \n" % (prog, sys.argv, nparm))
    inpedfilepath = sys.argv[1]
    outhtmlname = sys.argv[2]
    outfilepath = sys.argv[3]
    try:
        os.makedirs(outfilepath)
    except Exception:
        pass
    rgConv(inpedfilepath, outhtmlname, outfilepath)
    flist = os.listdir(outfilepath)
    with open(outhtmlname, "w") as f:
        f.write(galhtmlprefix % prog)
        print(f"## Rgenetics: http://rgenetics.org Galaxy Tools {prog} {timenow()}")  # becomes info
        f.write(f"<div>## Rgenetics: http://rgenetics.org Galaxy Tools {prog} {timenow()}\n<ol>")
        for data in flist:
            f.write(f'<li><a href="{os.path.split(data)[-1]}">{os.path.split(data)[-1]}</a></li>\n')
        f.write("</div></body></html>")


if __name__ == "__main__":
    main()
