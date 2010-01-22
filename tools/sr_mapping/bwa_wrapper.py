#! /usr/bin/python

"""
Runs BWA on single-end or paired-end data.
Produces a SAM file containing the mappings.
Works with BWA version 0.5.3.

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

import optparse, os, shutil, sys, tempfile

def stop_err( msg ):
    sys.stderr.write( "%s\n" % msg )
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
    # make temp directory for placement of indices and copy reference file there
    tmp_index_dir = tempfile.mkdtemp()
    # index if necessary
    if options.fileSource == 'history':
        try:
            shutil.copy( options.ref, tmp_index_dir )
        except Exception, e:
            stop_err( 'Error creating temp directory for indexing purposes\n' + str( e ) )
        try:
            size = os.stat( options.ref ).st_size
            if size <= 2**30: 
                indexingAlg = 'is'
            else:
                indexingAlg = 'bwtsw'
        except:
            indexingAlg = 'is'
        indexing_cmds = '-a %s' % indexingAlg
        options.ref = os.path.join( tmp_index_dir, os.path.split( options.ref )[1] )
        cmd1 = 'bwa index %s %s 2> /dev/null' % ( indexing_cmds, options.ref )
        try:
            os.chdir( tmp_index_dir )
            os.system( cmd1 )
        except Exception, e:
            stop_err( 'Error indexing reference sequence\n' + str( e ) )
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
#        print 'options.genAlignType: %s and commands: %s' % (options.genAlignType, gen_alignment_cmds)
    # set up output files
    tmp_align_out = tempfile.NamedTemporaryFile()
    tmp_align_out2 = tempfile.NamedTemporaryFile()
    # prepare actual aligning and generate aligning commands
    cmd2 = 'bwa aln %s %s %s > %s 2> /dev/null' % ( aligning_cmds, options.ref, options.fastq, tmp_align_out.name )
    cmd2b = ''
    if options.genAlignType == 'paired':
        cmd2b = 'bwa aln %s %s %s > %s 2> /dev/null' % ( aligning_cmds, options.ref, options.rfastq, tmp_align_out2.name )
        cmd3 = 'bwa sampe %s %s %s %s %s %s >> %s 2> /dev/null' % ( gen_alignment_cmds, options.ref, tmp_align_out.name, tmp_align_out2.name, options.fastq, options.rfastq, options.output )
    else:
        cmd3 = 'bwa samse %s %s %s %s >> %s 2> /dev/null' % ( gen_alignment_cmds, options.ref, tmp_align_out.name, options.fastq, options.output ) 
    # align
    try:
        os.system( cmd2 )
    except Exception, e:
        stop_err( 'Error aligning sequence\n' + str( e ) )
    # and again if paired data
    try:
        if cmd2b: 
            os.system( cmd2b )
    except Exception, erf:
        stop_err( 'Error aligning second sequence\n' + str( e ) )
    # generate align
    try:
        os.system( cmd3 )
    except Exception, e:
        stop_err( 'Error sequence aligning sequence\n' + str( e ) )
    # clean up temp files
    tmp_align_out.close()
    tmp_align_out2.close()
    # remove header if necessary
    if options.suppressHeader == 'true':
        tmp_out = tempfile.NamedTemporaryFile()
        try:
            shutil.move( options.output, tmp_out.name )
        except Exception, e:
            stop_err( 'Error moving output file before removing headers\n' + str( e ) )
        fout = file( options.output, 'w' )
        for line in file( tmp_out.name, 'r' ):
            if not ( line.startswith( '@HD' ) or line.startswith( '@SQ' ) or line.startswith( '@RG' ) or line.startswith( '@PG' ) or line.startswith( '@CO' ) ):
                fout.write( line )
        fout.close()
        tmp_out.close()
    # clean up temp dir
    if os.path.exists( tmp_index_dir ):
        shutil.rmtree( tmp_index_dir )
    
if __name__=="__main__": __main__()
