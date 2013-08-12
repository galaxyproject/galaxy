# what to do if > 2 alleles after merge?
# may be an error or may be a strand flip
# ? estimate major/minor alleles and recode optionally
# ross lazarus oct 17 2007
# merge ped files
# need a series of ped files
# check the maps and find the LCD
# create a new ped with only the LCD snps
# ross lazarus oct 2007 for rgenetics/galaxy

import os, sys,array

def getLCD(lbase=[]):
    """read the maps and get the set of unique rs 
    """
    listmf = []
    rsdict = {}
    for i,basename in enumerate(lbase): # for each basename to be included
        mf = file('%s.map' % basename,'r').readlines()
        lmap = [x.strip().split() for x in mf] 
        rslist = [x[1] for x in lmap] # chrom rs gendist physdist
        for x in lmap:
            rsdict[x[1]] = (x[0],int(x[3]),x[1]) # key by chrom,offset,rs
        setrs = set(rslist)
        listmf.append(setrs) # list of map lines for processing
    lcd = listmf.pop(0) # start with first - order doesn't matter
    for setrs in listmf:
        lcd = lcd & setrs # intersection
    lcd = list(lcd) # now have lowest common denom as a list of rs
    lcdmap = [rsdict[rs] for rs in lcd] # restore chrom,offset,rs for rs to keep
    lcdmap.sort() # now in genomic order
    print 'got lcdmap=',lcdmap[:10]
    return lcdmap # sorted common map


def subsetPed(basename="",lcdmap = [],faff='1', ofaff='2'):
    """return founder and offspring subset of basename.ped containing only the markers in lcd
    lcd contains a sorted list of (chrom,offset,rs) for the common snps in all maps
    we need to keep genotypes all in the same column order
    """
    mf = file('%s.map' % basename,'r').readlines()
    lmap = [x.strip().split() for x in mf]
    rscols = {} # lookup marker table
    colrs = [] # lookup rs from column
    for i,m in enumerate(lmap): # get columns to keep in the order we want them
        rscols[m[1]] = i # keep track of where each rs is in this map
        colrs.append(m[1]) # and keep the list of rs for tracking alleles
    wewant = [rscols[x[2]] for x in lcdmap] # columns we want to keep
    print '#Subsetped faff=%s ofaff=%s keeping %d (%s) of potential lcd %d for %s' % \
          (faff,ofaff,len(wewant),wewant[:20],len(lcdmap),basename)
    pf = file('%s.ped' % basename,'r')
    ogeno = [] # offspring new lines
    fgeno = [] # founders
    oped = [] # for pedigrees
    fped = []
    rsadict = {} # keep a count of alleles - seems to be a problem
    for i,l in enumerate(pf):
        if (i+1) % 500 == 0:
            print '%s at line %d' % (basename,i+1)
        ll = l.strip().split()
        ped = ll[:6]
        founder = (ll[2] == '0' and ll[3] == '0') 
        aff = faff
        if not founder:
            aff = ofaff
        ped[5] = aff # adjust as needed
        if founder:
            fped.append(ped)
        else:
            oped.append(ped)
        gt = ll[6:]
        geno = []
        for snp in wewant: # columns in order
            thisrs = colrs[snp]
            base = snp*2
            g1 = gt[base]
            g2 = gt[base+1]
            geno.append(g1)
            geno.append(g2)
            if not rsadict.get(thisrs,None):
                rsadict[thisrs] = {}
            if g1 <> '0':
                if not rsadict[thisrs].get(g1,None):
                    rsadict[thisrs][g1] = 1
                else:
                    rsadict[thisrs][g1] += 1                
            if g2 <> '0':
                if not rsadict[thisrs].get(g2,None):
                    rsadict[thisrs][g2] = 1
                else:
                    rsadict[thisrs][g2] += 1
        keepgt = array.array('c',geno)
        if founder:
            fgeno.append(keepgt)
        else:
            ogeno.append(keepgt)
    print '#Subsetped %s %d fgeno %d ogeno' % (basename,len(fgeno),len(ogeno))
    return fped,oped,fgeno,ogeno,rsadict
                          

def mergePed(bnlist=[],faff=[],ofaff=[],newbasename='newped',fo=0):
    """
    take a list of basenames, get lcd and merge
    set founder affection according to faff flag
    and offspring according to ofaff flag
    """
    lcdmap = getLCD(bnlist) # list of chr,offset,rs for all snp common to all files
    print 'got %d lcd snps-%s' % (len(lcdmap),lcdmap[:5])
    cfped = []
    coped = []
    cfgeno = []
    cogeno = []
    allrsa = {}
    ignorers = {}
    for i,basename in enumerate(bnlist):
        fped,oped,fgeno,ogeno,trsadict = subsetPed(basename,lcdmap,faff[i],ofaff[i])
        print '%s gave %d fgeno' % (basename,len(fgeno))
        for rs in trsadict.keys():
            tk = trsadict[rs].keys()
            if len(tk) > 2:
                print 'for %s, rs %s has alleles %s' % (basename, rs, trsadict[rs])
            if not allrsa.get(rs,None):
                allrsa[rs] = {}
            for a in tk:
                if not allrsa[rs].get(a,None):
                    allrsa[rs][a] = trsadict[rs][a]
                else:
                    allrsa[rs][a] += trsadict[rs][a]
            tk = allrsa[rs].keys()
            if len(tk) > 2 and not ignorers.get(rs,None): # new
                #print 'After merge basename %s, rs %s has alleles %s' % (basename, rs,allrsa[rs])
                ignorers[rs] = rs
        cfped += fped
        coped += oped
        cfgeno += fgeno
        cogeno += ogeno
    print 'after merge all have %d fgeno and %d ogeno' % (len(cfgeno),len(cogeno))
    # now have offspring and founder rows in lcdmap order
    # write map file
    print '### found %d markers > 2 alleles' % (len(ignorers.keys()))
    keepmarkers = [x for x in range(len(lcdmap)) if not ignorers.get(lcdmap[x][2],None)]
    newmap = ['\t'.join((lcdmap[x][0],lcdmap[x][2],'0','%d' % lcdmap[x][1])) for x in keepmarkers] # chrom,offset,rs
    f = file('%s.map' % newbasename,'w')
    f.write('%s\n' % '\n'.join(newmap))
    f.close()
    for i,geno in enumerate(cfgeno): # convert each array into a list and keep the good markers
        gs = ''.join(['%s%s' % (geno[2*x],geno[2*x + 1]) for x in keepmarkers])
        g = array.array('c',gs) # good ones
        cfgeno[i] = g # replace
    print 'cfgeno converted'
    if not fo: # not founders only - note arrays are not lists!
        cfped += copy.copy(coped) #
        del coped
        for i,geno in enumerate(cogeno): # convert each array into a list and keep the good markers
            gs = ''.join(['%s%s' % (geno[2*x],geno[2*x + 1]) for x in keepmarkers])
            g = array.array('c',gs) # good ones
            cfgeno.append(g) # extend founders
        del cogeno
    print 'after if not fo now have %d cfgeno' % (len(cfgeno))
    f = file('%s.ped' % newbasename,'w')
    for n,ped in enumerate(cfped):
        l = ' '.join(ped + list(cfgeno[n]))
        if n % 100 == 0 and n > 0:
            print 'writing line %d' % n
        f.write(l)
        f.write('\n')
    f.close()
    print 'wrote %d map rows and %d ped rows to %s' % (len(newmap),len(cfped),newbasename)


if __name__ == "__main__":
    """expect a , delim list of basenames and paths of course quoted as sys.argv[1]
    a , delim list of founder affection states and of offspring affection states as 2 and 3
    """
    progname = sys.argv[0]
    if len(sys.argv) < 3:
        print     """expect a comma delim list of basenames and paths, a list of founder affection states
a list of offspring affection states and a flag for founders only as parameters - eg
%s hm550k_chr22_CEUYRIaff hm550k_chr22_CEU,hm550k_chr22_YRI '1,1' '1,2' 0""" % progname
        sys.exit()
    newbase = sys.argv[1].replace(' ','_')
    lbase = sys.argv[2].split(',')
    faff = sys.argv[3].split(',')
    ofaff = sys.argv[4].split(',')
    fo = sys.argv[5].lower() in ['1','true']
    lcdmap = getLCD(lbase)
    lcdmap = lcdmap[:100]
    mergePed(bnlist=lbase,faff=faff,ofaff=ofaff,newbasename=newbase,fo=fo)

    
    