#!/usr/bin/env python2.4

"""
Creates an html file to be used for viewing rgenetics files

   <command interpreter="python2.4">rgenetics_import.py $file_type_dir $base_name $output </command>



"""

import sys, os, glob, subprocess

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

def getMissval(inroot=''):
   """ 
   read some lines...ugly hack - try to guess missing value
   should be N or 0 but might be . or -
   """
   commonmissvals = {'N':'N','0':'0','n':'n','9':'9','-':'-','.':'.'}
   f = file(inroot,'r')
   missval = None
   while missval == None: # doggedly continue until we solve the mystery
        try:
          l = f.readline()
        except:
          missval = '0'
          break
        ll = l.split()[6:] # ignore pedigree stuff
        for c in ll:
            if commonmissvals.get(c,None):
               missval = c       
               break
   if not missval: 
       missval = '0' # punt
   return missval

def doConvert(destdir='',sourcedir='',basename='',logf='',missval='0'):
    """
echo 'Rgenetics http://rgenetics.org Galaxy Tools ped file importer'
echo "CL = $1 $2 $3 $4 $5"
echo 'called as importPed.sh $i $filelib_library_path $o $logfile $m $userId $userEmail'
echo "Calling Plink to import $1"
mkdir $4
echo 'Rgenetics http://rgenetics.org Galaxy Tools ped file importer'
echo "CL = $1 $2 $3 $4 $5"
echo 'called as importPed.sh $i $filelib_library_path $o $logfile $m $userId $userEmail'
echo "Calling Plink to import $1"
mkdir $4
cp $1/$2.map $4/
plink --file $1/$2 --make-bed --out $4/$2 --missing-genotype $5 > $3[rerla@hg rgenetics]$
    """
    try:
        os.makedirs(destdir)
    except:
        pass
    inroot = os.path.join(sourcedir,basename)
    outroot = os.path.join(destdir,basename)
    src = '%s.%s' % (inroot,'map')
    cl = 'cp %s %s' % (src,destdir)
    p = subprocess.Popen(cl,shell=True)
    retval = p.wait() # copy map to lped
    cl = 'plink --file %s --make-bed --out %s --missing-genotype %s > %s' % (inroot,outroot,missval,logf)
    p = subprocess.Popen(cl,shell=True)
    retval = p.wait() # run plink
    return
   

def doImport():
    """ convert lped into pbed and import into one of the new html composite data types for Rgenetics
        Dan Blankenberg with mods by Ross Lazarus 
        October 2007

   <command interpreter="python2.4">rgLpedPbed.py $input_path $output $missval</command> 
   <command interpreter="python2.4">
     rgLpedPbed.py $i.extra_files_path "$i.metadata.base_name" $outfile $outfile.files_path $missval
   </command>
    """
    progname = sys.argv[0]
    import_path = sys.argv.pop(1)
    base_name = sys.argv.pop(1)
    outfile = sys.argv.pop(1)
    outfilefpath = sys.argv.pop(1)
    missval = sys.argv.pop(1)
    export_path = os.path.join(os.path.split(import_path)[0],'pbed')
    try: # get a bigger hammer 
      os.makedirs(export_path)
    except:
      pass # bah. ugh. please fix me with a proper os test
    logf = file(outfile,'w')
    doConvert(destdir=export_path,sourcedir=import_path,basename=base_name,logf=logf,missval=missval)
    logf.close()
    plinklog = file(outfile,'r').read()
    out = file(outfile,'w') # start again
    out.write(galhtmlprefix % progname)
    flist = glob.glob(os.path.join(export_path, '%s.*' % (base_name))) # all the files matching basename
    for i, data in enumerate( flist ):
        out.write('<li><a href="%s">%s</a></li>\n' % (os.path.split(data)[-1],os.path.split(data)[-1]))
    out.write('<h3>Plink log follows:</h3><pre>')
    out.write(plinklog)
    out.write('</pre><br>')
    out.write("</div></body></html>")
    out.close()


if __name__ == "__main__": 
   doImport()

