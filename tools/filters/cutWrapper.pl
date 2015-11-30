#!/usr/bin/perl -w

use strict;
use warnings;

my @columns = ();
my $del = "";
my @in = ();
my @out = ();
my $command = "";
my $field = 0;
my $start = 0;
my $end = 0;
my $step = 0;
my $i = 0;
my $fill_char = "";
my $keep_header = 0;

# a wrapper for cut for use in galaxy
# cutWrapper.pl [filename] [columns] [delim] [output] [fill-char] [keep-header]

die "Check arguments\n" unless @ARGV == 6;

$ARGV[1] =~ s/\s+//g;
foreach ( split /,/, $ARGV[1] ) {
  if (m/^c\d{1,}$/i) {
    push (@columns, $_);
    $columns[@columns-1] =~s/c//ig;
  } elsif (m/^c\d{1,}-c\d{1,}$/i) {
    ($start, $end)  = split(/-/, $_);
    $start =~ s/c//ig;
    $end =~ s/c//ig;
    for $i ($start .. $end) {
       push (@columns, $i);
    }
  } elsif (m/^c\d{1,}-c\d{1,}\|\d{1,}$/i) {
    ($start, $end)  = split(/-/, $_);
    $start =~ s/c//ig;
    ($end, $step) = split(/\|/, $end);
    $end =~ s/c//ig;
    for ($i=$start;$i<=$end;$i+=$step) {
       push (@columns, $i);
    }
  } else {
  print "Skipping invalid column assignment: \"", $_, "\"\n";
  }
}

die "No columns specified, columns are not preceded with 'c', or commas are not used to separate column numbers: $ARGV[1]\n" if @columns == 0;

my $column_delimiters_href = {
  'T' => q{\t},
  'C' => ",",
  'D' => "-",
  'U' => "_",
  'P' => q{\|},
  'Dt' => q{\.},
  'Sp' => q{\s+}
};

$del = $column_delimiters_href->{$ARGV[2]};

open (OUT, ">$ARGV[3]") or die "Cannot create $ARGV[2]:$!\n";
open (IN,  "<$ARGV[0]") or die "Cannot open $ARGV[0]:$!\n";

$fill_char = $ARGV[4];

$keep_header = int($ARGV[5]);


while (my $line=<IN>) {
   my $is_header = ($line =~ /^#/);
   if ($is_header && $keep_header==0) {
     #Ignore comment lines
   } else {
     chop($line);
     @in = split(/$del/, $line);
     if ($is_header && $keep_header == 2){
         $in[0] =~ s/^#+//;
     }
     if ($keep_header == 2 or !$is_header){
         foreach $field (@columns) {
           if (defined($in[$field-1])) {
             push(@out, $in[$field-1]);
           } else {
             push(@out, $fill_char);
           }
         }
     }
     elsif ($is_header){
         @out = ($line);
     }
     if ($is_header && $keep_header == 2){
         print OUT "#";
     }
     print OUT join("\t",@out), "\n";
     @out = ();
   }
}

#while (<IN>) {
#  chop;
#  @in = split /$del/; 
#  foreach $field (@columns) {
#    if (defined($in[$field-1])) {
#      push(@out, $in[$field-1]);
#    } else {
#      push(@out, ".");
#    }
#  }
#  print OUT join("\t",@out), "\n";
#  @out = ();
#}
close IN;

close OUT;
    
