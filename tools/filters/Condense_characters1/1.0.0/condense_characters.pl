#! /usr/bin/perl -w

use strict;
use warnings;

# condenses all consecutive characters of one type
# convert_characters.pl [input] [character] [output]

die "Check arguments" unless @ARGV == 3;

my $inputfile = $ARGV[0];
my $character = $ARGV[1];
my $outputfile = $ARGV[2];


my $convert_from;
my $convert_to;


if ($character eq "s")
{
    $convert_from = '\s';
}
elsif ($character eq "T")
{
    $convert_from = '\t';
}
elsif ($character eq "Sp")
{
    $convert_from = " ";
}
elsif ($character eq "Dt")
{
    $convert_from = '\.';
}
elsif ($character eq "C")
{
    $convert_from = ",";
}
elsif ($character eq "D")
{
    $convert_from = "-";
}
elsif ($character eq "U")
{
    $convert_from = "_";
}
elsif ($character eq "P")
{
    $convert_from = '\|';
}
else
{
    die "Invalid value specified for convert from\n";
}


if ($character eq "T")
{
    $convert_to = "\t";
}
elsif ($character eq "Sp")
{
    $convert_to = " ";
}
elsif ($character eq "Dt")
{
    $convert_to = "\.";
}
elsif ($character eq "C")
{
    $convert_to = ",";
}
elsif ($character eq "D")
{
    $convert_to = "-";
}
elsif ($character eq "U")
{
    $convert_to = "_";
}
elsif ($character eq "P")
{
    $convert_to = "|";
}
else
{
    die "Invalid value specified for Convert to\n";
}

my $fhIn;
open ($fhIn, "< $inputfile") or die "Cannot open source file";

my $fhOut;
open ($fhOut, "> $outputfile");

while (<$fhIn>)
{
    my $thisLine = $_;
    chomp $thisLine;
    $thisLine =~ s/${convert_from}+/$convert_to/g;
    print $fhOut $thisLine,"\n";    
}
close ($fhIn) or die "Cannot close source file";
close ($fhOut) or die "Cannot close output file";
