#! /usr/bin/perl -w

use strict;
use warnings;
use File::Temp "tempfile";
#use POSIX qw(tmpnam);

my ($input1, $input2, $mode, $out_file1) = @ARGV;

my ($fh, $file1) = tempfile();
my ($fh1,$file2) = tempfile(); 

`sort $input1 > $file1`;
`sort $input2 > $file2`;
`comm $mode $file1 $file2 > $out_file1`;
`rm $file1 ; rm $file2`;



