#! /usr/bin/python

import os, sys, math, tempfile, zipfile, re
from rpy import *

assert sys.version_info[:2] >= (2.4)

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



def __main__():

    # I/O
    infile_score_name = sys.argv[1].strip()
    outfile_R_name = sys.argv[2].strip()
    
    try:
        score_threshold = int(sys.argv[3].strip())
    except:
        stop_err('Please enter a threshold for quality score.')
        
    # unzip infile
    if (zipfile.is_zipfile(infile_score_name)): 
        unzip_infile = unzip(infile_score_name)
    else: unzip_infile = infile_score_name

    # detect whether it's tabular or fasta format
    seq_method = None
    score_file = unzip_infile
    test_fh = open(score_file,'r')
    while seq_method is None: 
        read_scorefile = test_fh.readline()
        if read_scorefile.startswith('#'):
            continue 
        if not read_scorefile:
            continue
        elif read_scorefile.startswith(">"):
            read_next_line = test_fh.readline()
            fields = read_next_line.split()
            for score in fields:
                try: 
                    int(score)
                    seq_method = '454'
                except:
                    seq_method = 'Failed'
                    break
        elif len(read_scorefile.split('\t')) > 0:
            fields = read_scorefile.split()
            for score in fields:
                try:
                    int(score)
                    seq_method = 'solexa'
                except:
                    seq_method = 'Failed'
                    break
        else:
            stop_err('Your input file format does not fit the requirement. Please use either fasta format or tabular format')
            
    if seq_method == 'Failed':
        stop_err('Unable to determine the file format. Please use either fasta-like format (except title lines, the file contains only numeric values) or tabular format')
        
    test_fh.close()
    
        
    # R   
    cont_high_quality = []
    
    invalid_lines = 0
    invalid_scores = 0
                               
    if (seq_method == 'solexa'):
            for i, line in enumerate(open(score_file)):

                line = line.rstrip('\r\n')
                if line.startswith('#'):
                    continue
                if not line:
                    continue
                
                each_loc = line.split('\t')
                
                for j, each_base in enumerate(each_loc):
                    each_nuc_error = each_base.split()
                    
                    try:
                        each_nuc_error[0] = int(each_nuc_error[0])
                        each_nuc_error[1] = int(each_nuc_error[1])
                        each_nuc_error[2] = int(each_nuc_error[2])
                        each_nuc_error[3] = int(each_nuc_error[3])
                        big = max(each_nuc_error)
                    except:
                        invalid_scores += 1
                        big = 0
                        
                    if j == 0:
                        cont_high_quality.append(1)
                    else:
                        if big >= score_threshold:
                            cont_high_quality[len(cont_high_quality)-1] += 1
                        else:
                            cont_high_quality.append(1)
    else:
            tmp_score = ''
            for i, line in enumerate(open(score_file)):
                if line.startswith('#'):
                    continue
                if not line:
                    continue
                if line.startswith('>'):
                    if len(tmp_score) > 0:
                        each_loc = tmp_score.split()
                        for j, each_base in enumerate(each_loc):
                            try:
                                each_base = int(each_base)
                            except:
                                invalid_scores += 1
                                each_base = 0
                            if j == 0:
                                cont_high_quality.append(1)
                            else:
                                if each_base >= score_threshold:
                                    cont_high_quality[len(cont_high_quality)-1] += 1
                                else:
                                    cont_high_quality.append(1)
                    tmp_score = ''
                else:
                    tmp_score = tmp_score + ' ' + line
                    
            if len(tmp_score) > 0:
                each_loc = tmp_score.split()
                for j, each_base in enumerate(each_loc):
                    try:
                        each_base = int(each_base)
                    except:
                        invalid_scores += 1
                        each_base = 0
                    if j == 0:
                        cont_high_quality.append(1)
                    else:
                        if each_base >= score_threshold:
                            cont_high_quality[len(cont_high_quality)-1] += 1
                        else:
                            cont_high_quality.append(1)
    
    # throw messages of invalid values
    if invalid_lines > 0: 
        print 'Skipped %d lines due to invalid format' %(invalid_lines)
    if invalid_scores > 0:
        print 'Skipped %d scores due to invalid values' %(invalid_scores)
               
    # generate pdf figures
    cont_high_quality = array (cont_high_quality)
    
    outfile_R_pdf = outfile_R_name 
    r.pdf(outfile_R_pdf)
    
    title = "histogram of continueous high quality scores"
    xlim_range = [1,max(cont_high_quality)]
    nclass = max(cont_high_quality)
    if nclass > 100: nclass = 100
    r.hist(cont_high_quality,probability=True, xlab="Continueous High Quality Score length (bp)", ylab="Frequency (%)", xlim=xlim_range, main=title, nclass=nclass)
    
    if zipfile.is_zipfile(infile_score_name) and os.path.exists(unzip_infile):
        os.remove(unzip_infile)
        
    r.dev_off()    
    r.quit(save = "no")

if __name__=="__main__":__main__()
