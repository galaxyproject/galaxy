"""
Converts any type of FASTQ file to Sanger type  and makes small adjustments if necessary.

usage: %prog [options]
   -i, --input=i: Input FASTQ candidate file
   -r, --origType=r: Original type
   -a, --allOrNot=a: Whether or not to check all blocks
   -b, --blocks=b: Number of blocks to check
   -o, --output=o: Output file

usage: %prog input_file oroutput_file
"""

import math, sys
from galaxy import eggs
import pkg_resources; pkg_resources.require( "bx-python" )
from bx.cookbook import doc_optparse

def stop_err( msg ):
    sys.stderr.write( "%s\n" % msg )
    sys.exit()
    
def all_bases_valid(seq):
    """Confirm that the sequence contains only bases"""
    valid_bases = ['a', 'A', 'c', 'C', 'g', 'G', 't', 'T', 'N']
    for base in seq:
        if base not in valid_bases:
            return False
    return True

def __main__():
    #Parse Command Line
    options, args = doc_optparse.parse( __doc__ )
    orig_type = options.origType
    if orig_type == 'sanger' and options.allOrNot == 'not':
        max_blocks = int(options.blocks)
    else:
        max_blocks = -1
    fin = file(options.input, 'r')
    fout = file(options.output, 'w')
    range_min = 1000
    range_max = -5
    block_num = 0
    bad_blocks = 0
    base_len = -1
    line_count = 0
    lines = []
    line = fin.readline()
    while line:
        if line.strip() and max_blocks >= 0 and block_num > 0 and orig_type == 'sanger' and block_num >= max_blocks:
            fout.write(line)
            if line_count % 4 == 0:
                block_num += 1
            line_count += 1
        elif line.strip():
            # the line that starts a block, with a name
            if line_count % 4 == 0 and line.startswith('@'):
                lines.append(line)
            else:
                # if we expect a sequence of bases
                if line_count % 4 == 1 and all_bases_valid(line.strip()):
                    lines.append(line)
                    base_len = len(line.strip())
                # if we expect the second name line
                elif line_count % 4 == 2 and line.startswith('+'):
                    lines.append(line)
                # if we expect a sequence of qualities and it's the expected length
                elif line_count % 4 == 3:
                    split_line = line.strip().split()
                    # decimal qualities
                    if len(split_line) == base_len:
                        # convert
                        phred_list = []
                        for ch in split_line:
                            int_ch = int(ch)
                            if int_ch < range_min:
                                range_min = int_ch
                            if int_ch > range_max:
                                range_max = int_ch
                            if int_ch >= 0 and int_ch <= 93:
                                phred_list.append(chr(int_ch + 33))
                        # make sure we haven't lost any quality values
                        if len(phred_list) == base_len:
                            # print first three lines
                            for l in lines:
                                fout.write(l)
                            # print converted quality line
                            fout.write(''.join(phred_list))
                            # reset
                            lines = []
                            base_len = -1
                        # abort if so
                        else:
                            bad_blocks += 1
                            lines = []
                            base_len = -1
                    # ascii qualities
                    elif len(split_line[0]) == base_len:
                        qualities = []
                        # print converted quality line
                        if orig_type == 'illumina':
                            for c in line.strip():
                                if ord(c) - 64 < range_min:
                                    range_min = ord(c) - 64
                                if ord(c) - 64 > range_max:
                                    range_max = ord(c) - 64
                                if ord(c) < 64 or ord(c) > 126:
                                    bad_blocks += 1
                                    base_len = -1
                                    lines = []
                                    break
                                else:
                                    qualities.append( chr( ord(c) - 31 ) )
                            quals = ''.join(qualities)
                        elif orig_type == 'solexa':
                            for c in line.strip():
                                if ord(c) - 64 < range_min:
                                    range_min = ord(c) - 64
                                if ord(c) - 64 > range_max:
                                    range_max = ord(c) - 64
                                if ord(c) < 59 or ord(c) > 126:
                                    bad_blocks += 1
                                    base_len = -1
                                    lines = []
                                    break
                                else:
                                    p = 10.0**( ( ord(c) - 64 ) / -10.0 ) / ( 1 + 10.0**( ( ord(c) - 64 ) / -10.0 ) )
                                    qualities.append( chr( int( -10.0*math.log10( p ) ) + 33 ) )
                            quals = ''.join(qualities)
                        else:  # 'sanger'
                            for c in line.strip():
                                if ord(c) - 33 < range_min:
                                    range_min = ord(c) - 33
                                if ord(c) - 33 > range_max:
                                    range_max = ord(c) - 33
                                if ord(c) < 33 or ord(c) > 126:
                                    bad_blocks += 1
                                    base_len = -1
                                    lines = []
                                    break
                                else:
                                    qualities.append(c)
                            quals = ''.join(qualities)
                        # make sure we don't have bad qualities
                        if len(quals) == base_len:
                            # print first three lines
                            for l in lines:
                                fout.write(l)
                            # print out quality line
                            fout.write(quals+'\n')
                        # reset
                        lines = []
                        base_len = -1
                    else:
                        bad_blocks += 1
                        base_len = -1
                        lines = []
                    # mark the successful end of a block
                    block_num += 1
            line_count += 1
        line = fin.readline()
    fout.close()
    fin.close()
    if range_min != 1000 and range_min != -5:
        outmsg = 'The range of quality values found were: %s to %s' % (range_min, range_max)
    else:
        outmsg = ''
    if bad_blocks > 0:
        outmsg += '\nThere were %s bad blocks skipped' % (bad_blocks)
    sys.stdout.write(outmsg)

if __name__=="__main__": __main__() 