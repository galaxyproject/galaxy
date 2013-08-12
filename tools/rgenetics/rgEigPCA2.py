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
import sys,os,time,subprocess,string

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


def timenow():    
   """return current time as a string    """    
   return time.strftime('%d/%m/%Y %H:%M:%S', time.localtime(time.time()))

def readMap(fprefix="example"):
    """
    """
    map = []
    f = file('%s.map' % fprefix,'r')
    for l in f:
        ll = l.strip().split()
        if len(ll) >= 4:
            map.append((ll[:4]))
    return map

def majAllele(adict={'A':20,'C':100}):
    """return commonest allele
    """
    ak = adict.keys()
    if len(ak) == 1: # mono
        return ak[0] # is major allele
    m = None
    maxn = -9
    for k,n in adict.iteritems():
        if n > maxn:
            maxn = n
            m = k
    return m

def convertPedEigen(fprefix="example", linkage=True, logf = None):
    missing = ['N','0','.']
    # eigenstrat codes
    emissval = '9'
    ehet = '1'
    ehom1 = '0'
    ehom2 = '2'
    swapdict = {ehom1:ehom2,ehom2:ehom1,ehet:ehet,emissval:emissval} # if initial ref allele was wrong, use these to swap
    mdict = dict(zip(missing,missing))
    f = file('%s.ped' % fprefix,'r')
    if linkage: # read map file
        map = readMap(fprefix)
        rslist = [x[1] for x in map] # get rs numbers
    else:
        head = f.next().strip()
        rslist = head.split()
    nrs = len(rslist) # number of markers
    e = [[] for x in xrange(nrs)] # marker rows, subject cols
    adicts = [{} for x in xrange(nrs)] # count of alleles in a dict for each marker
    refallele = [None for x in xrange(nrs)] # list of first observed alleles
    nsubj = 0
    indiv = []
    for l in f:
        ll = l.strip().split()
        if len(ll) >= 7:
            nsubj += 1
            sid = '%s_%s' % (ll[0],ll[1])
            gender = 'M'
            if ll[4] == '2':
                gender = 'F'
            status = 'Case'
            if ll[5] == '1':
                status = 'Control'
            indiv.append('%s %s %s' % (sid,gender,status)) # for the ind file
            for snp in xrange(nrs):
                g1,g2 = ll[2*snp + 6],ll[2*snp + 7] # pair of genos
                if mdict.get(g1,None) or mdict.get(g2,None): # one or both missing
                    esnp = emissval # missing value
                else:
                    if not refallele[snp]:
                        refallele[snp] = g1 # first one we saw!
                    for g in (g1,g2):
                        if adicts[snp].get(g,None): # bump
                            adicts[snp][g] += 1
                        else:
                            adicts[snp][g] = 1 # first time
                    if g1 == g2: # hom
                        if g1 == refallele[snp]:
                            esnp = ehom2 # 2 copies of current reference allele
                        else:
                            esnp = ehom1 # no copies
                    else:
                        esnp = ehet # het - always has one copy of reference allele
                e[snp].append(esnp) # append the eigenstrat geno code for this new subject
    for snp in xrange(nrs): # now check to see if reference = major allele
        major = majAllele(adicts[snp])
        if major <> refallele[snp]: # either None or we need to change all the codes
            if major <> None:
                for i in range(nsubj):
                    if e[snp][i] <> emissval:
                        e[snp][i] = swapdict[e[snp][i]]
    res = [''.join(x) for x in e] # convert to rows
    res.append('\n')
    res = '\n'.join(res) # convert to write
    outf = file('%s.eigenstrat' % fprefix,'w')
    outf.write(res)
    outf.close()
    res = '\n'.join(indiv) # the eigenstrat individual file
    outf = file('%s.ind' % fprefix,'w')
    outf.write(res)
    outf.close()


def makePlot(eigpca='test.pca',title='test',pdfname='test',h=10,w=8):
    """
    the eigenvec file has a # row with the eigenvectors, then subject ids, eigenvecs and lastly
    the subject class    
    """
    import rpy
    f = file(eigpca,'r')
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
            pca1.append(v1)
            pca2.append(v2)
    # now have vectors of group,pca1 and pca2
    llist = [x.encode('ascii') for x in glist] # remove label unicode - eesh
    plist = range(1,len(llist)+1) # pch
    clist = range(1,len(llist)+1) # colours - should probably be chosen more carefully
    colvec = [clist[i-1] for i in gvec] # colour for each point
    pchvec = [plist[i-1] for i in gvec] # plot symbol for each point 
    rpy.r.pdf( pdfname, h , w  )
    maint = '%s Eigensoft Plot' % (title)
    rpy.r.par(mai=(1,1,1,0.5))
    #rpy.r("par(xaxs='i',yaxs='i')")
    rpy.r.plot(pca1,pca2,type='p',main=maint, ylab='Second ancestry eigenvector', xlab='First ancestry eigenvector',
               col=gvec,cex=0.8,pch=gvec)
    rpy.r.legend("top",legend=llist,pch=plist,col=clist,title="Sample")
    rpy.r.grid(nx = 10, ny = 10, col = "lightgray", lty = "dotted")
    rpy.r.dev_off()
   

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

    <command interpreter="python2.4">
    rgEigPCA2.py $i.extra_files_path/$i.metadata.base_name "$title" 
    $out_file1 $out_file1.files_path $k $m $t $s $pca
    </command>
    
    """
    if len(sys.argv) < 9:
        print 'Need an input eigenstrat format genotype file root, a title, a temp id and the temp file path for outputs,'
        print ' and the 4 integer tuning parameters k,m,t and s in order. Given that, will run smartpca for eigensoft'
        sys.exit(1)
    else:
        print >> sys.stdout, 'rgEigPCA2.py got %s' % (' '.join(sys.argv))
    skillme = ' %s' % string.punctuation
    trantab = string.maketrans(skillme,'_'*len(skillme))
    ofname = sys.argv[5]        
    progname = os.path.basename(sys.argv[0])
    infile = sys.argv[1]
    title = sys.argv[2].translate(trantab) # must replace all of these for urls containing title
    outfile1 = sys.argv[3]
    newfilepath = sys.argv[4]
    eigen_k = sys.argv[5]
    eigen_m = sys.argv[6]
    eigen_t = sys.argv[7]
    eigen_s = sys.argv[8]
    eigpca = sys.argv[9] # path to new dataset for pca results - for later adjustment
    eigentitle = os.path.join(newfilepath,title)
    explanations=['Principle components','Samples plotted in first 2 eigenvector space','Eigenvalues',
    'Smartpca log (also shown below)']
    rplotname = 'rplot.pdf'
    rplotout = os.path.join(newfilepath,'%s_%s' % (title,rplotname)) # for R plots
    eigenexts = ["pca.xls", rplotname, "eval.xls"] 
    newfiles = ['%s_%s' % (title,x) for x in eigenexts] # produced by eigenstrat
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
    # this is a mess. todo clean up - should each datatype have it's own directory? Yes
    # probably. Then titles are universal - but userId libraries are separate.
    smartscript = '/usr/local/bin/smartpca.perl'
    smartCL = '%s -i %s.eigenstratgeno -a %s.map -b %s.ind -o %s -p %s -e %s -l %s -k %s -m %s -t %s -s %s' % \
          (smartscript,infile, infile, infile, eigenouts[0],eigenouts[1],eigenouts[2],eigenlogf, \
           eigen_k, eigen_m, eigen_t, eigen_s)
    p=subprocess.Popen(smartCL,shell=True,cwd=newfilepath)        
    retval = p.wait() 
    # copy the eigenvector output file needed for adjustment to the user's eigenstrat library directory
    elog = file(os.path.join(newfilepath,eigenlogf),'r').read()
    eeigen = os.path.join(newfilepath,'%s.evec' % eigenouts[0]) # need these for adjusting
    eigpcaRes = file(eeigen,'r').read()
    file(eigpca,'w').write(eigpcaRes)
    makePlot(eigpca=eigpca,pdfname=rplotout,title=title)
    s = '<div>Output from %s run at %s<br>\n' % (progname,timenow())       
    lf.write('<h4>%s</h4>\n' % s)
    s = 'If you need to rerun this analysis, the command line used was\n<pre>%s</pre>\n</div>' % (smartCL)
    lf.write(s)
    lf.write('<div><h4>Click the links below to view Eigenstrat smartpca outputs</h4><br><ol>\n')
    newfiles[0] = '%s.%s' % (newfiles[0],'evec') # smartpca insists..
    for i in range(len(newfiles)):
       lf.write('<li><a href="%s">%s</a></li>\n' % (newfiles[i],explanations[i]))
    lf.write('</ol></div>')
    lf.write('Log %s contents follow below<p>' % eigenlogf)
    lf.write('<pre>%s</pre>' % elog) # the eigenlog
    lf.write('</div></body></html>\n')
    lf.close()


if __name__ == "__main__":
   runEigen()
