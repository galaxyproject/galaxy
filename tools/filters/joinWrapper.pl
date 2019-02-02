#! /usr/bin/perl -w

use strict;
use warnings;
use File::Temp "tempfile";

my ($input1, $input2, $field1, $field2, $mode, $OOption, $out_file1) = @ARGV;

die "No arguments\n" unless @ARGV == 7;

my ($fh1, $file1) = tempfile();
my ($fh2, $file2) = tempfile(); 

`sort -k $field1 $input1 > $file1`;
`sort -k $field2 $input2 > $file2`;

my $option = "";
my @fields = ();
my $line = "";

if ($OOption eq "Y") {
  if (defined($fh1)) {
    $line = <$fh1>;
  } else {
    die "Failed to create file $file1\n";
  }
  @fields = split /\t/, $line;
  die "The field you selected does not exist in the input file" if (@fields < $field1);
  my @optionO = ();
  my $i = 0;
  foreach (@fields) {
    ++$i;
    push(@optionO, "1.$i");
  }
  $option = "-o " . join(",", @optionO);
} else {
  $option = "";
}

$ENV{'LC_ALL'} = 'POSIX';

if ($mode eq "V") {
  `join -v 1 $option -1 $field1 -2 $field2 $file1 $file2 | tr " " "\t" > $out_file1`;
} else {
  `join $option -1 $field1 -2 $field2 $file1 $file2 | tr " " "\t" > $out_file1`;
}

`rm $file1 ; rm $file2`;



