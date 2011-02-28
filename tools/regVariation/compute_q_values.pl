# A program to compute the q-values based on the p-values of multiple simultaneous tests. 
# The q-valules are computed using a specific R package created by John Storey called "qvalue".
# The input is a TABULAR format file consisting of one column only that represents the p-values 
# of multiple simultaneous tests, one line for every p-value. 
# The first output is a TABULAR format file consisting of one column only that represents the q-values 
# corresponding to p-values, one line for every q-value. 
# the second output is a TABULAR format file consisting of three pages: the first page represents 
# the p-values histogram, the second page represents the q-values histogram, and the third page represents 
# the four Q-plots as introduced in the "qvalue" package manual.

use strict;
use warnings;
use IO::Handle;
use File::Temp qw/ tempfile tempdir /;
my $tdir = tempdir( CLEANUP => 0 );

# check to make sure having correct input and output files
my $usage = "usage: compute_q_values.pl [TABULAR.in] [lambda] [pi0_method] [fdr_level] [robust] [TABULAR.out] [PDF.out] \n";
die $usage unless @ARGV == 7;

#get the input arguments
my $p_valuesInputFile = $ARGV[0];
my $lambdaValue =  $ARGV[1];
my $pi0_method =  $ARGV[2];
my $fdr_level =  $ARGV[3];
my $robustValue =  $ARGV[4];
my $q_valuesOutputFile = $ARGV[5];
my $p_q_values_histograms_QPlotsFile = $ARGV[6];

if($lambdaValue =~ /sequence/){
	$lambdaValue = "seq(0, 0.95, 0.05)";
}

#open the input files
open (INPUT, "<", $p_valuesInputFile) || die("Could not open file $p_valuesInputFile \n");
open (OUTPUT1, ">", $q_valuesOutputFile) || die("Could not open file $q_valuesOutputFile \n");
open (OUTPUT2, ">", $p_q_values_histograms_QPlotsFile) || die("Could not open file $p_q_values_histograms_QPlotsFile \n");
#open (ERROR,  ">", "error.txt")  or die ("Could not open file error.txt \n");

#save all error messages into the error file $errorFile using the error file handle ERROR
#STDERR -> fdopen( \*ERROR,  "w" ) or die ("Could not direct errors to the error file error.txt \n");

#warn "Hello Error File \n";

#variable to store the name of the R script file
my $r_script;

# R script to implement the calcualtion of q-values based on multiple simultaneous tests p-values 	
# construct an R script file and save it in a temp directory
chdir $tdir;
$r_script = "q_values_computation.r";

open(Rcmd,">", $r_script) or die "Cannot open $r_script \n\n"; 
print Rcmd "
	#options(show.error.messages = FALSE);
	
	#load necessary packages
	suppressPackageStartupMessages(library(tcltk));
	library(qvalue);
	
	#read the p-values of the multiple simultaneous tests from the input file $p_valuesInputFile
	p <- scan(\"$p_valuesInputFile\", quiet = TRUE);
	
	#compute the q-values that correspond to the p-values of the multiple simultaneous tests
	qobj <- qvalue(p, pi0.meth = \"$pi0_method\", lambda = $lambdaValue, fdr.level = $fdr_level, robust = $robustValue);
	#qobj <- qvalue(p, pi0.meth = \"smoother\", lambda = seq(0, 0.95, 0.05), fdr.level = 0.05);
	#qobj <- qvalue(p, pi0.meth = \"bootstrap\", fdr.level = 0.05);
	
	#draw the p-values histogram, the q-values histogram, and the four Q-plots 
	# and save them on multiple pages of the output file $p_q_values_histograms_QPlotsFile
	pdf(file = \"$p_q_values_histograms_QPlotsFile\", width = 6.25, height = 6, family = \"Times\", pointsize = 12, onefile = TRUE)
	hist(qobj\$pvalues);
	#dev.off();
	
	hist(qobj\$qvalues);
	#dev.off(); 
	
	qplot(qobj);  
	dev.off();
	
	#save the q-values in the output file $q_valuesOutputFile
	qobj\$pi0 <- signif(qobj\$pi0,digits=6)
	qwrite(qobj, filename=\"$q_valuesOutputFile\"); 

	#options(show.error.messages = TRUE);
	#eof\n";
close Rcmd;	

system("R --no-restore --no-save --no-readline < $r_script > $r_script.out");

#close the input and output and error files
#close(ERROR);
close(OUTPUT2);
close(OUTPUT1);
close(INPUT);
