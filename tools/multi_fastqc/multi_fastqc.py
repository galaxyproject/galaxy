# Visualize the output of FastQC for multiple samples

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
    parser.add_argument("-n", "--names", dest = "names", nargs = "+", type=str, required=True, default=None, help="Names to be displayed on legend.")
    parser.add_argument("-o1", "--output1", dest = "output1", required=True, type=str, default=None, help="Label Output File One")

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
    return file_dict

def plot_per_seq_quality(in_files, output, file_names):
    with PdfPages(output) as pdf:

        for i in range(0, len(in_files)):
            list_ = in_files[i].split('/')
            leg_name = file_names[i]
            f_dict = get_modules(in_files[i])
            arr_ = np.array(f_dict['Per sequence quality scores'])
            plt.plot(arr_[:,0], arr_[:,1], label=leg_name)
        plt.ylabel('Count')
        plt.xlabel('Mean Sequence Quality')
        plt.title('Per Sequence Quality Scores')
        ax = plt.subplot(111)
        box = ax.get_position()
        ax.set_position([box.x0, box.y0, box.width * 0.8, box.height])
        ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))
        pdf.savefig()
        plt.close()

if __name__ == "__main__":
    args = explorer_argparse()
    plot_per_seq_quality(vars(args)['input'], vars(args)['output1'], vars(args)['names'])
