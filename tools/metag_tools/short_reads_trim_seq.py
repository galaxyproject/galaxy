#! /usr/bin/python
"""
trim reads based on the quality scores
input: read file and quality score file
output: trimmed read file
"""

import os, sys, math, tempfile, zipfile, re

def stop_err(msg):
    
    sys.stderr.write(msg)
    sys.stderr.write("\n")
    sys.exit()
    

def unzip(zip_file):
    
    zip_inst = zipfile.ZipFile(zip_file, 'r')
    
    tmpfilename = tempfile.NamedTemporaryFile().name
    for name in zip_inst.namelist():
        file(tmpfilename,'a').write(zip_inst.read(name))
    
    zip_inst.close()
    
    return tmpfilename


def show_output(outfile_seq, seq_title, segments):
    if (len(segments) > 1):
        for i in range(len(segments)):
            print >> outfile_seq, "%s_%d\n%s" % (seq_title, i, segments[i])
    elif (len(segments[0]) > 0):
        print >> outfile_seq, "%s\n%s" % (seq_title, segments[0])
    return


def trim_seq(seq, score, specific_argument, trim_score, threshold):

    seq_method = '454'
    trim_after_this_position = 0
    keep_homopolymers = 'no'
    
    # trim after a certain position
    if specific_argument.isdigit():
        keep_homopolymers = 'no'
        trim_after_this_position = int(specific_argument)    
        if (trim_after_this_position > 0 and trim_after_this_position < len(seq)):
            seq = seq[0:trim_after_this_position]
    else:
        keep_homopolymers = specific_argument
                
    new_trim_seq = ''
            
    for i in range(len(seq)):
        if (i >= len(score)): score.append(0) 
        if (int(score[i]) >= trim_score):
            pass_nuc = seq[i:(i+1)]
        else:
            # keep homopolymers?
            if keep_homopolymers == 'yes' and (((i == 0) or (seq[i:(i+1)].lower() == seq[(i-1):i].lower()))):
                    pass_nuc = seq[i:(i+1)]
            else:
                pass_nuc = ' '             
        new_trim_seq = new_trim_seq + pass_nuc
            
        # find the max substrings
        segments = new_trim_seq.split()
        max_segment = ''
        len_max_segment = 0
    
        if (threshold == 0):
            for each_segment in segments:
                if (len_max_segment < len(each_segment)):
                    max_segment = each_segment + ','
                    len_max_segment = len(each_segment)
                elif (len_max_segment == len(each_segment)):
                    max_segment = max_segment + each_segment + ','
        else:
            for each_segment in segments:
                if (len(each_segment) >= threshold):
                    max_segment = max_segment + each_segment + ','
        
    return max_segment[0:-1]

def __main__():

    # I/O
    seq_method = sys.argv[1].strip().lower()
    try:
        threshold_trim = int(sys.argv[2].strip())
    except:
        stop_err("Invalid value for minimal quality score")
    try:
        threshold_report = int(sys.argv[3].strip())
    except:
        stop_err("Invalid value for minimal sequence length")

    outfile_seq_name = sys.argv[4].strip()
    infile_seq_name = sys.argv[5].strip()
    infile_score_name = sys.argv[6].strip()
    special_argument = sys.argv[7].strip()
    if seq_method == '454':
        keep_homopolymers = special_argument
    else:
        trim_after_this_position = int(special_argument)
    
    # unzip files
    if (zipfile.is_zipfile(infile_seq_name)):
        unzip_seq_infile = unzip(infile_seq_name) 
    else: unzip_seq_infile = infile_seq_name

    if (zipfile.is_zipfile(infile_score_name)): 
        unzip_score_infile = unzip(infile_score_name)
    else: unzip_score_infile = infile_score_name

    
    outfile_seq = open(outfile_seq_name,'w')
    

    if (os.path.exists(unzip_seq_infile) and os.path.exists(unzip_score_infile)):
        # read one sequence
        to_find_score = True
        seq = None
        score = None
        score_fh = open(unzip_score_infile,'r')
        if seq_method == '454':
            for i, line in enumerate (open (unzip_seq_infile) ):
                line = line.rstrip('\r\n')
                if line.startswith('#'):
                    continue
                if (line.startswith('>')):
                    if seq:
                        to_find_score = True
                        score = None
                        while to_find_score:
                            score_line = score_fh.readline().rstrip('\r\n')
                            if not score_line: break
                            if score_line.startswith('#'):
                                continue
                            if (score_line.startswith('>')):
                                if score:
                                    score = score.split()       
                                    new_trim_seq_segments = trim_seq(seq, score, special_argument, threshold_trim, threshold_report)                                            
                                    # output trimmed sequence to a fasta file
                                    segments = new_trim_seq_segments.split(',')
                                    show_output(outfile_seq, seq_title, segments)
                                    to_find_score = False    
                                score = None
                            else:
                                if not score: score = score_line
                                else:
                                    score = score + ' ' + score_line
                    seq_title = line
                    seq = None
                else:
                    if not seq: seq = line
                    else:
                        seq = seq + line
            if seq:
                score = None
                while score_line:
                    score_line = score_fh.readline().rstrip('\r\n')
                    if score_line.startswith('#'):
                        continue
                    if ( not score_line.startswith('>')):
                        if not score: score = score_line
                        else:
                            score = score + ' ' + score_line
                if score: 
                    score = score.split()       
                    new_trim_seq_segments = trim_seq(seq, score, special_argument, threshold_trim, threshold_report)                                            
                    # output trimmed sequence to a fasta file
                    segments = new_trim_seq_segments.split(',')
                    show_output(outfile_seq, seq_title, segments)    
        else: # Solexa format
            for i, line in enumerate (open (unzip_seq_infile) ):
                line = line.rstrip('\r\n')
                if line.startswith('#'):
                    continue
                seq_title = '>' + str(i)
                seq = line.split()[-1]
                score = score_fh.readline()
                each_loc = score.split('\t')
                score = []
                for each_base in each_loc:
                    each_nuc_error = each_base.split()
                    each_nuc_error[0] = int(each_nuc_error[0])
                    each_nuc_error[1] = int(each_nuc_error[1])
                    each_nuc_error[2] = int(each_nuc_error[2])
                    each_nuc_error[3] = int(each_nuc_error[3])
                    big = max(each_nuc_error)
                    score.append(big)
                new_trim_seq_segments = trim_seq(seq, score, special_argument, threshold_trim, threshold_report)
                # output trimmed sequence to a fasta file
                segments = new_trim_seq_segments.split(',')
                show_output(outfile_seq, seq_title, segments)    
        score_fh.close()
    outfile_seq.close()
                            
    if (zipfile.is_zipfile(infile_seq_name)): os.remove(unzip_seq_infile)
    if (zipfile.is_zipfile(infile_score_name)): os.remove(unzip_score_infile)
    
if __name__ == "__main__": __main__()