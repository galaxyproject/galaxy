#!/usr/bin/env python

"""
Runs SRMA on a SAM/BAM file;
TODO: more documentation

usage: srma_wrapper.py [options]

See below for options
"""

import optparse, os, shutil, subprocess, sys, tempfile

def stop_err( msg ):
    sys.stderr.write( '%s\n' % msg )
    sys.exit()

def parseRefLoc( refLoc, refUID ):
    for line in open( refLoc ):
        if not line.startswith( '#' ):
            fields = line.strip().split( '\t' )
            if len( fields ) >= 3:
                if fields[0] == refUID:
                    return fields[1]
    return None

def __main__():
    #Parse Command Line
    parser = optparse.OptionParser()
    parser.add_option( '-r', '--ref', dest='ref', help='The reference genome to index and use' )
    parser.add_option( '-u', '--refUID', dest='refUID', help='The pre-index reference genome unique Identifier' )
    #parser.add_option( '-L', '--refLocations', dest='refLocations', help='The filepath to the srma indices location file' )
    parser.add_option( '-i', '--input', dest='input', help='The SAM/BAM input file' )
    parser.add_option( '-I', '--inputIndex', dest='inputIndex', help='The SAM/BAM input index file' )
    parser.add_option( '-o', '--output', dest='output', help='The SAM/BAM output file' )
    parser.add_option( '-O', '--offset', dest='offset', help='The alignment offset' )
    parser.add_option( '-Q', '--minMappingQuality', dest='minMappingQuality', help='The minimum mapping quality' )
    parser.add_option( '-P', '--minAlleleProbability', dest='minAlleleProbability', help='The minimum allele probability conditioned on coverage (for the binomial quantile).' )
    parser.add_option( '-C', '--minAlleleCoverage', dest='minAlleleCoverage', help='The minimum haploid coverage for the consensus' )
    parser.add_option( '-R', '--range', dest='range', help='A range to examine' )
    parser.add_option( '-c', '--correctBases', dest='correctBases', help='Correct bases ' )
    parser.add_option( '-q', '--useSequenceQualities', dest='useSequenceQualities', help='Use sequence qualities ' )
    parser.add_option( '-M', '--maxHeapSize', dest='maxHeapSize', help='The maximum number of nodes on the heap before re-alignment is ignored' )
    parser.add_option( '-s', '--fileSource', dest='fileSource', help='Whether to use a previously indexed reference sequence or one from history (indexed or history)' )
    parser.add_option( '-p', '--params', dest='params', help='Parameter setting to use (pre_set or full)' )
    parser.add_option( '-j', '--jarBin', dest='jarBin', default='', help='The path to where jars are stored' )
    parser.add_option( '-f', '--jarFile', dest='jarFile', help='The file name of the jar file to use')
    (options, args) = parser.parse_args()

    # make temp directory for srma
    tmp_dir = tempfile.mkdtemp()
    buffsize = 1048576

    # set up reference filenames
    reference_filepath_name = None
    # need to create SRMA dict and Samtools fai files for custom genome
    if options.fileSource == 'history':
        try:
            reference_filepath = tempfile.NamedTemporaryFile( dir=tmp_dir, suffix='.fa' )
            reference_filepath_name = reference_filepath.name
            reference_filepath.close()
            fai_filepath_name = '%s.fai' % reference_filepath_name
            dict_filepath_name = reference_filepath_name.replace( '.fa', '.dict' )
            os.symlink( options.ref, reference_filepath_name )
            # create fai file using Samtools
            index_fai_cmd = 'samtools faidx %s' % reference_filepath_name
            try:
                tmp = tempfile.NamedTemporaryFile( dir=tmp_dir ).name
                tmp_stderr = open( tmp, 'wb' )
                proc = subprocess.Popen( args=index_fai_cmd, shell=True, cwd=tmp_dir, stderr=tmp_stderr.fileno() )
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
                # clean up temp dir
                if os.path.exists( tmp_dir ):
                    shutil.rmtree( tmp_dir )
                stop_err( 'Error creating Samtools index for custom genome file: %s\n' % str( e ) )
            # create dict file using SRMA
            dict_cmd = 'java -cp "%s" net.sf.picard.sam.CreateSequenceDictionary R=%s O=%s' % ( os.path.join( options.jarBin, options.jarFile ), reference_filepath_name, dict_filepath_name )
            try:
                tmp = tempfile.NamedTemporaryFile( dir=tmp_dir ).name
                tmp_stderr = open( tmp, 'wb' )
                proc = subprocess.Popen( args=dict_cmd, shell=True, cwd=tmp_dir, stderr=tmp_stderr.fileno() )
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
                # clean up temp dir
                if os.path.exists( tmp_dir ):
                    shutil.rmtree( tmp_dir )
                stop_err( 'Error creating index for custom genome file: %s\n' % str( e ) )
        except Exception, e:
            # clean up temp dir
            if os.path.exists( tmp_dir ):
                shutil.rmtree( tmp_dir )
            stop_err( 'Problem handling SRMA index (dict file) for custom genome file: %s\n' % str( e ) )
    # using built-in dict/index files
    else:
        if options.ref:
            reference_filepath_name = options.ref
        else:
            reference_filepath_name = parseRefLoc( options.refLocation, options.refUID )
    if reference_filepath_name is None:
        raise ValueError( 'A valid genome reference was not provided.' )

    # set up aligning and generate aligning command options
    if options.params == 'pre_set':
        srma_cmds = ''
    else:
        if options.useSequenceQualities == 'true':
            useSequenceQualities = 'true'
        else:
            useSequenceQualities = 'false'
        ranges = 'null'
        if options.range == 'None':
            range = 'null'
        else:
            range = options.range
        srma_cmds = "OFFSET=%s MIN_MAPQ=%s MINIMUM_ALLELE_PROBABILITY=%s MINIMUM_ALLELE_COVERAGE=%s RANGES=%s RANGE=%s CORRECT_BASES=%s USE_SEQUENCE_QUALITIES=%s MAX_HEAP_SIZE=%s" % ( options.offset, options.minMappingQuality, options.minAlleleProbability, options.minAlleleCoverage, ranges, range, options.correctBases, options.useSequenceQualities, options.maxHeapSize )

    # perform alignments
    buffsize = 1048576
    try:
        #symlink input bam and index files due to the naming conventions required by srma here
        input_bam_filename = os.path.join( tmp_dir, '%s.bam' % os.path.split( options.input )[-1] )
        os.symlink( options.input, input_bam_filename )
        input_bai_filename = "%s.bai" % os.path.splitext( input_bam_filename )[0]
        os.symlink( options.inputIndex, input_bai_filename )

        #create a temp output name, ending in .bam due to required naming conventions? unkown if required
        output_bam_filename = os.path.join( tmp_dir, "%s.bam" % os.path.split( options.output )[-1] )
        # generate commandline
        cmd = 'java -jar %s I=%s O=%s R=%s %s' % ( os.path.join( options.jarBin, options.jarFile ), input_bam_filename, output_bam_filename, reference_filepath_name, srma_cmds )

        # need to nest try-except in try-finally to handle 2.4
        try:
            try:
                tmp = tempfile.NamedTemporaryFile( dir=tmp_dir ).name
                tmp_stderr = open( tmp, 'wb' )
                proc = subprocess.Popen( args=cmd, shell=True, cwd=tmp_dir, stderr=tmp_stderr.fileno() )
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
                raise Exception, 'Error executing SRMA. ' + str( e )
            # move file from temp location (with .bam name) to provided path
            shutil.move( output_bam_filename, options.output )
            # check that there are results in the output file
            if os.path.getsize( options.output ) <= 0:
                raise Exception, 'The output file is empty. You may simply have no matches, or there may be an error with your input file or settings.'
        except Exception, e:
            stop_err( 'The re-alignment failed.\n' + str( e ) )
    finally:
        # clean up temp dir
        if os.path.exists( tmp_dir ):
            shutil.rmtree( tmp_dir )

if __name__=="__main__": __main__()
