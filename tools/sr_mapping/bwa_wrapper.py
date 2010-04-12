#!/usr/bin/env python

"""
Runs BWA on single-end or paired-end data.
Produces a SAM file containing the mappings.
Works with BWA version 0.5.3-0.5.5.

usage: bwa_wrapper.py [options]
    -t, --threads=t: The number of threads to use
    -r, --ref=r: The reference genome to use or index
    -f, --fastq=f: The (forward) fastq file to use for the mapping
    -F, --rfastq=F: The reverse fastq file to use for mapping if paired-end data
    -u, --output=u: The file to save the output (SAM format)
    -g, --genAlignType=g: The type of pairing (single or paired)
    -p, --params=p: Parameter setting to use (pre_set or full)
    -s, --fileSource=s: Whether to use a previously indexed reference sequence or one from history (indexed or history)
    -n, --maxEditDist=n: Maximum edit distance if integer
    -m, --fracMissingAligns=m: Fraction of missing alignments given 2% uniform base error rate if fraction
    -o, --maxGapOpens=o: Maximum number of gap opens
    -e, --maxGapExtens=e: Maximum number of gap extensions
    -d, --disallowLongDel=d: Disallow a long deletion within specified bps
    -i, --disallowIndel=i: Disallow indel within specified bps
    -l, --seed=l: Take the first specified subsequences
    -k, --maxEditDistSeed=k: Maximum edit distance to the seed
    -M, --mismatchPenalty=M: Mismatch penalty
    -O, --gapOpenPenalty=O: Gap open penalty
    -E, --gapExtensPenalty=E: Gap extension penalty
    -R, --suboptAlign=R: Proceed with suboptimal alignments even if the top hit is a repeat
    -N, --noIterSearch=N: Disable iterative search
    -T, --outputTopN=T: Output top specified hits
    -S, --maxInsertSize=S: Maximum insert size for a read pair to be considered mapped good
    -P, --maxOccurPairing=P: Maximum occurrences of a read for pairings
    -D, --dbkey=D: Dbkey for reference genome
    -H, --suppressHeader=h: Suppress header
"""

import optparse, os, shutil, subprocess, sys, tempfile

def stop_err( msg ):
    sys.stderr.write( '%s\n' % msg )
    sys.exit()

def __main__():
    #Parse Command Line
    parser = optparse.OptionParser()
    parser.add_option( '-t', '--threads', dest='threads', help='The number of threads to use' )
    parser.add_option( '-r', '--ref', dest='ref', help='The reference genome to use or index' )
    parser.add_option( '-f', '--fastq', dest='fastq', help='The (forward) fastq file to use for the mapping' )
    parser.add_option( '-F', '--rfastq', dest='rfastq', help='The reverse fastq file to use for mapping if paired-end data' )
    parser.add_option( '-u', '--output', dest='output', help='The file to save the output (SAM format)' )
    parser.add_option( '-g', '--genAlignType', dest='genAlignType', help='The type of pairing (single or paired)' )
    parser.add_option( '-p', '--params', dest='params', help='Parameter setting to use (pre_set or full)' )
    parser.add_option( '-s', '--fileSource', dest='fileSource', help='Whether to use a previously indexed reference sequence or one form history (indexed or history)' )
    parser.add_option( '-n', '--maxEditDist', dest='maxEditDist', help='Maximum edit distance if integer' )
    parser.add_option( '-m', '--fracMissingAligns', dest='fracMissingAligns', help='Fraction of missing alignments given 2% uniform base error rate if fraction' )
    parser.add_option( '-o', '--maxGapOpens', dest='maxGapOpens', help='Maximum number of gap opens' )
    parser.add_option( '-e', '--maxGapExtens', dest='maxGapExtens', help='Maximum number of gap extensions' )
    parser.add_option( '-d', '--disallowLongDel', dest='disallowLongDel', help='Disallow a long deletion within specified bps' )
    parser.add_option( '-i', '--disallowIndel', dest='disallowIndel', help='Disallow indel within specified bps' )
    parser.add_option( '-l', '--seed', dest='seed', help='Take the first specified subsequences' )
    parser.add_option( '-k', '--maxEditDistSeed', dest='maxEditDistSeed', help='Maximum edit distance to the seed' )
    parser.add_option( '-M', '--mismatchPenalty', dest='mismatchPenalty', help='Mismatch penalty' )
    parser.add_option( '-O', '--gapOpenPenalty', dest='gapOpenPenalty', help='Gap open penalty' )
    parser.add_option( '-E', '--gapExtensPenalty', dest='gapExtensPenalty', help='Gap extension penalty' )
    parser.add_option( '-R', '--suboptAlign', dest='suboptAlign', help='Proceed with suboptimal alignments even if the top hit is a repeat' )
    parser.add_option( '-N', '--noIterSearch', dest='noIterSearch', help='Disable iterative search' )
    parser.add_option( '-T', '--outputTopN', dest='outputTopN', help='Output top specified hits' )
    parser.add_option( '-S', '--maxInsertSize', dest='maxInsertSize', help='Maximum insert size for a read pair to be considered mapped good' )
    parser.add_option( '-P', '--maxOccurPairing', dest='maxOccurPairing', help='Maximum occurrences of a read for pairings' )
    parser.add_option( '-D', '--dbkey', dest='dbkey', help='Dbkey for reference genome' )
    parser.add_option( '-H', '--suppressHeader', dest='suppressHeader', help='Suppress header' )
    (options, args) = parser.parse_args()
    # make temp directory for placement of indices
    tmp_index_dir = tempfile.mkdtemp()
    tmp_dir = tempfile.mkdtemp()
    # index if necessary
    if options.fileSource == 'history':
        ref_file = tempfile.NamedTemporaryFile( dir=tmp_index_dir )
        ref_file_name = ref_file.name
        ref_file.close()
        os.symlink( options.ref, ref_file_name )
        # determine which indexing algorithm to use, based on size
        try:
            size = os.stat( options.ref ).st_size
            if size <= 2**30: 
                indexingAlg = 'is'
            else:
                indexingAlg = 'bwtsw'
        except:
            indexingAlg = 'is'
        indexing_cmds = '-a %s' % indexingAlg
        cmd1 = 'bwa index %s %s' % ( indexing_cmds, ref_file_name )
        try:
            tmp = tempfile.NamedTemporaryFile( dir=tmp_index_dir ).name
            tmp_stderr = open( tmp, 'wb' )
            proc = subprocess.Popen( args=cmd1, shell=True, cwd=tmp_index_dir, stderr=tmp_stderr.fileno() )
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
            # clean up temp dirs
            if os.path.exists( tmp_index_dir ):
                shutil.rmtree( tmp_index_dir )
            if os.path.exists( tmp_dir ):
                shutil.rmtree( tmp_dir )
            stop_err( 'Error indexing reference sequence. ' + str( e ) )
    else:
        ref_file_name = options.ref
    # set up aligning and generate aligning command options
    if options.params == 'pre_set':
        aligning_cmds = '-t %s' % options.threads
        gen_alignment_cmds = ''
    else:
        if options.maxEditDist != '0':
            editDist = options.maxEditDist
        else:
            editDist = options.fracMissingAligns
        if options.seed != '-1':
            seed = '-l %s' % options.seed
        else:
            seed = ''
        if options.suboptAlign == 'true':
            suboptAlign = '-R'
        else:
            suboptAlign = ''
        if options.noIterSearch == 'true':
            noIterSearch = '-N'
        else:
            noIterSearch = ''
        aligning_cmds = '-n %s -o %s -e %s -d %s -i %s %s -k %s -t %s -M %s -O %s -E %s %s %s' % \
                        ( editDist, options.maxGapOpens, options.maxGapExtens, options.disallowLongDel,
                          options.disallowIndel, seed, options.maxEditDistSeed, options.threads,
                          options.mismatchPenalty, options.gapOpenPenalty, options.gapExtensPenalty,
                          suboptAlign, noIterSearch )
        if options.genAlignType == 'single':
            gen_alignment_cmds = '-n %s' % options.outputTopN
        elif options.genAlignType == 'paired':
            gen_alignment_cmds = '-a %s -o %s' % ( options.maxInsertSize, options.maxOccurPairing )
    # set up output files
    tmp_align_out = tempfile.NamedTemporaryFile( dir=tmp_dir )
    tmp_align_out_name = tmp_align_out.name
    tmp_align_out.close()
    tmp_align_out2 = tempfile.NamedTemporaryFile( dir=tmp_dir )
    tmp_align_out2_name = tmp_align_out2.name
    tmp_align_out2.close()
    # prepare actual aligning and generate aligning commands
    cmd2 = 'bwa aln %s %s %s > %s' % ( aligning_cmds, ref_file_name, options.fastq, tmp_align_out_name )
    cmd2b = ''
    if options.genAlignType == 'paired':
        cmd2b = 'bwa aln %s %s %s > %s' % ( aligning_cmds, ref_file_name, options.rfastq, tmp_align_out2_name )
        cmd3 = 'bwa sampe %s %s %s %s %s %s >> %s' % ( gen_alignment_cmds, ref_file_name, tmp_align_out_name, tmp_align_out2_name, options.fastq, options.rfastq, options.output )
    else:
        cmd3 = 'bwa samse %s %s %s %s >> %s' % ( gen_alignment_cmds, ref_file_name, tmp_align_out_name, options.fastq, options.output )
    # perform alignments
    buffsize = 1048576
    try:
        # need to nest try-except in try-finally to handle 2.4
        try:
            # align
            try:
                tmp = tempfile.NamedTemporaryFile( dir=tmp_dir ).name
                tmp_stderr = open( tmp, 'wb' )
                proc = subprocess.Popen( args=cmd2, shell=True, cwd=tmp_dir, stderr=tmp_stderr.fileno() )
                returncode = proc.wait()
                tmp_stderr.close()
                # get stderr, allowing for case where it's very large
                tmp_stderr = open( tmp, 'rb' )
                stderr = ''
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
                raise Exception, 'Error aligning sequence. ' + str( e )
            # and again if paired data
            try:
                if cmd2b:
                    tmp = tempfile.NamedTemporaryFile( dir=tmp_dir ).name
                    tmp_stderr = open( tmp, 'wb' )
                    proc = subprocess.Popen( args=cmd2b, shell=True, cwd=tmp_dir, stderr=tmp_stderr.fileno() )
                    returncode = proc.wait()
                    tmp_stderr.close()
                    # get stderr, allowing for case where it's very large
                    tmp_stderr = open( tmp, 'rb' )
                    stderr = ''
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
                raise Exception, 'Error aligning second sequence. ' + str( e )
            # generate align
            try:
                tmp = tempfile.NamedTemporaryFile( dir=tmp_dir ).name
                tmp_stderr = open( tmp, 'wb' )
                proc = subprocess.Popen( args=cmd3, shell=True, cwd=tmp_dir, stderr=tmp_stderr.fileno() )
                returncode = proc.wait()
                tmp_stderr.close()
                # get stderr, allowing for case where it's very large
                tmp_stderr = open( tmp, 'rb' )
                stderr = ''
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
                raise Exception, 'Error generating alignments. ' + str( e ) 
            # remove header if necessary
            if options.suppressHeader == 'true':
                tmp_out = tempfile.NamedTemporaryFile( dir=tmp_dir)
                tmp_out_name = tmp_out.name
                tmp_out.close()
                try:
                    shutil.move( options.output, tmp_out_name )
                except Exception, e:
                    raise Exception, 'Error moving output file before removing headers. ' + str( e )
                fout = file( options.output, 'w' )
                for line in file( tmp_out.name, 'r' ):
                    if not ( line.startswith( '@HD' ) or line.startswith( '@SQ' ) or line.startswith( '@RG' ) or line.startswith( '@PG' ) or line.startswith( '@CO' ) ):
                        fout.write( line )
                fout.close()
            # check that there are results in the output file
            if os.path.getsize( options.output ) > 0:
                sys.stdout.write( 'BWA run on %s-end data' % options.genAlignType )
            else:
                raise Exception, 'The output file is empty. You may simply have no matches, or there may be an error with your input file or settings.'
        except Exception, e:
            stop_err( 'The alignment failed.\n' + str( e ) )
    finally:
        # clean up temp dir
        if os.path.exists( tmp_index_dir ):
            shutil.rmtree( tmp_index_dir )
        if os.path.exists( tmp_dir ):
            shutil.rmtree( tmp_dir )

if __name__=="__main__": __main__()
