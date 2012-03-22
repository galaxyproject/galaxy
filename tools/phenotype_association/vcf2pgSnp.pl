#!/usr/bin/perl -w
use strict;

#convert from a vcf file to a pgSnp file. 
#frequency count = chromosome count
#either a single column/individual 
#or all columns as a population 

my $in;
my $stCol = 9;
my $endCol;
if (@ARGV && scalar @ARGV == 2) {
   $stCol = shift @ARGV;
   $in = shift @ARGV;
   if ($stCol eq 'all') { $stCol = 10; }
   else { $endCol = $stCol; }
   $stCol--; #go from 1 based to zero based column number
   if ($stCol < 9) { 
      print "ERROR genotype fields don't start until column 10\n";
      exit;
   }
}elsif (@ARGV && scalar @ARGV == 1) {
   $in = shift @ARGV;
}elsif (@ARGV) {
   print "usage: vcf2pgSnp.pl [indColNum default=all] file.vcf > file.pgSnp\n";
   exit;
}

open(FH, $in) or die "Couldn't open $in, $!\n";
while (<FH>) {
   chomp; 
   if (/^\s*#/) { next; } #skip comments/headers
   if (/^\s*$/) { next; } #skip blank lines
   my @f = split(/\t/);
   #chr pos1base ID refNt altNt[,|D#|Int] quality filter info format geno1 ...
   my $a;
   my %nt;
   my %all;
   my $cnt = 0;
   my $var;
   if ($f[3] eq 'N') { next; } #ignore ref=N
   if ($f[4] =~ /[DI]/ or $f[3] =~ /[DI]/) { next; } #don't do microsatellite
   #if ($f[4] =~ /[ACTG],[ACTG]/) { next; } #only do positions with single alternate
   if ($f[6] && !($f[6] eq '.' or $f[6] eq 'PASS')) { next; } #filtered for some reason
   my $ind = 0;
   if ($f[8] ne 'GT') { #more than just genotype
      my @t = split(/:/, $f[8]);
      foreach (@t) { if ($_ eq 'GT') { last; } $ind++; }
      if ($ind == 0 && $f[8] !~ /^GT/) { die "ERROR couldn't find genotype in format $f[8]\n"; }
   }
   #count 0's, 1's, 2's
   if (!$endCol) { $endCol = $#f; }
   foreach my $col ($stCol .. $endCol) {
      if ($ind > 0) { 
         my @t = split(/:/, $f[$col]);
         $f[$col] = $t[$ind] . ":"; #only keep genotype part
      }
      if ($f[$col] =~ /^(0|1|2).(0|1|2)/) {
         $nt{$1}++;
         $nt{$2}++;
      }elsif ($f[$col] =~ /^(0|1|2):/) { #chrY or male chrX, single
         $nt{$1}++;
      } #else ignore
   }
   if (%nt) {
      if ($f[0] !~ /chr/) { $f[0] = "chr$f[0]"; }
      print "$f[0]\t", ($f[1]-1), "\t$f[1]\t"; #position info
      my $cnt = scalar(keys %nt);
      my $fr;
      my $sc;
      my $all;
      if (exists $nt{0}) {
         $all = uc($f[3]);
         $fr = $nt{0};
         $sc = 0;
      }
      if (!exists $nt{0} && exists $nt{1}) {
         if ($f[4] =~ /([ACTG]),?/) {
            $all = $1;
            $fr = $nt{1};
            $sc = 0;
         }else { die "bad variant nt $f[4] for nt 1"; }
      }elsif (exists $nt{1}) {
         if ($f[4] =~ /([ACTG]),?/) {
            $all .= '/' . $1;
            $fr .= ",$nt{1}";
            $sc .= ",0";
         }else { die "bad variant nt $f[4] for nt 1"; }
      }
      if (exists $nt{2}) {
         if ($f[4] =~ /^[ACTG],([ACTG]),?/) {
            $all .= '/' . $1;
            $fr .= ",$nt{2}";
            $sc .= ",0";
         }else { die "bad variant nt $f[4] for nt 2"; }
      }
      if (exists $nt{3}) {
         if ($f[4] =~ /^[ACTG],[ACTG],([ACTG])/) {
            $all .= '/' . $1;
            $fr .= ",$nt{3}";
            $sc .= ",0";
         }else { die "bad variant nt $f[4] for nt 3"; }
      }
      if (exists $nt{4}) {
         if ($f[4] =~ /^[ACTG],[ACTG],[ACTG],([ACTG])/) {
            $all .= '/' . $1;
            $fr .= ",$nt{4}";
            $sc .= ",0";
         }else { die "bad variant nt $f[4] for nt 4"; }
      }
      print "$all\t$cnt\t$fr\t$sc\n";
   }
}
close FH;

exit;
