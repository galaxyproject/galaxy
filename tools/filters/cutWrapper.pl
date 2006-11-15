#! /usr/bin/perl -w

use strict;
use warnings;

my @columns = ();
my $columnList = "";
my $command = "";

# a wrapper for cut for use in galaxy
# cutWrapper.pl [filename] [columns] [delim] [output]

die "Check arguments $ARGV[1]\n" unless @ARGV == 4;

$ARGV[1] =~ s/\s+//g;
@columns = split /,/, $ARGV[1];

foreach (@columns) {
    $columnList .= "$_," if m/^c\d{1,}$/i;
}
$columnList =~s/c//ig;

die "<font color=\"yellow\">No columns specified or bad syntax: $ARGV[1]</font>\n" if length($columnList) == 0;

if ($ARGV[2] eq 'T') {
    $command = "cut -f $columnList $ARGV[0]";
} elsif ($ARGV[2] eq 'C') {
    $command = "cut -f $columnList -d \",\" $ARGV[0]";
} elsif ($ARGV[2] eq 'D') {
    $command = "cut -f $columnList -d \"-\" $ARGV[0]";
} elsif ($ARGV[2] eq 'U') {
    $command = "cut -f $columnList -d \"_\" $ARGV[0]";
} elsif ($ARGV[2] eq 'P') {
    $command = "cut -f $columnList -d \"|\" $ARGV[0]";
} elsif ($ARGV[2] eq 'Dt') {
    $command = "cut -f $columnList -d \".\" $ARGV[0]";
} elsif ($ARGV[2] eq 'Sp') {
    $command = "cut -f $columnList -d \" \" $ARGV[0]";
}



open (OUT, ">$ARGV[3]") or die "Cannot create $ARGV[2]:$!\n";
open (CUT, "$command |") or die "Cannot run cut:$!\n";
while (<CUT>) {
    print OUT;
}
close OUT;
close CUT;
    
