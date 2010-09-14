#!/usr/bin/env perl

use strict;
use warnings;

###################################################
# linkToDavid.pl
# Generates a link to David for a list of gene IDs.
###################################################
 
if (!@ARGV or scalar @ARGV != 4) {
   print "usage: linkToDavid.pl infile.tab 1basedCol idType outfile\n";
   exit 1;
}

my $in = shift @ARGV;
my $col = shift @ARGV;
my $type = shift @ARGV;
my $out = shift @ARGV;

if ($col < 1) { 
   print "ERROR the column number should be 1 based counting\n";
   exit 1;
}
my @gene;
open(FH, $in) or die "Couldn't open $in, $!\n";
while (<FH>) {
   chomp;
   my @f = split(/\t/);
   if (scalar @f < $col) {
      print "ERROR there is no column $col in $in\n";
      exit 1;
   }
   if ($f[$col-1]) { push(@gene, $f[$col-1]); }
}
close FH or die "Couldn't close $in, $!\n";

if (scalar @gene > 400) {
   print "ERROR David only allows 400 genes submitted via a link\n";
   exit 1;
}
 
my $link = 'http://david.abcc.ncifcrf.gov/api.jsp?type=TYPE&ids=GENELIST&tool=summary';

my $g = join(",", @gene);
$link =~ s/GENELIST/$g/;
$link =~ s/TYPE/$type/;
#print output
if (length $link > 2048) { 
   print "ERROR too many genes to fit in URL, please select a smaller set\n";
   exit;
}
open(FH, ">", $out) or die "Couldn't open $out, $!\n";
print FH "<html><head><title>DAVID link</title></head><body>\n",
      '<A TARGET=_BLANK HREF="', $link, '">click here to send of identifiers to DAVID</A>', "\n",
      '</body></html>', "\n";
close FH or die "Couldn't close $out, $!\n";

exit;
