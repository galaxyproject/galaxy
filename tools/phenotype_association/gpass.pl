#!/usr/bin/env perl

use strict;
use warnings;
use File::Basename;
use File::Temp qw/ tempfile /;

$ENV{'PATH'} .= ':' . dirname($0);

#this is a wrapper for gpass that converts a linkage pedigree file to input 
#for this program

my($map, $ped, $out, $fdr) = @ARGV;

if (!$map or !$ped or !$out or !$fdr) { die "missing args\n"; }

my($fh, $name) = tempfile();
#by default this file is removed when these variable go out of scope
print $fh "map=$map ped=$ped\n";
close $fh;  #converter will overwrite, just keep name

#run converter 
system("lped_to_geno.pl $map $ped > $name") == 0
	or die "system lped_to_geno.pl $map $ped > $name failed\n";

#system("cp $name tmp.middle");

#run GPASS
system("gpass $name -o $out -fdr $fdr 1>/dev/null") == 0
	or die "system gpass $name -o $out -fdr $fdr, failed\n";

#merge SNP data with results
merge();

exit;

########################################

#merge the input and output files so have SNP data with result
sub merge {
   open(FH, $out) or die "Couldn't open $out, $!\n";
   my %res;
   my @ind;
   while (<FH>) {
      chomp;
      my $line = $_;
      if ($line =~ /^(\d+)/) { $res{$1} = $line; push(@ind, $1); }
      else { $res{'index'} = $line; }
   }
   close FH;
   if (!@ind) { return; } #no results, leave alone
   @ind = sort { $a <=> $b } @ind;
   $res{'index'} =~ s/Index/#ID\tchr\tposition/;
   #read input file to get SNP data
   open(FH, $name) or die "Couldn't open $name, $!\n";
   my $i = 0; #index is 0 based not counting header line
   my $c = shift @ind;
   while (<FH>) {
      chomp; 
      if (/^ID/) { next; }
      my @f = split(/\s+/);
      if ($i == $c) { 
         $res{$i} =~ s/^$i/$f[0]\t$f[1]\t$f[2]/;
         if (!@ind) { last; }
         $c = shift @ind;
      }
      $i++;      
   }
   close FH;
   #now reprint results with SNP data included
   open(FH, ">", $out) or die "Couldn't write to $out, $!\n";
   print FH $res{'index'}, "\n";
   delete $res{'index'};
   foreach $i (keys %res) {
      print FH $res{$i}, "\n";
   }
   close FH;
}

