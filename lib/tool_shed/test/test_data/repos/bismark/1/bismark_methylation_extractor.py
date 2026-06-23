#!/usr/bin/env python

import argparse, os, shutil, subprocess, sys, tempfile, fileinput
import zipfile
from glob import glob

def stop_err( msg ):
    sys.stderr.write( "%s\n" % msg )
    sys.exit()

def zipper(dir, zip_file):
    zip = zipfile.ZipFile(zip_file, 'w', compression=zipfile.ZIP_DEFLATED)
    root_len = len(os.path.abspath(dir))
    for root, dirs, files in os.walk(dir):
        archive_root = os.path.abspath(root)[root_len:]
        for f in files:
            fullpath = os.path.join(root, f)
            archive_name = os.path.join(archive_root, f)
            zip.write(fullpath, archive_name, zipfile.ZIP_DEFLATED)
    zip.close()
    return zip_file

def __main__():
    #Parse Command Line
    parser = argparse.ArgumentParser(description='Wrapper for the bismark methylation caller.')

    # input options
    parser.add_argument( '--infile', help='Input file in SAM format.' )
    parser.add_argument( '--single-end', dest='single_end', action="store_true" )
    parser.add_argument( '--paired-end', dest='paired_end', action="store_true" )

    parser.add_argument( '--report-file', dest='report_file' )
    parser.add_argument( '--comprehensive', action="store_true" )
    parser.add_argument( '--merge-non-cpg', dest='merge_non_cpg', action="store_true" )
    parser.add_argument( '--no-overlap', dest='no_overlap', action="store_true" )
    parser.add_argument( '--compress' )
    parser.add_argument( '--ignore-bps', dest='ignore_bps', type=int )

    # OT - original top strand
    parser.add_argument( '--cpg_ot' )
    parser.add_argument( '--chg_ot' )
    parser.add_argument( '--chh_ot' )
    # CTOT - complementary to original top strand
    parser.add_argument( '--cpg_ctot' )
    parser.add_argument( '--chg_ctot' )
    parser.add_argument( '--chh_ctot' )
    # OB - original bottom strand
    parser.add_argument( '--cpg_ob' )
    parser.add_argument( '--chg_ob' )
    parser.add_argument( '--chh_ob' )
    # CTOT - complementary to original bottom strand
    parser.add_argument( '--cpg_ctob' )
    parser.add_argument( '--chg_ctob' )
    parser.add_argument( '--chh_ctob' )

    parser.add_argument( '--cpg_context' )
    parser.add_argument( '--chg_context' )
    parser.add_argument( '--chh_context' )

    parser.add_argument( '--non_cpg_context' )

    parser.add_argument( '--non_cpg_context_ot' )
    parser.add_argument( '--non_cpg_context_ctot' )
    parser.add_argument( '--non_cpg_context_ob' )
    parser.add_argument( '--non_cpg_context_ctob' )

    args = parser.parse_args()


    # Build methylation extractor command
    output_dir = tempfile.mkdtemp()
    cmd = 'bismark_methylation_extractor --no_header -o %s %s %s'

    additional_opts = ''
    # Set up all options
    if args.single_end:
        additional_opts += ' --single-end '
    else:
        additional_opts += ' --paired-end '
    if args.no_overlap:
        additional_opts += ' --no_overlap '
    if args.ignore_bps:
        additional_opts += ' --ignore %s ' % args.ignore_bps
    if args.comprehensive:
        additional_opts += ' --comprehensive '
    if args.merge_non_cpg:
        additional_opts += ' --merge_non_CpG '
    if args.report_file:
        additional_opts += ' --report '


    # Final command:
    cmd = cmd % (output_dir, additional_opts, args.infile)

    # Run
    try:
        tmp_out = tempfile.NamedTemporaryFile().name
        tmp_stdout = open( tmp_out, 'wb' )
        tmp_err = tempfile.NamedTemporaryFile().name
        tmp_stderr = open( tmp_err, 'wb' )
        proc = subprocess.Popen( args=cmd, shell=True, cwd=".", stdout=tmp_stdout, stderr=tmp_stderr )
        returncode = proc.wait()
        tmp_stderr.close()
        # get stderr, allowing for case where it's very large
        tmp_stderr = open( tmp_err, 'rb' )
        stderr = ''
        buffsize = 1048576
        try:
            while True:
                stderr += tmp_stderr.read( buffsize )
                if not stderr or len( stderr ) % buffsize != 0:
                    break
        except OverflowError:
            pass
        tmp_stdout.close()
        tmp_stderr.close()
        if returncode != 0:
            raise Exception, stderr
            
        # TODO: look for errors in program output.
    except Exception, e:
        stop_err( 'Error in bismark methylation extractor:\n' + str( e ) ) 


    # collect and copy output files

    if args.compress:
        zipper(output_dir, args.compress)


    if args.cpg_ot:
        shutil.move( glob(os.path.join( output_dir, '*CpG_OT_*'))[0], args.cpg_ot )
    if args.chg_ot:
        shutil.move( glob(os.path.join( output_dir, '*CHG_OT_*'))[0], args.chg_ot )
    if args.chh_ot:
        shutil.move( glob(os.path.join( output_dir, '*CHH_OT_*'))[0], args.chh_ot )
    if args.cpg_ctot:
        shutil.move( glob(os.path.join( output_dir, '*CpG_CTOT_*'))[0], args.cpg_ctot )
    if args.chg_ctot:
        shutil.move( glob(os.path.join( output_dir, '*CHG_CTOT_*'))[0], args.chg_ctot )
    if args.chh_ctot:
        shutil.move( glob(os.path.join( output_dir, '*CHH_CTOT_*'))[0], args.chh_ctot )
    if args.cpg_ob:
        shutil.move( glob(os.path.join( output_dir, '*CpG_OB_*'))[0], args.cpg_ob )
    if args.chg_ob:
        shutil.move( glob(os.path.join( output_dir, '*CHG_OB_*'))[0], args.chg_ob )
    if args.chh_ob:
        shutil.move( glob(os.path.join( output_dir, '*CHH_OB_*'))[0], args.chh_ob )
    if args.cpg_ctob:
        shutil.move( glob(os.path.join( output_dir, '*CpG_CTOB_*'))[0], args.cpg_ctob )
    if args.chg_ctob:
        shutil.move( glob(os.path.join( output_dir, '*CHG_CTOB_*'))[0], args.chg_ctob )
    if args.chh_ctob:
        shutil.move( glob(os.path.join( output_dir, '*CHH_CTOB_*'))[0], args.chh_ctob )

    # context-dependent methylation output files
    if args.cpg_context:
        shutil.move( glob(os.path.join( output_dir, '*CpG_context_*'))[0], args.cpg_context )
    if args.chg_context:
        shutil.move( glob(os.path.join( output_dir, '*CHG_context_*'))[0], args.chg_context )
    if args.chh_context:
        shutil.move( glob(os.path.join( output_dir, '*CHH_context_*'))[0], args.chh_context )

    if args.non_cpg_context:
        shutil.move( glob(os.path.join( output_dir, '*Non_CpG_context_*'))[0], args.non_cpg_context )

    if args.non_cpg_context_ot:
        shutil.move( glob(os.path.join( output_dir, '*Non_CpG_OT_*'))[0], args.non_cpg_context_ot )
    if args.non_cpg_context_ctot:
        shutil.move( glob(os.path.join( output_dir, '*Non_CpG_CTOT_*'))[0], args.non_cpg_context_ctot )
    if args.non_cpg_context_ob:
        shutil.move( glob(os.path.join( output_dir, '*Non_CpG_OB_*'))[0], args.non_cpg_context_ob )
    if args.non_cpg_context_ctob:
        shutil.move( glob(os.path.join( output_dir, '*Non_CpG_CTOB_*'))[0], args.non_cpg_context_ctob )



    if args.report_file:
        shutil.move( glob(os.path.join( output_dir, '*_splitting_report*'))[0], args.report_file )


    # Clean up temp dirs
    if os.path.exists( output_dir ):
        shutil.rmtree( output_dir )

if __name__=="__main__": __main__()
