#! /usr/bin/python

import os, sys, math, tempfile, zipfile, re
from rpy import *

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


def merge_to_20_datapoints(tmp_score):

    number_of_points = 20
    read_length = len(tmp_score)
    
    step = int(math.floor((read_length-1)*1.0/number_of_points))
    score = []
    point = 1
    point_sum = 0
    step_average = 0
    score_points_tmp = 0
    
    for i in xrange(1,read_length):
        if (i < (point * step)):
            point_sum += int(tmp_score[i])
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
            
    return score_points_tmp

def __main__():
    # I/O
    infile_score_name = sys.argv[1].strip()
    outfile_R_name = sys.argv[2].strip()

    # unzip infile
    tmp_score_dir = ''
    score_file_list = []
    if (zipfile.is_zipfile(infile_score_name)): (tmp_score_dir, score_file_list) = unzip_files(infile_score_name)
    else: score_file_list = [infile_score_name]

    # detect whether it's tabular or fasta format
    seq_method = ''
    test_file = score_file_list[0]
    test_fh = open(test_file,'r')
    while seq_method == '': 
        read_scorefile = test_fh.readline()
        if read_scorefile.startswith('#'):
            continue 
        elif read_scorefile.startswith(">"):
            seq_method = '454'
        else:
            seq_method = 'solexa'
    test_fh.close()
    
    # quantile array
    quality_score = {}
    
    # R
    score_points = []   
    score_matrix = []
    
    tmp_read_length = 0
    tmp_varied_length = False
    
    test_file = score_file_list[0]
    if (seq_method == 'solexa'):
        tmp_score = []
        for i, line in enumerate(open(test_file)):
            line = line.rstrip('\r\n')
            tmp_score = line.split('\t')
            if (tmp_read_length == 0): tmp_read_length = len(tmp_score)
            if (tmp_read_length != len(tmp_score)):
                tmp_varied_length = True
    else:    
        # skip the last fasta sequence
        tmp_score = ''
        for i, line in enumerate(open(test_file)):
            line = line.rstrip('\r\n')
            if line.startswith('>'):
                if len(tmp_score) > 0:
                    tmp_score = tmp_score.split()
                    if (tmp_read_length == 0): tmp_read_length = len(tmp_score)
                    if (tmp_read_length != len(tmp_score)):
                        tmp_varied_length = True
                tmp_score = ''
            else:
                tmp_score = tmp_score + ' ' + line
            
    if (tmp_varied_length): number_of_points = 20
    else: number_of_points = tmp_read_length
                        
    # data for R boxplot
    # data for quantile
    if (seq_method == 'solexa'):
        for score_file in score_file_list:
            for i, line in enumerate(open(score_file)):
                line = line.rstrip('\r\n')
                each_loc = line.split('\t')
                tmp_array = []
                for each_base in each_loc:
                    each_nuc_error = each_base.split()
                    each_nuc_error[0] = int(each_nuc_error[0])
                    each_nuc_error[1] = int(each_nuc_error[1])
                    each_nuc_error[2] = int(each_nuc_error[2])
                    each_nuc_error[3] = int(each_nuc_error[3])
                    big = max(each_nuc_error)
                    tmp_array.append(big)
                score_points.append(tmp_array)
                # quantile
                for j,k in enumerate(tmp_array):
                    if quality_score.has_key((j,k)):
                        quality_score[(j, k)] += 1
                    else:
                        quality_score[(j, k)] = 1
    else:
        tmp_score = ''
        for score_file in score_file_list:
            for i, line in enumerate(open(score_file)):
                if line.startswith('>'):
                    if len(tmp_score) > 0:
                        tmp_score = ['0'] + tmp_score.split()
                        read_length = len(tmp_score)
                        tmp_array = []
                        if (tmp_varied_length is False):
                            tmp_score.pop(0)
                            score_points.append(tmp_score)
                            tmp_array = tmp_score
                        elif (read_length > 100):
                            score_points_tmp = merge_to_20_datapoints(tmp_score)
                            score_points.append(score_points_tmp)
                            tmp_array = score_points_tmp
                        for j, k in enumerate(tmp_array):
                            if quality_score.has_key((j,k)):
                                quality_score[(j,k)] += 1
                            else:
                                quality_score[(j,k)] = 1
                    tmp_score = ''
                else:
                    tmp_score = tmp_score + ' ' + line
            if len(tmp_score) > 0:
                tmp_score = ['0'] + tmp_score.split()
                read_length = len(tmp_score)
                if (tmp_varied_length is False):
                    tmp_score.pop(0)
                    score_points.append(tmp_score)
                elif (read_length > 100):
                    score_points_tmp = merge_to_20_datapoints(tmp_score)
                    score_points.append(score_points_tmp)
                    tmp_array = score_points_tmp
                for j, k in enumerate(tmp_array):
                    if quality_score.has_key((j,k)):
                        quality_score[(j,k)] += 1
                    else:
                        quality_score[(j,k)] = 1

    
    """
    # quantile
    keys = quality_score.keys()
    keys.sort()
    for key in keys:
        print key, quality_score[key]
    """
    
    # reverse the matrix, for R
    tmp_array = []
    for i in range(number_of_points-1):
        for j in range(len(score_points)):
            tmp_array.append(int(score_points[j][i]))
        score_matrix.append(tmp_array)
        tmp_array = []

    # generate pdf figures
    outfile_R_pdf = outfile_R_name 
    r.pdf(outfile_R_pdf)
    
    title = "boxplot of quality scores"
    if (tmp_varied_length is False):
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

    if (os.path.isdir(tmp_score_dir)):
        for file_name in score_file_list:
            os.remove(file_name)
        os.removedirs(tmp_score_dir)

    r.quit(save = "no")

if __name__=="__main__":__main__()
