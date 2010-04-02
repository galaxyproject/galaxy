#!/usr/bin/env python

"""
TODO
1. decrease memory usage
2. multi-fasta fastq file, ex. 454
3. split reads into small chuncks?

SHRiMP wrapper

Inputs: 
1. reference seq 
2. reads

Outputs: 
1. table of 8 columns:
         chrom   ref_loc     read_id     read_loc    ref_nuc     read_nuc    quality     coverage
2. SHRiMP output
         
Parameters:
    -s    Spaced Seed                             (default: 111111011111)
    -n    Seed Matches per Window                 (default: 2)
    -t    Seed Hit Taboo Length                   (default: 4)
    -9    Seed Generation Taboo Length            (default: 0)
    -w    Seed Window Length                      (default: 115.00%)
    -o    Maximum Hits per Read                   (default: 100)
    -r    Maximum Read Length                     (default: 1000)
    -d    Kmer Std. Deviation Limit               (default: -1 [None])

    -m    S-W Match Value                         (default: 100)
    -i    S-W Mismatch Value                      (default: -150)
    -g    S-W Gap Open Penalty (Reference)        (default: -400)
    -q    S-W Gap Open Penalty (Query)            (default: -400)
    -e    S-W Gap Extend Penalty (Reference)      (default: -70)
    -f    S-W Gap Extend Penalty (Query)          (default: -70)
    -h    S-W Hit Threshold                       (default: 68.00%)

Command:
%rmapper -s spaced_seed -n seed_matches_per_window -t seed_hit_taboo_length -9 seed_generation_taboo_length -w seed_window_length -o max_hits_per_read -r max_read_length -d kmer -m sw_match_value -i sw_mismatch_value -g sw_gap_open_ref -q sw_gap_open_query -e sw_gap_ext_ref -f sw_gap_ext_query -h sw_hit_threshold <query> <target> > <output> 2> <log> 

SHRiMP output:
>7:2:1147:982/1 chr3    +   36586562    36586595    2   35  36  2900    3G16G13
>7:2:1147:982/1 chr3    +   95338194    95338225    4   35  36  2700    9T7C14
>7:2:587:93/1   chr3    +   14913541    14913577    1   35  36  2960    19--16

"""

import os, sys, tempfile, os.path, re

assert sys.version_info[:2] >= (2.4)

def stop_err( msg ):
    
    sys.stderr.write( "%s\n" % msg )
    sys.exit()

def reverse_complement(s):
    
    complement_dna = {"A":"T", "T":"A", "C":"G", "G":"C", "a":"t", "t":"a", "c":"g", "g":"c", "N":"N", "n":"n" , ".":".", "-":"-"}
    reversed_s = []
    for i in s:
        reversed_s.append(complement_dna[i])
    reversed_s.reverse()
    return "".join(reversed_s)

def generate_sub_table(result_file, ref_file, score_files, table_outfile, hit_per_read, insertion_size):
    
    invalid_editstring_char = 0
    
    all_score_file = score_files.split(',')
    
    if len(all_score_file) != hit_per_read: stop_err('One or more query files is missing. Please check your dataset.')
        
    temp_table_name = tempfile.NamedTemporaryFile().name
    temp_table = open(temp_table_name, 'w')
    
    outfile = open(table_outfile,'w')
    
    # reference seq: not a single fasta seq
    refseq = {}
    chrom_cov = {}
    seq = ''
    
    for i, line in enumerate(file(ref_file)):
        line = line.rstrip()
        if not line or line.startswith('#'): continue
        
        if line.startswith('>'):
            if seq:
                if refseq.has_key(title):
                    pass
                else:
                    refseq[title] = seq
                    chrom_cov[title] = {}
                seq = ''
            title = line[1:]
        else:
            seq += line
    if seq:
        if not refseq.has_key(title):
            refseq[title] = seq
            chrom_cov[title] = {}

    # find hits : one end and/or the other
    hits = {}
    for i, line in enumerate(file(result_file)):
        line = line.rstrip()
        if not line or line.startswith('#'): continue
        
        #FORMAT: readname contigname strand contigstart contigend readstart readend readlength score editstring
        fields = line.split('\t')
        readname = fields[0][1:]
        chrom = fields[1]
        strand = fields[2]
        chrom_start = int(fields[3]) - 1
        chrom_end = int(fields[4])
        read_start = fields[5]
        read_end = fields[6]
        read_len = fields[7]
        score = fields[8]
        editstring = fields[9]
        
        if hit_per_read == 1:
            endindex = '1'
        else:
            readname, endindex = readname.split('/')
        
        if hits.has_key(readname):
            if hits[readname].has_key(endindex):
                hits[readname][endindex].append([strand, editstring, chrom_start, chrom_end, read_start, chrom])
            else:
                hits[readname][endindex] = [[strand, editstring, chrom_start, chrom_end, read_start, chrom]]
        else:
            hits[readname] = {}
            hits[readname][endindex] = [[strand, editstring, chrom_start, chrom_end, read_start, chrom]]
    
    # find score : one end and the other end
    hits_score = {}
    readname = ''
    score = ''
    for num_score_file in range(len(all_score_file)):
        score_file = all_score_file[num_score_file]
        for i, line in enumerate(file(score_file)):
            line = line.rstrip()
            if not line or line.startswith('#'): continue
        
            if line.startswith('>'):
                if score:
                    if hits.has_key(readname):
                        if len(hits[readname]) == hit_per_read:
                            if hits_score.has_key(readname):
                                if hits_score[readname].has_key(endindex):
                                    pass
                                else:
                                    hits_score[readname][endindex] = score
                            else:
                                hits_score[readname] = {}
                                hits_score[readname][endindex] = score
                    score = ''
                if hit_per_read == 1:
                    readname = line[1:]
                    endindex = '1'
                else:
                    readname, endindex = line[1:].split('/')
            else:
                score = line
                
        if score:   # the last one
            if hits.has_key(readname):
                if len(hits[readname]) == hit_per_read:
                    if hits_score.has_key(readname):
                        if hits_score[readname].has_key(endindex):
                            pass
                        else:
                            hits_score[readname][endindex] = score
                    else:
                        hits_score[readname] = {}
                        hits_score[readname][endindex] = score
    
    # call to all mappings            
    for readkey in hits.keys():
        if len(hits[readkey]) != hit_per_read: continue

        matches = []
        match_count = 0
        
        if hit_per_read == 1:
            if len(hits[readkey]['1']) == 1:
                matches = [ hits[readkey]['1'] ]
                match_count = 1
        else:
            end1_data = hits[readkey]['1']
            end2_data = hits[readkey]['2']
            
            for i, end1_hit in enumerate(end1_data):
                crin_strand = {'+': False, '-': False}
                crin_insertSize = {'+': False, '-': False}
        
                crin_strand[end1_hit[0]] = True
                crin_insertSize[end1_hit[0]] = int(end1_hit[2])
            
                for j, end2_hit in enumerate(end2_data):
                    crin_strand[end2_hit[0]] = True
                    crin_insertSize[end2_hit[0]] = int(end2_hit[2])
                
                    if end1_hit[-1] != end2_hit[-1] : continue

                    if crin_strand['+'] and crin_strand['-']:
                        if (crin_insertSize['-'] - crin_insertSize['+']) <= insertion_size:
                            matches.append([end1_hit, end2_hit])
                            match_count += 1

        if match_count == 1:
            
            for x, end_data in enumerate(matches[0]):
                
                end_strand, end_editstring, end_chr_start, end_chr_end, end_read_start, end_chrom = end_data
                end_read_start = int(end_read_start) - 1

                if end_strand == '-':
                    refsegment = reverse_complement(refseq[end_chrom][end_chr_start:end_chr_end]) 
                else:
                    refsegment = refseq[end_chrom][end_chr_start:end_chr_end]
                
                match_len = 0
                editindex = 0
                gap_read = 0
                
                while editindex < len(end_editstring):
                    
                    editchr = end_editstring[editindex]
                    chrA = ''
                    chrB = ''
                    locIndex = []
                    
                    if editchr.isdigit():
                        editcode = ''
                        
                        while editchr.isdigit() and editindex < len(end_editstring):
                            editcode += editchr
                            editindex += 1
                            if editindex < len(end_editstring): editchr = end_editstring[editindex]
                        
                        for baseIndex in range(int(editcode)):
                            chrA += refsegment[match_len+baseIndex]
                            chrB = chrA
                        
                        match_len += int(editcode)
                        
                    elif editchr == 'x':
                        # crossover: inserted between the appropriate two bases
                        # Two sequencing errors: 4x15x6 (25 matches with 2 crossovers)
                        # Treated as errors in the reads; Do nothing.
                        editindex += 1
                        
                    elif editchr.isalpha(): 
                        editcode = editchr
                        editindex += 1
                        chrA = refsegment[match_len]
                        chrB = editcode
                        match_len += len(editcode)
                        
                    elif editchr == '-':
                        editcode = editchr
                        editindex += 1
                        chrA = refsegment[match_len]
                        chrB = editcode
                        match_len += len(editcode)
                        gap_read += 1
                        
                    elif editchr == '(':
                        editcode = ''
                        
                        while editchr != ')' and editindex < len(end_editstring):
                            if editindex < len(end_editstring): editchr = end_editstring[editindex]
                            editcode += editchr
                            editindex += 1
                        
                        editcode = editcode[1:-1]
                        chrA = '-'*len(editcode)
                        chrB = editcode
                        
                    else:
                        invalid_editstring_char += 1
                        
                    if end_strand == '-':
                        
                        chrA = reverse_complement(chrA)
                        chrB = reverse_complement(chrB)
                        
                    pos_line = ''
                    rev_line = ''
                    
                    for mappingIndex in range(len(chrA)):
                        # reference
                        chrAx = chrA[mappingIndex]
                        # read
                        chrBx = chrB[mappingIndex]

                        if chrAx and chrBx and chrBx.upper() != 'N':
                            
                            if end_strand == '+':
                            
                                chrom_loc = end_chr_start+match_len-len(chrA)+mappingIndex         
                                read_loc = end_read_start+match_len-len(chrA)+mappingIndex-gap_read
                                
                                if chrAx == '-': chrom_loc -= 1
                                
                                if chrBx == '-': 
                                    scoreBx = '-1'
                                else:
                                    scoreBx = hits_score[readkey][str(x+1)].split()[read_loc]
                                
                                # 1-based on chrom_loc and read_loc
                                pos_line = pos_line + '\t'.join([end_chrom, str(chrom_loc+1), readkey+'/'+str(x+1), str(read_loc+1), chrAx, chrBx, scoreBx]) + '\n'
                                
                            else:
                                
                                chrom_loc = end_chr_end-match_len+mappingIndex
                                read_loc = end_read_start+match_len-1-mappingIndex-gap_read
                                
                                if chrAx == '-': chrom_loc -= 1
                                
                                if chrBx == '-': 
                                    scoreBx = '-1'     
                                else:
                                    scoreBx = hits_score[readkey][str(x+1)].split()[read_loc]
                                    
                                # 1-based on chrom_loc and read_loc                                                                       
                                rev_line = '\t'.join([end_chrom, str(chrom_loc+1), readkey+'/'+str(x+1), str(read_loc+1), chrAx, chrBx, scoreBx]) +'\n' + rev_line

                            if chrom_cov.has_key(end_chrom):
                                
                                if chrom_cov[end_chrom].has_key(chrom_loc):
                                    chrom_cov[end_chrom][chrom_loc] += 1
                                else:
                                    chrom_cov[end_chrom][chrom_loc] = 1
                                    
                            else:
                                
                                chrom_cov[end_chrom] = {}
                                chrom_cov[end_chrom][chrom_loc] = 1
                    
                    if pos_line: temp_table.write('%s\n' %(pos_line.rstrip('\r\n')))
                    if rev_line: temp_table.write('%s\n' %(rev_line.rstrip('\r\n')))
    
    temp_table.close()

    # chrom-wide coverage
    for i, line in enumerate(open(temp_table_name)):
        
        line = line.rstrip()
        if not line or line.startswith('#'): continue
        
        fields = line.split()
        chrom = fields[0]
        eachBp = int(fields[1])
        readname = fields[2]
        
        if hit_per_read == 1:
            fields[2] = readname.split('/')[0]
            
        if chrom_cov[chrom].has_key(eachBp):
            outfile.write('%s\t%d\n' %('\t'.join(fields), chrom_cov[chrom][eachBp]))
        else:
            outfile.write('%s\t%d\n' %('\t'.join(fields), 0))
            
    outfile.close()
    
    if os.path.exists(temp_table_name): os.remove(temp_table_name)
    
    if invalid_editstring_char:
        print 'Skip ', invalid_editstring_char, ' invalid characters in editstrings'
        
    return True 
   
def convert_fastqsolexa_to_fasta_qual(infile_name, query_fasta, query_qual):
    
    outfile_seq = open( query_fasta, 'w' )
    outfile_score = open( query_qual, 'w' )

    seq_title_startswith = ''
    qual_title_startswith = ''
    
    default_coding_value = 64       # Solexa ascii-code
    fastq_block_lines = 0
    
    for i, line in enumerate( file( infile_name ) ):
        line = line.rstrip()
        if not line or line.startswith( '#' ): continue
        
        fastq_block_lines = ( fastq_block_lines + 1 ) % 4
        line_startswith = line[0:1]
        
        if fastq_block_lines == 1:
            # first line is @title_of_seq
            if not seq_title_startswith:
                seq_title_startswith = line_startswith
                
            if line_startswith != seq_title_startswith:
                outfile_seq.close()
                outfile_score.close()
                stop_err( 'Invalid fastqsolexa format at line %d: %s.' % ( i + 1, line ) )
                
            read_title = line[1:]
            outfile_seq.write( '>%s\n' % line[1:] )
            
        elif fastq_block_lines == 2:
            # second line is nucleotides
            read_length = len( line )
            outfile_seq.write( '%s\n' % line )
            
        elif fastq_block_lines == 3:
            # third line is +title_of_qualityscore ( might be skipped )
            if not qual_title_startswith:
                qual_title_startswith = line_startswith
                
            if line_startswith != qual_title_startswith:
                outfile_seq.close()
                outfile_score.close()
                stop_err( 'Invalid fastqsolexa format at line %d: %s.' % ( i + 1, line ) )    
                
            quality_title = line[1:]
            if quality_title and read_title != quality_title:
                outfile_seq.close()
                outfile_score.close()
                stop_err( 'Invalid fastqsolexa format at line %d: sequence title "%s" differes from score title "%s".' % ( i + 1, read_title, quality_title ) )
                
            if not quality_title:
                outfile_score.write( '>%s\n' % read_title )
            else:
                outfile_score.write( '>%s\n' % line[1:] )
                
        else:
            # fourth line is quality scores
            qual = ''
            fastq_integer = True
            # peek: ascii or digits?
            val = line.split()[0]
            try: 
                check = int( val )
                fastq_integer = True
            except:
                fastq_integer = False
                
            if fastq_integer:
                # digits
                qual = line
            else:
                # ascii
                quality_score_length = len( line )
                if quality_score_length == read_length + 1:
                    # first char is qual_score_startswith
                    qual_score_startswith = ord( line[0:1] )
                    line = line[1:]
                elif quality_score_length == read_length:
                    qual_score_startswith = default_coding_value
                else:
                    stop_err( 'Invalid fastqsolexa format at line %d: the number of quality scores ( %d ) is not the same as bases ( %d ).' % ( i + 1, quality_score_length, read_length ) )
                    
                for j, char in enumerate( line ):
                    score = ord( char ) - qual_score_startswith    # 64
                    qual = "%s%s " % ( qual, str( score ) )
                    
            outfile_score.write( '%s\n' % qual )
              
    outfile_seq.close()
    outfile_score.close()

    return True

def __main__():
    
    # SHRiMP path
    shrimp = 'rmapper-ls'
    
    # I/O
    input_target_file = sys.argv[1]                  # fasta
    shrimp_outfile    = sys.argv[2]                # shrimp output
    table_outfile     = sys.argv[3]                 # table output
    single_or_paired  = sys.argv[4].split(',')       
    
    insertion_size = 600
    
    if len(single_or_paired) == 1:                  # single or paired
        type_of_reads = 'single'
        hit_per_read  = 1
        input_query   = single_or_paired[0]
        query_fasta   = tempfile.NamedTemporaryFile().name
        query_qual    = tempfile.NamedTemporaryFile().name

    else:                                           # paired-end
        type_of_reads    = 'paired'
        hit_per_read     = 2
        input_query_end1 = single_or_paired[0]  
        input_query_end2 = single_or_paired[1]
        insertion_size = int(single_or_paired[2])
        query_fasta_end1 = tempfile.NamedTemporaryFile().name
        query_fasta_end2 = tempfile.NamedTemporaryFile().name
        query_qual_end1  = tempfile.NamedTemporaryFile().name
        query_qual_end2  = tempfile.NamedTemporaryFile().name
        
    # SHRiMP parameters: total = 15, default values
    spaced_seed = '111111011111'
    seed_matches_per_window = '2'
    seed_hit_taboo_length = '4'
    seed_generation_taboo_length = '0'
    seed_window_length = '115.0'
    max_hits_per_read = '100'
    max_read_length = '1000'
    kmer = '-1'
    sw_match_value = '100'
    sw_mismatch_value = '-150'
    sw_gap_open_ref = '-400'
    sw_gap_open_query = '-400'
    sw_gap_ext_ref = '-70'
    sw_gap_ext_query = '-70'
    sw_hit_threshold = '68.0'

    # TODO: put the threshold on each of these parameters
    if len(sys.argv) > 5:
        
        try:
            if sys.argv[5].isdigit():
                spaced_seed = sys.argv[5]
            else:
                stop_err('Error in assigning parameter: Spaced seed.')
        except:
            stop_err('Spaced seed must be a combination of 1s and 0s.')
        
        seed_matches_per_window = sys.argv[6]
        seed_hit_taboo_length = sys.argv[7]
        seed_generation_taboo_length = sys.argv[8]
        seed_window_length = sys.argv[9]
        max_hits_per_read = sys.argv[10]
        max_read_length = sys.argv[11]
        kmer = sys.argv[12]
        sw_match_value = sys.argv[13]
        sw_mismatch_value = sys.argv[14]
        sw_gap_open_ref = sys.argv[15]
        sw_gap_open_query = sys.argv[16]
        sw_gap_ext_ref = sys.argv[17]
        sw_gap_ext_query = sys.argv[18]
        sw_hit_threshold = sys.argv[19]
    
    # temp file for shrimp log file
    shrimp_log = tempfile.NamedTemporaryFile().name
    
    # convert fastq to fasta and quality score files
    if type_of_reads == 'single':
        return_value = convert_fastqsolexa_to_fasta_qual(input_query, query_fasta, query_qual)
    else:
        return_value = convert_fastqsolexa_to_fasta_qual(input_query_end1, query_fasta_end1, query_qual_end1)
        return_value = convert_fastqsolexa_to_fasta_qual(input_query_end2, query_fasta_end2, query_qual_end2)
        
    # SHRiMP command
    if type_of_reads == 'single':
        command = ' '.join([shrimp,  '-s', spaced_seed, '-n', seed_matches_per_window, '-t', seed_hit_taboo_length, '-9', seed_generation_taboo_length, '-w', seed_window_length, '-o', max_hits_per_read, '-r', max_read_length, '-d', kmer, '-m', sw_match_value, '-i', sw_mismatch_value, '-g', sw_gap_open_ref, '-q', sw_gap_open_query, '-e', sw_gap_ext_ref, '-f', sw_gap_ext_query, '-h', sw_hit_threshold, query_fasta, input_target_file, '>', shrimp_outfile, '2>', shrimp_log])
    
        try:
            os.system(command)
        except Exception, e:
            if os.path.exists(query_fasta): os.remove(query_fasta)
            if os.path.exists(query_qual): os.remove(query_qual)
            stop_err(str(e))
            
    else: # paired
        command_end1 = ' '.join([shrimp, '-s', spaced_seed, '-n', seed_matches_per_window, '-t', seed_hit_taboo_length, '-9', seed_generation_taboo_length, '-w', seed_window_length, '-o', max_hits_per_read, '-r', max_read_length, '-d', kmer, '-m', sw_match_value, '-i', sw_mismatch_value, '-g', sw_gap_open_ref, '-q', sw_gap_open_query, '-e', sw_gap_ext_ref, '-f', sw_gap_ext_query, '-h', sw_hit_threshold, query_fasta_end1, input_target_file, '>', shrimp_outfile, '2>', shrimp_log])
        command_end2 = ' '.join([shrimp, '-s', spaced_seed, '-n', seed_matches_per_window, '-t', seed_hit_taboo_length, '-9', seed_generation_taboo_length, '-w', seed_window_length, '-o', max_hits_per_read, '-r', max_read_length, '-d', kmer, '-m', sw_match_value, '-i', sw_mismatch_value, '-g', sw_gap_open_ref, '-q', sw_gap_open_query, '-e', sw_gap_ext_ref, '-f', sw_gap_ext_query, '-h', sw_hit_threshold, query_fasta_end2, input_target_file, '>>', shrimp_outfile, '2>>', shrimp_log])
        
        try:
            os.system(command_end1)
            os.system(command_end2)
        except Exception, e:
            if os.path.exists(query_fasta_end1): os.remove(query_fasta_end1)
            if os.path.exists(query_fasta_end2): os.remove(query_fasta_end2)
            if os.path.exists(query_qual_end1): os.remove(query_qual_end1)
            if os.path.exists(query_qual_end2): os.remove(query_qual_end2)
            stop_err(str(e))
    
    # check SHRiMP output: count number of lines
    num_hits = 0
    if shrimp_outfile:
        for i, line in enumerate(file(shrimp_outfile)):
            line = line.rstrip('\r\n')
            if not line or line.startswith('#'): continue
            try:
                fields = line.split()
                num_hits += 1
            except Exception, e:
                stop_err(str(e))
                
    if num_hits == 0:   # no hits generated
        err_msg = ''
        if shrimp_log:
            for i, line in enumerate(file(shrimp_log)):
                if line.startswith('error'):            # deal with memory error: 
                    err_msg += line                     # error: realloc failed: Cannot allocate memory
                if re.search('Reads Matched', line):    # deal with zero hits
                    if int(line[8:].split()[2]) == 0:
                        err_msg = 'Zero hits found.\n' 
        stop_err('SHRiMP Failed due to:\n' + err_msg)
        
    # convert to table
    if type_of_reads == 'single':
        return_value = generate_sub_table(shrimp_outfile, input_target_file, query_qual, table_outfile, hit_per_read, insertion_size)
    else:
        return_value = generate_sub_table(shrimp_outfile, input_target_file, query_qual_end1+','+query_qual_end2, table_outfile, hit_per_read, insertion_size)
        
    # remove temp. files
    if type_of_reads == 'single':
        if os.path.exists(query_fasta): os.remove(query_fasta)
        if os.path.exists(query_qual): os.remove(query_qual)
    else:
        if os.path.exists(query_fasta_end1): os.remove(query_fasta_end1)
        if os.path.exists(query_fasta_end2): os.remove(query_fasta_end2)
        if os.path.exists(query_qual_end1): os.remove(query_qual_end1)
        if os.path.exists(query_qual_end2): os.remove(query_qual_end2)    
    
    if os.path.exists(shrimp_log): os.remove(shrimp_log)

    
if __name__ == '__main__': __main__()
    
