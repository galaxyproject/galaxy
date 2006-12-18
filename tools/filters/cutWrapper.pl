#! /usr/bin/perl -w

use strict;
use warnings;

my @columns = ();
my $del = "";
my @in = ();
my @out = ();
my $command = "";
my $field = 0;

# a wrapper for cut for use in galaxy
# cutWrapper.pl [filename] [columns] [delim] [output]

die "Check arguments\n" unless @ARGV == 4;

$ARGV[1] =~ s/\s+//g;
foreach ( split /,/, $ARGV[1] ) {
  if (m/^c\d{1,}$/i) {
    push (@columns, $_);
    $columns[@columns-1] =~s/c//ig;
  }
}

die "No columns specified, columns are not preceded with 'c', or commas are not used to separate column numbers: $ARGV[1]\n" if @columns == 0;

if ($ARGV[2] eq 'T') {
    $del = "\t";
} elsif ($ARGV[2] eq 'C')  {
    $del = ",";
} elsif ($ARGV[2] eq 'D')  {
    $del = "-";
} elsif ($ARGV[2] eq 'U')  {
    $del = "_";
} elsif ($ARGV[2] eq 'P')  {
    $del = "|";
} elsif ($ARGV[2] eq 'Dt') {
    $del = ".";
} elsif ($ARGV[2] eq 'Sp') {
    $del = " ";
}

open (OUT, ">$ARGV[3]") or die "Cannot create $ARGV[2]:$!\n";
open (IN,  "<$ARGV[0]") or die "Cannot open $ARGV[0]:$!\n";
while (<IN>) {
  chop;
  @in = split /$del/; 
  foreach $field (@columns) {
    if (defined($in[$field-1])) {
      push(@out, $in[$field-1]);
    } else {
      push(@out, ".");
    }
  }
  print OUT join("$del",@out), "\n";
  @out = ();
}
close IN;

close OUT;
    
