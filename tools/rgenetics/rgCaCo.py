#!/usr/local/bin/python
# hack to run and process a plink case control association
# expects args as  
# bfilepath outname jobname outformat (wig,xls)
# ross lazarus 
# for wig files, we need annotation so look for map file or complain
"""
Parameters for wiggle track definition lines
All options are placed in a single line separated by spaces:

  track type=wiggle_0 name=track_label description=center_label \
        visibility=display_mode color=r,g,b altColor=r,g,b \
        priority=priority autoScale=on|off \
        gridDefault=on|off maxHeightPixels=max:default:min \
        graphType=bar|points viewLimits=lower:upper \
        yLineMark=real-value yLineOnOff=on|off \
        windowingFunction=maximum|mean|minimum smoothingWindow=off|2-16
"""

import sys,math,shutil,subprocess,os,time,tempfile,string
from os.path import abspath
from rgutils import timenow, plinke
imagedir = '/static/rg' # if needed for images
myversion = 'V000.1 April 2007'
verbose = False

def makeGFF(resf='',outfname='',logf=None,twd='.',name='track name',description='track description',topn=1000):
    """
    score must be scaled to 0-1000
    
    Want to make some wig tracks from each analysis
    Best n -log10(p). Make top hit the window.
    we use our tab output which has
    rs	chrom	offset	ADD_stat	ADD_p	ADD_log10p
    rs3094315	1	792429	1.151	0.2528	0.597223

    """

    def is_number(s):
        try:
            float(s)
            return True
        except ValueError:
            return False
    header = 'track name=%s description="%s" visibility=2 useScore=1 color=0,60,120\n' % (name,description)          
    column_names = [ 'Seqname', 'Source', 'Feature', 'Start', 'End', 'Score', 'Strand', 'Frame', 'Group' ]
    halfwidth=100
    resfpath = os.path.join(twd,resf)
    resf = open(resfpath,'r')
    resfl = resf.readlines() # dumb but convenient for millions of rows
    resfl = [x.split() for x in resfl]
    headl = resfl[0]
    resfl = resfl[1:]
    headl = [x.strip().upper() for x in headl]
    headIndex = dict(zip(headl,range(0,len(headl))))
    whatwewant = ['CHR','RS','OFFSET','LOG10ARMITAGEP']
    wewant = [headIndex.get(x,None) for x in whatwewant]
    if None in wewant: # missing something
       logf.write('### Error missing a required header from %s in makeGFF - headIndex=%s\n' % (whatwewant,headIndex))
       return
    ppos = wewant[3] # last in list
    resfl = [x for x in resfl if x[ppos] > '' and x[ppos] <> 'NA']
    resfl = [(float(x[ppos]),x) for x in resfl] # decorate
    resfl.sort()
    resfl.reverse() # using -log10 so larger is better
    pvals = [x[0] for x in resfl] # need to scale
    resfl = [x[1] for x in resfl] # drop decoration  
    resfl = resfl[:topn] # truncate
    maxp = max(pvals) # need to scale
    minp = min(pvals)
    prange = abs(maxp-minp) + 0.5 # fudge
    scalefact = 1000.0/prange
    logf.write('###maxp=%f,minp=%f,prange=%f,scalefact=%f\n' % (maxp,minp,prange,scalefact))
    for i,row in enumerate(resfl):
        row[ppos] = '%d' % (int(scalefact*pvals[i])) 
        resfl[i] = row # replace
    outf = file(outfname,'w')
    outf.write(header)
    outres = [] # need to resort into chrom offset order
    for i,lrow in enumerate(resfl):
        chrom,snp,offset,p, = [lrow[x] for x in wewant]
        gff = ('chr%s' % chrom,'rgCaCo','variation','%d' % (int(offset)-halfwidth),
               '%d' % (int(offset)+halfwidth),p,'.','.','%s logp=%1.2f' % (snp,pvals[i]))
        outres.append(gff)
    outres = [(x[0],int(x[3]),x) for x in outres] # decorate
    outres.sort() # into chrom offset
    outres=[x[2] for x in outres] # undecorate
    outres = ['\t'.join(x) for x in outres]    
    outf.write('\n'.join(outres))
    outf.write('\n')
    outf.close()


def plink_assocToGG(plinkout="hm",tag='test'):
   """ plink --assoc output looks like this
   #  CHR         SNP   A1      F_A      F_U   A2        CHISQ            P           OR 
   #   1   rs3094315    G   0.6685   0.1364    A        104.1    1.929e-24        12.77 
   # write as a genegraph input file
   """
   inf = file('%s.assoc' % plinkout,'r')
   outf = file('%sassoc.xls' % plinkout,'w')
   res = ['rs\tlog10p%s\tFakeInvOR%s\tRealOR%s' % (tag,tag,tag),] # output header for ucsc genome graphs
   head = inf.next()
   for l in inf:
    ll = l.split()
    if len(ll) >= 8:
      p = float(ll[7])
      if p <> 'NA': # eesh
          logp = '%9.9f' % -math.log10(p)
      else:
          logp = 'NA'
      try:
         orat = ll[8]
      except:
         orat = 'NA'
      orat2 = orat
      # invert large negative odds ratios
      if float(orat) < 1 and float(orat) > 0.0:
         orat2 = '%9.9f' % (1.0/float(orat))
      outl = [ll[1],logp, orat2, orat]
      res.append('\t'.join(outl))
   outf.write('\n'.join(res))
   outf.write('\n')
   outf.close()
   inf.close()

def xformModel(infname='',resf='',outfname='',
               name='foo',mapf='/usr/local/galaxy/data/rg/ped/x.bim',flog=None):
    """munge a plink .model file into either a ucsc track or an xls file
    rerla@meme ~/plink]$ head hmYRI_CEU.model 
    CHR         SNP     TEST            AFF          UNAFF        CHISQ   DF            P
    1   rs3094315     GENO       41/37/11        0/24/64           NA   NA           NA
    1   rs3094315    TREND         119/59         24/152        81.05    1    2.201e-19
    1   rs3094315  ALLELIC         119/59         24/152        104.1    1    1.929e-24
    1   rs3094315      DOM          78/11          24/64           NA   NA           NA

    bim file has
[rerla@beast pbed]$ head plink_wgas1_example.bim
1	rs3094315	0.792429	792429	G	A
1	rs6672353	0.817376	817376	A	G
    """
    if verbose:
        print 'Rgenetics rgCaCo.xformModel got resf=%s,  outfname=%s' % (resf,outfname)
    res = []
    rsdict = {}       
    map = file(mapf,'r')
    for l in map: # plink map 
        ll = l.strip().split()
        if len(ll) >= 3:
            rs=ll[1].strip()
            chrom = ll[0]
            if chrom.lower() == 'x':
                chrom='23'
            elif chrom.lower() == 'y':
                chrom = 24
            elif chrom.lower() == 'mito':
                chrom = 25
            offset = ll[3]
            rsdict[rs] = (chrom,offset)
    res.append('rs\tChr\tOffset\tGenop\tlog10Genop\tArmitagep\tlog10Armitagep\tAllelep\tlog10Allelep\tDomp\tlog10Domp') 
    f = open(resf,'r')
    headl = f.readline()
    if headl.find('\t') <> -1:
       headl = headl.split('\t')
       delim = '\t'
    else:
       headl = headl.split()
       delim = None
    whatwewant = ['CHR','SNP','TEST','AFF','UNAFF','CHISQ','P']
    wewant = [headl.index(x) for x in whatwewant]
    llen = len(headl)
    lnum = anum = 0
    lastsnp = None # so we know when to write out a gg line
    outl = {}
    f.seek(0)
    for lnum,l in enumerate(f):
        if lnum == 0:
            continue
        ll = l.split()
        if delim:
           ll = l.split(delim)
        if len(ll) >= llen: # valid line
            chr,snp,test,naff,nuaff,chi,p = [ll[x] for x in wewant]
            snp = snp.strip()
            chrom,offset = rsdict.get(snp,(None,None))
            anum += 1
            fp = 1.0 # if NA
            lp = 0.0
            try:
                fp = float(p)
                if fp > 0:
                  lp = -math.log10(fp)
                else:
                    fp = 9e-100
                    flog.write('### WARNING - Plink calculated %s for %s p value!!! 9e-100 substituted!\n' % (p,test))
                    flog.write('### offending line #%d in %s = %s' % (lnum,l))
            except:
                pass
            if snp <> lastsnp:
                if len(outl.keys()) > 3:
                    sl = [outl.get(x,'?') for x in ('snp','chrom','offset','GENO','TREND','ALLELIC','DOM')]
                    res.append('\t'.join(sl)) # last snp line
                outl = {'snp':snp,'chrom':chrom,'offset':offset} # first 3 cols for gg line
                lastsnp = snp # reset for next marker
            #if p == 'NA':
            #      p = 1.0 
            # let's pass downstream for handling R is fine?
            outl[test] = '%s\t%f' % (p,lp)
    if len(outl.keys()) > 3:
        l = [outl.get(x,'?') for x in ('snp','chrom','offset','GENO','TREND','ALLELIC','DOM')]
        res.append('\t'.join(l)) # last snp line
    f = file(outfname,'w')
    res.append('')
    f.write('\n'.join(res))
    f.close()



                
if __name__ == "__main__":
    """
    # called as 
    <command interpreter="python">
        rgCaCo.py '$i.extra_files_path/$i.metadata.base_name' "$name" 
        '$out_file1' '$logf' '$logf.files_path' '$gffout'
    </command>    </command>
    """
    if len(sys.argv) < 7:
       s = 'rgCaCo.py needs 6 params - got %s \n' % (sys.argv)
       print >> sys.stdout, s
       sys.exit(0)
    bfname = sys.argv[1]
    name = sys.argv[2]
    killme = string.punctuation + string.whitespace
    trantab = string.maketrans(killme,'_'*len(killme))
    name = name.translate(trantab)
    outfname = sys.argv[3]
    logf = sys.argv[4]
    logoutdir = sys.argv[5]
    gffout = sys.argv[6]
    topn = 1000
    try:
        os.makedirs(logoutdir)
    except:
        pass
    map_file = None
    me = sys.argv[0]
    amapf = '%s.bim' % bfname # to decode map in xformModel
    flog = file(logf,'w')
    logme = []
    cdir = os.getcwd()
    s = 'Rgenetics %s http://rgenetics.org Galaxy Tools, rgCaCo.py started %s\n' % (myversion,timenow())
    print >> sys.stdout, s # so will appear as blurb for file
    logme.append(s)
    if verbose:
        s = 'rgCaCo.py:  bfname=%s, logf=%s, argv = %s\n' % (bfname, logf, sys.argv) 
        print >> sys.stdout, s # so will appear as blurb for file
        logme.append(s)
    twd = tempfile.mkdtemp(suffix='rgCaCo') # make sure plink doesn't spew log file into the root!
    tname = os.path.join(twd,name)
    vcl = [plinke,'--noweb','--bfile',bfname,'--out',name,'--model']
    p=subprocess.Popen(' '.join(vcl),shell=True,stdout=flog,cwd=twd)
    retval = p.wait()
    resf = '%s.model' % tname # plink output is here we hope
    xformModel(bfname,resf,outfname,name,amapf,flog) # leaves the desired summary file
    makeGFF(resf=outfname,outfname=gffout,logf=flog,twd=twd,name='rgCaCo_TopTable',description=name,topn=topn)
    flog.write('\n'.join(logme))
    flog.close() # close the log used
    #shutil.copytree(twd,logoutdir)
    shutil.rmtree(twd) # clean up

