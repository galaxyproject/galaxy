#! /usr/bin/perl -w

use strict;
use warnings;

# fixedValueColumn.pl $input $out_file1 "expression" "iterate [yes|no]"

my ($input, $out_file1, $expression, $iterate) = @ARGV;
my $i = 0;
my $numeric = 0;

die "Check arguments\n" unless @ARGV == 4;

open (DATA, "<$input") or die "Cannot open $input:$!\n";
open (OUT,  ">$out_file1") or die "Cannot create $out_file1:$!\n";

if ($expression =~ m/^\d+$/) {
  $numeric = 1;
  $i = $expression;
}

while (<DATA>) {
  chop;
  if ($iterate eq "no") {
    print OUT "$_\t$expression\n";
  } else {
    print OUT "$_\t$i\n" if $numeric == 1;
    print OUT "$_\t$expression-$i\n" if $numeric == 0;
    ++$i;
  }
}

close DATA;
close OUT;
