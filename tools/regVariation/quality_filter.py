#!/usr/bin/env python
#Guruprasad Ananda
"""
Filter based on nucleotide quality (PHRED score).

usage: %prog input out_file primary_species mask_species score mask_char mask_region mask_region_length
"""


from __future__ import division
from galaxy import eggs
import pkg_resources 
pkg_resources.require( "bx-python" )
pkg_resources.require( "lrucache" )
try:
    pkg_resources.require("numpy")
except:
    pass

import psyco_full
import sys
import os, os.path
from UserDict import DictMixin
from bx.binned_array import BinnedArray, FileBinnedArray
from bx.bitset import *
from bx.bitset_builders import *
from fpconst import isNaN
from bx.cookbook import doc_optparse
from galaxy.tools.exception_handling import *
import bx.align.maf

class FileBinnedArrayDir( DictMixin ):
    """
    Adapter that makes a directory of FileBinnedArray files look like
    a regular dict of BinnedArray objects. 
    """
    def __init__( self, dir ):
        self.dir = dir
        self.cache = dict()
    def __getitem__( self, key ):
        value = None
        if key in self.cache:
            value = self.cache[key]
        else:
            fname = os.path.join( self.dir, "%s.qa.bqv" % key )
            if os.path.exists( fname ):
                value = FileBinnedArray( open( fname ) )
                self.cache[key] = value
        if value is None:
            raise KeyError( "File does not exist: " + fname )
        return value

def stop_err(msg):
    sys.stderr.write(msg)
    sys.exit()

def load_scores_ba_dir( dir ):
    """
    Return a dict-like object (keyed by chromosome) that returns 
    FileBinnedArray objects created from "key.ba" files in `dir`
    """
    return FileBinnedArrayDir( dir )

def bitwise_and ( string1, string2, maskch ):
    result=[]
    for i,ch in enumerate(string1):
        try:
            ch = int(ch)
        except:
            pass
        if string2[i] == '-':
            ch = 1
        if ch and string2[i]:
            result.append(string2[i])
        else:
            result.append(maskch)
    return ''.join(result)

def main():   
    # Parsing Command Line here
    options, args = doc_optparse.parse( __doc__ )
    
    try:
        #chr_col_1, start_col_1, end_col_1, strand_col_1 = parse_cols_arg( options.cols )
        inp_file, out_file, pri_species, mask_species, qual_cutoff, mask_chr, mask_region, mask_length, loc_file = args
        qual_cutoff = int(qual_cutoff)
        mask_chr = int(mask_chr)
        mask_region = int(mask_region)
        if mask_region != 3:
            mask_length = int(mask_length)
        else:
            mask_length_r = int(mask_length.split(',')[0])
            mask_length_l = int(mask_length.split(',')[1])
    except:
        stop_err( "Data issue, click the pencil icon in the history item to correct the metadata attributes of the input dataset." )
    
    if pri_species == 'None':
        stop_err( "No primary species selected, try again by selecting at least one primary species." )
    if mask_species == 'None':
        stop_err( "No mask species selected, try again by selecting at least one species to mask." )

    mask_chr_count = 0
    mask_chr_dict = {0:'#', 1:'$', 2:'^', 3:'*', 4:'?', 5:'N'}
    mask_reg_dict = {0:'Current pos', 1:'Current+Downstream', 2:'Current+Upstream', 3:'Current+Both sides'}

    #ensure dbkey is present in the twobit loc file
    filepath = None
    try:
        pspecies_all = pri_species.split(',')
        pspecies_all2 = pri_species.split(',')
        pspecies = []
        filepaths = []
        for line in open(loc_file):
            if pspecies_all2 == []:    
                break
            if line[0:1] == "#":
                continue
            fields = line.split('\t')
            try:
                build = fields[0]
                for i,dbkey in enumerate(pspecies_all2):
                    if dbkey == build:
                        pspecies.append(build)
                        filepaths.append(fields[1])
                        del pspecies_all2[i]        
                    else:
                        continue
            except:
                pass
    except Exception, exc:
        stop_err( 'Initialization errorL %s' % str( exc ) )
    
    if len(pspecies) == 0:
        stop_err( "Quality scores are not available for the following genome builds: %s" % ( pspecies_all2 ) )
    if len(pspecies) < len(pspecies_all):
        print "Quality scores are not available for the following genome builds: %s" %(pspecies_all2)
    
    scores_by_chrom = []
    #Get scores for all the primary species
    for file in filepaths:
        scores_by_chrom.append(load_scores_ba_dir( file.strip() ))
    
    try:
        maf_reader = bx.align.maf.Reader( open(inp_file, 'r') )
        maf_writer = bx.align.maf.Writer( open(out_file,'w') )
    except Exception, e:
        stop_err( "Your MAF file appears to be malformed: %s" % str( e ) )
    
    maf_count = 0
    for block in maf_reader:
        status_strings = []
        for seq in range (len(block.components)):
            src = block.components[seq].src
            dbkey = src.split('.')[0]
            chr = src.split('.')[1]
            if not (dbkey in pspecies):
                continue
            else:    #enter if the species is a primary species
                index = pspecies.index(dbkey)
                sequence = block.components[seq].text
                s_start = block.components[seq].start
                size = len(sequence)    #this includes the gaps too
                status_str = '1'*size
                status_list = list(status_str)
                if status_strings == []:
                    status_strings.append(status_str)
                ind = 0
                s_end = block.components[seq].end
                #Get scores for the entire sequence
                try:
                    scores = scores_by_chrom[index][chr][s_start:s_end]
                except:
                    continue
                pos = 0
                while pos < (s_end-s_start):    
                    if sequence[ind] == '-':    #No score for GAPS
                        ind += 1
                        continue
                    score = scores[pos]
                    if score < qual_cutoff:
                        score = 0
                        
                    if not(score):
                        if mask_region == 0:    #Mask Corresponding position only
                            status_list[ind] = '0'
                            ind += 1
                            pos += 1
                        elif mask_region == 1:    #Mask Corresponding position + downstream neighbors
                            for n in range(mask_length+1):
                                try:
                                    status_list[ind+n] = '0'
                                except:
                                    pass
                            ind = ind + mask_length + 1
                            pos = pos + mask_length + 1
                        elif mask_region == 2:    #Mask Corresponding position + upstream neighbors
                            for n in range(mask_length+1):
                                try:
                                    status_list[ind-n] = '0'
                                except:
                                    pass
                            ind += 1
                            pos += 1
                        elif mask_region == 3:    #Mask Corresponding position + neighbors on both sides
                            for n in range(-mask_length_l,mask_length_r+1):
                                try:
                                    status_list[ind+n] = '0'
                                except:
                                    pass
                            ind = ind + mask_length_r + 1
                            pos = pos + mask_length_r + 1
                    else:
                        pos += 1
                        ind += 1
                    
                status_strings.append(''.join(status_list))
        
        if status_strings == []:    #this block has no primary species
            continue
        output_status_str = status_strings[0]
        for stat in status_strings[1:]:
            try:
                output_status_str = bitwise_and (status_strings[0], stat, '0')
            except Exception, e:
                break
            
        for seq in range (len(block.components)):
            src = block.components[seq].src
            dbkey = src.split('.')[0]
            if dbkey not in mask_species.split(','):
                continue
            sequence = block.components[seq].text
            sequence = bitwise_and (output_status_str, sequence, mask_chr_dict[mask_chr])
            block.components[seq].text = sequence
            mask_chr_count += output_status_str.count('0')
        maf_writer.write(block)
        maf_count += 1
        
    maf_reader.close()
    maf_writer.close()
    print "No. of blocks = %d; No. of masked nucleotides = %s; Mask character = %s; Mask region = %s; Cutoff used = %d" %(maf_count, mask_chr_count, mask_chr_dict[mask_chr], mask_reg_dict[mask_region], qual_cutoff)
    
    
if __name__ == "__main__":
    main()
