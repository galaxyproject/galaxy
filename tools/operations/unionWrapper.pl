#! /usr/bin/perl -w

use strict;
use warnings;
use File::Temp "tempfile";
my @inLine = ();
my @outLine = ();

my ($input1, $input2, $chromCol1, $startCol1, $endCol1, $strandCol1, $chromCol2, $startCol2, $endCol2, $strandCol2, $dbkey, $out_file1) = @ARGV;
my $galaxyOpsStatus;

die "Check arguments\n" unless @ARGV == 12;

#                 0       1       2          3          4        5           6          7          8        9           10     11
# unionWrapper.pl $input1 $input2 $chromCol1 $startCol1 $endCol1 $strandCol1 $chromCol2 $startCol2 $endCol2 $strandCol2 $dbkey $out_file1
# checks that metadata is the same for both inputs
# if it is different the second input file is reformatted in this way:
# 1). chrom start end and strand forced to be the same as in input1
# 2). everything else in input2 is packed together using "-" as a delimiter
#     and put in the column that is max(chrom1, start1, end1, strand1)+1

if ($ARGV[2] == $ARGV[6] &&
    $ARGV[3] == $ARGV[7] &&
    $ARGV[4] == $ARGV[8] ) { # do nothing run galaxyOps3 as is
    $galaxyOpsStatus = system("galaxyOps3 $dbkey -chromCol=$chromCol1 -startCol=$startCol1 -stopCol=$endCol1 -strandCol=$strandCol1 -chromCol2=$chromCol2 -startCol2=$startCol2 -stopCol2=$endCol2 $input1 $input2 -unionLists -chrom=all -bed=$out_file1");
  } else {
    my ($fh, $filename) = tempfile();
    open (INPUT2, "<$input2") or die "Cannot open $input2:$!\n";
    while (<INPUT2>) {
      chop;
      my @inLine = split /\t/;
      $outLine[$chromCol1-1]  = $inLine[$chromCol2-1];
      $outLine[$startCol1-1]  = $inLine[$startCol2-1];
      $outLine[$endCol1-1]    = $inLine[$endCol2-1];
      $outLine[$strandCol1-1] = $inLine[$strandCol2-1];
      $outLine[@outLine] = join("-",@inLine) . "\n";
      for my $i ( 0 .. @outLine-1 ) {
	$outLine[$i] = "." if !defined($outLine[$i]);
      }
      print $fh join("\t", @outLine) unless m/^#/;
      @outLine = ();
    }
    $galaxyOpsStatus = system("galaxyOps3 $dbkey -chromCol=$chromCol1 -startCol=$startCol1 -stopCol=$endCol1 -strandCol=$strandCol1 -chromCol2=$chromCol1 -startCol2=$startCol1 -stopCol2=$endCol1 $input1 $filename -unionLists -chrom=all -bed=$out_file1");
# Nasty hack below: for some reason galaxyOps3 print (null) in some lines. UNIX specific line below gets rid of these things
`grep -v "null" $out_file1 > $filename; cp $filename $out_file1 ; rm -f $filename`;
}
die "galaxyOps exited abnormally: $?\n" unless $galaxyOpsStatus == 0;
