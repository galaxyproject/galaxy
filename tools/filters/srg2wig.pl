#! /usr/bin/perl -w

use strict;
use warnings;
use File::Temp "tempfile";

# converts srg file into wig file:
#
# if input looks like this:
#
#chr2   16447976        1.08385
#chr2   16447977        0.01
#chr4   16417846        1.26935
#chr4   16418578        1.54405
#
#the the output will look like that:
# 
#variableStep chrom=chr2
#16447976        1.08385
#16447977        0.01
#variableStep chrom=chr4
#16417846        1.26935
#16418578        1.54405
#
#srg2wig.pl input_file output_file
#

die "Not enouth arguments\n" unless @ARGV == 2;

open(IN, "<$ARGV[0]") or die "Cannot open $ARGV[0]\n";
my ($fh1, $fn1) = tempfile();
my $i = 0;

while (<IN>) {
  chop;
  if (m/^(chr\w+)\t(\d+)\t([\d\.]+)$/) {
    print $fh1 "$_\n";
  } else {
    print STDERR "Line $i does not conform to srg format : $_. Skipping...\n";
  }
  ++$i;
}
close (IN);
my ($fh2, $fn2) = tempfile();
my $sortStatus = system("sort -f -n -k 1,2 $fn1 -o $fn2");
die "srg2wig exited abnormally: $?" unless $sortStatus == 0;

open (OUT, ">$ARGV[1]") or die "Cannot create file $ARGV[1]\n";

my @chr = ();

while (<$fh2>) {
  chop;
  my @tmp = split /\t/;
  print OUT "variableStep chrom=$tmp[0]\n" if $. == 1;
  push (@chr, $tmp[0]);
  if ($chr[@chr-1] ne $chr[@chr-2]) {
    print OUT "variableStep chrom=$chr[@chr-1]\n";
    print OUT "$tmp[1]\t$tmp[2]\n";
  } else {
    print OUT "$tmp[1]\t$tmp[2]\n";
  }
}
close OUT;
`rm -f $fn1 $fn2`;
