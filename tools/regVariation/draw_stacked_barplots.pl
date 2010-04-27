#!/usr/bin/perl -w

# This program draws, in a pdf file, a stacked bars plot for different categories of data and for 
# different criteria. For each criterion a stacked bar is drawn, such that the height of each stacked 
# sub-bar represents the number of elements in each category satisfying that criterion.
# The input consists of a TABULAR format file, where the left column represents the names of categories 
# and the other columns are headed by the names of criteria, such that each data value in the file 
# represents the number of elements in a certain category satisfying a certain criterion.
# The output is a PDF file containing a stacked bars plot representing the number of elements in each 
# category satisfying each criterion. The drawing is done using R code.  

  
use strict;
use warnings;

my $criterion;
my @criteriaArray = ();
my $criteriaNumber = 0;
my $lineCounter = 0;

#variable to store the names of R script file
my $r_script;

# check to make sure having correct files
my $usage = "usage: draw_stacked_bar_plot.pl [TABULAR.in] [PDF.out] \n";
die $usage unless @ARGV == 2;

my $categoriesInputFile = $ARGV[0];

my $categories_criteria_bars_plot_outputFile = $ARGV[1];

#open the input file
open (INPUT, "<", $categoriesInputFile) || die("Could not open file $categoriesInputFile \n"); 
open (OUTPUT, ">", $categories_criteria_bars_plot_outputFile) || die("Could not open file $categories_criteria_bars_plot_outputFile \n");

# R script to implement the drawing of a stacked bar plot representing thes significant motifs in each category of motifs 	
#construct an R script file 
$r_script = "motif_significance_bar_plot.r";
open(Rcmd,">", $r_script) or die "Cannot open $r_script \n\n";
print Rcmd "
			#store the table content of the first file into a matrix
			categoriesTable <- read.table(\"$categoriesInputFile\", header = TRUE);
			categoriesMatrix <- as.matrix(categoriesTable); 
			
			
			#compute the sum of elements in the column with the maximum sum in each matrix
			columnSumsVector <- colSums(categoriesMatrix);
			maxColumn <- max (columnSumsVector);
			
			if (maxColumn %% 10 != 0){
				maxColumn <- maxColumn + 10;
			}
			
			plotHeight = maxColumn/8;
			criteriaVector <- names(categoriesTable);
			
			pdf(file = \"$categories_criteria_bars_plot_outputFile\", width = length(criteriaVector), height = plotHeight, family = \"Times\", pointsize = 12, onefile = TRUE);
			
			
			
			#draw the first barplot
			barplot(categoriesMatrix, ylab = \"No. of elements in each category\", xlab = \"Criteria\", ylim = range(0, maxColumn), col = \"black\", density = c(10, 20, 30, 40, 50, 60, 70, 80), angle = c(45, 90, 135), names.arg = criteriaVector);
			
			#draw the legend
			legendX = 0.2;
			legendY = maxColumn;
			
			legend (legendX, legendY, legend = rownames(categoriesMatrix), density = c(10, 20, 30, 40, 50, 60, 70, 80), angle = c(45, 90, 135));
   			
   			dev.off();
			
			#eof\n";
close Rcmd;	
system("R --no-restore --no-save --no-readline < $r_script > $r_script.out");

#close the input files
close(OUTPUT);
close(INPUT);
