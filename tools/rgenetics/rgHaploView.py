"""
released under the terms of the LGPL
copyright ross lazarus August 2007
for the rgenetics project

Special galaxy tool for the camp2007 data
Allows grabbing genotypes from an arbitrary region and estimating
ld using haploview

stoopid haploview won't allow control of dest directory for plots - always end
up where the data came from - need to futz to get it where it belongs

Needs a mongo results file in the location hardwired below or could be passed in as
a library parameter - but this file must have a very specific structure
rs chrom offset float1...floatn


"""


import sys, array, os, string, tempfile, shutil, subprocess, glob
from rgutils import galhtmlprefix

progname = os.path.split(sys.argv[0])[1]

javabin = 'java'
#hvbin = '/usr/local/bin/Haploview.jar'
#hvbin = '/home/universe/linux-i686/haploview/Haploview.jar'
# get this from tool as a parameter - can use 



atrandic = {'A':'1','C':'2','G':'3','T':'4','N':'0','-':'0','1':'1','2':'2','3':'3','4':'4','0':'0'}

class NullDevice:
    """ """
    def write(self, s):
        pass

def ld():
    """  ### Sanity check the arguments

    <command interpreter="python">
    rgHaploView.py "$ucsc_region" "$rslist" "$title" "$out_file1"
    "$lhistIn.extra_files_path" "$lhistIn.metadata.base_name"
    "$minmaf" "$maxdist" "$ldtype" "$hires" "$memsize" "$out_file1.files_path"
    "$infoTrack" "$tagr2" "$hmpanel" ${GALAXY_DATA_INDEX_DIR}/rg/bin/haploview.jar
    </command>

    remember to figure out chromosome and complain if > 1?
    and use the -chromosome <1-22,X,Y> parameter to haploview
    skipcheck?
    """
    progname = os.path.split(sys.argv[0])[-1]
    ts = '%s%s' % (string.punctuation,string.whitespace)
    ptran =  string.maketrans(ts,'_'*len(ts))
    if len(sys.argv) < 16:
        s = '##!%s: Expected 16 params in sys.argv, got %d (%s)' % (progname,len(sys.argv), sys.argv)
        print s
        sys.exit(1)

    ### Figure out what genomic region we are interested in
    region = sys.argv[1]
    orslist = sys.argv[2].replace('X',' ').lower() # galaxy replaces newlines with XX - go figure
    title = sys.argv[3].translate(ptran)
    # for outputs
    outfile = sys.argv[4]
    logfn = 'Log_%s.txt' % (title)
    histextra = sys.argv[5]
    base_name = sys.argv[6]
    pedFileBase = os.path.join(histextra,base_name)
    print 'pedfilebase=%s' % pedFileBase
    minMaf=sys.argv[7]
    if minMaf:
        try:
            minMaf = float(minMaf)
        except:
            minMaf = 0.0
    maxDist=sys.argv[8] or None
    ldType=sys.argv[9] or 'RSQ'
    hiRes = (sys.argv[10].lower() == 'hi')
    memSize= sys.argv[11] or '1000'
    memSize = int(memSize)
    outfpath = sys.argv[12]
    infotrack = False # note that otherwise this breaks haploview in headless mode 
    #infotrack = sys.argv[13] == 'info'
    # this fails in headless mode as at april 2010 with haploview 4.2
    tagr2 = sys.argv[14] or '0.8'
    hmpanels = sys.argv[15] # eg "['CEU','YRI']"
    if hmpanels:
       hmpanels = hmpanels.replace('[','')
       hmpanels = hmpanels.replace(']','')
       hmpanels = hmpanels.replace("'",'')
       hmpanels = hmpanels.split(',')
    hvbin = sys.argv[16] # added rml june 2008
    bindir = os.path.split(hvbin)[0]
    # jan 2010 - always assume utes are on path to avoid platform problems
    pdfjoin = 'pdfjoin' # os.path.join(bindir,'pdfjoin')
    pdfnup = 'pdfnup' # os.path.join(bindir,'pdfnup')
    mogrify = 'mogrify' # os.path.join(bindir,'mogrify')
    convert = 'convert' # os.path.join(bindir,'convert')
    log_file = os.path.join(outfpath,logfn)
    MAP_FILE = '%s.map' % pedFileBase
    DATA_FILE = '%s.ped' % pedFileBase
    try:
        os.makedirs(outfpath)
        s = '## made new path %s\n' % outfpath
    except:
        pass
    lf = file(log_file,'w')
    s = 'PATH=%s\n' % os.environ.get('PATH','?')
    lf.write(s)
    hlogf = os.path.join(outfpath,'%s.log' % pedFileBase)
    chromosome = ''
    spos = epos = -9
    rslist = []
    rsdict = {}
    hlog = []

    if region > '':
        useRs = []
        useRsdict={}
        try: # TODO make a regexp?
            c,rest = region.split(':')
            chromosome = c.replace('chr','')
            rest = rest.replace(',','') # remove commas
            spos,epos = rest.split('-')
            spos = int(spos)
            epos = int(epos)
            s = '## %s parsing chrom %s from %d to %d\n' % (progname,chromosome,spos,epos)
            lf.write(s)
            lf.write('\n')
            print >> sys.stdout, s
        except:
            s = '##! %s unable to parse region %s - MUST look like "chr8:10,000-100,000\n' % (progname,region)
            print >> sys.stdout, s
            lf.write(s)
            lf.write('\n')
            lf.close()
            sys.exit(1)
    else:
        useRs = orslist.split() # galaxy replaces newlines with XX - go figure
        useRsdict = dict(zip(useRs,useRs))
    useTemp = False
    try:
        dfile = open(DATA_FILE, 'r')
    except: # bad input file name?
        s = '##! RGeno unable to open file %s\n' % (DATA_FILE)
        lf.write(s)
        lf.write('\n')
        lf.close()
        print >> sys.stdout, s
        raise
        sys.exit(1)
    try:
        mfile = open(MAP_FILE, 'r')
    except: # bad input file name?
        s = '##! RGeno unable to open file %s' % (MAP_FILE)
        lf.write(s)
        lf.write('\n')
        lf.close()
        print >> sys.stdout, s
        raise
        sys.exit(1)
    if len(useRs) > 0 or spos <> -9 : # subset region
        useTemp = True
        ### Figure out which markers are in this region
        markers = []
        snpcols = {}
        chroms = {}
        minpos = 2**32
        maxpos = 0
        for lnum,row in enumerate(mfile):
            line = row.strip()
            if not line: continue
            chrom, snp, genpos, abspos = line.split()
            try:
                ic = int(chrom)
            except:
                ic = None
            if ic and ic <= 23:
                try:
                    abspos = int(abspos)
                    if abspos > maxpos:
                        maxpos = abspos
                    if abspos < minpos:
                        minpos = abspos
                except:
                    abspos = epos + 999999999 # so next test fails
            if useRsdict.get(snp,None) or (spos <> -9 and chrom == chromosome and (spos <= abspos <= epos)):
                if chromosome == '':
                    chromosome = chrom
                chroms.setdefault(chrom,chrom)
                markers.append((chrom,abspos,snp)) # decorate for sort into genomic
                snpcols[snp] = lnum # so we know which col to find genos for this marker
        markers.sort()
        rslist = [x[2] for x in markers] # drop decoration
        rsdict = dict(zip(rslist,rslist))
        if len(rslist) == 0:
            s = '##! %s found no rs numbers in %s' % (progname,sys.argv[1:3])
            lf.write(s)
            lf.write('\n')
            lf.close()
            print >> sys.stdout, s
            sys.exit(1)
        if spos == -9:
            spos = minpos
            epos = maxpos
        s = '## %s looking for %d rs (%s)' % (progname,len(rslist),rslist[:5])
        lf.write(s)
        print >> sys.stdout, s
        wewant = [(6+(2*snpcols[x])) for x in rslist] #
        # column indices of first geno of each marker pair to get the markers into genomic
        ### ... and then parse the rest of the ped file to pull out
        ### the genotypes for all subjects for those markers
        # /usr/local/galaxy/data/rg/1/lped/
        tempMapName = os.path.join(outfpath,'%s.info' % title)
        tempMap = file(tempMapName,'w')
        tempPedName = os.path.join(outfpath,'%s.ped' % title)
        tempPed = file(tempPedName,'w')
        pngpath = '%s.LD.PNG' % tempPedName
        map = ['%s\t%s' % (x[2],x[1]) for x in markers] # snp,abspos in genomic order for haploview
        tempMap.write('%s\n' % '\n'.join(map))
        tempMap.close()
        nrows = 0
        for line in dfile:
            line = line.strip()
            if not line:
                continue
            fields = line.split()
            preamble = fields[:6]
            g = ['%s %s' % (fields[snpcol], fields[snpcol+1]) for snpcol in wewant]
            g = ' '.join(g)
            g = g.split() # we'll get there
            g = [atrandic.get(x,'0') for x in g] # numeric alleles...
            tempPed.write('%s %s\n' % (' '.join(preamble), ' '.join(g)))
            nrows += 1
        tempPed.close()
        s = '## %s: wrote %d markers, %d subjects for region %s\n' % (progname,len(rslist),nrows,region)
        lf.write(s)
        lf.write('\n')
        print >> sys.stdout,s
    else: # even if using all, must set up haploview info file instead of map
        markers = []
        chroms = {}
        spos = sys.maxint
        epos = -spos
        for lnum,row in enumerate(mfile):
          line = row.strip()
          if not line: continue
          chrom, snp, genpos, abspos = line.split()
          try:
            ic = int(chrom)
          except:
            ic = None
          if ic and ic <= 23:
            if chromosome == '':
                chromosome = chrom
            chroms.setdefault(chrom,chrom)
            try:
                p = int(abspos)
                if p < spos and p <> 0:
                    spos = p
                if p > epos and p <> 0:
                    epos = p
            except:
                pass
            markers.append('%s %s' % (snp,abspos)) # no sort - pass
        # now have spos and epos for hapmap if hmpanels
        tempMapName = os.path.join(outfpath,'%s.info' % title)
        tempMap = file(tempMapName,'w')
        tempMap.write('\n'.join(markers))
        tempMap.close()
        tempPedName = os.path.join(outfpath,'%s.ped' % title)
        try: # will fail on winblows!
            os.symlink(DATA_FILE,tempPedName)
        except:
            shutil.copy(DATA_FILE,tempPedName) # wasteful but..
    nchroms = len(chroms) # if > 1 can't really do this safely
    if nchroms > 1:
        s = '## warning - multiple chromosomes found in your map file - %s\n' % ','.join(chroms.keys())
        lf.write(s)
        print >> sys.stdout,s
        sys.exit(1)
    DATA_FILE = tempPedName # for haploview
    INFO_FILE = tempMapName
    dfile.close()
    mfile.close()
    fblog,blog = tempfile.mkstemp()
    ste = open(blog,'w') # to catch the blather
    # if no need to rewrite - set up names for haploview call
    vcl = [javabin,'-jar',hvbin,'-n','-memory','%d' % memSize,'-pairwiseTagging',
           '-pedfile',DATA_FILE,'-info',INFO_FILE,'-tagrsqcounts',
           '-tagrsqcutoff',tagr2,
           '-ldcolorscheme',ldType]
    if minMaf:
        vcl += ['-minMaf','%f' % minMaf]
    if maxDist:
        vcl += ['-maxDistance',maxDist]
    if hiRes:
        vcl.append('-png')
    else:
        vcl.append('-compressedpng')
    if nchroms == 1:
        vcl += ['-chromosome',chromosome]
    if infotrack:
        vcl.append('-infoTrack')
    p=subprocess.Popen(' '.join(vcl),shell=True,cwd=outfpath,stderr=ste,stdout=lf)
    retval = p.wait()
    s = '## executing %s returned %d\n' % (' '.join(vcl),retval)
    lf.write(s)
    vcl = [mogrify, '-resize 800x400!', '*.PNG']
    p=subprocess.Popen(' '.join(vcl),shell=True,cwd=outfpath,stderr=lf,stdout=lf)
    retval = p.wait()
    s = '## executing %s returned %d\n' % (' '.join(vcl),retval)
    lf.write(s)
    inpng = '%s.LD.PNG' % DATA_FILE # stupid but necessary - can't control haploview name mangle
    inpng = inpng.replace(' ','')
    inpng = os.path.split(inpng)[-1]
    tmppng = '%s.tmp.png' % title
    tmppng = tmppng.replace(' ','')
    outpng = '1_%s.png' % title
    outpng = outpng.replace(' ','')
    outpng = os.path.split(outpng)[-1]
    vcl = [convert, '-resize 800x400!', inpng, tmppng]
    p=subprocess.Popen(' '.join(vcl),shell=True,cwd=outfpath,stderr=lf,stdout=lf)
    retval = p.wait()
    s = '## executing %s returned %d\n' % (' '.join(vcl),retval)
    lf.write(s)
    s = "text 10,300 '%s'" % title[:40]
    vcl = ['convert', '-pointsize 25','-fill maroon',
          '-draw "%s"' % s, tmppng, outpng]
    p=subprocess.Popen(' '.join(vcl),shell=True,cwd=outfpath,stderr=lf,stdout=lf)
    retval = p.wait()
    s = '## executing %s returned %d\n' % (' '.join(vcl),retval)
    lf.write(s)
    try:
        os.remove(os.path.join(outfpath,tmppng))
    except:
        pass    # label all the plots then delete all the .PNG files before munging
    fnum=1
    if hmpanels:
        sp = '%d' % (spos/1000.) # hapmap wants kb
        ep = '%d' % (epos/1000.)
        for panel in hmpanels:
            if panel > '' and panel.lower() <> 'none': # in case someone checks that option too :)
                ptran = panel.strip()
                ptran = ptran.replace('+','_')
                fnum += 1 # preserve an order or else we get sorted
                vcl = [javabin,'-jar',hvbin,'-n','-memory','%d' % memSize,
                  '-chromosome',chromosome, '-panel',panel.strip(),
                  '-hapmapDownload','-startpos',sp,'-endpos',ep,
                  '-ldcolorscheme',ldType]
                if minMaf:
                    vcl += ['-minMaf','%f' % minMaf]
                if maxDist:
                    vcl += ['-maxDistance',maxDist]
                if hiRes:
                    vcl.append('-png')
                else:
                    vcl.append('-compressedpng')
                if infotrack:
                    vcl.append('-infoTrack')
                p=subprocess.Popen(' '.join(vcl),shell=True,cwd=outfpath,stderr=ste,stdout=lf)
                retval = p.wait()
                inpng = 'Chromosome%s%s.LD.PNG' % (chromosome,panel)
                inpng = inpng.replace(' ','') # mysterious spaces!
                outpng = '%d_HapMap_%s_%s.png' % (fnum,ptran,chromosome,)
                # hack for stupid chb+jpt
                outpng = outpng.replace(' ','')
                tmppng = '%s.tmp.png' % title
                tmppng = tmppng.replace(' ','')
                outpng = os.path.split(outpng)[-1]
                vcl = [convert, '-resize 800x400!', inpng, tmppng]
                p=subprocess.Popen(' '.join(vcl),shell=True,cwd=outfpath,stderr=lf,stdout=lf)
                retval = p.wait()
                s = '## executing %s returned %d\n' % (' '.join(vcl),retval)
                lf.write(s)
                s = "text 10,300 'HapMap %s'" % ptran.strip()
                vcl = [convert, '-pointsize 25','-fill maroon',
                      '-draw "%s"' % s, tmppng, outpng]
                p=subprocess.Popen(' '.join(vcl),shell=True,cwd=outfpath,stderr=lf,stdout=lf)
                retval = p.wait()
                s = '## executing %s returned %d\n' % (' '.join(vcl),retval)
                lf.write(s)
                try:
                    os.remove(os.path.join(outfpath,tmppng))
                except:
                    pass
    nimages = len(glob.glob(os.path.join(outfpath,'*.png'))) # rely on HaploView shouting - PNG @!
    lf.write('### nimages=%d\n' % nimages)
    if nimages > 0: # haploview may fail?
        vcl = '%s -format pdf -resize 800x400! *.png' % mogrify
        p=subprocess.Popen(vcl,shell=True,cwd=outfpath,stderr=lf,stdout=lf)
        retval = p.wait()
        lf.write('## executing %s returned %d\n' % (vcl,retval))
        vcl = '%s "*.pdf" --fitpaper true --outfile alljoin.pdf' % pdfjoin
        p=subprocess.Popen(vcl,shell=True,cwd=outfpath,stderr=lf,stdout=lf)
        retval = p.wait()
        lf.write('## executing %s returned %d\n' % (vcl,retval))
        vcl = '%s alljoin.pdf --nup 1x%d --outfile allnup.pdf' % (pdfnup,nimages)
        p=subprocess.Popen(vcl,shell=True,cwd=outfpath,stderr=lf,stdout=lf)
        retval = p.wait()
        lf.write('## executing %s returned %d\n' % (vcl,retval))
        #vcl = ['convert', 'allnup.pdf', 'allnup.png'] # this fails - bad pdf?
        #p=subprocess.Popen(' '.join(vcl),shell=True,cwd=outfpath)
        #retval = p.wait()
        #lf.write('## executing %s returned %d\n' % (vcl,retval))
    lf.write('\n'.join(hlog))
    ste.close() # temp file used to catch haploview blather
    hblather = open(blog,'r').readlines() # to catch the blather    
    os.unlink(blog)
    if len(hblather) > 0:
       lf.write('## In addition, Haploview complained:')
       lf.write(''.join(hblather))
       lf.write('\n')
    lf.close()
    flist = glob.glob(os.path.join(outfpath, '*'))
    flist.sort()
    ts = '!"#$%&\'()*+,-/:;<=>?@[\\]^_`{|}~' + string.whitespace
    ftran =  string.maketrans(ts,'_'*len(ts))
    outf = file(outfile,'w')
    outf.write(galhtmlprefix % progname)
    s = '<h4>rgenetics for Galaxy %s, wrapping HaploView</h4>' % (progname)
    outf.write(s)
    """
    as at ashg 2009, convert fails on allnup.pdf - probably too complex...
    mainthumb = 'allnup.png'
    mainpdf = 'allnup.pdf'
    if os.path.exists(mainpdf):
        if not os.path.exists(mainthumb):
            outf.write('<table><tr><td colspan="3"><a href="%s">Main combined LD plot</a></td></tr></table>\n' % (mainpdf))
        else:
            outf.write('<table><tr><td><a href="%s"><img src="%s" alt="Main combined LD image" hspace="10" align="middle">')
            outf.write('</td><td>Click this thumbnail to display the main combined LD image</td></tr></table>\n' % (mainpdf,mainthumb))
    else:
        outf.write('(No main image was generated - this usually means a Haploview error connecting to Hapmap site - please try later)<br/>\n')
    outf.write('## Called as %s' % sys.argv)
    """
    outf.write('<br><div><hr><ul>\n')
    for i, data in enumerate( flist ):
        dn = os.path.split(data)[-1]
        if dn[:3] <> 'all':
            continue
        newdn = dn.translate(ftran)
        if dn <> newdn:
            os.rename(os.path.join(outfpath,dn),os.path.join(outfpath,newdn))
            dn = newdn
        dnlabel = dn
        ext = dn.split('.')[-1]
        if dn == 'allnup.pdf':
            dnlabel = 'All pdf plots on a single page'
        elif dn == 'alljoin.pdf':
            dnlabel = 'All pdf plots, each on a separate page'
        outf.write('<li><a href="%s">%s - %s</a></li>\n' % (dn,dn,dnlabel))
    for i, data in enumerate( flist ):
        dn = os.path.split(data)[-1]
        if dn[:3] == 'all':
            continue
        newdn = dn.translate(ftran)
        if dn <> newdn:
            os.rename(os.path.join(outfpath,dn),os.path.join(outfpath,newdn))
            dn = newdn
        dnlabel = dn
        ext = dn.split('.')[-1]
        if dn == 'allnup.pdf':
            dnlabel = 'All pdf plots on a single page'
        elif dn == 'alljoin.pdf':
            dnlabel = 'All pdf plots, each on a separate page'
        elif ext == 'info':
            dnlabel = '%s map data for Haploview input' % title
        elif ext == 'ped':
            dnlabel = '%s genotype data for Haploview input' % title
        elif dn.find('CEU') <> -1 or dn.find('YRI') <> -1 or dn.find('CHB_JPT') <> -1: # is hapmap
            dnlabel = 'Hapmap data'
        if ext == 'TAGS' or ext == 'TESTS' or ext == 'CHAPS':
            dnlabel = dnlabel + ' Tagger output'
        outf.write('<li><a href="%s">%s - %s</a></li>\n' % (dn,dn,dnlabel))
    outf.write('</ol><br>')
    outf.write("</div><div><hr>Job Log follows below (see %s)<pre>" % logfn)
    s = file(log_file,'r').readlines()
    s = '\n'.join(s)
    outf.write('%s</pre><hr></div>' % s)
    outf.write('</body></html>')
    outf.close()
    if useTemp:
        try:
            os.unlink(tempMapName)
            os.unlink(tempPedName)
        except:
            pass
        
if __name__ == "__main__":
    ld()

