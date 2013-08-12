#!/usr/local/bin/python
# hack to run and process a plink tdt
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

import sys,math,shutil,subprocess,os
from os.path import abspath
imagedir = '/static/rg' # if needed for images

def xformTDT(infname='',resf='',outtype='wig',outfname='',name='foo',mapf='/usr/local/galaxy/data/rg/ped/x.map'):
    """munge a plink .tdt file into either a ucsc track or an xls file
  CHR         SNP  A1:A2      T:U_TDT       OR_TDT    CHISQ_TDT        P_TDT
   0   MitoT217C    2:3          0:0           NA           NA           NA
   0   MitoG228A    1:4          0:0           NA           NA           NA
   0   MitoT250C    2:3          0:0           NA           NA           NA
    map file has
    1       rs4378174       0       003980745
    1       rs10796404      0       005465256
    1       rs2697965       0       014023092

    """
    print >> sys.stdout,'xformTDT got resf=%s, outtype=%s, outfname=%s' % (resf,outtype,outfname)
    res = []
    if outtype == 'gg': # genome graphs style - rs p logp with header
        res.append('rs\tlog10TDTP\tFakeTDTOR\tTDTOR') # header
    rsdict = {}
    if outtype == 'wig': # need a map file!
        if not mapf:
                sys.stderr.write('rgPbat called with requested wig format but no map file provided - cannot determine locations')
                sys.exit(1)        
        map = file(mapf,'r')
        for l in map: # plink map 
            ll = l.strip().split()
            if len(ll) >= 3:
                rs=ll[1].strip()
                chrom = ll[0]
                offset = ll[3]
                rsdict[rs] = (chrom,offset)
        s = '''track type=wiggle_0 name="%s" description="Pbat results from %s" visibility=full color=0,0,255 altColor=0,255,0 priority=priority autoScale=on gridDefault=on maxHeightPixels=90:90:30 graphType=bar''' % (name,infname)
	res.append(s)
    f = open(resf,'r')
    headl = f.next().strip()
    headl = headl.split()
    chrpos = headl.index('CHR')
    rspos = headl.index('SNP')
    transpos = headl.index('A1:A2')
    orpos = headl.index('OR_TDT')
    ppos = headl.index('P_TDT')
    chisqpos = headl.index('CHISQ_TDT')
    wewant = [chrpos,rspos,transpos,orpos,ppos,chisqpos]
    llen = len(headl)
    lnum = anum = 0
    for l in f:
        lnum += 1
        ll = l.split()
        if len(ll) >= llen: # valid line
            chr,snp,trabs,orat,p,chi = [ll[x] for x in wewant]
            snp = snp.strip()
            if p == 'NA' or orat == 'NA':
               lp = 0.0
               fp = 1.0
               orat = '1.0'
               fakeorat = '1.0'
            else:
              try:
                fp = float(p)
                if fp <> 0:
                   lp = -math.log10(fp)
              except:
                lp = fp = 0.0
              try:
              	fakeorat = orat
              	if float(orat) < 1.0:
                  fakeorat = '%3.4f' % (1.0/float(orat)) # invert so large values big
              except:
                fakeorat = '1.0'
            if outtype == 'gg':
                    outl = '\t'.join([snp,'%3.3f' % lp,fakeorat,orat])
	    if outtype == 'wig': # wiggle track
		    l = []
                    slp = '%5.5f' % lp
                    chrom,offset = rsdict.get(snp,(None,None))
                    if chrom == None:
                       sys.stderr.write('# rgPbat cannot make a wig file - rs %s not found in map file %s' % (snp,mapf))
                       sys.exit(1) 
        	    try:
            		epos = '%d' % (int(offset) + 1) # mapinfo column
        	    except:
            		print 'bad epos - offset =',offset
                        epos = offset   
                    outl = 'chr%s\t%s\t%s\t%s' % (chrom,offset,epos,slp)
            res.append(outl)
    f = file(outfname,'w')
    res.append('')
    f.write('\n'.join(res))
    f.close()

                
if __name__ == "__main__":
    # plinkTDT.py $i $name $outformat $out_file1 $logf $map
    if len(sys.argv) < 6:
       s = 'plinkTDT.py needs 5 params - got %s \n' % (sys.argv)
       sys.stderr.write(s) # print >>,s would probably also work?
       sys.exit(0)
    print >> sys.stdout,'rgPbat.py called with %s' % sys.argv
    bfname = sys.argv[1]
    name = sys.argv[2]
    outformat = sys.argv[3]
    outfname = sys.argv[4]
    logf = sys.argv[5]
    if len(sys.argv) >= 7:
       map_file = sys.argv[6] # or use hardcoded one at top of this file kludge
    else:
       map_file = None
    cdir = os.getcwd()
    me = sys.argv[0]
    mypath = abspath(os.path.join(cdir,me)) # get abs path to this python script
    shpath = abspath(os.path.sep.join(mypath.split(os.path.sep)[:-1]))
    alogf = abspath(os.path.join(cdir,logf)) # absolute paths
    if map_file:
        amapf = abspath(os.path.join(cdir,map_file)) # absolute paths
    aoutf = abspath(os.path.join(cdir,outfname)) # absolute paths
    workdir = abspath(os.path.sep.join(mypath.split(os.path.sep)[:-1])) # trim end off './database/files/foo.dat' 
    os.chdir(workdir)
    sto = file(alogf,'w')
    plink = '/usr/local/bin/plink'
    vcl = [plink,'--bfile',bfname,'--out',name,'--mind','0.5','--tdt']
    sto.write('rgPbat.py: workdir=%s, bfname=%s, logf=%s, argv = %s\n' % (workdir,bfname,alogf, sys.argv)) 
    sto.write('rgPbat.py: vcl=%s' % (' '.join(vcl))) 
    #'/usr/local/bin/plink','/usr/local/bin/plink',pc1,pc2,pc3)
    #os.spawnv(os.P_WAIT,plink,vcl)
    p=subprocess.Popen(' '.join(vcl),shell=True,stdout=sto)
    retval = p.wait()
    shutil.copy('%s.log' % name,alogf)
    resf = '%s.tdt' % name # plink output is here we hope
    xformTDT(bfname,resf,outformat,aoutf,name,amapf) # leaves the desired summary file
    os.chdir(cdir)
    sto.close()



