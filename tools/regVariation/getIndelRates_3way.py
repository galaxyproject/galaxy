#!/usr/bin/env python
#Guruprasad Ananda

from galaxy import eggs
import pkg_resources
pkg_resources.require( "bx-python" )

import sys, os, tempfile
import traceback
import fileinput
from warnings import warn

from galaxy.tools.util.galaxyops import *
from bx.intervals.io import *

from bx.intervals.operations import quicksect

def stop_err(msg):
    sys.stderr.write(msg)
    sys.exit()
    
def counter(node, start, end, sort_col):
    global full, blk_len, blk_list
    if node.start < start:
        if node.right:
            counter(node.right, start, end, sort_col)
    elif start <= node.start <= end and start <= node.end <= end:
        full += 1
        if node.other[0] not in blk_list:
            blk_list.append(node.other[0])
            blk_len += int(node.other[sort_col+2])
        if node.left and node.left.maxend > start:
            counter(node.left, start, end, sort_col)
        if node.right: 
            counter(node.right, start, end, sort_col)
    elif node.start > end:
        if node.left: 
            counter(node.left, start, end, sort_col)
            

infile = sys.argv[1]  
fout = open(sys.argv[2],'w')
int_file = sys.argv[3]
if int_file != "None": #User has specified an interval file
    try:
        fint = open(int_file, 'r')
        dbkey_i = sys.argv[4]
        chr_col_i, start_col_i, end_col_i, strand_col_i = parse_cols_arg( sys.argv[5] )
    except:
        stop_err("Unable to open input Interval file")
        
def main():

    for i, line in enumerate( file ( infile )):
        line = line.rstrip('\r\n')
        if len( line )>0 and not line.startswith( '#' ):
            elems = line.split( '\t' )
            break
        if i == 30:
            break # Hopefully we'll never get here...
        
    if len( elems ) != 18:
        stop_err( "This tool only works on tabular data output by 'Fetch Indels from 3-way alignments' tool. The data in your input dataset is either missing or not formatted properly." )
    
    for i, line in enumerate( file ( infile )):
        line = line.rstrip('\r\n')
        elems = line.split('\t')
        try:
            assert int(elems[0])
            assert len(elems) == 18
            if int_file != "None":
                if dbkey_i not in elems[3] and  dbkey_i not in elems[8] and dbkey_i not in elems[13]:
                    stop_err("The species build corresponding to your interval file is not present in the Indel file.") 
                if dbkey_i in elems[3]:
                    sort_col = 4
                elif dbkey_i in elems[8]:
                    sort_col = 9
                elif dbkey_i in elems[13]:
                    sort_col = 14
            else:
                species = []
                species.append( elems[3].split('.')[0] )
                species.append( elems[8].split('.')[0] )
                species.append( elems[13].split('.')[0] )
                sort_col = 0    #Based on block numbers
            break
        except:
            continue
        
        
    fin = open(infile, 'r')
    skipped = 0
    
    if int_file == "None":
        sorted_infile = tempfile.NamedTemporaryFile()
        cmdline = "sort -n -k"+str(1)+" -o "+sorted_infile.name+" "+infile
        try:
            os.system(cmdline)
        except:
            stop_err("Encountered error while sorting the input file.")
        print >>fout, "#Block\t%s_InsRate\t%s_InsRate\t%s_InsRate\t%s_DelRate\t%s_DelRate\t%s_DelRate" %(species[0],species[1],species[2],species[0],species[1],species[2])
        prev_bnum = -1
        sorted_infile.seek(0)
        for line in sorted_infile.readlines():
            line = line.rstrip('\r\n')
            elems = line.split('\t')
            try:
                assert int(elems[0])
                assert len(elems) == 18
                new_bnum = int(elems[0])
                if new_bnum != prev_bnum:
                    if prev_bnum != -1:
                        irate = []
                        drate = []
                        for i,elem in enumerate(inserts):
                            try:
                                irate.append(str("%.2e" %(inserts[i]/blen[i])))
                            except:
                                irate.append('0')
                            try:
                                drate.append(str("%.2e" %(deletes[i]/blen[i])))
                            except:
                                drate.append('0')
                        print >>fout, "%s\t%s\t%s" %(prev_bnum, '\t'.join(irate) , '\t'.join(drate))
                    inserts = [0.0, 0.0, 0.0]
                    deletes = [0.0, 0.0, 0.0]
                    blen = []
                    blen.append( int(elems[6]) )
                    blen.append( int(elems[11]) )
                    blen.append( int(elems[16]) )
                line_sp = elems[1].split('.')[0]
                sp_ind = species.index(line_sp)
                if elems[1].endswith('insert'):
                    inserts[sp_ind] += 1
                elif elems[1].endswith('delete'):
                    deletes[sp_ind] += 1
                prev_bnum = new_bnum 
            except Exception, ei:
                #print >>sys.stderr, ei
                continue
        irate = []
        drate = []
        for i,elem in enumerate(inserts):
            try:
                irate.append(str("%.2e" %(inserts[i]/blen[i])))
            except:
                irate.append('0')
            try:
                drate.append(str("%.2e" %(deletes[i]/blen[i])))
            except:
                drate.append('0')
        print >>fout, "%s\t%s\t%s" %(prev_bnum, '\t'.join(irate) , '\t'.join(drate))
        sys.exit()
    
    
    inf = open(infile, 'r')
    start_met = False
    end_met = False
    sp_file = tempfile.NamedTemporaryFile()
    for n, line in enumerate(inf):
        line = line.rstrip('\r\n')
        elems = line.split('\t')
        try:
            assert int(elems[0])
            assert len(elems) == 18
            if dbkey_i not in elems[1]: 
                if not(start_met):   
                    continue
                else:
                    sp_end = n
                    break
            else:
                print >>sp_file, line
                if not(start_met):
                    start_met = True
                    sp_start = n
        except:
            continue
    
    try:
        assert sp_end
    except:
        sp_end = n+1
    
    sp_file.seek(0)
    win = NiceReaderWrapper( fileinput.FileInput( int_file ),
                                chrom_col=chr_col_i,
                                start_col=start_col_i,
                                end_col=end_col_i,
                                strand_col=strand_col_i,
                                fix_strand=True)
    
    indel = NiceReaderWrapper( fileinput.FileInput( sp_file.name ),
                                chrom_col=1,
                                start_col=sort_col,
                                end_col=sort_col+1,
                                strand_col=-1,
                                fix_strand=True)
    
    indelTree = quicksect.IntervalTree()
    for item in indel:
        if type( item ) is GenomicInterval:
            indelTree.insert( item, indel.linenum, item.fields )
    result=[]
    
    global full, blk_len, blk_list
    for interval in win:
        if type( interval ) is Header:
            pass
        if type( interval ) is Comment:
            pass
        elif type( interval ) == GenomicInterval:
            chrom = interval.chrom
            start = int(interval.start)
            end = int(interval.end)
            if start > end: 
                warn( "Interval start after end!" )
            ins_chr = "%s.%s_insert" %(dbkey_i,chrom)
            del_chr = "%s.%s_delete" %(dbkey_i,chrom)
            irate = 0
            drate = 0
            if ins_chr not in indelTree.chroms and del_chr not in indelTree.chroms:
                pass    
            else:
                if ins_chr in indelTree.chroms:
                    full = 0.0
                    blk_len = 0
                    blk_list = []
                    root = indelTree.chroms[ins_chr]    #root node for the chrom insertion tree
                    counter(root, start, end, sort_col)
                    if blk_len:
                        irate = full/blk_len
                
                if del_chr in indelTree.chroms:
                    full = 0.0
                    blk_len = 0
                    blk_list = []
                    root = indelTree.chroms[del_chr]    #root node for the chrom insertion tree
                    counter(root, start, end, sort_col)
                    if blk_len:
                        drate = full/blk_len
                
            interval.fields.append(str("%.2e" %irate))
            interval.fields.append(str("%.2e" %drate))
            print >>fout, "\t".join(interval.fields)
            fout.flush()

if __name__ == "__main__":
    main()    