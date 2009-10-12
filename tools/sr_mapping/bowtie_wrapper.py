#! /usr/bin/python

"""
Runs Bowtie on single-end or paired-end data.
"""

import optparse, os, sys, tempfile

def stop_err( msg ):
    sys.stderr.write( "%s\n" % msg )
    sys.exit()
 
def __main__():
    #Parse Command Line
    parser = optparse.OptionParser()
    parser.add_option('', '--threads', dest='threads', help='The number of threads to run')
    parser.add_option('', '--input1', dest='input1', help='The (forward or single-end) reads file in Sanger FASTQ format')
    parser.add_option('', '--input2', dest='input2', help='The reverse reads file in Sanger FASTQ format')
    parser.add_option('', '--output', dest='output', help='The output file')
    parser.add_option('', '--paired', dest='paired', help='Whether the data is single- or paired-end')
    parser.add_option('', '--genomeSource', dest='genomeSource', help='The type of reference provided')
    parser.add_option('', '--ref', dest='ref', help='The reference genome to use or index')
    parser.add_option('', '--skip', dest='skip', help='Skip the first n reads')
    parser.add_option('', '--alignLimit', dest='alignLimit', help='Only align the first n reads')
    parser.add_option('', '--trimH', dest='trimH', help='Trim n bases from high-quality (left) end of each read before alignment')
    parser.add_option('', '--trimL', dest='trimL', help='Trim n bases from low-quality (right) end of each read before alignment')
    parser.add_option('', '--mismatchSeed', dest='mismatchSeed', help='Maximum number of mismatches permitted in the seed')
    parser.add_option('', '--mismatchQual', dest='mismatchQual', help='Maximum permitted total of quality values at mismatched read positions')
    parser.add_option('', '--seedLen', dest='seedLen', help='Seed length')
    parser.add_option('', '--rounding', dest='rounding', help='Whether or not to round to the nearest 10 and saturating at 30')
    parser.add_option('', '--maqSoapAlign', dest='maqSoapAlign', help='Choose MAQ- or SOAP-like alignment policy')
    parser.add_option('', '--tryHard', dest='tryHard', help='Whether or not to try as hard as possible to find valid alignments when they exist')
    parser.add_option('', '--valAlign', dest='valAlign', help='Report up to n valid arguments per read')
    parser.add_option('', '--allValAligns', dest='allValAligns', help='Whether or not to report all valid alignments per read')
    parser.add_option('', '--suppressAlign', dest='suppressAlign', help='Suppress all alignments for a read if more than n reportable alignments exist')
    parser.add_option('', '--best', dest='best', help="Whether or not to make Bowtie guarantee that reported singleton alignments are 'best' in terms of stratum and in terms of the quality values at the mismatched positions")
    parser.add_option('', '--maxBacktracks', dest='maxBacktracks', help='Maximum number of backtracks permitted when aligning a read')
    parser.add_option('', '--strata', dest='strata', help='Whether or not to report only those alignments that fall in the best stratum if many valid alignments exist and are reportable')
    parser.add_option('', '--minInsert', dest='minInsert', help='Minimum insert size for valid paired-end alignments')
    parser.add_option('', '--maxInsert', dest='maxInsert', help='Maximum insert size for valid paired-end alignments')
    parser.add_option('', '--mateOrient', dest='mateOrient', help='The upstream/downstream mate orientation for valid paired-end alignment against the forward reference strand')
    parser.add_option('', '--maxAlignAttempt', dest='maxAlignAttempt', help='Maximum number of attempts Bowtie will make to match an alignment for one mate with an alignment for the opposite mate')
    parser.add_option('', '--forwardAlign', dest='forwardAlign', help='Whether or not to attempt to align the forward reference strand')
    parser.add_option('', '--reverseAlign', dest='reverseAlign', help='Whether or not to attempt to align the reverse-complement reference strand')
    parser.add_option('', '--offrate', dest='offrate', help='Override the offrate of the index to n')
    parser.add_option('', '--seed', dest='seed', help='Seed for pseudo-random number generator')
    parser.add_option('', '--dbkey', dest='dbkey', help='')
    parser.add_option('', '--params', dest='params', help='Whether to use default or specified parameters')
    parser.add_option('', '--iauto_b', dest='iauto_b', help='Automatic or specified behavior')
    parser.add_option('', '--ipacked', dest='ipacked', help='Whether or not to use a packed representation for DNA strings')
    parser.add_option('', '--ibmax', dest='ibmax', help='Maximum number of suffixes allowed in a block')
    parser.add_option('', '--ibmaxdivn', dest='ibmaxdivn', help='Maximum number of suffixes allowed in a block as a fraction of the length of the reference')
    parser.add_option('', '--idcv', dest='idcv', help='The period for the difference-cover sample')
    parser.add_option('', '--inodc', dest='inodc', help='Whether or not to disable the use of the difference-cover sample')
    parser.add_option('', '--inoref', dest='inoref', help='Whether or not to build the part of the reference index used only in paried-end alignment')
    parser.add_option('', '--ioffrate', dest='ioffrate', help='How many rows get marked during annotation of some or all of the Burrows-Wheeler rows')
    parser.add_option('', '--iftab', dest='iftab', help='The size of the lookup table used to calculate an initial Burrows-Wheeler range with respect to the first n characters of the query')
    parser.add_option('', '--intoa', dest='intoa', help='Whether or not to convert Ns in the reference sequence to As')
    parser.add_option('', '--iendian', dest='iendian', help='Endianness to use when serializing integers to the index file')
    parser.add_option('', '--iseed', dest='iseed', help='Seed for the pseudorandom number generator')
    parser.add_option('', '--icutoff', dest='icutoff', help='Number of first bases of the reference sequence to index')
    parser.add_option('', '--indexSettings', dest='index_settings', help='Whether or not indexing options are to be set')
    parser.add_option('', '--suppressHeader', dest='suppressHeader', help='Suppress header')
    (options, args) = parser.parse_args()
    
    # index if necessary
    if options.genomeSource == 'history':
        # set up commands
        if options.index_settings =='index_pre_set':
            indexing_cmds = ''
        else:
            try:
                indexing_cmds = '%s %s %s %s %s %s %s --offrate %s %s %s %s %s %s' % \
                                (('','--noauto')[options.iauto_b=='set'], 
                                 ('','--packed')[options.ipacked=='packed'],
                                 ('','--bmax %s'%options.ibmax)[options.ibmax!='None' and options.ibmax>=1], 
                                 ('','--bmaxdivn %s'%options.ibmaxdivn)[options.ibmaxdivn!='None'],
                                 ('','--dcv %s'%options.idcv)[options.idcv!='None'], 
                                 ('','--nodc')[options.inodc=='nodc'],
                                 ('','--noref')[options.inoref=='noref'], options.ioffrate, 
                                 ('','--ftabchars %s'%options.iftab)[int(options.iftab)>=0], 
                                 ('','--ntoa')[options.intoa=='yes'], 
                                 ('--little','--big')[options.iendian=='big'],
                                 ('','--seed %s'%options.iseed)[int(options.iseed)>0], 
                                 ('','--cutoff %s'%options.icutoff)[int(options.icutoff)>0])
            except ValueError:
                indexing_cmds = ''
                
        # make temp directory for placement of indices and copy reference file there
        tmp_dir = tempfile.gettempdir()
        try:
            os.system('cp %s %s' % (options.ref, tmp_dir))
        except Exception, erf:
            stop_err('Error creating temp directory for indexing purposes\n' + str(erf))
        options.ref = os.path.join(tmp_dir,os.path.split(options.ref)[1])
        cmd1 = 'cd %s; bowtie-build %s -f %s %s 2> /dev/null' % (tmp_dir, indexing_cmds, options.ref, options.ref)
        try:
            os.system(cmd1)
        except Exception, erf:
            stop_err('Error indexing reference sequence\n' + str(erf))
    
    # set up aligning and generate aligning command options
    # automatically set threads to 8 in both cases
    if options.params == 'pre_set':
        aligning_cmds = '-p %s -S' % options.threads
    else:
        try:
            aligning_cmds = '%s %s %s %s %s %s %s %s %s %s %s %s %s %s ' \
                            '%s %s %s %s %s %s %s %s %s %s -p %s -S' % \
                            (('','-s %s'%options.skip)[options.skip!='None'], 
                             ('','-u %s'%options.alignLimit)[int(options.alignLimit)>0],
                             ('','-5 %s'%options.trimH)[int(options.trimH)>=0], 
                             ('','-3 %s'%options.trimL)[int(options.trimL)>=0], 
                             ('','-n %s'%options.mismatchSeed)[options.mismatchSeed=='0' or options.mismatchSeed=='1' or options.mismatchSeed=='2' or options.mismatchSeed=='3'], 
                             ('','-e %s'%options.mismatchQual)[int(options.mismatchQual)>=0], 
                             ('','-l %s'%options.seedLen)[int(options.seedLen)>=5], 
                             ('','--nomaqround')[options.rounding=='noRound'],
                             ('','-v %s'%options.maqSoapAlign)[options.maqSoapAlign!='-1'],
                             ('','-I %s'%options.minInsert)[options.minInsert!='None'], 
                             ('','-X %s'%options.maxInsert)[options.maxInsert!='None'], 
                             ('','--%s'%options.mateOrient)[options.mateOrient!='None'],
                             ('','--pairtries %s'%options.maxAlignAttempt)[options.maxAlignAttempt!='None' and int(options.maxAlignAttempt)>=0],
                             ('','--nofw')[options.forwardAlign=='noForward'],
                             ('','--norc')[options.reverseAlign=='noReverse'],
                             ('','--maxbts %s'%options.maxBacktracks)[options.maxBacktracks!='None' and (options.mismatchSeed=='2' or options.mismatchSeed=='3')], 
                             ('','-y')[options.tryHard=='doTryHard'],
                             ('','-k %s'%options.valAlign)[options.valAlign!='None' and int(options.valAlign)>=0], 
                             ('','-a')[options.allValAligns=='doAllValAligns' and int(options.allValAligns)>=0],
                             ('','-m %s'%options.suppressAlign)[int(options.suppressAlign)>=0], 
                             ('','--best')[options.best=='doBest'],
                             ('','--strata')[options.strata=='doStrata'],
                             ('','-o %s'%options.offrate)[int(options.offrate)>=0],
                             ('','--seed %s'%options.seed)[int(options.seed)>=0],
                             options.threads)
        except ValueError:
            aligning_cmds = '-p %s -S' % options.threads 

    # prepare actual aligning commands
    if options.paired == 'paired':
        cmd2 = 'bowtie %s %s -1 %s -2 %s > %s 2> /dev/null' % (aligning_cmds, options.ref, options.input1, options.input2, options.output) 
    else:
        cmd2 = 'bowtie %s %s %s > %s 2> /dev/null' % (aligning_cmds, options.ref, options.input1, options.output) 

    # align
    try:
        os.system(cmd2)
    except Exception, erf:
        stop_err("Error aligning sequence\n" + str(erf))

    # remove header if necessary
    if options.suppressHeader == 'true':
        tmp_out = tempfile.NamedTemporaryFile()
        cmd3 = 'cp %s %s' % (options.output, tmp_out.name)
        try:
            os.system(cmd3)
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

if __name__=="__main__": __main__()
