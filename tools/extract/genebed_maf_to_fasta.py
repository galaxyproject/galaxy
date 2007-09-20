#!/usr/bin/env python2.4

"""
Reads a gene BED and an indexed MAF. Produces a FASTA file containing
the aligned gene sequences, based upon the provided coordinates

If index_file is not provided maf_file.index is used.

Alignment blocks are layered ontop of each other based upon score.

usage: %prog dbkey_of_BED comma_separated_list_of_additional_dbkeys_to_extract comma_separated_list_of_indexed_maf_files input_gene_bed_file output_fasta_file
"""

#import psyco_full
import pkg_resources; pkg_resources.require( "bx-python" )
import bx.align.maf
import sys
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
    
    #Allow users to specify gap char for missing data: ? or -
    try:
        GAP_NO_DATA = sys.argv.pop(1)
        ALL_GAP_TYPES = [GAP_NORMAL,GAP_NO_DATA,GAP_INSERT]
    except: pass
    
    #ensure dbkey is set
    if dbkey == "?": 
        print >>sys.stderr, "You must specify a proper build in order to extract alignments. You can specify your genome build by clicking on the pencil icon associated with your interval file."
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
        print >>sys.stdout, 'genebed_maf_to_fasta.py initialization error -> %s' % exc 
    
    
    
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


    
    #Step through gene bed
    for line in open(interval_file, "r").readlines():
        line_count += 1
        try:
            if line[0:1]=="#":
                continue
            
            #Storage for exons of this gene
            exons = []
            
            #load gene bed fields
            try:
                fields = line.split()
                chrom     = fields[0]
                tx_start  = int( fields[1] )
                tx_end    = int( fields[2] )
                name      = fields[3]
                strand    = fields[5]
                if strand != '-': strand='+' #Default strand is +
                cds_start = int( fields[6] )
                cds_end   = int( fields[7] )
                
                #Calculate and store starts and ends of coding exons
                region_start, region_end = cds_start, cds_end
                exon_starts = map( int, fields[11].rstrip( ',\n' ).split( ',' ) )
                exon_starts = map((lambda x: x + tx_start ), exon_starts)
                exon_ends = map( int, fields[10].rstrip( ',' ).split( ',' ) )
                exon_ends = map((lambda x, y: x + y ), exon_starts, exon_ends);
                for start, end in zip( exon_starts, exon_ends ):
                    start = max( start, region_start )
                    end = min( end, region_end )
                    if start < end:
                        alignment = Genomic_Region()
                        for i in range(end-start):
                            alignment.append(Genomic_Position(dbkey, target_dbkey))
                        exons.append({'name':name,'ref_chrom':chrom,'ref_start':start,'ref_end':end,'ref_strand':strand,'alignment':alignment})
            except Exception, e:
                print "Error loading exon positions from input line %i:" % line_count, e
                continue
            
            for exon in exons:
                try:
                    src = dbkey + "." + exon['ref_chrom']
                    start = exon['ref_start']
                    end = exon['ref_end']
                    strand = exon['ref_strand']
                    alignment = exon['alignment']
                    
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
                        sliced_offset = sliced_ref.start - exon['ref_start']
                        
                        ref_block_seq =  list(sliced_ref.text.rstrip())
                        
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
                        
                        
                        
                    
                except Exception, e:
                    print "Error filling exons with MAFs from input line %i:" % line_count, e
                    continue
                    
            
            #exons loaded, now output them stitched together in proper orientation
            sequences = {}
            for key in [dbkey] + target_dbkey:
                sequences[key] = ""
            
            step_list = range(len(exons))
            if strand == "-": step_list.reverse()
            for i in step_list:
                exon = exons[i]
                for key in [dbkey] + target_dbkey:
                    if strand == "-":
                        sequences[key] += reverse_complement(exon['alignment'].get_sequence(key))
                    else:
                        sequences[key] += exon['alignment'].get_sequence(key)
            
            
            if include_primary:
                print >>output, ">%s.%s" %(dbkey, name)
                print >>output, sequences[dbkey]
            for t_key in target_dbkey:
                print >>output, ">%s.%s" %(t_key, name)
                print >>output, sequences[t_key]
            print >>output
            
            genes_extracted += 1

        except Exception, e:
            print "Unexpected error from input line %i:" % line_count, e
            continue
    
    output.close()
    print "%i genes were extracted successfully." % genes_extracted
if __name__ == "__main__": __main__()
