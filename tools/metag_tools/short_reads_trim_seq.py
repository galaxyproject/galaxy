#! /usr/bin/python

import os, sys, math, tempfile, zipfile, re

def stop_err(msg):
    
    sys.stderr.write(msg)
    sys.stderr.write("\n")
    sys.exit()
    

def unzip_files(file_name):
    
    read_file = []
    
    temp_dir_name = tempfile.mkdtemp() + '/'
    temp_new_dest = temp_dir_name + file_name.split('/')[-1]
    command_line = 'cp ' + file_name + ' ' + temp_dir_name + '\nunzip ' + temp_new_dest + ' -d ' + temp_dir_name
    
    os.system(command_line)
    os.remove(temp_new_dest)
    
    dest = os.listdir(temp_dir_name)
    if ((len(dest) == 1) and (os.path.isdir(dest[0]))):
        new_file_dir = temp_dir_name + dest[0] + '/'
        dest = os.listdir(new_file_dir)
    else:
        new_file_dir = temp_dir_name
    
    for filex in dest:
        filex = new_file_dir + filex
        read_file.append(filex)
        
    return new_file_dir, read_file

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
    tmp_seq_dir = ''
    seq_file_list = []
    if (zipfile.is_zipfile(infile_seq_name)): (tmp_seq_dir, seq_file_list) = unzip_files(infile_seq_name)
    else: seq_file_list = [infile_seq_name]

    tmp_score_dir = ''
    score_file_list = []
    if (zipfile.is_zipfile(infile_score_name)): (tmp_score_dir, score_file_list) = unzip_files(infile_score_name)
    else: score_file_list = [infile_score_name]

    # open both sequence and score file
    score_dirname_list = []
    score_rootname_list = []
    score_extname_list = []
    for score_file in score_file_list:
        (score_dirname, score_basename) = os.path.split(score_file)
        (score_rootname, score_extname) = os.path.splitext(score_basename)
        score_dirname_list.append(score_dirname)
        score_rootname_list.append(score_rootname)
        score_extname_list.append(score_extname)
    
    outfile_seq = open(outfile_seq_name,'w')
    
    for seq_file in seq_file_list:
        if (len(seq_file_list) > 1):
            (seq_dirname, seq_basename) = os.path.split(seq_file)
            (seq_rootname, seq_extname) = os.path.splitext(seq_basename)
            if (seq_rootname in score_rootname_list):
                file_index = score_rootname_list.index(seq_rootname)
                score_file = os.path.join(score_dirname_list[file_index], seq_rootname+score_extname_list[file_index])
        else:
            score_file = score_file_list[0]
            if (os.path.exists(seq_file) and os.path.exists(score_file)):
                # read one sequence
                to_find_score = True
                seq = None
                score = None
                score_fh = open(score_file,'r')
                if seq_method == '454':
                    for i, line in enumerate (open (seq_file) ):
                        line = line.rstrip('\r\n')
                        if (line.startswith('>')):
                            if seq:
                                to_find_score = True
                                score = None
                                while to_find_score:
                                    score_line = score_fh.readline().rstrip('\r\n')
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
                    for i, line in enumerate (open (seq_file) ):
                        line = line.rstrip('\r\n')
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
                            
    if (os.path.isdir(tmp_seq_dir)): 
        for file_name in seq_file_list:
            os.remove(file_name)
        os.removedirs(tmp_seq_dir)
    
    if (os.path.isdir(tmp_score_dir)):
        for file_name in score_file_list:
            os.remove(file_name)
        os.removedirs(tmp_score_dir)

if __name__ == "__main__": __main__()