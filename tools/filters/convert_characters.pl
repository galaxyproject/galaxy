#! /usr/bin/perl -w

use strict;
use warnings;

# converts all characters of one type into another 
# convert_characters.pl [input] [convert_from] [convert_to] [output]

die "Check argument\n" unless @ARGV == 4;

my $inputfile = $ARGV[0];
my $convert_from = $ARGV[1];
my $convert_to = $ARGV[2];
my $outputfile = $ARGV[3];

if ($convert_from eq "s")
{
    $convert_from = '\s';
}
elsif ($convert_from eq "T")
{
    $convert_from = '\t';
}
elsif ($convert_from eq "Sp")
{
    $convert_from = '\s';
}
elsif ($convert_from eq "Dt")
{
    $convert_from = '\.';
}
elsif ($convert_from eq "C")
{
    $convert_from = ",";
}
elsif ($convert_from eq "D")
{
    $convert_from = "-";
}
elsif ($convert_from eq "U")
{
    $convert_from = "_";
}
elsif ($convert_from eq "P")
{
    $convert_from = '\|';
}
else
{
    die "Invalid value specified for convert from\n";
}


if ($convert_to eq "T")
{
    $convert_to = "\t";
}
elsif ($convert_to eq "Sp")
{
    $convert_to = '\s';
}
elsif ($convert_to eq "Dt")
{
    $convert_to = "\.";
}
elsif ($convert_to eq "C")
{
    $convert_to = ",";
}
elsif ($convert_to eq "D")
{
    $convert_to = "-";
}
elsif ($convert_to eq "U")
{
    $convert_to = "_";
}
elsif ($convert_to eq "P")
{
    $convert_to = "|";
}
else
{
    die "Invalid value specified for convert to\n";
}

my $fhIn;
open ($fhIn, "< $inputfile") or die "Cannot open source file";

my $fhOut;
open ($fhOut, "> $outputfile");

while (<$fhIn>)
{
    my $thisLine = $_;
    chomp $thisLine;
    $thisLine =~ s/$convert_from{1,}/$convert_to/g;
    print $fhOut $thisLine,"\n";    
}
close ($fhIn) or die "Cannot close source file\n";
close ($fhOut) or die "Cannot close output fil\n";
