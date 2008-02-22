#! /usr/bin/perl -w

use strict;
use warnings;

# Removes the specified number of lines from the beginning of the file.
# remove_beginning.pl [input] [num_lines] [output]

die "Check arguments" unless @ARGV == 3;

my $inputfile = $ARGV[0];
my $num_lines = $ARGV[1];
my $outputfile = $ARGV[2];

my $curCount=0;

my $fhIn;
open ($fhIn, "< $inputfile") or die "Cannot open source file";

my $fhOut;
open ($fhOut, "> $outputfile");

while (<$fhIn>)
{
    $curCount++;
    if ($curCount<=$num_lines)
    {
        next;
    }
    print $fhOut $_;
}
close ($fhIn) or die "Cannot close source file";
close ($fhOut) or die "Cannot close output file";
