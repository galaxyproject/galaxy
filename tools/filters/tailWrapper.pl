#! /usr/bin/perl -w

use strict;
use warnings;

# a wrapper for tail for use in galaxy
# lessWrapper.pl [filename] [# lines to show] [output]

die "Check arguments" unless @ARGV == 3;
die "<font color=\"yellow\">Line number should be an integer</font>\n" unless $ARGV[1]=~ m/^\d+$/;

open (OUT, ">$ARGV[2]") or die "Cannot create $ARGV[2]:$!\n";
open (TAIL, "tail $ARGV[0] -n $ARGV[1]|") or die "Cannot run tail:$!\n";
while (<TAIL>) {
    print OUT;
}
close OUT;
close TAIL;
    
