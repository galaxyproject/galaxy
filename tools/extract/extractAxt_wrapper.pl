#! /usr/bin/perl -w

# Galaxy (universe) wrapper for Rico's extractAxt
# For this to work extractAxt should be intalled in bins/
# directory of universe's tools section
# Takes the following parameters:
# extractorAxt_wrapper.pl -i $inp_file1 -o $out_file1 --species $species -g $dbkey $chroCol $startCol $endCol $strandCol
# Location of alignment files is taken from /depot/data1/cache/alignseq.loc

use strict;
use warnings;
use File::Temp "tempfile";


die "<font color=\"yellow\">Your query genome, $ARGV[7], is the same as your target genome, $ARGV[5]. Please go back and select different target genome</font>\n" if ($ARGV[5] eq $ARGV[7]);

die "Not enough params -> check\n" unless @ARGV == 12;

my $alignseqLoc = "/depot/data2/galaxy/alignseq.loc";
my %alignLocation = ();
my @locFields = ();
my $extractAxtStatus = 0;
my $alignDir = "";
my @bed = ();

$ARGV[5] = "musMus$1" if ($ARGV[5]=~ m/^mm(\d)$/);
$ARGV[7] = "musMus$1" if ($ARGV[7]=~ m/^mm(\d)$/);
$ARGV[5] = "ratNor$1" if ($ARGV[5]=~ m/^rn(\d)$/);
$ARGV[7] = "ratNor$1" if ($ARGV[7]=~ m/^rn(\d)$/);


open (LOC, "<$alignseqLoc") or die "Cannot open $alignseqLoc:$!\n";
while (<LOC>) {
  if (m/^align/) {
    chop;
    @locFields = split " ";
    $alignLocation{$locFields[1]."-".$locFields[2]} = "$locFields[3]/";
  }
}
close LOC;

$alignDir = $alignLocation{"$ARGV[7]-$ARGV[5]"};

die "No alignments between $ARGV[7] and $ARGV[5] are presently stored on Galaxy site. E-mail to galaxy-user\@bx.psu.edu to request them\n" if !defined($alignDir);

if ($ARGV[8] == 1 and $ARGV[9] == 2 and $ARGV[10] == 3 and $ARGV[11] == 6) {
  $extractAxtStatus = system("extractAxt -b $ARGV[1] -c -n -o $ARGV[3] $alignDir");
} else {

  my ($fh, $filename) = tempfile();
  open (DATA, "<$ARGV[1]") or die "Cannot open $ARGV[1]:$!\n";
  while (<DATA>) {
    chop;
    my @line = split /\t/;
    $line[$ARGV[11]-1] = "+" if !defined$line[$ARGV[11]-1];
    my $nameLine = substr(join("-",@line),0,50);
    my $bedLine = "$line[$ARGV[8]-1]\t$line[$ARGV[9]-1]\t$line[$ARGV[10]-1]\t\t$nameLine\t$line[$ARGV[11]-1]\n";
    print $fh $bedLine if !m/^#/;
  }
  close DATA;
  $extractAxtStatus = system("extractAxt -b $filename -c -n -o $ARGV[3] $alignDir");
  `rm -f $filename`;
}

die "axt extractor exited abnormally: $?. E-mail to galaxy-user\@bx.psu.edu to report this problem\n" unless $extractAxtStatus == 0;

