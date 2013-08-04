"""
## python version of CG counter
## I hope this is easier to understand 
## It was much easier to write
## ross lazarus march 13 2011
**Attribution**

Antony Kaspi wanted a GC counter in Galaxy, so he wrote a perl on liner and proposed the tool.

Ross Lazarus tried really hard to like perl but finally ran screaming
back to the re module for this first working version.

All rights reserved. Copyright March 2011 Ross Lazarus
This artifact is licensed under the LGPL
As are all the Rgenetics series of Galaxy tools (ross period lazarus at gmaildotcom)
Depending on how far you want this attribution to go, don't forget 
a boatload of other people's work like linux, python perl, and such without which 
none of this stuff would work.
"""
import sys,os,re

delim = '\t'
if len(sys.argv) < 3:
    print 'Need an input file path, an output file path and whether to append'
    sys.exit(1)
infname = sys.argv[1]
assert os.path.isfile(infname), 'Cannot open given infile %s' % infname
outfname = sys.argv[2]
appen = False
if len(sys.argv) > 3:
    appen = True
inf = open(infname,'r')
outf = open(outfname,'w')
ex = re.compile('CG',re.IGNORECASE)
for row in inf.readlines():
    r = row.strip().split(delim)
    if len(r) < 3:
        continue
    seq = r[3]
    cgcount = '%d' % len(ex.findall(seq))
    if appen:
        newrow = r + [cgcount,]
    else:
        newrow = r[:3] + [cgcount,]
    outf.write('\t'.join(newrow))
    outf.write('\n')
outf.close()
inf.close()
"""
#!/usr/bin/perl -w
# antony kaspi's perl one liner GC counter
# converted into a perl script for galaxy
# by ross lazarus. March 2011
# ugh. 
# perl one liners may be convenient to write but it's ugly to read and work with 
# now I need toclean my brain out with some mental floss.

use strict;
use warnings;

die "Check arguments" unless @ARGV == 3;

my $delim = "\t";
my @in = ();
my $inputfile = $ARGV[0];
my $outputfile = $ARGV[1];
my $appen
my $fhIn;
my $c;
my $seq;
my @row = ();
my $fhOut;
open ($fhIn, "< $inputfile") or die "Cannot open source file";

open ($fhOut, "> $outputfile") or die "Cannot open output file for writing";
while (<$fhIn>)
{
  $c=0;
  chop;
  @in = split /$delim/;
  if (scalar @in < 3) { next; }
  $seq = $in[3];
  @row = @in[0..2];
  while($seq =~ /CG/ig){++$c};
  push(@row,$c);
  print $fhOut join($delim,@row),"\n"
}
close ($fhIn) or die "Cannot close source file";
close ($fhOut) or die "Cannot close output file";

"""
