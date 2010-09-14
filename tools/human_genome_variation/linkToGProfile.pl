#!/usr/bin/env perl

use strict;
use warnings;

###################################################
# linkToGProfile.pl
# Generates a link to gprofile for a list of gene IDs.
# g:Profiler a web-based toolset for functional profiling of gene lists from large-scale experiments (2007) NAR 35 W193-W200
###################################################
 
if (!@ARGV or scalar @ARGV != 4) {
   print "usage: linkToGProfile.pl infile.tab 1basedCol idType outfile\n";
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
 
my $link = 'http://biit.cs.ut.ee/gprofiler/index.cgi?organism=hsapiens&query=GENELIST&r_chr=1&r_start=start&r_end=end&analytical=1&domain_size_type=annotated&term=&significant=1&sort_by_structure=1&user_thr=1.00&output=png&prefix=TYPE';
$link =~ s/TYPE/$type/;
my $g = join("+", @gene);
$link =~ s/GENELIST/$g/;
#print output
if (length $link > 2048) { 
   print "ERROR too many genes to fit in URL, please select a smaller set\n";
   exit;
}
open(FH, ">", $out) or die "Couldn't open $out, $!\n";
print FH "<html><head><title>g:Profiler link</title></head><body>\n",
      '<A TARGET=_BLANK HREF="', $link, '">click here to send list of identifiers to g:Profiler</A>', "\n",
      '</body></html>', "\n";
close FH or die "Couldn't close $out, $!\n";

#also do link that prints text that could be pulled back into Galaxy?
exit;
