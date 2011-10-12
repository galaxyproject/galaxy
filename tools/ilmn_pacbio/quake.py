#!/usr/bin/env python
from optparse import OptionParser, SUPPRESS_HELP
import os, random, sys
import cov_model

############################################################
# quake.py
#
# Launch pipeline to correct errors in Illumina sequencing
# reads.
############################################################

#r_dir = '/nfshomes/dakelley/research/error_correction/bin'
quake_dir = os.path.abspath(os.path.dirname(sys.argv[0]))

############################################################
# main
############################################################
def main():
    usage = 'usage: %prog [options]'
    parser = OptionParser(usage)
    parser.add_option('-r', dest='readsf', help='Fastq file of reads')
    parser.add_option('-f', dest='reads_listf', help='File containing fastq file names, one per line or two per line for paired end reads.')
    parser.add_option('-k', dest='k', type='int', help='Size of k-mers to correct')
    parser.add_option('-p', dest='proc', type='int', default=4, help='Number of processes [default: %default]')
    parser.add_option('-q', dest='quality_scale', type='int', default=-1, help='Quality value ascii scale, generally 64 or 33. If not specified, it will guess.')
    parser.add_option('--no_count', dest='no_count', action='store_true', default=False, help='Kmers are already counted and in expected file [reads file].qcts or [reads file].cts [default: %default]')
    parser.add_option('--no_cut', dest='no_cut', action='store_true', default=False, help='Coverage model is optimized and cutoff was printed to expected file cutoff.txt [default: %default]')
    parser.add_option('--int', dest='counted_kmers', action='store_true', default=False, help='Kmers were counted as integers w/o the use of quality values [default: %default]')
    parser.add_option('--ratio', dest='ratio', type='int', default=200, help='Likelihood ratio to set trusted/untrusted cutoff.  Generally set between 10-1000 with lower numbers suggesting a lower threshold. [default: %default]')
    # help='Model kmer coverage as a function of GC content of kmers [default: %default]'
    parser.add_option('--gc', dest='model_gc', action='store_true', default=False, help=SUPPRESS_HELP)
    parser.add_option('--headers', action='store_true', default=False, help='Output original read headers (i.e. pass --headers to correct)' )
    (options, args) = parser.parse_args()

    if not options.readsf and not options.reads_listf:
        parser.error('Must provide fastq file of reads with -r or file with list of fastq files of reads with -f')
    if not options.k:
        parser.error('Must provide k-mer size with -k')
    if options.quality_scale == -1:
        options.quality_scale = guess_quality_scale(options.readsf, options.reads_listf)

    if options.counted_kmers:
        cts_suf = 'cts'
    else:
        cts_suf = 'qcts'
    if options.readsf:
        ctsf = '%s.%s' % (os.path.splitext( os.path.split(options.readsf)[1] )[0], cts_suf)
        reads_str = '-r %s' % options.readsf
    else:
        ctsf = '%s.%s' % (os.path.split(options.reads_listf)[1], cts_suf)
        reads_str = '-f %s' % options.reads_listf

    if not options.no_count and not options.no_cut:
        count_kmers(options.readsf, options.reads_listf, options.k, ctsf, options.quality_scale)

    if not options.no_cut:
        # model coverage
        if options.counted_kmers:
            cov_model.model_cutoff(ctsf, options.ratio)
        else:
            if options.model_gc:
                cov_model.model_q_gc_cutoffs(ctsf, 10000, options.ratio)
            else:
                cov_model.model_q_cutoff(ctsf, 25000, options.ratio)


    if options.model_gc:
        # run correct C++ code
        os.system('%s/correct %s -k %d -m %s -a cutoffs.gc.txt -p %d -q %d' % (quake_dir,reads_str, options.k, ctsf, options.proc, options.quality_scale))

    else:
        cutoff = open('cutoff.txt').readline().rstrip()

        # run correct C++ code
        headers = '--headers' if options.headers else ''
        os.system('%s/correct %s %s -k %d -m %s -c %s -p %d -q %d' % (quake_dir,headers, reads_str, options.k, ctsf, cutoff, options.proc, options.quality_scale))


################################################################################
# guess_quality_scale
# Guess at ascii scale of quality values by examining
# a bunch of reads and looking for quality values < 64,
# in which case we set it to 33.
################################################################################
def guess_quality_scale(readsf, reads_listf):
    reads_to_check = 1000
    if not readsf:
        readsf = open(reads_listf).readline().split()[0]

    fqf = open(readsf)
    reads_checked = 0
    header = fqf.readline()
    while header and reads_checked < reads_to_check:
        seq = fqf.readline()
        mid = fqf.readline()
        qual = fqf.readline().rstrip()
        reads_checked += 1
        for q in qual:
            if ord(q) < 64:
                print 'Guessing quality values are on ascii 33 scale'
                return 33
        header = fqf.readline()

    print 'Guessing quality values are on ascii 64 scale'
    return 64
        


############################################################
# count_kmers
#
# Count kmers in the reads file using AMOS count-kmers or
# count-qmers
############################################################
def count_kmers(readsf, reads_listf, k, ctsf, quality_scale):
    # find files
    fq_files = []
    if readsf:
        fq_files.append(readsf)
    else:
        for line in open(reads_listf):
            for fqf in line.split():
                fq_files.append(fqf)

    if ctsf[-4:] == 'qcts':
        os.system('cat %s | %s/count-qmers -k %d -q %d > %s' % (' '.join(fq_files), quake_dir, k, quality_scale, ctsf))
    else:
        os.system('cat %s | %s/count-kmers -k %d > %s' % (' '.join(fq_files), quake_dir, k, ctsf))
    
            
############################################################
# __main__
############################################################
if __name__ == '__main__':
    main()
