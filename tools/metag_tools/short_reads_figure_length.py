#! /usr/bin/python
"""
Galaxy
to commit
4.2 for i, line in enumerate(file(filename)):
4.4 stop passing read_seqfile and read_scorefile around
4.5 use --> if __name__ == "__main__": __main__()
5. use galaxy extention
Input:
    sequence file(s): zip or text file --> for 454 and Solexa 
Output:
    pdf files from R, length histogram --> before and after trim
----
Wen-Yu Chung
"""
import os, sys, math, tempfile, zipfile, re
from rpy import *

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
            (run_id, file_id, read_x, read_y, read) = each_line.split()
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


def generate_hist_figure():
    # R module and code
        
    tmp_array = []

    # data for R hist
    # write the length only!
    outfile = open(outfile_R_name,'w')
    title_keys = seq_hash.keys()
    for read_title in title_keys:
        tmp_seq = seq_hash[(read_title)]
        length_before_trim.append(len(tmp_seq))
        print >> outfile, len(tmp_seq)
    outfile.close()
        
    max_length_before_trim = max(length_before_trim)
    
    # generate pdf figures
    """
    outfile_R_pdf = outfile_R_name 
    r.pdf(outfile_R_pdf)
    
    title = infile_seq_name.split('/')[-1]
    xlim_range = [1,max_length_before_trim]
    r.hist(length_before_trim,prob=1, xlab="Read length (bp)", ylab="Frequency (%)", xlim=xlim_range, main=title, nclass=100)
    r.dev_off()
    """
    return 0


# I/O
infile_seq_name = sys.argv[1].strip()
outfile_R_name = sys.argv[2].strip()

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

# detect whether it's tabular or fasta format
if read_seqfile[0].startswith(">"):
    seq_method = '454'
else:
    seq_method = 'solexa'

    
# parse files
if (seq_method == 'solexa'):
    seq_hash = parse_solexa_files(read_seqfile, 'seq')
else: # the other two are both fasta format
    seq_hash = parse_fasta_format(read_seqfile)

# R
status = generate_hist_figure()

# close and remove temporary files
r.quit(save = "no")
