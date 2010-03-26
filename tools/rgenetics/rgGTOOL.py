#!/usr/local/bin/python
# hack to run and process a linkage format file into
# the format used by Marchini's SNPTEST imputed case control association
# expects args as  
#         rgGTOOL.py $i $o $discrete $logf $outdir
# ross lazarus 

import sys,math,shutil,subprocess,os,time
from os.path import abspath
imagedir = '/static/rg' # if needed for images
myversion = 'V000.1 August 2007'

def timenow():
    """return current time as a string
    """
    return time.strftime('%d/%m/%Y %H:%M:%S', time.localtime(time.time()))


                
if __name__ == "__main__":
    if len(sys.argv) < 6:
       s = 'rgGTOOL.py needs 5 params - got %s \n' % (sys.argv)
       sys.stderr.write(s) # print >>,s would probably also work?
       sys.exit(0)
    print 'Rgenetics %s http://rgenetics.org SNPTEST Tools, rgGTOOL.py starting at %s' % (myversion,timenow())
    pname = sys.argv[1]
    lpedname = pname.split('.ped')[0] # get file name part
    outname = sys.argv[2]
    discrete = sys.argv[3]
    logf = sys.argv[4]
    outdir = sys.argv[5]
    cdir = os.getcwd()
    me = sys.argv[0]
    mypath = abspath(os.path.join(cdir,me)) # get abs path to this python script
    shpath = abspath(os.path.sep.join(mypath.split(os.path.sep)[:-1]))
    alogf = abspath(os.path.join(cdir,logf)) # absolute paths
    apedf = abspath(os.path.join(cdir,'%s.ped' % lpedname)) # absolute paths
    amapf = abspath(os.path.join(cdir,'%s.map' % lpedname)) # absolute paths
    outg = abspath(os.path.join(outdir,'%s.gen' % outname)) # absolute paths
    outs = abspath(os.path.join(outdir,'%s.sample' % outname)) # absolute paths
    workdir = abspath(os.path.sep.join(mypath.split(os.path.sep)[:-1])) # trim end off './database/files/foo.dat' 
    os.chdir(workdir)
    tlogname = '%s.logtemp' % outname
    sto = file(tlogname,'w')
    sto.write('rgGTOOL.py: called with %s\n' % (sys.argv)) 
    exme = 'gtool'
    vcl = [exme,'-P','--ped',apedf,'--map',amapf,'--discrete_phenotype',discrete,'--og',outg,'--os',outs]
    #'/usr/local/bin/plink','/usr/local/bin/plink',pc1,pc2,pc3)
    #os.spawnv(os.P_WAIT,plink,vcl)
    p=subprocess.Popen(' '.join(vcl),shell=True,stdout=sto)
    retval = p.wait()
    sto.write('rgGTOOL.py after calling %s: vcl=%s\n' % (exme,vcl)) 
    sto.close()
    shutil.move(tlogname,alogf)
    os.chdir(cdir)



