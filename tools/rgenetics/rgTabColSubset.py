"""
released under the terms of the LGPL
copyright ross lazarus May 2011
for the rgenetics project

Special galaxy tool for subsetting an arbitrary phenotype tabular file
Allows grabbing arbitrary columns 

called as
    <description>from a tabular file</description>
  <code file="rgTabColSubset_code.py"/>    
   <command interpreter="python">rgTabColSubset.py -i "$infile" -n "$title1" -o "$outfile" -c "$cols" 
   </command>
   <inputs>


"""


import sys,optparse,os

sep = '\t'

op = optparse.OptionParser()
op.add_option('-i', '--input', default=None)
op.add_option('-o', '--output', default=None)
op.add_option('-c', '--cols', default=None) 
op.add_option('-n', '--title', default='Subset')
opts, args = op.parse_args()
assert os.path.isfile(opts.input), '## Cannot open supplied input file %s' % opts.input
wewant = opts.cols.split(',')
wewant = map(int,wewant)
lastcol = max(wewant)
assert len(wewant) > 0, '## Must have at least one column in the -c parameter - got %s' % opts.cols
f = open(opts.input,'r')
dat = f.readlines()
dat = [x.split(sep) for x in dat]
head = dat[0]
assert len(head) >= lastcol,'## Supplied file %s has %d tab delimited column names - last requested column %d is too big' % (opts.input,len(head),lastcol)
o = open(opts.output,'w')
subset = ['\t'.join((x[i] for i in wewant)) for x in dat]
o.write('\n'.join(subset))
o.write('\n')
o.close()
info = 'Subset %d columns out of %d from %s written to %s' % (len(wewant),len(head),opts.input,opts.output)
print >> sys.stdout, info
