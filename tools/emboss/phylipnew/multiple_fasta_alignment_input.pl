#! /usr/bin/perl -w
use strict;
use File::Temp qw/ tempfile tempdir /;

#<mode> fdnadist -sequence /home/djb396/galaxy/universe/universe-release/database/files/068b3a6b67ceb1ca039f34221090d6fb.dat -outfile /home/djb396/galaxy/universe/universe-release/database/files/680e9b07ac3770e7533ba280050fe8dd.dat -method f -gamma n -gammacoefficient "1" -invarfrac "0.0" -ttratio "2.0" -freqsfrom yes -basefreq "0.25 0.25 0.25 0.25" -lower no -printdata no -progress no -auto
#modes = multipleset;singleset (sets of alignment)


my @arguments = @ARGV;
my $mode = shift(@arguments);
my $program = $arguments[0];
my $headerLines=0;

#fix quotes; could try to quote all args that don't have a "-", but negative numbers?
if ($program eq "fdnadist")
{
    $arguments[10]="\"".$arguments[10]."\"";
    $arguments[12]="\"".$arguments[12]."\"";
    $arguments[14]="\"".$arguments[14]."\"";
    $arguments[18]="\"".$arguments[18]."\"";
    $headerLines=3;
}
elsif ($program eq "fprotdist")
{
    $arguments[10]="\"".$arguments[10]."\"";
    $arguments[12]="\"".$arguments[12]."\"";
    $arguments[18]="\"".$arguments[18]."\"";
    $arguments[20]="\"".$arguments[20]."\"";
    $arguments[22]="\"".$arguments[22]."\"";
    $headerLines=3;
}
elsif ($program eq "fseqboot")
{
    $arguments[10]="\"".$arguments[10]."\"";
    $arguments[12]="\"".$arguments[12]."\"";
    $arguments[14]="\"".$arguments[14]."\"";
    $arguments[18]="\"".$arguments[18]."\"";
    $headerLines=0;
}

#perl /home/djb396/galaxy/universe/universe-release/tools/emboss/phylipnew/multiple_fasta_alignment_input.pl multipleset fdnadist -sequence /home/djb396/galaxy/universe/universe-release/database/files/99c72e2f584c80c110354c8edf20371b.dat -outfile /home/djb396/galaxy/universe/universe-release/database/files/412f93381909832dbce42b206643de22.dat -method f -gamma n -gammacoefficient "1" -invarfrac "0.0" -ttratio "2.0" -freqsfrom yes -basefreq "0.25 0.25 0.25 0.25" -lower no -printdata no -progress no -auto

my $outputfile=$arguments[4];

if ($mode =~ /multipleset/)
{
    my $inputfile=$arguments[2];

    my $fhIn;
    open ($fhIn, $inputfile) or die "Can't open source file.";
    #my $outputContents="";
    
    my $fhOut;
    open ($fhOut, "> $outputfile") or die "Can't open output file.";
    
    
    local $/ = '';
    while (<$fhIn>)
    {
    	my ($fhTempIn, $filenameTempIn) = tempfile();
    	print $fhTempIn $_;
    	close ($fhTempIn) or die "Couldn't close temporary file";
    	
    	my (undef, $filenameTempOut) = tempfile();
    	
    	close ($filenameTempOut);
    	
    	$arguments[2]=$filenameTempIn;
    	$arguments[4]=$filenameTempOut;
    	
    	my $cmd_string = join (" ",@arguments);
    	#print "\ncmd: $cmd_string\n";
    	my $results = `$cmd_string`;
    	#print $results;
    	
    	local $/ = "\n";
    	
    	open (RESULT, $filenameTempOut) or die "Can't open individual result file.";
    	my @contents = <RESULT>;
    	
    	close (RESULT);
    	for (my $i=0;$i<$headerLines;$i++)
    	{
    	    shift @contents;
    	}
    	
    	my $outputContents = join("",@contents)."\n";
    	print $fhOut $outputContents;
    	#print $outputContents;
    }

    close ($fhOut);
}
else
{
    my $cmd_string = join (" ",@arguments);
    my $results = `$cmd_string`;
    print $results;
    
    open (RESULT, $outputfile) or die "Can't open final result file.";
    my @contents = <RESULT>;
    close RESULT;
    for (my $i=0;$i<$headerLines;$i++)
    {
        shift @contents;
    }
    open (RESULT, "> $outputfile") or die "Can't open final result file.";
    print RESULT join("",@contents);
    close RESULT;
}
