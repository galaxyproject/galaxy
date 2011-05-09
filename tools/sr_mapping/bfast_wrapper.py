#!/usr/bin/env python

"""
Runs BFAST on single-end or paired-end data.
TODO: more documentation

TODO: 
    - auto-detect gzip or bz2
    - split options (?)
    - queue lengths (?)
    - assumes reference always has been indexed
    - main and secondary indexes
    - scoring matrix file ?
    - read group file ?

usage: bfast_wrapper.py [options]
    -r, --ref=r: The reference genome to use or index
    -f, --fastq=f: The fastq file to use for the mapping
    -F, --output=u: The file to save the output (SAM format)
    -s, --fileSource=s: Whether to use a previously indexed reference sequence or one from history (indexed or history)
    -p, --params=p: Parameter setting to use (pre_set or full)
    -n, --numThreads=n: The number of threads to use
    -A, --space=A: The encoding space (0: base 1: color)
    -o, --offsets=o: The offsets for 'match'
    -l, --loadAllIndexes=l: Load all indexes into memory
    -k, --keySize=k: truncate key size in 'match'
    -K, --maxKeyMatches=K: the maximum number of matches to allow before a key is ignored
    -M, --maxNumMatches=M: the maximum number of matches to allow before the read is discarded
    -w, --whichStrand=w: the strands to consider (0: both 1: forward 2: reverse)
    -t, --timing=t: output timing information to stderr
    -u, --ungapped=u: performed ungapped local alignment
    -U, --unconstrained=U: performed local alignment without mask constraints
    -O, --offset=O: the number of bases before and after each hit to consider in local alignment
    -q, --avgMismatchQuality=q: average mismatch quality
    -a, --algorithm=a: post processing algorithm (0: no filtering, 1: all passing filters, 2: unique, 3: best scoring unique, 4: best score all)
    -P, --disallowPairing=P: do not choose alignments based on pairing
    -R, --reverse=R: paired end reads are given on reverse strands
    -z, --random=z: output a random best scoring alignment
    -D, --dbkey=D: Dbkey for reference genome
    -H, --suppressHeader=H: Suppress the sam header
"""

import optparse, os, shutil, subprocess, sys, tempfile

def stop_err( msg ):
    sys.stderr.write( '%s\n' % msg )
    sys.exit()

def __main__():
    #Parse Command Line
    parser = optparse.OptionParser()
    parser.add_option( '-r', '--ref', dest='ref', help='The reference genome to index and use' )
    parser.add_option( '-f', '--fastq', dest='fastq', help='The fastq file to use for the mapping' )
    parser.add_option( '-F', '--output', dest='output', help='The file to save the output (SAM format)' )
    parser.add_option( '-A', '--space', dest='space', type="choice", default='0', choices=('0','1' ), help='The encoding space (0: base 1: color)' )
    parser.add_option( '-H', '--suppressHeader', action="store_true", dest='suppressHeader', default=False, help='Suppress header' )
    parser.add_option( '-n', '--numThreads', dest='numThreads', type="int", default="1", help='The number of threads to use' )
    parser.add_option( '-t', '--timing', action="store_true", default=False, dest='timing', help='output timming information to stderr' )
    parser.add_option( '-l', '--loadAllIndexes', action="store_true", default=False, dest='loadAllIndexes', help='Load all indexes into memory' )
    parser.add_option( '-m', '--indexMask', dest='indexMask', help='String containing info on how to build custom indexes' )
    parser.add_option( "-b", "--buildIndex", action="store_true", dest="buildIndex", default=False, help='String containing info on how to build custom indexes' )
    parser.add_option( "--indexRepeatMasker", action="store_true", dest="indexRepeatMasker", default=False, help='Do not index lower case sequences. Such as those created by RepeatMasker' )
    parser.add_option( '--indexContigOptions', dest='indexContigOptions', default="", help='The contig range options to use for the indexing' )
    parser.add_option( '--indexExonsFileName', dest='indexExonsFileName', default="", help='The exons file to use for the indexing' )
    
    parser.add_option( '-o', '--offsets', dest='offsets', default="", help='The offsets for \'match\'' )
    parser.add_option( '-k', '--keySize', dest='keySize', type="int", default="-1", help='truncate key size in \'match\'' )
    parser.add_option( '-K', '--maxKeyMatches', dest='maxKeyMatches', type="int", default="-1", help='the maximum number of matches to allow before a key is ignored' )
    parser.add_option( '-M', '--maxNumMatches', dest='maxNumMatches', type="int", default="-1", help='the maximum number of matches to allow bfore the read is discarded' )
    parser.add_option( '-w', '--whichStrand', dest='whichStrand', type="choice", default='0', choices=('0','1','2'), help='the strands to consider (0: both 1: forward 2: reverse)' )
    
    parser.add_option( '--scoringMatrixFileName', dest='scoringMatrixFileName', help='Scoring Matrix file used to score the alignments' )
    parser.add_option( '-u', '--ungapped', dest='ungapped', action="store_true", default=False, help='performed ungapped local alignment' )
    parser.add_option( '-U', '--unconstrained', dest='unconstrained', action="store_true", default=False, help='performed local alignment without mask constraints' )
    parser.add_option( '-O', '--offset', dest='offset', type="int", default="0", help='the number of bases before and after each hit to consider in local alignment' )
    parser.add_option( '-q', '--avgMismatchQuality', type="int", default="-1", dest='avgMismatchQuality', help='average mismatch quality' )
    
    parser.add_option( '-a', '--algorithm', dest='algorithm', default='0', type="choice", choices=('0','1','2','3','4' ), help='post processing algorithm (0: no filtering, 1: all passing filters, 2: unique, 3: best scoring unique, 4: best score all' )
    parser.add_option( '--unpaired', dest='unpaired', action="store_true", default=False, help='do not choose alignments based on pairing' )
    parser.add_option( '--reverseStrand', dest='reverseStrand', action="store_true", default=False, help='paired end reads are given on reverse strands' )
    parser.add_option( '--pairedEndInfer', dest='pairedEndInfer', action="store_true", default=False, help='break ties when one end of a paired end read by estimating the insert size distribution' )
    parser.add_option( '--randomBest', dest='randomBest', action="store_true", default=False, help='output a random best scoring alignment' )
    
    (options, args) = parser.parse_args()

    # output version # of tool
    try:
        tmp = tempfile.NamedTemporaryFile().name
        tmp_stdout = open( tmp, 'wb' )
        proc = subprocess.Popen( args='bfast 2>&1', shell=True, stdout=tmp_stdout )
        tmp_stdout.close()
        returncode = proc.wait()
        stdout = None
        for line in open( tmp_stdout.name, 'rb' ):
            if line.lower().find( 'version' ) >= 0:
                stdout = line.strip()
                break
        if stdout:
            sys.stdout.write( '%s\n' % stdout )
        else:
            raise Exception
    except:
        sys.stdout.write( 'Could not determine BFAST version\n' )

    buffsize = 1048576

    # make temp directory for bfast, requires trailing slash
    tmp_dir = '%s/' % tempfile.mkdtemp()
    
    #'generic' options used in all bfast commands here
    if options.timing:
        all_cmd_options = "-t"
    else:
        all_cmd_options = ""
    
    try:
        if options.buildIndex:
            reference_filepath = tempfile.NamedTemporaryFile( dir=tmp_dir, suffix='.fa' ).name
            #build bfast indexes
            os.symlink( options.ref, reference_filepath )
            
            #bfast fast2brg
            try:
                nuc_space = [ "0" ]
                if options.space == "1":
                    #color space localalign appears to require nuc space brg
                    nuc_space.append( "1" )
                for space in nuc_space:
                    cmd = 'bfast fasta2brg -f "%s" -A "%s" %s' % ( reference_filepath, space, all_cmd_options )
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
                raise Exception, 'Error in \'bfast fasta2brg\'.\n' + str( e )
            
            #bfast index
            try:
                all_index_cmds = 'bfast index %s -f "%s" -A "%s" -n "%s"' % ( all_cmd_options, reference_filepath, options.space, options.numThreads )
                
                if options.indexRepeatMasker:
                    all_index_cmds += " -R"
                
                if options.indexContigOptions:
                    index_contig_options = map( int, options.indexContigOptions.split( ',' ) )
                    if index_contig_options[0] >= 0:
                        all_index_cmds += ' -s "%s"' % index_contig_options[0]
                    if index_contig_options[1] >= 0:
                        all_index_cmds += ' -S "%s"' % index_contig_options[1]
                    if index_contig_options[2] >= 0:
                        all_index_cmds += ' -e "%s"' % index_contig_options[2]
                    if index_contig_options[3] >= 0:
                        all_index_cmds += ' -E "%s"' % index_contig_options[3]
                elif options.indexExonsFileName:
                    all_index_cmds += ' -x "%s"' % options.indexExonsFileName
                
                index_count = 1
                for mask, hash_width in [ mask.split( ':' ) for mask in options.indexMask.split( ',' ) ]:
                    cmd = '%s -m "%s" -w "%s" -i "%i"' % ( all_index_cmds, mask, hash_width, index_count )
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
                    index_count += 1
            except Exception, e:
                raise Exception, 'Error in \'bfast index\'.\n' + str( e )
            
        else:
            reference_filepath = options.ref
        assert reference_filepath and os.path.exists( reference_filepath ), 'A valid genome reference was not provided.'
        
        # set up aligning and generate aligning command options
        # set up temp output files
        tmp_bmf = tempfile.NamedTemporaryFile( dir=tmp_dir )
        tmp_bmf_name = tmp_bmf.name
        tmp_bmf.close()
        tmp_baf = tempfile.NamedTemporaryFile( dir=tmp_dir )
        tmp_baf_name = tmp_baf.name
        tmp_baf.close()
        
        bfast_match_cmd = 'bfast match -f "%s" -r "%s" -n "%s" -A "%s" -T "%s" -w "%s" %s' % ( reference_filepath, options.fastq, options.numThreads, options.space, tmp_dir, options.whichStrand, all_cmd_options )
        bfast_localalign_cmd = 'bfast localalign -f "%s" -m "%s" -n "%s" -A "%s" -o "%s" %s' % ( reference_filepath, tmp_bmf_name, options.numThreads, options.space, options.offset, all_cmd_options )
        bfast_postprocess_cmd = 'bfast postprocess -O 1 -f "%s" -i "%s" -n "%s" -A "%s" -a "%s" %s' % ( reference_filepath, tmp_baf_name, options.numThreads, options.space, options.algorithm, all_cmd_options )
        
        if options.offsets:
            bfast_match_cmd += ' -o "%s"' % options.offsets
        if options.keySize >= 0:
            bfast_match_cmd += ' -k "%s"' % options.keySize
        if options.maxKeyMatches >= 0:
            bfast_match_cmd += ' -K "%s"' % options.maxKeyMatches
        if options.maxNumMatches >= 0:
            bfast_match_cmd += ' -M "%s"' % options.maxNumMatches
            bfast_localalign_cmd += ' -M "%s"' % options.maxNumMatches
        if options.scoringMatrixFileName:
            bfast_localalign_cmd += ' -x "%s"' % options.scoringMatrixFileName
            bfast_postprocess_cmd += ' -x "%s"' % options.scoringMatrixFileName
        if options.ungapped:
            bfast_localalign_cmd += ' -u'
        if options.unconstrained:
            bfast_localalign_cmd += ' -U'
        if options.avgMismatchQuality >= 0:
            bfast_localalign_cmd += ' -q "%s"' % options.avgMismatchQuality
            bfast_postprocess_cmd += ' -q "%s"' % options.avgMismatchQuality
        if options.algorithm == 3:
            if options.pairedEndInfer:
                bfast_postprocess_cmd += ' -P'
            if options.randomBest:
                bfast_postprocess_cmd += ' -z'
        if options.unpaired:
            bfast_postprocess_cmd += ' -U'
        if options.reverseStrand:
            bfast_postprocess_cmd += ' -R'
        
        #instead of using temp files, should we stream through pipes?
        bfast_match_cmd += " > %s" % tmp_bmf_name
        bfast_localalign_cmd += " > %s" % tmp_baf_name
        bfast_postprocess_cmd += " > %s" % options.output
        
        # need to nest try-except in try-finally to handle 2.4
        try:
            # bfast 'match'
            try:
                tmp = tempfile.NamedTemporaryFile( dir=tmp_dir ).name
                tmp_stderr = open( tmp, 'wb' )
                proc = subprocess.Popen( args=bfast_match_cmd, shell=True, cwd=tmp_dir, stderr=tmp_stderr.fileno() )
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
                raise Exception, 'Error in \'bfast match\'. \n' + str( e )
            # bfast 'localalign'
            try:
                tmp = tempfile.NamedTemporaryFile( dir=tmp_dir ).name
                tmp_stderr = open( tmp, 'wb' )
                proc = subprocess.Popen( args=bfast_localalign_cmd, shell=True, cwd=tmp_dir, stderr=tmp_stderr.fileno() )
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
                raise Exception, 'Error in \'bfast localalign\'. \n' + str( e )
            # bfast 'postprocess'
            try:
                tmp = tempfile.NamedTemporaryFile( dir=tmp_dir ).name
                tmp_stderr = open( tmp, 'wb' )
                proc = subprocess.Popen( args=bfast_postprocess_cmd, shell=True, cwd=tmp_dir, stderr=tmp_stderr.fileno() )
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
                raise Exception, 'Error in \'bfast postprocess\'. \n' + str( e )
            # remove header if necessary
            if options.suppressHeader:
                tmp_out = tempfile.NamedTemporaryFile( dir=tmp_dir)
                tmp_out_name = tmp_out.name
                tmp_out.close()
                try:
                    shutil.move( options.output, tmp_out_name )
                except Exception, e:
                    raise Exception, 'Error moving output file before removing headers. \n' + str( e )
                fout = file( options.output, 'w' )
                for line in file( tmp_out.name, 'r' ):
                    if len( line ) < 3 or line[0:3] not in [ '@HD', '@SQ', '@RG', '@PG', '@CO' ]:
                        fout.write( line )
                fout.close()
            # check that there are results in the output file
            if os.path.getsize( options.output ) > 0:
                if "0" == options.space:
                    sys.stdout.write( 'BFAST run on Base Space data' )
                else:
                    sys.stdout.write( 'BFAST run on Color Space data' )
            else:
                raise Exception, 'The output file is empty. You may simply have no matches, or there may be an error with your input file or settings.'
        except Exception, e:
            stop_err( 'The alignment failed.\n' + str( e ) )
    finally:
        # clean up temp dir
        if os.path.exists( tmp_dir ):
            shutil.rmtree( tmp_dir )

if __name__=="__main__": __main__()
