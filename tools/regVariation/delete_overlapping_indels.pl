#!/usr/bin/perl -w

# This program detects overlapping indels in a chromosome and keeps all non-overlapping indels. As for overlapping indels, 
# the first encountered one is kept and all others are removed. It requires three inputs: 
# The first input is a TABULAR format file containing coordinates of indels in blocks extracted from multi-alignment.
# The second input is an integer number representing the number of the column where indel start coordinates are stored in the input file.
# The third input is an integer number representing the number of the column where indel end coordinates are stored in the input file.
# The output is a TABULAR format file containing all non-overlapping indels in the input file, and the first encountered indel of overlapping ones.
# Note: The number of the first column is 1.
 
use strict;
use warnings;

#varaibles to handle information related to indels
my $indel1 = "";
my $indel2 = "";
my @indelArray1 = ();
my @indelArray2 = ();
my $lineCounter1 = 0;
my $lineCounter2 = 0;
my $totalNumberofNonOverlappingIndels = 0;

# check to make sure having correct files
my $usage = "usage: delete_overlapping_indels.pl [TABULAR.in] [indelStartColumn] [indelEndColumn] [TABULAR.out]\n";
die $usage unless @ARGV == 4;

my $inputFile = $ARGV[0];
my $indelStartColumn = $ARGV[1] - 1;
my $indelEndColumn = $ARGV[2] - 1;
my $outputFile = $ARGV[3];

#verifie column numbers
if ($indelStartColumn < 0 ){
	die ("The indel start column number is invalid \n"); 
}
if ($indelEndColumn < 0 ){
	die ("The indel end column number is invalid \n"); 
}

#open the input and output files
open (INPUT, "<", $inputFile) || die ("Could not open file $inputFile \n"); 
open (OUTPUT, ">", $outputFile) || die ("Could not open file $outputFile \n"); 

#store the input file in the array @rawData
my @indelsRawData = <INPUT>;

#iterated through the indels of the input file
INDEL1:
foreach $indel1 (@indelsRawData){
	chomp ($indel1);
	$lineCounter1++;
	
	#get the first indel
	@indelArray1 = split(/\t/, $indel1);
	 
	#our purpose is to detect overlapping indels and to store one copy of them only in the output file
	#all other non-overlapping indels will stored in the output file also
			 
	$lineCounter2 = 0;
		 
	#iterated through the indels of the input file
	INDEL2:
	foreach $indel2 (@indelsRawData){
		chomp ($indel2);
		$lineCounter2++;
				
		if ($lineCounter2 > $lineCounter1){
			#get the second indel
			@indelArray2 = split(/\t/, $indel2);
		 				
 			#check if the two indels are overlapping
 			if (($indelArray2[$indelEndColumn] >= $indelArray1[$indelStartColumn] && $indelArray2[$indelEndColumn] <= $indelArray1[$indelEndColumn]) || ($indelArray2[$indelStartColumn] >= $indelArray1[$indelStartColumn] && $indelArray2[$indelStartColumn] <= $indelArray1[$indelEndColumn])){
 				#print ("There is an overlap between" . "\n" . $indel1 . "\n" . $indel2 . "\n");
 				#print("The two overlapping indels are located at the lines: " . $lineCounter1 . " " . $lineCounter2 . "\n\n");
 				
 				#break out of the loop and go back to the outerloop
 				next INDEL1;
 			}
 			else{
 				#print("The two non-overlaapping indels are located at the lines: " . $lineCounter1 . " " . $lineCounter2 . "\n");
 			}
		}
	}
		 
	print OUTPUT $indel1 . "\n";
	$totalNumberofNonOverlappingIndels++;
}

#print("The total number of indels is: " . $lineCounter1 . "\n");
#print("The total number of non-overlapping indels is: " . $totalNumberofNonOverlappingIndels . "\n");

#close the input and output files
close(OUTPUT);
close(INPUT);