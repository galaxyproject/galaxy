#!/usr/bin/env python

"""
Condenses pileup format into ranges of bases.

usage: %prog [options]
   -i, --input=i: Input pileup file
   -o, --output=o: Output pileup
   -c, --coverage=c: Coverage
   -f, --format=f: Pileup format
   -b, --base=b: Base to select
   -s, --seq_column=s: Sequence column
   -l, --loc_column=l: Base location column
   -r, --base_column=r: Reference base column
   -C, --cvrg_column=C: Coverage column
"""

from galaxy import eggs
import pkg_resources; pkg_resources.require( "bx-python" )
from bx.cookbook import doc_optparse
import sys

def stop_err( msg ):
    sys.stderr.write( msg )
    sys.exit()

def __main__():
    strout = ''
    #Parse Command Line
    options, args = doc_optparse.parse( __doc__ )
    coverage = int(options.coverage)
    fin = file(options.input, 'r')
    fout = file(options.output, 'w')
    inLine = fin.readline()
    if options.format == 'six':
        seqIndex = 0
        locIndex = 1
        baseIndex = 2
        covIndex = 3
    elif options.format == 'ten':
        seqIndex = 0
        locIndex = 1
        if options.base == 'first':
            baseIndex = 2
        else:
            baseIndex = 3
        covIndex = 7
    else:
        seqIndex = int(options.seq_column) - 1
        locIndex = int(options.loc_column) - 1
        baseIndex = int(options.base_column) - 1
        covIndex = int(options.cvrg_column) - 1
    lastSeq = ''
    lastLoc = -1
    locs = []
    startLoc = -1
    bases = []
    while inLine.strip() != '':
        lineParts = inLine.split('\t')
        try:
            seq, loc, base, cov = lineParts[seqIndex], int(lineParts[locIndex]), lineParts[baseIndex], int(lineParts[covIndex])
        except IndexError, ei:
            if options.format == 'ten':
                stop_err( 'It appears that you have selected 10 columns while your file has 6. Make sure that the number of columns you specify matches the number in your file.\n' + str( ei ) )
            else:
                stop_err( 'There appears to be something wrong with your column index values.\n' + str( ei ) )
        except ValueError, ev:
            if options.format == 'six':
                stop_err( 'It appears that you have selected 6 columns while your file has 10. Make sure that the number of columns you specify matches the number in your file.\n' + str( ev ) )
            else:
                stop_err( 'There appears to be something wrong with your column index values.\n' + str( ev ) )
#        strout += str(startLoc) + '\n'
#        strout += str(bases) + '\n'
#        strout += '%s\t%s\t%s\t%s\n' % (seq, loc, base, cov)
        if loc == lastLoc+1 or lastLoc == -1:
            if cov >= coverage:
                if seq == lastSeq or lastSeq == '':
                    if startLoc == -1:
                        startLoc = loc
                    locs.append(loc)
                    bases.append(base)
                else:
                    if len(bases) > 0:
                        fout.write('%s\t%s\t%s\t%s\n' % (lastSeq, startLoc-1, lastLoc, ''.join(bases)))
                    startLoc = loc
                    locs = [loc]
                    bases = [base]
            else:
                if len(bases) > 0:
                    fout.write('%s\t%s\t%s\t%s\n' % (lastSeq, startLoc-1, lastLoc, ''.join(bases)))
                startLoc = -1
                locs = []
                bases = []
        else:
            if len(bases) > 0:
                fout.write('%s\t%s\t%s\t%s\n' % (lastSeq, startLoc-1, lastLoc, ''.join(bases)))
            if cov >= coverage:
                startLoc = loc
                locs = [loc]
                bases = [base]
            else:
                startLoc = -1
                locs = []
                bases = []
        lastSeq = seq
        lastLoc = loc
        inLine = fin.readline()
    if len(bases) > 0:
        fout.write('%s\t%s\t%s\t%s\n' % (lastSeq, startLoc-1, lastLoc, ''.join(bases)))
    fout.close()
    fin.close()
    
#    import sys
#    strout += file(fout.name,'r').read()
#    sys.stderr.write(strout)

if __name__ == "__main__" : __main__()
