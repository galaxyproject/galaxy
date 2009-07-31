#! /usr/bin/python

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
 
def __main__():
    #Parse Command Line
    options, args = doc_optparse.parse( __doc__ )
    # if paired-end data (have reverse input files)
    if options.input3 != "None" and options.input4 != "None":
        tmpf = tempfile.NamedTemporaryFile()    #forward reads
        tmpr = tempfile.NamedTemporaryFile()    #reverse reads

        cmd1 = "bwa_solid2fastq_modified.pl 'yes' %s %s %s %s %s %s %s 2>&1" %(tmpf.name,tmpr.name,None,options.input1,options.input2,options.input3,options.input4)
        try:
            os.system(cmd1)
            os.system('gunzip -c %s >> %s' %(tmpf.name,options.output1))
            os.system('gunzip -c %s >> %s' %(tmpr.name,options.output2))

        except Exception, eq:
            stop_err("Error converting data to fastq format.\n" + str(eq))
    # if single-end data
    else:
        tmpf = tempfile.NamedTemporaryFile()   
        cmd1 = "bwa_solid2fastq_modified.pl 'no' %s %s %s %s %s %s %s 2>&1" % (tmpf.name, None, None, options.input1, options.input2, None, None)
        try:
            os.system(cmd1)
            os.system('gunzip -c %s >> %s' % (tmpf.name, options.output1))
            tmpf.close()
        except Exception, eq:
            stop_err("Error converting data to fastq format.\n" + str(eq))        

if __name__=="__main__": __main__()
