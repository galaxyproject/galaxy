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
from bx import interval_index_file
import sys, os
import string
import tempfile

#Used to reverse compliment DNA
DNA_COMP = string.maketrans( "ACGTacgt", "TGCAtgca" )
def reverse_complement(text):
    comp = [ch for ch in text.translate(DNA_COMP)]
    comp.reverse()
    return "".join(comp)


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
        print >>sys.stderr, "You must specify a proper build in order to extract alignments."
        sys.exit()
    
    output = open(output_file, "w");
    
    line_count = 0
    genes_extracted = 0
    
    #index maf for use here
    indexes = interval_index_file.Indexes()
    
    maf_reader = bx.align.maf.Reader( open( mafFile ) )
    # Need to be a bit tricky in our iteration here to get the 'tells' right
    while 1:
        pos = maf_reader.file.tell()
        block = maf_reader.next()
        if block is None: break
        for c in block.components:
            indexes.add( c.src, c.forward_strand_start, c.forward_strand_end, pos )
    index_filename = tempfile.NamedTemporaryFile().name
    out = open(index_filename,'w')
    indexes.write(out)
    out.close()
    
    
    index = bx.align.maf.Indexed(mafFile, index_filename = index_filename)
    
    
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
                        target_chrom = {}
                        target_strand = {}
                        target_start = {}
                        target_end = {}
                        target_sequence = {}
                        for t_key in target_dbkey:
                            #initialize exons with gaps in all positions
                            target_sequence[t_key] = [GAP_NO_DATA for i in range(end-start)]
                            target_chrom[t_key] = []
                            target_strand[t_key] = []
                            target_start[t_key] = []
                            target_end[t_key] = []
                        exons.append({'name':name,'ref_chrom':chrom,'target_chrom':target_chrom,'ref_start':start,'target_start':target_start,'ref_end':end,'target_end':target_end,'ref_strand':strand,'target_strand':target_strand,'ref_sequence':[GAP_NO_DATA for i in range(end-start)],'target_sequence':target_sequence,'ref_gaps':[]})
            except Exception, e:
                print "Error loading exon positions from input line %i:" % line_count, e
                continue
            
            for exon in exons:
                try:
                    src = dbkey + "." + exon['ref_chrom']
                    start = exon['ref_start']
                    end = exon['ref_end']
                    strand = exon['ref_strand']
                    
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
                        
                        #save old score here for later use, since slice results score==0
                        old_score =  maf.score
                        
                        #slice maf by start and end
                        # If the reference component is on the '-' strand we should complement the interval
                        if ref.strand == '-':
                            slice_start = max( ref.src_size - end, ref.start )
                            slice_end = max( ref.src_size - start, ref.end )
                        else:
                            slice_start = max( start, ref.start )
                            slice_end = min( end, ref.end )
                        sliced = maf.slice_by_component( ref, slice_start, slice_end ) 
                        
                        sliced_ref = sliced.get_component_by_src( src )
                        sliced_target={}
                        for t_key in target_dbkey:
                            sliced_target[t_key] = sliced.get_component_by_src_start( t_key )
                        
                        start_offset = sliced_ref.start - exon['ref_start']
                        
                        ref_seq =  list(sliced_ref.text)
                        
                        #sliced_target is empty if doesn't exist
                        targ_seq = {}
                        for t_key in target_dbkey:
                            try:
                                targ_seq[t_key] = list(sliced_target[t_key].text)
                            except:
                                targ_seq[t_key] = [GAP_NO_DATA for i in range(len(ref_seq))]
                        
                        
                        #determin new gap locations 
                        new_ref_gap_indicies = [i+start_offset for i in xrange(len(ref_seq)) if ref_seq[i] == GAP_NORMAL]
                        try:
                            old_ref_gap_indicies = exon['ref_gaps'][0:]
                        except:
                            old_ref_gap_indicies = []
                        new_adj_gap_indicies = []
                        old_adj_gap_indicies = []
                        
                        while len(new_ref_gap_indicies+old_ref_gap_indicies) > 0:
                            this_gap = min(new_ref_gap_indicies+old_ref_gap_indicies)
                            
                            #gap exists previously, but is not currently present
                            if this_gap in old_ref_gap_indicies and this_gap not in new_ref_gap_indicies:
                                #add gap to exist list
                                old_adj_gap_indicies.append(this_gap)
                                #update indicies of new gaps
                                for i in range(len(new_ref_gap_indicies)):
                                    new_ref_gap_indicies[i] = new_ref_gap_indicies[i]+1
                                #remove gap from old_ref_gap_indicies
                                old_ref_gap_indicies.remove(this_gap)
                                
                                #add gap char into block sequences:
                                ref_seq.insert(this_gap-start_offset,GAP_INSERT)
                                for t_key in target_dbkey:
                                    targ_seq[t_key].insert(this_gap-start_offset,GAP_INSERT)
                                
                            #gap doesn't exists previously, but is currently present
                            elif this_gap not in old_ref_gap_indicies and this_gap in new_ref_gap_indicies:
                                #add gap to new list
                                new_adj_gap_indicies.append(this_gap)
                                #update indicies of new gaps
                                for i in range(len(old_ref_gap_indicies)):
                                    old_ref_gap_indicies[i] = old_ref_gap_indicies[i]+1
                                #remove gap from new_ref_gap_indicies
                                new_ref_gap_indicies.remove(this_gap)
                                
                                #gap doesn't exist previously, add gap char into exon sequences:
                                exon['ref_sequence'].insert(this_gap,GAP_INSERT)
                                for t_key in target_dbkey:
                                    exon['target_sequence'][t_key].insert(this_gap,GAP_INSERT)
                                
                            #gap is in new and old, simply place it back on both lists
                            else:
                                old_adj_gap_indicies.append(this_gap)
                                new_adj_gap_indicies.append(this_gap)
                                #remove gaps from working list
                                old_ref_gap_indicies.remove(this_gap)
                                new_ref_gap_indicies.remove(this_gap)
                        
                        #create and sort list of all Gaps, removing duplicates
                        temp = {}
                        for g in (old_adj_gap_indicies + new_adj_gap_indicies): temp[g]=g
                        temp = temp.keys()
                        temp.sort()
                        exon['ref_gaps'] = temp
                        
                        #Exon and block sequences should now have same number of gaps
                        
                        
                        filled = False
                        for i in range(start_offset, len(exon['ref_sequence'])):
                            if i-start_offset >= len(ref_seq): break #this block doesn't cover to edge
                            
                            #Don't overwrite bases with gaps
                            if ref_seq[i-start_offset] not in ALL_GAP_TYPES:
                                exon['ref_sequence'][i] = ref_seq[i-start_offset]
                            for t_key in target_dbkey:
                                if targ_seq[t_key][i-start_offset] not in ALL_GAP_TYPES:
                                    exon['target_sequence'][t_key][i] = targ_seq[t_key][i-start_offset]
                            
                            #Store block info for exons
                            if not filled:
                                for t_key in target_dbkey:
                                    if sliced_target[t_key]:
                                        exon['target_start'][t_key].append(sliced_target[t_key].start)
                                        exon['target_end'][t_key].append(sliced_target[t_key].end)
                                        exon['target_strand'][t_key].append(sliced_target[t_key].strand)
                                        exon['target_chrom'][t_key].append(bx.align.maf.src_split(sliced_target[t_key].src)[-1])
                                filled=True
                    
                except Exception, e:
                    print "Error filling exons with MAFs from input line %i:" % line_count, e
                    continue
                    
            
            #exons loaded, now output them stitched together in proper orientation
            seq1=""
            seq2={}
            chr1=[]
            chr2={}
            start1=[]
            start2={}
            end1=[]
            end2={}
            strand1=[]
            strand2={}
            gaps =[]
            gap_offset = 0
            gene_name = ""
            for t_key in target_dbkey:
                seq2[t_key]=""
                start2[t_key]=[]
                end2[t_key]=[]
                chr2[t_key]=[]
                strand2[t_key]=[]
            
            strand = exons[0]['ref_strand']
            if strand == '-':
                exons.reverse()
                for exon in exons:
                    gene_name = exon['name']
                    for gap in exon['ref_gaps']:
                        gaps.append(len(exon['ref_sequence'])-gap+gap_offset-1)
                    gap_offset += len(exon['ref_sequence'])
                    
                    chr1.append(exon['ref_chrom'])
                    start1.append(str(exon['ref_start']))
                    end1.append(str(exon['ref_end']))
                    strand1.append(exon['ref_strand'])
                    seq1+=reverse_complement("".join(exon['ref_sequence']))
                    for t_key in target_dbkey:
                        start2[t_key].append(str(exon['target_start'][t_key])[1:-1].replace(" ",""))
                        end2[t_key].append(str(exon['target_end'][t_key])[1:-1].replace(" ",""))
                        chr2[t_key].append(",".join(exon['target_chrom'][t_key]))
                        strand2[t_key].append(",".join(exon['target_strand'][t_key]))
                        seq2[t_key]+=reverse_complement("".join(exon['target_sequence'][t_key]))
                        
            else:
                for exon in exons:
                    gene_name = exon['name']
                    for gap in exon['ref_gaps']:
                        gaps.append(gap+gap_offset)
                    gap_offset += len(exon['ref_sequence'])
                    
                    chr1.append(exon['ref_chrom'])
                    start1.append(str(exon['ref_start']))
                    end1.append(str(exon['ref_end']))
                    strand1.append(exon['ref_strand'])
                    seq1+="".join(exon['ref_sequence'])
                    for t_key in target_dbkey:
                        start2[t_key].append(str(exon['target_start'][t_key])[1:-1].replace(" ",""))
                        end2[t_key].append(str(exon['target_end'][t_key])[1:-1].replace(" ",""))
                        chr2[t_key].append(",".join(exon['target_chrom'][t_key]))
                        strand2[t_key].append(",".join(exon['target_strand'][t_key]))
                        seq2[t_key]+="".join(exon['target_sequence'][t_key])
            
            gaps.sort()
            if include_primary:
                #print >>output, ">%s.%s|%s(%s)%s-%s|gaps:%s" %(dbkey, gene_name,";".join(chr1),";".join(strand1),";".join(start1),";".join(end1),",".join([str(i) for i in gaps ]))
                print >>output, ">%s.%s" %(dbkey, gene_name)
                print >>output, seq1
            for t_key in target_dbkey:
                #print >>output, ">%s.%s|%s(%s)%s-%s" %(t_key, gene_name,";".join(chr2[t_key]),";".join(strand2[t_key]),";".join(start2[t_key]),";".join(end2[t_key]))
                print >>output, ">%s.%s" %(t_key, gene_name)
                print >>output, seq2[t_key]
            print >>output
            
            genes_extracted += 1

        except Exception, e:
            print "Unexpected error from input line %i:" % line_count, e
            continue
    
    output.close()
    os.unlink(index_filename)
    print "%i genes were extracted successfully." % genes_extracted
if __name__ == "__main__": __main__()
