#!/usr/bin/env python
## yufei.luo@gustave.roussy 22/07/2013

"""
Runs BWA on single-end or paired-end data.
Produces a SAM file containing the mappings.
Works with BWA version 0.7.5. 
NOTICE: In this wrapper, we only use 'mem' for mapping step.

usage: bwa_0_7_5.py [args]

See below for args
"""

import optparse, os, shutil, subprocess, sys, tempfile
import argparse

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

    descr = "bwa_0_7_5.py: version 1.0. Map the reads(long length) against the genome reference with BWA MEM. \n"
    descr += "Usage: BWA mem -t thread -R groupInfo refSequence read.R1.fastq (read.R2.fastq) > out.sam"
    parser = argparse.ArgumentParser(description=descr)
    parser.add_argument( '-t', '--threads', default=1, help='The number of threads to use [1]' )
    parser.add_argument( '--color-space', default=False, help='If the input files are SOLiD format' )    
    parser.add_argument( '--ref', help='The reference genome to use or index' )
    parser.add_argument( '-f', '--fastq', help='The (forward) fastq file to use for the mapping' )
    parser.add_argument( '-F', '--rfastq', help='The reverse fastq file to use for mapping if paired-end data' )
    parser.add_argument( '-u', '--output', help='The file to save the output (SAM format)' )
    parser.add_argument( '-g', '--genAlignType',  help='The type of pairing (single or paired)' )
    parser.add_argument( '--params', help='Parameter setting to use (pre_set or full)' )
    parser.add_argument( '-s', '--fileSource', help='Whether to use a previously indexed reference sequence or one form history (indexed or history)' )
    parser.add_argument( '-D', '--dbkey', help='Dbkey for reference genome' )

    parser.add_argument( '-k', '--minEditDistSeed', default=19, type=int, help='Minimum edit distance to the seed [19]' )
    parser.add_argument( '-w', '--bandWidth', default=100, type=int, help='Band width for banded alignment [100]' )
    parser.add_argument( '-d', '--offDiagonal', default=100, type=int, help='off-diagonal X-dropoff [100]' )
    parser.add_argument( '-r', '--internalSeeds', default=1.5, type=float, help='look for internal seeds inside a seed longer than {-k} * FLOAT [1.5]' )
    parser.add_argument( '-c', '--seedsOccurrence', default=10000, type=int, help='skip seeds with more than INT occurrences [10000]' )
    parser.add_argument( '-S', '--mateRescue', default=False, help='skip mate rescue' )
    parser.add_argument( '-P', '--skipPairing', default=False, help='skpe pairing, mate rescue performed unless -S also in use' )
    parser.add_argument( '-A', '--seqMatch', default=1, type=int, help='score of a sequence match' )
    parser.add_argument( '-B', '--mismatch', default=4,type=int, help='penalty for a mismatch' )
    parser.add_argument( '-O', '--gapOpen', default=6, type=int, help='gap open penalty' )
    parser.add_argument( '-E', '--gapExtension', default=None, help='gap extension penalty; a gap of size k cost {-O} + {-E}*k [1]' )
    parser.add_argument( '-L', '--clipping', default=5, type=int, help='penalty for clipping [5]' )
    parser.add_argument( '-U', '--unpairedReadpair', default=17, type=int, help='penalty for an unpaired read pair [17]' )
    parser.add_argument( '-p', '--interPairEnd', default=False, help='first query file consists of interleaved paired-end sequences' )
    parser.add_argument( '--rgid', help='Read group identifier' )
    parser.add_argument( '--rgsm', help='Sample' )
    parser.add_argument( '--rgpl', choices=[ 'CAPILLARY', 'LS454', 'ILLUMINA', 'SOLID', 'HELICOS', 'IONTORRENT', 'PACBIO' ], help='Platform/technology used to produce the reads' )
    parser.add_argument( '--rglb', help='Library name' )
    parser.add_argument( '--rgpu', help='Platform unit (e.g. flowcell-barcode.lane for Illumina or slide for SOLiD)' )
    parser.add_argument( '--rgcn', help='Sequencing center that produced the read' )
    parser.add_argument( '--rgds', help='Description' )
    parser.add_argument( '--rgdt', help='Date that run was produced (ISO8601 format date or date/time, like YYYY-MM-DD)' )
    parser.add_argument( '--rgfo', help='Flow order' )
    parser.add_argument( '--rgks', help='The array of nucleotide bases that correspond to the key sequence of each read' )
    parser.add_argument( '--rgpg', help='Programs used for processing the read group' )
    parser.add_argument( '--rgpi', help='Predicted median insert size' )
    parser.add_argument( '-T', '--minScore', default=30, type=int, help='minimum score to output [30]' )
    parser.add_argument( '-M', '--mark', default=False, help='mark shorter split hits as secondary (for Picard/GATK compatibility)' )
    args = parser.parse_args()


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
#    if args.color_space:
#        if not check_is_double_encoded( args.fastq ):
#            stop_err( 'Your file must be double-encoded (it must be converted from "numbers" to "bases"). See the help section for details' )
#        if args.genAlignType == 'paired':
#            if not check_is_double_encoded( args.rfastq ):
#                stop_err( 'Your reverse reads file must also be double-encoded (it must be converted from "numbers" to "bases"). See the help section for details' )

    fastq = args.fastq
    if args.rfastq:
         rfastq = args.rfastq

    # set color space variable
#    if args.color_space:
#        color_space = '-c'
#    else:
#        color_space = ''

    # make temp directory for placement of indices
    tmp_index_dir = tempfile.mkdtemp()
    tmp_dir = tempfile.mkdtemp()
    # index if necessary
    # if args.fileSource == 'history' and not args.do_not_build_index:
    if args.fileSource == 'history' :
        ref_file = tempfile.NamedTemporaryFile( dir=tmp_index_dir )
        ref_file_name = ref_file.name
        ref_file.close()
        os.symlink( args.ref, ref_file_name )
        # determine which indexing algorithm to use, based on size
        try:
            size = os.stat( args.ref ).st_size
            if size <= 2**30: 
                indexingAlg = 'is'
            else:
                indexingAlg = 'bwtsw'
        except:
            indexingAlg = 'is'
        #indexing_cmds = '%s -a %s' % ( color_space, indexingAlg )
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
        ref_file_name = args.ref
    # if args.illumina13qual:
    #     illumina_quals = "-I"
    # else:
    #     illumina_quals = ""

    # set up aligning and generate aligning command args
    start_cmds = '-t %s ' % args.threads
    if args.params == 'pre_set':
        # aligning_cmds = '-t %s %s %s' % ( args.threads, color_space, illumina_quals )
        #start_cmds = '-t %s ' % args.threads 
        end_cmds = ' '
        print start_cmds, end_cmds

    else:
        end_cmds = '-k %s -w %s -d %s -r %s -c %s -A %s -B %s -O %s -L %s -U %s -T %s ' % (args.minEditDistSeed, args.bandWidth, args.offDiagonal, args.internalSeeds, args.seedsOccurrence, args.seqMatch, args.mismatch, args.gapOpen, args.clipping, args.unpairedReadpair, args.minScore)
        if args.mateRescue:
            end_cmds += '-S '
            if args.skipPairing:
                end_cmds += '-P '
        else:
            if args.skipPairing:
                print "Option Error and will not be considered, you should also choose 'skip mate rescue -S' option! "
        if args.gapExtension != None:
            end_cmds += '-E %s ' % args.gapExtension

        if args.rgid:
            if not args.rglb or not args.rgpl or not args.rgsm or not args.rglb:
                stop_err( 'If you want to specify read groups, you must include the ID, LB, PL, and SM tags.' )
            # readGroup = '@RG\tID:%s\tLB:%s\tPL:%s\tSM:%s' % ( args.rgid, args.rglb, args.rgpl, args.rgsm )
            readGroup = '@RG\tID:%s\tLB:%s\tPL:%s\tSM:%s' % ( args.rgid, args.rglb, args.rgpl, args.rgsm )
            if args.rgpu:
                readGroup += '\tPU:%s' % args.rgpu
            if args.rgcn:
                readGroup += '\tCN:%s' % args.rgcn
            if args.rgds:
                readGroup += '\tDS:%s' % args.rgds
            if args.rgdt:
                readGroup += '\tDT:%s' % args.rgdt
            if args.rgfo:
                readGroup += '\tFO:%s' % args.rgfo
            if args.rgks:
                readGroup += '\tKS:%s' % args.rgks
            if args.rgpg:
                readGroup += '\tPG:%s' % args.rgpg
            if args.rgpi:
                readGroup += '\tPI:%s' % args.rgpi
            end_cmds += ' -R "%s" ' % readGroup

        if args.interPairEnd:
            end_cmds += '-p %s ' % args.interPairEnd
        if args.mark:
            end_cmds += '-M '


    if args.genAlignType == 'paired':
        cmd = 'bwa mem %s %s %s %s %s > %s' % ( start_cmds, ref_file_name, fastq, rfastq, end_cmds, args.output )
    else:
        cmd = 'bwa mem %s %s %s %s > %s' % ( start_cmds, ref_file_name, fastq, end_cmds, args.output )

  # perform alignments
    buffsize = 1048576
    try:
        # need to nest try-except in try-finally to handle 2.4
        try:
            try:
                tmp = tempfile.NamedTemporaryFile( dir=tmp_dir ).name
                tmp_stderr = open( tmp, 'wb' )
		print "The cmd is %s" % cmd
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

            # check that there are results in the output file
            if os.path.getsize( args.output ) > 0:
                sys.stdout.write( 'BWA run on %s-end data' % args.genAlignType )
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
