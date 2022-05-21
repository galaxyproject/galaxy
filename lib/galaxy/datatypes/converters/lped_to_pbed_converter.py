# for rgenetics - lped to pbed
# where to stop with converters
# pbed might be central
# eg lped/eigen/fbat/snpmatrix all to pbed
# and pbed to lped/eigen/fbat/snpmatrix ?
# that's a lot of converters

import os
import subprocess
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


def getMissval(inped=""):
    """
    read some lines...ugly hack - try to guess missing value
    should be N or 0 but might be . or -
    """
    commonmissvals = {"N": "N", "0": "0", "n": "n", "9": "9", "-": "-", ".": "."}
    try:
        f = open(inped)
    except Exception:
        return None  # signal no in file
    missval = None
    while missval is None:  # doggedly continue until we solve the mystery
        try:
            line = f.readline()
        except Exception:
            break
        ll = line.split()[6:]  # ignore pedigree stuff
        for c in ll:
            if commonmissvals.get(c, None):
                missval = c
                f.close()
                return missval
    if not missval:
        missval = "N"  # punt
    f.close()
    return missval


def rgConv(inpedfilepath, outhtmlname, outfilepath, plink):
    """ """
    pedf = f"{inpedfilepath}.ped"
    basename = os.path.split(inpedfilepath)[-1]  # get basename
    outroot = os.path.join(outfilepath, basename)
    missval = getMissval(inped=pedf)
    if not missval:
        print(f"### lped_to_pbed_converter.py cannot identify missing value in {pedf}")
        missval = "0"
    subprocess.check_call(
        [plink, "--noweb", "--file", inpedfilepath, "--make-bed", "--out", outroot, "--missing-genotype", missval],
        cwd=outfilepath,
    )


def main():
    """
    need to work with rgenetics composite datatypes
    so in and out are html files with data in extrafiles path
    <command>python '$__tool_directory__/lped_to_pbed_converter.py' '$input1/$input1.metadata.base_name'
    '$output1' '$output1.extra_files_path' '${GALAXY_DATA_INDEX_DIR}/rg/bin/plink'
    </command>
    """
    nparm = 4
    if len(sys.argv) < nparm:
        sys.exit("## %s called with %s - needs %d parameters \n" % (prog, sys.argv, nparm))
    inpedfilepath = sys.argv[1]
    outhtmlname = sys.argv[2]
    outfilepath = sys.argv[3]
    try:
        os.makedirs(outfilepath)
    except Exception:
        pass
    plink = sys.argv[4]
    rgConv(inpedfilepath, outhtmlname, outfilepath, plink)
    flist = os.listdir(outfilepath)
    with open(outhtmlname, "w") as f:
        f.write(galhtmlprefix % prog)
        s = f"## Rgenetics: http://rgenetics.org Galaxy Tools {prog} {timenow()}"  # becomes info
        print(s)
        f.write(f"<div>{s}\n<ol>")
        for data in flist:
            f.write(f'<li><a href="{os.path.split(data)[-1]}">{os.path.split(data)[-1]}</a></li>\n')
        f.write("</ol></div></div></body></html>")


if __name__ == "__main__":
    main()
