#!/usr/bin/env python
#
#Copyright (c) 2011, Pacific Biosciences of California, Inc.
#
#All rights reserved.
#
#Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:
#    * Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
#    * Neither the name of Pacific Biosciences nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.
#
#THIS SOFTWARE IS PROVIDED BY PACIFIC BIOSCIENCES AND ITS CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
#WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL PACIFIC BIOSCIENCES OR ITS CONTRIBUTORS BE LIABLE FOR ANY
#DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
#LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
import sys, os
from optparse import OptionParser
from galaxy import eggs
import pkg_resources
pkg_resources.require( 'bx-python' )
from bx.seq.fasta import FastaReader

def getStats( fastaFile, genomeLength, minContigLength ):
    lengths = []
    stats = { "Num" : 0,
              "Sum" : 0, 
              "Max" : 0, 
              "Avg" : 0,
              "N50" : 0,
              "99%" : 0 }
    fasta_reader = FastaReader( open( fastaFile, 'rb' ) )
    while True:
        seq = fasta_reader.next()
        if not seq:
            break
        if seq.length < minContigLength:
            continue
        lengths.append( seq.length )
    if lengths:
        stats[ 'Num' ] = len( lengths )
        stats[ 'Sum' ] = sum( lengths )
        stats[ 'Max' ] = max( lengths )
        stats[ 'Avg' ] = int( sum( lengths ) / float( len( lengths ) ) )
        stats[ 'N50' ] = 0
        stats[ '99%' ] = 0
        if genomeLength == 0:
            genomeLength = sum( lengths )
        lengths.sort()
        lengths.reverse()
        lenSum = 0
        stats[ "99%" ] = len( lengths )
        for idx, length in enumerate( lengths ):
            lenSum += length
            if ( lenSum > genomeLength / 2 ):
                stats[ "N50" ] = length
                break
        lenSum = 0
        for idx, length in enumerate( lengths ):
            lenSum += length
            if lenSum > genomeLength * 0.99:
                stats[ "99%" ] = idx + 1
                break
    return stats

def __main__():
    #Parse Command Line
    usage = 'Usage: %prog input output --minContigLength'
    parser = OptionParser( usage=usage )
    parser.add_option( "--minContigLength", dest="minContigLength", help="Minimum length of contigs to analyze" )
    parser.add_option( "--genomeLength", dest="genomeLength", help="Length of genome for which to calculate N50s" )
    parser.set_defaults( minContigLength=0, genomeLength=0 )
    options, args = parser.parse_args()
    input_fasta_file = args[ 0 ]
    output_tabular_file = args[ 1 ]
    statKeys = "Num Sum Max Avg N50 99%".split( " " )
    stats = getStats( input_fasta_file, int( options.genomeLength ), int( options.minContigLength ) )
    fout = open( output_tabular_file, "w" )
    fout.write( "%s\n" % "\t".join( map( lambda key: str( stats[ key ] ), statKeys ) ) )
    fout.close()

if __name__=="__main__": __main__()
