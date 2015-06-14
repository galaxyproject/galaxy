#!/usr/bin/env python

### Wrapper for BreakDancer.
### All options are currently supported.
### This script currently hard codes the location of samtools. 

from argparse import ArgumentParser
import os
import logging
import subprocess

### Location of SAMTOOLS - HTSLIB. This is needed to run samtools stats.
SAMTOOLS = os.environ['SAMTOOLS_v020_EXE_PATH'] 

def bd_argparse():
    parser = ArgumentParser(description='Run BreakDancer')
    ### Required
    #parser.add_argument("--config_file", action="store", help="BreakDancer Analysis Config File", default="bd.config")

    ### Optional
    parser.add_argument("-o", action="store", help="operate on a single chromosome [all chromosomes]")
    parser.add_argument("-s", action="store", help="minimum length of a region", default=7)
    parser.add_argument("-c", action="store", help="cutoff in unit of standard deviation", default=3)
    parser.add_argument("-m", action="store", help="maximum SV size", default=1000000000)
    parser.add_argument("-q", help="minimum alternative mapping quality", action="store", default=35)
    parser.add_argument("-r", help="minimum number of read pairs required to establish a connection", action="store", default=2)
    parser.add_argument("-x", help="maximum threshold of haploid sequence coverage for regions to be ignored", action="store", default=1000)
    parser.add_argument("-b", help="buffer size for building connection", action="store", default=100)
    parser.add_argument("-t", help="only detect transchromosomal rearrangement", action="store_true", default=False)
    parser.add_argument("-d", help="prefix of fastq files that SV supporting reads will be saved by library", action="store")
    parser.add_argument("-g", help="dump SVs and supporting reads in BED format for GBrowse", action="store")
    parser.add_argument("-l", help="analyze Illumina long insert (mate-pair) library", action="store_true", default=False)
    parser.add_argument("-a", help="print out copy number and support reads per library rather than per bam", action="store_true", default=False)
    parser.add_argument("-f", help="print out Allele Frequency column", action="store_true", default=False)
    parser.add_argument("-y", help="output score filter", default=30)

    ### Wrapper arguments
    parser.add_argument("--input_tumor", help="Input Tumor BAM")
    parser.add_argument("--input_normal", help="Input Normal BAM")
    parser.add_argument("--output_file", action="store", help="Output Breakpoints", default="bd_out")
    parser.add_argument("--config_file", action="store", help="BreakDancer Analysis Config File", default="bd.config")

    # Process arguments
    args = parser.parse_args()
    
    return args


### Send the top 100,000 lines of a BAM file through Samtools to be processed for insert size stats.

def find_stats(bam_file):

    bam_stats = []

    cmd = SAMTOOLS + " view -bh " + bam_file + " | head -100000 | " + SAMTOOLS + " stats - | grep ^SN | cut -f 2- | grep 'insert size\|maximum length'"
    print(cmd)
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    while True:
        line = p.stdout.readline()
        print line
        if line != '':
            bam_stats.append(line.rstrip('\n').split('\t')[1])
        else:
            break

    return bam_stats

### Create the BreakDancer command.

def build_cmd(options, config):

    start_cmds = "breakdancer-max " + options['config_file']
    for arg, value in options.items():
        if arg == "f":
            start_cmds += " -h"
        elif value == True:
            start_cmds += " -" + arg
        elif value != None and value != False and arg != "config_file" and arg != 'input_tumor' and arg != 'input_normal' and arg != 'output_file':
            start_cmds += " -" + arg + " " + str(value)

    start_cmds += " > " + options['output_file']
    print(start_cmds)

    return start_cmds

### Run command.

def execute(cmd):
    logging.info("RUNNING: %s" % (cmd))
    print "running", cmd
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    stdout, stderr = p.communicate()
    if len(stderr):
        print stderr
    return p.returncode

### Create the config file that BreakDancer will need.

def writeTemp(outfile, normal_stats, tumor_stats, input_normal, input_tumor):

    outfile.write("map:" + input_tumor + "\tmean:" + tumor_stats[1] + "\tstd:" + tumor_stats[2] + "\treadlen:" + tumor_stats[0] + "\tsample:tumor\texe:samtools view\n")
    outfile.write("map:" + input_normal + "\tmean:" + normal_stats[1] + "\tstd:" + normal_stats[2] + "\treadlen:" + normal_stats[0] + "\tsample:normal\texe:samtools view\n")
    
    outfile.close()
    

def main():
    args = bd_argparse()
    normal_stats = find_stats(args.input_normal)
    print("Calculated Normal Stats.")
    tumor_stats = find_stats(args.input_tumor)
    print("Calculated Tumor Stats.")
    """
    print normal_stats
    print tumor_stats
    print tumor_stats[0]
    print tumor_stats[1]
    print tumor_stats[2]
    print normal_stats[0]
    print normal_stats[1]
    print normal_stats[2]
    """
    writeTemp(open(args.config_file, 'w'), normal_stats, tumor_stats, args.input_normal, args.input_tumor)
    print("Wrote Config File.")
    this_cmd = build_cmd(vars(args), args.config_file)
    execute(this_cmd)


if __name__ == "__main__":
    main()
