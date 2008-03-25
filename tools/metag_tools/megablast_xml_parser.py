#! /usr/bin/python
    
import cElementTree 
import sys, os

def parse_megablast_xml_output(infile_name,outfile_name):

    source  = infile_name
    outfile = open(outfile_name, 'w')
    
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
        context = cElementTree.iterparse(source, events=("start", "end"))
    except:
        print >> sys.stderr, "Please note: this tool is for megablast output option -m 7 only."
        print >> sys.stderr, "The file has inappropriate format for this tool."
        sys.exit()
        
    # turn it into an iterator
    context = iter(context)

    # get the root element
    try:
        event, root = context.next()
    except:
        print >> sys.stderr, "Please note: this tool is for megablast output option -m 7 only."
        print >> sys.stderr, "The file has inappropriate format for this tool."
        sys.exit()
    
    try:    
        for event, elem in context:
           # for every <Iteration> tag
           if event == "end" and elem.tag == "Iteration":
               query = elem.findtext("Iteration_query-def")
               qLen  = elem.findtext("Iteration_query-len")
               # for every <Hit> within <Iteration>
               for hit in elem.findall("Iteration_hits/Hit/"):
                   subject = hit.findtext("Hit_id")
                   sLen    = hit.findtext("Hit_len")
                   # for every <Hsp> within <Hit>
                   for hsp in hit.findall("Hit_hsps/Hsp"):
                        for tag in hspTags:
                            hspData.append(hsp.findtext(tag))
                        print >> outfile, query, '\t', qLen, '\t', subject, '\t', sLen, '\t', hspData
                        hspData = []

               # prevents ElementTree from growing large datastructure
               root.clear()
               elem.clear()
    except:
        print >> sys.stderr, "Your file may contain tags that are not recognized by the parser."
        print >> sys.stderr, "Please use megablast output option -m 7 only."
        sys.exit()
    
    outfile.close()
    
    return

def __main__():

    infile_name = sys.argv[1]
    outfile_name = sys.argv[2]
    
    parse_megablast_xml_output(infile_name, outfile_name)

    
if __name__ == "__main__": __main__()
