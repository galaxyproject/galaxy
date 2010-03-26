"""
# galaxy tool xml files can define a galaxy supplied output filename
# that must be passed to the tool and used to return output
# here, the plink log file is copied to that file and removed
# took a while to figure this out!
# use exec_before_job to give files sensible names
#
# ross april 14 2007
# plink cleanup script
# ross lazarus March 2007 for camp illumina whole genome data
# note problems with multiple commands being ignored - eg --freq --missing --mendel 
# only the first seems to get done...
#
##Summary statistics versus inclusion criteria
##
##Feature                         As summary statistic    As inclusion criteria
##Missingness per individual      --missing               --mind N
##Missingness per marker          --missing               --geno N        
##Allele frequency                --freq                  --maf N
##Hardy-Weinberg equilibrium      --hardy                 --hwe N
##Mendel error rates              --mendel                --me N M
#
# call as plinkClean.py $i $o $mind $geno $hwe $maf $mef $mei $outfile 
# note plinkClean_code.py does some renaming before the job starts

    
    <command interpreter="python2.4">
        rgClean.py '$input_file.extra_files_path' '$input_file.metadata.base_name' '$title' '$mind' '$geno' '$hwe' '$maf' 
        '$mef' '$mei' '$out_file1' '$out_file1.files_path' '$userId' 
 
  
"""
import sys,shutil,os,subprocess, glob, string, tempfile, time
from rgutils import galhtmlprefix, timenow, plinke
prog = os.path.split(sys.argv[0])[-1]
myversion = 'January 4 2010'
verbose=False


def fixoutaff(outpath='',newaff='1'):
    """ quick way to create test data sets - set all aff to 1 or 2 for
    some hapmap data and then merge
    [rerla@beast galaxy]$ head tool-data/rg/library/pbed/affyHM_CEU.fam
    1341 14 0 0 2 1
    1341 2 13 14 2 1
    1341 13 0 0 1 1
    1340 9 0 0 1 1
    1340 10 0 0 2 1
    """
    nchanged = 0
    fam = '%s.fam' % outpath
    famf = open(fam,'r')
    fl = famf.readlines()
    famf.close()
    for i,row in enumerate(fl):
        lrow = row.split()
        if lrow[-1] <> newaff:
            lrow[-1] = newaff
            fl[i] = ' '.join(lrow)
            fl[i] += '\n'
            nchanged += 1
    fo = open(fam,'w')
    fo.write(''.join(fl))
    fo.close()
    return nchanged
            


def clean():
    """
    """
    if len(sys.argv) < 16:
        print >> sys.stdout, '## %s expected 12 params in sys.argv, got %d - %s' % (prog,len(sys.argv),sys.argv)
        print >> sys.stdout, """this script will filter a linkage format ped
        and map file containing genotypes. It takes 14 parameters - the plink --f parameter and"
        a new filename root for the output clean data followed by the mind,geno,hwe,maf, mef and mei"
        documented in the plink docs plus the file to be returned to Galaxy
        called as:
        <command interpreter="python">
        rgClean.py '$input_file.extra_files_path' '$input_file.metadata.base_name' '$title' '$mind'
        '$geno' '$hwe' '$maf' '$mef' '$mei' '$out_file1' '$out_file1.files_path'
        '$relfilter' '$afffilter' '$sexfilter' '$fixaff'
        </command>

        """
        sys.exit(1)
    plog = []
    inpath = sys.argv[1]
    inbase = sys.argv[2]
    killme = string.punctuation + string.whitespace
    trantab = string.maketrans(killme,'_'*len(killme))
    title = sys.argv[3].translate(trantab)
    mind = sys.argv[4]
    geno = sys.argv[5]
    hwe = sys.argv[6]
    maf = sys.argv[7]
    me1 = sys.argv[8]
    me2 = sys.argv[9]
    outfname = sys.argv[10]
    outfpath = sys.argv[11]
    relf = sys.argv[12]
    afff = sys.argv[13]
    sexf = sys.argv[14]
    fixaff = sys.argv[15]
    output = os.path.join(outfpath,outfname)
    outpath = os.path.join(outfpath,title)
    outprunepath = os.path.join(outfpath,'ldprune_%s' % title)
    try:
      os.makedirs(outfpath)
    except:
      pass
    bfile = os.path.join(inpath,inbase)
    outf = file(outfname,'w')
    vcl = [plinke,'--noweb','--bfile',bfile,'--make-bed','--out',
          outpath,'--set-hh-missing','--mind',mind,
          '--geno',geno,'--maf',maf,'--hwe',hwe,'--me',me1,me2]
    # yes - the --me parameter takes 2 values - mendels per snp and per family
    if relf == 'oo': # plink filters are what they leave...
        vcl.append('--filter-nonfounders') # leave only offspring
    elif relf == 'fo':
        vcl.append('--filter-founders')
    if afff == 'affonly':
        vcl.append('--filter-controls')
    elif relf == 'unaffonly':
        vcl.append('--filter-cases')
    if sexf == 'fsex':
        vcl.append('--filter-females')
    elif relf == 'msex':
        vcl.append('--filter-males')        
    p=subprocess.Popen(' '.join(vcl),shell=True,cwd=outfpath)
    retval = p.wait()
    plog.append('%s started, called as %s' % (prog,' '.join(sys.argv)))
    outf.write(galhtmlprefix % prog)
    outf.write('<ul>\n')
    plogf = '%s.log' % os.path.join(outfpath,title)
    try:
        plogl = file(plogf,'r').readlines()
        plog += [x.strip() for x in plogl]
    except:
        plog += ['###Cannot open plink log file %s' % plogf,]
    # if fixaff, want to 'fix' the fam file
    if fixaff <> '0':
        nchanged = fixoutaff(outpath=outpath,newaff=fixaff)
        plog += ['## fixaff was requested  %d subjects affection status changed to %s' % (nchanged,fixaff)] 
    pf = file(plogf,'w')
    pf.write('\n'.join(plog))
    pf.close()
    globme = os.path.join(outfpath,'*')
    flist = glob.glob(globme)
    flist.sort()
    for i, data in enumerate( flist ):
        outf.write('<li><a href="%s">%s</a></li>\n' % (os.path.split(data)[-1],os.path.split(data)[-1]))
    outf.write('</ul>\n')
    outf.write("</ul></br></div></body></html>")
    outf.close()


if __name__ == "__main__":
    clean()

