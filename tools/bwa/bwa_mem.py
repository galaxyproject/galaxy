#!/usr/bin/env python
# -*- coding: utf-8 -*-  #rlk moved this line to fall after the #! line
## yufei.luo@gustave.roussy 22/07/2013
## Copyright © 2014 CRS4 Srl. http://www.crs4.it/
## Modified by:
## Nicola Soranzo <nicola.soranzo@crs4.it>

"""
Runs BWA on single-end or paired-end data.
Produces a SAM file containing the mappings.
Works with BWA version >= 0.7.5.
NOTICE: In this wrapper, we only use 'mem' for mapping step.

usage: bwa_mem.py [options]

See below for options
"""

import optparse, os, shutil, subprocess, sys, tempfile

def __main__():
    descr = "bwa_mem.py: Map (long length) reads against a reference genome with BWA-MEM."
    parser = optparse.OptionParser(description=descr)
    parser.add_option( '-t', '--threads', default=1, help='The number of threads to use [1]' )
    parser.add_option( '--ref', help='The reference genome to use or index' )
    parser.add_option( '-f', '--fastq', help='The (forward) fastq file to use for the mapping' )
    parser.add_option( '-F', '--rfastq', help='The reverse fastq file to use for mapping if paired-end data' )
    parser.add_option( '-u', '--output', help='The file to save the output (SAM format)' )
    parser.add_option( '-g', '--genAlignType', help='The type of pairing (single or paired)' )
    parser.add_option( '--params', help='Parameter setting to use (pre_set or full)' )
    parser.add_option( '-s', '--fileSource', help='Whether to use a previously indexed reference sequence or one form history (indexed or history)' )
    parser.add_option( '-D', '--dbkey', help='Dbkey for reference genome' )

    parser.add_option( '-k', '--minSeedLength', type=int, help='Minimum seed length [19]' )
    parser.add_option( '-w', '--bandWidth', type=int, help='Band width for banded alignment [100]' )
    parser.add_option( '-d', '--offDiagonal', type=int, help='Off-diagonal X-dropoff [100]' )
    parser.add_option( '-r', '--internalSeeds', type=float, help='Look for internal seeds inside a seed longer than {-k} * FLOAT [1.5]' )
    parser.add_option( '-c', '--seedsOccurrence', type=int, help='Skip seeds with more than INT occurrences [10000]' )
    parser.add_option( '-S', '--mateRescue', action='store_true', help='Skip mate rescue' )
    parser.add_option( '-P', '--skipPairing', action='store_true', help='Skip pairing' )
    parser.add_option( '-A', '--seqMatch', type=int, help='Score for a sequence match [1]' )
    parser.add_option( '-B', '--mismatch', type=int, help='Penalty for a mismatch [4]' )
    parser.add_option( '-O', '--gapOpen', type=int, help='Gap open penalty [6]' )
    parser.add_option( '-E', '--gapExtension', type=int, help='Gap extension penalty; a gap of length k costs {-O} + {-E}*k [1]' )
    parser.add_option( '-L', '--clipping', help='Penalty for clipping [5]' )
    parser.add_option( '-U', '--unpairedReadpair', type=int, help='Penalty for an unpaired read pair [17]' )
    parser.add_option( '-p', '--interPairEnd', action='store_true', help='FASTQ file consists of interleaved paired-end sequences' )
    parser.add_option( '--rgid', help='Read group identifier' )
    parser.add_option( '--rgsm', help='Sample' )
    parser.add_option( '--rgpl', choices=[ 'CAPILLARY', 'LS454', 'ILLUMINA', 'SOLID', 'HELICOS', 'IONTORRENT', 'PACBIO' ], help='Platform/technology used to produce the reads' )
    parser.add_option( '--rglb', help='Library name' )
    parser.add_option( '--rgpu', help='Platform unit (e.g. flowcell-barcode.lane for Illumina or slide for SOLiD)' )
    parser.add_option( '--rgcn', help='Sequencing center that produced the read' )
    parser.add_option( '--rgds', help='Description' )
    parser.add_option( '--rgdt', help='Date that run was produced (ISO8601 format date or date/time, like YYYY-MM-DD)' )
    parser.add_option( '--rgfo', help='Flow order' )
    parser.add_option( '--rgks', help='The array of nucleotide bases that correspond to the key sequence of each read' )
    parser.add_option( '--rgpg', help='Programs used for processing the read group' )
    parser.add_option( '--rgpi', help='Predicted median insert size' )
    parser.add_option( '-T', '--minScore', type=int, help='Minimum score to output [30]' )
    parser.add_option( '-a', '--outputAll', action='store_true', help='Output all found alignments for single-end or unpaired paired-end reads' )
    parser.add_option( '-M', '--mark', action='store_true', help='Mark shorter split hits as secondary (for Picard/GATK compatibility)' )
    parser.add_option( '-H', '--suppressHeader', dest='suppressHeader', action='store_true', help='Suppress header' )
    (options, args) = parser.parse_args()
    if len(args) > 0:
        parser.error('Wrong number of arguments')

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

    fastq = options.fastq
    if options.rfastq:
        rfastq = options.rfastq

    # make temp directory for placement of indices
    tmp_index_dir = tempfile.mkdtemp()
    tmp_dir = tempfile.mkdtemp()
    # index if necessary
    #if options.fileSource == 'history':
    if False:
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
            raise Exception, 'Error indexing reference sequence. ' + str( e )
    else:
        ref_file_name = options.ref
    # if options.illumina13qual:
    #     illumina_quals = "-I"
    # else:
    #     illumina_quals = ""

    # set up aligning and generate aligning command args
    start_cmds = "bwa mem -t %s" % options.threads
    #if False:
    if options.interPairEnd:
        start_cmds += ' -p'
    if options.params != 'pre_set':
	if options.minSeedLength is not None:
	    start_cmds += " -k %d" % options.minSeedLength
	if options.bandWidth is not None:
	    start_cmds += " -w %d" % options.bandWidth
	if options.offDiagonal is not None:
	    start_cmds += " -d %d" % options.offDiagonal
	if options.internalSeeds is not None:
	    start_cmds += " -r %s" % options.internalSeeds
	if options.seedsOccurrence is not None:
	    start_cmds += " -c %d" % options.seedsOccurrence
	if options.mateRescue:
	    start_cmds += ' -S'
	if options.skipPairing:
	    start_cmds += ' -P'
	if options.seqMatch is not None:
	    start_cmds += " -A %d" % options.seqMatch
	if options.mismatch is not None:
	    start_cmds += " -B %d" % options.mismatch
	if options.gapOpen is not None:
	    start_cmds += " -O %d" % options.gapOpen
	if options.gapExtension is not None:
	    start_cmds += " -E %d" % options.gapExtension
	if options.clipping:
	    start_cmds += " -L %s" % options.clipping
	if options.unpairedReadpair is not None:
	    start_cmds += " -U %d" % options.unpairedReadpair
	if options.minScore is not None:
	    start_cmds += " -T %d" % options.minScore
        if options.outputAll:
            start_cmds += ' -a'
        if options.mark:
            start_cmds += ' -M'
        if options.rgid:
            #if not options.rglb or not options.rgpl or not options.rgsm or not options.rglb:
                #sys.exit( 'If you want to specify read groups, you must include the ID, LB, PL, and SM tags.' )
            if not options.rglb or not options.rgsm or not options.rglb:
                sys.exit( 'If you want to specify read groups, you must include the ID, LB, and SM tags.') 
            #readGroup = '@RG\tID:%s\tLB:%s\tPL:%s\tSM:%s' % ( options.rgid, options.rglb, options.rgpl, options.rgsm )
            readGroup = '@RG\tID:%s\tLB:%s\tSM:%s' % ( options.rgid, options.rglb, options.rgsm )
            if options.rgpl:
                readGroup += '\tPL:%s' % options.rgpl
            if options.rgpu:
                readGroup += '\tPU:%s' % options.rgpu
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
            start_cmds += " -R '%s'" % readGroup

    if options.genAlignType == 'paired':
        cmd = "%s %s %s %s > %s" % ( start_cmds, ref_file_name, fastq, rfastq, options.output )
    else:
        cmd = "%s %s %s > %s" % ( start_cmds, ref_file_name, fastq, options.output )

  # perform alignments
    buffsize = 1048576
    try:
        # need to nest try-except in try-finally to handle 2.4
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
            raise Exception, 'Error generating alignments. ' + str( e )
        # remove header if necessary
        if options.suppressHeader:
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
    finally:
        # clean up temp dir
        if os.path.exists( tmp_index_dir ):
            shutil.rmtree( tmp_index_dir )
        if os.path.exists( tmp_dir ):
            shutil.rmtree( tmp_dir )

if __name__ == "__main__":
    __main__()
