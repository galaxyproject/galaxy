# parse affy hapmap data into separate ped files
# in preparation for importing into the framingham
# data in eigenstrat format
# what's another 270 samples on top of the 9200 we already
# have.. :)

# challenges include reading affy annotation
# dealing with the missing affy ids - in the data
# but not the annotation
# reading the genotypes and translating affyid's into
# dbsnp rs
# writing the pedigree data
# writing the map files
# for founders only separately - important for eigenstrat...

import csv, os, sys


def readHapMapPed(races=['CEU','CHB','YRI','JPT']):
    """read the hapmap pedigree files and construct a
    dictionary for sample id to pedigree lookup
    remember race - useful for parsing it out
    """
    samptoped = {}
    for race in races:
        infname = 'pedinfo2sample_%s.txt' % race
        f = open(infname,'r')
        ll = f.readlines()
        for l in ll:
            sl = l.strip().split()
            if len(sl) >= 7:
                pedid,iid,pid,mid,gender,iurn,surn = l.strip().split()
                sampid = surn.split(':')[-2] # eg NA12003
                samptoped[sampid] = (pedid,iid,pid,mid,gender,race)
            elif len(sl) == 6: # eesh different (no famid!) for the jpt/chb non families
                # why not put a dummy value here for heaven's sake, next time you make these?
                iid,pid,mid,gender,iurn,surn = l.strip().split()
                sampid = surn.split(':')[-2] # eg NA12003
                iid = sampid[2:]
                samptoped[sampid] = (iid,iid,pid,mid,gender,race)
            else:
                print 'cannot parse pedid,iid,pid,mid,gender,iurn,surn sl=%s' % sl
    return samptoped

class illAnno550F:
    """iterable to return file lines as field lists
    mysql and sqlite expect for executemany
    Inserts a Null value for primary key which sqlite will autoincrement
    affy csv file header:
    IlmnID,Name,IlmnStrand,SNP,AddressA_ID,AlleleA_ProbeSeq,AddressB_ID,AlleleB_ProbeSeq,
    GenomeBuild,Chr,MapInfo,Ploidy,Species,Source,SourceVersion,SourceStrand,SourceSeq,
    TopGenomicSeq,BeadSetId
    this version ONLY returns probe_set_id, affy_SNP_id, dbsnpid, chrom, pos, strand as
    defined in wewant below
    """
    def __init__(self,fname=''):
        self.wewant = ['Name','IlmnID','SNP','Chr','MapInfo'] # this determines which fields we keep!
        self.f = file(fname,'r')
        header = ''
        while header.strip() <> '[Assay]':
            header = self.f.next()
        header = self.f.next()
        fieldnames = header.strip().split(',') # is csv
        fieldnames = [x.replace(' ','_') for x in fieldnames]
        fieldnames = [x.replace('-','') for x in fieldnames]
        fieldnames = [x.replace('"','') for x in fieldnames] # get rid of quotes
        self.header = fieldnames
        if debug:
            print 'header=%s' % fieldnames
            print 'wewant=%s' % self.wewant
        self.wewantin = [self.header.index(x) for x in self.wewant] # keep these fields
        self.lnum = 1
        self.fname = fname
        self.started = time.time()

    def next(self):
        try:
            line = self.f.next()
            self.lnum += 1
        except:
            raise StopIteration
        ll = line.strip().split(',')
        ll = [x.replace('"','') for x in ll] # remove remaining quotes from csv
        ll = [ll[x] for x in self.wewantin] # filter only the fields we want to save
        ll.insert(0,None) # for autoincrement pk
        ll = tuple(ll)
        if self.lnum % 10000 == 0:
            if debug:
                dur = time.time() - self.started
                print 'illAnnoF reading line %d of %s = %5.2f recs/sec' % (self.lnum,self.fname,self.lnum/dur)
        return ll

    def __iter__(self):
        return self

def loadIll550k(infname='HumanHap550v3_A.csv', dbname='HumanHap550',tablename='HumanHap550v3_A'):
    """load illumina 550k data                     
    header row is row 8           
    IlmnID,Name,IlmnStrand,SNP,AddressA_ID,AlleleA_ProbeSeq,AddressB_ID,AlleleB_ProbeSeq,
    GenomeBuild,Chr,MapInfo,Ploidy,Species,Source,SourceVersion,SourceStrand,SourceSeq,
    TopGenomicSeq,BeadSetId 


    """          
    con = MySQLdb.Connect('hg', 'refseq', 'Genbank')
    curs = genome.cursor() # use default cursor
    fieldnames = ['id','rs','chrom','offset']
    nfields = len(fieldnames)
    varss = '''id INT UNSIGNED NOT NULL AUTO_INCREMENT, rs char(12), chrom varchar(10), offset int(12),       
    index rsindex (rs), index chromrs (chrom, rs), primary key (id)'''
    sql = 'DROP TABLE IF EXISTS %s.%s' % (dbname,tablename) # start again each time
    curs.execute(sql)
    sql = 'CREATE TABLE %s.%s (%s)' % (dbname,tablename,varss)       
    curs.execute(sql)
    varplaces = ','.join(['?']*nfields) # sqlite uses qmarks
    insertsql = 'INSERT INTO %s.%s (%s) values (%s)' % (dbname,tablename,','.join(fieldnames),varplaces)
    f = illAnno550F(infname)
    curs.executemany(insertsql,f) # just pass a file iterator!@
    con.commit() # only at end of each file to speed things up
    print 'wrote %d snps from %s' % (nsnps,infname)


def getAffy500kMarkers():
    """use affy's annotation files
[rerla@meme affy500raw]$ head Mapping250K_Sty.na24.annot.csv
##For information about the Annotation file content, please see the bundled README file.
"Probe Set ID","Affy SNP ID","dbSNP RS ID","Chromosome","Physical Position","Strand","ChrX pseudo-autosomal region 1","Cytoband","Flank","Allele 
A","Al"
"SNP_A-1780358","10001174","rs17325399","5","54442707","+","0","q11.2","ggataatacatattca[A/G]accaataacatacagc","A","G","NM_152623 // downstream 
// 1873"
"SNP_A-1780551","10003881","rs12454921","18","52924726","-","0","q21.31","ggatatcaaagttcca[A/G]gatgtcttttgaggtt","A","G","NM_052834 // 
downstream // 76"


    """
    rslist = []
    fskel = 'Mapping250K_%s.na24.annot.csv'
    affyid = "Probe Set ID"
    crs= 'dbSNP RS ID' # csv reader column for rs number in affy annotation file
    cstart= 'Physical Position' # pompous pratt whoever named these columns
    cchrom= 'Chromosome'
    aallele = "Allele A"
    ballele = "Allele B"
    for chip in ['Sty','Nsp']:
        fname = fskel % chip
        affyf = file(fname,'rb',2**30)
        crap = affyf.readline() # why oh why?
        f = csv.DictReader(affyf) # whew
        for n,row in enumerate(f):
            if n % 100000 == 0:
                print 'at row %d in %s' % (n,fname)
            rs = row[crs]
            if rs[0] <> '-':
                chrom=row[cchrom]
                start=row[cstart]
                id = row[affyid]
                aA = row[aallele]
                aB = row[ballele]
                adict = {'A':aA,'B':aB,'N':'N'}
                try:
                    start = int(start)
                    rslist.append((chrom,start,rs,id,adict))
                except:
                    print 'rs %s start = %s' % (start,rs)
    rslist.sort()
    affyids = [x[3] for x in rslist]
    rs = [x[2] for x in rslist]
    affydict=dict(zip(affyids,rs)) # lookup to translate
    return rslist,affydict


def readAffy500kHapMap(races=['CEU','CHB','YRI','JPT']):
    """
    read the affy hapmap genotypes and note which rs numbers have been
    parsed
    [rerla@hg affyhapmap]$ head Nsp_HapMap270.brlmm.call 
        NA06985 NA06991 NA06993 NA06994 NA07000 NA07019 NA07022 NA07029 NA07034 NA07048 NA07055 NA07056 NA07345 NA07348 NA07357 NA10830 NA10831 
NA108350
SNP_A-1780270   BB      AB      AA      AA      AB      AB      AB      AA      BB      AB      AA      BB      AA      AA      AA      AA      
AB     B

    """
    rslist,affydict = getAffy500kMarkers()
    digests = ['Nsp','Sty']
    idgt = None
    nofind = 0
    pedrslist = []
    for digest in digests:
        infname = '%s_HapMap270.brlmm.call' % digest
        f = file(infname,'r')
        head = f.readline()
        ids = head.strip().split()
        if idgt == None: # only do this first time
            idgt = {}
            for id in ids:
                idgt[id] = []
        for n,l in enumerate(f):
            if n % 100000 == 0:
                print 'at line %d in %s' % (n,infname)
            if l.strip() > '':
                ll = l.strip().split()
                snp = ll[0]
                rs = affydict.get(snp,None)
                if rs == None:
                    nofind += 1
                    if nofind % 1000 == 0:
                        print 'Cannot find affyid %s in affyid dictionary from annotation - WTF*%d?' % (snp,
                                                                                                    nofind)
                else:
                    pedrslist.append(rs)
                    genos = ll[1:]
                    for n,id in enumerate(ids):
                        idgt[id].append(genos[n]) # build transposed dataset for each id
    return idgt,rslist,pedrslist


def writePed(idgt={}, race=None, samptoped={}, rslist=[], pedrslist=[], doFounders=1):
    """write the transposed list of genotypes for each subject to a
    ped file for each race
    """
    pedrsdict=dict(zip(pedrslist,pedrslist)) # for lookups
    map = []
    for chrom,start,rs,id,adict in rslist:
        if pedrsdict.get(rs,None): # only include if in pedigree file
            map.append('%s\t%s\t0\t%d\n' % (chrom,rs,start))
            pedrsdict[rs] = chrom,start,rs,id,adict
    map = ''.join(map) # one gimungous string
    amapfname = 'affyHM_%s.map' % race
    fmapfname = 'affyHM_%s_founders.map' % race
    mapf = file(amapfname,'w')
    mapf.write(map)
    mapf.close()
    mapf = file(fmapfname,'w')
    mapf.write(map)
    mapf.close()
    del map
    print 'wrote map files %s and %s' % (amapfname,fmapfname)
    apfname = 'affyHM_%s.ped' % race
    fpfname = 'affyHM_%s_founders.ped' % race
    af = file(apfname,'w')
    if doFounders:
        ff = file(fpfname,'w')    
    ids = idgt.keys()
    ids.sort()
    ares = []
    fres = []
    for id in ids:
        ok = 1
        try:
            pedid,iid,pid,mid,gender,thisrace = samptoped[id]
        except:
            print '##Strange, cannot find id %s in the hapmap pedigree data structure' % id
            ok = 0
        if ok and thisrace == race:
            genos = idgt[id] # ['AA','...']
            outg = []
            if len(genos) < len(pedrslist):
                print '##problem for id %s - idgt[id] has %d snps, pedrslist has %d' % (id,len(genos),len(pedrslist))
            else:
                for i in range(len(pedrslist)): # only output rs for which we got anno
                    rs = pedrslist[i]
                    if len(pedrsdict[rs]) == 5: # not just rs
                        chrom,start,rs,id,adict = pedrsdict[rs]                        
                        gs = genos[i]
                        gt = [adict[x] for x in gs] # translate stooopid a and b
                        outg.append(' '.join(gt)) 
                row = [pedid,iid,pid,mid,gender,'1'] # unaffected
                row += outg
                s = ' '.join(row)
                af.write(s)
                af.write('\n')
                if doFounders and mid == '0' and pid == '0': # no parents
                    ff.write(s) # include in founders only
                    ff.write('\n')
    af.close()
    if doFounders:
        ff.close()


def parseAffyhapmap(races=['CEU','CHB','YRI','JPT'],doF=[1,0,1,0]):
    samptoped = readHapMapPed(races=races)
    idgt,rslist,pedrslist = readAffy500kHapMap(races=races)
    for i,race in enumerate(races):
        doFounders=doF[i] # no separate founders for JPT or CHB
        print 'writing %s ped files' % race
        writePed(idgt=idgt,race=race,samptoped=samptoped,rslist=rslist,pedrslist=pedrslist,doFounders=doFounders)


if __name__ == "__main__":
    parseAffyhapmap()

  