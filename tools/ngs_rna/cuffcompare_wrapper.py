#!/usr/bin/env python

import optparse, os, shutil, subprocess, sys, tempfile

def stop_err( msg ):
    sys.stderr.write( '%s\n' % msg )
    sys.exit()

# Copied from sam_to_bam.py:
def check_seq_file( dbkey, cached_seqs_pointer_file ):
    seq_path = ''
    for line in open( cached_seqs_pointer_file ):
        line = line.rstrip( '\r\n' )
        if line and not line.startswith( '#' ) and line.startswith( 'index' ):
            fields = line.split( '\t' )
            if len( fields ) < 3:
                continue
            if fields[1] == dbkey:
                seq_path = fields[2].strip()
                break
    return seq_path

def __main__():
    #Parse Command Line
    parser = optparse.OptionParser()
    parser.add_option( '-r', dest='ref_annotation', help='An optional "reference" annotation GTF. Each sample is matched against this file, and sample isoforms are tagged as overlapping, matching, or novel where appropriate. See the refmap and tmap output file descriptions below.' )
    parser.add_option( '-R', action="store_true", dest='ignore_nonoverlap', help='If -r was specified, this option causes cuffcompare to ignore reference transcripts that are not overlapped by any transcript in one of cuff1.gtf,...,cuffN.gtf. Useful for ignoring annotated transcripts that are not present in your RNA-Seq samples and thus adjusting the "sensitivity" calculation in the accuracy report written in the transcripts accuracy file' )
    parser.add_option( '-s', dest='use_seq_data', action="store_true", help='Causes cuffcompare to look into for fasta files with the underlying genomic sequences (one file per contig) against which your reads were aligned for some optional classification functions. For example, Cufflinks transcripts consisting mostly of lower-case bases are classified as repeats. Note that <seq_dir> must contain one fasta file per reference chromosome, and each file must be named after the chromosome, and have a .fa or .fasta extension.')
    
    # Wrapper / Galaxy options.
    parser.add_option( '', '--dbkey', dest='dbkey', help='The build of the reference dataset' )
    parser.add_option( '', '--index_dir', dest='index_dir', help='GALAXY_DATA_INDEX_DIR' )
    parser.add_option( '', '--ref_file', dest='ref_file', help='The reference dataset from the history' )
    
    # Outputs.
    parser.add_option( '', '--combined-transcripts', dest='combined_transcripts' )
    
    (options, args) = parser.parse_args()
    
    # output version # of tool
    try:
        tmp = tempfile.NamedTemporaryFile().name
        tmp_stdout = open( tmp, 'wb' )
        proc = subprocess.Popen( args='cuffcompare 2>&1', shell=True, stdout=tmp_stdout )
        tmp_stdout.close()
        returncode = proc.wait()
        stdout = None
        for line in open( tmp_stdout.name, 'rb' ):
            if line.lower().find( 'cuffcompare v' ) >= 0:
                stdout = line.strip()
                break
        if stdout:
            sys.stdout.write( '%s\n' % stdout )
        else:
            raise Exception
    except:
        sys.stdout.write( 'Could not determine Cuffcompare version\n' )
        
    # Set/link to sequence file.
    if options.use_seq_data:
        if options.ref_file != 'None':
            # Sequence data from history.
            # Create symbolic link to ref_file so that index will be created in working directory.
            seq_path = "ref.fa"
            os.symlink( options.ref_file, seq_path  )
        else:
            # Sequence data from loc file.
            cached_seqs_pointer_file = os.path.join( options.index_dir, 'sam_fa_indices.loc' )
            if not os.path.exists( cached_seqs_pointer_file ):
                stop_err( 'The required file (%s) does not exist.' % cached_seqs_pointer_file )
            # If found for the dbkey, seq_path will look something like /galaxy/data/equCab2/sam_index/equCab2.fa,
            # and the equCab2.fa file will contain fasta sequences.
            seq_path = check_seq_file( options.dbkey, cached_seqs_pointer_file )
            if seq_path == '':
                stop_err( 'No sequence data found for dbkey %s, so sequence data cannot be used.' % options.dbkey  )
    
    # Build command.
    
    # Base.
    cmd = "cuffcompare -o cc_output "
    
    # Add options.
    if options.ref_annotation:
        cmd += " -r %s " % options.ref_annotation
    if options.ignore_nonoverlap:
        cmd += " -R "
    if options.use_seq_data:
        cmd += " -s %s " % seq_path
        
    # Add input files.
        
    # Need to symlink inputs so that output files are written to temp directory.
    for i, arg in enumerate( args ):
        input_file_name = "./input%i" % ( i+1 )
        os.symlink( arg, input_file_name )
        cmd += "%s " % input_file_name

    # Debugging.
    print cmd
    
    # Run command.
    try:        
        tmp_name = tempfile.NamedTemporaryFile( dir="." ).name
        tmp_stderr = open( tmp_name, 'wb' )
        proc = subprocess.Popen( args=cmd, shell=True, stderr=tmp_stderr.fileno() )
        returncode = proc.wait()
        tmp_stderr.close()
        
        # Get stderr, allowing for case where it's very large.
        tmp_stderr = open( tmp_name, 'rb' )
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
        
        # Error checking.
        if returncode != 0:
            raise Exception, stderr
            
        # Copy outputs.
        shutil.copyfile( "cc_output.combined.gtf" , options.combined_transcripts )    
            
        # check that there are results in the output file
        cc_output_fname = "cc_output.stats"
        if len( open( cc_output_fname, 'rb' ).read().strip() ) == 0:
            raise Exception, 'The main output file is empty, there may be an error with your input file or settings.'
    except Exception, e:
        stop_err( 'Error running cuffcompare. ' + str( e ) )
        
if __name__=="__main__": __main__()
