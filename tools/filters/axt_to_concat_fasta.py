#!/usr/bin/env python
"""
Adapted from bx/scripts/axt_to_concat_fasta.py
"""
from galaxy import eggs
import pkg_resources
pkg_resources.require( "bx-python" )

import sys
import bx.align.axt

def usage(s=None):
	message = """
axt_to_fasta species1 species2 < axt_file > fasta_file
"""
	if (s == None): sys.exit (message)
	else:           sys.exit ("%s\n%s" % (s,message))


def main():

	# check the command line
	species1 = sys.argv[1]
	species2 = sys.argv[2]

	# convert the alignment blocks

	reader = bx.align.axt.Reader(sys.stdin,support_ids=True,\
	                             species1=species1,species2=species2)
	sp1text = list()
	sp2text = list()
	for a in reader:
		sp1text.append(a.components[0].text)
		sp2text.append(a.components[1].text)
	sp1seq = "".join(sp1text)
	sp2seq = "".join(sp2text)
	print_component_as_fasta(sp1seq,species1)
	print_component_as_fasta(sp2seq,species2)
		


# $$$ this should be moved to a bx.align.fasta module

def print_component_as_fasta(text,src):
	header = ">" + src
	print header
	print text


if __name__ == "__main__": main()

