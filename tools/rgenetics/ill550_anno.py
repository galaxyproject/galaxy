# illumina sentrix annotation for ucsc wiggle tracks
# read the annotation csv file
# make a sqlite table of illumina id
# chromosome and offset for
# making wiggle tracks
# added routine to generate a test data set for
# the infinium pipeline with real hapmap family data
# yri + ceu families - 60 trios with as many infinium 550k snps



import time, sys, os, random

from pysqlite2 import dbapi2 as sqlite
import MySQLdb

try:
    import psyco
    psyco.full()
except:
    print 'no psyco :('
debug = 1

class ucscWig:
    """wiggle formatter 
    extracts chrom, offset, data as list
    writes this as a wiggle file for the ucsc browser
    """
    def __init__(self,name='Default name',description='Default description',
                 autoscale='on',maxHeightPixels=100,data=[]):
        """
        data assumed to be rs number followed by any number of numeric columns with
        some kind of header line
        http://genome.ucsc.edu/goldenPath/help/wiggle.html has
        track type=wiggle_0 name=track_label description=center_label \
        visibility=display_mode color=r,g,b altColor=r,g,b \
        priority=priority autoScale=on|off \
        gridDefault=on|off maxHeightPixels=max:default:min \
        graphType=bar|points viewLimits=lower:upper \
        yLineMark=real-value yLineOnOff=on|off \
        windowingFunction=maximum|mean|minimum smoothingWindow=off|2-16
        """
        self.data=data
        self.name=name
        self.description=description
        self.autoscale=autoscale
        self.maxHeightPixels=maxHeightPixels

    def write(self):
        """eg from http://genome.ucsc.edu/goldenPath/help/wiggle.html has
track type=wiggle_0 name="variableStep" description="variableStep format" \
    visibility=full autoScale=off viewLimits=0.0:25.0 color=255,200,0 \
    yLineMark=11.76 yLineOnOff=on priority=10
variableStep chrom=chr19 span=150
59304701 10.0
59304901 12.5
59305401 15.0
59305601 17.5
59305901 20.0
59306081 17.5
59306301 15.0
59306691 12.5
59307871 10.0
        """
        res = []
        s = '''track type=wiggle_0 name="%s" description="%s"
            autoScale=%s''' % (self.name,self.description,self.autoscale)
        res.append(s)
        for d in self.data:
            res.append('\t'.join(d)) # d is a list - it must be formatted right
        

class dbsnpAnno:
    """
    sqlite table for dbsnp entries. All of them...
    """
    def __init__(self,infname='seq_snp.md', dbname='dbsnp125',tablename='dbsnp'):
        """
        'feature_name','chr_orient','chromosome','chr_start'
        """
        self.infname = infname # current refseq snp mapping file
        self.dbname = dbname
        self.tablename=tablename
        self.con = sqlite.connect(dbname) #,isolation_level=None)
        # Get a Cursor object that operates in the context of Connection con:
        self.cur = self.con.cursor()
        fieldtypes = ['INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL','text','text','text','text','text']
        fieldnames = ['id','rs','strand','chr','offset']
        self.fieldnames = fieldnames
        self.fieldtypes = fieldtypes
        nfields = len(fieldnames)
        self.createvars = ','.join(['%s %s' % (self.fieldnames[x],self.fieldtypes[x]) for x in range(nfields)])
        varplaces = ','.join(['?']*nfields) # sqlite uses qmarks
        self.insertsql = 'INSERT INTO %s (%s) values (%s)' % (self.tablename,','.join(self.fieldnames),varplaces)        

    def seq_snpAnnoF(self, fname=''):
        """iterable to return file lines as field lists
        mysql and sqlite expect for executemany
        Inserts a Null value for primary key which sqlite will autoincrement
        seq_snp.md.gz has #tax_id chromosome      chr_start       chr_stop        chr_orient
        contig  ctg_start       ctg_stop        ctg_orient   feature_name    feature_id
        feature_type    group_label     weight as header
        """
        self.wewant = ['feature_name','chr_orient','chromosome','chr_stop'] # the end pos is the one ucsc shows
        self.f = file(fname,'r')
        header = self.f.next()
        fieldnames = header.strip().split() # is space delim
        self.header = fieldnames
        if debug:
            print 'header=%s' % fieldnames
            print 'wewant=%s' % self.wewant
        self.wewantin = [self.header.index(x) for x in self.wewant] # keep these fields
        self.lnum = 1
        self.fname = fname
        self.started = time.time()
        lnum = 0
        for line in self.f:
            lnum += 1
            if lnum % 100000 == 0:
                print 'at lnum %d in %s' % (lnum,self.fname)
            ll = line.strip().split()
            if len(ll) > 12:
                group = ll[12].lower() # Celera or reference
                if group == 'reference':
                    ll = [ll[x] for x in self.wewantin] # filter only the fields we want to save
                    ll[-1] = '%d' % (int(ll[-1]) + 1) # (sorry, but) start is base before
                    ll.insert(0,None) # null for sqlite pk
                    yield ll

    def makeAnno(self):
        self.con = sqlite.connect(self.dbname) #,isolation_level=None)
        # Get a Cursor object that operates in the context of Connection con:
        self.cur = self.con.cursor()
        try:
            sql = 'drop table %s' % self.tablename
            self.cur.execute(sql)
        except:
            if debug:
                print 'no %s to drop this time!' % self.tablename
            else:
                pass
        sql = 'create table %s (%s)' % (self.tablename,self.createvars)
        self.cur.execute(sql)
        sql = 'PRAGMA synchronous=OFF'
        self.cur.execute(sql)
        sql = 'PRAGMA default_cache_size=5000'
        self.cur.execute(sql)
        sql = 'create index if not exists rs on %s (rs)' % self.tablename
        self.cur.execute(sql)
        #sql = 'create index if not exists pos on %s (chr,offset)' % self.tablename
        #self.cur.execute(sql)
        #sql = 'create index if not exists offset on %s (offset)' % self.tablename
        #self.cur.execute(sql)
        f = self.seq_snpAnnoF(self.infname)
        self.cur.executemany(self.insertsql,f) # just pass a file iterator!@
        self.con.commit() # only at end of each file to speed things up


       
class ill500Anno:
    """
    header row is row 8
    IlmnID,Name,IlmnStrand,SNP,AddressA_ID,AlleleA_ProbeSeq,AddressB_ID,AlleleB_ProbeSeq,
    GenomeBuild,Chr,MapInfo,Ploidy,Species,Source,SourceVersion,SourceStrand,SourceSeq,
    TopGenomicSeq,BeadSetId

    """
    
    def __init__(self,infname='HumanHap550v3_A.csv', dbname='HumanHap550',tablename='HumanHap550v3_A'):
        self.infname = infname # current sentrix 550k v3 anno file
        self.dbname = dbname
        self.tablename=tablename
        self.con = sqlite.connect(dbname) #,isolation_level=None)
        # Get a Cursor object that operates in the context of Connection con:
        self.cur = self.con.cursor()
        fieldtypes = ['INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL','text','text','text','text','text']
        fieldnames = ['id','rs','illid','snp','chr','offset']
        self.fieldnames = fieldnames
        self.fieldtypes = fieldtypes
        nfields = len(fieldnames)
        self.createvars = ','.join(['%s %s' % (self.fieldnames[x],self.fieldtypes[x]) for x in range(nfields)])
        varplaces = ','.join(['?']*nfields) # sqlite uses qmarks
        self.insertsql = 'INSERT INTO %s (%s) values (%s)' % (self.tablename,','.join(self.fieldnames),varplaces)        

    class illAnnoF:
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

    def makeAnno(self):
        try:
            sql = 'drop table %s' % self.tablename
            self.cur.execute(sql)
        except:
            if debug:
                print 'no %s to drop this time!' % self.tablename
            else:
                pass
        sql = 'create table %s (%s)' % (self.tablename,self.createvars)
        self.cur.execute(sql)
        sql = 'create index if not exists rs on %s (rs)' % self.tablename
        self.cur.execute(sql)
        sql = 'create index if not exists pos on %s (chr,offset)' % self.tablename
        self.cur.execute(sql)
        sql = 'PRAGMA synchronous=OFF'
        self.cur.execute(sql)
        sql = 'PRAGMA default_cache_size=5000'
        self.cur.execute(sql)
        #sql = 'create index if not exists offset on %s (offset)' % self.tablename
        #self.cur.execute(sql)
        f = self.illAnnoF(self.infname)
        self.cur.executemany(self.insertsql,f) # just pass a file iterator!@
        self.con.commit() # only at end of each file to speed things up


def testIll(infname='HumanHap550v3_A.csv'):
    i = ill500Anno(infname=infname, dbname='HumanHap550',tablename='HumanHap550v3_A')
    i.makeAnno()
    
def testdbSNP():
    i = dbsnpAnno(infname='seq_snp.md', dbname='dbsnp',tablename='dbsnp')
    i.makeAnno()

hapmapped = {'NA18564': ['22', '22', '0', '0', '2', '1'], 'NA18987': ['78', '258', '0', '0', '2', '1'],
             'NA18566': ['23', '23', '0', '0', '2', '1'], 'NA10835': ['1416', '1', '11', '12', '1', '1'],
             'NA18561': ['6', '6', '0', '0', '1', '1'], 'NA18562': ['7', '7', '0', '0', '1', '1'],
             'NA18563': ['24', '24', '0', '0', '1', '1'], 'NA07357': ['1345', '12', '0', '0', '1', '1'],
             'NA10838': ['1420', '1', '9', '10', '1', '1'], 'NA10839': ['1420', '2', '11', '12', '2', '1'],
             'NA11831': ['1350', '12', '0', '0', '1', '1'], 'NA11830': ['1350', '11', '0', '0', '2', '1'],
             'NA07056': ['1340', '12', '0', '0', '2', '1'], 'NA11832': ['1350', '13', '0', '0', '2', '1'],
             'NA12056': ['1344', '12', '0', '0', '1', '1'], 'NA12057': ['1344', '13', '0', '0', '2', '1'],
             'NA18863': ['24', '1', '3', '2', '1', '1'], 'NA18862': ['24', '3', '0', '0', '1', '1'],
             'NA11839': ['1349', '13', '0', '0', '1', '1'], 'NA18967': ['69', '249', '0', '0', '1', '1'],
             'NA19130': ['101', '3', '0', '0', '1', '1'], 'NA10830': ['1408', '1', '10', '11', '1', '1'],
             'NA10831': ['1408', '2', '12', '13', '2', '1'], 'NA12264': ['1375', '11', '0', '0', '1', '1'],
             'NA18516': ['13', '3', '0', '0', '1', '1'], 'NA12707': ['1358', '1', '11', '12', '1', '1'],
             'NA18968': ['59', '239', '0', '0', '2', '1'], 'NA19116': ['60', '2', '0', '0', '2', '1'],
             'NA18550': ['17', '17', '0', '0', '2', '1'], 'NA18552': ['19', '19', '0', '0', '2', '1'],
             'NA07348': ['1345', '2', '12', '13', '2', '1'], 'NA10846': ['1334', '1', '10', '11', '1', '1'],
             'NA19192': ['112', '3', '0', '0', '1', '1'], 'NA18558': ['4', '4', '0', '0', '1', '1'],
             'NA19137': ['43', '2', '0', '0', '2', '1'], 'NA19171': ['47', '3', '0', '0', '1', '1'],
             'NA19172': ['47', '2', '0', '0', '2', '1'], 'NA19173': ['47', '1', '3', '2', '1', '1'],
             'NA18872': ['17', '1', '3', '2', '1', '1'], 'NA19138': ['43', '3', '0', '0', '1', '1'],
             'NA18870': ['17', '2', '0', '0', '2', '1'], 'NA18871': ['17', '3', '0', '0', '1', '1'],
             'NA19161': ['56', '1', '3', '2', '1', '1'], 'NA11829': ['1350', '10', '0', '0', '1', '1'],
             'NA19160': ['56', '3', '0', '0', '1', '1'], 'NA06985': ['1341', '14', '0', '0', '2', '1'],
             'NA19132': ['101', '1', '3', '2', '2', '1'], 'NA18978': ['71', '251', '0', '0', '2', '1'],
             'NA07055': ['1341', '12', '0', '0', '2', '1'], 'NA18973': ['66', '246', '0', '0', '2', '1'],
             'NA18972': ['64', '244', '0', '0', '2', '1'], 'NA18981': ['75', '255', '0', '0', '2', '1'],
             'NA18970': ['72', '252', '0', '0', '1', '1'], 'NA18976': ['70', '250', '0', '0', '2', '1'],
             'NA18975': ['68', '248', '0', '0', '2', '1'], 'NA18974': ['77', '257', '0', '0', '1', '1'],
             'NA19206': ['51', '2', '0', '0', '2', '1'], 'NA19207': ['51', '3', '0', '0', '1', '1'],
             'NA19204': ['48', '2', '0', '0', '2', '1'], 'NA19205': ['48', '1', '3', '2', '1', '1'],
             'NA19202': ['45', '1', '3', '2', '2', '1'], 'NA19203': ['48', '3', '0', '0', '1', '1'],
             'NA19200': ['45', '3', '0', '0', '1', '1'], 'NA19201': ['45', '2', '0', '0', '2', '1'],
             'NA18861': ['24', '2', '0', '0', '2', '1'], 'NA18960': ['62', '242', '0', '0', '1', '1'],
             'NA18971': ['76', '256', '0', '0', '1', '1'], 'NA19208': ['51', '1', '3', '2', '1', '1'],
             'NA18860': ['12', '1', '3', '2', '1', '1'], 'NA10851': ['1344', '1', '12', '13', '1', '1'],
             'NA06994': ['1340', '9', '0', '0', '1', '1'], 'NA10854': ['1349', '2', '13', '14', '2', '1'],
             'NA10855': ['1350', '2', '12', '13', '2', '1'], 'NA10856': ['1350', '1', '10', '11', '1', '1'],
             'NA10857': ['1346', '1', '11', '12', '1', '1'], 'NA12801': ['1454', '1', '12', '13', '1', '1'],
             'NA18547': ['15', '15', '0', '0', '2', '1'], 'NA19143': ['74', '2', '0', '0', '2', '1'],
             'NA18545': ['13', '13', '0', '0', '2', '1'], 'NA18542': ['12', '12', '0', '0', '2', '1'],
             'NA19144': ['74', '3', '0', '0', '1', '1'], 'NA18540': ['10', '10', '0', '0', '2', '1'],
             'NA18980': ['73', '253', '0', '0', '2', '1'], 'NA18953': ['58', '238', '0', '0', '1', '1'],
             'NA18969': ['61', '241', '0', '0', '2', '1'], 'NA19194': ['112', '1', '3', '2', '1', '1'],
             'NA19209': ['50', '2', '0', '0', '2', '1'], 'NA18961': ['63', '243', '0', '0', '1', '1'],
             'NA18964': ['57', '237', '0', '0', '2', '1'], 'NA19240': ['117', '1', '3', '2', '2', '1'],
             'NA18966': ['67', '247', '0', '0', '1', '1'], 'NA18517': ['13', '2', '0', '0', '2', '1'],
             'NA12760': ['1447', '9', '0', '0', '1', '1'], 'NA12761': ['1447', '10', '0', '0', '2', '1'],
             'NA12762': ['1447', '11', '0', '0', '1', '1'], 'NA12763': ['1447', '12', '0', '0', '2', '1'],
             'NA18952': ['55', '235', '0', '0', '1', '1'], 'NA19005': ['86', '266', '0', '0', '1', '1'],
             'NA19007': ['88', '268', '0', '0', '1', '1'], 'NA19000': ['85', '265', '0', '0', '1', '1'],
             'NA19003': ['89', '269', '0', '0', '2', '1'], 'NA19140': ['71', '2', '0', '0', '2', '1'],
             'NA18532': ['5', '5', '0', '0', '2', '1'], 'NA18537': ['8', '8', '0', '0', '2', '1'],
             'NA10860': ['1362', '1', '13', '14', '1', '1'], 'NA10863': ['1375', '2', '11', '12', '2', '1'],
             'NA11992': ['1362', '13', '0', '0', '1', '1'], 'NA11993': ['1362', '14', '0', '0', '2', '1'],
             'NA18956': ['56', '236', '0', '0', '2', '1'], 'NA18951': ['48', '228', '0', '0', '2', '1'],
             'NA11882': ['1347', '15', '0', '0', '2', '1'], 'NA11994': ['1362', '15', '0', '0', '1', '1'],
             'NA11995': ['1362', '16', '0', '0', '2', '1'], 'NA11840': ['1349', '14', '0', '0', '2', '1'],
             'NA07000': ['1340', '10', '0', '0', '2', '1'], 'NA12892': ['1463', '16', '0', '0', '2', '1'],
             'NA19129': ['77', '1', '3', '2', '2', '1'], 'NA19193': ['112', '2', '0', '0', '2', '1'],
             'NA12891': ['1463', '15', '0', '0', '1', '1'], 'NA12003': ['1420', '9', '0', '0', '1', '1'],
             'NA19128': ['77', '3', '0', '0', '1', '1'], 'NA12005': ['1420', '11', '0', '0', '1', '1'],
             'NA12004': ['1420', '10', '0', '0', '2', '1'], 'NA12753': ['1447', '2', '11', '12', '2', '1'],
             'NA12006': ['1420', '12', '0', '0', '2', '1'], 'NA19099': ['105', '2', '0', '0', '2', '1'],
             'NA19098': ['105', '3', '0', '0', '1', '1'], 'NA19152': ['72', '2', '0', '0', '2', '1'],
             'NA18624': ['36', '36', '0', '0', '1', '1'], 'NA18623': ['33', '33', '0', '0', '1', '1'],
             'NA18622': ['31', '31', '0', '0', '1', '1'], 'NA18621': ['29', '29', '0', '0', '1', '1'],
             'NA18620': ['28', '28', '0', '0', '1', '1'], 'NA18529': ['3', '3', '0', '0', '2', '1'],
             'NA19142': ['71', '1', '3', '2', '1', '1'], 'NA19153': ['72', '3', '0', '0', '1', '1'],
             'NA18521': ['16', '1', '3', '2', '1', '1'], 'NA18522': ['16', '3', '0', '0', '1', '1'],
             'NA18523': ['16', '2', '0', '0', '2', '1'], 'NA18524': ['2', '2', '0', '0', '1', '1'],
             'NA18526': ['1', '1', '0', '0', '2', '1'], 'NA18942': ['46', '226', '0', '0', '2', '1'],
             'NA07019': ['1340', '2', '11', '12', '2', '1'], 'NA18940': ['47', '227', '0', '0', '1', '1'],
             'NA18947': ['50', '230', '0', '0', '2', '1'], 'NA18944': ['51', '231', '0', '0', '1', '1'],
             'NA18945': ['52', '232', '0', '0', '1', '1'], 'NA19119': ['60', '3', '0', '0', '1', '1'],
             'NA18948': ['54', '234', '0', '0', '1', '1'], 'NA18949': ['53', '233', '0', '0', '2', '1'],
             'NA06993': ['1341', '13', '0', '0', '1', '1'], 'NA18965': ['65', '245', '0', '0', '1', '1'],
             'NA12156': ['1408', '13', '0', '0', '2', '1'], 'NA12155': ['1408', '12', '0', '0', '1', '1'],
             'NA12154': ['1408', '10', '0', '0', '1', '1'], 'NA18959': ['60', '240', '0', '0', '1', '1'],
             'NA06991': ['1341', '2', '13', '14', '2', '1'], 'NA19154': ['72', '1', '3', '2', '1', '1'],
             'NA19012': ['90', '270', '0', '0', '1', '1'], 'NA19141': ['71', '3', '0', '0', '1', '1'],
             'NA12814': ['1454', '14', '0', '0', '1', '1'], 'NA12815': ['1454', '15', '0', '0', '2', '1'],
             'NA12812': ['1454', '12', '0', '0', '1', '1'], 'NA12813': ['1454', '13', '0', '0', '2', '1'],
             'NA10859': ['1347', '2', '14', '15', '2', '1'], 'NA18635': ['41', '41', '0', '0', '1', '1'],
             'NA18636': ['43', '43', '0', '0', '1', '1'], 'NA18637': ['45', '45', '0', '0', '1', '1'],
             'NA18632': ['38', '38', '0', '0', '1', '1'], 'NA18633': ['40', '40', '0', '0', '1', '1'],
             'NA12802': ['1454', '2', '14', '15', '2', '1'], 'NA19239': ['117', '3', '0', '0', '1', '1'],
             'NA07022': ['1340', '11', '0', '0', '1', '1'], 'NA19145': ['74', '1', '3', '2', '1', '1'],
             'NA07029': ['1340', '1', '9', '10', '1', '1'], 'NA12239': ['1334', '13', '0', '0', '2', '1'],
             'NA12751': ['1444', '14', '0', '0', '2', '1'], 'NA12236': ['1408', '11', '0', '0', '2', '1'],
             'NA12234': ['1375', '12', '0', '0', '2', '1'], 'NA12750': ['1444', '13', '0', '0', '1', '1'],
             'NA12144': ['1334', '10', '0', '0', '1', '1'], 'NA12145': ['1334', '11', '0', '0', '2', '1'],
             'NA12146': ['1334', '12', '0', '0', '1', '1'], 'NA12752': ['1447', '1', '9', '10', '1', '1'],
             'NA18609': ['16', '16', '0', '0', '1', '1'], 'NA18608': ['18', '18', '0', '0', '1', '1'],
             'NA19120': ['60', '1', '3', '2', '1', '1'], 'NA19127': ['77', '2', '0', '0', '2', '1'],
             'NA12865': ['1459', '2', '11', '12', '2', '1'], 'NA12864': ['1459', '1', '9', '10', '1', '1'],
             'NA18603': ['9', '9', '0', '0', '1', '1'], 'NA19159': ['56', '2', '0', '0', '2', '1'],
             'NA18605': ['11', '11', '0', '0', '1', '1'], 'NA18853': ['18', '3', '0', '0', '1', '1'],
             'NA07034': ['1341', '11', '0', '0', '1', '1'], 'NA19221': ['58', '1', '3', '2', '2', '1'],
             'NA19222': ['58', '2', '0', '0', '2', '1'], 'NA19223': ['58', '3', '0', '0', '1', '1'],
             'NA18505': ['5', '2', '0', '0', '2', '1'], 'NA19094': ['40', '1', '3', '2', '2', '1'],
             'NA18555': ['21', '21', '0', '0', '2', '1'], 'NA18943': ['49', '229', '0', '0', '1', '1'],
             'NA18612': ['26', '26', '0', '0', '1', '1'], 'NA12249': ['1416', '12', '0', '0', '2', '1'],
             'NA18611': ['20', '20', '0', '0', '1', '1'], 'NA18594': ['30', '30', '0', '0', '2', '1'],
             'NA19238': ['117', '2', '0', '0', '2', '1'], 'NA18593': ['44', '44', '0', '0', '2', '1'],
             'NA18592': ['42', '42', '0', '0', '2', '1'], 'NA18515': ['13', '1', '3', '2', '1', '1'],
             'NA19131': ['101', '2', '0', '0', '2', '1'], 'NA12872': ['1459', '9', '0', '0', '1', '1'],
             'NA12873': ['1459', '10', '0', '0', '2', '1'], 'NA12874': ['1459', '11', '0', '0', '1', '1'],
             'NA12875': ['1459', '12', '0', '0', '2', '1'], 'NA07345': ['1345', '13', '0', '0', '2', '1'],
             'NA12878': ['1463', '2', '15', '16', '2', '1'], 'NA19139': ['43', '1', '3', '2', '1', '1'],
             'NA18577': ['35', '35', '0', '0', '2', '1'], 'NA18576': ['34', '34', '0', '0', '2', '1'],
             'NA18573': ['32', '32', '0', '0', '2', '1'], 'NA18572': ['14', '14', '0', '0', '1', '1'],
             'NA18571': ['27', '27', '0', '0', '2', '1'], 'NA18570': ['25', '25', '0', '0', '2', '1'],
             'NA19211': ['50', '1', '3', '2', '1', '1'], 'NA19210': ['50', '3', '0', '0', '1', '1'],
             'NA12740': ['1444', '2', '13', '14', '2', '1'], 'NA11881': ['1347', '14', '0', '0', '1', '1'],
             'NA18579': ['37', '37', '0', '0', '2', '1'], 'NA10847': ['1334', '2', '12', '13', '2', '1'],
             'NA18999': ['87', '267', '0', '0', '2', '1'], 'NA12044': ['1346', '12', '0', '0', '2', '1'],
             'NA19092': ['40', '3', '0', '0', '1', '1'], 'NA10861': ['1362', '2', '15', '16', '2', '1'],
             'NA12043': ['1346', '11', '0', '0', '1', '1'], 'NA18991': ['80', '260', '0', '0', '2', '1'],
             'NA18990': ['79', '259', '0', '0', '1', '1'], 'NA18992': ['82', '262', '0', '0', '2', '1'],
             'NA18995': ['74', '254', '0', '0', '1', '1'], 'NA18994': ['81', '261', '0', '0', '1', '1'],
             'NA18997': ['83', '263', '0', '0', '2', '1'], 'NA07048': ['1341', '1', '11', '12', '1', '1'],
             'NA18858': ['12', '2', '0', '0', '2', '1'], 'NA18859': ['12', '3', '0', '0', '1', '1'],
             'NA18913': ['28', '3', '0', '0', '1', '1'], 'NA18912': ['28', '2', '0', '0', '2', '1'],
             'NA18914': ['28', '1', '3', '2', '1', '1'], 'NA18504': ['5', '3', '0', '0', '1', '1'],
             'NA18582': ['39', '39', '0', '0', '2', '1'], 'NA19093': ['40', '2', '0', '0', '2', '1'],
             'NA18852': ['18', '2', '0', '0', '2', '1'], 'NA12248': ['1416', '11', '0', '0', '1', '1'],
             'NA18854': ['18', '1', '3', '2', '1', '1'], 'NA18855': ['23', '2', '0', '0', '2', '1'],
             'NA18856': ['23', '3', '0', '0', '1', '1'], 'NA18857': ['23', '1', '3', '2', '1', '1'],
             'NA18502': ['4', '2', '0', '0', '2', '1'], 'NA18503': ['5', '1', '3', '2', '1', '1'],
             'NA18500': ['4', '1', '3', '2', '1', '1'], 'NA18501': ['4', '3', '0', '0', '1', '1'],
             'NA18506': ['9', '1', '3', '2', '1', '1'], 'NA18507': ['9', '3', '0', '0', '1', '1'],
             'NA12717': ['1358', '12', '0', '0', '2', '1'], 'NA12716': ['1358', '11', '0', '0', '1', '1'],
             'NA18998': ['84', '264', '0', '0', '2', '1'], 'NA18508': ['9', '2', '0', '0', '2', '1'],
             'NA19101': ['42', '3', '0', '0', '1', '1'], 'NA19100': ['105', '1', '3', '2', '2', '1'],
             'NA19103': ['42', '1', '3', '2', '1', '1'], 'NA19102': ['42', '2', '0', '0', '2', '1']}

rcdict = {'A':'T','C':'G','G':'C','T':'A','N':'N'} # for reverse complimenting alleles


def writeHapMaptesterYRI(testing = 1, ftest = 0.1):
    """write a hapmap ped file containing ceu and yri as affected offspring (!)
    for plink testing
    ross lazarus march 8 2007
    """
    genome = MySQLdb.Connect('godzilla', 'refseq', 'Genbank')
    curs = genome.cursor(cursorclass=MySQLdb.cursors.DictCursor) # use dict cursor as cols are subject ids
    curs.execute('use hapmap')
    i = ill500Anno(infname='HumanHap550v3_A.csv', dbname='HumanHap550',tablename='HumanHap550v3_A')
    chrlist = map(str,range(1,23))
    chrlist += ['X','Y']
    subjgeno = {}
    chrmaplist = {}
    allmaplist = []
    outf = file('hapmapCEU_YRItest.ped','w')
    for chrom in chrlist: # work by chrom as hapmap data is organized that way
        chrmaplist[chrom] = []
        nrs = 0
        i.cur.execute('select rs from %s where chr="%s" order by offset' % (i.tablename,chrom))
        rslist = i.cur.fetchall()
        i.cur.execute('select chr,rs,offset from %s where chr="%s" order by offset' % (i.tablename,chrom))
        amap = i.cur.fetchall()
        allmaplist += [[y.encode() for y in x] for x in amap]
        for rs in rslist:
            if not testing or random.random() <= ftest: # take a fraction
                rs = rs[0].encode() # sqlite returns unicode strings
                sql = 'select * from CEU_%s where RS = "%s"' % (chrom,rs)
                curs.execute(sql) # get all illumina rs
                ceu = curs.fetchall()
                if len(ceu) > 0:
                    ceu = ceu[0]
                    strand = ceu['STRAND']
                    rc = False
                    if strand == '-':
                        rc = True
                    chrmaplist[chrom].append(rs)
                    nrs += 1
                    for k in ceu.keys():
                        if k[:2] == 'NA': # is a NA identifier field
                            geno = map(None,ceu[k]) # to list
                            if len(geno) <> 2:
                                print 'strange geno',ceu[k]
                            else:
                                if rc:
                                    geno = [rcdict[x] for x in geno] # reverse compliment
                                if subjgeno.get(k,None):
                                    subjgeno[k].append('%s %s' % (geno[0],geno[1])) # genotype
                                else: # first time
                                    subjgeno[k] = ['%s %s' % (geno[0],geno[1]),]
        print 'for chrom %s found %d rs' % (chrom, nrs)
    # now have all ceu subjects in subjgeno
    res = []
    for id in subjgeno.keys(): # for each subject
        row = hapmapped[id]
        row += subjgeno[id]
        res.append(' '.join(row))
    res.sort()
    res.append('')
    outf.write('\n'.join(res))
    outf.write('\n')
    print 'wrote %d rows' % len(res)
    subjgeno = {} # start again for YRI
    for chrom in chrlist:
        for rs in chrmaplist[chrom]: # only look for yri snps where some found in ceu
            sql = 'select * from YRI_%s where RS = "%s"' % (chrom,rs)
            curs.execute(sql) # get all illumina rs
            ceu = curs.fetchall()
            if len(ceu) > 0:
                ceu = ceu[0]
                strand = ceu['STRAND']
                rc = False
                if strand == '-':
                    rc = True
                for k in ceu.keys():
                    if k[:2] == 'NA': # is a NA identifier field
                        geno = map(None,ceu[k]) # to list
                        if len(geno) <> 2:
                            print 'strange geno',ceu[k]
                        else:
                            if rc:
                                geno = [rcdict[x] for x in geno] # reverse compliment
                            if subjgeno.get(k,None):
                                subjgeno[k].append('%s %s' % (geno[0],geno[1])) # genotype
                            else: # first time
                                subjgeno[k] = ['%s %s' % (geno[0],geno[1]),]
                                ped = hapmapped[k] # fiddle so yri kids are all affected
                                ped[-1] = '2'
                                hapmapped[k] = ped
            else: # missing in yri
                for k in subjgeno.keys():
                    subjgeno[k].append('N N') # set to missing
    res = []
    for id in subjgeno.keys(): # for each subject
        row = hapmapped[id]
        row += subjgeno[id]
        res.append(' '.join(row))
    res.sort()
    outf.write('\n'.join(res))
    outf.write('\n')   
    outf.close()
    outf = file('hapmapQCtest.map','w')
    maplist = []
    for chrom in chrlist:
        maplist += chrmaplist[chrom] # append all lists in chrom order
    mapdict = dict(zip(maplist,maplist))
    maplist2 = []
    for x in allmaplist:
        if mapdict.get(x[1],None):
            x.insert(2,'0')
            maplist2.append(' '.join(x))
    print maplist2[:10]
    maplist2.append('') 
    outf.write('\n'.join(maplist2))
    outf.close()
    
    
    
if __name__ == "__main__":
    #testdbSNP()
    # first time only
    #testIll()
    writeHapMaptester(testing = 0,ftest = 0.001)
