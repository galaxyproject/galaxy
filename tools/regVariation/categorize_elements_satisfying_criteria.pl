#!/usr/bin/perl -w

# The program takes as input a set of categories, such that each category contains many elements.
# It also takes a table relating elements with criteria, such that each element is assigned a number
# representing the number of times the element satisfies a certain criterion. 
# The first input is a TABULAR format file, such that the left column represents the name of categories and, 
# all other columns represent the names of elements.
# The second input is a TABULAR format file relating elements with criteria, such that the first line
# represents the names of criteria and the left column represents the names of elements.
# The output is a TABULAR format file relating catergories with criteria, such that each categoy is 
# assigned a number representing the total number of times its elements satisfies a certain criterion.
# Each category is assigned as many numbers as criteria.

use strict;
use warnings;

#variables to handle information of the categories input file
my @categoryElementsArray = ();
my @categoriesArray = ();
my $categoryMemberNames;
my $categoryName;
my %categoryMembersHash = ();
my $memberNumber = 0;
my $totalMembersNumber = 0;
my $totalCategoriesNumber = 0;
my @categoryCountersTwoDimArray = ();
my $lineCounter1 = 0;

#variables to handle information of the criteria and elements data input file
my $elementLine;
my @elementDataArray = ();
my $elementName;
my @criteriaArray = ();
my $criteriaNumber = 0;
my $totalCriteriaNumber = 0;
my $lineCounter2 = 0;

#variable representing the row and column indices used to store results into a two-dimensional array
my $row = 0;
my $column = 0;

# check to make sure having correct files
my $usage = "usage: categorize_motifs_significance.pl [TABULAR.in] [TABULAR.in] [TABULAR.out] \n";
die $usage unless @ARGV == 3;

#get the categories input file
my $categories_inputFile = $ARGV[0];

#get the criteria and data input file
my $elements_data_inputFile = $ARGV[1];

#get the output file
my $categorized_data_outputFile = $ARGV[2];

#open the input and output files
open (INPUT1, "<", $categories_inputFile) || die("Could not open file $categories_inputFile \n");
open (INPUT2, "<", $elements_data_inputFile ) || die("Could not open file $elements_data_inputFile  \n");
open (OUTPUT, ">", $categorized_data_outputFile) || die("Could not open file $categorized_data_outputFile \n"); 

#store the first input file into an array
my @categoriesData = <INPUT1>;

#reset the value of $lineCounter1 to 0 
$lineCounter1 = 0;

#iterate through the first input file to get the names of categories and their corresponding elements	
foreach $categoryMemberNames (@categoriesData){
	chomp ($categoryMemberNames);
		
	@categoryElementsArray = split(/\t/, $categoryMemberNames);
	
	#store the name of the current category into an array
	$categoriesArray [$lineCounter1] = $categoryElementsArray[0];
	
	#store the name of the current category into a two-dimensional array
	$categoryCountersTwoDimArray [$lineCounter1] [0] = $categoryElementsArray[0];
		
	#get the total number of elements in the current category
	$totalMembersNumber = @categoryElementsArray;
	
	#store the names of categories and their corresponding elements	into a hash
	for ($memberNumber = 1; $memberNumber < $totalMembersNumber; $memberNumber++) {
			
		$categoryMembersHash{$categoryElementsArray[$memberNumber]} = $categoriesArray[$lineCounter1];
	}
	
	$lineCounter1++;
}

#store the second input file into an array
my @elementsData = <INPUT2>;

#reset the value of $lineCounter2 to 0 
$lineCounter2 = 0;

#iterate through the second input file in order to count the number of elements
#in each category that satisfy each criterion	
foreach $elementLine (@elementsData){
	chomp ($elementLine);
		
	$lineCounter2++;
	
	@elementDataArray = split(/\t/, $elementLine);
	
	#if at the first line, get the total number of criteria and the total  
	#number of catergories and initialize the two-dimensional array
	if ($lineCounter2 == 1){
		@criteriaArray = @elementDataArray;	
		$totalCriteriaNumber = @elementDataArray;
		
		$totalCategoriesNumber = @categoriesArray;
		
		#initialize the two-dimensional array
		for ($row = 0; $row < $totalCategoriesNumber; $row++) {
	
			for ($column = 1; $column <= $totalCriteriaNumber; $column++) {
				
				$categoryCountersTwoDimArray [$row][$column] = 0;
			}
		}
	}
	else{
		#get the element data
		$elementName = $elementDataArray[0];
		
		#do the counting and store the result in the two-dimensional array
		for ($criteriaNumber = 0; $criteriaNumber < $totalCriteriaNumber; $criteriaNumber++) {
			
			if ($elementDataArray[$criteriaNumber + 1] > 0){
				
				$categoryName = $categoryMembersHash{$elementName};
				
				my ($categoryIndex) = grep $categoriesArray[$_] eq $categoryName, 0 .. $#categoriesArray;
				
				$categoryCountersTwoDimArray [$categoryIndex] [$criteriaNumber + 1] = $categoryCountersTwoDimArray [$categoryIndex] [$criteriaNumber + 1] + $elementDataArray[$criteriaNumber + 1];
			}
		}
	}
}

print OUTPUT "\t";

#store the criteria names into the output file	
for ($column = 1; $column <= $totalCriteriaNumber; $column++) {
		
	if ($column < $totalCriteriaNumber){
		print OUTPUT $criteriaArray[$column - 1] . "\t";
	}
	else{
		print OUTPUT $criteriaArray[$column - 1] . "\n";
	}
}
	
#store the category names and their corresponding number of elements satisfying criteria into the output file
for ($row = 0; $row < $totalCategoriesNumber; $row++) {
	
	for ($column = 0; $column <= $totalCriteriaNumber; $column++) {
		
		if ($column < $totalCriteriaNumber){
			print OUTPUT $categoryCountersTwoDimArray [$row][$column] . "\t";
		}
		else{
			print OUTPUT $categoryCountersTwoDimArray [$row][$column] . "\n";
		}
	}
}

#close the input and output file
close(OUTPUT);
close(INPUT2);
close(INPUT1);

