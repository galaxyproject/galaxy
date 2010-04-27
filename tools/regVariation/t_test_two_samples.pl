# A program to implement the non-pooled t-test for two samples where the alternative hypothesis is two-sided or one-sided. 
# The first input file is a TABULAR format file representing the first sample and consisting of one column only.
# The second input file is a TABULAR format file representing the first sample nd consisting of one column only.
# The third input is the sidedness of the t-test: either two-sided or, one-sided with m1 less than m2 or, 
# one-sided with m1 greater than m2. 
# The fourth input is the equality status of the standard deviations of both populations
# The output file is a TXT file representing the result of the two sample t-test.

use strict;
use warnings;

#variable to handle the motif information
my $motif;
my $motifName = "";
my $motifNumber = 0;
my $totalMotifsNumber = 0;
my @motifNamesArray = ();

# check to make sure having correct files
my $usage = "usage: non_pooled_t_test_two_samples_galaxy.pl [TABULAR.in] [TABULAR.in] [testSidedness] [standardDeviationEquality] [TXT.out] \n";
die $usage unless @ARGV == 5;

#get the input arguments
my $firstSampleInputFile = $ARGV[0];
my $secondSampleInputFile = $ARGV[1];
my $testSidedness = $ARGV[2];
my $standardDeviationEquality = $ARGV[3]; 
my $outputFile = $ARGV[4];

#open the input files
open (INPUT1, "<", $firstSampleInputFile) || die("Could not open file $firstSampleInputFile \n"); 
open (INPUT2, "<", $secondSampleInputFile) || die("Could not open file $secondSampleInputFile \n"); 
open (OUTPUT, ">", $outputFile) || die("Could not open file $outputFile \n");


#variables to store the name of the R script file
my $r_script;
	
# R script to implement the two-sample test on the motif frequencies in upstream flanking region 	
#construct an R script file and save it in the same directory where the perl file is located
$r_script = "non_pooled_t_test_two_samples.r";

open(Rcmd,">", $r_script) or die "Cannot open $r_script \n\n";
print Rcmd "
        sampleTable1 <- read.table(\"$firstSampleInputFile\", header=FALSE);
		sample1 <- sampleTable1[, 1];
		
		sampleTable2 <- read.table(\"$secondSampleInputFile\", header=FALSE);
		sample2 <- sampleTable2[, 1];
		
		testSideStatus <- \"$testSidedness\";
		STEqualityStatus <- \"$standardDeviationEquality\";
		
		#open the output a text file
		sink(file = \"$outputFile\");
		
		#check if the t-test is two-sided
		if (testSideStatus == \"two-sided\"){
			
			#check if the standard deviations are equal in both populations
			if (STEqualityStatus == \"equal\"){
				#two-sample t-test where standard deviations are assumed to be unequal, the test is two-sided
				testResult <- t.test(sample1, sample2, var.equal = TRUE);	
			} else{
				#two-sample t-test where standard deviations are assumed to be unequal, the test is two-sided
				testResult <- t.test(sample1, sample2, var.equal = FALSE);
			}
		} else{  #the t-test is one sided	
			
			#check if the t-test is two-sided with m1 < m2
			if (testSideStatus == \"one-sided:_m1_less_than_m2\"){
				
				#check if the standard deviations are equal in both populations
				if (STEqualityStatus == \"equal\"){
					#two-sample t-test where standard deviations are assumed to be unequal, the test is one-sided: Halt: m1 < m2
					testResult <- t.test(sample1, sample2, var.equal = TRUE, alternative = \"less\");
				} else{
					#two-sample t-test where standard deviations are assumed to be unequal, the test is one-sided: Halt: m1 < m2
					testResult <- t.test(sample1, sample2, var.equal = FALSE, alternative = \"less\");
				}
			} else{   #the t-test is one-sided with m1 > m2
				#check if the standard deviations are equal in both populations
				if (STEqualityStatus == \"equal\"){
					#two-sample t-test where standard deviations are assumed to be unequal, the test is one-sided: Halt: m1 < m2
					testResult <- t.test(sample1, sample2, var.equal = TRUE, alternative = \"greater\");
				} else{
					#two-sample t-test where standard deviations are assumed to be unequal, the test is one-sided: Halt: m1 < m2
					testResult <- t.test(sample1, sample2, var.equal = FALSE, alternative = \"greater\");
				}
			}
		}
		
		#save the output of the t-test into the output text file
		testResult;
		
		#close the output text file
		sink();
		
		#eof" . "\n";
		
close Rcmd;	

system("R --no-restore --no-save --no-readline < $r_script > $r_script.out");

#close the input and output files
close(OUTPUT);
close(INPUT2);
close(INPUT1);

