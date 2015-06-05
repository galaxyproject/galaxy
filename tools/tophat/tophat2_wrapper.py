#!/usr/bin/env python
"""
 wrapper script for running Tophat2
"""

import sys, argparse, os, subprocess, shutil, tempfile


# replace the .dat suffix of a file created by Galaxy so it can be recognized
# by a tool such as Tophat
def replace_filename_suffix( work_dir, input_filename ):
    print 'input filename:' + input_filename
    output_filename = input_filename 
    # get the Galaxy filename without the path
    galaxy_filename_basename = os.path.basename(input_filename)
    # get the Galaxy filename suffix
    galaxy_filename_suffix = os.path.splitext(galaxy_filename_basename)[1]
    print 'file name suffix' + '[' + galaxy_filename_suffix + ']'
    # if the suffix is not .dat then assume the file has been directly supplied to Tophat
    # and Tophat can work with it as it normally would 
    if galaxy_filename_suffix != ".gz" and galaxy_filename_suffix != ".fq":
        # see if the input file has ben gzipped
        gunzip_test_cmd = "gunzip -t --suffix \"" + galaxy_filename_suffix + "\" " + input_filename 
        print 'gunzip cmd:' + gunzip_test_cmd      
        status =subprocess.call(args = gunzip_test_cmd, stderr=subprocess.STDOUT, shell=True)
        # if the file is a gzipped file then replace the .dat suffix with .fq.gz
        # use .fq as part of the suffix becuase we assume that only fasta files are provided
        # to Tophat
        print 'work dir:' + work_dir
        if status == 0:
           filename_suffix = ".fq.gz"       
        else:
           filename_suffix = ".fq"       
        # attach the new suffix to the original filename and create a new file name in a specified working directory
        output_filename = os.path.join( work_dir, "%s%s" % ( galaxy_filename_basename, filename_suffix ) )
        # create a symlink with the new file name to point to the original .dat input file for Tophat to use
        # the new file extensions will enable Tophat to process the file appropriately
        print "symlink " + input_filename  +  " " + output_filename
        os.symlink( os.path.abspath(input_filename), output_filename)

    print output_filename
    return output_filename           

def __main__():
    #Parse Command Line
    parser = argparse.ArgumentParser()

    parser.add_argument( '-p', '--pass_through', dest='pass_through_options', action='store', type=str, help='These options are passed through directly to Tophat2 without any modification.' )
    parser.add_argument( '--input_filename1', dest='input_filename1', action='store', type=str, help='Fastq input filename' )
    parser.add_argument( '--input_filename2', dest='input_filename2', action='store', type=str, help='Fastq input filename for reverse reads if available' )

 
    options = parser.parse_args()
    print options.pass_through_options
    cmd = options.pass_through_options

    # create a temporary working directory where we can put a symlink
    # to the real Galaxy input file which may not have the correct naming convention
    # for Tophat
    work_dir = tempfile.mkdtemp(dir="./", prefix="tophat2_work_")

    print options.input_filename1
    # remove quote characters and spaces from path filename 
    filename = options.input_filename1.translate(None, '" ')
    filename = replace_filename_suffix(work_dir, filename)
    print filename
    cmd = cmd + " " + filename

    if options.input_filename2 != 'None': 
       print options.input_filename2
       # remove quote characters and spaces from path filename 
       filename = options.input_filename2.translate(None, '" ')
       filename = replace_filename_suffix(work_dir, filename)
       print filename
       cmd = cmd + " " + filename

    print "Command:"
    print cmd

    try:
        subprocess.check_output(args=cmd, stderr=subprocess.STDOUT, shell=True)
    except subprocess.CalledProcessError, e:
        print "!!!!!!!!!!!!Tophat2 ERROR: stdout output:\n", e.output

    shutil.rmtree(work_dir)

if __name__=="__main__": __main__()



