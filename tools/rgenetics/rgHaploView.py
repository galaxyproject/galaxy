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
    """ a dev/null for ignoring output
    """
    def write(self, s):
        pass

class ldPlot:
    
    def __init__(self, argv=[]):
        """
        setup
        """
        self.args=argv
        self.parseArgs(argv=self.args)
        self.setupRegions()
                
    def parseArgs(self,argv=[]):
        """
        """
        ts = '%s%s' % (string.punctuation,string.whitespace)
        ptran =  string.maketrans(ts,'_'*len(ts))
        ### Figure out what genomic region we are interested in
        self.region = argv[1]
        self.orslist = argv[2].replace('X',' ').lower() # galaxy replaces newlines with XX - go figure
        self.title = argv[3].translate(ptran)
        # for outputs
        self.outfile = argv[4]
        self.logfn = 'Log_%s.txt' % (self.title)
        self.histextra = argv[5]
        self.base_name = argv[6]
        self.pedFileBase = os.path.join(self.histextra,self.base_name)
        print 'pedfilebase=%s' % self.pedFileBase
        self.minMaf=argv[7]
        if self.minMaf:
            try:
                self.minMaf = float(self.minMaf)
            except:
                self.minMaf = 0.0
        self.maxDist=argv[8] or None
        self.ldType=argv[9] or 'RSQ'
        self.hiRes = (argv[10].lower() == 'hi')
        self.memSize= argv[11] or '1000'
        self.memSize = int(self.memSize)
        self.outfpath = argv[12]
        self.infotrack = False # note that otherwise this breaks haploview in headless mode 
        #infotrack = argv[13] == 'info'
        # this fails in headless mode as at april 2010 with haploview 4.2
        self.tagr2 = argv[14] or '0.8'
        hmpanels = argv[15] # eg "['CEU','YRI']"
        if hmpanels:
           hmpanels = hmpanels.replace('[','')
           hmpanels = hmpanels.replace(']','')
           hmpanels = hmpanels.replace("'",'')
           hmpanels = hmpanels.split(',')
        self.hmpanels = hmpanels
        self.hvbin = argv[16] # added rml june 2008
        self.bindir = os.path.split(self.hvbin)[0]
        # jan 2010 - always assume utes are on path to avoid platform problems
        self.pdfjoin = 'pdfjoin' # os.path.join(bindir,'pdfjoin')
        self.pdfnup = 'pdfnup' # os.path.join(bindir,'pdfnup')
        self.mogrify = 'mogrify' # os.path.join(bindir,'mogrify')
        self.convert = 'convert' # os.path.join(bindir,'convert')
        self.log_file = os.path.join(self.outfpath,self.logfn)
        self.MAP_FILE = '%s.map' % self.pedFileBase
        self.DATA_FILE = '%s.ped' % self.pedFileBase
        try:
            os.makedirs(self.outfpath)
            s = '## made new path %s\n' % self.outfpath
        except:
            pass
        self.lf = file(self.log_file,'w')
        s = 'PATH=%s\n' % os.environ.get('PATH','?')
        self.lf.write(s)

    def getRs(self):
        if self.region > '':
            useRs = []
            useRsdict={}
            try: # TODO make a regexp?
                c,rest = self.region.split(':')
                chromosome = c.replace('chr','')
                rest = rest.replace(',','') # remove commas
                spos,epos = rest.split('-')
                spos = int(spos)
                epos = int(epos)
                s = '## %s parsing chrom %s from %d to %d\n' % (progname,chromosome,spos,epos)
                self.lf.write(s)
                self.lf.write('\n')
                print >> sys.stdout, s
            except:
                s = '##! %s unable to parse region %s - MUST look like "chr8:10,000-100,000\n' % (progname,self.region)
                print >> sys.stdout, s
                self.lf.write(s)
                self.lf.write('\n')
                self.lf.close()
                sys.exit(1)
        else:
            useRs = self.orslist.split() # galaxy replaces newlines with XX - go figure
            useRsdict = dict(zip(useRs,useRs))
        return useRs, useRsdict

    
    def setupRegions(self):
        """
        This turns out to be complex because we allow the user
        flexibility - paste a list of rs or give a region.
        In most cases, some subset has to be generated correctly before running Haploview
        """
        chromosome = ''
        spos = epos = -9
        rslist = []
        rsdict = {}
        useRs,useRsdict = self.getRs()
        self.useTemp = False
        try:
            dfile = open(self.DATA_FILE, 'r')
        except: # bad input file name?
            s = '##! RGeno unable to open file %s\n' % (self.DATA_FILE)
            self.lf.write(s)
            self.lf.write('\n')
            self.lf.close()
            print >> sys.stdout, s
            raise
            sys.exit(1)
        try:
            mfile = open(self.MAP_FILE, 'r')
        except: # bad input file name?
            s = '##! RGeno unable to open file %s' % (self.MAP_FILE)
            lf.write(s)
            lf.write('\n')
            lf.close()
            print >> sys.stdout, s
            raise
            sys.exit(1)
        if len(useRs) > 0 or spos <> -9 : # subset region
            self.useTemp = True
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
                s = '##! %s: Found no rs numbers matching %s' % (progname,self.args[1:3])
                self.lf.write(s)
                self.lf.write('\n')
                self.lf.close()
                print >> sys.stdout, s
                sys.exit(1)
            if spos == -9:
                spos = minpos
                epos = maxpos
            s = '## %s looking for %d rs (%s)' % (progname,len(rslist),rslist[:5])
            self.lf.write(s)
            print >> sys.stdout, s
            wewant = [(6+(2*snpcols[x])) for x in rslist] #
            # column indices of first geno of each marker pair to get the markers into genomic
            ### ... and then parse the rest of the ped file to pull out
            ### the genotypes for all subjects for those markers
            # /usr/local/galaxy/data/rg/1/lped/
            self.tempMapName = os.path.join(self.outfpath,'%s.info' % self.title)
            self.tempMap = file(self.tempMapName,'w')
            self.tempPedName = os.path.join(self.outfpath,'%s.ped' % self.title)
            self.tempPed = file(self.tempPedName,'w')
            self.pngpath = '%s.LD.PNG' % self.tempPedName
            map = ['%s\t%s' % (x[2],x[1]) for x in markers] # snp,abspos in genomic order for haploview
            self.tempMap.write('%s\n' % '\n'.join(map))
            self.tempMap.close()
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
                self.tempPed.write('%s %s\n' % (' '.join(preamble), ' '.join(g)))
                nrows += 1
            self.tempPed.close()
            s = '## %s: wrote %d markers, %d subjects for region %s\n' % (progname,len(rslist),nrows,self.region)
            self.lf.write(s)
            self.lf.write('\n')
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
            self.tempMapName = os.path.join(self.outfpath,'%s.info' % self.title)
            self.tempMap = file(self.tempMapName,'w')
            self.tempMap.write('\n'.join(markers))
            self.tempMap.close()
            self.tempPedName = os.path.join(self.outfpath,'%s.ped' % self.title)
            try: # will fail on winblows!
                os.symlink(self.DATA_FILE,self.tempPedName)
            except:
                shutil.copy(self.DATA_FILE,self.tempPedName) # wasteful but..
        self.nchroms = len(chroms) # if > 1 can't really do this safely
        dfile.close()
        mfile.close()
        self.spos = spos
        self.epos = epos
        self.chromosome = chromosome
        if self.nchroms > 1:
            s = '## warning - multiple chromosomes found in your map file - %s\n' % ','.join(chroms.keys())
            self.lf.write(s)
            print >> sys.stdout,s
            sys.exit(1)

    def run(self,vcl):
        """
        """
        p=subprocess.Popen(vcl,shell=True,cwd=self.outfpath,stderr=self.lf,stdout=self.lf)
        retval = p.wait()
        self.lf.write('## executing %s returned %d\n' % (vcl,retval))

    def plotHmPanels(self,ste):
        """
        """
        sp = '%d' % (self.spos/1000.) # hapmap wants kb
        ep = '%d' % (self.epos/1000.)
        fnum=0
        for panel in self.hmpanels:
            if panel > '' and panel.lower() <> 'none': # in case someone checks that option too :)
                ptran = panel.strip()
                ptran = ptran.replace('+','_')
                fnum += 1 # preserve an order or else we get sorted
                vcl = [javabin,'-jar',self.hvbin,'-n','-memory','%d' % self.memSize,
                  '-chromosome',self.chromosome, '-panel',panel.strip(),
                  '-hapmapDownload','-startpos',sp,'-endpos',ep,
                  '-ldcolorscheme',self.ldType]
                if self.minMaf:
                    vcl += ['-minMaf','%f' % self.minMaf]
                if self.maxDist:
                    vcl += ['-maxDistance',self.maxDist]
                if self.hiRes:
                    vcl.append('-png')
                else:
                    vcl.append('-compressedpng')
                if self.infotrack:
                    vcl.append('-infoTrack')
                p=subprocess.Popen(' '.join(vcl),shell=True,cwd=self.outfpath,stderr=ste,stdout=self.lf)
                retval = p.wait()
                inpng = 'Chromosome%s%s.LD.PNG' % (self.chromosome,panel)
                inpng = inpng.replace(' ','') # mysterious spaces!
                outpng = '%d_HapMap_%s_%s.png' % (fnum,ptran,self.chromosome)
                # hack for stupid chb+jpt
                outpng = outpng.replace(' ','')
                tmppng = '%s.tmp.png' % self.title
                tmppng = tmppng.replace(' ','')
                outpng = os.path.split(outpng)[-1]
                vcl = [self.convert, '-resize 800x400!', inpng, tmppng]
                self.run(' '.join(vcl))
                s = "text 10,300 'HapMap %s'" % ptran.strip()
                vcl = [self.convert, '-pointsize 25','-fill maroon',
                      '-draw "%s"' % s, tmppng, outpng]
                self.run(' '.join(vcl))
                try:
                    os.remove(os.path.join(self.outfpath,tmppng))
                except:
                    pass

    def doPlots(self):
        """
        """    
        DATA_FILE = self.tempPedName # for haploview
        INFO_FILE = self.tempMapName
        fblog,blog = tempfile.mkstemp()
        ste = open(blog,'w') # to catch the blather
        # if no need to rewrite - set up names for haploview call
        vcl = [javabin,'-jar',self.hvbin,'-n','-memory','%d' % self.memSize,'-pairwiseTagging',
               '-pedfile',DATA_FILE,'-info',INFO_FILE,'-tagrsqcounts',
               '-tagrsqcutoff',self.tagr2, '-ldcolorscheme',self.ldType]
        if self.minMaf:
            vcl += ['-minMaf','%f' % self.minMaf]
        if self.maxDist:
            vcl += ['-maxDistance',self.maxDist]
        if self.hiRes:
            vcl.append('-png')
        else:
            vcl.append('-compressedpng')
        if self.nchroms == 1:
            vcl += ['-chromosome',self.chromosome]
        if self.infotrack:
            vcl.append('-infoTrack')
        self.run(' '.join(vcl))
        vcl = [self.mogrify, '-resize 800x400!', '*.PNG']
        self.run(' '.join(vcl))
        inpng = '%s.LD.PNG' % DATA_FILE # stupid but necessary - can't control haploview name mangle
        inpng = inpng.replace(' ','')
        inpng = os.path.split(inpng)[-1]
        tmppng = '%s.tmp.png' % self.title
        tmppng = tmppng.replace(' ','')
        outpng = '1_%s.png' % self.title
        outpng = outpng.replace(' ','')
        outpng = os.path.split(outpng)[-1]
        vcl = [self.convert, '-resize 800x400!', inpng, tmppng]
        self.run(' '.join(vcl))
        s = "text 10,300 '%s'" % self.title[:40]
        vcl = [self.convert, '-pointsize 25','-fill maroon',
              '-draw "%s"' % s, tmppng, outpng]
        self.run(' '.join(vcl))
        try:
            os.remove(os.path.join(self.outfpath,tmppng))
        except:
            pass    # label all the plots then delete all the .PNG files before munging
        fnum=1
        if self.hmpanels:
            self.plotHmPanels(ste)
        nimages = len(glob.glob(os.path.join(self.outfpath,'*.png'))) # rely on HaploView shouting - PNG @!
        self.lf.write('### nimages=%d\n' % nimages)
        if nimages > 0: # haploview may fail?
            vcl = '%s -format pdf -resize 800x400! *.png' % self.mogrify
            self.run(vcl)
            vcl = '%s *.pdf --fitpaper true --outfile alljoin.pdf' % self.pdfjoin
            self.run(vcl)
            vcl = '%s alljoin.pdf --nup 1x%d --outfile allnup.pdf' % (self.pdfnup,nimages)
            self.run(vcl)
            vcl = '%s -resize x300 allnup.pdf allnup.png' % (self.convert)
            self.run(vcl)
        ste.close() # temp file used to catch haploview blather
        hblather = open(blog,'r').readlines() # to catch the blather    
        os.unlink(blog)
        if len(hblather) > 0:
           self.lf.write('## In addition, Haploview complained:')
           self.lf.write(''.join(hblather))
           self.lf.write('\n')
        self.lf.close()
        
    def writeHtml(self):
        """
        """
        flist = glob.glob(os.path.join(self.outfpath, '*'))
        flist.sort()
        ts = '!"#$%&\'()*+,-/:;<=>?@[\\]^_`{|}~' + string.whitespace
        ftran =  string.maketrans(ts,'_'*len(ts))
        outf = file(self.outfile,'w')
        outf.write(galhtmlprefix % progname)
        s = '<h4>rgenetics for Galaxy %s, wrapping HaploView</h4>' % (progname)
        outf.write(s)
        mainthumb = 'allnup.png'
        mainpdf = 'allnup.pdf'
        if os.path.exists(os.path.join(self.outfpath,mainpdf)):
            if not os.path.exists(os.path.join(self.outfpath,mainthumb)):
                outf.write('<table><tr><td colspan="3"><a href="%s">Main combined LD plot</a></td></tr></table>\n' % (mainpdf))
            else:
                outf.write('<table><tr><td><a href="%s"><img src="%s" title="Main combined LD image" hspace="10" align="middle">' % (mainpdf,mainthumb))
                outf.write('</td><td>Click the thumbnail at left to download the main combined LD image <a href=%s>%s</a></td></tr></table>\n' % (mainpdf,mainpdf))
        else:
            outf.write('(No main image was generated - this usually means a Haploview error connecting to Hapmap site - please try later)<br/>\n')
        outf.write('<br><div><hr><ul>\n')
        for i, data in enumerate( flist ):
            dn = os.path.split(data)[-1]
            if dn[:3] <> 'all':
                continue
            newdn = dn.translate(ftran)
            if dn <> newdn:
                os.rename(os.path.join(self.outfpath,dn),os.path.join(self.outfpath,newdn))
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
                os.rename(os.path.join(self.outfpath,dn),os.path.join(self.outfpath,newdn))
                dn = newdn
            dnlabel = dn
            ext = dn.split('.')[-1]
            if dn == 'allnup.pdf':
                dnlabel = 'All pdf plots on a single page'
            elif dn == 'alljoin.pdf':
                dnlabel = 'All pdf plots, each on a separate page'
            elif ext == 'info':
                dnlabel = '%s map data for Haploview input' % self.title
            elif ext == 'ped':
                dnlabel = '%s genotype data for Haploview input' % self.title
            elif dn.find('CEU') <> -1 or dn.find('YRI') <> -1 or dn.find('CHB_JPT') <> -1: # is hapmap
                dnlabel = 'Hapmap data'
            if ext == 'TAGS' or ext == 'TESTS' or ext == 'CHAPS':
                dnlabel = dnlabel + ' Tagger output'
            outf.write('<li><a href="%s">%s - %s</a></li>\n' % (dn,dn,dnlabel))
        outf.write('</ol><br>')
        outf.write("</div><div><hr>Job Log follows below (see %s)<pre>" % self.logfn)
        s = file(self.log_file,'r').readlines()
        s = '\n'.join(s)
        outf.write('%s</pre><hr></div>' % s)
        outf.write('</body></html>')
        outf.close()
        if self.useTemp:
            try:
                os.unlink(self.tempMapName)
                os.unlink(self.tempPedName)
            except:
                pass
        
if __name__ == "__main__":
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
    if len(sys.argv) < 16:
        s = '##!%s: Expected 16 params in sys.argv, got %d (%s)' % (progname,len(sys.argv), sys.argv)
        print s
        sys.exit(1)
    ld = ldPlot(argv = sys.argv)
    ld.doPlots()
    ld.writeHtml()



