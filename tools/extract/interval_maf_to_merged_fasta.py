#!/usr/bin/env python2.4

"""
Reads a gene BED and an indexed MAF. Produces a FASTA file containing
the aligned gene sequences, based upon the provided coordinates

If index_file is not provided maf_file.index is used.

Alignment blocks are layered ontop of each other based upon score.

usage: %prog dbkey_of_BED comma_separated_list_of_additional_dbkeys_to_extract comma_separated_list_of_indexed_maf_files input_gene_bed_file output_fasta_file
"""
#Dan Blankenberg
#import psyco_full
import pkg_resources; pkg_resources.require( "bx-python" )
import bx.align.maf
from bx import interval_index_file
import bx.intervals.io
import sys, os
import string

#Used to reverse compliment DNA
DNA_COMP = string.maketrans( "ACGTacgt", "TGCAtgca" )
def reverse_complement(text):
    comp = [ch for ch in text.translate(DNA_COMP)]
    comp.reverse()
    return "".join(comp)

#an object corresponding to a reference genome position
class Genomic_Position(object):
    def __init__(self, dbkey, t_keys):
        self.dbkey = dbkey
        self.bases = {}
        for t_key in [dbkey]+t_keys: self.bases[t_key] = "-"
        self.children = []
    def get_sequence (self, key = None):
        if not key: key = self.dbkey
        seq = ""
        positions = [self] + self.children
        for position in positions:
            seq += position.bases[key]
        return seq
#a list of reference genome positions
class Genomic_Region(list):
    def get_sequence (self, key):
        seq = ""
        for position in self:
            seq += position.get_sequence(key)
        return seq
    def count_gaps(self):
        gaps = 0
        for position in self:
            gaps =+ len(position.children)
        return gaps

#define Different Gap types, mostly used for debuging
GAP_NORMAL = "-"
GAP_NO_DATA = "?"
GAP_INSERT = "!"
GAP_NO_DATA = GAP_INSERT = GAP_NORMAL #Makes all Gaps equal, comment for debug chars

ALL_GAP_TYPES = [GAP_NORMAL,GAP_NO_DATA,GAP_INSERT]


def __main__():

    #Parse Command Line
    dbkey = sys.argv.pop(1)
    target_dbkey = sys.argv.pop(1).split(",")
    include_primary = True
    try: target_dbkey.remove(dbkey)
    except: include_primary = False
    mafFile = sys.argv.pop(1)
    interval_file = sys.argv.pop(1)
    output_file = sys.argv.pop(1)
    chr_col  = int(sys.argv.pop(1).strip())-1
    start_col = int(sys.argv.pop(1).strip())-1
    end_col = int(sys.argv.pop(1).strip())-1
    strand_col = int(sys.argv.pop(1).strip())-1
    
    #Allow users to specify gap char for missing data: ? or -
    try:
        GAP_NO_DATA = sys.argv.pop(1)
        ALL_GAP_TYPES = [GAP_NORMAL,GAP_NO_DATA,GAP_INSERT]
    except: pass
    
    #ensure dbkey is set
    if dbkey == "?": 
        print >>sys.stderr, "You must specify a proper build in order to extract alignments."
        sys.exit()
    
    output = open(output_file, "w");
    
    line_count = 0
    genes_extracted = 0
    
    
    maf_sets = {}
    try:
        for line in open( "/depot/data2/galaxy/maf_index.loc" ):
            if line[0:1] == "#" : continue
            fields = line.split('\t')
            #read each line, if not enough fields, go to next line
            try:
                maf_desc = fields[0]
                maf_uid = fields[1]
                builds = fields[2]
                build_to_common_list = {}
                common_to_build_list = {}
                split_builds = builds.split(",")
                for build in split_builds:
                    this_build = build.split("=")[0]
                    try:
                        this_common = build.split("=")[1]
                    except:
                        this_common = this_build
                    build_to_common_list[this_build]=this_common
                    common_to_build_list[this_common]=this_build
                    
                paths = fields[3].replace("\n","").replace("\r","")
                maf_sets[maf_uid]={}
                maf_sets[maf_uid]['description']=maf_desc
                maf_sets[maf_uid]['builds']=build_to_common_list
                maf_sets[maf_uid]['common']=common_to_build_list
                maf_sets[maf_uid]['paths']=paths.split(",")
            except:
                continue

    except Exception, exc:
        print >>sys.stdout, 'interval_maf_to_merged_fasta.py initialization error -> %s' % exc 
    
    
    
    #Open MAF Files, with indexes
    try:
        mafFile = maf_sets[mafFile]['paths']
    except:
        print >>sys.stderr, "The MAF source specified appears to be invalid."
        sys.exit()
    
    try:
        # Open indexed access to mafs
        index = bx.align.maf.MultiIndexed( mafFile, keep_open=True, parse_e_rows=True )
    except:
        print >>sys.stderr, "The MAF source specified [", mafType ,"] appears to be missing."
        sys.exit()

    #Step through interval file
    for region in bx.intervals.io.GenomicIntervalReader( open(interval_file, 'r' ), chrom_col=chr_col, start_col=start_col, end_col=end_col, strand_col=strand_col, fix_strand=True):
        target_sequences = {}
        alignment = Genomic_Region()
        for i in range(region.end-region.start): alignment.append(Genomic_Position(dbkey, target_dbkey))
        src = dbkey + "." + region.chrom
        start = region.start
        end = region.end
        strand = region.strand
        
        blocks = index.get( src, start, end )
        
        #Order the blocks by score, lowest first
        blocks2 = []
        for block in blocks:
            for i in range(0,len(blocks2)):
                if float(block.score) < float(blocks2[i].score):
                    blocks2.insert(i,block)
                    break
            else:
                blocks2.append( block )
        blocks = blocks2
        
        for maf in blocks:
            maf = maf.limit_to_species([dbkey]+target_dbkey)
            maf.remove_all_gap_columns()
            ref = maf.get_component_by_src( src )
            #We want our block coordinates to be from positive strand
            if ref.strand == "-":
                maf = maf.reverse_complement()
                ref = maf.get_component_by_src( src )
                
            #save old score here for later use, since slice results score==0
            old_score =  maf.score
            
            #slice maf by start and end
            slice_start = max( start, ref.start )
            slice_end = min( end, ref.end )
            
            try:
                sliced = maf.slice_by_component( ref, slice_start, slice_end )
            except:
                continue
            sliced_ref = sliced.get_component_by_src( src )
            sliced_offset = sliced_ref.start - region.start
            
            ref_block_seq =  list(sliced_ref.text.rstrip().rstrip("-"))
            
            #sliced_target is empty if doesn't exist
            targ_block_seq = {}
            for t_key in target_dbkey:
                try:
                    targ_block_seq[t_key] = list(sliced.get_component_by_src_start( t_key ).text) #list(sliced_target[t_key].text)
                except:
                    targ_block_seq[t_key] = [GAP_NO_DATA for i in range(len(ref_block_seq))]
            
            
            gaps_found = 0
            recent_gaps = 0
            for i in range(len(ref_block_seq)):
                if ref_block_seq[i] not in GAP_NORMAL: #this is a position
                    recent_gaps = 0
                    alignment[i+sliced_offset-gaps_found].bases[dbkey] = ref_block_seq[i]
                    for t_key in target_dbkey:
                        if targ_block_seq[t_key][i] not in ALL_GAP_TYPES:
                            alignment[i+sliced_offset-gaps_found].bases[t_key] = targ_block_seq[t_key][i]
                else: #this is a gap
                    gaps_found += 1
                    recent_gaps += 1
                    if recent_gaps > len(alignment[i+sliced_offset-gaps_found].children):
                        alignment[i+sliced_offset-gaps_found].children.append(Genomic_Position(dbkey, target_dbkey))
                    if ref_block_seq[i] not in ALL_GAP_TYPES:
                        alignment[i+sliced_offset-gaps_found].children[recent_gaps-1].bases[dbkey] = ref_block_seq[i]
                    for t_key in target_dbkey:
                        if targ_block_seq[t_key][i] not in ALL_GAP_TYPES:
                            alignment[i+sliced_offset-gaps_found].children[recent_gaps-1].bases[t_key] = targ_block_seq[t_key][i]
            
            
        if include_primary:
            print >>output, ">%s.%s(%s):%s-%s" %(dbkey, region.chrom, region.strand, region.start, region.end )
            if region.strand == "-":
                print >>output, reverse_complement(alignment.get_sequence(dbkey))
            else:
                print >>output, alignment.get_sequence(dbkey)
        for t_key in target_dbkey:
            print >>output, ">%s" %(t_key)
            if region.strand == "-":
                print >>output, reverse_complement(alignment.get_sequence(t_key))
            else:
                print >>output, alignment.get_sequence(t_key)
        print >>output
        
        genes_extracted += 1
    
    output.close()
    
    print "%i regions were extracted successfully." % genes_extracted
if __name__ == "__main__": __main__()
