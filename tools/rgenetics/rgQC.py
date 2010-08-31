# oct 15 rpy replaced - temp fix until we get gnuplot working 
# rpy deprecated - replace with RRun
# fixes to run functional test! oct1 2009
# needed to expand our path with os.path.realpath to get newpath working with
# all the fancy pdfnup stuff
# and a fix to pruneld to write output to where it should be
# smallish data in test-data/smallwga in various forms
# python ../tools/rgenetics/rgQC.py -i smallwga -o smallwga -s smallwga/smallwga.html -p smallwga
# child files are deprecated and broken as at july 19 2009
# need to move them to the html file extrafiles path
# found lots of corner cases with some illumina data where cnv markers were
# included
# and where affection status was all missing !
# added links to tab files showing worst 1/keepfrac markers and subjects
# ross lazarus january 2008
#
# added named parameters
# to ensure no silly slippages if non required parameter in the most general case
# some potentially useful things here reusable in complex scripts
# with lots'o'html (TM)
# aug 17 2007 rml
#
# added marker and subject and parenting april 14 rml
# took a while to get the absolute paths right for all the file munging
# as of april 16 seems to work..
# getting galaxy to serve images in html reports is a little tricky
# we don't want QC reports to be dozens of individual files, so need
# to use the url /static/rg/... since galaxy's web server will happily serve images
# from there
# galaxy passes output files as relative paths
# these have to be munged by rgQC.py before calling this
# galaxy will pass in 2 file names - one for the log
# and one for the final html report
# of the form './database/files/dataset_66.dat'
# we need to be working in that directory so our plink output files are there
# so these have to be munged by rgQC.py before calling this
# note no ped file passed so had to remove the -l option
# for plinkParse.py that makes a heterozygosity report from the ped
# file - needs fixing...
# new: importing manhattan/qqplot plotter
# def doManQQ(input_fname,chrom_col,offset_col,pval_cols,title,grey,ctitle,outdir):
#    """ draw a qq for pvals and a manhattan plot if chrom/offset <> 0
#    contains some R scripts as text strings - we substitute defaults into the calls
#    to make them do our bidding - and save the resulting code for posterity
#    this can be called externally, I guess...for QC eg?
#    """
#
#    rcmd = '%s%s' % (rcode,rcode2 % (input_fname,chrom_col,offset_col,pval_cols,title,grey))
#    rlog,flist = RRun(rcmd=rcmd,title=ctitle,outdir=outdir)
#    return rlog,flist
  

from optparse import OptionParser

import sys,os,shutil, glob, math, subprocess, time, operator, random, tempfile, copy, string
from os.path import abspath
from rgutils import galhtmlprefix, galhtmlpostfix, RRun, timenow, plinke, rexe, runPlink, pruneLD
import rgManQQ

prog = os.path.split(sys.argv[0])[1]
vers = '0.4 april 2009 rml'
idjoiner = '_~_~_' # need something improbable..
# many of these may need fixing for a new install

myversion = vers
keepfrac = 20 # fraction to keep after sorting by each interesting value

missvals = {'0':'0','N':'N','-9':'-9','-':'-'} # fix me if these change!

mogresize = "x300" # this controls the width for jpeg thumbnails



            
def makePlots(markers=[],subjects=[],newfpath='.',basename='test',nbreaks='20',nup=3,height=10,width=8,rgbin=''):
    """
    marker rhead = ['snp','chrom','maf','a1','a2','missfrac',
    'p_hwe_all','logp_hwe_all','p_hwe_unaff','logp_hwe_unaff','N_Mendel']
    subject rhead = ['famId','iId','FracMiss','Mendel_errors','Ped_sex','SNP_sex','Status','Fest']
    """

        
    def rHist(plotme=[],outfname='',xlabname='',title='',basename='',nbreaks=50):
        """   rHist <- function(plotme,froot,plotname,title,mfname,nbreaks=50)
        # generic histogram and vertical boxplot in a 3:1 layout
        # returns the graphic file name for inclusion in the web page
        # broken out here for reuse
        # ross lazarus march 2007
        """
        screenmat = (1,2,1,2) # create a 2x2 cabvas
        widthlist = (80,20) # change to 4:1 ratio for histo and boxplot
        rpy.r.pdf( outfname, height , width  )
        #rpy.r.layout(rpy.r.matrix(rpy.r.c(1,1,1,2), 1, 4, byrow = True)) # 3 to 1 vertical plot
        m = rpy.r.matrix((1,1,1,2),nrow=1,ncol=4,byrow=True)
        # in R, m = matrix(c(1,2),nrow=1,ncol=2,byrow=T)
        rpy.r("layout(matrix(c(1,1,1,2),nrow=1,ncol=4,byrow=T))") # 4 to 1 vertical plot
        maint = 'QC for %s - %s' % (basename,title)
        rpy.r.hist(plotme,main=maint, xlab=xlabname,breaks=nbreaks,col="maroon",cex=0.8)
        rpy.r.boxplot(plotme,main='',col="maroon",outline=False)
        rpy.r.dev_off()

    def rCum(plotme=[],outfname='',xlabname='',title='',basename='',nbreaks=100):
        """
        Useful to see what various cutoffs yield - plot percentiles
        """
        n = len(plotme)
        maxveclen = 1000.0 # for reasonable pdf sizes!
        yvec = copy.copy(plotme)
        # arrives already in decending order of importance missingness or mendel count by subj or marker
        xvec = range(n)
        xvec = [100.0*(n-x)/n for x in xvec] # convert to centile
        # now have half a million markers eg - too many to plot all for a pdf - sample to get 10k or so points
        if n > maxveclen: # oversample part of the distribution
            always = min(1000,n/20) # oversample smaller of lowest few hundred items or 5%
            skip = int(n/maxveclen) # take 1 in skip to get about maxveclen points
            samplei = [i for i in range(n) if (i % skip == 0) or (i < always)] # always oversample first sorted values
            yvec = [yvec[i] for i in samplei] # always get first and last
            xvec = [xvec[i] for i in samplei] # always get first and last
        # need to supply the x axis or else rpy prints the freaking vector on the pdf - go figure
        rpy.r.pdf( outfname, height , width  )
        maint = 'QC for %s - %s' % (basename,title)
        rpy.r("par(lab=c(10,10,10))") # so our grid is denser than the default 5
        rpy.r.plot(xvec,yvec,type='p',main=maint, ylab=xlabname, xlab='Sample Percentile',col="maroon",cex=0.8)
        rpy.r.grid(nx = None, ny = None, col = "lightgray", lty = "dotted")
        rpy.r.dev_off()

    def rQQ(plotme=[], outfname='fname',title='title',xlabname='Sample',basename=''):
        """
        y is data for a qq plot and ends up on the x axis go figure
        if sampling, oversample low values - all the top 1% ?
        this version called with -log10 transformed hwe
        """
        nrows = len(plotme)
        fn = float(nrows)
        xvec = [-math.log10(x/fn) for x in range(1,(nrows+1))]
        mx = [0,math.log10(fn)] # if 1000, becomes 3 for the null line
        maxveclen = 3000
        yvec = copy.copy(plotme)
        if nrows > maxveclen:
            # now have half a million markers eg - too many to plot all for a pdf - sample to get 10k or so points
            # oversample part of the distribution
            always = min(1000,nrows/20) # oversample smaller of lowest few hundred items or 5%
            skip = int(nrows/float(maxveclen)) # take 1 in skip to get about maxveclen points
            samplei = [i for i in range(nrows) if (i < always) or (i % skip == 0)]
            # always oversample first sorted (here lowest) values
            yvec = [yvec[i] for i in samplei] # always get first and last
            xvec = [xvec[i] for i in samplei] # and sample xvec same way
            maint='Log QQ Plot (random %d of %d)' % (len(yvec),nrows)
        else:
            maint='Log QQ Plot(n=%d)' % (nrows)
        mx = [0,math.log10(fn)] # if 1000, becomes 3 for the null line
        ylab = '%s' % xlabname
        xlab = '-log10(Uniform 0-1)'
        # need to supply the x axis or else rpy prints the freaking vector on the pdf - go figure
        rpy.r.pdf( outfname, height , width  )
        rpy.r("par(lab=c(10,10,10))") # so our grid is denser than the default 5
        rpy.r.qqplot(xvec,yvec,xlab=xlab,ylab=ylab,main=maint,sub=title,pch=19,col="maroon",cex=0.8)
        rpy.r.points(mx,mx,type='l')
        rpy.r.grid(nx = None, ny = None, col = "lightgray", lty = "dotted")
        rpy.r.dev_off()

    def rMultiQQ(plotme = [],nsplits=5, outfname='fname',title='title',xlabname='Sample',basename=''):
        """
        data must contain p,x,y as data for a qq plot, quantiles of x and y axis used to create a
        grid of qq plots to show departure from null at extremes of data quality
        Need to plot qqplot(p,unif) where the p's come from one x and one y quantile
        and ends up on the x axis go figure
        if sampling, oversample low values - all the top 1% ?
        """
        data = copy.copy(plotme)
        nvals = len(data)
        stepsize = nvals/nsplits
        logstep = math.log10(stepsize) # so is 3 for steps of 1000
        quints = range(0,nvals,stepsize) # quintile cutpoints for each layer
        data.sort(key=itertools.itemgetter(1)) # into x order
        rpy.r.pdf( outfname, height , width  )
        rpy.r("par(mfrow = c(%d,%d))" % (nsplits,nsplits))
        yvec = [-math.log10(random.random()) for x in range(stepsize)]
        yvec.sort() # size of each step is expected range for xvec under null?!
        for rowstart in quints:
            rowend = rowstart + stepsize
            if nvals - rowend < stepsize: # finish last split
                rowend = nvals
            row = data[rowstart:rowend]
            row.sort(key=itertools.itemgetter(2)) # into y order
            for colstart in quints:
                colend = colstart + stepsize
                if nvals - colend < stepsize: # finish last split
                    colend = nvals
                cell = row[colstart:colend]
                xvec = [-math.log10(x[0]) for x in cell] # all the pvalues for this cell
                rpy.r.qqplot(xvec,yvec,xlab=xlab,ylab=ylab,pch=19,col="maroon",cex=0.8)
                rpy.r.points(c(0,logstep),c(0,logstep),type='l')
        rpy.r.dev_off()


    def rQQNorm(plotme=[], outfname='fname',title='title',xlabname='Sample',basename=''):
        """
        y is data for a qqnorm plot
        if sampling, oversample low values - all the top 1% ?
        """
        rangeunif = len(plotme)
        nunif = 1000
        maxveclen = 3000
        nrows = len(plotme)
        data = copy.copy(plotme)
        if nrows > maxveclen:
            # now have half a million markers eg - too many to plot all for a pdf - sample to get 10k or so points
            # oversample part of the distribution
            always = min(1000,nrows/20) # oversample smaller of lowest few hundred items or 5%
            skip = int((nrows-always)/float(maxveclen)) # take 1 in skip to get about maxveclen points
            samplei = [i for i in range(nrows) if (i % skip == 0) or (i < always)]
            # always oversample first sorted (here lowest) values
            yvec = [data[i] for i in samplei] # always get first and last
            maint='Log QQ Plot (random %d of %d)' % (len(yvec),nrows)
        else:
            yvec = data
            maint='Log QQ Plot(n=%d)' % (nrows)
        n = 1000
        ylab = '%s' % xlabname
        xlab = 'Normal'
        # need to supply the x axis or else rpy prints the freaking vector on the pdf - go figure
        rpy.r.pdf( outfname, height , width  )
        rpy.r("par(lab=c(10,10,10))") # so our grid is denser than the default 5
        rpy.r.qqnorm(yvec,xlab=xlab,ylab=ylab,main=maint,sub=title,pch=19,col="maroon",cex=0.8)
        rpy.r.grid(nx = None, ny = None, col = "lightgray", lty = "dotted")
        rpy.r.dev_off()

    def rMAFMissqq(plotme=[], outfname='fname',title='title',xlabname='Sample',basename=''):
        """
        layout qq plots for pvalues within rows of increasing MAF and columns of increasing missingness
        like the GAIN qc tools
        y is data for a qq plot and ends up on the x axis go figure
        if sampling, oversample low values - all the top 1% ?
        """
        rangeunif = len(plotme)
        nunif = 1000
        fn = float(rangeunif)
        xvec = [-math.log10(x/fn) for x in range(1,(rangeunif+1))]
        skip = max(int(rangeunif/fn),1)
        # force include last points
        mx = [0,math.log10(fn)] # if 1000, becomes 3 for the null line
        maxveclen = 2000
        nrows = len(plotme)
        data = copy.copy(plotme)
        data.sort() # low to high - oversample low values
        if nrows > maxveclen:
            # now have half a million markers eg - too many to plot all for a pdf - sample to get 10k or so points
            # oversample part of the distribution
            always = min(1000,nrows/20) # oversample smaller of lowest few hundred items or 5%
            skip = int(nrows/float(maxveclen)) # take 1 in skip to get about maxveclen points
            samplei = [i for i in range(nrows) if (i % skip == 0) or (i < always)]
            # always oversample first sorted (here lowest) values
            yvec = [data[i] for i in samplei] # always get first and last
            xvec = [xvec[i] for i in samplei] # and sample xvec same way
            maint='Log QQ Plot (random %d of %d)' % (len(yvec),nrows)
        else:
            yvec = data
            maint='Log QQ Plot(n=%d)' % (nrows)
        n = 1000
        mx = [0,log10(fn)] # if 1000, becomes 3 for the null line
        ylab = '%s' % xlabname
        xlab = '-log10(Uniform 0-1)'
        # need to supply the x axis or else rpy prints the freaking vector on the pdf - go figure
        rpy.r.pdf( outfname, height , width  )
        rpy.r("par(lab=c(10,10,10))") # so our grid is denser than the default 5
        rpy.r.qqplot(xvec,yvec,xlab=xlab,ylab=ylab,main=maint,sub=title,pch=19,col="maroon",cex=0.8)
        rpy.r.points(mx,mx,type='l')
        rpy.r.grid(nx = None, ny = None, col = "lightgray", lty = "dotted")
        rpy.r.dev_off()


    fdsto,stofile = tempfile.mkstemp()
    sto = open(stofile,'w')
    import rpy # delay to avoid rpy stdout chatter replacing galaxy file blurb
    mog = 'mogrify'
    pdfnup = 'pdfnup'
    pdfjoin = 'pdfjoin'
    shead = subjects.pop(0) # get rid of head
    mhead = markers.pop(0)
    maf = mhead.index('maf')
    missfrac = mhead.index('missfrac')
    logphweall = mhead.index('logp_hwe_all')
    logphweunaff = mhead.index('logp_hwe_unaff')
    # check for at least some unaffected rml june 2009
    m_mendel = mhead.index('N_Mendel')
    fracmiss = shead.index('FracMiss')
    s_mendel = shead.index('Mendel_errors')
    s_het = shead.index('F_Stat')
    params = {}
    hweres = [float(x[logphweunaff]) for x in markers if len(x[logphweunaff]) >= logphweunaff
         and x[logphweunaff].upper() <> 'NA']
    if len(hweres) <> 0:
        xs = [logphweunaff, missfrac, maf, m_mendel, fracmiss, s_mendel, s_het]
        # plot for each of these cols
    else: # try hwe all instead - maybe no affection status available
        xs = [logphweall, missfrac, maf, m_mendel, fracmiss, s_mendel, s_het]
    ordplotme = [1,1,1,1,1,1,1] # ordered plots for everything!
    oreverseme = [1,1,0,1,1,1,0] # so larger values are oversampled
    qqplotme = [1,0,0,0,0,0,0] #
    qnplotme = [0,0,0,0,0,0,1] #
    nplots = len(xs)
    xlabnames = ['log(p) HWE (unaff)', 'Missing Rate: Markers', 'Minor Allele Frequency',
                 'Marker Mendel Error Count', 'Missing Rate: Subjects',
                 'Subject Mendel Error Count','Subject Inbreeding (het) F Statistic']
    plotnames = ['logphweunaff', 'missfrac', 'maf', 'm_mendel', 'fracmiss', 's_mendel','s_het']
    ploturls = ['%s_%s.pdf' % (basename,x) for x in plotnames] # real plotnames
    ordplotnames = ['%s_cum' % x for x in plotnames]
    ordploturls = ['%s_%s.pdf' % (basename,x) for x in ordplotnames] # real plotnames
    outfnames = [os.path.join(newfpath,ploturls[x]) for x in range(nplots)]
    ordoutfnames = [os.path.join(newfpath,ordploturls[x]) for x in range(nplots)]
    datasources = [markers,markers,markers,markers,subjects,subjects,subjects] # use this table
    titles = ["Marker HWE","Marker Missing Genotype", "Marker MAF","Marker Mendel",
        "Subject Missing Genotype","Subject Mendel",'Subject F Statistic']
    html = []
    pdflist = []
    for n,column in enumerate(xs):
        dat = [float(x[column]) for x in datasources[n] if len(x) >= column
               and x[column][:2].upper() <> 'NA'] # plink gives both!
        if sum(dat) <> 0: # eg nada for mendel if case control?
            rHist(plotme=dat,outfname=outfnames[n],xlabname=xlabnames[n],
              title=titles[n],basename=basename,nbreaks=nbreaks)
            row = [titles[n],ploturls[n],outfnames[n] ]
            html.append(row)
            pdflist.append(outfnames[n])
            if ordplotme[n]: # for missingness, hwe - plots to see where cutoffs will end up
                otitle = 'Ranked %s' % titles[n]
                dat.sort()
                if oreverseme[n]:
                    dat.reverse()
                rCum(plotme=dat,outfname=ordoutfnames[n],xlabname='Ordered %s' % xlabnames[n],
                  title=otitle,basename=basename,nbreaks=1000)
                row = [otitle,ordploturls[n],ordoutfnames[n]]
                html.append(row)
                pdflist.append(ordoutfnames[n])
            if qqplotme[n]: #
                otitle = 'LogQQ plot %s' % titles[n]
                dat.sort()
                dat.reverse()
                ofn = os.path.split(ordoutfnames[n])
                ofn = os.path.join(ofn[0],'QQ%s' % ofn[1])
                ofu = os.path.split(ordploturls[n])
                ofu = os.path.join(ofu[0],'QQ%s' % ofu[1])
                rQQ(plotme=dat,outfname=ofn,xlabname='QQ %s' % xlabnames[n],
                  title=otitle,basename=basename)
                row = [otitle,ofu,ofn]
                html.append(row)
                pdflist.append(ofn)
            elif qnplotme[n]:
                otitle = 'F Statistic %s' % titles[n]
                dat.sort()
                dat.reverse()
                ofn = os.path.split(ordoutfnames[n])
                ofn = os.path.join(ofn[0],'FQNorm%s' % ofn[1])
                ofu = os.path.split(ordploturls[n])
                ofu = os.path.join(ofu[0],'FQNorm%s' % ofu[1])
                rQQNorm(plotme=dat,outfname=ofn,xlabname='F QNorm %s' % xlabnames[n],
                  title=otitle,basename=basename)
                row = [otitle,ofu,ofn]
                html.append(row)
                pdflist.append(ofn)
        else:
            print '#$# no data for # %d - %s, data[:10]=%s' % (n,titles[n],dat[:10])
    if nup>0:
        # pdfjoin --outfile chr1test.pdf `ls database/files/dataset_396_files/*.pdf`
        # pdfnup chr1test.pdf --nup 3x3 --frame true --outfile chr1test3.pdf
        filestojoin = ' '.join(pdflist) # all the file names so far
        afname = '%s_All_Paged.pdf' % (basename)
        fullafname = os.path.join(newfpath,afname)
        expl = 'All %s QC Plots joined into a single pdf' % basename
        vcl = '%s %s --outfile %s ' % (pdfjoin,filestojoin, fullafname)
        # make single page pdf
        x=subprocess.Popen(vcl,shell=True,cwd=newfpath,stderr=sto,stdout=sto)
        retval = x.wait()
        row = [expl,afname,fullafname]
        html.insert(0,row) # last rather than second
        nfname = '%s_All_%dx%d.pdf' % (basename,nup,nup)
        fullnfname = os.path.join(newfpath,nfname)
        expl = 'All %s QC Plots %d by %d to a page' % (basename,nup,nup)
        vcl = '%s %s --nup %dx%d --frame true --outfile %s' % (pdfnup,afname,nup,nup,fullnfname)
        # make thumbnail images
        x=subprocess.Popen(vcl,shell=True,cwd=newfpath,stderr=sto,stdout=sto)
        retval = x.wait()
        row = [expl,nfname,fullnfname]
        html.insert(1,row) # this goes second
    vcl = '%s -format jpg -resize %s %s' % (mog, mogresize, os.path.join(newfpath,'*.pdf'))
    # make thumbnail images
    x=subprocess.Popen(vcl,shell=True,cwd=newfpath,stderr=sto,stdout=sto)
    retval = x.wait()
    sto.close()
    cruft = open(stofile,'r').readlines()
    return html,cruft # elements for an ordered list of urls or whatever..  


def RmakePlots(markers=[],subjects=[],newfpath='.',basename='test',nbreaks='100',nup=3,height=8,width=10,rexe=''):
    """
    nice try but the R scripts are huge and take forever to run if there's a lot of data
    marker rhead = ['snp','chrom','maf','a1','a2','missfrac',
    'p_hwe_all','logp_hwe_all','p_hwe_unaff','logp_hwe_unaff','N_Mendel']
    subject rhead = ['famId','iId','FracMiss','Mendel_errors','Ped_sex','SNP_sex','Status','Fest']
    """
    colour = "maroon"
        
    def rHist(plotme='',outfname='',xlabname='',title='',basename='',nbreaks=nbreaks):
        """   rHist <- function(plotme,froot,plotname,title,mfname,nbreaks=50)
        # generic histogram and vertical boxplot in a 3:1 layout
        # returns the graphic file name for inclusion in the web page
        # broken out here for reuse
        # ross lazarus march 2007
        """
        R = []
        maint = 'QC for %s - %s' % (basename,title)
        screenmat = (1,2,1,2) # create a 2x2 canvas
        widthlist = (80,20) # change to 4:1 ratio for histo and boxplot
        R.append('pdf("%s",h=%d,w=%d)' % (outfname,height,width))
        R.append("layout(matrix(c(1,1,1,2),nrow=1,ncol=4,byrow=T))")
        R.append("plotme = read.table(file='%s',head=F,sep='\t')" % plotme)
        R.append('hist(plotme, main="%s",xlab="%s",breaks=%d,col="%s")' % (maint,xlabname,nbreaks,colour))
        R.append('boxplot(plotme,main="",col="%s",outline=F)' % (colour) )
        R.append('dev.off()')
        return R
        
    def rCum(plotme='',outfname='',xlabname='',title='',basename='',nbreaks=100):
        """
        Useful to see what various cutoffs yield - plot percentiles
        """
        R = []
        n = len(plotme)
        R.append("plotme = read.table(file='%s',head=T,sep='\t')" % plotme)
        # arrives already in decending order of importance missingness or mendel count by subj or marker
        maint = 'QC for %s - %s' % (basename,title)
        R.append('pdf("%s",h=%d,w=%d)' % (outfname,height,width))
        R.append("par(lab=c(10,10,10))")
        R.append('plot(plotme$xvec,plotme$yvec,type="p",main="%s",ylab="%s",xlab="Sample Percentile",col="%s")' % (maint,xlabname,colour))
        R.append('dev.off()')
        return R

    def rQQ(plotme='', outfname='fname',title='title',xlabname='Sample',basename=''):
        """
        y is data for a qq plot and ends up on the x axis go figure
        if sampling, oversample low values - all the top 1% ?
        this version called with -log10 transformed hwe
        """
        R = []
        nrows = len(plotme)
        fn = float(nrows)
        xvec = [-math.log10(x/fn) for x in range(1,(nrows+1))]
        #mx = [0,math.log10(fn)] # if 1000, becomes 3 for the null line
        maxveclen = 3000
        yvec = copy.copy(plotme)
        if nrows > maxveclen:
            # now have half a million markers eg - too many to plot all for a pdf - sample to get 10k or so points
            # oversample part of the distribution
            always = min(1000,nrows/20) # oversample smaller of lowest few hundred items or 5%
            skip = int(nrows/float(maxveclen)) # take 1 in skip to get about maxveclen points
            if skip < 2:
                skip = 2
            samplei = [i for i in range(nrows) if (i < always) or (i % skip == 0)]
            # always oversample first sorted (here lowest) values
            yvec = [yvec[i] for i in samplei] # always get first and last
            xvec = [xvec[i] for i in samplei] # and sample xvec same way
            maint='Log QQ Plot (random %d of %d)' % (len(yvec),nrows)
        else:
            maint='Log QQ Plot(n=%d)' % (nrows)
        mx = [0,math.log10(fn)] # if 1000, becomes 3 for the null line
        ylab = '%s' % xlabname
        xlab = '-log10(Uniform 0-1)'
        # need to supply the x axis or else rpy prints the freaking vector on the pdf - go figure
        x = ['%f' % x for x in xvec]
        R.append('xvec = c(%s)' % ','.join(x))
        y = ['%f' % x for x in yvec]
        R.append('yvec = c(%s)' % ','.join(y))
        R.append('mx = c(0,%f)' % (math.log10(fn)))
        R.append('pdf("%s",h=%d,w=%d)' % (outfname,height,width))
        R.append("par(lab=c(10,10,10))")
        R.append('qqplot(xvec,yvec,xlab="%s",ylab="%s",main="%s",sub="%s",pch=19,col="%s",cex=0.8)' % (xlab,ylab,maint,title,colour))
        R.append('points(mx,mx,type="l")')
        R.append('grid(col="lightgray",lty="dotted")')
        R.append('dev.off()')
        return R

    def rMultiQQ(plotme = '',nsplits=5, outfname='fname',title='title',xlabname='Sample',basename=''):
        """
        data must contain p,x,y as data for a qq plot, quantiles of x and y axis used to create a
        grid of qq plots to show departure from null at extremes of data quality
        Need to plot qqplot(p,unif) where the p's come from one x and one y quantile
        and ends up on the x axis go figure
        if sampling, oversample low values - all the top 1% ?
        """
        data = copy.copy(plotme)
        nvals = len(data)
        stepsize = nvals/nsplits
        logstep = math.log10(stepsize) # so is 3 for steps of 1000
        R.append('mx = c(0,%f)' % logstep)
        quints = range(0,nvals,stepsize) # quintile cutpoints for each layer
        data.sort(key=itertools.itemgetter(1)) # into x order
        #rpy.r.pdf( outfname, h , w  )
        #rpy.r("par(mfrow = c(%d,%d))" % (nsplits,nsplits))
        R.append('pdf("%s",h=%d,w=%d)' % (outfname,height,width))
        yvec = [-math.log10(random.random()) for x in range(stepsize)]
        yvec.sort() # size of each step is expected range for xvec under null?!
        y = ['%f' % x for x in yvec]
        R.append('yvec = c(%s)' % ','.join(y))
        for rowstart in quints:
            rowend = rowstart + stepsize
            if nvals - rowend < stepsize: # finish last split
                rowend = nvals
            row = data[rowstart:rowend]
            row.sort(key=itertools.itemgetter(2)) # into y order
            for colstart in quints:
                colend = colstart + stepsize
                if nvals - colend < stepsize: # finish last split
                    colend = nvals
                cell = row[colstart:colend]
                xvec = [-math.log10(x[0]) for x in cell] # all the pvalues for this cell
                x = ['%f' % x for x in xvec]
                R.append('xvec = c(%s)' % ','.join(x))
                R.append('qqplot(xvec,yvec,xlab="%s",ylab="%s",main="%s",sub="%s",pch=19,col="%s",cex=0.8)' % (xlab,ylab,maint,title,colour))
                R.append('points(mx,mx,type="l")')
                R.append('grid(col="lightgray",lty="dotted")')
                #rpy.r.qqplot(xvec,yvec,xlab=xlab,ylab=ylab,pch=19,col="maroon",cex=0.8)
                #rpy.r.points(c(0,logstep),c(0,logstep),type='l')
        R.append('dev.off()')
        #rpy.r.dev_off()
        return R


    def rQQNorm(plotme=[], outfname='fname',title='title',xlabname='Sample',basename=''):
        """
        y is data for a qqnorm plot
        if sampling, oversample low values - all the top 1% ?
        """
        rangeunif = len(plotme)
        nunif = 1000
        maxveclen = 3000
        nrows = len(plotme)
        data = copy.copy(plotme)
        if nrows > maxveclen:
            # now have half a million markers eg - too many to plot all for a pdf - sample to get 10k or so points
            # oversample part of the distribution
            always = min(1000,nrows/20) # oversample smaller of lowest few hundred items or 5%
            skip = int((nrows-always)/float(maxveclen)) # take 1 in skip to get about maxveclen points
            samplei = [i for i in range(nrows) if (i % skip == 0) or (i < always)]
            # always oversample first sorted (here lowest) values
            yvec = [data[i] for i in samplei] # always get first and last
            maint='Log QQ Plot (random %d of %d)' % (len(yvec),nrows)
        else:
            yvec = data
            maint='Log QQ Plot(n=%d)' % (nrows)
        n = 1000
        ylab = '%s' % xlabname
        xlab = 'Normal'
        # need to supply the x axis or else rpy prints the freaking vector on the pdf - go figure
        #rpy.r.pdf( outfname, h , w  )
        #rpy.r("par(lab=c(10,10,10))") # so our grid is denser than the default 5
        #rpy.r.qqnorm(yvec,xlab=xlab,ylab=ylab,main=maint,sub=title,pch=19,col="maroon",cex=0.8)
        #rpy.r.grid(nx = None, ny = None, col = "lightgray", lty = "dotted")
        #rpy.r.dev_off()
        y = ['%f' % x for x in yvec]
        R.append('yvec = c(%s)' % ','.join(y))
        R.append('pdf("%s",h=%d,w=%d)' % (outfname,height,width))
        R.append("par(lab=c(10,10,10))")
        R.append('qqnorm(yvec,xlab="%s",ylab="%s",main="%s",sub="%s",pch=19,col="%s",cex=0.8)' % (xlab,ylab,maint,title,colour))
        R.append('grid(col="lightgray",lty="dotted")')
        R.append('dev.off()')
        return R

    def rMAFMissqq(plotme=[], outfname='fname',title='title',xlabname='Sample',basename=''):
        """
        layout qq plots for pvalues within rows of increasing MAF and columns of increasing missingness
        like the GAIN qc tools
        y is data for a qq plot and ends up on the x axis go figure
        if sampling, oversample low values - all the top 1% ?
        """
        rangeunif = len(plotme)
        nunif = 1000
        fn = float(rangeunif)
        xvec = [-math.log10(x/fn) for x in range(1,(rangeunif+1))]
        skip = max(int(rangeunif/fn),1)
        # force include last points
        mx = [0,math.log10(fn)] # if 1000, becomes 3 for the null line
        maxveclen = 2000
        nrows = len(plotme)
        data = copy.copy(plotme)
        data.sort() # low to high - oversample low values
        if nrows > maxveclen:
            # now have half a million markers eg - too many to plot all for a pdf - sample to get 10k or so points
            # oversample part of the distribution
            always = min(1000,nrows/20) # oversample smaller of lowest few hundred items or 5%
            skip = int(nrows/float(maxveclen)) # take 1 in skip to get about maxveclen points
            samplei = [i for i in range(nrows) if (i % skip == 0) or (i < always)]
            # always oversample first sorted (here lowest) values
            yvec = [data[i] for i in samplei] # always get first and last
            xvec = [xvec[i] for i in samplei] # and sample xvec same way
            maint='Log QQ Plot (random %d of %d)' % (len(yvec),nrows)
        else:
            yvec = data
            maint='Log QQ Plot(n=%d)' % (nrows)
        n = 1000
        mx = [0,log10(fn)] # if 1000, becomes 3 for the null line
        ylab = '%s' % xlabname
        xlab = '-log10(Uniform 0-1)'
        R.append('mx = c(0,%f)' % (math.log10(fn)))
        x = ['%f' % x for x in xvec]
        R.append('xvec = c(%s)' % ','.join(x))
        y = ['%f' % x for x in yvec]
        R.append('yvec = c(%s)' % ','.join(y))
        R.append('pdf("%s",h=%d,w=%d)' % (outfname,height,width))
        R.append("par(lab=c(10,10,10))")
        R.append('qqplot(xvec,yvec,xlab="%s",ylab="%s",main="%s",sub="%s",pch=19,col="%s",cex=0.8)' % (xlab,ylab,maint,title,colour))
        R.append('points(mx,mx,type="l")')
        R.append('grid(col="lightgray",lty="dotted")')
        R.append('dev.off()')


    shead = subjects.pop(0) # get rid of head
    mhead = markers.pop(0)
    maf = mhead.index('maf')
    missfrac = mhead.index('missfrac')
    logphweall = mhead.index('logp_hwe_all')
    logphweunaff = mhead.index('logp_hwe_unaff')
    # check for at least some unaffected rml june 2009
    m_mendel = mhead.index('N_Mendel')
    fracmiss = shead.index('FracMiss')
    s_mendel = shead.index('Mendel_errors')
    s_het = shead.index('F_Stat')
    params = {}
    h = [float(x[logphweunaff]) for x in markers if len(x[logphweunaff]) >= logphweunaff
         and x[logphweunaff].upper() <> 'NA']
    if len(h) <> 0:
        xs = [logphweunaff, missfrac, maf, m_mendel, fracmiss, s_mendel, s_het]
        # plot for each of these cols
    else: # try hwe all instead - maybe no affection status available
        xs = [logphweall, missfrac, maf, m_mendel, fracmiss, s_mendel, s_het]
    ordplotme = [1,1,1,1,1,1,1] # ordered plots for everything!
    oreverseme = [1,1,0,1,1,1,0] # so larger values are oversampled
    qqplotme = [1,0,0,0,0,0,0] #
    qnplotme = [0,0,0,0,0,0,1] #
    nplots = len(xs)
    xlabnames = ['log(p) HWE (unaff)', 'Missing Rate: Markers', 'Minor Allele Frequency',
                 'Marker Mendel Error Count', 'Missing Rate: Subjects',
                 'Subject Mendel Error Count','Subject Inbreeding (het) F Statistic']
    plotnames = ['logphweunaff', 'missfrac', 'maf', 'm_mendel', 'fracmiss', 's_mendel','s_het']
    ploturls = ['%s_%s.pdf' % (basename,x) for x in plotnames] # real plotnames
    ordplotnames = ['%s_cum' % x for x in plotnames]
    ordploturls = ['%s_%s.pdf' % (basename,x) for x in ordplotnames] # real plotnames
    outfnames = [os.path.join(newfpath,ploturls[x]) for x in range(nplots)]
    ordoutfnames = [os.path.join(newfpath,ordploturls[x]) for x in range(nplots)]
    datasources = [markers,markers,markers,markers,subjects,subjects,subjects] # use this table
    titles = ["Marker HWE","Marker Missing Genotype", "Marker MAF","Marker Mendel",
        "Subject Missing Genotype","Subject Mendel",'Subject F Statistic']
    html = []
    pdflist = []
    R = []
    for n,column in enumerate(xs):
        dfn = '%d_%s.txt' % (n,titles[n])
        dfilepath = os.path.join(newfpath,dfn)
        dat = [float(x[column]) for x in datasources[n] if len(x) >= column
               and x[column][:2].upper() <> 'NA'] # plink gives both!
        if sum(dat) <> 0: # eg nada for mendel if case control?
            plotme = file(dfilepath,'w')
            plotme.write('\n'.join(['%f' % x for x in dat])) # pass as a file - copout!
            tR = rHist(plotme=dfilepath,outfname=outfnames[n],xlabname=xlabnames[n],
              title=titles[n],basename=basename,nbreaks=nbreaks)
            R += tR
            row = [titles[n],ploturls[n],outfnames[n] ]
            html.append(row)
            pdflist.append(outfnames[n])
            if ordplotme[n]: # for missingness, hwe - plots to see where cutoffs will end up
                otitle = 'Ranked %s' % titles[n]
                dat.sort()
                if oreverseme[n]:
                    dat.reverse()
                    ndat = len(dat)
                    xvec = range(ndat)
                    xvec = [100.0*(n-x)/n for x in xvec] # convert to centile
                    # now have half a million markers eg - too many to plot all for a pdf - sample to get 10k or so points
                    maxveclen = 1000.0 # for reasonable pdf sizes!
                    if ndat > maxveclen: # oversample part of the distribution
                        always = min(1000,ndat/20) # oversample smaller of lowest few hundred items or 5%
                        skip = int(ndat/maxveclen) # take 1 in skip to get about maxveclen points
                        samplei = [i for i in range(ndat) if (i % skip == 0) or (i < always)] # always oversample first sorted values
                        yvec = [yvec[i] for i in samplei] # always get first and last
                        xvec = [xvec[i] for i in samplei] # always get first and last
                        plotme = file(dfilepath,'w')
                        plotme.write('xvec\tyvec\n')
                        plotme.write('\n'.join(['%f\t%f' % (xvec[i],y) for y in yvec])) # pass as a file - copout!
                tR = rCum(plotme=dat,outfname=ordoutfnames[n],xlabname='Ordered %s' % xlabnames[n],
                  title=otitle,basename=basename,nbreaks=nbreaks)
                R += tR
                row = [otitle,ordploturls[n],ordoutfnames[n]]
                html.append(row)
                pdflist.append(ordoutfnames[n])
            if qqplotme[n]: #
                otitle = 'LogQQ plot %s' % titles[n]
                dat.sort()
                dat.reverse()
                ofn = os.path.split(ordoutfnames[n])
                ofn = os.path.join(ofn[0],'QQ%s' % ofn[1])
                ofu = os.path.split(ordploturls[n])
                ofu = os.path.join(ofu[0],'QQ%s' % ofu[1])
                tR = rQQ(plotme=dat,outfname=ofn,xlabname='QQ %s' % xlabnames[n],
                  title=otitle,basename=basename)
                R += tR
                row = [otitle,ofu,ofn]
                html.append(row)
                pdflist.append(ofn)
            elif qnplotme[n]:
                otitle = 'F Statistic %s' % titles[n]
                dat.sort()
                dat.reverse()
                ofn = os.path.split(ordoutfnames[n])
                ofn = os.path.join(ofn[0],'FQNorm%s' % ofn[1])
                ofu = os.path.split(ordploturls[n])
                ofu = os.path.join(ofu[0],'FQNorm%s' % ofu[1])
                tR = rQQNorm(plotme=dat,outfname=ofn,xlabname='F QNorm %s' % xlabnames[n],
                  title=otitle,basename=basename)
                R += tR
                row = [otitle,ofu,ofn]
                html.append(row)
                pdflist.append(ofn)
        else:
            print '#$# no data for # %d - %s, data[:10]=%s' % (n,titles[n],dat[:10])
    rlog,flist = RRun(rcmd=R,title='makeQCplots',outdir=newfpath)
    if nup>0:
        # pdfjoin --outfile chr1test.pdf `ls database/files/dataset_396_files/*.pdf`
        # pdfnup chr1test.pdf --nup 3x3 --frame true --outfile chr1test3.pdf
        filestojoin = ' '.join(pdflist) # all the file names so far
        afname = '%s_All_Paged.pdf' % (basename)
        fullafname = os.path.join(newfpath,afname)
        expl = 'All %s QC Plots joined into a single pdf' % basename
        vcl = 'pdfjoin %s --outfile %s ' % (filestojoin, fullafname)
        # make single page pdf
        x=subprocess.Popen(vcl,shell=True,cwd=newfpath)
        retval = x.wait()
        row = [expl,afname,fullafname]
        html.insert(0,row) # last rather than second
        nfname = '%s_All_%dx%d.pdf' % (basename,nup,nup)
        fullnfname = os.path.join(newfpath,nfname)
        expl = 'All %s QC Plots %d by %d to a page' % (basename,nup,nup)
        vcl = 'pdfnup %s --nup %dx%d --frame true --outfile %s' % (afname,nup,nup,fullnfname)
        # make thumbnail images
        x=subprocess.Popen(vcl,shell=True,cwd=newfpath)
        retval = x.wait()
        row = [expl,nfname,fullnfname]
        html.insert(1,row) # this goes second
    vcl = 'mogrify -format jpg -resize %s %s' % (mogresize, os.path.join(newfpath,'*.pdf'))
    # make thumbnail images
    x=subprocess.Popen(vcl,shell=True,cwd=newfpath)
    retval = x.wait()
    return html # elements for an ordered list of urls or whatever..

def countHet(bedf='fakeped_500000',linkageped=True,froot='fake500k',outfname="ahetf",logf='rgQC.log'):
    """
    NO LONGER USED - historical interest
    count het loci for each subject to look for outliers = ? contamination
    assume ped file is linkage format
    need to make a ped file from the bed file we were passed
    """
    vcl = [plinke,'--bfile',bedf,'--recode','--out','%s_recode' % froot] # write a recoded ped file from the real .bed file
    p=subprocess.Popen(' '.join(vcl),shell=True)
    retval = p.wait()
    f = open('%s_recode.recode.ped' % froot,'r')
    if not linkageped:
        head = f.next() # throw away header
    hets = [] # simple count of het loci per subject. Expect poisson?
    n = 1
    for l in f:
        n += 1
        ll = l.strip().split()
        if len(ll) > 6:
            iid = idjoiner.join(ll[:2]) # fam_iid
            gender = ll[4]
            alleles = ll[6:]
            nallele = len(alleles)
            nhet = 0
            for i in range(nallele/2):
                a1=alleles[2*i]
                a2=alleles[2*i+1]
                if alleles[2*i] <> alleles[2*i+1]: # must be het
                    if not missvals.get(a1,None) and not missvals.get(a2,None):
                        nhet += 1
            hets.append((nhet,iid,gender)) # for sorting later
    f.close()
    hets.sort()
    hets.reverse() # biggest nhet now on top
    f = open(outfname ,'w')
    res = ['%d\t%s\t%s' % (x) for x in hets] # I love list comprehensions
    res.insert(0,'nhetloci\tfamid_iid\tgender')
    res.append('')
    f.write('\n'.join(res))
    f.close()



def subjectRep(froot='cleantest',outfname="srep",newfpath='.',logf = None):
    """by subject (missingness = .imiss, mendel = .imendel)
    assume replicates have an underscore in family id for
    hapmap testing
    For sorting, we need floats and integers
    """
    isexfile = '%s.sexcheck' % froot
    imissfile = '%s.imiss' % froot
    imendfile = '%s.imendel' % froot
    ihetfile = '%s.het' % froot
    logf.write('## subject reports starting at %s\n' % timenow())
    outfile = os.path.join(newfpath,outfname)
    idlist = []
    imissdict = {}
    imenddict = {}
    isexdict = {}
    ihetdict = {}
    Tops = {}
    Tnames = ['Ranked Subject Missing Genotype', 'Ranked Subject Mendel',
              'Ranked Sex check', 'Ranked Inbreeding (het) F statistic']
    Tsorts = [2,3,6,8]
    Treverse = [True,True,True,False] # so first values are worser
    #rhead = ['famId','iId','FracMiss','Mendel_errors','Ped_sex','SNP_sex','Status','Fest']
    ##              FID            IID MISS_PHENO   N_MISS   N_GENO   F_MISS
    ##  1552042370_A   1552042370_A          N     5480   549883 0.009966
    ##  1552042410_A   1552042410_A          N     1638   549883 0.002979
 
    # ------------------missing--------------------
    # imiss has FID  IID MISS_PHENO N_MISS  F_MISS
    # we want F_MISS
    try:
        f = open(imissfile,'r')
    except:
        logf.write('# file %s is missing - talk about irony\n' % imissfile)
        f = None
    if f:
        for n,line in enumerate(f):
            ll = line.strip().split()
            if n == 0:
                head = [x.upper() for x in ll] # expect above                
                fidpos = head.index('FID')
                iidpos = head.index('IID')
                fpos = head.index('F_MISS')
            elif len(ll) >= fpos: # full line
                fid = ll[fidpos]
                #if fid.find('_') == -1: # not replicate! - icondb ids have these...
                iid = ll[iidpos]
                fmiss = ll[fpos]
                id = '%s%s%s' % (fid,idjoiner,iid)
                imissdict[id] = fmiss
                idlist.append(id)
        f.close()
    logf.write('## imissfile %s contained %d ids\n' % (imissfile,len(idlist)))
    # ------------------mend-------------------
    # *.imendel has FID  IID   N
    # we want N
    gotmend = True
    try:
        f = open(imendfile,'r')
    except:
        gotmend = False
        for id in idlist:
            imenddict[id] = '0'
    if gotmend:
        for n,line in enumerate(f):
            ll = line.strip().split()
            if n == 0:
                head = [x.upper() for x in ll] # expect above                
                npos = head.index('N')
                fidpos = head.index('FID')
                iidpos = head.index('IID')
            elif len(ll) >= npos: # full line
                fid = ll[fidpos]
                iid = ll[iidpos]
                id = '%s%s%s' % (fid,idjoiner,iid)
                nmend = ll[npos]
                imenddict[id] = nmend
        f.close()
    else:
        logf.write('## error No %s file - assuming not family data\n' % imendfile)
    # ------------------sex check------------------
    #[rerla@hg fresh]$ head /home/rerla/fresh/database/files/dataset_978_files/CAMP2007Dirty.sexcheck
    # sexcheck has FID IID PEDSEX SNPSEX STATUS F
    ##
    ##     FID     Family ID
    ##     IID     Individual ID
    ##     PEDSEX  Sex as determined in pedigree file (1=male, 2=female)
    ##     SNPSEX  Sex as determined by X chromosome
    ##     STATUS  Displays "PROBLEM" or "OK" for each individual
    ##     F       The actual X chromosome inbreeding (homozygosity) estimate
    ##
    ##    A PROBLEM arises if the two sexes do not match, or if the SNP data or pedigree data are
    ##    ambiguous with regard to sex.
    ##    A male call is made if F is more than 0.8; a femle call is made if F is less than 0.2.
    try:
        f = open(isexfile,'r')
        got_sexcheck = 1
    except:
        got_sexcheck = 0
    if got_sexcheck:
        for n,line in enumerate(f):
            ll = line.strip().split()
            if n == 0:
                head = [x.upper() for x in ll] # expect above                
                fidpos = head.index('FID')
                iidpos = head.index('IID')
                pedsexpos = head.index('PEDSEX')
                snpsexpos = head.index('SNPSEX')
                statuspos = head.index('STATUS')
                fpos = head.index('F')
            elif len(ll) >= fpos: # full line
                fid = ll[fidpos]
                iid = ll[iidpos]
                fest = ll[fpos]
                pedsex = ll[pedsexpos]
                snpsex = ll[snpsexpos]
                stat = ll[statuspos]
                id = '%s%s%s' % (fid,idjoiner,iid)
                isexdict[id] = (pedsex,snpsex,stat,fest)
        f.close()
    else:
        # this only happens if there are no subjects!
        logf.write('No %s file - assuming no sex errors' % isexfile)
    ##
    ##    FID  IID       O(HOM)       E(HOM)        N(NM)            F
    ##    457    2       490665    4.928e+05       722154    -0.009096
    ##    457    3       464519     4.85e+05       710986      -0.0908
    ##   1037    2       461632    4.856e+05       712025       -0.106
    ##   1037    1       491845    4.906e+05       719353     0.005577
    try:
        f = open(ihetfile,'r')
    except:
        f = None
        logf.write('## No %s file - did we run --het in plink?\n' % ihetfile)
    if f:
        for i,line in enumerate(f):
            ll = line.strip().split()
            if i == 0:
                head = [x.upper() for x in ll] # expect above                
                fidpos = head.index('FID')
                iidpos = head.index('IID')
                fpos = head.index('F')
                n = 0
            elif len(ll) >= fpos: # full line
                fid = ll[fidpos]            
                iid = ll[iidpos]
                fhet = ll[fpos]
                id = '%s%s%s' % (fid,idjoiner,iid)
                ihetdict[id] = fhet
        f.close()      # now assemble and output result list
    rhead = ['famId','iId','FracMiss','Mendel_errors','Ped_sex','SNP_sex','Status','XHomEst','F_Stat']
    res = []
    fres = [] # floats for sorting
    for id in idlist: # for each snp in found order
        fid,iid = id.split(idjoiner) # recover keys
        f_missing = imissdict.get(id,'0.0')
        nmend = imenddict.get(id,'0')
        (pedsex,snpsex,status,fest) = isexdict.get(id,('0','0','0','0.0'))
        fhet = ihetdict.get(id,'0.0')
        res.append([fid,iid,f_missing,nmend,pedsex,snpsex,status,fest,fhet])
        try:
            ff_missing = float(f_missing)
        except:
            ff_missing = 0.0
        try:
            inmend = int(nmend)
        except:
            inmend = 0
        try:
            ffest = float(fest)
        except:
            fest = 0.0
        try:
            ffhet = float(fhet)
        except:
            ffhet = 0.0
        fres.append([fid,iid,ff_missing,inmend,pedsex,snpsex,status,ffest,ffhet])
    ntokeep = max(20,len(res)/keepfrac)
    for i,col in enumerate(Tsorts):
        fres.sort(key=operator.itemgetter(col))
        if Treverse[i]:
            fres.reverse()
        repname = Tnames[i]
        Tops[repname] = fres[0:ntokeep]
        Tops[repname] = [map(str,x) for x in Tops[repname]]
        Tops[repname].insert(0,rhead)
    res.sort()
    res.insert(0,rhead)
    logf.write('### writing %s report with %s' % ( outfile,res[0]))  
    f = open(outfile,'w')
    f.write('\n'.join(['\t'.join(x) for x in res]))
    f.write('\n')
    f.close()
    return res,Tops

def markerRep(froot='cleantest',outfname="mrep",newfpath='.',logf=None,maplist=None ):
    """by marker (hwe = .hwe, missingness=.lmiss, freq = .frq)
    keep a list of marker order but keep all stats in dicts
    write out a fake xls file for R or SAS etc
    kinda clunky, but..
    TODO: ensure stable if any file not found?
    """
    mapdict = {}
    if maplist <> None:
       rslist = [x[1] for x in maplist]
       offset = [(x[0],x[3]) for x in maplist]
       mapdict = dict(zip(rslist,offset))
    hwefile = '%s.hwe' % froot
    lmissfile = '%s.lmiss' % froot
    freqfile = '%s.frq' % froot
    lmendfile = '%s.lmendel' % froot
    outfile = os.path.join(newfpath,outfname)
    markerlist = []
    chromlist = []
    hwedict = {}
    lmissdict = {}
    freqdict = {}
    lmenddict = {}
    Tops = {}
    Tnames = ['Ranked Marker MAF', 'Ranked Marker Missing Genotype', 'Ranked Marker HWE', 'Ranked Marker Mendel']
    Tsorts = [3,6,10,11]
    Treverse = [False,True,True,True] # so first values are worse(r)
    #res.append([rs,chrom,offset,maf,a1,a2,f_missing,hwe_all[0],hwe_all[1],hwe_unaff[0],hwe_unaff[1],nmend])
    #rhead = ['snp','chrom','maf','a1','a2','missfrac','p_hwe_all','logp_hwe_all','p_hwe_unaff','logp_hwe_unaff','N_Mendel']
    # -------------------hwe--------------------------
    #    hwe has SNP TEST  GENO   O(HET)   E(HET) P_HWD
    # we want all hwe where P_HWD <> NA
    # ah changed in 1.04 to
    ##  CHR         SNP     TEST   A1   A2                 GENO   O(HET)   E(HET)            P 
    ##   1   rs6671164      ALL    2    3           34/276/613    0.299   0.3032       0.6644
    ##   1   rs6671164      AFF    2    3                0/0/0      nan      nan           NA
    ##   1   rs6671164    UNAFF    2    3           34/276/613    0.299   0.3032       0.6644
    ##   1   rs4448553      ALL    2    3            8/176/748   0.1888   0.1848       0.5975
    ##   1   rs4448553      AFF    2    3                0/0/0      nan      nan           NA
    ##   1   rs4448553    UNAFF    2    3            8/176/748   0.1888   0.1848       0.5975
    ##   1   rs1990150      ALL    1    3           54/303/569   0.3272   0.3453       0.1067
    ##   1   rs1990150      AFF    1    3                0/0/0      nan      nan           NA
    ##   1   rs1990150    UNAFF    1    3           54/303/569   0.3272   0.3453       0.1067
    logf.write('## marker reports starting at %s\n' % timenow())
    try:
        f = open(hwefile,'r')
    except:
        f = None
        logf.write('## error - no hwefile %s found\n' % hwefile)
    if f:
        for i,line in enumerate(f):
            ll = line.strip().split()
            if i == 0: # head
                head = [x.upper() for x in ll] # expect above                
                try:
                    testpos = head.index('TEST')
                except:
                    testpos = 2 # patch for 1.04 which has b0rken headers - otherwise use head.index('TEST')
                try:
                    ppos = head.index('P')
                except:
                    ppos = 8 # patch - for head.index('P')
                snppos = head.index('SNP')
                chrpos = head.index('CHR')
                logf.write('hwe header testpos=%d,ppos=%d,snppos=%d\n' % (testpos,ppos,snppos))
            elif len(ll) >= ppos: # full line
                ps = ll[ppos].upper()
                rs = ll[snppos]
                chrom = ll[chrpos]
                test = ll[testpos]
                if not hwedict.get(rs,None):
                    hwedict[rs] = {}
                    markerlist.append(rs)
                chromlist.append(chrom) # one place to find it?
                lpvals = 0
                if ps.upper() <> 'NA' and ps.upper() <> 'NAN': # worth keeping
                    lpvals = '0'
                    if ps <> '1':
                        try:
                            pval = float(ps)
                            lpvals = '%f' % -math.log10(pval)
                        except:
                            pass
                    hwedict[rs][test] = (ps,lpvals)
            else:
                logf.write('short line #%d = %s\n' % (i,ll))
        f.close()
    # ------------------missing--------------------
    """lmiss has  
    CHR          SNP   N_MISS   N_GENO   F_MISS
   1   rs12354060        0       73        0
   1    rs4345758        1       73   0.0137
   1    rs2691310       73       73        1
   1    rs2531266       73       73        1
    # we want F_MISS"""
    try:
        f = open(lmissfile,'r')
    except:
        f = None
    if f:
        for i,line in enumerate(f):
            ll = line.strip().split()
            if i == 0:
                head = [x.upper() for x in ll] # expect above                
                fracpos = head.index('F_MISS')
                npos = head.index('N_MISS')
                snppos = head.index('SNP')
            elif len(ll) >= fracpos: # full line
                rs = ll[snppos]
                fracval = ll[fracpos]                
                lmissdict[rs] = fracval # for now, just that?
            else:
                lmissdict[rs] = 'NA'
        f.close()
    # ------------------freq-------------------
    # frq has CHR          SNP   A1   A2          MAF       NM
    # we want maf
    try:
        f = open(freqfile,'r')
    except:
        f = None
    if f:
        for i,line in enumerate(f):
            ll = line.strip().split()
            if i == 0:
                head = [x.upper() for x in ll] # expect above                
                mafpos = head.index('MAF')
                a1pos = head.index('A1')
                a2pos = head.index('A2')
                snppos = head.index('SNP')
            elif len(ll) >= mafpos: # full line
                rs = ll[snppos]
                a1 = ll[a1pos]
                a2 = ll[a2pos]
                maf = ll[mafpos]
                freqdict[rs] = (maf,a1,a2)
        f.close()
    # ------------------mend-------------------
    # lmend has CHR SNP   N
    # we want N
    gotmend = True
    try:
        f = open(lmendfile,'r')
    except:
        gotmend = False
        for rs in markerlist:
            lmenddict[rs] = '0'
    if gotmend:
        for i,line in enumerate(f):
            ll = line.strip().split()
            if i == 0:
                head = [x.upper() for x in ll] # expect above                
                npos = head.index('N')
                snppos = head.index('SNP')
            elif len(ll) >= npos: # full line
                rs = ll[snppos]
                nmend = ll[npos]
                lmenddict[rs] = nmend
        f.close()
    else:
        logf.write('No %s file - assuming not family data\n' % lmendfile)
    # now assemble result list
    rhead = ['snp','chromosome','offset','maf','a1','a2','missfrac','p_hwe_all','logp_hwe_all','p_hwe_unaff','logp_hwe_unaff','N_Mendel']
    res = []
    fres = []
    for rs in markerlist: # for each snp in found order
        f_missing = lmissdict.get(rs,'NA')
        maf,a1,a2 = freqdict.get(rs,('NA','NA','NA'))
        hwe_all = hwedict[rs].get('ALL',('NA','NA')) # hope this doesn't change...
        hwe_unaff = hwedict[rs].get('UNAFF',('NA','NA'))
        nmend = lmenddict.get(rs,'NA')
        (chrom,offset)=mapdict.get(rs,('?','0'))
        res.append([rs,chrom,offset,maf,a1,a2,f_missing,hwe_all[0],hwe_all[1],hwe_unaff[0],hwe_unaff[1],nmend])
    ntokeep = max(10,len(res)/keepfrac)

    def msortk(item=None):
        """
        deal with non numeric sorting
        """
        try:
           return float(item)
        except:
           return item

    for i,col in enumerate(Tsorts):
        res.sort(key=msortk(lambda x:x[col]))
        if Treverse[i]:
            res.reverse()
        repname = Tnames[i]
        Tops[repname] = res[0:ntokeep]
        Tops[repname].insert(0,rhead)
    res.sort(key=lambda x: '%s_%10d' % (x[1].ljust(4,'0'),int(x[2]))) # in chrom offset order
    res.insert(0,rhead)
    f = open(outfile,'w')
    f.write('\n'.join(['\t'.join(x) for x in res]))
    f.close()
    return res,Tops



  
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


if __name__ == "__main__":
    u = """ called in xml as
     <command interpreter="python">
        rgQC.py -i '$input_file.extra_files_path/$input_file.metadata.base_name' -o "$out_prefix" 
        -s '$html_file' -p '$html_file.files_path' -l '${GALAXY_DATA_INDEX_DIR}/rg/bin/plink' 
        -r '${GALAXY_DATA_INDEX_DIR}/rg/bin/R' 
    </command>

        Prepare a qc report - eg:
    print "%s %s -i birdlped -o birdlped -l qc.log -s htmlf -m marker.xls -s sub.xls -p ./" % (sys.executable,prog)

    """
    progname = os.path.basename(sys.argv[0])
    if len(sys.argv) < 9:
        print '%s requires 6 parameters - got %d = %s' % (progname,len(sys.argv),sys.argv)
        sys.exit(1)
    parser = OptionParser(usage=u, version="%prog 0.01")
    a = parser.add_option
    a("-i","--infile",dest="infile")
    a("-o","--oprefix",dest="opref")
    a("-l","--plinkexe",dest="plinke", default=plinke)
    a("-r","--rexe",dest="rexe", default=rexe)
    a("-s","--snps",dest="htmlf")
    #a("-m","--markerRaw",dest="markf")
    #a("-r","--rawsubject",dest="subjf")
    a("-p","--patho",dest="newfpath")
    (options,args) = parser.parse_args()
    basename = os.path.split(options.infile)[-1] # just want the file prefix to find the .xls files below
    killme = string.punctuation + string.whitespace
    trantab = string.maketrans(killme,'_'*len(killme))
    opref = options.opref.translate(trantab)
    alogh,alog = tempfile.mkstemp(suffix='.txt')
    plogh,plog = tempfile.mkstemp(suffix='.txt')
    alogf = open(alog,'w')
    plogf = open(plog,'w')
    ahtmlf = options.htmlf
    amarkf = 'MarkerDetails_%s.xls' % opref
    asubjf = 'SubjectDetails_%s.xls' % opref
    newfpath = options.newfpath
    newfpath = os.path.realpath(newfpath)
    try:
       os.makedirs(newfpath)
    except:
       pass
    ofn = basename
    bfn = options.infile
    try:
       mapf = '%s.bim' % bfn
       maplist = file(mapf,'r').readlines()
       maplist = [x.split() for x in maplist]
    except:
       maplist = None
       alogf.write('## error - cannot open %s to read map - no offsets will be available for output files')
    #rerla@beast galaxy]$ head test-data/tinywga.bim
    #22      rs2283802       0       21784722        4       2
    #22      rs2267000       0       21785366        4       2
    rgbin = os.path.split(rexe)[0] # get our rg bin path
    #plinktasks = [' --freq',' --missing',' --mendel',' --hardy',' --check-sex'] # plink v1 fixes that bug!
    # if we could, do all at once? Nope. Probably never.
    plinktasks = [['--freq',],['--hwe 0.0', '--missing','--hardy'],
    ['--mendel',],['--check-sex',]]
    vclbase = [options.plinke,'--noweb','--out',basename,'--bfile',bfn,'--mind','1.0','--geno','1.0','--maf','0.0']
    runPlink(logf=plogf,plinktasks=plinktasks,cd=newfpath, vclbase=vclbase)
    plinktasks = [['--bfile',bfn,'--indep-pairwise 40 20 0.5','--out %s' % basename],
    ['--bfile',bfn,'--extract %s.prune.in --make-bed --out ldp_%s' % (basename, basename)],
                  ['--bfile ldp_%s --het --out %s' % (basename,basename)]]
    # subset of ld independent markers for eigenstrat and other requirements
    vclbase = [options.plinke,'--noweb']
    plogout = pruneLD(plinktasks=plinktasks,cd=newfpath,vclbase = vclbase)
    plogf.write('\n'.join(plogout))
    plogf.write('\n')
    repout = os.path.join(newfpath,basename)
    subjects,subjectTops = subjectRep(froot=repout,outfname=asubjf,newfpath=newfpath,
                logf=alogf) # writes the subject_froot.xls file
    markers,markerTops = markerRep(froot=repout,outfname=amarkf,newfpath=newfpath,
                logf=alogf,maplist=maplist) # marker_froot.xls
    nbreaks = 100
    s = '## starting plotpage, newfpath=%s,m=%s,s=%s/n' % (newfpath,markers[:2],subjects[:2])
    alogf.write(s)
    print s
    plotpage,cruft = makePlots(markers=markers,subjects=subjects,newfpath=newfpath,
                         basename=basename,nbreaks=nbreaks,height=10,width=8,rgbin=rgbin)
    #plotpage = RmakePlots(markers=markers,subjects=subjects,newfpath=newfpath,basename=basename,nbreaks=nbreaks,rexe=rexe)

    # [titles[n],plotnames[n],outfnames[n] ]
    html = []
    html.append('<table cellpadding="5" border="0">')
    size = getfSize(amarkf,newfpath)
    html.append('<tr><td colspan="3"><a href="%s" type="application/vnd.ms-excel">%s</a>%s tab delimited</td></tr>' % \
                (amarkf,'Click here to download the Marker QC Detail report file',size))
    size = getfSize(asubjf,newfpath)
    html.append('<tr><td colspan="3"><a href="%s" type="application/vnd.ms-excel">%s</a>%s tab delimited</td></tr>' % \
                (asubjf,'Click here to download the Subject QC Detail report file',size))
    for (title,url,ofname) in plotpage:
        ttitle = 'Ranked %s' % title
        dat = subjectTops.get(ttitle,None)
        if not dat:
            dat = markerTops.get(ttitle,None)
        imghref = '%s.jpg' % os.path.splitext(url)[0] # removes .pdf
        thumbnail = os.path.join(newfpath,imghref)
        if not os.path.exists(thumbnail): # for multipage pdfs, mogrify makes multiple jpgs - fugly hack
            imghref = '%s-0.jpg' % os.path.splitext(url)[0] # try the first jpg
            thumbnail = os.path.join(newfpath,imghref)
        if not os.path.exists(thumbnail):
            html.append('<tr><td colspan="3"><a href="%s">%s</a></td></tr>' % (url,title))
        else:
            html.append('<tr><td><a href="%s"><img src="%s" alt="%s" hspace="10" align="middle">' \
                    % (url,imghref,title))
            if dat: # one or the other - write as an extra file and make a link here
                t = '%s.xls' % (ttitle.replace(' ','_'))
                fname = os.path.join(newfpath,t)
                f = file(fname,'w')
                f.write('\n'.join(['\t'.join(x) for x in dat])) # the report
                size = getfSize(t,newfpath)
                html.append('</a></td><td>%s</td><td><a href="%s">Worst data</a>%s</td></tr>' % (title,t,size))
            else:
                html.append('</a></td><td>%s</td><td>&nbsp;</td></tr>' % (title))
    html.append('</table><hr><h3>All output files from the QC run are available below</h3>')
    html.append('<table cellpadding="5" border="0">\n')
    flist = os.listdir(newfpath) # we want to catch 'em all
    flist.sort()
    for f in flist:
        fname = os.path.split(f)[-1]
        size = getfSize(fname,newfpath)
        html.append('<tr><td><a href="%s">%s</a>%s</td></tr>' % (fname,fname,size))
    html.append('</table>')
    alogf.close()
    plogf.close()
    llog = open(alog,'r').readlines()
    plogfile = open(plog,'r').readlines()
    os.unlink(alog)
    os.unlink(plog)
    llog += plogfile # add lines from pruneld log
    lf = file(ahtmlf,'w') # galaxy will show this as the default view
    lf.write(galhtmlprefix % progname)
    s = '\n<div>Output from Rgenetics QC report tool run at %s<br>\n' % (timenow())
    lf.write('<h4>%s</h4>\n' % s)
    lf.write('</div><div><h4>(Click any preview image to download a full sized PDF version)</h4><br><ol>\n')
    lf.write('\n'.join(html))
    lf.write('<h4>QC run log contents</h4>')
    lf.write('<pre>%s</pre>' % (''.join(llog))) # plink logs
    if len(cruft) > 0:
        lf.write('<h2>Blather from pdfnup follows:</h2><pre>%s</pre>' % (''.join(cruft))) # pdfnup
    lf.write('%s\n<hr>\n' % galhtmlpostfix)
    lf.close()

