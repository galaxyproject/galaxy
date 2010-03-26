"""
# oct 2009 - must make a map file in case later usage requires it...
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
# this is rgLDIndep.py - main task is to decrease LD by filtering high LD pairs
# remove that function from rgClean.py as it may not be needed.
  
"""
import sys,shutil,os,subprocess, glob, string, tempfile, time
from rgutils import plinke, timenow, galhtmlprefix

prog = os.path.split(sys.argv[0])[-1]
myversion = 'January 4 2010'


def pruneld(plinktasks=[] ,cd='./',vclbase = []):
    """
    plink blathers when doing pruning - ignore
    Linkage disequilibrium based SNP pruning
    if a million snps in 3 billion base pairs, have mean 3k spacing
    assume 40-60k of ld in ceu, a window of 120k width is about 40 snps
    so lots more is perhaps less efficient - each window computational cost is
    ON^2 unless the code is smart enough to avoid unecessary computation where
    allele frequencies make it impossible to see ld > the r^2 cutoff threshold
    So, do a window and move forward 20? 
    from the plink docs at http://pngu.mgh.harvard.edu/~purcell/plink/summary.shtml#prune
    
Sometimes it is useful to generate a pruned subset of SNPs that are in approximate linkage equilibrium with each other. This can be achieved via two commands: --indep which prunes based on the variance inflation factor (VIF), which recursively removes SNPs within a sliding window; second, --indep-pairwise which is similar, except it is based only on pairwise genotypic correlation.

Hint The output of either of these commands is two lists of SNPs: those that are pruned out and those that are not. A separate command using the --extract or --exclude option is necessary to actually perform the pruning.

The VIF pruning routine is performed:
plink --file data --indep 50 5 2

will create files

     plink.prune.in
     plink.prune.out

Each is a simlpe list of SNP IDs; both these files can subsequently be specified as the argument for 
a --extract or --exclude command.

The parameters for --indep are: window size in SNPs (e.g. 50), the number of SNPs to shift the 
window at each step (e.g. 5), the VIF threshold. The VIF is 1/(1-R^2) where R^2 is the multiple correlation coefficient for a SNP being regressed on all other SNPs simultaneously. That is, this considers the correlations between SNPs but also between linear combinations of SNPs. A VIF of 10 is often taken to represent near collinearity problems in standard multiple regression analyses (i.e. implies R^2 of 0.9). A VIF of 1 would imply that the SNP is completely independent of all other SNPs. Practically, values between 1.5 and 2 should probably be used; particularly in small samples, if this threshold is too low and/or the window size is too large, too many SNPs may be removed.

The second procedure is performed:
plink --file data --indep-pairwise 50 5 0.5

This generates the same output files as the first version; the only difference is that a 
simple pairwise threshold is used. The first two parameters (50 and 5) are the same as above (window size and step); the third parameter represents the r^2 threshold. Note: this represents the pairwise SNP-SNP metric now, not the multiple correlation coefficient; also note, this is based on the genotypic correlation, i.e. it does not involve phasing.

To give a concrete example: the command above that specifies 50 5 0.5 would a) consider a
window of 50 SNPs, b) calculate LD between each pair of SNPs in the window, b) remove one of a pair of SNPs if the LD is greater than 0.5, c) shift the window 5 SNPs forward and repeat the procedure.

To make a new, pruned file, then use something like (in this example, we also convert the 
standard PED fileset to a binary one):
plink --file data --extract plink.prune.in --make-bed --out pruneddata
    """
    logres = ['## Rgenetics %s: http://rgenetics.org Galaxy Tools rgLDIndep.py Plink pruneLD runner\n' % myversion,]
    for task in plinktasks: # each is a list
        fplog,plog = tempfile.mkstemp()
        sto = open(plog,'w') # to catch the blather
        vcl = vclbase + task
        s = '## ldindep now executing %s\n' % ' '.join(vcl)
        print s
        logres.append(s)
        x = subprocess.Popen(' '.join(vcl),shell=True,stdout=sto,stderr=sto,cwd=cd)
        retval = x.wait()
        sto.close()
        sto = open(plog,'r') # read
        try:
            lplog = sto.readlines()
            lplog = [x for x in lplog if x.find('Pruning SNP') == -1]
            logres += lplog
            logres.append('\n')
        except:
            logres.append('### %s Strange - no std out from plink when running command line\n%s' % (timenow(),' '.join(vcl)))
        sto.close()
        os.unlink(plog) # no longer needed
    return logres



def clean():
    """
    """
    if len(sys.argv) < 14:
        print >> sys.stdout, '## %s expected 14 params in sys.argv, got %d - %s' % (prog,len(sys.argv),sys.argv)
        print >> sys.stdout, """this script will filter a linkage format ped
        and map file containing genotypes. It takes 14 parameters - the plink --f parameter and"
        a new filename root for the output clean data followed by the mind,geno,hwe,maf, mef and mei"
        documented in the plink docs plus the file to be returned to Galaxy
        Called as:
        <command interpreter="python">
        rgLDIndep.py '$input_file.extra_files_path' '$input_file.metadata.base_name' '$title' '$mind'
        '$geno' '$hwe' '$maf' '$mef' '$mei' '$out_file1'
        '$out_file1.extra_files_path'  '$window' '$step' '$r2'
        </command>
        """
        sys.exit(1)
    plog = ['## Rgenetics: http://rgenetics.org Galaxy Tools rgLDIndep.py started %s\n' % timenow()]
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
    winsize = sys.argv[12]
    step = sys.argv[13]
    r2 = sys.argv[14]
    output = os.path.join(outfpath,outfname)
    outpath = os.path.join(outfpath,title)
    outprunepath = os.path.join(outfpath,'ldprune_%s' % title)
    try:
      os.makedirs(outfpath)
    except:
      pass
    bfile = os.path.join(inpath,inbase)
    filterout = os.path.join(outpath,'filtered_%s' % inbase)
    outf = file(outfname,'w')
    outf.write(galhtmlprefix % prog)
    ldin = bfile
    plinktasks = [['--bfile',ldin,'--indep-pairwise %s %s %s' % (winsize,step,r2),'--out',outpath,
    '--mind',mind,'--geno',geno,'--maf',maf,'--hwe',hwe,'--me',me1,me2,],
    ['--bfile',ldin,'--extract %s.prune.in --make-bed --out %s' % (outpath,outpath)],
    ['--bfile',outpath,'--recode --out',outpath]] # make map file - don't really need ped but...
    # subset of ld independent markers for eigenstrat and other requirements
    vclbase = [plinke,'--noweb']
    prunelog = pruneld(plinktasks=plinktasks,cd=outfpath,vclbase = vclbase)
    """This generates the same output files as the first version;
    the only difference is that a simple pairwise threshold is used.
    The first two parameters (50 and 5) are the same as above (window size and step);
    the third parameter represents the r^2 threshold.
    Note: this represents the pairwise SNP-SNP metric now, not the
    multiple correlation coefficient; also note, this is based on the
    genotypic correlation, i.e. it does not involve phasing. 
    """
    plog += prunelog
    flog = '%s.log' % outpath
    flogf = open(flog,'w')
    flogf.write(''.join(plog))
    flogf.write('\n')
    flogf.close()
    globme = os.path.join(outfpath,'*')
    flist = glob.glob(globme)
    flist.sort()
    for i, data in enumerate( flist ):
        outf.write('<li><a href="%s">%s</a></li>\n' % (os.path.split(data)[-1],os.path.split(data)[-1]))
    outf.write('</ol></div>\n')
    outf.write("</div></body></html>")
    outf.close()


if __name__ == "__main__":
    clean()

