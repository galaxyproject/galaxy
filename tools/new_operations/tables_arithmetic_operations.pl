# A program to implement arithmetic operations on tabular files data. The program takes three inputs:
# The first input is a TABULAR format file containing numbers only.
# The second input is a TABULAR format file containing numbers only.
# The two files must have the same number of columns and the same number of rows
# The third input is an arithmetic operation: +, -, *, or / for addition, subtraction, multiplication, or division, respectively 
# The output file is a TABULAR format file containing the result of implementing the arithmetic operation on both input files.
# The output file has the same number of columns and the same number of rows as each of the two input files.
# Note: in case of division, none of the values in the second input file could be 0.

use strict;
use warnings;

#variables to handle information of the first input tabular file
my $lineData1 = "";
my @lineDataArray1 = ();
my $lineArraySize = 0;
my $lineCounter1 = 0;

#variables to handle information of the second input tabular file
my $lineData2= "";
my @lineDataArray2 = ();
my $lineCounter2 = 0;

my $result = 0;

# check to make sure having the correct number of arguments
my $usage = "usage: tables_arithmetic_operations.pl [TABULAR.in] [TABULAR.in] [ArithmeticOperation] [TABULAR.out] \n";
die $usage unless @ARGV == 4;

#variables to store the names of input and output files
my $inputTabularFile1 = $ARGV[0];
my $inputTabularFile2 = $ARGV[1];
my $arithmeticOperation = $ARGV[2];
my $outputTabularFile = $ARGV[3];

#open the input and output files
open (INPUT1, "<", $inputTabularFile1) || die("Could not open file $inputTabularFile1 \n"); 
open (INPUT2, "<", $inputTabularFile2) || die("Could not open file $inputTabularFile2 \n"); 
open (OUTPUT, ">", $outputTabularFile) || die("Could not open file $outputTabularFile \n");

#store the first input file in the array @motifsFrequencyData1
my @tabularData1 = <INPUT1>;
	
#store the second input file in the array @motifsFrequencyData2
my @tabularData2 = <INPUT2>;

#reset the $lineCounter1 to 0	
$lineCounter1 = 0;

#iterated through the lines of the first input file 
INDEL1:
foreach $lineData1 (@tabularData1){
	chomp ($lineData1);
	$lineCounter1++;
	
	#reset the $lineCounter2 to 0
	$lineCounter2 = 0;
	
	#iterated through the lines of the second input file 
	foreach $lineData2 (@tabularData2){
		chomp ($lineData2);
		$lineCounter2++;

		#check if the two motifs are the same in the two input files
		if ($lineCounter1 == $lineCounter2){
			
			@lineDataArray1 = split(/\t/, $lineData1);
			@lineDataArray2 = split(/\t/, $lineData2);
			
			$lineArraySize = @lineDataArray1;
			
			for (my $index = 0; $index < $lineArraySize; $index++){
				
				if ($arithmeticOperation eq "Addition"){
					#compute the additin of both values
					$result = $lineDataArray1[$index] + $lineDataArray2[$index];
				}
				
				if ($arithmeticOperation eq "Subtraction"){
					#compute the subtraction of both values
					$result = $lineDataArray1[$index] - $lineDataArray2[$index];
				}	
				
				if ($arithmeticOperation eq "Multiplication"){
					#compute the multiplication of both values
					$result = $lineDataArray1[$index] * $lineDataArray2[$index];
				}
				
				if ($arithmeticOperation eq "Division"){
					
					#check if the denominator is 0
					if ($lineDataArray2[$index] != 0){
						#compute the division of both values
						$result = $lineDataArray1[$index] / $lineDataArray2[$index];
					}
					else{
						die("A denominator could not be zero \n"); 
					}
				}
				
				#store the result in the output file
				if ($index < $lineArraySize - 1){
					print OUTPUT $result . "\t";
				}
				else{
					print OUTPUT $result . "\n";
				}
			}
			next INDEL1;
		}
	}
}	 

#close the input and output files
close(OUTPUT);
close(INPUT2);
close(INPUT1);