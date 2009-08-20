#!/usr/bin/env python
from Bio import GenBank
import sys, os, textwrap

assert sys.version_info[:2] >= ( 2, 4 )

def make_fasta(rec):
    '''Creates fasta format from a record'''
    gi   = rec.annotations.get('gi','')
    org  = rec.annotations.get('organism','')
    date = rec.annotations.get('date','')
    head = '>gi:%s, id:%s, org:%s, date:%s\n' % (gi, rec.id, org, date)
    body = '\n'.join(textwrap.wrap(rec.seq.data, width=80))
    return head, body
    
if __name__ == '__main__':
    
    mode  = sys.argv[1]
    text  = sys.argv[2]
    output_file = sys.argv[3]

    print 'Searching for %s <br>' % text
    
    # check if inputs are all numbers
    try:
        gi_list = text.split()
        tmp = map(int, gi_list)
    except ValueError:
        gi_list = GenBank.search_for(text, max_ids=10)
    
    fp = open(output_file, 'wt')
    record_parser = GenBank.FeatureParser()
    ncbi_dict = GenBank.NCBIDictionary(mode, 'genbank', parser = record_parser)
    for gid in gi_list:
        res = ncbi_dict[gid]
        head, body =  make_fasta(res)
        fp.write(head+body+'\n')
        print head
    fp.close()

   

