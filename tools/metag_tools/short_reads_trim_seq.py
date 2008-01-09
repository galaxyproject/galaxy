#! /usr/bin/python
"""
Galaxy
to commit
1. filter: select read length longer than a threshold without trimming (minimum score = 0?)
4. incorporate greg's changes.
4.2 for i, line in enumerate(file(filename)):
4.4 stop passing read_seqfile and read_scorefile around
4.5 use --> if __name__ == "__main__": __main__()
5. use galaxy extention
6. a better trimming process for 454 (homopolymers)
6.1 to keep the longest homoloplymers
Input:
1. sequence file(s): zip or text file --> for 454 and Solexa 
2. quality score file(s): zip or text file --> for 454 and Solexa
3. trace file(s): zip or single scf file --> for Sanger
4. threshold to trim the sequence
5. threshold of the trimmed sequence length to be reported
Output:
trimmed sequence in one file
----
Wen-Yu Chung
"""
import os, sys, math, tempfile, zipfile, re
#from rpy import *

# default and initialize values
number_of_points = 20
read_seqfile = []
read_scorefile = []
title_keys = []
seq_hash = {}
score_hash = {}
trim_seq_hash = {}
tmp_seq = ''
tmp_score = []            # change variables here

length_before_trim = []
length_after_trim = []
score_points = []

database_tmp = "/tmp/"        # default dir: current directory
if (not os.path.isdir(database_tmp)):
    os.mkdir(database_tmp)
    
# functions
def stop_err(msg):
    
    sys.stderr.write(msg)
    sys.stderr.write("\n")
    sys.exit()
    

def read_input_files(file_list):
    
    read_file = []
    
    for file_name in file_list:
        infile = open(file_name,'r')
        read_file = infile.readlines()
        infile.close()

    return read_file


def unzip_files(file_name):
    
    read_file = []
    
    temp_dir_name = tempfile.mkdtemp() + '/'        #dir=database_tmp
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


def parse_solexa_files(result, type):
    # parse solexa seq and probability files only
    # not fasta format
    # assign numeric id
        
    tmp_hash = {}
    tmp_title = ''
    tmp_seq = ''
    tmp_id = 0
    
    if (type == 'seq'):
        for each_line in result:
            tmp_seq = ''
            each_line.strip('\r\n')
            tmp_id += 1
            fasta_id = '>' + str(tmp_id)
            #(run_id, file_id, read_x, read_y, read) = each_line.split()
            tmp_values = each_line.split()
            read = tmp_values[-1]
            tmp_hash[(fasta_id)] = read
    else: # type == score
        for each_line in result:
            tmp_seq = []
            each_line.strip('\r\n')
            tmp_id += 1
            fasta_id = '>' + str(tmp_id)
            each_loc = each_line.split('\t')
            for each_base in each_loc:
                each_nuc_error = each_base.split()
                each_nuc_error[0] = int(each_nuc_error[0])
                each_nuc_error[1] = int(each_nuc_error[1])
                each_nuc_error[2] = int(each_nuc_error[2])
                each_nuc_error[3] = int(each_nuc_error[3])
                big = max(each_nuc_error)
                #baseIndex = each_nuc_error.index(big)
                tmp_seq.append(big)
            tmp_hash[(fasta_id)] = tmp_seq
    
    return tmp_hash

    
def parse_fasta_format(result):    
    # detect whether it's score or seq files
    # return a hash: key = title and value = seq
        
    tmp_hash = {}
    tmp_title = ''
    tmp_seq = ''

    for each_line in result:
        each_line = each_line.strip('\r\n')
        if (each_line[0] == '>'):
            if (len(tmp_seq) > 0):
                tmp_hash[(tmp_title)] = tmp_seq
            tmp_title = each_line
            tmp_seq = ''
        else:
            tmp_seq = tmp_seq + each_line
            if (each_line.split()[0].isdigit()):
                tmp_seq = tmp_seq + ' '
    if (len(tmp_seq) > 0):
        tmp_hash[(tmp_title)] = tmp_seq
        
    return tmp_hash


def trim_seq():
    # trim sequence
    title_keys = seq_hash.keys()
    for read_title in title_keys:
        tmp_seq = seq_hash[(read_title)]
        if (seq_method == 'solexa'):
            tmp_score = score_hash[(read_title)]
        else:
            tmp_score = score_hash[(read_title)].split()
        
        trim_seq = ''
    
        for i in range(len(tmp_seq)):
            if (int(tmp_score[i]) > threshold_trim):
                pass_nuc = tmp_seq[i:(i+1)]
            else:
                pass_nuc = ' '
            trim_seq = trim_seq + pass_nuc
            
        # find the max substrings
        segments = trim_seq.split()
        max_segment = ''
        len_max_segment = 0
    
        if (threshold_report == 0):
            for each_segment in segments:
                if (len_max_segment < len(each_segment)):
                    max_segment = each_segment + ','
                    len_max_segment = len(each_segment)
                elif (len_max_segment == len(each_segment)):
                    max_segment = max_segment + each_segment + ','
        else:
            for each_segment in segments:
                if (len(each_segment) >= threshold_report):
                    max_segment = max_segment + each_segment + ','
    
        trim_seq_hash[(read_title)] = max_segment[0:-1]
    
    return trim_seq_hash

def __main__():
    # I/O
    seq_method = sys.argv[1].strip().lower()
    try:
        threshold_trim = int(sys.argv[2].strip())
    except:
        stop_err("Invalid value for minimal quality score")
    try:
        threshold_report= int(sys.argv[3].strip())
    except:
        stop_err("Invalid value for minimal sequence length")
    outfile_seq_name = sys.argv[4].strip()
    infile_seq_name = sys.argv[5].strip()
    infile_score_name = sys.argv[6].strip()
    
    # to unzip or not unzip file
    tmp_seq_dir = ''
    seq_file_list = []
    if (zipfile.is_zipfile(infile_seq_name)): (tmp_seq_dir, seq_file_list) = unzip_files(infile_seq_name)
    else: seq_file_list = [infile_seq_name]
    read_seqfile = read_input_files(seq_file_list)
    if (os.path.isdir(tmp_seq_dir)): 
        for file_name in seq_file_list:
            os.remove(file_name)
        os.removedirs(tmp_seq_dir)

    tmp_score_dir = ''
    score_file_list = []
    if (zipfile.is_zipfile(infile_score_name)): (tmp_score_dir, score_file_list) = unzip_files(infile_score_name)
    else: score_file_list = [infile_score_name]
    read_scorefile = read_input_files(score_file_list)
    if (os.path.isdir(tmp_score_dir)):
        for file_name in score_file_list:
            os.remove(file_name)
        os.removedirs(tmp_score_dir)

    # parse files
    if (seq_method == 'solexa'):
        seq_hash = parse_solexa_files(read_seqfile, 'seq')
        score_hash = parse_solexa_files(read_scorefile, 'score')
        if (threshold_report > 36):
            print "the read length from solexa is 36bp, your choice of read length is not valid.\n"
            print "the threshold is set to zero (return the longest substring).\n"
            threshold_report = 0
        number_of_points = 36
    else: # the other two are both fasta format
        seq_hash = parse_fasta_format(read_seqfile)
        score_hash = parse_fasta_format(read_scorefile)
        number_of_points = 20

    # trim sequence
    trim_seq_hash = trim_seq()
    
    # output trimmed sequence to a fasta file
    outfile_seq = open(outfile_seq_name,'w')
    title_keys = seq_hash.keys()
    for read_title in title_keys:
        tmp_seq = seq_hash[(read_title)]
        tmp_trim_seq = trim_seq_hash[(read_title)].split(',')    
        if (len(tmp_trim_seq) > 1):
            for i in range(len(tmp_trim_seq)):
                print >> outfile_seq, "%s %d\n%s" % (read_title, i, tmp_trim_seq[i])        
        elif (len(tmp_trim_seq[0]) > 0):
            print >> outfile_seq, "%s\n%s" % (read_title, tmp_trim_seq[0])
    outfile_seq.close()

#if __name__ == "__main__": __main__()
if 1:
    # I/O
    seq_method = sys.argv[1].strip().lower()
    try:
        threshold_trim = int(sys.argv[2].strip())
    except:
        stop_err("Invalid value for minimal quality score")
    try:
        threshold_report= int(sys.argv[3].strip())
    except:
        stop_err("Invalid value for minimal sequence length")
    outfile_seq_name = sys.argv[4].strip()
    infile_seq_name = sys.argv[5].strip()
    infile_score_name = sys.argv[6].strip()
    
    # to unzip or not unzip file
    tmp_seq_dir = ''
    seq_file_list = []
    if (zipfile.is_zipfile(infile_seq_name)): (tmp_seq_dir, seq_file_list) = unzip_files(infile_seq_name)
    else: seq_file_list = [infile_seq_name]
    read_seqfile = read_input_files(seq_file_list)
    if (os.path.isdir(tmp_seq_dir)): 
        for file_name in seq_file_list:
            os.remove(file_name)
        os.removedirs(tmp_seq_dir)

    tmp_score_dir = ''
    score_file_list = []
    if (zipfile.is_zipfile(infile_score_name)): (tmp_score_dir, score_file_list) = unzip_files(infile_score_name)
    else: score_file_list = [infile_score_name]
    read_scorefile = read_input_files(score_file_list)
    if (os.path.isdir(tmp_score_dir)):
        for file_name in score_file_list:
            os.remove(file_name)
        os.removedirs(tmp_score_dir)

    # parse files
    if (seq_method == 'solexa'):
        seq_hash = parse_solexa_files(read_seqfile, 'seq')
        score_hash = parse_solexa_files(read_scorefile, 'score')
        if (threshold_report > 36):
            print "the read length from solexa is 36bp, your choice of read length is not valid.\n"
            print "the threshold is set to zero (return the longest substring).\n"
            threshold_report = 0
        number_of_points = 36
    else: # the other two are both fasta format
        seq_hash = parse_fasta_format(read_seqfile)
        score_hash = parse_fasta_format(read_scorefile)
        number_of_points = 20

    # trim sequence
    trim_seq_hash = trim_seq()
    
    # output trimmed sequence to a fasta file
    outfile_seq = open(outfile_seq_name,'w')
    title_keys = seq_hash.keys()
    for read_title in title_keys:
        tmp_seq = seq_hash[(read_title)]
        tmp_trim_seq = trim_seq_hash[(read_title)].split(',')    
        if (len(tmp_trim_seq) > 1):
            for i in range(len(tmp_trim_seq)):
                print >> outfile_seq, "%s %d\n%s" % (read_title, i, tmp_trim_seq[i])        
        elif (len(tmp_trim_seq[0]) > 0):
            print >> outfile_seq, "%s\n%s" % (read_title, tmp_trim_seq[0])
    outfile_seq.close()

