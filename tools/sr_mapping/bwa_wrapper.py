#!/usr/bin/env python

"""
Runs BWA on single-end or paired-end data.
Produces a SAM file containing the mappings.
Works with BWA version 0.5.9.

usage: bwa_wrapper.py [options]

See below for options
"""

import optparse, os, shutil, subprocess, sys, tempfile

def stop_err( msg ):
    sys.stderr.write( '%s\n' % msg )
    sys.exit()

def check_is_double_encoded( fastq ):
    # check that first read is bases, not one base followed by numbers
    bases = [ 'A', 'C', 'G', 'T', 'a', 'c', 'g', 't', 'N' ]
    nums = [ '0', '1', '2', '3' ]
    for line in file( fastq, 'rb'):
        if not line.strip() or line.startswith( '@' ):
            continue
        if len( [ b for b in line.strip() if b in nums ] ) > 0:
            return False
        elif line.strip()[0] in bases and len( [ b for b in line.strip() if b in bases ] ) == len( line.strip() ):
            return True
        else:
            raise Exception, 'First line in first read does not appear to be a valid FASTQ read in either base-space or color-space'
    raise Exception, 'There is no non-comment and non-blank line in your FASTQ file'

def __main__():
    #Parse Command Line
    parser = optparse.OptionParser()
    parser.add_option( '-t', '--threads', dest='threads', help='The number of threads to use' )
    parser.add_option( '-c', '--color-space', dest='color_space', action='store_true', help='If the input files are SOLiD format' )
    parser.add_option( '-r', '--ref', dest='ref', help='The reference genome to use or index' )
    parser.add_option( '-f', '--input1', dest='fastq', help='The (forward) fastq file to use for the mapping' )
    parser.add_option( '-F', '--input2', dest='rfastq', help='The reverse fastq file to use for mapping if paired-end data' )
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
    parser.add_option( '-R', '--suboptAlign', dest='suboptAlign', default=None, help='Proceed with suboptimal alignments even if the top hit is a repeat' )
    parser.add_option( '-N', '--noIterSearch', dest='noIterSearch', help='Disable iterative search' )
    parser.add_option( '-T', '--outputTopN', dest='outputTopN', help='Maximum number of alignments to output in the XA tag for reads paired properly' )
    parser.add_option( '', '--outputTopNDisc', dest='outputTopNDisc', help='Maximum number of alignments to output in the XA tag for disconcordant read pairs (excluding singletons)' )
    parser.add_option( '-S', '--maxInsertSize', dest='maxInsertSize', help='Maximum insert size for a read pair to be considered mapped good' )
    parser.add_option( '-P', '--maxOccurPairing', dest='maxOccurPairing', help='Maximum occurrences of a read for pairings' )
    parser.add_option( '', '--rgid', dest='rgid', help='Read group identifier' )
    parser.add_option( '', '--rgcn', dest='rgcn', help='Sequencing center that produced the read' )
    parser.add_option( '', '--rgds', dest='rgds', help='Description' )
    parser.add_option( '', '--rgdt', dest='rgdt', help='Date that run was produced (ISO8601 format date or date/time, like YYYY-MM-DD)' )
    parser.add_option( '', '--rgfo', dest='rgfo', help='Flow order' )
    parser.add_option( '', '--rgks', dest='rgks', help='The array of nucleotide bases that correspond to the key sequence of each read' )
    parser.add_option( '', '--rglb', dest='rglb', help='Library name' )
    parser.add_option( '', '--rgpg', dest='rgpg', help='Programs used for processing the read group' )
    parser.add_option( '', '--rgpi', dest='rgpi', help='Predicted median insert size' )
    parser.add_option( '', '--rgpl', dest='rgpl', choices=[ 'CAPILLARY', 'LS454', 'ILLUMINA', 'SOLID', 'HELICOS', 'IONTORRENT' and 'PACBIO' ], help='Platform/technology used to produce the reads' )
    parser.add_option( '', '--rgpu', dest='rgpu', help='Platform unit (e.g. flowcell-barcode.lane for Illumina or slide for SOLiD)' )
    parser.add_option( '', '--rgsm', dest='rgsm', help='Sample' )
    parser.add_option( '-D', '--dbkey', dest='dbkey', help='Dbkey for reference genome' )
    parser.add_option( '-X', '--do_not_build_index', dest='do_not_build_index', action='store_true', help="Don't build index" )
    parser.add_option( '-H', '--suppressHeader', dest='suppressHeader', help='Suppress header' )
    parser.add_option( '-I', '--illumina1.3', dest='illumina13qual', help='Input FASTQ files have Illuina 1.3 quality scores' )
    (options, args) = parser.parse_args()

    # output version # of tool
    try:
        tmp = tempfile.NamedTemporaryFile().name
        tmp_stdout = open( tmp, 'wb' )
        proc = subprocess.Popen( args='bwa 2>&1', shell=True, stdout=tmp_stdout )
        tmp_stdout.close()
        returncode = proc.wait()
        stdout = None
        for line in open( tmp_stdout.name, 'rb' ):
            if line.lower().find( 'version' ) >= 0:
                stdout = line.strip()
                break
        if stdout:
            sys.stdout.write( 'BWA %s\n' % stdout )
        else:
            raise Exception
    except:
        sys.stdout.write( 'Could not determine BWA version\n' )

    # check for color space fastq that's not double-encoded and exit if appropriate
    if options.color_space:
        if not check_is_double_encoded( options.fastq ):
            stop_err( 'Your file must be double-encoded (it must be converted from "numbers" to "bases"). See the help section for details' )
        if options.genAlignType == 'paired':
            if not check_is_double_encoded( options.rfastq ):
                stop_err( 'Your reverse reads file must also be double-encoded (it must be converted from "numbers" to "bases"). See the help section for details' )

    fastq = options.fastq
    if options.rfastq:
         rfastq = options.rfastq

    # set color space variable
    if options.color_space:
        color_space = '-c'
    else:
        color_space = ''

    # make temp directory for placement of indices
    tmp_index_dir = tempfile.mkdtemp()
    tmp_dir = tempfile.mkdtemp()
    # index if necessary
    if options.fileSource == 'history' and not options.do_not_build_index:
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
        indexing_cmds = '%s -a %s' % ( color_space, indexingAlg )
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
    if options.illumina13qual:
        illumina_quals = "-I"
    else:
        illumina_quals = ""

    # set up aligning and generate aligning command options
    if options.params == 'pre_set':
        aligning_cmds = '-t %s %s %s' % ( options.threads, color_space, illumina_quals )
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
        if options.suboptAlign:
            suboptAlign = '-R "%s"' % ( options.suboptAlign )
        else:
            suboptAlign = ''
        if options.noIterSearch == 'true':
            noIterSearch = '-N'
        else:
            noIterSearch = ''
        aligning_cmds = '-n %s -o %s -e %s -d %s -i %s %s -k %s -t %s -M %s -O %s -E %s %s %s %s %s' % \
                        ( editDist, options.maxGapOpens, options.maxGapExtens, options.disallowLongDel,
                          options.disallowIndel, seed, options.maxEditDistSeed, options.threads,
                          options.mismatchPenalty, options.gapOpenPenalty, options.gapExtensPenalty,
                          suboptAlign, noIterSearch, color_space, illumina_quals )
        if options.genAlignType == 'paired':
            gen_alignment_cmds = '-a %s -o %s' % ( options.maxInsertSize, options.maxOccurPairing )
            if options.outputTopNDisc:
                gen_alignment_cmds += ' -N %s' % options.outputTopNDisc
        else:
            gen_alignment_cmds = ''
        if options.rgid:
            if not options.rglb or not options.rgpl or not options.rgsm:
                stop_err( 'If you want to specify read groups, you must include the ID, LB, PL, and SM tags.' )
            readGroup = '@RG\tID:%s\tLB:%s\tPL:%s\tSM:%s' % ( options.rgid, options.rglb, options.rgpl, options.rgsm )
            if options.rgcn:
                readGroup += '\tCN:%s' % options.rgcn
            if options.rgds:
                readGroup += '\tDS:%s' % options.rgds
            if options.rgdt:
                readGroup += '\tDT:%s' % options.rgdt
            if options.rgfo:
                readGroup += '\tFO:%s' % options.rgfo
            if options.rgks:
                readGroup += '\tKS:%s' % options.rgks
            if options.rgpg:
                readGroup += '\tPG:%s' % options.rgpg
            if options.rgpi:
                readGroup += '\tPI:%s' % options.rgpi
            if options.rgpu:
                readGroup += '\tPU:%s' % options.rgpu
            gen_alignment_cmds += ' -r "%s"' % readGroup
        if options.outputTopN:
            gen_alignment_cmds += ' -n %s' % options.outputTopN
    # set up output files
    tmp_align_out = tempfile.NamedTemporaryFile( dir=tmp_dir )
    tmp_align_out_name = tmp_align_out.name
    tmp_align_out.close()
    tmp_align_out2 = tempfile.NamedTemporaryFile( dir=tmp_dir )
    tmp_align_out2_name = tmp_align_out2.name
    tmp_align_out2.close()
    # prepare actual aligning and generate aligning commands
    cmd2 = 'bwa aln %s %s %s > %s' % ( aligning_cmds, ref_file_name, fastq, tmp_align_out_name )
    cmd2b = ''
    if options.genAlignType == 'paired':
        cmd2b = 'bwa aln %s %s %s > %s' % ( aligning_cmds, ref_file_name, rfastq, tmp_align_out2_name )
        cmd3 = 'bwa sampe %s %s %s %s %s %s >> %s' % ( gen_alignment_cmds, ref_file_name, tmp_align_out_name, tmp_align_out2_name, fastq, rfastq, options.output )
    else:
        cmd3 = 'bwa samse %s %s %s %s >> %s' % ( gen_alignment_cmds, ref_file_name, tmp_align_out_name, fastq, options.output )
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
