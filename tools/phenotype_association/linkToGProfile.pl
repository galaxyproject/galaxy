#!/usr/bin/env perl

use strict;
use warnings;

###################################################
# linkToGProfile.pl
# Generates a link to gprofile for a list of gene IDs.
# g:Profiler a web-based toolset for functional profiling of gene lists from large-scale experiments (2007) NAR 35 W193-W200
###################################################
 
if (!@ARGV or scalar @ARGV < 4) {
   print "usage: linkToGProfile.pl infile.tab idType outfile -gene=1basedCol -chr=1basedCol -start=1basedCol -end=1basedCol\n";
   exit 1;
}

my $in = shift @ARGV;
my $type = shift @ARGV;
my $out = shift @ARGV;

my $col = 9999;  #large unrealistic default
my $chr = 9999;
my $st = 9999;
my $end = 9999;
foreach (@ARGV) {
   if (/gene=(\d+)/) { $col = $1; }
   elsif (/chr=(\d+)/) { $chr = $1; }
   elsif (/start=(\d+)/) { $st = $1; }
   elsif (/end=(\d+)/) { $end = $1; }
   elsif (/region=1/) { $type = 'region'; }
}

if ($col < 1 or $chr < 1 or $st < 1 or $end < 1) { 
   print "ERROR the column number should be 1 based counting\n";
   exit 1;
}
my @gene;
my @pos;
open(FH, $in) or die "Couldn't open $in, $!\n";
while (<FH>) {
   chomp;
   my @f = split(/\t/);
   if ($type ne 'region') {
      if (scalar @f < $col) {
         print "ERROR there is no column $col in $in for type $type\n";
         exit 1;
      }
      if ($f[$col-1]) { push(@gene, $f[$col-1]); }
   }else {
      if (scalar @f < $chr or scalar @f < $st or scalar @f < $end) {
         print "ERROR there is not enough columns ($chr,$st,$end) in $in\n";
         exit 1;
      }
      if ($f[$chr-1]) {
         $f[$chr-1] =~ s/chr//;
         push(@pos, "$f[$chr-1]:$f[$st-1]:$f[$end-1]");
      }
   }
}
close FH or die "Couldn't close $in, $!\n";
 
#region_query = 1 for coordinates X:1:10
#can now do POST method
#http://biit.cs.ut.ee/gprofiler/index.cgi?organism=hsapiens&query=pax6&term=&analytical=1&user_thr=1&sort_by_structure=1&output=txt
my $g = join("+", @gene) if @gene;
if (@pos) { $g = join("+", @pos); }
my %params = (
"analytical"=>1,
"organism"=>"hsapiens",
"query"=>$g,
"term"=>"",
"output"=>"png",
"prefix"=>$type,
"user_thr"=>"1.00"
);
if (@pos) { $params{"region_query"} = 1; }

open(FH, ">", $out) or die "Couldn't open $out, $!\n";
print FH "<html><head><title>g:Profiler link</title></head><body>\n";
print FH '<form method="POST" action="http://biit.cs.ut.ee/gprofiler/index.cgi">', "\n";
foreach my $k (keys %params) {
   print FH "<input type='hidden' name='$k' value='$params{$k}'>\n";
}
print FH '<input type="Submit" name="foo" value="Send to g:Profiler">';
print FH '</form></body></html>', "\n";
close FH or die "Couldn't close $out, $!\n";

#also do link that prints text that could be pulled back into Galaxy?
exit;
