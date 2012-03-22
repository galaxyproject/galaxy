#!/usr/bin/perl -w
use strict;

#divide the alleles and their information into separate columns for pgSnp-like
#files. Keep any additional columns beyond the pgSnp ones.
#reads from stdin, writes to stdout
my $ref;
my $in;
if (@ARGV && $ARGV[0] =~ /-ref=(\d+)/) {
   $ref = $1 -1;
   if ($ref == -1) { undef $ref; }
   shift @ARGV;
}
if (@ARGV) { 
   $in = shift @ARGV;
}

open(FH, $in) or die "Couldn't open $in, $!\n";
while (<FH>) {
   chomp;
   my @f = split(/\t/);
   my @a = split(/\//, $f[3]);
   my @fr = split(/,/, $f[5]);
   my @sc = split(/,/, $f[6]);
   if ($f[4] == 1) { #homozygous add N, 0, 0
      if ($ref) { push(@a, $f[$ref]); }
      else { push(@a, "N"); }
      push(@fr, 0);
      push(@sc, 0);
   }
   if ($f[4] > 2) { next; } #skip those with more than 2 alleles
   print "$f[0]\t$f[1]\t$f[2]\t$a[0]\t$fr[0]\t$sc[0]\t$a[1]\t$fr[1]\t$sc[1]";
   if (scalar @f > 7) {
      splice(@f, 0, 7); #remove first 7
      print "\t", join("\t", @f), "\n";
   }else { print "\n"; }
}
close FH;

exit;

