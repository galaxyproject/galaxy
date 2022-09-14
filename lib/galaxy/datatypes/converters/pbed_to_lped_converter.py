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


def rgConv(inpedfilepath, outhtmlname, outfilepath, plink):
    """ """
    basename = os.path.split(inpedfilepath)[-1]  # get basename
    outroot = os.path.join(outfilepath, basename)
    subprocess.check_call([plink, "--noweb", "--bfile", inpedfilepath, "--recode", "--out", outroot], cwd=outfilepath)


def main():
    """
    need to work with rgenetics composite datatypes
    so in and out are html files with data in extrafiles path
    <command>python '$__tool_directory__/pbed_to_lped_converter.py' '$input1/$input1.metadata.base_name'
    '$output1' '$output1.extra_files_path' '${GALAXY_DATA_INDEX_DIR}/rg/bin/plink'
    </command>
    """
    nparm = 4
    if len(sys.argv) < nparm:
        sys.exit("PBED to LPED converter called with %s - needs %d parameters \n" % (sys.argv, nparm))
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
        s = f"## Rgenetics: http://bitbucket.org/rgalaxy Galaxy Tools {prog} {timenow()}"  # becomes info
        print(s)
        f.write(f"<div>{s}\n<ol>")
        for data in flist:
            f.write(f'<li><a href="{os.path.split(data)[-1]}">{os.path.split(data)[-1]}</a></li>\n')
        f.write("</ol></div></div></body></html>")


if __name__ == "__main__":
    main()
