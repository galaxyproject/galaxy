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
def bedToolsBamMX(bedfile,bam_list,halfwindow,bam_filenames,ignoreDupes,countBetween,opts):
    """
    try bedtools 
root@iaas1-int:/data/galaxy_june_2011# multiBamCov 

Tool:    bedtools multicov (aka multiBamCov)
Version: v2.16.2
Summary: Counts sequence coverage for multiple bams at specific loci.

Usage:   bedtools multicov [OPTIONS] -bams aln.1.bam aln.2.bam ... aln.n.bam -bed <bed/gff/vcf>

Options: 
        -bams   The bam files.

        -bed    The bed file.

        -q      Minimum mapping quality allowed. Default is 0.

        -D      Include duplicate reads.  Default counts non-duplicates only

        -F      Include failed-QC reads.  Default counts pass-QC reads only

        -p      Only count proper pairs.  Default counts all alignments with
                MAPQ > -q argument, regardless of the BAM FLAG field.

    """
    mapqMin = None
    seend = {}
    if opts.mapqMin and int(opts.mapqMin) > 0:
        mapqMin = int(opts.mapqMin)
    cl = []
    cl.append('multiBamCov')
    if mapqMin:
        cl.append('-q')
        cl.append('%d' % mapqMin)
    if opts.ignoreDupes == 'true':
       cl.append('-D')
    cl.append('-bams')
    for i,abam in enumerate(bam_list): # these are sample file named symlinks with symlinked bai
        cl.append(abam)
    cl.append('-bed')
    cl.append(bedfile)
    cwd = os.getcwd()
    tlog = os.path.join(cwd,'bedtools.log')
    sto = open(tlog,'w')
    outf = open(opts.outfname,'w')
    p = subprocess.Popen(cl,shell=False,stdout=outf,stderr=sto,cwd=cwd)
    retcode = p.wait()
    outf.close()
    sto.close()
    res = open(tlog,'r').readlines()
    res.append(' '.join(cl))
    return '',res


def usage():
        print >> sys.stderr, """Usage: python bedtoolsbams2mx.py -w <halfwindowsize> -b <bedfile.bed> -o <outfilename> [-i] [-c] --bamf "<bam1.bam>,<bam1.bam.bai>,<bam1.column_header>" --bamf "...<bamN.column_header>" """
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
        assert os.path.isfile(b),'## Supplied input bam file "%s" not found' % b
        cname = bcolname[i]
        if cname == "":
            bfname = os.path.split(b)[-1] # becomes column header
            cname = os.path.splitext(bfname)[0] # becomes column header
        bam_filenames.append(cname) # becomes column header
        bn = os.path.basename(b)
        tf,tbam = tempfile.mkstemp(suffix='%s.bam' % cname,dir=opts.tmpdir)
        os.unlink(tbam)
        try:
            os.symlink(b,tbam)
        except:
            shutil.copy(b,tbam)
        realusebams.append(tbam)
        bai = baif[i]
        assert os.path.isfile(bai),'## Supplied input bai file "%s" not found' % bai
        tempbai = '%s.bai' % tbam
        try:
           os.symlink(bai,tempbai)
        except:
           shutil.copy(bai,tempbai) # if on different devices 
    res,notes = bedToolsBamMX(bedfile, realusebams,halfwindow,bam_filenames,ignoreDupes,countBetween,opts)
    if len(notes) > 0: 
        print >> sys.stdout, '\n'.join(notes)
    # clean up temp files
    for tbam in realusebams:
          try:
               os.unlink(tbam)
               os.unlink('%s.bai' % tbam)
          except:
               pass

