"""
run smartpca

This uses galaxy code developed by Dan to deal with
arbitrary output files using an html dataset with it's own
subdirectory containing the arbitrary files
We create that html file and add all the links we need

Note that we execute the smartpca.perl program in the output subdirectory
to avoid having to clear out the job directory after running

Code to convert linkage format ped files into eigenstratgeno format is left here
in case we decide to autoconvert

Added a plot in R with better labels than the default eigensoft plot december 26 2007

DOCUMENTATION OF smartpca program:

smartpca runs Principal Components Analysis on input genotype data and
  outputs principal components (eigenvectors) and eigenvalues.
  The method assumes that samples are unrelated.  (However, a small number
  of cryptically related individuals is usually not a problem in practice
  as they will typically be discarded as outliers.)

5 different input formats are supported.  See ../CONVERTF/README
for documentation on using the convertf program to convert between formats.

The syntax of smartpca is "../bin/smartpca -p parfile".  We illustrate
how parfile works via a toy example (see example.perl in this directory).
This example takes input in EIGENSTRAT format.  The syntax of how to take input
in other formats is analogous to the convertf program, see ../CONVERTF/README.

The smartpca program prints various statistics to standard output.
To redirect this information to a file, change the above syntax to
"../bin/smartpca -p parfile >logfile".  For a description of these
statistics, see the documentation file smartpca.info in this directory.

Estimated running time of the smartpca program is
  2.5e-12 * nSNP * NSAMPLES^2 hours            if not removing outliers.
  2.5e-12 * nSNP * NSAMPLES^2 hours * (1+m)    if m outlier removal iterations.
Thus, under the default of up to 5 outlier removal iterations, running time is
  up to 1.5e-11 * nSNP * NSAMPLES^2 hours.

------------------------------------------------------------------------

DESCRIPTION OF EACH PARAMETER in parfile for smartpca:

genotypename: input genotype file (in any format: see ../CONVERTF/README)
snpname:      input snp file      (in any format: see ../CONVERTF/README)
indivname:    input indiv file    (in any format: see ../CONVERTF/README)
evecoutname:  output file of eigenvectors.  See numoutevec parameter below.
evaloutname:  output file of all eigenvalues

OPTIONAL PARAMETERS:

numoutevec:     number of eigenvectors to output.  Default is 10.
numoutlieriter: maximum number of outlier removal iterations.
  Default is 5.  To turn off outlier removal, set this parameter to 0.
numoutlierevec: number of principal components along which to
  remove outliers during each outlier removal iteration.  Default is 10.
outliersigmathresh: number of standard deviations which an individual must
  exceed, along one of the top (numoutlierevec) principal components, in
  order for that individual to be removed as an outlier.  Default is 6.0.
outlieroutname: output logfile of outlier individuals removed. If not specified,
  smartpca will print this information to stdout, which is the default.
usenorm: Whether to normalize each SNP by a quantity related to allele freq.
  Default is YES.  (When analyzing microsatellite data, should be set to NO.
  See Patterson et al. 2006.)
altnormstyle: Affects very subtle details in normalization formula.
  Default is YES (normalization formulas of Patterson et al. 2006)
  To match EIGENSTRAT (normalization formulas of Price et al. 2006), set to NO.
missingmode: If set to YES, then instead of doing PCA on # reference alleles,
  do PCA on whether each data point is missing or nonmissing.  Default is NO.
  May be useful for detecting informative missingness (Clayton et al. 2005).
nsnpldregress: If set to a positive integer, then LD correction is turned on,
  and input to PCA will be the residual of a regression involving that many
  previous SNPs, according to physical location.  See Patterson et al. 2006.
  Default is 0 (no LD correction).  If desiring LD correction, we recommend 2.
maxdistldregress: If doing LD correction, this is the maximum genetic distance
  (in Morgans) for previous SNPs used in LD correction.  Default is no maximum.
poplistname:   If wishing to infer eigenvectors using only individuals from a
  subset of populations, and then project individuals from all populations
  onto those eigenvectors, this input file contains a list of population names,
  one population name per line, which will be used to infer eigenvectors.
  It is assumed that the population of each individual is specified in the
  indiv file.  Default is to use individuals from all populations.
phylipoutname: output file containing an fst matrix which can be used as input
  to programs in the PHYLIP package, such as the "fitch" program for
  constructing phylogenetic trees.
noxdata:    if set to YES, all SNPs on X chr are excluded from the data set.
  The smartpca default for this parameter is YES, since different variances
  for males vs. females on X chr may confound PCA analysis.
nomalexhet: if set to YES, any het genotypes on X chr for males are changed
  to missing data.  The smartpca default for this parameter is YES.
badsnpname: specifies a list of SNPs which should be excluded from the data set.
  Same format as example.snp.  Cannot be used if input is in
  PACKEDPED or PACKEDANCESTRYMAP format.
popsizelimit: If set to a positive integer, the result is that only the first
  popsizelimit individuals from each population will be included in the
  analysis. It is assumed that the population of each individual is specified
  in the indiv file.  Default is to use all individuals in the analysis.

The next 5 optional parameters allow the user to output genotype, snp and
  indiv files which will be identical to the input files except that:
    Any individuals set to Ignore in the input indiv file will be
      removed from the data set (see ../CONVERTF/README)
    Any data excluded or set to missing based on noxdata, nomalexhet and
      badsnpname parameters (see above) will be removed from the data set.
    The user may decide to output these files in any format.
outputformat:    ANCESTRYMAP,  EIGENSTRAT, PED, PACKEDPED or PACKEDANCESTRYMAP
genotypeoutname: output genotype file
snpoutname:      output snp file
indivoutname:    output indiv file
outputgroup: see documentation in ../CONVERTF/README
"""
import sys,os,time,subprocess,string,glob
from rgutils import RRun, galhtmlprefix, galhtmlpostfix, timenow, smartpca, rexe, plinke
verbose = False

def makePlot(eigpca='test.pca',title='test',pdfname='test.pdf',h=8,w=10,nfp=None,rexe=''):
    """
    the eigenvec file has a # row with the eigenvectors, then subject ids, eigenvecs and lastly
    the subject class
    Rpy not being used here. Write a real R script and run it. Sadly, this means putting numbers
    somewhere - like in the code as monster R vector constructor c(99.3,2.14) strings
    At least you have the data and the analysis in one single place. Highly reproducible little
    piece of research.
    """
    debug=False
    f = file(eigpca,'r')
    R = []
    if debug:
      R.append('sessionInfo()')
      R.append("print('dir()=:')")
      R.append('dir()')
      R.append("print('pdfname=%s')" % pdfname)
    gvec = []
    pca1 = []
    pca2 = []
    groups = {}
    glist = [] # list for legend
    ngroup = 1 # increment for each new group encountered for pch vector
    for n,row in enumerate(f):
        if n > 1:
            rowlist = row.strip().split()
            group = rowlist[-1]
            v1 = rowlist[1]
            v2 = rowlist[2]
            try:
                v1 = float(v1)
            except:
                v1 = 0.0
            try:
                v2 = float(v2)
            except:
                v2 = 0.0
            if not groups.get(group,None):
                groups[group] = ngroup
                glist.append(group)
                ngroup += 1 # for next group
            gvec.append(groups[group]) # lookup group number
            pca1.append('%f' % v1)
            pca2.append('%f' % v2)
    # now have vectors of group,pca1 and pca2
    llist = [x.encode('ascii') for x in glist] # remove label unicode - eesh
    llist = ['"%s"' % x for x in llist] # need to quote for R
    R.append('llist=c(%s)' % ','.join(llist))

    plist = range(2,len(llist)+2) # pch - avoid black circles
    R.append('glist=c(%s)' % ','.join(['%d' % x for x in plist]))
    pgvec = ['%d' % (plist[i-1]) for i in gvec] # plot symbol/colour for each point
    R.append("par(lab=c(10,10,10))") # so our grid is denser than the default 5
    R.append("par(mai=c(1,1,1,0.5))")
    maint = title
    R.append('pdf("%s",h=%d,w=%d)' % (pdfname,h,w))
    R.append("par(lab=c(10,10,10))")
    R.append('pca1 = c(%s)' % ','.join(pca1))
    R.append('pca2 = c(%s)' % ','.join(pca2))
    R.append('pgvec = c(%s)' % ','.join(pgvec))
    s = "plot(pca1,pca2,type='p',main='%s', ylab='Second ancestry eigenvector'," % maint
    s += "xlab='First ancestry eigenvector',col=pgvec,cex=0.8,pch=pgvec)"
    R.append(s)
    R.append('legend("top",legend=llist,pch=glist,col=glist,title="Sample")')
    R.append('grid(nx = 10, ny = 10, col = "lightgray", lty = "dotted")')
    R.append('dev.off()')
    R.append('png("%s.png",h=%d,w=%d,units="in",res=72)' % (pdfname,h,w))
    s = "plot(pca1,pca2,type='p',main='%s', ylab='Second ancestry eigenvector'," % maint
    s += "xlab='First ancestry eigenvector',col=pgvec,cex=0.8,pch=pgvec)"
    R.append(s)
    R.append('legend("top",legend=llist,pch=glist,col=glist,title="Sample")')
    R.append('grid(nx = 10, ny = 10, col = "lightgray", lty = "dotted")')
    R.append('dev.off()')
    rlog,flist = RRun(rcmd=R,title=title,outdir=nfp)
    print >> sys.stdout, '\n'.join(R)
    print >> sys.stdout, rlog


def getfSize(fpath,outpath):
    """
    format a nice file size string
    """
    size = ''
    fp = os.path.join(outpath,fpath)
    if os.path.isfile(fp):
        n = float(os.path.getsize(fp))
        if n > 2**20:
            size = ' (%1.1f MB)' % (n/2**20)
        elif n > 2**10:
            size = ' (%1.1f KB)' % (n/2**10)
        elif n > 0:
            size = ' (%d B)' % (int(n))
    return size


def runEigen():
    """ run the smartpca prog - documentation follows

    smartpca.perl -i fakeped_100.eigenstratgeno -a fakeped_100.map -b fakeped_100.ind -p fakeped_100 -e fakeped_100.eigenvals -l
        fakeped_100.eigenlog -o fakeped_100.eigenout

DOCUMENTATION OF smartpca.perl program:

This program calls the smartpca program (see ../POPGEN/README).
For this to work, the bin directory containing smartpca MUST be in your path.
See ./example.perl for a toy example.

../bin/smartpca.perl
-i example.geno  : genotype file in EIGENSTRAT format (see ../CONVERTF/README)
-a example.snp   : snp file   (see ../CONVERTF/README)
-b example.ind   : indiv file (see ../CONVERTF/README)
-k k             : (Default is 10) number of principal components to output
-o example.pca   : output file of principal components.  Individuals removed
                   as outliers will have all values set to 0.0 in this file.
-p example.plot  : prefix of output plot files of top 2 principal components.
                   (labeling individuals according to labels in indiv file)
-e example.eval  : output file of all eigenvalues
-l example.log   : output logfile
-m maxiter       : (Default is 5) maximum number of outlier removal iterations.
                   To turn off outlier removal, set -m 0.
-t topk          : (Default is 10) number of principal components along which
                   to remove outliers during each outlier removal iteration.
-s sigma         : (Default is 6.0) number of standard deviations which an
                   individual must exceed, along one of topk top principal
                   components, in order to be removed as an outlier.

    now uses https://www.bx.psu.edu/cgi-bin/trac.cgi/galaxy/changeset/1832

All files can be viewed however, by making links in the primary (HTML) history item like:
<img src="display_child?parent_id=2&designation=SomeImage?" alt="Some Image"/>
<a href="display_child?parent_id=2&designation=SomeText?">Some Text</a>

    <command interpreter="python">
    rgEigPCA.py "$i.extra_files_path/$i.metadata.base_name" "$title" "$out_file1"
    "$out_file1.files_path" "$k" "$m" "$t" "$s" "$pca"
    </command>

    """
    if len(sys.argv) < 9:
        print 'Need an input genotype file root, a title, a temp id and the temp file path for outputs,'
        print ' and the 4 integer tuning parameters k,m,t and s in order. Given that, will run smartpca for eigensoft'
        sys.exit(1)
    else:
        print >> sys.stdout, 'rgEigPCA.py got %s' % (' '.join(sys.argv))
    skillme = ' %s' % string.punctuation
    trantab = string.maketrans(skillme,'_'*len(skillme))
    ofname = sys.argv[5]
    progname = os.path.basename(sys.argv[0])
    infile = sys.argv[1]
    infpath,base_name = os.path.split(infile) # now takes precomputed or autoconverted ldreduced dataset
    title = sys.argv[2].translate(trantab) # must replace all of these for urls containing title
    outfile1 = sys.argv[3]
    newfilepath = sys.argv[4]
    try:
       os.mkdirs(newfilepath)
    except:
       pass
    op = os.path.split(outfile1)[0]
    try: # for test - needs this done
        os.makedirs(op)
    except:
        pass
    eigen_k = sys.argv[5]
    eigen_m = sys.argv[6]
    eigen_t = sys.argv[7]
    eigen_s = sys.argv[8]
    eigpca = sys.argv[9] # path to new dataset for pca results - for later adjustment
    eigentitle = os.path.join(newfilepath,title)
    explanations=['Samples plotted in first 2 eigenvector space','Principle components','Eigenvalues',
    'Smartpca log (contents shown below)']
    rplotname = 'PCAPlot.pdf'
    eigenexts = [rplotname, "pca.xls", "eval.xls"]
    newfiles = ['%s_%s' % (title,x) for x in eigenexts] # produced by eigenstrat
    rplotout = os.path.join(newfilepath,newfiles[0]) # for R plots
    eigenouts = [x for x in newfiles]
    eigenlogf = '%s_log.txt' % title
    newfiles.append(eigenlogf) # so it will also appear in the links
    lfname = outfile1
    lf = file(lfname,'w')
    lf.write(galhtmlprefix % progname)
    try:
        os.makedirs(newfilepath)
    except:
        pass
    smartCL = '%s -i %s.bed -a %s.bim -b %s.fam -o %s -p %s -e %s -l %s -k %s -m %s -t %s -s %s' % \
          (smartpca,infile, infile, infile, eigenouts[1],'%s_eigensoftplot.pdf' % title,eigenouts[2],eigenlogf, \
           eigen_k, eigen_m, eigen_t, eigen_s)
    env = os.environ
    p=subprocess.Popen(smartCL,shell=True,cwd=newfilepath)
    retval = p.wait()
    # copy the eigenvector output file needed for adjustment to the user's eigenstrat library directory
    elog = file(os.path.join(newfilepath,eigenlogf),'r').read()
    eeigen = os.path.join(newfilepath,'%s.evec' % eigenouts[1]) # need these for adjusting
    try:
        eigpcaRes = file(eeigen,'r').read()
    except:
        eigpcaRes = ''
    file(eigpca,'w').write(eigpcaRes)
    makePlot(eigpca=eigpca,pdfname=newfiles[0],title=title,nfp=newfilepath,rexe=rexe)
    s = 'Output from %s run at %s<br/>\n' % (progname,timenow())
    lf.write('<h4>%s</h4>\n' % s)
    lf.write('newfilepath=%s, rexe=%s' % (newfilepath,rexe))
    lf.write('(click on the image below to see a much higher quality PDF version)')
    thumbnail = '%s.png' % newfiles[0] # foo.pdf.png - who cares?
    if os.path.exists(os.path.join(newfilepath,thumbnail)):
        lf.write('<table border="0" cellpadding="10" cellspacing="10"><tr><td>\n')
        lf.write('<a href="%s"><img src="%s" alt="%s" hspace="10" align="left" /></a></td></tr></table><br/>\n' \
            % (newfiles[0],thumbnail,explanations[0]))
    allfiles = os.listdir(newfilepath)
    allfiles.sort()
    sizes = [getfSize(x,newfilepath) for x in allfiles]
    lallfiles = ['<li><a href="%s">%s %s</a></li>\n' % (x,x,sizes[i]) for i,x in enumerate(allfiles)] # html list
    lf.write('<div class="document">All Files:<ol>%s</ol></div>' % ''.join(lallfiles))
    lf.write('<div class="document">Log %s contents follow below<p/>' % eigenlogf)
    lf.write('<pre>%s</pre></div>' % elog) # the eigenlog
    s = 'If you need to rerun this analysis, the command line used was\n%s\n<p/>' % (smartCL)
    lf.write(s)
    lf.write(galhtmlpostfix) # end galhtmlprefix div
    lf.close()


if __name__ == "__main__":
   runEigen()
