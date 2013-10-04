# updated ross lazarus august 2011 to NOT include region and to finesse the name as the region for bed3 format inputs
# also now sums all duplicate named regions and provides a summary of any collapsing as the info
# updated ross lazarus july 26 to respect the is_duplicate flag rather than try to second guess
# note Heng Li argues that removing dupes is a bad idea for RNA seq
# updated ross lazarus july 22 to count reads OUTSIDE each bed region during the processing of each bam
# added better sorting with decoration of a dict key later sorted and undecorated.
# code cleaned up and galaxified ross lazarus july 18 et seq.
# bams2mx.py -turns a series of bam and a bed file into a matrix of counts Usage bams2mx.py <halfwindow> <bedfile.bed> <bam1.bam> 
# <bam2.bam>
#
# TODO options -shift -unique
#


import os
import re
import sys 
import pysam 
import optparse 
import tempfile 
import shutil
import operator
import subprocess

OUTSIDECONTIG = 'NotInBedRegions' # used as a fake contig name and region for recording the count of reads outside a real contig
IGNORED = 'DupesNotCounted' # used as contig name for ignored duplicate reads if ignoreDupes is set
LIBSIZE = 'LibrarySize' # total reads in bam (!)
OUTEMPTY = True

class Xcpt(Exception):
    def __init__(self, msg):
        self.msg = msg

def countReads(f,opts):
    """ count reads - newer pysams do this with count.
   we need the first integer in
(vgalaxy)galaxy@omics:/data/galaxy-central$ samtools flagstat test-data/tophat_out7h.bam
462 + 0 in total (QC-passed reads + QC-failed reads)
0 + 0 duplicates
462 + 0 mapped (100.00%:-nan%)
462 + 0 paired in sequencing
262 + 0 read1
200 + 0 read2
156 + 0 properly paired (33.77%:-nan%)
216 + 0 with itself and mate mapped
246 + 0 singletons (53.25%:-nan%)
0 + 0 with mate mapped to a different chr
0 + 0 with mate mapped to a different chr (mapQ>=5)
    """
    out_dir=opts.tmpdir
    tlog = os.path.join(out_dir,'countReads.tmp')
    cl = ['samtools', 'flagstat', f]
    sto = open(tlog,'w')
    p = subprocess.Popen(' '.join(cl),shell=True,stdout=sto,stderr=sto,cwd=out_dir)
    retcode = p.wait()
    sto.close()
    res = open(tlog,'r').readlines()
    try:
        row1 = res[0].strip().split()
        count = int(row1[0])
    except:
        count = 0
        raise Xcpt('Unable to get count from running samtools flagstat')
    return count


def keynat(s=None):
     '''
     borrowed from http://code.activestate.com/recipes/285264-natural-string-sorting/
     A natural sort helper function for sort() and sorted()
     without using regular expressions or exceptions.
     >>> items = ('Z', 'a', '10th', '1st', '9') sorted(items)
     ['10th', '1st', '9', 'Z', 'a']
     >>> sorted(items, key=keynat)
     ['1st', '9', '10th', 'a', 'Z']
     '''
     if type(s) == type([]) or type(s) == type(()) :
         s = s[0]
     it = type(1)
     r = []
     for c in s:
         if c.isdigit():
             d = int(c)
             if r and type( r[-1] ) == it:
                 r[-1] = r[-1] * 10 + d
             else:
                 r.append(d)
         else:
             r.append(c.lower())
     return r


def sort_table(table, cols):
    """ sort a table by multiple columns
        table: a list of lists (or tuple of tuples) where each inner list 
               represents a row
        cols:  a list (or tuple) specifying the column numbers to sort by
               e.g. (1,0) would sort by column 1, then by column 0
    """
    for col in reversed(cols):
        table = sorted(table, key=operator.itemgetter(col))
    return table


#i.e. chr1:10-100 ChIP_SAHA.bam 20
def bedBamMX(bedfile,bam_list,halfwindow,bam_filenames,ignoreDupes,countBetween,opts):
    mapqMin = None
    if opts.mapqMin and int(opts.mapqMin) > 0:
        mapqMin = int(opts.mapqMin)
    res = [] # store output
    #suck in bed file
    dat=open(bedfile, 'r').readlines()
    dat = [x.strip().split('\t') for x in dat] # only do once
    dat = [x for x in dat if len(x) >= 3] # only want non empty rows - must have chr start end at least
    mindat = min([len(x) for x in dat])
    maxdat = max([len(x) for x in dat])
    nbed = len(dat)    
    assert nbed > 0,'## Supplied BED file %s is empty or contains fewer than 3 columns - cannot proceed' % bedfile
    assert maxdat == mindat,'## Supplied BED file %s has variable number of columns - from %d to %d. Possibly not using tabs in some places? Cannot reiably proceed' % (bedfile,mindat,maxdat)
    for i,row in enumerate(dat):
        row[1] = int(row[1])
        row[2] = int(row[2]) # for sorting
        dat[i] = row
    dat.sort() # into chrom start end order
    if maxdat == 3 or opts.forceName=="true":
        for i,row in enumerate(dat): # fake a name field in col 4 for bed3 (eg ChIP data)
            row = [row[0],row[1],row[2],"%s:%d-%d" % (row[0],row[1],row[2])]
            dat[i] = row       
    chroms = set([x[0] for x in dat]) # unique   
    d = {}
    dcontigs={} # dict for making contig list
    allnotmapped = 0
    mapqFiltered = 0
    print "bed has %d contigs" % nbed
    for i,f in enumerate(bam_list):
        sampName = bam_filenames[i] # better be unique
        sampName = sampName.replace('#','') # for R
        sampName = sampName.replace('(','') # for R
        sampName = sampName.replace(')','') # for R
        if d.get(sampName,None):
            print >> sys.stdout, '##ERROR: Duplicate input %s - ignored!!' % sampName
            continue
        d[sampName] = {} # new data
        outreads = 0 # count of reads outside each bed region for library size normalization 
        ignoredoutreads = 0
        outchrom = None
        outstart = None
        outend = None
        notmapped = 0
        # pysam expects to find infile.bai
        bam_index = "%s.bai" % f
        if (not os.path.isfile(bam_index)):
            print >> sys.stdout,'indexing ',f
            pysam.index(f)
        samfile = pysam.Samfile( f, "rb" )
        nbam = 0
        for c in chroms:
            try:
                nbam += samfile.count(c,1,999999999) # for non bed region count
            except:
                pass
        print 'bam %s has %d total reads' % (f,nbam)
        ignored = 0 # this is per sample over all regions
        ignoredoutreads = 0 # ditto but for total reads outside regions fudgtimate
        for bedrec in dat:
            hits = 0 # count by contig
            chrom = bedrec[0].strip()
            start = int(bedrec[1]) # new contig start becomes old inter-region end
            end = int(bedrec[2])
            regionID = bedrec[3]
            contigKey = chrom.lower().replace('chr','') # decorator for ordering later
            dcontigs.setdefault((contigKey,regionID),regionID) # will make a new entry if not there - note ready for sorting
            if (start == -1): # Whole contig
                for alignedread in samfile.fetch(chrom): # check for dupes or count
                    if not alignedread.is_unmapped:
                        if ignoreDupes and alignedread.is_duplicate:
                            ignored += 1
                        else:
                            if mapqMin:
                                if alignedread.mapq < mapqMin:
                                    mapqFiltered += 1
                                else:
                                    hits += 1   
                            else:
                                hits += 1
                    else:
                        notmapped += 1
            else: #Not whole contig
                try:
                    for alignedread in samfile.fetch(chrom,max(start-halfwindow,1) , end+halfwindow): # check bed interval - indexed lookup
                        if not alignedread.is_unmapped:
                            if ignoreDupes and alignedread.is_duplicate:
                                ignored += 1
                            else:
                                if mapqMin:
                                    if alignedread.mapq < mapqMin:
                                       mapqFiltered += 1
                                    else:
                                       hits += 1
                                else:
                                    hits += 1
                        else:
                            notmapped += 1
                except ValueError:
                    pass
            if d[sampName].get(regionID,None) == None:
                d[sampName][regionID] = 0 # in case new
            d[sampName][regionID] += hits # or if duplicated, sum
        if ignoreDupes:
            d[sampName][IGNORED] = ignored
        if countBetween:
            inbed = sum(d[sampName].values())
            d[sampName][OUTSIDECONTIG] = nbam - inbed
        if countLib:
            d[sampName][LIBSIZE] = nbam
        allnotmapped += notmapped
        samfile.close()
    lcontigs = dcontigs.keys() # unique decorated for sorting contig values
    lcontigs = sort_table(lcontigs,(0,1)) #Sort on chr and offset
    lcontigs = sorted(lcontigs,key=keynat) # just the first column - preserves other ordering
    lcontigs = [x[1] for x in lcontigs] # undecorate
    lcontigs = list(set(lcontigs))
    lcontigs.sort()
    ncontigs = len(lcontigs) # unique contigs
    notes = []
    if ncontigs <> nbed: # some dups - report
        notes.append('#Dupes: %d contignames in %d bed rows' % (ncontigs,nbed)) 
    if countBetween:
        lcontigs.append(OUTSIDECONTIG) # name used to store the count each bam's reads outside the bed file regions
    if ignoreDupes:
        lcontigs.append(IGNORED)
    s = "Contigname"
    for sampName in d:
        s += "\t"+ sampName.replace(' ','_')
    res.append(s)
    for regionID in lcontigs:
        row = [regionID,]
        tothits = 0
        for sampName in d: # Grab the values for each sample
            hits = d[sampName].get(regionID,0) # will return zero for empty contigs
            row.append('%d' % hits)
            tothits += hits
        if OUTEMPTY or (tothits > 0): # output rows > 0 counts
            res.append('\t'.join(row)) # row of data
    if allnotmapped > 0: # should never happen:
        notes.append('pysam returned %d unmapped reads - ignored!' % allnotmapped)
    if mapqMin and (mapqFiltered > 0):
        notes.append('mapqMin=%d, filtered %d reads total' % (mapqMin,mapqFiltered))
    return res,notes

def usage():
        print >> sys.stderr, """Usage: python bams2mx.py -w <halfwindowsize> -b <bedfile.bed> -o <outfilename> [-i] [-c] --bamf "<bam1.bam>,<bam1.bam.bai>,<bam1.column_header>" --bamf "...<bamN.column_header>" """
        sys.exit(1)

if __name__ == "__main__":
    """  
    <command interpreter="python">
    bams2mx.py -w "$halfwin" -b "$bedfile" -o "$outfile" -i "$ignoreDupes" -c "$countBetween"
    #for $b in $bamfiles:
    --bamf "'${b.bamf}','${b.bamf.metadata.bam_index}','${b.bamf.name}'"
    #end for
    </command>
    """
    if len(sys.argv) < 6:
        usage()
        sys.exit(1)
    op = optparse.OptionParser()
    # All tools
    op.add_option('-w', '--halfwindow', default="0")
    op.add_option('-b', '--bedfile', default=None)
    op.add_option('-o', '--outfname', default=None)
    op.add_option('-i','--ignoreDupes',default="true")
    op.add_option('-c','--countBetween', default="false")
    op.add_option('-f','--forceName', default="false")
    op.add_option('-l','--countLib', default="true")
    op.add_option('--bamf', default=[], action="append")
    op.add_option('--tmpdir', default=None)
    op.add_option('--mapqMin', default=None)
    opts, args = op.parse_args()
    assert opts.tmpdir <> None, '##ERROR bams2mx: requires a temporary directory on the command line as eg: "--tmpdir /data/tmp"'
    halfwindow = int(opts.halfwindow)
    bedfile = opts.bedfile
    assert os.path.isfile(bedfile),'##ERROR bams2mx: Supplied input bed file "%s" not found' % bedfile
    outfname = opts.outfname
    ignoreDupes = opts.ignoreDupes.lower() == 'true'
    countBetween = opts.countBetween.lower() == 'true'
    countLib = opts.countLib.lower() == 'true'
    realusebams = []
    realusebais = []
    bam_filenames = []
    # ugh. pysam insists on foo.bam and foo.bai
    tb='?'
    bamdat = opts.bamf
    bamf = [x.split(',')[0].replace("'",'').replace('"','') for x in bamdat] # get rid of wrapper supplied quotes
    baif = [x.split(',')[1].replace("'",'').replace('"','') for x in bamdat] # get rid of wrapper supplied quotes
    bcolname = [x.split(',')[2].replace("'",'').replace('"','') for x in bamdat]
    assert len(bamf) == len(baif) == len(bcolname), '##ERROR bams2mx: Count of bam/bai/cname not consistent - %d/%d/%d' % (len(bamf),len(baif),len(bcolname))
    for i,b in enumerate(bamf):
        if b.lower() == "none":
           continue
        assert os.path.isfile(b),'## Supplied input bam file "%s" not found' % b
        bn = os.path.basename(b)
        tf,tbam = tempfile.mkstemp(suffix='%s.bam' % bn,dir=opts.tmpdir)
        os.unlink(tbam)
        try:
            os.symlink(b,tbam)
        except:
            shutil.copy(b,tbam)
        realusebams.append(tbam)
        bai = baif[i]
        cname = bcolname[i]
        assert os.path.isfile(bai),'## Supplied input bai file "%s" not found' % bai
        tempbai = '%s.bai' % tbam
        try:
           os.symlink(bai,tempbai)
        except:
           shutil.copy(bai,tempbai) # if on different devices 
        if cname == "":
            bfname = os.path.split(b)[-1] # becomes column header
            cname = os.path.splitext(bfname)[0] # becomes column header
        bam_filenames.append(cname) # becomes column header
    res,notes = bedBamMX(bedfile, realusebams,halfwindow,bam_filenames,ignoreDupes,countBetween,opts)
    outf = open(outfname,'w')
    outf.write('\n'.join(res))
    outf.write('\n')
    outf.close()
    if len(notes) > 0: 
        print >> sys.stdout, ';'.join(notes)
    # clean up temp files
    for tbam in realusebams:
          try:
               os.unlink(tbam)
               os.unlink('%s.bai' % tbam)
          except:
               pass

