#! /usr/bin/python

"""
Runs BWA on single-end or paired-end data.
Produces a SAM file containing the mappings.
"""

import optparse, os, shutil, sys, tempfile

def stop_err( msg ):
    sys.stderr.write( "%s\n" % msg )
    sys.exit()
 
def __main__():
    #Parse Command Line
    parser = optparse.OptionParser()
    parser.add_option('', '--threads', dest='threads', help='The number of threads to use')
    parser.add_option('', '--ref', dest='ref', help='The reference genome to use or index')
    parser.add_option('', '--fastq', dest='fastq', help='The (forward) fastq file to use for the mapping')
    parser.add_option('', '--rfastq', dest='rfastq', help='The reverse fastq file to use for mapping if paired-end data')
    parser.add_option('', '--output', dest='output', help='The file to save the output (SAM format)')
    parser.add_option('', '--genAlignType', dest='genAlignType', help='The type of pairing (single or paired)')
    parser.add_option('', '--params', dest='params', help='Parameter setting to use (pre_set or full)')
    parser.add_option('', '--fileType', dest='fileType', help='Type of reference sequence file (solid or solexa)')
    parser.add_option('', '--fileSource', dest='fileSource', help='Whether to use a previously indexed reference sequence or one form history (indexed or history)')
    parser.add_option('-n', '--maxEditDist', dest='maxEditDist', help='Maximum edit distance if integer')
    parser.add_option('', '--fracMissingAligns', dest='fracMissingAligns', help='Fraction of missing alignments given 2% uniform base error rate if fraction')
    parser.add_option('-o', '--maxGapOpens', dest='maxGapOpens', help='Maximum number of gap opens')
    parser.add_option('-e', '--maxGapExtens', dest='maxGapExtens', help='Maximum number of gap extensions')
    parser.add_option('-d', '--disallowLongDel', dest='disallowLongDel', help='Disallow a long deletion within specified bps')
    parser.add_option('-i', '--disallowIndel', dest='disallowIndel', help='Disallow indel within specified bps')
    parser.add_option('-l', '--seed', dest='seed', help='Take the first specified subsequences')
    parser.add_option('-k', '--maxEditDistSeed', dest='maxEditDistSeed', help='Maximum edit distance to the seed')
    parser.add_option('-M', '--mismatchPenalty', dest='mismatchPenalty', help='Mismatch penalty')
    parser.add_option('-O', '--gapOpenPenalty', dest='gapOpenPenalty', help='Gap open penalty')
    parser.add_option('-E', '--gapExtensPenalty', dest='gapExtensPenalty', help='Gap extension penalty')
    parser.add_option('-c', '--colorSpaceRev', dest='colorSpaceRev', help="Reverse query but don't complement it")
    parser.add_option('-R', '--suboptAlign', dest='suboptAlign', help='Proceed with suboptimal alignments even if the top hit is a repeat')
    parser.add_option('-N', '--noIterSearch', dest='noIterSearch', help='Disable iterative search')
    parser.add_option('', '--outputTopN', dest='outputTopN', help='Output top specified hits')
    parser.add_option('', '--maxInsertSize', dest='maxInsertSize', help='Maximum insert size for a read pair to be considered mapped good')
    parser.add_option('', '--maxOccurPairing', dest='maxOccurPairing', help='Maximum occurrences of a read for pairings')
    parser.add_option('', '--dbkey', dest='dbkey', help='')
    parser.add_option('', '--suppressHeader', dest='suppressHeader', help='Suppress header')
    (options, args) = parser.parse_args()
    # make temp directory for placement of indices and copy reference file there
    tmp_index_dir = tempfile.mkdtemp()
    # index if necessary
    if options.fileSource == 'history':
        try:
            shutil.copy(options.ref, tmp_index_dir)
        except Exception, erf:
            stop_err('Error creating temp directory for indexing purposes\n' + str(erf))
        try:
            size = os.stat(options.ref).st_size
            if size <= 2**30: 
                indexingAlg = 'is'
            else:
                indexingAlg = 'bwtsw'
        except:
            indexingAlg = 'is'
        if options.fileType == 'solid':
            indexing_cmds = '-c -a %s' % indexingAlg
        else:
            indexing_cmds = '-a %s' % indexingAlg
        options.ref = os.path.join(tmp_index_dir,os.path.split(options.ref)[1])
        cmd1 = 'bwa index %s %s 2> /dev/null' % (indexing_cmds, options.ref)
        try:
            os.chdir(tmp_index_dir)
            os.system(cmd1)
        except Exception, erf:
            stop_err('Error indexing reference sequence\n' + str(erf))
    # set up aligning and generate aligning command options
    if options.params == 'pre_set':
        if options.fileType == 'solid':
            aligning_cmds = '-c -t %s' % options.threads
        else:
            aligning_cmds = '-t %s' % options.threads
        gen_alignment_cmds = ''
    else:
        aligning_cmds = '-n %s -o %s -e %s -d %s -i %s %s -k %s -t %s -M %s -O %s -E %s %s %s %s' % \
                        ((options.fracMissingAligns, options.maxEditDist)[options.maxEditDist != '0'], 
                         options.maxGapOpens, options.maxGapExtens, options.disallowLongDel, 
                         options.disallowIndel, ('',' -l %s'%options.seed)[options.seed!='-1'],
                         options.maxEditDistSeed, options.threads, options.mismatchPenalty, 
                         options.gapOpenPenalty, options.gapExtensPenalty, ('',' -c')[options.colorSpaceRev=='true'], 
                         ('',' -R')[options.suboptAlign=='true'], ('',' -N')[options.noIterSearch=='true'])
        if options.genAlignType == 'single':
            gen_alignment_cmds = '-n %s' % options.outputTopN
        elif options.genAlignType == 'paired':
            gen_alignment_cmds = '-a %s -o %s' % (options.maxInsertSize, options.maxOccurPairing)
#        print 'options.genAlignType: %s and commands: %s' % (options.genAlignType, gen_alignment_cmds)
    # set up output files
    tmp_align_out = tempfile.NamedTemporaryFile()
    tmp_align_out2 = tempfile.NamedTemporaryFile()
    # prepare actual aligning and generate aligning commands
    cmd2 = 'bwa aln %s %s %s > %s 2> /dev/null' % (aligning_cmds, options.ref, options.fastq, tmp_align_out.name)
    cmd2b = ''
    if options.genAlignType == 'paired':
        cmd2b = 'bwa aln %s %s %s > %s 2> /dev/null' % (aligning_cmds, options.ref, options.rfastq, tmp_align_out2.name)
        cmd3 = 'bwa sampe %s %s %s %s %s %s >> %s 2> /dev/null' % (gen_alignment_cmds, options.ref, tmp_align_out.name, tmp_align_out2.name, options.fastq, options.rfastq, options.output)
    else:
        cmd3 = 'bwa samse %s %s %s %s >> %s 2> /dev/null' % (gen_alignment_cmds, options.ref, tmp_align_out.name, options.fastq, options.output) 
    # align
    try:
        os.system(cmd2)
    except Exception, erf:
        stop_err("Error aligning sequence\n" + str(erf))
    # and again if paired data
    try:
        if cmd2b: 
            os.system(cmd2b)
    except Exception, erf:
        stop_err("Error aligning second sequence\n" + str(erf))
    # generate align
    try:
        os.system(cmd3)
    except Exception, erf:
        stop_err("Error sequence aligning sequence\n" + str(erf))
    # clean up temp files
    tmp_align_out.close()
    tmp_align_out2.close()
    # remove header if necessary
    if options.suppressHeader == 'true':
        tmp_out = tempfile.NamedTemporaryFile()
        cmd4 = 'cp %s %s' % (options.output, tmp_out.name)
        try:
            os.system(cmd4)
        except Exception, erf:
            stop_err("Error copying output file before removing headers\n" + str(erf))
        output = file(tmp_out.name, 'r')
        fout = file(options.output, 'w')
        header = True
        line = output.readline()
        while line.strip() != '':
            if header:
                if line.startswith('@HD') or line.startswith('@SQ') or line.startswith('@RG') or line.startswith('@PG') or line.startswith('@CO'):
                    pass
                else:
                    header = False
                    fout.write(line)
            else:
                fout.write(line)
            line = output.readline()
        fout.close()
        tmp_out.close()
    # clean up temp dir
    if os.path.exists(tmp_index_dir):
        shutil.rmtree(tmp_index_dir)
    
if __name__=="__main__": __main__()
