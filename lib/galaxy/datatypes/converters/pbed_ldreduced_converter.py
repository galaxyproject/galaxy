# converter for ldreduced rgenetics datatype
# used for grr and eigenstrat - shellfish if we get around to it
#

import os,sys,tempfile,subprocess,time

from galaxy import eggs

prog="pbed_ldreduced_converter.py"

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

plinke = 'plink' 


def timenow():
    """return current time as a string
    """
    return time.strftime('%d/%m/%Y %H:%M:%S', time.localtime(time.time()))


def pruneLD(plinktasks=[],cd='./',vclbase = []):
    """
    """
    fplog,plog = tempfile.mkstemp()
    alog = []
    alog.append('## Rgenetics: http://rgenetics.org Galaxy Tools rgQC.py Plink pruneLD runner\n')
    for task in plinktasks: # each is a list
        vcl = vclbase + task
        sto = file(plog,'w')
        x = subprocess.Popen(' '.join(vcl),shell=True,stdout=sto,stderr=sto,cwd=cd)
        retval = x.wait()
        sto.close()
        try:
            lplog = file(plog,'r').readlines()
            lplog = [x for x in lplog if x.find('Pruning SNP') == -1]
            alog += lplog
            alog.append('\n')
            os.unlink(plog) # no longer needed
        except:
            alog.append('### %s Strange - no std out from plink when running command line\n%s\n' % (timenow(),' '.join(vcl)))
    return alog
 

def makeLDreduced(basename,infpath=None,outfpath=None,plinke='plink',forcerebuild=False,returnFname=False,
        winsize="60", winmove="40", r2thresh="0.1" ):
    """ not there so make and leave in output dir for post job hook to copy back into input extra files path for next time
    """
    ldr = basename # we store ld reduced and thinned data
    ldreduced = os.path.join(outfpath,ldr) # note where this is going
    outbase = os.path.join(outfpath,basename)
    inbase = os.path.join(infpath)
    loglines = []
    ldbedname = '%s.bed' % ldreduced
    bedname = '%s.bed' % basename
    ldbedfn = os.path.join(infpath,ldbedname)
    bedfn = os.path.join(infpath,bedname)
    bmap = os.path.join(infpath,'%s.bim' % basename)
    plinktasks = []
    vclbase = [plinke,'--noweb']
    plinktasks += [['--bfile',inbase,'--indep-pairwise %s %s %s' % (winsize,winmove,r2thresh),'--out %s' % outbase],
            ['--bfile',inbase,'--extract %s.prune.in --make-bed --out %s' % (outbase, outbase)]]
    vclbase = [plinke,'--noweb']
    loglines = pruneLD(plinktasks=plinktasks,cd=outfpath,vclbase = vclbase)

def main():
    """
    need to work with rgenetics composite datatypes
    so in and out are html files with data in extrafiles path
  <command interpreter="python">
   pbed_ldreduced_converter.py '$input1.extra_files_path/$input1.metadata.base_name' '$winsize' '$winmove' '$r2thresh' 
   '$output1' '$output1.files_path' 'plink'    
  </command>
    """
    nparm = 7
    if len(sys.argv) < nparm:
        sys.stderr.write('## %s called with %s - needs %d parameters \n' % (prog,sys.argv,nparm))
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
    except:
        pass
    plink = sys.argv[7]
    makeLDreduced(base_name,infpath=inpedfilepath,outfpath=outfilepath,plinke=plink,forcerebuild=False,returnFname=False,
        winsize=winsize,winmove=winmove,r2thresh=r2thresh)
    f = file(outhtmlname,'w')
    f.write(galhtmlprefix % prog)
    flist = os.listdir(outfilepath)
    s1 = '## Rgenetics: http://rgenetics.org Galaxy Tools %s %s' % (prog,timenow()) # becomes info
    s2 = 'Input %s, winsize=%s, winmove=%s, r2thresh=%s' % (base_name,winsize,winmove,r2thresh)
    print '%s %s' % (s1,s2)
    f.write('<div>%s\n%s\n<ol>' % (s1,s2))
    for i, data in enumerate( flist ):
        f.write('<li><a href="%s">%s</a></li>\n' % (os.path.split(data)[-1],os.path.split(data)[-1]))
    f.write("</div></body></html>")
    f.close()
  

if __name__ == "__main__":
   main()

