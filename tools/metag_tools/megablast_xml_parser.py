#!/usr/bin/env python
    
import sys, os, re

if sys.version_info[:2] >= ( 2, 5 ):
    import xml.etree.cElementTree as ElementTree
else:
    from galaxy import eggs
    import pkg_resources; pkg_resources.require( "elementtree" )
    from elementtree import ElementTree

def stop_err( msg ):
    sys.stderr.write( "%s\n" % msg )
    sys.exit()

def __main__():
    source  = sys.argv[1]
    hspTags = [
           "Hsp_bit-score",
           "Hsp_evalue",
           "Hsp_query-from",
           "Hsp_query-to",
           "Hsp_hit-from",
           "Hsp_hit-to",
           "Hsp_query-frame",
           "Hsp_hit-frame",
           "Hsp_identity",
           "Hsp_align-len",
           "Hsp_qseq",
           "Hsp_hseq",
           "Hsp_midline"
          ]
    hspData = []

    # get an iterable
    try: 
        context = ElementTree.iterparse( source, events=( "start", "end" ) )
    except:
        stop_err( "Invalid data format." )
    # turn it into an iterator
    context = iter( context )
    # get the root element
    try:
        event, root = context.next()
    except:
        stop_err( "Invalid data format." )

    outfile = open( sys.argv[2], 'w' )
    try:
        for event, elem in context:
           # for every <Iteration> tag
           if event == "end" and elem.tag == "Iteration":
               query = elem.findtext( "Iteration_query-def" )
               qLen = elem.findtext( "Iteration_query-len" )
               # for every <Hit> within <Iteration>
               for hit in elem.findall( "Iteration_hits/Hit" ):
                   subject = hit.findtext( "Hit_id" )
                   if re.search( '^gi', subject ):
                       subject = subject.split('|')[1]
                   sLen = hit.findtext( "Hit_len" )
                   # for every <Hsp> within <Hit>
                   for hsp in hit.findall( "Hit_hsps/Hsp" ):
                        outfile.write( "%s\t%s\t%s\t%s" % ( query, qLen, subject, sLen ) )
                        for tag in hspTags:
                            outfile.write("\t%s" %(hsp.findtext( tag )))
                            #hspData.append( hsp.findtext( tag ) )
                        #hspData = []
                        outfile.write('\n')
               # prevents ElementTree from growing large datastructure
               root.clear()
               elem.clear()
    except:
        outfile.close()
        stop_err( "The input data is malformed, or there is more than one dataset in the input file. Error: %s" % sys.exc_info()[1] )

    outfile.close()

if __name__ == "__main__": __main__()
