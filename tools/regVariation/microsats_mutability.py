#!/usr/bin/env python
#Guruprasad Ananda
"""
This tool computes microsatellite mutability for the orthologous microsatellites fetched from  'Extract Orthologous Microsatellites from pair-wise alignments' tool.
"""
from galaxy import eggs
import sys, string, re, commands, tempfile, os, fileinput
from galaxy.tools.util.galaxyops import *
from bx.intervals.io import *
from bx.intervals.operations import quicksect

fout = open(sys.argv[2],'w')
p_group = int(sys.argv[3])        #primary "group-by" feature
p_bin_size = int(sys.argv[4])
s_group = int(sys.argv[5])        #sub-group by feature
s_bin_size = int(sys.argv[6])
mono_threshold = 9
non_mono_threshold = 4
p_group_cols = [p_group, p_group+7]
s_group_cols = [s_group, s_group+7]
num_generations = int(sys.argv[7])
region = sys.argv[8] 
int_file = sys.argv[9]
if int_file != "None": #User has specified an interval file
    try:
        fint = open(int_file, 'r')
        dbkey_i = sys.argv[10]
        chr_col_i, start_col_i, end_col_i, strand_col_i = parse_cols_arg( sys.argv[11] )
    except:
        stop_err("Unable to open input Interval file")
    
def stop_err(msg):
    sys.stderr.write(msg)
    sys.exit()

def reverse_complement(text):
    DNA_COMP = string.maketrans( "ACGTacgt", "TGCAtgca" )
    comp = [ch for ch in text.translate(DNA_COMP)]
    comp.reverse()
    return "".join(comp)

def get_unique_elems(elems):
    seen=set()
    return[x for x in elems if x not in seen and not seen.add(x)]

def get_binned_lists(uniqlist, binsize):
    binnedlist=[]
    uniqlist.sort()
    start = int(uniqlist[0])
    bin_ind=0
    l_ind=0
    binnedlist.append([])
    while l_ind < len(uniqlist):
        elem = int(uniqlist[l_ind])
        if elem in range(start,start+binsize):
            binnedlist[bin_ind].append(elem)
        else:
            start += binsize
            bin_ind += 1
            binnedlist.append([])
            binnedlist[bin_ind].append(elem)
        l_ind += 1
    return binnedlist

def fetch_weight(H,C,t):
    if (H-(C-H)) < t:
        return 2.0
    else:
        return 1.0

def mutabilityEstimator(repeats1,repeats2,thresholds):
    mut_num = 0.0    #Mutability Numerator
    mut_den = 0.0    #Mutability denominator
    for ind,H in enumerate(repeats1):
        C = repeats2[ind]
        t = thresholds[ind]
        w = fetch_weight(H,C,t)
        mut_num += ((H-C)*(H-C)*w)
        mut_den += w
    return [mut_num, mut_den]

def output_writer(blk, blk_lines):
    global winspecies, speciesind
    all_elems_1=[]
    all_elems_2=[]
    all_s_elems_1=[]
    all_s_elems_2=[]
    for bline in blk_lines:
        if not(bline):
            continue
        items = bline.split('\t')
        seq1 = items[1]
        start1 = items[2]
        end1 = items[3]
        seq2 = items[8]
        start2 = items[9]
        end2 = items[10] 
        if p_group_cols[0] == 6:
            items[p_group_cols[0]] = int(items[p_group_cols[0]])
            items[p_group_cols[1]] = int(items[p_group_cols[1]])
        if s_group_cols[0] == 6:
            items[s_group_cols[0]] = int(items[s_group_cols[0]])
            items[s_group_cols[1]] = int(items[s_group_cols[1]])
        all_elems_1.append(items[p_group_cols[0]])    #primary col elements for species 1
        all_elems_2.append(items[p_group_cols[1]])    #primary col elements for species 2
        if s_group_cols[0] != -1:    #sub-group is not None
            all_s_elems_1.append(items[s_group_cols[0]])    #secondary col elements for species 1
            all_s_elems_2.append(items[s_group_cols[1]])    #secondary col elements for species 2
    uniq_elems_1 = get_unique_elems(all_elems_1)
    uniq_elems_2 = get_unique_elems(all_elems_2)
    if s_group_cols[0] != -1:
        uniq_s_elems_1 = get_unique_elems(all_s_elems_1)
        uniq_s_elems_2 = get_unique_elems(all_s_elems_2)
    mut1={}
    mut2={}
    count1 = {}
    count2 = {}
    """
    if p_group_cols[0] == 7:    #i.e. the option chosen is group-by unit(AG, GTC, etc)
        uniq_elems_1 = get_unique_units(j.sort(lambda x, y: len(x)-len(y)))
    """
    if p_group_cols[0] == 6:    #i.e. the option chosen is group-by repeat number.
        uniq_elems_1 = get_binned_lists(uniq_elems_1,p_bin_size)
        uniq_elems_2 = get_binned_lists(uniq_elems_2,p_bin_size)
        
    if s_group_cols[0] == 6:    #i.e. the option chosen is subgroup-by repeat number.
        uniq_s_elems_1 = get_binned_lists(uniq_s_elems_1,s_bin_size)
        uniq_s_elems_2 = get_binned_lists(uniq_s_elems_2,s_bin_size)

    for pitem1 in uniq_elems_1:
        #repeats1 = []
        #repeats2 = []
        thresholds = []
        if s_group_cols[0] != -1:    #Sub-group by feature is not None
            for sitem1 in uniq_s_elems_1:
                repeats1 = []
                repeats2 = []
                if type(sitem1) == type(''):
                    sitem1 = sitem1.strip()
                for bline in blk_lines:
                    belems = bline.split('\t')
                    if type(pitem1) == list:
                        if p_group_cols[0] == 6:
                            belems[p_group_cols[0]] = int(belems[p_group_cols[0]])
                        if belems[p_group_cols[0]] in pitem1:
                            if belems[s_group_cols[0]]==sitem1:
                                repeats1.append(int(belems[6]))
                                repeats2.append(int(belems[13]))
                                if belems[4] == 'mononucleotide':
                                    thresholds.append(mono_threshold)
                                else:
                                    thresholds.append(non_mono_threshold)
                                mut1[str(pitem1)+'\t'+str(sitem1)]=mutabilityEstimator(repeats1,repeats2,thresholds)
                                if region == 'align':
                                    count1[str(pitem1)+'\t'+str(sitem1)]=min(sum(repeats1),sum(repeats2))
                                else:    
                                    if winspecies == 1:
                                        count1["%s\t%s" %(pitem1,sitem1)]=sum(repeats1)
                                    elif winspecies == 2:
                                        count1["%s\t%s" %(pitem1,sitem1)]=sum(repeats2)
                    else:
                        if type(sitem1) == list:
                            if s_group_cols[0] == 6:
                                belems[s_group_cols[0]] = int(belems[s_group_cols[0]])
                            if belems[p_group_cols[0]]==pitem1 and belems[s_group_cols[0]] in sitem1:
                                repeats1.append(int(belems[6]))
                                repeats2.append(int(belems[13]))
                                if belems[4] == 'mononucleotide':
                                    thresholds.append(mono_threshold)
                                else:
                                    thresholds.append(non_mono_threshold)
                                mut1["%s\t%s" %(pitem1,sitem1)]=mutabilityEstimator(repeats1,repeats2,thresholds)
                                if region == 'align':
                                    count1[str(pitem1)+'\t'+str(sitem1)]=min(sum(repeats1),sum(repeats2))
                                else:    
                                    if winspecies == 1:
                                        count1[str(pitem1)+'\t'+str(sitem1)]=sum(repeats1)
                                    elif winspecies == 2:
                                        count1[str(pitem1)+'\t'+str(sitem1)]=sum(repeats2)
                        else:
                            if belems[p_group_cols[0]]==pitem1 and belems[s_group_cols[0]]==sitem1:
                                repeats1.append(int(belems[6]))
                                repeats2.append(int(belems[13]))
                                if belems[4] == 'mononucleotide':
                                    thresholds.append(mono_threshold)
                                else:
                                    thresholds.append(non_mono_threshold)
                                mut1["%s\t%s" %(pitem1,sitem1)]=mutabilityEstimator(repeats1,repeats2,thresholds)
                                if region == 'align':
                                    count1[str(pitem1)+'\t'+str(sitem1)]=min(sum(repeats1),sum(repeats2))
                                else:    
                                    if winspecies == 1:
                                        count1["%s\t%s" %(pitem1,sitem1)]=sum(repeats1)
                                    elif winspecies == 2:
                                        count1["%s\t%s" %(pitem1,sitem1)]=sum(repeats2)
        else:   #Sub-group by feature is None
            for bline in blk_lines:
                belems = bline.split('\t')
                if type(pitem1) == list:
                    #print >>sys.stderr, "item: " + str(item1)
                    if p_group_cols[0] == 6:
                        belems[p_group_cols[0]] = int(belems[p_group_cols[0]])
                    if belems[p_group_cols[0]] in pitem1:
                        repeats1.append(int(belems[6]))
                        repeats2.append(int(belems[13]))
                        if belems[4] == 'mononucleotide':
                            thresholds.append(mono_threshold)
                        else:
                            thresholds.append(non_mono_threshold)
                else:
                    if belems[p_group_cols[0]]==pitem1:
                        repeats1.append(int(belems[6]))
                        repeats2.append(int(belems[13]))
                        if belems[4] == 'mononucleotide':
                            thresholds.append(mono_threshold)
                        else:
                            thresholds.append(non_mono_threshold)
            mut1["%s" %(pitem1)]=mutabilityEstimator(repeats1,repeats2,thresholds)
            if region == 'align':
                count1["%s" %(pitem1)]=min(sum(repeats1),sum(repeats2))
            else:            
                if winspecies == 1:
                    count1[str(pitem1)]=sum(repeats1)
                elif winspecies == 2:
                    count1[str(pitem1)]=sum(repeats2)
                
    for pitem2 in uniq_elems_2:
        #repeats1 = []
        #repeats2 = []
        thresholds = []
        if s_group_cols[0] != -1:    #Sub-group by feature is not None
            for sitem2 in uniq_s_elems_2:
                repeats1 = []
                repeats2 = []
                if type(sitem2)==type(''):
                    sitem2 = sitem2.strip()
                for bline in blk_lines:
                    belems = bline.split('\t')
                    if type(pitem2) == list:
                        if p_group_cols[0] == 6:
                            belems[p_group_cols[1]] = int(belems[p_group_cols[1]])
                        if belems[p_group_cols[1]] in pitem2 and belems[s_group_cols[1]]==sitem2:
                            repeats2.append(int(belems[13]))
                            repeats1.append(int(belems[6]))
                            if belems[4] == 'mononucleotide':
                                thresholds.append(mono_threshold)
                            else:
                                thresholds.append(non_mono_threshold)
                            mut2["%s\t%s" %(pitem2,sitem2)]=mutabilityEstimator(repeats2,repeats1,thresholds)
                            #count2[str(pitem2)+'\t'+str(sitem2)]=len(repeats2)
                            if region == 'align':
                                count2["%s\t%s" %(pitem2,sitem2)]=min(sum(repeats1),sum(repeats2))
                            else: 
                                if winspecies == 1:
                                    count2["%s\t%s" %(pitem2,sitem2)]=len(repeats2)
                                elif winspecies == 2:
                                    count2["%s\t%s" %(pitem2,sitem2)]=len(repeats1)
                    else:
                        if type(sitem2) == list:
                            if s_group_cols[0] == 6:
                                belems[s_group_cols[1]] = int(belems[s_group_cols[1]])
                            if belems[p_group_cols[1]]==pitem2 and belems[s_group_cols[1]] in sitem2:
                                repeats2.append(int(belems[13]))
                                repeats1.append(int(belems[6]))
                                if belems[4] == 'mononucleotide':
                                    thresholds.append(mono_threshold)
                                else:
                                    thresholds.append(non_mono_threshold)
                                mut2["%s\t%s" %(pitem2,sitem2)]=mutabilityEstimator(repeats2,repeats1,thresholds)
                                if region == 'align':
                                    count2["%s\t%s" %(pitem2,sitem2)]=min(sum(repeats1),sum(repeats2))
                                else: 
                                    if winspecies == 1:
                                        count2["%s\t%s" %(pitem2,sitem2)]=len(repeats2)
                                    elif winspecies == 2:
                                        count2["%s\t%s" %(pitem2,sitem2)]=len(repeats1)
                        else:
                            if belems[p_group_cols[1]]==pitem2 and belems[s_group_cols[1]]==sitem2:
                                repeats1.append(int(belems[13]))
                                repeats2.append(int(belems[6]))
                                if belems[4] == 'mononucleotide':
                                    thresholds.append(mono_threshold)
                                else:
                                    thresholds.append(non_mono_threshold)
                                mut2["%s\t%s" %(pitem2,sitem2)]=mutabilityEstimator(repeats2,repeats1,thresholds)
                                if region == 'align':
                                    count2["%s\t%s" %(pitem2,sitem2)]=min(sum(repeats1),sum(repeats2))
                                else: 
                                    if winspecies == 1:
                                        count2["%s\t%s" %(pitem2,sitem2)]=len(repeats2)
                                    elif winspecies == 2:
                                        count2["%s\t%s" %(pitem2,sitem2)]=len(repeats1)
        else:   #Sub-group by feature is None
            for bline in blk_lines:
                belems = bline.split('\t')
                if type(pitem2) == list:
                    if p_group_cols[0] == 6:
                        belems[p_group_cols[1]] = int(belems[p_group_cols[1]])
                    if belems[p_group_cols[1]] in pitem2:
                        repeats2.append(int(belems[13]))
                        repeats1.append(int(belems[6]))
                        if belems[4] == 'mononucleotide':
                            thresholds.append(mono_threshold)
                        else:
                            thresholds.append(non_mono_threshold)
                else:
                    if belems[p_group_cols[1]]==pitem2:
                        repeats2.append(int(belems[13]))
                        repeats1.append(int(belems[6]))
                        if belems[4] == 'mononucleotide':
                            thresholds.append(mono_threshold)
                        else:
                            thresholds.append(non_mono_threshold)
            mut2["%s" %(pitem2)]=mutabilityEstimator(repeats2,repeats1,thresholds)
            if region == 'align':
                count2["%s" %(pitem2)]=min(sum(repeats1),sum(repeats2))
            else:
                if winspecies == 1:
                    count2["%s" %(pitem2)]=sum(repeats2)
                elif winspecies == 2:
                    count2["%s" %(pitem2)]=sum(repeats1)
    for key in mut1.keys():
        if key in mut2.keys():
            mut = (mut1[key][0]+mut2[key][0])/(mut1[key][1]+mut2[key][1])
            count = count1[key]
            del mut2[key]
        else:
            unit_found = False
            if p_group_cols[0] == 7 or s_group_cols[0] == 7: #if it is Repeat Unit (AG, GCT etc.) check for reverse-complements too
                if p_group_cols[0] == 7:
                    this,other = 0,1
                else:
                    this,other = 1,0
                groups1 = key.split('\t')
                mutn = mut1[key][0]
                mutd = mut1[key][1]
                count = 0
                for key2 in mut2.keys():
                    groups2 = key2.split('\t')
                    if groups1[other] == groups2[other]:
                        if groups1[this] in groups2[this]*2 or reverse_complement(groups1[this]) in groups2[this]*2:
                            #mut = (mut1[key][0]+mut2[key2][0])/(mut1[key][1]+mut2[key2][1])
                            mutn += mut2[key2][0]
                            mutd += mut2[key2][1]
                            count += int(count2[key2])
                            unit_found = True
                            del mut2[key2]
                            #break
            if unit_found:
                mut = mutn/mutd
            else:
                mut = mut1[key][0]/mut1[key][1]
                count = count1[key]
        mut = "%.2e" %(mut/num_generations)
        if region == 'align':
            print >>fout, str(blk) + '\t'+seq1 + '\t' + seq2 + '\t' +key.strip()+ '\t'+str(mut) + '\t'+ str(count)
        elif region == 'win':
            fout.write("%s\t%s\t%s\t%s\n" %(blk,key.strip(),mut,count))
            fout.flush()
            
    #catch any remaining repeats, for instance if the orthologous position contained different repeat units
    for remaining_key in mut2.keys():
        mut = mut2[remaining_key][0]/mut2[remaining_key][1]
        mut = "%.2e" %(mut/num_generations)
        count = count2[remaining_key]
        if region == 'align':
            print >>fout, str(blk) + '\t'+seq1 + '\t'+seq2 + '\t'+remaining_key.strip()+ '\t'+str(mut)+ '\t'+ str(count)
        elif region == 'win':
            fout.write("%s\t%s\t%s\t%s\n" %(blk,remaining_key.strip(),mut,count))
            fout.flush()
            #print >>fout, blk + '\t'+remaining_key.strip()+ '\t'+str(mut)+ '\t'+ str(count)

def counter(node, start, end, report_func):
    if start <= node.start < end and start < node.end <= end:
        report_func(node) 
        if node.right:
            counter(node.right, start, end, report_func)
        if node.left:
            counter(node.left, start, end, report_func)
    elif node.start < start and node.right:
        counter(node.right, start, end, report_func)
    elif node.start >= end and node.left and node.left.maxend > start:
        counter(node.left, start, end, report_func)
            
        
def main():
    infile = sys.argv[1]
    
    for i, line in enumerate( file ( infile )):
        line = line.rstrip('\r\n')
        if len( line )>0 and not line.startswith( '#' ):
            elems = line.split( '\t' )
            break
        if i == 30:
            break # Hopefully we'll never get here...
    
    if len( elems ) != 15:
        stop_err( "This tool only works on tabular data output by 'Extract Orthologous Microsatellites from pair-wise alignments' tool. The data in your input dataset is either missing or not formatted properly." )
    global winspecies, speciesind
    if region == 'win':
        if dbkey_i in elems[1]:
            winspecies = 1
            speciesind = 1 
        elif dbkey_i in elems[8]:
            winspecies = 2
            speciesind = 8
        else:
            stop_err("The species build corresponding to your interval file is not present in the Microsatellite file.") 
        
    fin = open(infile, 'r')
    skipped = 0
    blk=0
    win=0
    linestr=""
    
    if region == 'win':
        
        msats = NiceReaderWrapper( fileinput.FileInput( infile ),
                                chrom_col = speciesind,
                                start_col = speciesind+1,
                                end_col = speciesind+2,
                                strand_col = -1,
                                fix_strand = True)
        msatTree = quicksect.IntervalTree()
        for item in msats:
            if type( item ) is GenomicInterval:
                msatTree.insert( item, msats.linenum, item.fields )
        
        for iline in fint:
            try:
                iline = iline.rstrip('\r\n')
                if not(iline) or iline == "":
                    continue
                ielems = iline.strip("\r\n").split('\t')
                ichr = ielems[chr_col_i]
                istart = int(ielems[start_col_i])
                iend = int(ielems[end_col_i])
                isrc = "%s.%s" %(dbkey_i,ichr)
                if isrc not in msatTree.chroms:
                    continue
                result = []
                root = msatTree.chroms[isrc]    #root node for the chrom
                counter(root, istart, iend, lambda node: result.append( node ))
                if not(result):
                    continue
                tmpfile1 = tempfile.NamedTemporaryFile('wb+')
                for node in result:
                    tmpfile1.write("%s\n" % "\t".join( node.other ))
                
                tmpfile1.seek(0)
                output_writer(iline, tmpfile1.readlines())
            except:
                skipped+=1
        if skipped:
            print "Skipped %d intervals as invalid." %(skipped)
    elif region == 'align':
        if s_group_cols[0] != -1:
            print >>fout, "#Window\tSpecies_1\tSpecies_2\tGroupby_Feature\tSubGroupby_Feature\tMutability\tCount"
        else:
            print >>fout, "#Window\tSpecies_1\tWindow_Start\tWindow_End\tSpecies_2\tGroupby_Feature\tMutability\tCount"
        prev_bnum = -1
        try:
            for line in fin:
                line = line.strip("\r\n")
                if not(line) or line == "":
                    continue
                elems = line.split('\t')
                try:
                    assert int(elems[0])
                    assert len(elems) == 15
                except:
                    continue
                new_bnum = int(elems[0])
                if new_bnum != prev_bnum:
                    if prev_bnum != -1:
                        output_writer(prev_bnum, linestr.strip().replace('\r','\n').split('\n'))
                    linestr = line + "\n"
                else:
                    linestr += line
                    linestr += "\n"
                prev_bnum = new_bnum
            output_writer(prev_bnum, linestr.strip().replace('\r','\n').split('\n'))
        except Exception, ea:
            print >>sys.stderr, ea
            skipped += 1
        if skipped:
            print "Skipped %d lines as invalid." %(skipped)
if __name__ == "__main__":
    main()