import cElementTree #python 2.5 xml.etree.cElementTree    
import sys, os

def parse_megablast_xml_output(infile,outfile = sys.stdout):

    source  = infile #sys.argv[1]

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
    context = cElementTree.iterparse(source, events=("start", "end"))

    # turn it into an iterator
    context = iter(context)

    # get the root element
    event, root = context.next()

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
    return

def __main__():
    megablast_command = "megablast -d Ecoli.fa -i Ecoli.30bp.random.fa -m 7 "
    infile = os.popen(megablast_command)
    outfile = None
    if len(sys.argv) > 1:
        outfile = open(sys.argv[1],'w')
    parse_megablast_xml_output(infile, outfile)
    
if __name__ == "__main__": __main__()
