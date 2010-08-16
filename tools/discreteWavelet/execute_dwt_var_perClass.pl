#!/usr/bin/perl -w

use warnings;
use IO::Handle;
use POSIX qw(floor ceil);

# example: perl execute_dwt_var_perClass.pl hg18_NCNR_10bp_3flanks_deletionHotspot_data_del.txt deletionHotspot 3flanks del

$usage = "execute_dwt_var_perClass.pl [TABULAR.in] [TABULAR.out] [TABULAR.out] [PDF.out] \n";
die $usage unless @ARGV == 4;

#get the input arguments
my $inputFile = $ARGV[0];
my $firstOutputFile = $ARGV[1];
my $secondOutputFile = $ARGV[2];
my $thirdOutputFile = $ARGV[3];

open (INPUT, "<", $inputFile) || die("Could not open file $inputFile \n");
open (OUTPUT1, ">", $firstOutputFile) || die("Could not open file $firstOutputFile \n");
open (OUTPUT2, ">", $secondOutputFile) || die("Could not open file $secondOutputFile \n");
open (OUTPUT3, ">", $thirdOutputFile) || die("Could not open file $thirdOutputFile \n");
open (ERROR,  ">", "error.txt")  or die ("Could not open file error.txt \n");

#save all error messages into the error file $errorFile using the error file handle ERROR
STDERR -> fdopen( \*ERROR,  "w" ) or die ("Could not direct errors to the error file error.txt \n");

# choosing meaningful names for the output files
$max_dwt = $firstOutputFile; 
$pvalue = $secondOutputFile; 
$pdf = $thirdOutputFile; 

# count the number of columns in the input file
while($buffer = <INPUT>){
	#if ($buffer =~ m/interval/){
		chomp($buffer);
		$buffer =~ s/^#\s*//;
		@contrl = split(/\t/, $buffer);
		last;
	#}
}
print "The number of columns in the input file is: " . (@contrl) . "\n";
print "\n";

# count the number of motifs in the input file
$count = 0;
for ($i = 0; $i < @contrl; $i++){
	$count++;
	print "# $contrl[$i]\n";
}
print "The number of motifs in the input file is:  $count \n";

# check if the number of motifs is not a multiple of 12, and round up is so
$count2 = ($count/12);
if ($count2 =~ m/(\D)/){
	print "the number of motifs is not a multiple of 12 \n";
	$count2 = ceil($count2);
}
else {
	print "the number of motifs is a multiple of 12 \n";
}
print "There will be $count2 subfiles\n\n";

# split infile into subfiles only 12 motif per file for R plotting
for ($x = 1; $x <= $count2; $x++){
	$a = (($x - 1) * 12 + 1);
	$b = $x * 12;
	
	if ($x < $count2){
		print "# data.short $x <- data_test[, +c($a:$b)]; \n"; 
	}
	else{
		print "# data.short $x <- data_test[, +c($a:ncol(data_test)]; \n";
	}
}

print "\n";
print "There are 4 output files: \n";
print "The first output file is a pdf file\n";
print "The second output file is a max_dwt file\n";
print "The third output file is a pvalues file\n";
print "The fourth output file is a test_final_pvalues file\n";

# write R script
$r_script = "get_dwt_varPermut_getMax.r"; 
print "The R file name is: $r_script \n";

open(Rcmd, ">", "$r_script") or die "Cannot open $r_script \n\n";

print Rcmd "
	######################################################################
	# plot power spectra, i.e. wavelet variance by class
	# add code to create null bands by permuting the original data series
	# get class of maximum significant variance per feature
	# generate plots and table matrix of variance including p-values
	######################################################################
	library(\"Rwave\");
	library(\"wavethresh\");
	library(\"waveslim\");

	options(echo = FALSE)

	# normalize data
	norm <- function(data){
		v <- (data-mean(data))/sd(data);
    	if(sum(is.na(v)) >= 1){
    		v<-data;
    	}
    	return(v);
	}

	dwt_var_permut_getMax <- function(data, names, filter = 4, bc = \"symmetric\", method = \"kendall\", wf = \"haar\", boundary = \"reflection\") {
		max_var = NULL;
    	matrix = NULL;
		title = NULL;
    	final_pvalue = NULL;
		short.levels = NULL;
		scale = NULL;
	
    	print(names);
    	
   	 	par(mfcol = c(length(names), length(names)), mar = c(0, 0, 0, 0), oma = c(4, 3, 3, 2), xaxt = \"s\", cex = 1, las = 1);
   	 	
    	short.levels <- wd(data[, 1], filter.number = filter, bc = bc)\$nlevels;
    	
    	title <- c(\"motif\");
    	for (i in 1:short.levels){
    		title <- c(title, paste(i, \"var\", sep = \"_\"), paste(i, \"pval\", sep = \"_\"), paste(i, \"test\", sep = \"_\"));
    	}
    	print(title);
        
		# normalize the raw data
    	data<-apply(data,2,norm);

    	for(i in 1:length(names)){
    		for(j in 1:length(names)){
				temp = NULL;
				results = NULL;
				wave1.dwt = NULL;
				out = NULL;
				
				out <- vector(length = length(title));
            	temp <- vector(length = short.levels);
            	
            	if(i < j) {
            		plot(temp, type = \"n\", axes = FALSE, xlab = NA, ylab = NA);
                	box(col = \"grey\"); 
                	grid(ny = 0, nx = NULL);
            	} else {
            		if (i > j){
                		plot(temp, type = \"n\", axes = FALSE, xlab = NA, ylab = NA);
                    	box(col = \"grey\"); 
                    	grid(ny = 0, nx = NULL);
                 	} else {
                 	
                 		wave1.dwt <- dwt(data[, i], wf = wf, short.levels, boundary = boundary); 
                		
                		temp_row = (short.levels + 1 ) * -1;
                		temp_col = 1;
                    	temp <- wave.variance(wave1.dwt)[temp_row, temp_col];

                    	#permutations code :
                    	feature1 = NULL;
						null = NULL;
						var_25 = NULL;
						var_975 = NULL;
						med = NULL;

                    	feature1 = data[, i];
                    	for (k in 1:1000) {
							nk_1 = NULL;
							null.levels = NULL;
							var = NULL;
							null_wave1 = NULL;

                        	nk_1 = sample(feature1, length(feature1), replace = FALSE);
                        	null.levels <- wd(nk_1, filter.number = filter, bc = bc)\$nlevels;
                        	var <- vector(length = length(null.levels));
                        	null_wave1 <- dwt(nk_1, wf = wf, short.levels, boundary = boundary);
                        	var<- wave.variance(null_wave1)[-8, 1];
                        	null= rbind(null, var);
                    	}
                    	null <- apply(null, 2, sort, na.last = TRUE);
                    	var_25 <- null[25, ];
                    	var_975 <- null[975, ];
                    	med <- (apply(null, 2, median, na.rm = TRUE));

                    	# plot
                    	results <- cbind(temp, var_25, var_975);
                    	matplot(results, type = \"b\", pch = \"*\", lty = 1, col = c(1, 2, 2), axes = F);

                    	# get pvalues by comparison to null distribution
                    	out <- (names[i]);
                    	for (m in 1:length(temp)){
                    		print(paste(\"scale\", m, sep = \" \"));
                        	print(paste(\"var\", temp[m], sep = \" \"));
                        	print(paste(\"med\", med[m], sep = \" \"));
                        	pv = tail = NULL;
							out <- c(out, format(temp[m], digits = 3));	
                        	if (temp[m] >= med[m]){
                        		# R tail test
                            	print(\"R\");
	                        	tail <- \"R\";
                            	pv <- (length(which(null[, m] >= temp[m])))/(length(na.exclude(null[, m])));

                        	} else {
                        		if (temp[m] < med[m]){
                                	# L tail test
                                	print(\"L\");
	                            	tail <- \"L\";
                                	pv <- (length(which(null[, m] <= temp[m])))/(length(na.exclude(null[, m])));
                        		}
							}
							out <- c(out, pv);
							print(pv);
							out <- c(out, tail);
                    	}
                    	final_pvalue <-rbind(final_pvalue, out);
                 	
                 
                    	# get variances outside null bands by comparing temp to null
                    	## temp stores variance for each scale, and null stores permuted variances for null bands
                    	for (n in 1:length(temp)){
                    		if (temp[n] <= var_975[n]){
                        		temp[n] <- NA;
                        	} else {
                        		temp[n] <- temp[n];
                        	}
                    	}
                    	matrix <- rbind(matrix, temp)
            		}
            	}
	        	# labels
	        	if (i == 1){
	        		mtext(names[j], side = 2, line = 0.5, las = 3, cex = 0.25);
	        	}
	        	if (j == 1){
	        		mtext(names[i], side = 3, line = 0.5, cex = 0.25);
	        	}
	        	if (j == length(names)){
	        		axis(1, at = (1:short.levels), las = 3, cex.axis = 0.5);
	        	}
    		}
    	}
		colnames(final_pvalue) <- title;
    	#write.table(final_pvalue, file = \"test_final_pvalue.txt\", sep = \"\\t\", quote = FALSE, row.names = FALSE, append = TRUE);

		# get maximum variance larger than expectation by comparison to null bands
    	varnames <- vector();
    	for(i in 1:length(names)){
    		name1 = paste(names[i], \"var\", sep = \"_\")
        	varnames <- c(varnames, name1)
    	}
   		rownames(matrix) <- varnames;
    	colnames(matrix) <- (1:short.levels);
    	max_var <- names;
    	scale <- vector(length = length(names));
    	for (x in 1:nrow(matrix)){
        	if (length(which.max(matrix[x, ])) == 0){
            	scale[x] <- NA;
        	}
        	else{
        		scale[x] <- colnames(matrix)[which.max(matrix[x, ])];
        	}
    	}
    	max_var <- cbind(max_var, scale);
    	write.table(max_var, file = \"$max_dwt\", sep = \"\\t\", quote = FALSE, row.names = FALSE, append = TRUE);
    	return(final_pvalue);
	}\n";

print Rcmd "
	# execute
	# read in data 
	
	data_test = NULL;
	data_test <- read.delim(\"$inputFile\");
	
	pdf(file = \"$pdf\", width = 11, height = 8);
	
	# loop to read and execute on all $count2 subfiles
	final = NULL;
	for (x in 1:$count2){
		sub = NULL;
		sub_names = NULL;
		a = NULL;
		b = NULL;
		
    	a = ((x - 1) * 12 + 1);
    	b = x * 12;
    
    	if (x < $count2){
    		sub <- data_test[, +c(a:b)];
			sub_names <- colnames(data_test)[a:b];
			final <- rbind(final, dwt_var_permut_getMax(sub, sub_names));
    	}
    	else{
    		sub <- data_test[, +c(a:ncol(data_test))];
			sub_names <- colnames(data_test)[a:ncol(data_test)];
			final <- rbind(final, dwt_var_permut_getMax(sub, sub_names));
			
    	}
	}

	dev.off();

	write.table(final, file = \"$pvalue\", sep = \"\\t\", quote = FALSE, row.names = FALSE);

	#eof\n";

close Rcmd;

system("echo \"wavelet ANOVA started on \`hostname\` at \`date\`\"\n");
system("R --no-restore --no-save --no-readline < $r_script > $r_script.out");
system("echo \"wavelet ANOVA ended on \`hostname\` at \`date\`\"\n");

#close the input and output and error files
close(ERROR);
close(OUTPUT3);
close(OUTPUT2);
close(OUTPUT1);
close(INPUT);