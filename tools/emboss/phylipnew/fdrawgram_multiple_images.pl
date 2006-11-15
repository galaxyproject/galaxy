#! /usr/bin/perl -w
use strict;
use File::Temp qw/ tempfile tempdir /;

my @arguments = @ARGV;
my $mode = shift(@arguments);
my $program = $arguments[0];

#fix quotes; could try to quote all args that don't have a "-", but negative numbers?
if ($program eq "fdrawgram")
{
    $arguments[14]="\"".$arguments[14]."\"";
    $arguments[18]="\"".$arguments[18]."\"";
    $arguments[20]="\"".$arguments[20]."\"";
    $arguments[22]="\"".$arguments[22]."\"";
    $arguments[24]="\"".$arguments[24]."\"";
    $arguments[28]="\"".$arguments[28]."\"";
    $arguments[30]="\"".$arguments[30]."\"";
}

my $outputfile=$arguments[4];

if ($mode =~ /multipleset/)
{
    my $inputfile=$arguments[2];
    my $outputfile = $arguments[4];
    my $fhIn;
    open ($fhIn, $inputfile) or die "Can't open source file.";
    my @imageFiles=();
    
    
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
    	
    	my $cmd = "gs -sDEVICE=png16m -sOutputFile=$filenameTempOut -dBATCH -dNOPAUSE -dQUIET $filenameTempOut";
    	$results = `$cmd`;
    	#print $results;
    	
    	push (@imageFiles, $filenameTempOut);
    }
    
    my $cmd_string = "montage -geometry +0+0 -tile 4x999999999999999";
    for (my $i=0;$i<@imageFiles;$i++)
    {
        $cmd_string .= " png:$imageFiles[$i]";
    }
    $cmd_string .= " png:$outputfile";
    #print "\ncmd: $cmd_string\n";
    my $results = `$cmd_string`;
    #print $results;

}
else
{
    my $cmd_string = join (" ",@arguments);
    #print "\ncmd: $cmd_string\n";
    my $results = `$cmd_string`;
    #print $results;
    
    my $cmd = "gs -sDEVICE=png16m -sOutputFile=$outputfile -dBATCH -dNOPAUSE -dQUIET $outputfile";
    $results = `$cmd`;
    #print $results;

}
