#! /usr/bin/perl -w
use strict;
use File::Copy;

my $cmd_string = join (" ",@ARGV);
my $results = `$cmd_string`;
my @files = split("\n",$results);
my $fileNameOut = $ARGV[14];
move($fileNameOut.".1.png",$fileNameOut);
