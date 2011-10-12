#!/usr/bin/env python
from optparse import OptionParser, SUPPRESS_HELP
import os, random, quake

############################################################
# cov_model.py
#
# Given a file of kmer counts, reports the cutoff to use
# to separate trusted/untrusted kmers.
############################################################

############################################################
# main
############################################################
def main():
    usage = 'usage: %prog [options] <counts file>'
    parser = OptionParser(usage)
    parser.add_option('--int', dest='count_kmers', action='store_true', default=False, help='Kmers were counted as integers w/o the use of quality values [default: %default]')
    parser.add_option('--ratio', dest='ratio', type='int', default=200, help='Likelihood ratio to set trusted/untrusted cutoff [default: %default]')
    parser.add_option('--no_sample', dest='no_sample', action='store_true', default=False, help='Do not sample kmer coverages into kmers.txt because its already done [default: %default]')
    # help='Model kmer coverage as a function of GC content of kmers [default: %default]'
    parser.add_option('--gc', dest='model_gc', action='store_true', default=False, help=SUPPRESS_HELP)
    (options, args) = parser.parse_args()

    if len(args) != 1:
        parser.error('Must provide kmers counts file')
    else:
        ctsf = args[0]

    if options.count_kmers:
        model_cutoff(ctsf, options.ratio)
        print 'Cutoff: %s' % open('cutoff.txt').readline().rstrip()
        
    else:
        if options.model_gc:
            model_q_gc_cutoffs(ctsf, 25000, options.ratio)
        else:
            model_q_cutoff(ctsf, 50000, options.ratio, options.no_sample)
            print 'Cutoff: %s' % open('cutoff.txt').readline().rstrip()


############################################################
# model_cutoff
#
# Make a histogram of kmers to give to R to learn the cutoff
############################################################
def model_cutoff(ctsf, ratio):
    # make kmer histogram
    cov_max = 0
    for line in open(ctsf):
        cov = int(line.split()[1])
        if cov > cov_max:
            cov_max = cov

    kmer_hist = [0]*cov_max
    for line in open(ctsf):
        cov = int(line.split()[1])
        kmer_hist[cov-1] += 1

    cov_out = open('kmers.hist', 'w')
    for cov in range(0,cov_max):
        if kmer_hist[cov]:
            print >> cov_out, '%d\t%d' % (cov+1,kmer_hist[cov])
    cov_out.close()

    os.system('R --slave --args %d < %s/cov_model.r 2> r.log' % (ratio,quake.quake_dir))


############################################################
# model_q_cutoff
#
# Sample kmers to give to R to learn the cutoff
# 'div100' is necessary when the number of kmers is too 
# large for random.sample, so we only consider every 100th
# kmer.
############################################################
def model_q_cutoff(ctsf, sample, ratio, no_sample=False):
    if not no_sample:
        # count number of kmer coverages
        num_covs = 0
        for line in open(ctsf):
            num_covs += 1

        # choose random kmer coverages
        div100 = False
        if sample >= num_covs:
            rand_covs = range(num_covs)
        else:
            if num_covs > 1000000000:
                div100 = True
                rand_covs = random.sample(xrange(num_covs/100), sample)
            else:
                rand_covs = random.sample(xrange(num_covs), sample)
        rand_covs.sort()

        # print to file
        out = open('kmers.txt', 'w')
        kmer_i = 0
        rand_i = 0
        for line in open(ctsf):
            if div100:
                if kmer_i % 100 == 0 and kmer_i/100 == rand_covs[rand_i]:
                    print >> out, line.split()[1]
                    rand_i += 1
                    if rand_i >= sample:
                        break
            else:
                if kmer_i == rand_covs[rand_i]:
                    print >> out, line.split()[1]
                    rand_i += 1
                    if rand_i >= sample:
                        break
            kmer_i += 1
        out.close()

    os.system('R --slave --args %d < %s/cov_model_qmer.r 2> r.log' % (ratio,quake.quake_dir))


############################################################
# model_q_gc_cutoffs
#
# Sample kmers to give to R to learn the cutoff for each
# GC value
############################################################
def model_q_gc_cutoffs(ctsf, sample, ratio):
    # count number of kmer coverages at each at
    k = len(open(ctsf).readline().split()[0])
    num_covs_at = [0]*(k+1)
    for line in open(ctsf):
        kmer = line.split()[0]
        num_covs_at[count_at(kmer)] += 1

    # for each AT bin
    at_cutoffs = []
    for at in range(1,k):
        # sample covs
        if sample >= num_covs_at[at]:
            rand_covs = range(num_covs_at[at])
        else:
            rand_covs = random.sample(xrange(num_covs_at[at]), sample)
        rand_covs.sort()

        # print to file
        out = open('kmers.txt', 'w')
        kmer_i = 0
        rand_i = 0
        for line in open(ctsf):
            (kmer,cov) = line.split()
            if count_at(kmer) == at:
                if kmer_i == rand_covs[rand_i]:
                    print >> out, cov
                    rand_i += 1
                    if rand_i >= sample:
                        break
                kmer_i += 1
        out.close()
        
        os.system('R --slave --args %d < %s/cov_model_qmer.r 2> r%d.log' % (ratio,quake.quake_dir,at))

        at_cutoffs.append( open('cutoff.txt').readline().rstrip() )
        if at in [1,k-1]:   # setting extremes to next closests
            at_cutoffs.append( open('cutoff.txt').readline().rstrip() )

        os.system('mv kmers.txt kmers.at%d.txt' % at)
        os.system('mv cutoff.txt cutoff.at%d.txt' % at)

    out = open('cutoffs.gc.txt','w')
    print >> out, '\n'.join(at_cutoffs)
    out.close()


############################################################
# model_q_gc_cutoffs_bigmem
#
# Sample kmers to give to R to learn the cutoff for each
# GC value
############################################################
def model_q_gc_cutoffs_bigmem(ctsf, sample, ratio):
    # input coverages
    k = 0
    for line in open(ctsf):
        (kmer,cov) = line.split()
        if k == 0:
            k = len(kmer)
            at_covs = ['']*(k+1)
        else:
            at = count_at(kmer)
            if at_covs[at]:
                at_covs[at].append(cov)
            else:
                at_covs[at] = [cov]

    for at in range(1,k):
        print '%d %d' % (at,len(at_covs[at]))

    # for each AT bin
    at_cutoffs = []
    for at in range(1,k):
        # sample covs
        if sample >= len(at_covs[at]):
            rand_covs = at_covs[at]
        else:
            rand_covs = random.sample(at_covs[at], sample)

        # print to file
        out = open('kmers.txt', 'w')
        for rc in rand_covs:
            print >> out, rc
        out.close()

        os.system('R --slave --args %d < %s/cov_model_qmer.r 2> r%d.log' % (ratio,quake.quake_dir,at))

        at_cutoffs.append( open('cutoff.txt').readline().rstrip() )
        if at in [1,k-1]:   # setting extremes to next closests
            at_cutoffs.append( open('cutoff.txt').readline().rstrip() )

        os.system('mv kmers.txt kmers.at%d.txt' % at)
        os.system('mv cutoff.txt cutoff.at%d.txt' % at)

    out = open('cutoffs.gc.txt','w')
    print >> out, '\n'.join(at_cutoffs)
    out.close()
        
    
############################################################
# count_at
#
# Count A's and T's in the given sequence
############################################################
def count_at(seq):
    return len([nt for nt in seq if nt in ['A','T']])


############################################################
# __main__
############################################################
if __name__ == '__main__':
    main()
