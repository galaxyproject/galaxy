#! /usr/bin/python
"""
Galaxy
to commit
4.2 for i, line in enumerate(file(filename)):
4.4 stop passing read_seqfile and read_scorefile around
4.5 use --> if __name__ == "__main__": __main__()
5. use galaxy extention
Input:
    quality score file(s): zip or text file
Output:
pdf files from R
    score distribution --> boxplot, Solexa as 36bp, 454 as 20 points
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


def generate_boxplot_figure():
    # R module and code
        
    score_matrix = []
    tmp_array = []
    
    # data for R boxplot
    title_keys = score_hash.keys()
    if (seq_method == 'solexa'):
        for read_title in title_keys:
            score_points.append(score_hash[(read_title)])
    else:
        for read_title in title_keys:
            tmp_score = '0 ' + score_hash[(read_title)]
            tmp_list = tmp_score.split()
            read_length = len(tmp_list)
            if (read_length > 100):
                step = int(math.floor((read_length-1)*1.0/number_of_points))
                score = []
                point = 1
                point_sum = 0
                step_average = 0
                for i in xrange(1,read_length):
                    if (i < (point * step)):
                        point_sum += int(tmp_list[i])
                        step_average += 1
                    else:
                        point_avg = point_sum*1.0/step_average
                        score.append(point_avg)
                        point += 1
                        point_sum = 0
                        step_average = 0

                if (step_average > 0):
                    point_avg = point_sum*1.0/step_average
                    score.append(point_avg)

                if (len(score) > number_of_points):
                    last_avg = 0
                    for j in xrange(number_of_points-1,len(score)):
                        last_avg += score[j]
                    last_avg = last_avg/(len(score)-number_of_points+1)
                else:    
                    last_avg = score[-1]
                score_points_tmp = []
                for k in range(number_of_points-1):
                    score_points_tmp.append(score[k])
                score_points_tmp.append(last_avg)
                score_points.append(score_points_tmp)
                score_points_tmp = []

    # reverse the matrix, for R
    for i in range(number_of_points-1):
        for j in range(len(score_points)):
            tmp_array.append(score_points[j][i])
        score_matrix.append(tmp_array)
        tmp_array = []

    # generate pdf figures
    outfile_R_pdf = outfile_R_name 
    r.pdf(outfile_R_pdf)
    
    #title = infile_score_name.split('/')[-1]
    title = "boxplot of quality scores"
    if (seq_method=='solexa'):
        r.boxplot(score_matrix,xlab="location in read length",main=title)
    else:
        r.boxplot(score_matrix,xlab="percentage in read length",xaxt="n",main=title)
        x_old_range = []
        x_new_range = []
        step = 100/number_of_points 
        for i in xrange(0,100,step):
            x_old_range.append((i/step))
            x_new_range.append(i)
        r.axis(1,x_old_range,x_new_range)
    
    r.dev_off()
    
    return 0


# I/O
infile_score_name = sys.argv[1].strip()
outfile_R_name = sys.argv[2].strip()

# to unzip or not unzip file
tmp_score_dir = ''
score_file_list = []
if (zipfile.is_zipfile(infile_score_name)): (tmp_score_dir, score_file_list) = unzip_files(infile_score_name)
else: score_file_list = [infile_score_name]
read_scorefile = read_input_files(score_file_list)
if (os.path.isdir(tmp_score_dir)):
    for file_name in score_file_list:
        os.remove(file_name)
    os.removedirs(tmp_score_dir)

# detect whether it's tabular or fasta format
if read_scorefile[0].startswith(">"):
    seq_method = '454'
else:
    seq_method = 'solexa'

# detect whether it's a sequence file 
if re.match('[A-Z]', read_scorefile[1]):
    stop_err("this is not a quality score file.")
        
# parse files
if (seq_method == 'solexa'):
    score_hash = parse_solexa_files(read_scorefile, 'score')
    number_of_points = 36
else: # the other two are both fasta format
    score_hash = parse_fasta_format(read_scorefile)
    number_of_points = 20

print seq_method, number_of_points

# R
status = generate_boxplot_figure()
r.quit(save = "no")
