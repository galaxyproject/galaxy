#!/usr/bin/env python
"""
 wrapper script for running application
"""

import sys, argparse, os, subprocess, shutil

def __main__():
    #Parse Command Line
    parser = argparse.ArgumentParser()

    parser.add_argument( '-p', '--pass_through', dest='pass_through_options', action='store', type=str, help='These options are passed through directly to the application without any modification.' )

    options = parser.parse_args()
    print options.pass_through_options
    cmd = options.pass_through_options


    print "Command:"
    print cmd

    try:
        subprocess.check_output(args=cmd, stderr=subprocess.STDOUT, shell=True)
    except subprocess.CalledProcessError, e:
        print "!!!!!!!!!!!!Cuffdiff ERROR: stdout output:\n", e.output


if __name__=="__main__": __main__()



