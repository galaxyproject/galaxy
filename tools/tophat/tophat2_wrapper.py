#!/usr/bin/env python
"""
 wrapper script for running Tophat2
"""

import sys, argparse, os, subprocess, shutil

def __main__():
    #Parse Command Line
    parser = argparse.ArgumentParser()

    parser.add_argument( '-p', '--pass_through', dest='pass_through_options', action='store', type=str, help='These options are passed through directly to Tophat2 without any modification.' )

 
    options = parser.parse_args()
    print options.pass_through_options
    cmd = options.pass_through_options

    print "Command:"
    print cmd

    try:
        subprocess.check_output(args=cmd, stderr=subprocess.STDOUT, shell=True)
    except subprocess.CalledProcessError, e:
        print "!!!!!!!!!!!!Tophat2 ERROR: stdout output:\n", e.output

if __name__=="__main__": __main__()



