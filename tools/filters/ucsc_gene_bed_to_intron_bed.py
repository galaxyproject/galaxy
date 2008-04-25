#!/usr/bin/env python

"""
Read a table dump in the UCSC gene table format and print a tab separated
list of intervals corresponding to requested features of each gene.

usage: ucsc_gene_table_to_intervals.py [options]

options:
  -h, --help                  show this help message and exit
  -rREGION, --region=REGION
                              Limit to region: one of coding, utr3, utr5, transcribed [default]
  -e, --exons                 Only print intervals overlapping an exon
  -i, --input=inputfile       input file
  -o, --output=outputfile     output file
"""

import optparse, string, sys

assert sys.version_info[:2] >= ( 2, 4 )

def main():

    # Parse command line    
    parser = optparse.OptionParser( usage="%prog [options] " )
    #parser.add_option( "-r", "--region", dest="region", default="transcribed",
    #                   help="Limit to region: one of coding, utr3, utr5, transcribed [default]" )
    #parser.add_option( "-e", "--exons",  action="store_true", dest="exons",
    #                   help="Only print intervals overlapping an exon" )
    parser.add_option( "-s", "--strand",  action="store_true", dest="strand",
                       help="Print strand after interval" )
    parser.add_option( "-i", "--input",  dest="input",  default=None,
                       help="Input file" )
    parser.add_option( "-o", "--output", dest="output", default=None,
                       help="Output file" )
    options, args = parser.parse_args()
    #assert options.region in ( 'coding', 'utr3', 'utr5', 'transcribed' ), "Invalid region argument"
    
    try:
        out_file = open (options.output,"w")
    except:
        print >> sys.stderr, "Bad output file."
        sys.exit(0)
    
    try:
        in_file = open (options.input)
    except:
        print >> sys.stderr, "Bad input file."
        sys.exit(0)
    
    #print "Region:", options.region+";"
    #print "Only overlap with Exons:",
    #if options.exons:
    #    print "Yes"
    #else:
    #    print "No"
    
    # Read table and handle each gene
    
    for line in in_file:
        try:
	    #print ("len: %d", len(line))
            if line[0:1] == "#":
                continue
	   
            # Parse fields from gene tabls
            fields = line.split( '\t' )
            chrom     = fields[0]
            tx_start  = int( fields[1] )
            tx_end    = int( fields[2] )
            name      = fields[3]
            strand    = fields[5].replace(" ","_")
            cds_start = int( fields[6] )
            cds_end   = int( fields[7] )
	    	
	    exon_starts = map( int, fields[11].rstrip( ',\n' ).split( ',' ) )
            exon_starts = map((lambda x: x + tx_start ), exon_starts)
            exon_ends = map( int, fields[10].rstrip( ',\n' ).split( ',' ) )
            exon_ends = map((lambda x, y: x + y ), exon_starts, exon_ends);
	    
	    i=0
	    while i < len(exon_starts)-1:
            	intron_starts = exon_ends[i] + 1
		intron_ends = exon_starts[i+1] - 1
		if strand: print_tab_sep(out_file, chrom, intron_starts, intron_ends, name, "0", strand )
                else: print_tab_sep(out_file, chrom, intron_starts, intron_ends )
		i+=1
            # If only interested in exons, print the portion of each exon overlapping
            # the region of interest, otherwise print the span of the region
            
        except:
            continue

def print_tab_sep(out_file, *args ):
    """Print items in `l` to stdout separated by tabs"""
    print >>out_file, string.join( [ str( f ) for f in args ], '\t' )

if __name__ == "__main__": main()
