#!/usr/bin/env python
import sys
import os
import random

from optparse import OptionParser
from pbpy.io.FastaIO import FastaEntry, SimpleFastaReader

class FastaStats:
    def __init__(self, argv):
        self.__parseOptions( argv )
        
    def __parseOptions(self, argv):
        usage = 'Usage: %prog [--help] [options] [fastaFileList]'
        parser = OptionParser( usage=usage )
        parser.add_option("--minContigLength", help="Minimum length of contigs to analyze")
        parser.add_option("--genomeLength", help="Length of genome to calculate N50s for.")
        parser.add_option("--outputFormat", help="Format of output [wiki]")
        parser.add_option("--noHeader", action="store_true",
            help="Don't output a header line" )
        parser.set_defaults( noHeader=False, 
            minContigLength=0, genomeLength=0, outputFormat="wiki")

        self.options, args = parser.parse_args(argv)
        
        if len(args) < 2:
            parser.error( 'Expected 1 arguments' )

        self.fastaFiles = args[1:]
        self.outputFormat = self.options.outputFormat
        self.genomeLength = int(self.options.genomeLength)
        self.minContigLength = int(self.options.minContigLength)
        self.statKeys = "File Num Sum Max Avg N50 99%".split(" ")

    def getStats(self, fastaFile):
        lengths = []
        for entry in SimpleFastaReader(fastaFile):
            if len(entry.sequence) < self.minContigLength: continue
            lengths.append( len(entry.sequence) )

        stats = {"File":fastaFile,   
            "Num":len(lengths),
            "Sum":sum(lengths), 
            "Max":max(lengths), 
            # "MinLenSum": sum( filter(lambda x: x > self.minContigLength, lengths)), 
            "Avg":int(sum(lengths)/float(len(lengths))),
            "N50":0,
            "99%":0}

        if self.genomeLength == 0: self.genomeLength = sum(lengths)
         
        lengths.sort()
        lengths.reverse()
        lenSum = 0
        stats["99%"] = len(lengths)
        for idx, length in enumerate(lengths):
            lenSum += length
            if (lenSum > self.genomeLength/2):
                stats["N50"] = length
                break
        lenSum = 0
        for idx, length in enumerate(lengths):
            lenSum += length
            if (lenSum > self.genomeLength*0.99):
                stats["99%"] = idx + 1
                break

        return stats

    def header(self):
        if self.outputFormat == "wiki":
            buffer = '{| width="200" cellspacing="1" cellpadding="1" border="1"\n'
            buffer += '|-\n'
            for key in self.statKeys:
                buffer += '| %s\n' % key
            return buffer
        elif self.outputFormat == "tsv":
            return "%s\n" % "\t".join(self.statKeys)
        else:
            sys.exit("Unsupported format %s" % self.outputFormat)
    
    def footer(self):
        if self.outputFormat == "wiki":
            return "|}\n"
        else:
            return ""

    def format(self, stats):
        if self.outputFormat == "wiki":
            buffer = "|-\n"
            for key in self.statKeys:
                buffer += "| %s\n" % stats[key]
            return buffer
        elif self.outputFormat == "tsv":
            return "%s\n" % "\t".join(map(lambda key: str(stats[key]), self.statKeys))
        else:
            sys.exit("Unsupported format %s" % self.outputFormat)
        
    def run(self):  
        if not self.options.noHeader:
            print self.header(),
        for file in self.fastaFiles: print self.format(self.getStats(file)),
        print self.footer()

if __name__=='__main__':
    app = FastaStats(sys.argv)
    app.run()
