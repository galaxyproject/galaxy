# May 2013
# Change to htseq as the counting engine - wrap so arbitrary number of columns created  
# borged Simon Anders' "count.py" since we need a vector of counts rather than a new sam file as output
# note attribution for htseq and count.py :
## Written by Simon Anders (sanders@fs.tum.de), European Molecular Biology
## Laboratory (EMBL). (c) 2010. Released under the terms of the GNU General
## Public License v3. Part of the 'HTSeq' framework, version HTSeq-0.5.4p3
# updated ross lazarus august 2011 to NOT include region and to finesse the name as the region for bed3 format inputs
# also now sums all duplicate named regions and provides a summary of any collapsing as the info
# updated ross lazarus july 26 to respect the is_duplicate flag rather than try to second guess
# note Heng Li argues that removing dupes is a bad idea for RNA seq
# updated ross lazarus july 22 to count reads OUTSIDE each bed region during the processing of each bam
# added better sorting with decoration of a dict key later sorted and undecorated.
# code cleaned up and galaxified ross lazarus july 18 et seq.
# bams2mx.py -turns a series of bam and a bed file into a matrix of counts Usage bams2mx.py <halfwindow> <bedfile.bed> <bam1.bam> 
# <bam2.bam>
# uses pysam to read and count bam reads over each bed interval for each sample for speed
# still not so fast
# TODO options -shift -unique
#
"""
how this gets run:

(vgalaxy)galaxy@iaas1-int:~$ cat database/job_working_directory/027/27014/galaxy_27014.sh
#!/bin/sh
GALAXY_LIB="/data/extended/galaxy/lib"
if [ "$GALAXY_LIB" != "None" ]; then
    if [ -n "$PYTHONPATH" ]; then
        PYTHONPATH="$GALAXY_LIB:$PYTHONPATH"
    else
        PYTHONPATH="$GALAXY_LIB"
    fi
    export PYTHONPATH
fi

cd /data/extended/galaxy/database/job_working_directory/027/27014
python /data/extended/galaxy/tools/rgenetics/htseqsams2mx.py -g "/data/extended/galaxy/database/files/034/dataset_34115.dat" -o "/data/extended/galaxy/database/files/034/dataset_34124.dat" -m "union" --id_attribute "gene_id" --feature_type "exon"     --samf "'/data/extended/galaxy/database/files/033/dataset_33980.dat','T5A_C1PPHACXX_AGTTCC_L003_R1.fastq_bwa.sam'"     --samf "'/data/extended/galaxy/database/files/033/dataset_33975.dat','T5A_C1PPHACXX_AGTTCC_L002_R1.fastq_bwa.sam'"; cd /data/extended/galaxy; /data/extended/galaxy/set_metadata.sh ./database/files /data/extended/galaxy/database/job_working_directory/027/27014 . /data/extended/galaxy/universe_wsgi.ini /data/tmp/tmpmwsElH /data/extended/galaxy/database/job_working_directory/027/27014/galaxy.json /data/extended/galaxy/database/job_working_directory/027/27014/metadata_in_HistoryDatasetAssociation_45202_sfOMGa,/data/extended/galaxy/database/job_working_directory/027/27014/metadata_kwds_HistoryDatasetAssociation_45202_gaMnxa,/data/extended/galaxy/database/job_working_directory/027/27014/metadata_out_HistoryDatasetAssociation_45202_kZPsZO,/data/extended/galaxy/database/job_working_directory/027/27014/metadata_results_HistoryDatasetAssociation_45202_bXU7IU,,/data/extended/galaxy/database/job_working_directory/027/27014/metadata_override_HistoryDatasetAssociation_45202_hyLAvh
echo $? > /data/extended/galaxy/database/job_working_directory/027/27014/galaxy_27014.ec

"""

import os
import re
import sys 
import HTSeq.scripts.count as htcount
import optparse 
import tempfile 
import shutil
import operator
import subprocess
import itertools
import warnings
import traceback
import HTSeq
import time


class Xcpt(Exception):
    def __init__(self, msg):
        self.msg = msg


def htseqMX(gff_filename,sam_filenames,colnames,sam_exts,sam_bais,opts):
    """
    Code taken from count.py in Simon Anders HTSeq distribution
    Wrapped in a loop to accept multiple bam/sam files and their names from galaxy to
    produce a matrix of contig counts by sample for downstream use in edgeR and DESeq tools
    """
    class UnknownChrom( Exception ):
       pass
       
    def my_showwarning( message, category, filename, lineno = None, line = None ):
       sys.stdout.write( "Warning: %s\n" % message )      
        
    def invert_strand( iv ):
       iv2 = iv.copy()
       if iv2.strand == "+":
          iv2.strand = "-"
       elif iv2.strand == "-":
          iv2.strand = "+"
       else:
          raise ValueError, "Illegal strand"
       return iv2

    def count_reads_in_features( sam_filenames, colnames, gff_filename, opts ):
       """ Hacked version of htseq count.py
       """
       if opts.quiet:
          warnings.filterwarnings( action="ignore", module="HTSeq" ) 
       features = HTSeq.GenomicArrayOfSets( "auto", opts.stranded != "no" )
       mapqMin = int(opts.mapqMin)       
       counts = {}
       nreads = 0
       empty = 0
       ambiguous = 0
       notaligned = 0
       lowqual = 0
       nonunique = 0          
       filtered = 0 # new filter_extras - need a better way to do this - independent filter tool?
       gff = HTSeq.GFF_Reader( gff_filename )   
       try:
          for i,f in enumerate(gff):
             if f.type == opts.feature_type:
                try:
                   feature_id = f.attr[ opts.id_attribute ]
                except KeyError:
                   sys.exit( "Feature at row %d %s does not contain a '%s' attribute" % 
                      ( (i+1), f.name, opts.id_attribute ) )
                if opts.stranded != "no" and f.iv.strand == ".":
                   sys.exit( "Feature %s at %s does not have strand information but you are "
                      "running htseq-count in stranded mode. Use '--stranded=no'." % 
                      ( f.name, f.iv ) )
                features[ f.iv ] += feature_id
                counts[ f.attr[ opts.id_attribute ] ] = [0 for x in colnames] # we use sami as an index here to bump counts later
       except:
          sys.stderr.write( "Error occured in %s.\n" % gff.get_line_number_string() )
          raise
          
       if not opts.quiet:
          sys.stdout.write( "%d GFF lines processed.\n" % i )
          
       if len( counts ) == 0 and not opts.quiet:
          sys.stdout.write( "Warning: No features of type '%s' found.\n" % opts.feature_type )
       for sami,sam_filename in enumerate(sam_filenames):
           colname = colnames[sami]
           isbam = sam_exts[sami] == 'bam'
           hasbai = sam_bais[sami] > ''
           if hasbai:
               tempname = os.path.splitext(os.path.basename(sam_filename))[0]
               tempbam = '%s.bam' % tempname
               tempbai = '%s.bai' % tempname
               os.link(sam_filename,tempbam)
               os.link(sam_bais[sami],tempbai)
           try:
              if isbam:
                  if hasbai:
                      read_seq = HTSeq.BAM_Reader ( tempbam )
                  else:
                      read_seq = HTSeq.BAM_Reader( sam_filename )
              else:
                  read_seq = HTSeq.SAM_Reader( sam_filename )
              first_read = iter(read_seq).next()
              pe_mode = first_read.paired_end
           except:
              if isbam:
                  print >> sys.stderr, "Error occured when reading first line of bam file %s colname=%s \n" % (sam_filename,colname )
              else:
                  print >> sys.stderr, "Error occured when reading first line of sam file %s colname=%s \n" % (sam_filename,colname )
              raise

           try:
              if pe_mode:
                 read_seq_pe_file = read_seq
                 read_seq = HTSeq.pair_SAM_alignments( read_seq )
              for seqi,r in enumerate(read_seq):
                 nreads += 1
                 if not pe_mode:
                    if not r.aligned:
                       notaligned += 1
                       continue
                    try:
                       if len(opts.filter_extras) > 0:
                           for extra in opts.filter_extras:
                               if r.optional_field(extra):
                                     filtered += 1
                                     continue 
                       if r.optional_field( "NH" ) > 1:
                          nonunique += 1
                          continue
                    except KeyError:
                       pass
                    if r.aQual < mapqMin:
                       lowqual += 1
                       continue
                    if opts.stranded != "reverse":
                       iv_seq = ( co.ref_iv for co in r.cigar if co.type == "M" and co.size > 0 )
                    else:
                       iv_seq = ( invert_strand( co.ref_iv ) for co in r.cigar if co.type == "M" and co.size > 0 )            
                 else:
                    if r[0] is not None and r[0].aligned:
                       if opts.stranded != "reverse":
                          iv_seq = ( co.ref_iv for co in r[0].cigar if co.type == "M" and co.size > 0 )
                       else:
                          iv_seq = ( invert_strand( co.ref_iv ) for co in r[0].cigar if co.type == "M" and co.size > 0 )
                    else:
                       iv_seq = tuple()
                    if r[1] is not None and r[1].aligned:            
                       if opts.stranded != "reverse":
                          iv_seq = itertools.chain( iv_seq, 
                             ( invert_strand( co.ref_iv ) for co in r[1].cigar if co.type == "M" and co.size > 0 ) )
                       else:
                          iv_seq = itertools.chain( iv_seq, 
                             ( co.ref_iv for co in r[1].cigar if co.type == "M" and co.size > 0 ) )
                    else:
                       if ( r[0] is None ) or not ( r[0].aligned ):
                          notaligned += 1
                          continue         
                    try:
                       if ( r[0] is not None and r[0].optional_field( "NH" ) > 1 ) or \
                             ( r[1] is not None and r[1].optional_field( "NH" ) > 1 ):
                          nonunique += 1
                          continue
                    except KeyError:
                       pass
                    if ( r[0] and r[0].aQual < mapqMin ) or ( r[1] and r[1].aQual < mapqMin ):
                       lowqual += 1
                       continue         
                 
                 try:
                    if opts.mode == "union":
                       fs = set()
                       for iv in iv_seq:
                          if iv.chrom not in features.chrom_vectors:
                             raise UnknownChrom
                          for iv2, fs2 in features[ iv ].steps():
                             fs = fs.union( fs2 )
                    elif opts.mode == "intersection-strict" or opts.mode == "intersection-nonempty":
                       fs = None
                       for iv in iv_seq:
                          if iv.chrom not in features.chrom_vectors:
                             raise UnknownChrom
                          for iv2, fs2 in features[ iv ].steps():
                             if len(fs2) > 0 or opts.mode == "intersection-strict":
                                if fs is None:
                                   fs = fs2.copy()
                                else:
                                   fs = fs.intersection( fs2 )
                    else:
                       sys.exit( "Illegal overlap mode %s" % opts.mode )
                    if fs is None or len( fs ) == 0:
                       empty += 1
                    elif len( fs ) > 1:
                       ambiguous += 1
                    else:
                       ck = list(fs)[0]  
                       counts[ck][sami] += 1 # end up with counts for each sample as a list
                 except UnknownChrom:
                    if not pe_mode:
                       rr = r 
                    else: 
                       rr = r[0] if r[0] is not None else r[1]
                    empty += 1
                    if not opts.quiet:
                        sys.stdout.write( ( "Warning: Skipping read '%s', because chromosome " +
                          "'%s', to which it has been aligned, did not appear in the GFF file.\n" ) % 
                          ( rr.read.name, iv.chrom ) )
           except:
              if not pe_mode:
                 sys.stderr.write( "Error occured in %s.\n" % read_seq.get_line_number_string() )
              else:
                 sys.stderr.write( "Error occured in %s.\n" % read_seq_pe_file.get_line_number_string() )
              raise

           if not opts.quiet:
              sys.stdout.write( "%d sam %s processed for %s.\n" % ( seqi, "lines " if not pe_mode else "line pairs", colname ) )
       return counts,empty,ambiguous,lowqual,notaligned,nonunique,filtered,nreads

    warnings.showwarning = my_showwarning
    assert os.path.isfile(gff_filename),'## unable to open supplied gff file %s' % gff_filename
    try:
        counts,empty,ambiguous,lowqual,notaligned,nonunique,filtered,nreads = count_reads_in_features( sam_filenames, colnames, gff_filename,opts)
    except:
        sys.stderr.write( "Error: %s\n" % str( sys.exc_info()[1] ) )
        sys.stderr.write( "[Exception type: %s, raised in %s:%d]\n" % 
         ( sys.exc_info()[1].__class__.__name__, 
           os.path.basename(traceback.extract_tb( sys.exc_info()[2] )[-1][0]), 
           traceback.extract_tb( sys.exc_info()[2] )[-1][1] ) )
        sys.exit( 1 )
    return counts,empty,ambiguous,lowqual,notaligned,nonunique,filtered,nreads


def usage():
        print >> sys.stdout, """Usage: python htseqsams2mx.py -w <halfwindowsize> -g <gfffile.gff> -o <outfilename> [-i] [-c] --samf "<sam1.sam>,<sam1.column_header>" --samf "...<samN.column_header>" """
        sys.exit(1)

if __name__ == "__main__":
    """  
    <command interpreter="python">
    htseqsams2mx.py -w "$halfwin" -g "$gfffile" -o "$outfile" -m "union"
    #for $s in $samfiles:
    --samf "'${s.samf}','${s.samf.name}'"
    #end for
    </command>
    """
    if len(sys.argv) < 2:
        usage()
        sys.exit(1)
    starttime = time.time()
    op = optparse.OptionParser()
    # All tools
    op.add_option('-w', '--halfwindow', default="0")
    op.add_option('-m', '--mode', default="union")
    op.add_option('-s', '--stranded', default="no")
    op.add_option('-y', '--feature_type', default="exon")
    op.add_option('-g', '--gff_file', default=None)
    op.add_option('-o', '--outfname', default=None)
    op.add_option('-f','--forceName', default="false")
    op.add_option('--samf', default=[], action="append")
    op.add_option('--filter_extras', default=[], action="append")
    op.add_option('--mapqMin', default='0')
    op.add_option( "-t", "--type", type="string", dest="featuretype",
          default = "exon", help = "feature type (3rd column in GFF file) to be used, " +
             "all features of other type are ignored (default, suitable for Ensembl " +
             "GTF files: exon)" )

    op.add_option( "-i", "--id_attribute", type="string", dest="id_attribute",
          default = "gene_name", help = "GTF attribute to be used as feature ID (default, " +
          "suitable for Ensembl GTF files: gene_id)" )

    op.add_option( "-q", "--quiet", action="store_true", dest="quiet", default = False,
          help = "suppress progress report and warnings" )    
    opts, args = op.parse_args()
    halfwindow = int(opts.halfwindow)
    gff_file = opts.gff_file
    assert os.path.isfile(gff_file),'##ERROR htseqsams2mx: Supplied input GFF file "%s" not found' % gff_file
    outfname = opts.outfname
    sam_filenames = []
    colnames = []
    samf = opts.samf
    samfsplit = [x.split(',') for x in samf] # one per samf set
    samsets = []
    for samfs in samfsplit:
       samset = [x.replace("'","") for x in samfs]
       samset = [x.replace('"','') for x in samset]
       samsets.append(samset)
    samsets = [x for x in samsets if x[0].lower() != 'none'] 
    # just cannot stop getting these on cl! wtf in cheetah for a repeat group?
    samfnames = [x[0] for x in samsets]
    if len(set(samfnames)) != len(samfnames):
       samnames = []
       delme = []
       for i,s in enumerate(samfnames):
           if s in samnames:
              delme.append(i)
              print sys.stdout,'## WARNING htseqsams2mx: Duplicate input sam file %s in %s - ignoring dupe in 0 based position %s' %\
             (s,','.join(samfnames), str(delme))
           else:
              samnames.append(s) # first time
       samsets = [x for i,x in enumerate(samsets) if not (i in delme)]
       samfnames = [x[0] for x in samsets]
    scolnames = [x[1]for x in samsets]
    assert len(samfnames) == len(scolnames), '##ERROR sams2mx: Count of sam/cname not consistent - %d/%d' % (len(samfnames),len(scolnames))
    sam_exts = [x[2] for x in samsets]
    assert len(samfnames) == len(sam_exts), '##ERROR sams2mx: Count of extensions not consistent - %d/%d' % (len(samfnames),len(sam_exts))
    sam_bais = [x[3] for x in samsets] # these only exist for bams and need to be finessed with a symlink so pysam will just work
    for i,b in enumerate(samfnames):
        assert os.path.isfile(b),'## Supplied input sam file "%s" not found' % b
        sam_filenames.append(b)
        sampName = scolnames[i] # better be unique
        sampName = sampName.replace('#','') # for R
        sampName = sampName.replace('(','') # for R
        sampName = sampName.replace(')','') # for R
        sampName = sampName.replace(' ','_') # for R
        colnames.append(sampName)
    counts,empty,ambiguous,lowqual,notaligned,nonunique,filtered,nreads = htseqMX(gff_file, sam_filenames,colnames,sam_exts,sam_bais,opts)
    heads = '\t'.join(['Contig',] + colnames)
    res = [heads,]
    contigs = counts.keys()
    contigs.sort()
    totalc = 0
    emptycontigs = 0
    for contig in contigs:
        thisc = sum(counts[contig])
        if thisc > 0: # no output for empty contigs
            totalc += thisc
            crow = [contig,] + ['%d' % x for x in counts[contig]]
            res.append('\t'.join(crow))
        else:
            emptycontigs += 1
    outf = open(opts.outfname,'w')
    outf.write('\n'.join(res))
    outf.write('\n')
    outf.close()
    walltime = int(time.time() - starttime)
    accumulatornames = ('walltime (seconds)','total reads read','total reads counted','number of contigs','total empty reads','total ambiguous reads','total low quality reads',
           'total not aligned reads','total not unique mapping reads','extra filtered reads','empty contigs')
    accums = (walltime,nreads,totalc,len(contigs),empty,ambiguous,lowqual,notaligned,nonunique,filtered,emptycontigs)
    fracs = (1.0,1.0,float(totalc)/nreads,1.0,float(empty)/nreads,float(ambiguous)/nreads,float(lowqual)/nreads,float(notaligned)/nreads,float(nonunique)/nreads,float(filtered)/nreads,float(emptycontigs)/len(contigs))
    notes = ['%s = %d (%2.3f)' % (accumulatornames[i],x,100.0*fracs[i]) for i,x in enumerate(accums)]
    print >> sys.stdout, '\n'.join(notes)
    sys.exit(0)
