#!/usr/bin/env python
# Wrapper for oncotator v1.5.0.0

from argparse import ArgumentParser
import os
import sys
import tempfile
import shutil
import subprocess

def oncotator_argparse():
    parser = ArgumentParser(description='Run Oncotator')
    parser.add_argument("-v", "--verbose", dest="verbose", action="count", help="set verbosity level [default: 5]", default=5)
    parser.add_argument('-i', '--input_format', type=str, default="MAFLITE", choices=['VCF', 'SEG_FILE', 'MAFLITE'], help='Input format.  Note that MAFLITE will work for any tsv file with appropriate headers, so long as all of the required headers (or an alias -- see maflite.config) are present.  [default: %s]' % "MAFLITE")
    parser.add_argument('--db-dir', dest='db-dir', help='Main annotation database directory.')
    parser.add_argument('input_file', type=str, help='Input file to be annotated.  Type is specified through options.')
    parser.add_argument('output_file', type=str, help='Output file name of annotated file.')
    parser.add_argument('genome_build', metavar='genome_build', type=str, help="Genome build.  For example: hg19", choices=["hg19"])
    parser.add_argument('--skip-no-alt', dest="skip-no-alt", action='store_true', help="If specified, any mutation with annotation alt_allele_seen of 'False' will not be annotated or rendered.  Do not use if output format is a VCF.  If alt_allele_seen annotation is missing, render the mutation.")
    parser.add_argument('--prepend', dest="prepend", action='store_true', help="If specified for TCGAMAF output, will put a 'i_' in front of fields that are not directly rendered in Oncotator TCGA MAFs")
    parser.add_argument('--infer-onps', dest="infer-onps", action='store_true', help="Will merge adjacent SNPs,DNPs,TNPs,etc if they are in the same sample.  This assumes that the input file is position sorted.  This may cause problems with VCF -> VCF conversion, and does not guarantee input order is maintained.")
    parser.add_argument('-c', '--canonical-tx-file', dest="canonical-tx-file", type=str, help="Simple text file with list of transcript IDs (one per line) to always select where possible for variants.  Transcript IDs must match the ones used by the transcript provider in your datasource (e.g. gencode ENST00000123456).  If more than one transcript can be selected for a variant, uses the method defined by --tx-mode to break ties.  Using this list means that a transcript will be selected from this list first, possibly superseding a best-effect.  Note that transcript version number is not considered, whether included in the list or not.")

    # Process arguments
    args = parser.parse_args()
    
    return args

def create_opts(arg_dict):
    args = []
    flag_opts = set(('canonical-tx-file', 'skip-no-alt','prepend','infer-onps', 'input_format', 'db-dir'))
    wrapper_arguments = set(('input_file', 'output_file', 'genome_build'))
    for option, value in arg_dict.items():
        if option in wrapper_arguments:
            continue
        if (option in flag_opts):
            if value == True:
                args.append("--" + option)
            elif type(value) != bool and value != None:
                args.append("--" + option + " " + str(value))
    return " ".join(args)

def execute(options, input_file, output_file, build): 
    try:
        tmp_dir = tempfile.mkdtemp( dir='.' )
        tmp_file = tempfile.NamedTemporaryFile( dir=tmp_dir )
        tmp_file_name = tmp_file.name
        tmp_file.close()
        options_created = create_opts(options)
        command = 'oncotator -v --log_name /dev/null %s %s %s %s' % ( input_file, tmp_file_name, build, options_created )
        tmp = tempfile.NamedTemporaryFile( dir=tmp_dir ).name
        tmp_stderr = open( tmp, 'wb' )
        proc = subprocess.Popen( args=command, shell=True, cwd=tmp_dir, stderr=tmp_stderr.fileno() )
        returncode = proc.wait()
        tmp_stderr.close()
        # get stderr, allowing for case where it's very large
        tmp_stderr = open( tmp, 'rb' )
        stderr = ''
        buffsize = 1048576
        try:
            while True:
                stderr += tmp_stderr.read( buffsize )
                if not stderr or len( stderr ) % buffsize != 0:
                    break
        except OverflowError:
            pass
        tmp_stderr.close()
        if returncode != 0:
            raise Exception, stderr
    except Exception, e:
        #clean up temp files
        if os.path.exists( tmp_dir ):
            shutil.rmtree( tmp_dir )
        raise Exception, 'ERROR: Could not run oncotator tool!\n' + str( e )

    # Move tmp_file_name to our output dataset location
    shutil.move( tmp_file_name, output_file )
    #clean up temp files
    if os.path.exists( tmp_dir ):
        shutil.rmtree( tmp_dir )
    # check that there are results in the output file
    if os.path.getsize( output_file ) > 0:
        sys.stdout.write( 'Oncotator ran successfully.' )
    else:
        raise Exception, 'ERROR: Oncotator failed with errors!'

if __name__ == "__main__":
    args = oncotator_argparse()
    execute(vars(args), args.input_file, args.output_file, args.genome_build)
