#! /usr/bin/perl -w
use strict;
use File::Copy;

my $cmd_string = join (" ",@ARGV);
my $results = `$cmd_string`;
my @files = split("\n",$results);
my $fileNameOut = $ARGV[6];
my ($drive, $outputDir, $file) = File::Spec->splitpath( $fileNameOut );
my $destination = $fileNameOut;

foreach my $thisLine (@files)
{
	if ($thisLine =~ /Created /)
	{
		$thisLine =~ /[\w|\.]+$/;
		$thisLine =$&;
		#print "outfile: $thisLine\n";
		#there is only one file to move, so we can quit after finding it
		move($drive.$outputDir.$thisLine,$fileNameOut);
		exit(1);
	}
	else
	{
		print $thisLine,"\n";
	}
}
