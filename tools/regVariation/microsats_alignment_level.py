 #!/usr/bin/env python
#Guruprasad Ananda
"""
Uses SPUTNIK to fetch microsatellites and extracts orthologous repeats from the sputnik output.
"""
from galaxy import eggs
import sys, os, tempfile, string, math, re

def reverse_complement(text):
    DNA_COMP = string.maketrans( "ACGTacgt", "TGCAtgca" )
    comp = [ch for ch in text.translate(DNA_COMP)]
    comp.reverse()
    return "".join(comp)

def main():
    if len(sys.argv) != 8:
        print >>sys.stderr, "Insufficient number of arguments."
        sys.exit()
    
    infile = open(sys.argv[1],'r')
    separation = int(sys.argv[2])
    outfile = sys.argv[3]
    align_type = sys.argv[4]
    if align_type == "2way":
        align_type_len = 2
    elif align_type == "3way":
        align_type_len = 3
    mono_threshold = int(sys.argv[5])
    non_mono_threshold = int(sys.argv[6])
    allow_different_units = int(sys.argv[7])
    
    print "Min distance = %d bp; Min threshold for mono repeats = %d; Min threshold for non-mono repeats = %d; Allow different motifs = %s" %(separation, mono_threshold, non_mono_threshold, allow_different_units==1)
    try:
        fout = open(outfile, "w")
        print >>fout, "#Block\tSeq1_Name\tSeq1_Start\tSeq1_End\tSeq1_Type\tSeq1_Length\tSeq1_RepeatNumber\tSeq1_Unit\tSeq2_Name\tSeq2_Start\tSeq2_End\tSeq2_Type\tSeq2_Length\tSeq2_RepeatNumber\tSeq2_Unit"
        #sputnik_cmd = os.path.join(os.path.split(sys.argv[0])[0], "sputnik")
        sputnik_cmd = "sputnik"
        input = infile.read()
        skipped = 0
        block_num = 0
        input = input.replace('\r','\n')
        for block in input.split('\n\n'):
            block_num += 1
            tmpin = tempfile.NamedTemporaryFile()
            tmpout = tempfile.NamedTemporaryFile()
            tmpin.write(block.strip())
            blk = tmpin.read()
            cmdline = sputnik_cmd + " " + tmpin.name + "  > /dev/null 2>&1 >> " + tmpout.name
            try:
                os.system(cmdline)
            except Exception, es:
                continue
            sputnik_out = tmpout.read()
            tmpin.close()
            tmpout.close()
            if sputnik_out != "":
                if len(block.split('>')[1:]) != 2:        #len(sputnik_out.split('>')):
                    skipped += 1
                    continue
                align_block = block.strip().split('>')
                
                lendict = {'mononucleotide':1, 'dinucleotide':2, 'trinucleotide':3, 'tetranucleotide':4, 'pentanucleotide':5, 'hexanucleotide':6}
                blockdict={}
                r=0
                namelist=[]
                for k,sput_block in enumerate(sputnik_out.split('>')[1:]):
                    whole_seq = ''.join(align_block[k+1].split('\n')[1:]).replace('\n','').strip()
                    p = re.compile('\n(\S*nucleotide)')
                    repeats = p.split(sput_block.strip())
                    repeats_count = len(repeats)
                    j = 1
                    name = repeats[0].strip()
                    try:
                        coords = re.search('\d+[-_:]\d+',name).group()
                        coords = coords.replace('_','-').replace(':','-')
                    except Exception, e:
                        coords = '0-0'
                        pass
                    r += 1
                    blockdict[r]={}
                    try:
                        sp_name = name[:name.index('.')]
                        chr_name = name[name.index('.'):name.index('(')]
                        namelist.append(sp_name + chr_name)
                    except:
                        namelist.append(name[:20])
                    while j < repeats_count:
                        try:
                            if repeats[j].strip() not in lendict:
                                j += 2
                                continue
                            
                            if blockdict[r].has_key('types'):
                                blockdict[r]['types'].append(repeats[j].strip())        #type of microsat     
                            else:
                                blockdict[r]['types'] = [repeats[j].strip()]               #type of microsat  
                            
                            sequence = ''.join(align_block[r].split('\n')[1:]).replace('\n','').strip()
                            start = int(repeats[j+1].split('--')[0].split(':')[0].strip())
                            #check to see if there are gaps before the start of the repeat, and change the start accordingly
                            sgaps = 0
                            ch_pos = start - 1
                            while ch_pos >= 0:
                                if whole_seq[ch_pos] == '-':
                                    sgaps += 1
                                else:
                                    break    #break at the 1st non-gap character
                                ch_pos -= 1
                            if blockdict[r].has_key('starts'):
                                blockdict[r]['starts'].append(start+sgaps)        #start co-ords adjusted with alignment co-ords to include GAPS    
                            else:
                                blockdict[r]['starts'] = [start+sgaps]
                            
                            end = int(repeats[j+1].split('--')[0].split(':')[1].strip())
                            #check to see if there are gaps after the end of the repeat, and change the end accordingly
                            egaps = 0
                            for ch in whole_seq[end:]:
                                if ch == '-':
                                    egaps += 1
                                else:
                                    break    #break at the 1st non-gap character
                            if blockdict[r].has_key('ends'):
                                blockdict[r]['ends'].append(end+egaps)        #end co-ords adjusted with alignment co-ords to include GAPS    
                            else:
                                blockdict[r]['ends'] = [end+egaps]
                                
                            repeat_seq = ''.join(repeats[j+1].replace('\r','\n').split('\n')[1:]).strip()       #Repeat Sequence
                            repeat_len = repeats[j+1].split('--')[1].split()[1].strip()
                            gap_count = repeat_seq.count('-')
                            #print repeats[j+1].split('--')[1], len(repeat_seq), repeat_len, gap_count
                            repeat_len = str(int(repeat_len) - gap_count)
                            
                            rel_start = blockdict[r]['starts'][-1]
                            gaps_before_start = whole_seq[:rel_start].count('-')
                            
                            if blockdict[r].has_key('gaps_before_start'):
                                blockdict[r]['gaps_before_start'].append(gaps_before_start)  #lengths  
                            else:
                                blockdict[r]['gaps_before_start'] = [gaps_before_start]       #lengths 
                            
                            whole_seq_start= int(coords.split('-')[0])
                            if blockdict[r].has_key('whole_seq_start'):
                                blockdict[r]['whole_seq_start'].append(whole_seq_start)  #lengths  
                            else:
                                blockdict[r]['whole_seq_start'] = [whole_seq_start]       #lengths 
                                
                            if blockdict[r].has_key('lengths'):
                                blockdict[r]['lengths'].append(repeat_len)  #lengths  
                            else:
                                blockdict[r]['lengths'] = [repeat_len]       #lengths 
                            
                            if blockdict[r].has_key('counts'):
                                blockdict[r]['counts'].append(str(int(repeat_len)/lendict[repeats[j].strip()]))  #Repeat Unit
                            else:
                                blockdict[r]['counts'] = [str(int(repeat_len)/lendict[repeats[j].strip()])]         #Repeat Unit
                            
                            if blockdict[r].has_key('units'):
                                blockdict[r]['units'].append(repeat_seq[:lendict[repeats[j].strip()]])  #Repeat Unit
                            else:
                                blockdict[r]['units'] = [repeat_seq[:lendict[repeats[j].strip()]]]         #Repeat Unit
                            
                        except Exception, eh:
                            pass
                        j+=2
                    #check the co-ords of all repeats corresponding to a sequence and remove adjacent repeats separated by less than the user-specified 'separation'. 
                    delete_index_list = []
                    for ind, item in enumerate(blockdict[r]['ends']):
                        try:
                            if blockdict[r]['starts'][ind+1]-item < separation:
                                if ind not in delete_index_list:
                                    delete_index_list.append(ind)
                                if ind+1 not in delete_index_list:
                                    delete_index_list.append(ind+1)
                        except Exception, ek:
                            pass
                    for index in delete_index_list:    #mark them for deletion
                        try:
                            blockdict[r]['starts'][index] = 'marked'
                            blockdict[r]['ends'][index] = 'marked'
                            blockdict[r]['types'][index] = 'marked'
                            blockdict[r]['gaps_before_start'][index] = 'marked'
                            blockdict[r]['whole_seq_start'][index] = 'marked'
                            blockdict[r]['lengths'][index] = 'marked'
                            blockdict[r]['counts'][index] = 'marked'
                            blockdict[r]['units'][index] = 'marked'
                        except Exception, ej:
                            pass
                    #remove 'marked' elements from all the lists
                    """
                    for key in blockdict[r].keys():
                        for elem in blockdict[r][key]:
                            if elem == 'marked':
                                blockdict[r][key].remove(elem)
                    """
                    #print blockdict    
                
                #make sure that the blockdict has keys for both the species   
                if (1 not in blockdict) or (2 not in blockdict):
                    continue
                
                visited_2 = [0 for x in range(len(blockdict[2]['starts']))]
                for ind1,coord_s1 in enumerate(blockdict[1]['starts']):
                    if coord_s1 == 'marked':
                        continue
                    coord_e1 = blockdict[1]['ends'][ind1]
                    out = []
                    for ind2,coord_s2 in enumerate(blockdict[2]['starts']):
                        if coord_s2 == 'marked':
                            visited_2[ind2] = 1
                            continue
                        coord_e2 = blockdict[2]['ends'][ind2]
                        #skip if the 2 repeats are not of the same type or don't have the same repeating unit.
                        if allow_different_units == 0:
                            if (blockdict[1]['types'][ind1] != blockdict[2]['types'][ind2]):
                                continue
                            else:
                                if (blockdict[1]['units'][ind1] not in blockdict[2]['units'][ind2]*2) and (reverse_complement(blockdict[1]['units'][ind1]) not in blockdict[2]['units'][ind2]*2):
                                    continue
                        #print >>sys.stderr, (reverse_complement(blockdict[1]['units'][ind1]) not in blockdict[2]['units'][ind2]*2)
                        #skip if the repeat number thresholds are not met
                        if blockdict[1]['types'][ind1] == 'mononucleotide':
                            if (int(blockdict[1]['counts'][ind1]) < mono_threshold):
                                continue
                        else:
                            if (int(blockdict[1]['counts'][ind1]) < non_mono_threshold):
                                continue
                        
                        if blockdict[2]['types'][ind2] == 'mononucleotide':
                            if (int(blockdict[2]['counts'][ind2]) < mono_threshold):
                                continue
                        else:
                            if (int(blockdict[2]['counts'][ind2]) < non_mono_threshold):
                                continue
                        #print "s1,e1=%s,%s; s2,e2=%s,%s" %(coord_s1,coord_e1,coord_s2,coord_e2)
                        if (coord_s1 in range(coord_s2,coord_e2)) or (coord_e1 in range(coord_s2,coord_e2)):
                            out.append(str(block_num))
                            out.append(namelist[0])
                            rel_start = blockdict[1]['whole_seq_start'][ind1] + coord_s1 - blockdict[1]['gaps_before_start'][ind1]
                            rel_end = rel_start + int(blockdict[1]['lengths'][ind1]) 
                            out.append(str(rel_start))
                            out.append(str(rel_end))
                            out.append(blockdict[1]['types'][ind1])
                            out.append(blockdict[1]['lengths'][ind1])
                            out.append(blockdict[1]['counts'][ind1])
                            out.append(blockdict[1]['units'][ind1])
                            out.append(namelist[1])
                            rel_start = blockdict[2]['whole_seq_start'][ind2] + coord_s2 - blockdict[2]['gaps_before_start'][ind2]
                            rel_end = rel_start + int(blockdict[2]['lengths'][ind2]) 
                            out.append(str(rel_start))
                            out.append(str(rel_end))
                            out.append(blockdict[2]['types'][ind2])
                            out.append(blockdict[2]['lengths'][ind2])
                            out.append(blockdict[2]['counts'][ind2])
                            out.append(blockdict[2]['units'][ind2])
                            print >>fout, '\t'.join(out)
                            visited_2[ind2] = 1
                            out=[]
                
                if 0 in visited_2:    #there are still some elements in 2nd set which haven't found orthologs yet.
                    for ind2, coord_s2 in enumerate(blockdict[2]['starts']):
                        if coord_s2 == 'marked':
                            continue
                        if visited_2[ind] != 0:
                            continue
                        coord_e2 = blockdict[2]['ends'][ind2]
                        out = []
                        for ind1,coord_s1 in enumerate(blockdict[1]['starts']):
                            if coord_s1 == 'marked':
                                continue
                            coord_e1 = blockdict[1]['ends'][ind1]
                            #skip if the 2 repeats are not of the same type or don't have the same repeating unit.
                            if allow_different_units == 0:
                                if (blockdict[1]['types'][ind1] != blockdict[2]['types'][ind2]):
                                    continue
                                else:
                                    if (blockdict[1]['units'][ind1] not in blockdict[2]['units'][ind2]*2):# and reverse_complement(blockdict[1]['units'][ind1]) not in blockdict[2]['units'][ind2]*2:
                                        continue
                            #skip if the repeat number thresholds are not met
                            if blockdict[1]['types'][ind1] == 'mononucleotide':
                                if (int(blockdict[1]['counts'][ind1]) < mono_threshold):
                                    continue
                            else:
                                if (int(blockdict[1]['counts'][ind1]) < non_mono_threshold):
                                    continue
                            
                            if blockdict[2]['types'][ind2] == 'mononucleotide':
                                if (int(blockdict[2]['counts'][ind2]) < mono_threshold):
                                    continue
                            else:
                                if (int(blockdict[2]['counts'][ind2]) < non_mono_threshold):
                                    continue
                            
                            if (coord_s2 in range(coord_s1,coord_e1)) or (coord_e2 in range(coord_s1,coord_e1)):
                                out.append(str(block_num)) 
                                out.append(namelist[0])
                                rel_start = blockdict[1]['whole_seq_start'][ind1] + coord_s1 - blockdict[1]['gaps_before_start'][ind1]
                                rel_end = rel_start + int(blockdict[1]['lengths'][ind1]) 
                                out.append(str(rel_start))
                                out.append(str(rel_end))
                                out.append(blockdict[1]['types'][ind1])
                                out.append(blockdict[1]['lengths'][ind1])
                                out.append(blockdict[1]['counts'][ind1])
                                out.append(blockdict[1]['units'][ind1])
                                out.append(namelist[1])
                                rel_start = blockdict[2]['whole_seq_start'][ind2] + coord_s2 - blockdict[2]['gaps_before_start'][ind2]
                                rel_end = rel_start + int(blockdict[2]['lengths'][ind2]) 
                                out.append(str(rel_start))
                                out.append(str(rel_end))
                                out.append(blockdict[2]['types'][ind2])
                                out.append(blockdict[2]['lengths'][ind2])
                                out.append(blockdict[2]['counts'][ind2])
                                out.append(blockdict[2]['units'][ind2])
                                print >>fout, '\t'.join(out)
                                visited_2[ind2] = 1
                                out=[]
                            
                    #print >>fout, blockdict
    except Exception, exc:
        print >>sys.stderr, "type(exc),args,exc: %s, %s, %s" %(type(exc), exc.args, exc)

if __name__ == "__main__":
    main()
    
