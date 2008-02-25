#! /usr/bin/perl -w

use strict;
use warnings;


# Changes case to upper or lower in specified columns
# changeCase.pl [filename] [output] [upper|lower]

die "Check arguments\n" unless @ARGV == 3;

open (IN,  "<$ARGV[0]") or die "Cannot open $ARGV[0]:$!\n";
open (OUT, ">$ARGV[1]") or die "Cannot create $ARGV[1]:$!\n";

while (<IN>) {
        if ($ARGV[2] eq "up") {
                print OUT uc($_);
        } elsif ($ARGV[2] eq "lo") {
                print OUT lc($_);
        }
}

close IN;
close OUT;
    
