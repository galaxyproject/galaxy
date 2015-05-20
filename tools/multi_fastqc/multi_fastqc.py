# wrapper for RNASeq Explorer
import os
from argparse import ArgumentParser
import pandas as pd
import subprocess
import logging
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_pdf import PdfPages

def explorer_argparse():
    
    parser = ArgumentParser(description='RNASeq Explorer: Gene Expression vs Drug Resistance')
    parser.add_argument("-i", "--input", dest = "input", nargs = "+", type=str, required=True, default=None, help="List of fastqc_data.txt files.")
    parser.add_argument("-o1", "--output1", dest = "output1", required=True, type=str, default=None, help="Label Output File One")
    # parser.add_argument("-o2", "--output2", dest = "output2", required=True, type=str, default=None, help="Label Output File Two")

    args = parser.parse_args()
    
    return args

def get_modules(sing_file):
    file_dict = {}
    with open(sing_file) as f:  
        this_mod = ''
        for line in f.readlines():
            line = line.strip() # trim endline
            if (line[:2] == ">>" and line[:12] != ">>END_MODULE"): # for each module grab summary data
                module = line[2:-5] # grab module name
                status = line[-4:] # and overall status pass/warn/fail
                if module not in file_dict:
                    file_dict[module] = []
                    this_mod = module
            # removing headers
            elif (line[:2] != ">>" and line[:1] != "#"): # grab details under each module
                cols = line.split('\t')
                file_dict[this_mod].append(cols)
                #file_dict[this_mod] = file_dict[this_mod] + line + '\n'
    return file_dict

def plot_per_seq_quality(in_files, output):
    with PdfPages(output) as pdf:
        for input_f in in_files:
            list_ = input_f.split('/')
            leg_name = list_[len(list_)-1][:-4]
            f_dict = get_modules(input_f)
            arr_ = np.array(f_dict['Per sequence quality scores'])
            plt.plot(arr_[:,0], arr_[:,1], label=leg_name)
        plt.legend(loc='upper left')
        plt.ylabel('Count')
        plt.xlabel('Mean Sequence Quality')
        plt.title('Per Sequence Quality Scores')
        pdf.savefig()
        plt.close()

if __name__ == "__main__":
    args = explorer_argparse()
    plot_per_seq_quality(vars(args)['input'], vars(args)['output1'])
