#! /usr/bin/python
"""
Galaxy
to commit
2. use galaxy extention
Input:
trace file(s): zip or single scf file --> for Sanger
Output:
1. sequcence file
2. quality score file
----
Wen-Yu Chung
"""
import os, sys, math, tempfile, zipfile, re

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


def parse_trace_files(infile_name):

    trace_file = []
    tmp_dir = ''
    seq_file_name = tempfile.mkstemp()[1] #tempfile.NamedTemporaryFile(dir=database_tmp).name
    score_file_name = tempfile.mkstemp()[1] #tempfile.NamedTemporaryFile(dir=database_tmp).name 
    file_list_name = tempfile.mkstemp()[1] #tempfile.NamedTemporaryFile(dir=database_tmp).name 
    file_list = open(file_list_name,'w')
    
    if (zipfile.is_zipfile(infile_name)): 
        (tmp_dir, trace_file) = unzip_files(infile_name)
    else: 
        trace_file = [infile_name]
    for i in trace_file:
        print >> file_list,i
    file_list.close()
        
    # call phred
    phred_command = '~/phred/phred -if ' + file_list_name + ' -sa ' + seq_file_name + ' -qa ' + score_file_name + ' -process_nomatch 2>/dev/null' 
    os.system(phred_command)
    
    # remove every scf file and the file_list itself
    if (os.path.isdir(tmp_dir)):
        for i in trace_file:
            os.remove(i)
        os.removedirs(tmp_dir)
    os.remove(file_list_name)
        
    return seq_file_name, score_file_name

def __main__():
    # I/O
    infile_name = sys.argv[1].strip()
    outfile_seq_name = sys.argv[2].strip()
    outfile_score_name = sys.argv[3].strip()
    
    (infile_seq_name, infile_score_name)=parse_trace_files(infile_name)
    os.system("mv " + infile_seq_name + " " + outfile_seq_name)
    os.system("mv " + infile_score_name + " " + outfile_score_name)    

if __name__ == "__main__" : __main__()
