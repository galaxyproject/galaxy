#! /usr/bin/perl -w
use strict;

my $cmd_string = join (" ",@ARGV);
my $results = `$cmd_string`;
if ($ARGV[6]=~/yes/)
{
	print "Extension: html\n";
}
