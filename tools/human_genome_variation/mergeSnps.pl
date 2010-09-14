#!/usr/bin/env perl

use strict;
use warnings;

#this merges the significance output with the SNPs so users get more than an index

my($out, $snp) = @ARGV;

if (!$out or !$snp) { die "missing args\n"; }

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
      #0:      10 score= 14.224153 , df= 2 , p= 0.040760 , N=50
      if ($line =~ /^(\d+):\s+(.*)/) { $res{$1} = $2; push(@ind, $1); }
   }
   close FH;
   if (!@ind) { return; } #no results, leave alone
   @ind = sort { $a <=> $b } @ind;
   #read input file to get SNP data
   open(FH, $snp) or die "Couldn't open $snp, $!\n";
   my $i = 0; #0 based, not counting ID line
   my $c = shift @ind;
   while (<FH>) {
      chomp; 
      if (/^ID/) { next; }
      my @f = split(/\s+/);
      if ($i == $c) { 
         $res{$i} = "$f[0]\t$f[1]\t$f[2]\t$res{$i}";
         if (!@ind) { last; }
         $c = shift @ind;
      }
      $i++;      
   }
   close FH;
   #now reprint results with SNP data included
   open(FH, ">", $out) or die "Couldn't write to $out, $!\n";
   print FH "ID\tchr\tposition\tresults\n";
   foreach $i (keys %res) {
      print FH $res{$i}, "\n";
   }
   close FH;
}

