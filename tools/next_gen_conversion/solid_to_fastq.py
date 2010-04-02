#!/usr/bin/env python

"""
Converts SOLiD data to Sanger FASTQ format.

usage: %prog [options]
   -i, --input1=i: Forward reads file
   -q, --input2=q: Forward qual file
   -I, --input3=I: Reverse reads file
   -Q, --input4=Q: Reverse qual file
   -o, --output1=o: Forward output
   -r, --output2=r: Reverse output

usage: %prog forward_reads_file forwards_qual_file reverse_reads_file(or_None) reverse_qual_file(or_None) output_file ouptut_id output_dir
"""

import os, sys, tempfile
from galaxy import eggs
import pkg_resources; pkg_resources.require( "bx-python" )
from bx.cookbook import doc_optparse

def stop_err( msg ):
    sys.stderr.write( "%s\n" % msg )
    sys.exit()
    
def replaceNeg1(fin, fout):
    line = fin.readline()
    while line.strip():
        fout.write(line.replace('-1', '1'))
        line = fin.readline()
    fout.seek(0)
    return fout
 
def __main__():
    #Parse Command Line
    options, args = doc_optparse.parse( __doc__ )
    # common temp file setup
    tmpf = tempfile.NamedTemporaryFile()    #forward reads
    tmpqf = tempfile.NamedTemporaryFile()
    tmpqf = replaceNeg1(file(options.input2,'r'), tmpqf)
    # if paired-end data (have reverse input files)
    if options.input3 != "None" and options.input4 != "None":
        tmpr = tempfile.NamedTemporaryFile()    #reverse reads
        # replace the -1 in the qualities file 
        tmpqr = tempfile.NamedTemporaryFile()
        tmpqr = replaceNeg1(file(options.input4,'r'), tmpqr)
        cmd1 = "%s/bwa_solid2fastq_modified.pl 'yes' %s %s %s %s %s %s 2>&1" %(os.path.split(sys.argv[0])[0], tmpf.name, tmpr.name, options.input1, tmpqf.name, options.input3, tmpqr.name)
        try:
            os.system(cmd1)
            os.system('gunzip -c %s >> %s' %(tmpf.name,options.output1))
            os.system('gunzip -c %s >> %s' %(tmpr.name,options.output2))
        except Exception, eq:
            stop_err("Error converting data to fastq format.\n" + str(eq))
        tmpr.close()
        tmpqr.close()
    # if single-end data
    else:
        cmd1 = "%s/bwa_solid2fastq_modified.pl 'no' %s %s %s %s %s %s 2>&1" % (os.path.split(sys.argv[0])[0], tmpf.name, None, options.input1, tmpqf.name, None, None)
        try:
            os.system(cmd1)
            os.system('gunzip -c %s >> %s' % (tmpf.name, options.output1))
        except Exception, eq:
            stop_err("Error converting data to fastq format.\n" + str(eq))
    tmpqf.close()
    tmpf.close()
    sys.stdout.write('converted SOLiD data')

if __name__=="__main__": __main__()
