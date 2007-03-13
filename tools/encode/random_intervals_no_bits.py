#!/usr/bin/env python2.4
#%prog bounding_region_file mask_intervals_file intervals_to_mimic_file out_file mask_chr mask_start mask_end interval_chr interval_start interval_end interval_strand use_mask allow_strand_overlaps
import sys, random

max_iters = 100000

#Try to add a random region
def add_random_region(region, b_chr, b_start, b_end, exist_regions, mask, overlaps):
    rand_region = region.copy()
    for iter in range(max_iters):
        rand_region['start'] = random.randint(b_start, b_end - rand_region['length'])
        rand_region['end'] = rand_region['start'] + rand_region['length']
        
        if overlaps == "all":
            exist_regions.append(rand_region)
            return exist_regions, True
        
        found_overlap = False
        for region in exist_regions:
            if not (rand_region['end'] <= region['start'] or  region['end'] <= rand_region['start']):
                if overlaps=="none" or rand_region['strand'] == region['strand']:
                    found_overlap = True
            
        
        if not found_overlap:
            for region in mask:
	            if region['chr'] != rand_region['chr']:
	                continue
	            if not (rand_region['end'] <= region['start'] or  region['end'] <= rand_region['start']):
	                found_overlap = True
                
        if not found_overlap:
            exist_regions.append(rand_region)
            return exist_regions, True
    return exist_regions, False

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
                filepath =fields[3].replace("\n","").replace("\r","")
                available_regions[uid]=filepath
            except:
                continue

    except Exception, exc:
        print >>sys.stdout, 'random_intervals.py initialization error -> %s' % exc 

    if region_uid not in available_regions:
        print >>sys.stderr, "Invalid region selected"
        sys.exit(0)
    region_fname = available_regions[region_uid]

    
    bounds = []
    for line in open(region_fname):
        try:
	        if line[0:1] == "#":
	            continue
	        fields = line.split("\t")
	        b_dict = {}
	        b_dict['chr'] = fields[0]
	        b_dict['start'] = int(fields[1])
	        b_dict['end'] = int(fields[2].replace("\n","").replace("\r",""))
	        bounds.append(b_dict)
        except:
            continue
    
    regions = []
    for i in range(len(bounds)):
        regions.append([])
        
    for line in open(intervals_fname):
        try:
	        if line[0:1] == "#":
	            continue
	        fields = line.split("\t")
	        r_dict = {}
	        r_dict['chr'] = fields[interval_chr].replace("\n","").replace("\r","")
	        r_dict['start'] = int(fields[interval_start].replace("\n","").replace("\r",""))
	        r_dict['end'] = int(fields[interval_end].replace("\n","").replace("\r",""))
	        if interval_strand < 0:
	        	r_dict['strand'] = "+"
	        else:
	            try:
	                r_dict['strand'] = fields[interval_strand].replace("\n","").replace("\r","")
	            except:
	                r_dict['strand'] = "+"
	        r_dict['length'] = r_dict['end'] - r_dict['start']
	        
	        #loop through bounds, find first proper bounds then add in parrallel to regions
	        #if an interval crosses bounds, it will be added to the first bound
	        for i in range(len(bounds)):
	            b_chr = bounds[i]['chr']
	            if b_chr != r_dict["chr"]:
	                continue
	            b_start = bounds[i]['start']
	            b_end = bounds[i]['end']
	            
	            if (r_dict['start'] >= b_start and r_dict['start'] <= b_end) or (r_dict['end'] >= b_start and r_dict['end'] <= b_end):
	                regions[i].append(r_dict)
	                break
        except:
            continue    
    
    mask = []
    if use_mask != "no_mask":
        for line in open(mask_fname):
	        try:
		        if line[0:1] == "#":
		            continue
		        fields = line.split("\t")
		        m_dict = {}
		        m_dict['chr'] = fields[mask_chr].replace("\n","").replace("\r","")
		        m_dict['start'] = int(fields[mask_start].replace("\n","").replace("\r",""))
		        m_dict['end'] = int(fields[mask_end].replace("\n","").replace("\r",""))
		        mask.append(m_dict)
	        except:
	            continue


    
    out_file = open (out_fname, "w") or die ("Can not open output file")
    i = 0
    i_iters = 0
    region_count = 1
    while i < (len(bounds)):
        i_iters += 1
        random_regions = []
        added = True
        for j in range(len(regions[i])):
            random_regions, added = add_random_region(regions[i][j], bounds[i]['chr'], bounds[i]['start'], bounds[i]['end'], random_regions, mask, overlaps)
            if added == False:
                if i_iters < max_iters:
                    i-=1
                    break
                else:
                    added = True
                    i_iters = 0
                    print "After",str(max_iters),"x",str(max_iters),"iterations, a region could not be added."
                    if use_mask == "use_mask":
                        print "The mask you have provided may be too restrictive."
                
        if added == True:
	        i_iters = 0
	        for region in random_regions:
	            print >>out_file, "%s\t%d\t%d\t%s\t%s\t%s" % ( region['chr'], region['start'], region['end'], "region_"+str(region_count), "0", region['strand'] )
	            region_count +=1
        
        i+=1
    
    
if __name__ == "__main__": main()
