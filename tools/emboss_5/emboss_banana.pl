#! /usr/bin/perl -w
use strict;

my $cmd_string = join (" ",@ARGV);
#my $cmd_string = "/home/djb396/temp/emboss/bin/banana -sequence /home/djb396/universe-prototype/test.fasta -outfile result.txt -graph png -goutfile results -auto";
my $results = `$cmd_string`;
my @files = split("\n",$results);
foreach my $thisLine (@files)
{
	if ($thisLine =~ /Created /i)
	{
		$thisLine =~ /[\w|\.]+$/;
		$thisLine =$&;
		print "outfile: $thisLine\n";
	}
}
