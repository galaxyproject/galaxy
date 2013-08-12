# rgtableRanks.py
#
# copyright ross lazarus (ross.lazarus@gmail.com) June 2012
# 
# all rights reserved
# Licensed under the LGPL for your pleasure

import sys 
import shutil 
import subprocess 
import os 
import time 
import tempfile 
import optparse

import random
import sys
import string

class concordRank:
    """ hold a term and a rank from each for each term in each file
    can calculate some simple metrics
    """

    def __init__(self,term):
        self.term = term
        self.fileranks = {} # name -> rank
        self.fileMaxfracs = {}
        self.nfiles = 0
        self.nhits = 0
        self.ndups = 0

    def addRank(self,f,frank):
        """ bump files and ranks
        """
        if not self.fileranks.get(f,None):
             self.fileranks[f] = frank
             self.nfiles += 1
        else:
            print '## Term %s has appeared again - ignoring' % self.term
            self.ndups += 1
            
    def addMaxfrac(self,f,maxFrac):
        """ bump files and max frac in any one sample
        """
        if not self.fileMaxfracs.get(f,None):
             self.fileMaxfracs[f] = maxFrac
             
    def median(self,v=[]):
        vlen = len(v)
        if vlen == 0:
            return None
        if vlen == 1:
            return v[0]
        v.sort()
        mid = vlen/2 # integer = lower 
        if vlen % 2 == 0: # is even
            res = sum([v[mid-1],v[mid]])/2.0
        else:
            res = v[mid]
        return res 

    def mean(self,v=[]):
        vlen = len(v)
        if vlen == 0:
            return None
        if vlen == 1:
            return v[0]
        m = sum(v)/float(vlen)
        return m

    def sd(self,v=[]):
        vlen = len(v)
        if vlen < 2:
            return None
        m = self.mean(v)
        sqd = sum([(x-m)**2 for x in v])/float(vlen-1)
        return sqd**0.5

    def getStats(self):
        mu = 0
        med = 0
        sigma = 0
        if self.nfiles > 0:
            ranks = self.fileranks.values()
            ranks.sort() # for median
            mu = self.mean(ranks)
            med = self.median(ranks)
            sigma = self.sd(ranks)
        return (mu,med,sigma)
        
    def getMaxfracStats(self):
        mu = 0
        med = 0
        sigma = 0
        if self.nfiles > 0:
            k = self.fileMaxfracs.keys()
            v = self.fileMaxfracs.values()
            fraclist = [(v[i],k[i]) for i in range(len(k))]  # decorate
            fraclist.sort() # for median
            files = [x[1] for x in fraclist]
            fracs = [x[0] for x in fraclist]
            maxfrac = fraclist[-1] # return (frac,file)
            mu = self.mean(fracs)
            med = self.median(fracs)
            sigma = self.sd(fracs)
        return (mu,med,sigma,maxfrac)
            

class tableRanker:
    """ 
    estimate variance and median rank for every term in an arbitrary collection of input files
    """

    def __init__(self,opts=None):
        """
        """
        self.opts = opts
        self.retcode = 0
        self.flist = opts.input_list
        self.fnames = opts.input_name
        assert len(self.flist) == len(self.fnames), '## Error: Differing name and filepath list lengths = %s and %s' % (self.flist,self.fnames)
        self.nfiles = len(self.flist)
        self.colnum = int(opts.colnum) - 1
        self.termdict = {}
        self.delim = opts.delim
        self.hasHeader = (opts.has_header == "True")
        self.ntoreport = int(opts.ntoreport)
        self.doMaxfrac = opts.startNorm # none if not set
        self.normColumns = []
        self.startNorm = self.endNorm = None
        if self.doMaxfrac:
            self.startNorm = int(opts.startNorm)
            self.endNorm = int(opts.endNorm)
            assert self.startNorm > 0 and self.endNorm > 0, 'Start of normal counts and end of normal counts must both be greater than zero - given %d:%d' % (opts.startNorm,opts.endNorm)
            assert self.startNorm < self.endNorm,'Start of normal counts column must be less than end normal counts column'
            self.normColumns = range(self.startNorm-1, self.endNorm) 
        if len(self.flist) > 0:
            self.readAll() # autorun
 
    def addTerm(self,t=None,f=None,frank=None,maxFrac=None):
        """ tell concordRank to go bump itself
        """
        if not self.termdict.get(t,None):
            self.termdict[t] = concordRank(t) # create
        self.termdict[t].addRank(f,frank)
        if maxFrac:
           self.termdict[t].addMaxfrac(f,maxFrac)

    def readOne(self,fnum,f,fname):
        """ read a file and create/bump all concord term records to record term hits
        """
        col = self.colnum 
        d = open(f,'r').readlines()
        if self.hasHeader:
            d = d[1:] # drop header
        d = [x.strip().split(self.delim) for x in d]
        terms = [(x[col],i+1) for i,x in enumerate(d)] # assume sorted already
        if self.doMaxfrac:
            normCounts = [[float(x[i]) for i in self.normColumns] for x in d]
            normSums = [sum(x) for x in normCounts]
            normFracs = [[x/normSums[j] for x in y] for j,y in enumerate(normCounts)]
            maxF = [max(x) for x in normFracs]
        else:
            maxF = [None for x in terms]
        for i,(t,frank) in enumerate(terms):
            self.addTerm(t,fname,frank,maxF[i])
            
    def readAll(self):
        """ loop over all files
        """
        for fnum,f in enumerate(self.flist):
              self.readOne(fnum,f,self.fnames[fnum])

    def doTest(self,nf = 6, nt = 10000):
        """ generate some fake data - no need for files
             print a simple top table
        """ 
        alph = map(None,string.letters)
        terms = []
        for i in range(nt):
            random.shuffle(alph)
            terms.append(''.join(alph[:3]))
        for f in range(nf):
            random.shuffle(alph)
            fn = ''.join(alph[:5])
            self.flist.append(fn)
            self.nfiles += 1
            random.shuffle(terms)
            for frank,term in enumerate(terms):
                self.addTerm(term,fn,frank)
        self.nfiles = len(self.flist)
        r = self.report()         
        print '\n'.join(r[:50])
        print 'flist=',self.flist

    def report(self):
        """
        """
        res = []
        for t in self.termdict.values():
            (mu,med,sigma) = t.getStats()
            if self.doMaxfrac:
                (fmu,fmed,fsigma,fmaxfrac) = t.getMaxfracStats()
                newres = [med,(t.term,str(med),str(sigma),str(t.nfiles),str(fmu),str(fsigma),str(fmaxfrac[0]),fmaxfrac[1])]
            else:
                newres = [med,(t.term,str(med),str(sigma),str(t.nfiles))]
            res.append(newres)
        res.sort() # decorated in rank order
        res = ['\t'.join(x[1]) for x in res] # undecorate and return only the results for printing
        if self.doMaxfrac:
           res.insert(0,'Term\tMedianRank\tSDRank\tNfiles\tMeanMaxfrac\tSDMaxfrac\t')
        else:
           res.insert(0,'Term\tMedianRank\tSDRank\tNfiles')
        if self.ntoreport == 0:
            return res # not truncated
        else:
            return res[:self.ntoreport]



if __name__ == "__main__":
    op = optparse.OptionParser()
    a = op.add_option
    a('--input_list',default=[],action="append")
    a('--input_name',default=[],action="append")
    a('--output_tab',default="None")
    a('--colnum',default='1')
    a('--ntoreport',default='100')
    a('--has_header',default="True")
    a('--delim',default='\t')
    a('--startNorm',default=None)
    a('--endNorm',default=None)
    opts, args = op.parse_args()
    if len(sys.argv) == 1: # test
        sup = tableRanker(opts=opts)
        sup.doTest(nf=5)
    else:
        r = tableRanker(opts)
        res = r.report()
        o = open(opts.output_tab,'w')
        o.write('\n'.join(res))
        o.write('\n')
        o.close()
        if r.retcode:
            sys.exit(r.retcode) # indicate failure to job runner

