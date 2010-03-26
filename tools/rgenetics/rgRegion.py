"""
released under the terms of the LGPL
copyright ross lazarus August 2007 
for the rgenetics project

Special galaxy tool for the camp2007 data
Allows grabbing arbitrary columns from an arbitrary region

Needs a mongo results file in the location hardwired below or could be passed in as
a library parameter - but this file must have a very specific structure
rs chrom offset float1...floatn

called as
    <command interpreter="python">
        rsRegion.py $infile '$cols' $r $tag $out_file1
    </command>

cols is a delimited list of chosen column names for the subset
r is a ucsc location region pasted into the tool

"""


import sys,string       

trantab = string.maketrans(string.punctuation,'_'*len(string.punctuation))
print >> sys.stdout, '##rgRegion.py started'
if len(sys.argv) <> 6: 
  print >> sys.stdout, '##!expected  params in sys.argv, got %d - %s' % (len(sys.argv),sys.argv)
  sys.exit(1)
print '##got %d - %s' % (len(sys.argv),sys.argv)
# quick and dirty for galaxy - we always get something for each parameter
fname = sys.argv[1]
wewant = sys.argv[2].split(',')
region = sys.argv[3].lower()
tag = sys.argv[4].translate(trantab)
ofname = sys.argv[5] 
myname = 'rgRegion'
if len(wewant) == 0: # no columns selected?
  print >> sys.stdout, '##!%s:  no columns selected - cannot run' % myname
  sys.exit(1)
try:
  f = open(fname,'r')
except: # bad input file name?
  print >> sys.stdout, '##!%s unable to open file %s' % (myname, fname)
  sys.exit(1)
try: # TODO make a regexp?
  c,rest = region.split(':')
  c = c.replace('chr','') # leave although will break strict genome graphs  
  rest = rest.replace(',','') # remove commas
  spos,epos = rest.split('-')
  spos = int(spos)
  epos = int(epos)
except:
  print >> sys.stdout, '##!%s unable to parse region %s - MUST look like "chr8:10,000-100,000' % (myname,region)
  sys.exit(1)
print >> sys.stdout, '##%s parsing chrom %s from %d to %d' % (myname, c,spos,epos)
res = []
cnames = f.next().strip().split() # column titles for output
linelen = len(cnames)
wewant = [int(x) - 1 for x in wewant] # need col numbers base 0
for n,l in enumerate(f):
  ll = l.strip().split()
  thisc = ll[1]
  thispos = int(ll[2])
  if (thisc == c) and (thispos >= spos) and (thispos <= epos):
     if len(ll) == linelen:
        res.append([ll[x] for x in wewant]) # subset of columns!
     else:
        print >> sys.stdout, '##! looking for %d fields - found %d in ll=%s' % (linelen,len(ll),str(ll))
o = file(ofname,'w')
res = ['%s\n' % '\t'.join(x) for x in res] # turn into tab delim string
print >> sys.stdout, '##%s selected and returning %d data rows' % (myname,len(res))
head = [cnames[x] for x in wewant] # ah, list comprehensions - list of needed column names
o.write('%s\n' % '\t'.join(head)) # header row for output
o.write(''.join(res))
o.close()
f.close()    


