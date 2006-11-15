#! /usr/bin/perl -w

# Extends refions upstream or downstream by a specified number of bases
# If no strand info is provided -> assumes +
# extend.pl [input_file] [u,d,ud] [len] [start_col] [end_col] [strand_col]
# u  = upstream only
# d  = downstream only
# ud = upstream and downstream

open (IN, "<$ARGV[0]") or die "Cannot open $ARGV[0]:$!\n";

while (<IN>) {
  chop;
  @col   = split /\t/;
  if (!defined($ARGV[5]) or !defined($col[$ARGV[5]-1])) {
    $strand = "+";
  } else {
    $strand = $col[$ARGV[5]-1];
  }

  if ($strand eq "+") {
    $col[$ARGV[3]-1] = $col[$ARGV[3]-1] - $ARGV[2] if ($ARGV[1] eq "u" or $ARGV[1] eq "ud");
    $col[$ARGV[4]-1] = $col[$ARGV[4]-1] + $ARGV[2] if ($ARGV[1] eq "d" or $ARGV[1] eq "ud");
  } else {
    $col[$ARGV[3]-1] = $col[$ARGV[3]-1] - $ARGV[2] if ($ARGV[1] eq "d" or $ARGV[1] eq "ud");
    $col[$ARGV[4]-1] = $col[$ARGV[4]-1] + $ARGV[2] if ($ARGV[1] eq "u" or $ARGV[1] eq "ud");
  }
  $col[$ARGV[3]-1] = 0 if $col[$ARGV[3]-1] < 0;
  print join("\t", @col);
  print "\n";
}

close IN;
