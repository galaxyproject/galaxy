#!/usr/bin/env python

import os, sys

assert sys.version_info[:2] >= ( 2, 4 )

def stop_err( msg ):
    sys.stderr.write( "%s\n" % msg )
    sys.exit()

def reverse_complement(s):
    complement_dna = {"A":"T", "T":"A", "C":"G", "G":"C", "a":"t", "t":"a", "c":"g", "g":"c", "N":"N", "n":"n" , ".":"."}
    reversed_s = []
    for i in s:
        reversed_s.append(complement_dna[i])
    reversed_s.reverse()
    return "".join(reversed_s)

def __main__():
    nuc_index = {'a':0,'t':1,'c':2,'g':3}
    diff_hash = {}    # key = (chrom, index)
    infile = sys.argv[1]
    outfile = sys.argv[2]
    invalid_lines = 0
    invalid_chars = 0
    data_id = ''
    data_seq = ''

    for i, line in enumerate( open( infile ) ):
        line = line.rstrip( '\r\n' )
        if not line or line.startswith( '#' ):
            continue
        fields = line.split()
        if len(fields) != 23:    # standard number of pslx columns
            invalid_lines += 1
            continue
        if not fields[0].isdigit():
            invalid_lines += 1
            continue
        read_id = fields[9]
        chrom = fields[13]
        try:
            block_count = int(fields[17])
        except:
            invalid_lines += 1
            continue
        block_size = fields[18].split(',')
        read_start = fields[19].split(',')
        chrom_start = fields[20].split(',')
        read_seq = fields[21].split(',')
        chrom_seq = fields[22].split(',')

        for j in range(block_count):
            try:
                this_block_size = int(block_size[j])
                this_read_start = int(read_start[j])
                this_chrom_start = int(chrom_start[j])
            except:
                invalid_lines += 1
                break
            this_read_seq = read_seq[j]
            this_chrom_seq = chrom_seq[j]
            
            if not this_read_seq.isalpha():
                continue
            if not this_chrom_seq.isalpha():
                continue
            
            # brut force to check coverage                
            for k in range(this_block_size):
                cur_index = this_chrom_start+k
                sub_a = this_read_seq[k:(k+1)].lower()
                sub_b = this_chrom_seq[k:(k+1)].lower()
                if not diff_hash.has_key((chrom, cur_index)):
                    try:
                        diff_hash[(chrom, cur_index)] = [0,0,0,0,sub_b.upper()]    # a, t, c, g, ref. nuc.
                    except Exception, e:
                        stop_err( str( e ) )
                if sub_a in ['a','t','c','g']:
                    diff_hash[(chrom, cur_index)][nuc_index[(sub_a)]] += 1
                else:
                    invalid_chars += 1
                        
    outputfh = open(outfile, 'w')
    outputfh.write( "##title\tlocation\tref.\tcov.\tA\tT\tC\tG\n" )
    keys = diff_hash.keys()
    keys.sort()
    for i in keys:
        (chrom, location) = i
        sum = diff_hash[ (i) ][ 0 ] + diff_hash[ ( i ) ][ 1 ] + diff_hash[ ( i ) ][ 2 ] + diff_hash[ ( i ) ][ 3 ]    # did not include N's
        if sum == 0:
            continue
        ratio_A = diff_hash[ ( i ) ][ 0 ] * 100.0 / sum
        ratio_T = diff_hash[ ( i ) ][ 1 ] * 100.0 / sum
        ratio_C = diff_hash[ ( i ) ][ 2 ] * 100.0 / sum
        ratio_G = diff_hash[ ( i ) ][ 3 ] * 100.0 / sum
        (title_head, title_tail) = os.path.split(chrom)
        result = "%s\t%s\t%s\t%d\tA(%0.0f)\tT(%0.0f)\tC(%0.0f)\tG(%0.0f)\n" % ( title_tail, location, diff_hash[(i)][4], sum, ratio_A, ratio_T, ratio_C, ratio_G ) 
        outputfh.write(result)
    outputfh.close()

    if invalid_lines:
        print 'Skipped %d invalid lines. ' % ( invalid_lines )
    if invalid_chars:
        print 'Skipped %d invalid characters in the alignment. ' % (invalid_chars)
        
if __name__ == '__main__': __main__()