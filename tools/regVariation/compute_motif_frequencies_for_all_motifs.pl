#!/usr/bin/perl -w

# a program to compute the frequencies of each motif at a window size, determined by the user, in both 
# upstream and downstream sequences flanking indels in all chromosomes.
# the first input is a TABULAR format file containing the motif names and sequences, such that the file 
# consists of two columns: the left column represents the motif names and the right column represents 
# the motif sequence, one line per motif.
# the second input is a TABULAR format file containing the windows into which both upstream and downstream 
# sequences flanking indels have been divided.
# the fourth input is an integer number representing the number of windows to be considered in both 
# upstream and downstream flanking sequences.
# the output is a TABULAR format file consisting of three columns: the left column represents the motif 
# name, the middle column represents the motif frequency in the window of the upstream sequence flanking 
# an indel, and the the right column represents the motif frequency in the window of the downstream 
# sequence flanking an indel, one line per indel.
# The total number of lines in the output file = number of motifs x number of indels.

use strict;
use warnings;

#variable to handle the window information
my $window = "";
my $windowNumber = 0;
my $totalWindowsNumber = 0;
my $upstreamAndDownstreamFlankingSequencesWindows = "";

#variable to handle the motif information
my $motif = "";
my $motifName = "";
my $motifSequence = "";
my $motifNumber = 0;
my $totalMotifsNumber = 0;
my $upstreamMotifFrequencyCounter = 0;
my $downstreamMotifFrequencyCounter = 0;

#arrays to sotre window and motif data
my @windowsArray = ();
my @motifNamesArray = ();
my @motifSequencesArray = ();

#variable to handle the indel information
my $indelIndex = 0;

#variable to store line counter value
my $lineCounter = 0;

# check to make sure having correct files
my $usage = "usage: compute_motif_frequencies_for_all_motifs.pl [TABULAR.in] [TABULAR.in] [windowSize] [TABULAR.out] \n";
die $usage unless @ARGV == 4;

#get the input arguments
my $motifsInputFile = $ARGV[0];
my $indelFlankingSequencesWindowsInputFile = $ARGV[1];
my $numberOfConsideredWindows = $ARGV[2];
my $motifFrequenciesOutputFile = $ARGV[3];

#open the input files
open (INPUT1, "<", $motifsInputFile) || die("Could not open file $motifsInputFile \n"); 
open (INPUT2, "<", $indelFlankingSequencesWindowsInputFile) || die("Could not open file indelFlankingSequencesWindowsInputFile \n");   
open (OUTPUT, ">", $motifFrequenciesOutputFile) || die("Could not open file $motifFrequenciesOutputFile \n");   

#store the motifs input file in the array @motifsData
my @motifsData = <INPUT1>;

#iterated through the motifs (lines) of the motifs input file
foreach $motif (@motifsData){
	chomp ($motif);
	#print ($motif . "\n");
	
	#split the motif data into its name and its sequence
	my @motifNameAndSequenceArray = split(/\t/, $motif);
	
	#store the name of the motif into the array @motifNamesArray
	push @motifNamesArray, $motifNameAndSequenceArray[0];
	
	#store the sequence of the motif into the array @motifSequencesArray
	push @motifSequencesArray, $motifNameAndSequenceArray[1];
}

#compute the size of the motif names array 
$totalMotifsNumber = @motifNamesArray;


#store the first output file containing the windows of both upstream and downstream flanking sequences in the array @windowsData
my @windowsData = <INPUT2>;

#check if the number of considered window entered by the user is 0 or negative, if so make it equal to 1
if ($numberOfConsideredWindows <= 0){
	$numberOfConsideredWindows = 1;
}

#iterated through the motif sequences to check their occurrences in the considered windows
#and store the count of their occurrences in the corresponding ouput file
for ($motifNumber = 0; $motifNumber < $totalMotifsNumber; $motifNumber++){
	
	#get the motif name
	$motifName = $motifNamesArray[$motifNumber];
	
	#get the motif sequence
    $motifSequence = $motifSequencesArray[$motifNumber];
		        	
	#iterated through the lines of the second input file. Each line represents   
	#the windows of the upstream and downstream flanking sequences of an indel
	foreach $upstreamAndDownstreamFlankingSequencesWindows (@windowsData){
		
		chomp ($upstreamAndDownstreamFlankingSequencesWindows);
		$lineCounter++;
		
		#split both upstream and downstream flanking sequences into their windows
		my @windowsArray = split(/\t/, $upstreamAndDownstreamFlankingSequencesWindows);
		
		if ($lineCounter == 1){
			$totalWindowsNumber = @windowsArray;
			$indelIndex = ($totalWindowsNumber - 1)/2;		
		}
		
		#reset the motif frequency counters
		$upstreamMotifFrequencyCounter = 0;
		$downstreamMotifFrequencyCounter = 0;
		
		#iterate through the considered windows of the upstream flanking sequence and increment the motif frequency counter
		for ($windowNumber = $indelIndex - 1; $windowNumber > $indelIndex - $numberOfConsideredWindows - 1; $windowNumber--){
			
			#get the window
			$window = $windowsArray[$windowNumber];
			
			#if the motif is found in the window, then increment its corresponding counter
			if ($window =~ m/$motifSequence/i){
	        	$upstreamMotifFrequencyCounter++;
	        }  
		}
		
		#iterate through the considered windows of the upstream flanking sequence and increment the motif frequency counter
		for ($windowNumber = $indelIndex + 1; $windowNumber < $indelIndex + $numberOfConsideredWindows + 1; $windowNumber++){
			
			#get the window
		    $window = $windowsArray[$windowNumber];
		 
		    #if the motif is found in the window, then increment its corresponding counter
			if ($window =~ m/$motifSequence/i){
	        	$downstreamMotifFrequencyCounter++;
	        }  
		}
		
		#store the result into the output file of the motif
		print OUTPUT $motifName . "\t" . $upstreamMotifFrequencyCounter . "\t" . $downstreamMotifFrequencyCounter . "\n";
	}
}
	
#close the input and output files
close(OUTPUT);
close(INPUT2);
close(INPUT1);