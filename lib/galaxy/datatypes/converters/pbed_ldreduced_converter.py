# converter for ldreduced rgenetics datatype
# used for grr and eigenstrat - shellfish if we get around to it

import os
import subprocess
import sys
import tempfile
import time

prog = "pbed_ldreduced_converter.py"

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

plinke = "plink"


def timenow():
    """return current time as a string"""
    return time.strftime("%d/%m/%Y %H:%M:%S", time.localtime(time.time()))


def pruneLD(plinktasks=None, cd="./", vclbase=None):
    """ """
    plinktasks = plinktasks or []
    vclbase = vclbase or []
    alog = ["## Rgenetics: http://rgenetics.org Galaxy Tools rgQC.py Plink pruneLD runner\n"]
    with tempfile.NamedTemporaryFile(mode="r+") as plog:
        for task in plinktasks:  # each is a list
            vcl = vclbase + task
            subprocess.check_call(vcl, stdout=plog, stderr=plog, cwd=cd)
            try:
                plog.seek(0)
                lplog = [elem for elem in plog.readlines() if elem.find("Pruning SNP") == -1]
                alog += lplog
                alog.append("\n")
            except Exception:
                alog.append(
                    f"### {timenow()} Strange - no std out from plink when running command line\n{' '.join(vcl)}\n"
                )
    return alog


def makeLDreduced(
    basename,
    infpath=None,
    outfpath=None,
    plinke="plink",
    forcerebuild=False,
    returnFname=False,
    winsize="60",
    winmove="40",
    r2thresh="0.1",
):
    """not there so make and leave in output dir for post job hook to copy back into input extra files path for next time"""
    outbase = os.path.join(outfpath, basename)
    inbase = os.path.join(infpath)
    plinktasks = []
    vclbase = [plinke, "--noweb"]
    plinktasks += [
        ["--bfile", inbase, f"--indep-pairwise {winsize} {winmove} {r2thresh}", f"--out {outbase}"],
        ["--bfile", inbase, f"--extract {outbase}.prune.in --make-bed --out {outbase}"],
    ]
    vclbase = [plinke, "--noweb"]
    pruneLD(plinktasks=plinktasks, cd=outfpath, vclbase=vclbase)


def main():
    """
    need to work with rgenetics composite datatypes
    so in and out are html files with data in extrafiles path

    .. raw:: xml

        <command>
            python '$__tool_directory__/pbed_ldreduced_converter.py' '$input1.extra_files_path/$input1.metadata.base_name' '$winsize' '$winmove' '$r2thresh'
            '$output1' '$output1.files_path' 'plink'
        </command>
    """
    nparm = 7
    if len(sys.argv) < nparm:
        sys.stderr.write("## %s called with %s - needs %d parameters \n" % (prog, sys.argv, nparm))
        sys.exit(1)
    inpedfilepath = sys.argv[1]
    base_name = os.path.split(inpedfilepath)[-1]
    winsize = sys.argv[2]
    winmove = sys.argv[3]
    r2thresh = sys.argv[4]
    outhtmlname = sys.argv[5]
    outfilepath = sys.argv[6]
    try:
        os.makedirs(outfilepath)
    except Exception:
        pass
    plink = sys.argv[7]
    makeLDreduced(
        base_name,
        infpath=inpedfilepath,
        outfpath=outfilepath,
        plinke=plink,
        forcerebuild=False,
        returnFname=False,
        winsize=winsize,
        winmove=winmove,
        r2thresh=r2thresh,
    )
    flist = os.listdir(outfilepath)
    with open(outhtmlname, "w") as f:
        f.write(galhtmlprefix % prog)
        s1 = f"## Rgenetics: http://rgenetics.org Galaxy Tools {prog} {timenow()}"  # becomes info
        s2 = f"Input {base_name}, winsize={winsize}, winmove={winmove}, r2thresh={r2thresh}"
        print(f"{s1} {s2}")
        f.write(f"<div>{s1}\n{s2}\n<ol>")
        for data in flist:
            f.write(f'<li><a href="{os.path.split(data)[-1]}">{os.path.split(data)[-1]}</a></li>\n')
        f.write("</div></body></html>")


if __name__ == "__main__":
    main()
