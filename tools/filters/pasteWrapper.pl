#! /usr/bin/env perl

use strict;
use warnings;
my $command = "";
# a wrapper for paste for use in galaxy
# pasteWrapper.pl [filename1] [filename2] [delimiter] [output]

die "Check arguments" unless @ARGV == 4;

if ($ARGV[2] eq 'T') {
    $command = "paste $ARGV[0] $ARGV[1]";
} elsif ($ARGV[2] eq 'C') {
    $command = "paste -d \",\" $ARGV[0] $ARGV[1]";
} elsif ($ARGV[2] eq 'D') {
    $command = "paste -d \"-\" $ARGV[0] $ARGV[1]";
} elsif ($ARGV[2] eq 'U') {
    $command = "paste -d \"_\" $ARGV[0] $ARGV[1]";
} elsif ($ARGV[2] eq 'P') {
    $command = "paste -d \"|\" $ARGV[0] $ARGV[1]";
} elsif ($ARGV[2] eq 'Dt') {
    $command = "paste -d \".\" $ARGV[0] $ARGV[1]";
} elsif ($ARGV[2] eq 'Sp') {
    $command = "paste -d \" \" $ARGV[0] $ARGV[1]";
}

open (OUT, ">$ARGV[3]") or die "Cannot create $ARGV[2]:$!\n";
open (PASTE, "$command |") or die "Cannot run paste:$!\n";

while (<PASTE>) {
    print OUT;
}
close OUT;
close PASTE;
    
