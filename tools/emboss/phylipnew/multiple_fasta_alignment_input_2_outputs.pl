#! /usr/bin/perl -w
use strict;
use File::Temp qw/ tempfile tempdir /;

#fdnapars -sequence /tmp/Wb8TN6z739 -outfile /tmp/9fg3fV8D97 -trout yes -outtreefile /home/djb396/galaxy/universe/universe-release/database/files/a7eabb4d134e5d5acb5d11352bda68da.dat -maxtrees "10000" -thorough yes -rearrange yes -transversion no -njumble "0" -seed "1" -outgrno "0" -thresh no -threshold "1.0" -printdata no -progress no -stepbox no -ancseq no -treeprint yes -dotdiff yes -auto
#modes = multipleset;singleset (sets of alignment)


my @arguments = @ARGV;
my $mode = shift(@arguments);
my $program = $arguments[0];
my $headerLines1=0;
my $headerLines2=0;

#fix quotes; could try to quote all args that don't have a "-", but negative numbers?
if ($program eq "fdnapars")
{
    $arguments[10]="\"".$arguments[10]."\"";
    $arguments[18]="\"".$arguments[18]."\"";
    $arguments[20]="\"".$arguments[20]."\"";
    $arguments[22]="\"".$arguments[22]."\"";
    $arguments[26]="\"".$arguments[26]."\"";
    $headerLines1=0;
    $headerLines2=0;
}
elsif ($program eq "ffitch")
{
    $arguments[12]="\"".$arguments[12]."\"";
    $arguments[14]="\"".$arguments[14]."\"";
    $arguments[16]="\"".$arguments[16]."\"";
    $arguments[18]="\"".$arguments[18]."\"";
    $headerLines1=0;
    $headerLines2=0;
}
elsif ($program eq "fneighbor")
{
    $arguments[14]="\"".$arguments[14]."\"";
    $arguments[18]="\"".$arguments[18]."\"";
    $headerLines1=0;
    $headerLines2=0;
}
elsif ($program eq "fprotpars")
{
    $arguments[10]="\"".$arguments[10]."\"";
    $arguments[12]="\"".$arguments[12]."\"";
    $arguments[14]="\"".$arguments[14]."\"";
    $arguments[18]="\"".$arguments[18]."\"";
    $headerLines1=0;
    $headerLines2=0;
}
#perl /home/djb396/galaxy/universe/universe-release/tools/emboss/phylipnew/multiple_fasta_alignment_input.pl multipleset fdnadist -sequence /home/djb396/galaxy/universe/universe-release/database/files/99c72e2f584c80c110354c8edf20371b.dat -outfile /home/djb396/galaxy/universe/universe-release/database/files/412f93381909832dbce42b206643de22.dat -method f -gamma n -gammacoefficient "1" -invarfrac "0.0" -ttratio "2.0" -freqsfrom yes -basefreq "0.25 0.25 0.25 0.25" -lower no -printdata no -progress no -auto

my $outputfile1=$arguments[4];
my $outputfile2=$arguments[8];

if ($mode =~ /multipleset/)
{
    my $inputfile=$arguments[2];

    my $fhIn;
    open ($fhIn, $inputfile) or die "Can't open source file.";
    #my $outputContents="";
    
    my $fhOut1;
    open ($fhOut1, "> $outputfile1") or die "Can't open output file 1.";
    
    my $fhOut2;
    open ($fhOut2, "> $outputfile2") or die "Can't open output file 2.";
    
    local $/ = '';
    while (<$fhIn>)
    {
    	my ($fhTempIn, $filenameTempIn) = tempfile();
    	print $fhTempIn $_;
    	close ($fhTempIn) or die "Couldn't close temporary file";
    	
    	my (undef, $filenameTempOut1) = tempfile();
    	my (undef, $filenameTempOut2) = tempfile();
    	
    	
    	close ($filenameTempOut1);
    	close ($filenameTempOut2);
    	
    	$arguments[2]=$filenameTempIn;
    	$arguments[4]=$filenameTempOut1;
    	$arguments[8]=$filenameTempOut2;
    	
    	my $cmd_string = join (" ",@arguments);
    	#print "\ncmd: $cmd_string\n";
    	my $results = `$cmd_string`;
    	#print $results;
    	
    	local $/ = "\n";
    	
    	
    	
    	open (RESULT, $filenameTempOut1) or die "Can't open individual result file 1.";
    	my @contents1 = <RESULT>;
    	
    	close (RESULT);
    	for (my $i=0;$i<$headerLines1;$i++)
    	{
    	    shift @contents1;
    	}
    	
    	my $outputContents1 = join("",@contents1)."\n";
    	print $fhOut1 $outputContents1;
    	
    	
    	
    	open (RESULT, $filenameTempOut2) or die "Can't open individual result file 2.";
    	my @contents2 = <RESULT>;
    	
    	close (RESULT);
    	for (my $i=0;$i<$headerLines2;$i++)
    	{
    	    shift @contents2;
    	}
    	
    	my $outputContents2 = join("",@contents2)."\n";
    	print $fhOut2 $outputContents2;
    }

    close ($fhOut1);
    close ($fhOut2);
}
else
{
    my $cmd_string = join (" ",@arguments);
    my $results = `$cmd_string`;
    print $results;
    
    open (RESULT, $outputfile1) or die "Can't open final result file.";
    my @contents = <RESULT>;
    close RESULT;
    for (my $i=0;$i<$headerLines1;$i++)
    {
        shift @contents;
    }
    open (RESULT, "> $outputfile1") or die "Can't open final result file.";
    print RESULT join("",@contents);
    close RESULT;
}
