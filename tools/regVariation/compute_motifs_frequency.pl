#!/usr/bin/perl -w

# a program to compute the frequency of each motif at each window in both upstream and downstream sequences flanking indels
# in a chromosome/genome.
# the first input is a TABULAR format file containing the motif names and sequences, such that the file consists of two
# columns: the left column represents the motif names and the right column represents the motif sequence, one line per motif.
# the second input is a TABULAR format file containing the upstream and downstream sequences flanking indels, one line per indel.
# the fourth input is an integer number representing the window size according to which the upstream and downstream sequences
# flanking each indel will be divided.
# the first output is a TABULAR format file containing the windows into which both upstream and downstream sequences flanking 
# indels are divided.
# the second output is a TABULAR format file containing the motifs and their corresponding frequencies at each window in both 
# upstream and downstream sequences flanking indels, one line per motif.
 
use strict;
use warnings;

#variable to handle the falnking sequences information
my $sequence = "";
my $upstreamFlankingSequence = "";
my $downstreamFlankingSequence = "";
my $discardedSequenceLength = 0;
my $lengthOfDownstreamFlankingSequenceAfterTrimming = 0;

#variable to handle the window information
my $window = "";
my $windowStartIndex = 0;
my $windowNumber = 0;
my $totalWindowsNumber = 0;
my $totalNumberOfWindowsInUpstreamSequence = 0;
my $totalNumberOfWindowsInDownstreamSequence = 0;
my $totalWindowsNumberInBothFlankingSequences = 0;
my $totalWindowsNumberInMotifCountersTwoDimArray = 0;
my $upstreamAndDownstreamFlankingSequencesWindows = "";

#variable to handle the motif information
my $motif = "";
my $motifSequence = "";
my $motifNumber = 0;
my $totalMotifsNumber = 0;

#arrays to sotre window and motif data
my @windowsArray = ();
my @motifNamesArray = ();
my @motifSequencesArray = ();
my @motifCountersTwoDimArray = ();

#variables to store line counter values
my $lineCounter1 = 0;
my $lineCounter2 = 0;

# check to make sure having correct files
my $usage = "usage: compute_motifs_frequency.pl [TABULAR.in] [TABULAR.in] [windowSize] [TABULAR.out] [TABULAR.out]\n";
die $usage unless @ARGV == 5;

#get the input and output arguments
my $motifsInputFile = $ARGV[0];
my $indelFlankingSequencesInputFile = $ARGV[1];
my $windowSize = $ARGV[2];
my $indelFlankingSequencesWindowsOutputFile = $ARGV[3];
my $motifFrequenciesOutputFile = $ARGV[4];

#open the input and output files
open (INPUT1, "<", $motifsInputFile) || die("Could not open file $motifsInputFile \n"); 
open (INPUT2, "<", $indelFlankingSequencesInputFile) || die("Could not open file $indelFlankingSequencesInputFile \n"); 
open (OUTPUT1, ">", $indelFlankingSequencesWindowsOutputFile) || die("Could not open file $indelFlankingSequencesWindowsOutputFile \n");   
open (OUTPUT2, ">", $motifFrequenciesOutputFile) || die("Could not open file $motifFrequenciesOutputFile \n"); 

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

#store the input file in the array @sequencesData
my @sequencesData = <INPUT2>;

#iterated through the sequences of the second input file in order to create windwos file
foreach $sequence (@sequencesData){
	chomp ($sequence);
	$lineCounter1++;
	
	my @indelAndSequenceArray = split(/\t/, $sequence);
	
	#get the upstream falnking sequence
	$upstreamFlankingSequence = $indelAndSequenceArray[3];
	
	#if the window size is 0, then the whole upstream will be one window only
	if ($windowSize == 0){
		$totalNumberOfWindowsInUpstreamSequence = 1;
		$windowSize = length ($upstreamFlankingSequence);
	}
	else{
		#compute the total number of windows into which the upstream flanking sequence will be divided
		$totalNumberOfWindowsInUpstreamSequence = length ($upstreamFlankingSequence) / $windowSize;
		
		#compute the length of the subsequence to be discared from the upstream flanking sequence if any
		$discardedSequenceLength = length ($upstreamFlankingSequence) % $windowSize;
		
		#check if the sequence could be split into windows of equal sizes
	    if ($discardedSequenceLength != 0) {
	    	#trim the upstream flanking sequence
			$upstreamFlankingSequence = substr($upstreamFlankingSequence, $discardedSequenceLength); 
		}
	}
		
	#split the upstream flanking sequence into windows
	for ($windowNumber = 0; $windowNumber < $totalNumberOfWindowsInUpstreamSequence; $windowNumber++){
		$windowStartIndex = $windowNumber * $windowSize;
		print OUTPUT1 (substr($upstreamFlankingSequence, $windowStartIndex, $windowSize) . "\t");
	}
	
	#add a column representing the indel
	print OUTPUT1 ("indel" . "\t");
	
	#get the downstream falnking sequence
	$downstreamFlankingSequence = $indelAndSequenceArray[4];
	
	#if the window size is 0, then the whole upstream will be one window only
	if ($windowSize == 0){
		$totalNumberOfWindowsInDownstreamSequence = 1;
		$windowSize = length ($downstreamFlankingSequence);
	}
	else{
		#compute the total number of windows into which the downstream flanking sequence will be divided
		$totalNumberOfWindowsInDownstreamSequence = length ($downstreamFlankingSequence) / $windowSize;
		
		#compute the length of the subsequence to be discared from the upstream flanking sequence if any
		$discardedSequenceLength = length ($downstreamFlankingSequence) % $windowSize;
		
		#check if the sequence could be split into windows of equal sizes
	    if ($discardedSequenceLength != 0) {
	    	#compute the length of the sequence to be discarded
	    	$lengthOfDownstreamFlankingSequenceAfterTrimming = length ($downstreamFlankingSequence) - $discardedSequenceLength;
	    	
	    	#trim the downstream flanking sequence
			$downstreamFlankingSequence = substr($downstreamFlankingSequence, 0, $lengthOfDownstreamFlankingSequenceAfterTrimming); 
		}
	}
	
	#split the downstream flanking sequence into windows
	for ($windowNumber = 0; $windowNumber < $totalNumberOfWindowsInDownstreamSequence; $windowNumber++){
		$windowStartIndex = $windowNumber * $windowSize;
		print OUTPUT1 (substr($downstreamFlankingSequence, $windowStartIndex, $windowSize) . "\t");
	}
	
	print OUTPUT1 ("\n");
}

#compute the total number of windows on both upstream and downstream sequences flanking the indel
$totalWindowsNumberInBothFlankingSequences = $totalNumberOfWindowsInUpstreamSequence + $totalNumberOfWindowsInDownstreamSequence;

#add an additional cell to store the name of the motif and another one for the indel itself
$totalWindowsNumberInMotifCountersTwoDimArray = $totalWindowsNumberInBothFlankingSequences + 1 + 1;

#initialize the two dimensional array $motifCountersTwoDimArray. the first column will be initialized with motif names
for ($motifNumber = 0; $motifNumber < $totalMotifsNumber; $motifNumber++){
	
	for ($windowNumber = 0; $windowNumber < $totalWindowsNumberInMotifCountersTwoDimArray; $windowNumber++){
		
		if ($windowNumber == 0){
			$motifCountersTwoDimArray [$motifNumber] [0] = $motifNamesArray[$motifNumber];
		}
		elsif ($windowNumber == $totalNumberOfWindowsInUpstreamSequence + 1){
			$motifCountersTwoDimArray [$motifNumber] [$windowNumber] = "indel";
		}
		else{
			$motifCountersTwoDimArray [$motifNumber] [$windowNumber] = 0;
		}
	}
}

close(OUTPUT1);

#open the file the contains the windows of the upstream and downstream flanking sequences, which is actually the first output file
open (INPUT3, "<", $indelFlankingSequencesWindowsOutputFile) || die("Could not open file $indelFlankingSequencesWindowsOutputFile \n");   

#store the first output file containing the windows of both upstream and downstream flanking sequences in the array @windowsData
my @windowsData = <INPUT3>;

#iterated through the lines of the first output file. Each line represents   
#the windows of the upstream and downstream flanking sequences of an indel
foreach $upstreamAndDownstreamFlankingSequencesWindows (@windowsData){
	
	chomp ($upstreamAndDownstreamFlankingSequencesWindows);
	$lineCounter2++;
	
	#split both upstream and downstream flanking sequences into their windows
	my @windowsArray = split(/\t/, $upstreamAndDownstreamFlankingSequencesWindows);
	
	$totalWindowsNumber = @windowsArray;
	
	#iterate through the windows to search for matched motifs and increment their corresponding counters accordingly
	WINDOWS:
	for ($windowNumber = 0; $windowNumber < $totalWindowsNumber; $windowNumber++){
		
		#get the window
		$window = $windowsArray[$windowNumber];
		
        #if the window is the one that contains the indel, then skip the indel window
        if ($window eq "indel") {  
        	next WINDOWS;	
        }
        else{  #iterated through the motif sequences to check their occurrences in the winodw 
               #and increment their corresponding counters accordingly
	        
	        for ($motifNumber = 0; $motifNumber < $totalMotifsNumber; $motifNumber++){
	        	#get the motif sequence
	        	$motifSequence = $motifSequencesArray[$motifNumber];
	        	
	        	#if the motif is found in the window, then increment its corresponding counter
	        	if ($window =~ m/$motifSequence/i){
	        		$motifCountersTwoDimArray [$motifNumber] [$windowNumber + 1]++;
	        	}  
	        }
        }
	}
}

#store the motif counters values in the second output file
for ($motifNumber = 0; $motifNumber < $totalMotifsNumber; $motifNumber++){
	
	for ($windowNumber = 0; $windowNumber <= $totalWindowsNumber; $windowNumber++){
		
		print OUTPUT2 $motifCountersTwoDimArray [$motifNumber] [$windowNumber] . "\t";
		#print ($motifCountersTwoDimArray [$motifNumber] [$windowNumber] . " ");
	}
	print OUTPUT2 "\n";
	#print ("\n");
}
		
#close the input and output files
close(OUTPUT2);
close(OUTPUT1);
close(INPUT3);
close(INPUT2);
close(INPUT1);