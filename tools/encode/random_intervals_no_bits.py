#!/usr/bin/env python2.4
#Dan Blankenberg
#%prog bounding_region_file mask_intervals_file intervals_to_mimic_file out_file mask_chr mask_start mask_end interval_chr interval_start interval_end interval_strand use_mask allow_strand_overlaps
import sys, random
from copy import deepcopy

import pkg_resources
pkg_resources.require( "bx-python" )
import bx.intervals.io
import bx.intervals.intersection
import psyco_full

max_iters = 5


#Try to add a random region
def add_random_region(mimic_region, bound, exist_regions, plus_mask, minus_mask, overlaps):
    region_length, region_strand = mimic_region
    plus_count = plus_mask.count_range()
    minus_count = minus_mask.count_range()
    
    gaps = []
    if region_strand == "-": gaps = minus_mask.get_gaps(region_length)
    else: gaps = plus_mask.get_gaps(region_length)
    
    while True:
        try: gap_length, gap_start, gap_end = gaps.pop(random.randint(0,len(gaps)-1))
        except: break
        start = random.randint(bound.start+gap_start, bound.start+gap_end-region_length-1)
        end = start + region_length
        
        try_plus_mask = plus_mask.copy()
        try_minus_mask = minus_mask.copy()
        
        if region_strand == "-":
            try_minus_mask.set_range(start-bound.start, end-bound.start)
        else:
            try_plus_mask.set_range(start-bound.start, end-bound.start)
        
        rand_region = bx.intervals.io.GenomicInterval( None, [bound.chrom,start,end,region_strand], 0, 1, 2, 3, "+", fix_strand=True )
        
        if try_plus_mask.count_range() == plus_count + region_length or try_minus_mask.count_range() == minus_count + region_length:
            if overlaps in ["strand", "all"]: #overlaps allowed across strands
                exist_regions.append(rand_region)
                if overlaps == "strand":
                    return exist_regions, True, try_plus_mask, try_minus_mask
                else: #overlaps allowed everywhere
                    return exist_regions, True, plus_mask, minus_mask
            else: #no overlapping anywhere
                exist_regions.append(rand_region)
                if region_strand == "-": return exist_regions, True, try_minus_mask.copy(), try_minus_mask
                else: return exist_regions, True, try_plus_mask, try_plus_mask.copy()
        
        
    return exist_regions, False, plus_mask, minus_mask




def main():
    region_uid = sys.argv[1]
    mask_fname = sys.argv[2]
    intervals_fname = sys.argv[3]
    out_fname = sys.argv[4]
    mask_chr = int(sys.argv[5])-1
    mask_start = int(sys.argv[6])-1
    mask_end = int(sys.argv[7])-1
    interval_chr = int(sys.argv[8])-1
    interval_start = int(sys.argv[9])-1
    interval_end = int(sys.argv[10])-1
    interval_strand = int(sys.argv[11])-1
    use_mask = sys.argv[12]
    overlaps = sys.argv[13]
    
    
    available_regions = {}
    
    loc_file = "/depot/data2/galaxy/regions.loc"
    
    
    try:
        for line in open( loc_file ):
            if line[0:1] == "#" : continue
        
            fields = line.split('\t')
            #read each line, if not enough fields, go to next line
            try:
                build = fields[0]
                uid = fields[1]
                description = fields[2]
                filepath = fields[3].replace("\n","").replace("\r","")
                available_regions[uid]=filepath
            except:
                continue

    except Exception, exc:
        print >>sys.stdout, 'random_intervals.py initialization error -> %s' % exc 

    if region_uid not in available_regions:
        print >>sys.stderr, "Invalid region selected"
        sys.exit(0)
    region_fname = available_regions[region_uid]

    
    #set up bounding regions to hold random intervals
    bounds = []
    for bound in bx.intervals.io.GenomicIntervalReader( open( region_fname, 'r' ), chrom_col=0, start_col=1, end_col=2, fix_strand=True): bounds.append(bound)
    
    #set up length and number of regions to mimic
    regions = [ [] for i in range(len(bounds)) ]
    
    for region in bx.intervals.io.GenomicIntervalReader( open(intervals_fname, 'r' ), chrom_col=interval_chr, start_col=interval_start, end_col=interval_end, strand_col=interval_strand, fix_strand=True, return_header=False):
        #loop through bounds, find first proper bounds then add
        #if an interval crosses bounds, it will be added to the first bound
        for i in range(len(bounds)):
            if bounds[i].chrom != region.chrom:
                continue
            intersecter = bx.intervals.intersection.Intersecter()
            intersecter.add_interval( bounds[i] )
            if len(intersecter.find(region.start, region.end))>0:
                regions[i].append( (region.end-region.start, region.strand) ) #add region to proper bound and go to next region
                break
    for region in regions:
        region.sort()
        region.reverse()
    
    #read mask file
    mask = []
    if use_mask != "no_mask":
        for region in bx.intervals.io.GenomicIntervalReader( open(mask_fname, 'r' ), chrom_col=mask_chr, start_col=mask_start, end_col=mask_end, fix_strand=True): mask.append(region)
    
    out_file = open (out_fname, "w") or die ("Can not open output file")
    
    i = 0
    i_iters = 0
    region_count = 0
    best_regions = []
    num_fail = 0
    while i < len(bounds):
        i_iters += 1
        
        #order regions to mimic
        regions_to_mimic = regions[i][0:]
        if len(regions_to_mimic) < 1: #if no regions to mimic, skip
            i+=1
            i_iters = 0
            continue 
        
        #set up region mask
        plus_mask = Region(bounds[i].end-bounds[i].start)
        for region in mask:
            if region.chrom != bounds[i].chrom: continue
            mask_start = region.start - bounds[i].start
            mask_end = region.end - bounds[i].start
            if mask_start >= 0 and mask_end > 0:
                plus_mask.set_range(mask_start, mask_end)
        minus_mask = plus_mask.copy()
        
        random_regions = []
        num_added = 0
        for j in range(len(regions[i])):
            random_regions, added, plus_mask, minus_mask = add_random_region(regions_to_mimic[j], bounds[i], random_regions, plus_mask, minus_mask, overlaps)
            if added: num_added += 1
        
        if num_added == len(regions_to_mimic) or i_iters >= max_iters:
            if len(best_regions) > len(random_regions): random_regions = best_regions.copy()
            num_fail += (len(regions_to_mimic)-len(random_regions))
            i_iters = 0
            best_regions = []
            for region in random_regions:
                print >>out_file, "%s\t%d\t%d\t%s\t%s\t%s" % ( region.chrom, region.start, region.end, "region_"+str(region_count), "0", region.strand )
                region_count += 1
        else:
            i-=1
            if len(best_regions) < len(random_regions): best_regions = random_regions[:]
        
        i+=1
    
    out_file.close()
    if num_fail:
        print "After %i iterations, %i regions could not be added." % (max_iters, num_fail)
        if use_mask == "use_mask": print "The mask you have provided may be too restrictive."


class Region( list ):
    """
    A list for on/off regions
    """
    def __init__( self, size=0 ):
        for i in range(size): self.append(False)
    def copy(self):
        return deepcopy(self)
    def set_range(self, start=0, end=None):
        if start < 0: start = 0
        if (not end and end != 0) or end > len(self): end = len(self)
        for i in range(start,end): self[i]=True
    def count_range(self, start=0, end=None):
        if start < 0: start = 0
        if (not end and end != 0) or end > len(self): end = len(self)
        return self[start:end].count(True)
    def get_gaps(self, min_size = 0):
        gaps = []
        start = end = 0
        while True:
            try: start = self[end:].index(False) + end
            except: break
            try: end = self[start:].index(True) + start
            except: end = len(self)
            if end > start and end-start >= min_size: gaps.append( ( end-start, start, end ) )
        gaps.sort()
        gaps.reverse()
        return gaps
    

if __name__ == "__main__": main()