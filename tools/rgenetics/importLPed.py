#!/usr/bin/env python2.4

"""
Challenge is that we need 2 files - a map and a ped
Creates an html file to be used for viewing rgenetics files

<command interpreter="python2.4">
    importLPed.py $outfile $outfile.extra_files_path  $outfile.files_path $pedfile $mapfile $pedurl $mapurl $title $missval $userId
    </command>

    
"""

import sys, os, glob

galhtmlprefix = """<?xml version="1.0" encoding="utf-8" ?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
<meta name="generator" content="Galaxy %s tool output - see http://g2.trac.bx.psu.edu/" />
<title></title>
<link rel="stylesheet" href="/static/style/base.css" type="text/css" />
</head>
<body>
<div class="document">
"""


def saveFile(inf,outname):
    """inf is an http file object
    """
    f = file(outname,'w')
    f.write(inf.read())
    f.close()

    
def getLped(pedf='', pedu='', mapf='', mapu='',import_path=None, basename=None,userId=None):
    """snarf http file data or url contents; name as basename.ped/map and place
    in appropriate user's data directory
    """
    lpedpath = os.path.join(import_path,userId,'lped')
    try:
        os.makedirs(lpedpath)
        print 'made %s' % lpedpath
    except:
        print '%s already exists' % lpedpath # already exists...
    pedfname = os.path.join(lpedpath,'%s.ped' % basename)
    mapfname = os.path.join(lpedpath,'%s.map' % basename)
    if pedf > '':
        saveFile(pedf,pedfname)
    else:
        saveURL(pedu,pedfname)
    if mapf > '':
        saveFile(mapf,mapfname)
    else:
        saveURL(mapu,mapfname)
        


def doImport():
    """ import into one of the new html composite data types for Rgenetics
        Dan Blankenberg with mods by Ross Lazarus 
        October 2007
    """
    progname = sys.argv[0]
    outfile = sys.argv.pop(1)
    extrapath = sys.argv.pop(1)
    filepath = sys.argv.pop(1)
    pedfilename = sys.argv.pop(1).strip()
    mapfilename = sys.argv.pop(1).strip()
    pedurl = sys.argv.pop(1).strip()
    mapurl = sys.argv.pop(1).strip()
    basename = sys.argv.pop(1).strip().replace(' ','_')
    missval = sys.argv.pop(1)
    userId = sys.argv.pop(1)
    if (pedurl > '' or pedfile > '') and (mapurl > '' or mapfile > ''):

    else:
        print >> sys.stderr, 'Must have both a ped and map - either url or file'
        sys.exit(1)
    getLped(pedf=pedfilename, pedu=pedurl, mapf=mapfilename, mapu=mapurl,
            import_path=filepath, basename=basename,userId=userId)
            
    out = open(outfile,'w')
    out.write(galhtmlprefix % progname)
    flist = glob.glob("%s.*" % os.path.join(filepath, basename))
    for i, data in enumerate( flist ):
        print 'writing data %s' % data
        out.write('<li><a href="%s">%s</a></li>\n' % (os.path.split(data)[-1],os.path.split(data)[-1]))
    out.write("</div></body></html>")
    out.close()


if __name__ == "__main__": 
   doImport()

