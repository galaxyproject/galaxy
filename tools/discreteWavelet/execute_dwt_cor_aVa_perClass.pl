#!/usr/bin/perl -w

use warnings;
use IO::Handle;

$usage = "execute_dwt_cor_aVa_perClass.pl [TABULAR.in] [TABULAR.in] [TABULAR.out] [PDF.out]  \n";
die $usage unless @ARGV == 4;

#get the input arguments
my $firstInputFile = $ARGV[0];
my $secondInputFile = $ARGV[1];
my $firstOutputFile = $ARGV[2];
my $secondOutputFile = $ARGV[3];

open (INPUT1, "<", $firstInputFile) || die("Could not open file $firstInputFile \n");
open (INPUT2, "<", $secondInputFile) || die("Could not open file $secondInputFile \n");
open (OUTPUT1, ">", $firstOutputFile) || die("Could not open file $firstOutputFile \n");
open (OUTPUT2, ">", $secondOutputFile) || die("Could not open file $secondOutputFile \n");
open (ERROR,  ">", "error.txt")  or die ("Could not open file error.txt \n");

#save all error messages into the error file $errorFile using the error file handle ERROR
STDERR -> fdopen( \*ERROR,  "w" ) or die ("Could not direct errors to the error file error.txt \n");

print "There are two input data files: \n";
print "The input data file is: $firstInputFile \n";
print "The control data file is: $secondInputFile \n";

# IvC test
$test = "cor_aVa";

# construct an R script to implement the IvC test
print "\n";

$r_script = "get_dwt_cor_aVa_test.r"; 
print "$r_script \n";

open(Rcmd, ">", "$r_script") or die "Cannot open $r_script \n\n";
print Rcmd "
	##################################################################################
	# code to do all correlation tests of form: motif(a) vs. motif(a)
	# add code to create null bands by permuting the original data series
	# generate plots and table matrix of correlation coefficients including p-values
	##################################################################################
	library(\"Rwave\");
	library(\"wavethresh\");
	library(\"waveslim\");
	
	options(echo = FALSE)
	
	# normalize data
	norm <- function(data){
        v <- (data - mean(data))/sd(data);
        if(sum(is.na(v)) >= 1){
        	v <- data;
        }
        return(v);
	}
	
	dwt_cor <- function(data.short, names.short, data.long, names.long, test, pdf, table, filter = 4, bc = \"symmetric\", method = \"kendall\", wf = \"haar\", boundary = \"reflection\") {
		print(test);
	    print(pdf);
		print(table);
		
	    pdf(file = pdf);   
	    final_pvalue = NULL;
		title = NULL;
		
	    short.levels <- wd(data.short[, 1], filter.number = filter, bc = bc)\$nlevels;
		title <- c(\"motif\");
        for (i in 1:short.levels){
	        title <- c(title, paste(i, \"cor\", sep = \"_\"), paste(i, \"pval\", sep = \"_\"));
        }
        print(title);
	
        # normalize the raw data
        data.short <- apply(data.short, 2, norm);
        data.long <- apply(data.long, 2, norm);
        
        for(i in 1:length(names.short)){
        	# Kendall Tau
            # DWT wavelet correlation function
            # include significance to compare
            wave1.dwt = wave2.dwt = NULL;
            tau.dwt = NULL;
            out = NULL;

            print(names.short[i]);
            print(names.long[i]);
            
            # need exit if not comparing motif(a) vs motif(a)
            if (names.short[i] != names.long[i]){
            	stop(paste(\"motif\", names.short[i], \"is not the same as\", names.long[i], sep = \" \"));
            }
            else {
            	wave1.dwt <- dwt(data.short[, i], wf = wf, short.levels, boundary = boundary);
                wave2.dwt <- dwt(data.long[, i], wf = wf, short.levels, boundary = boundary);
                tau.dwt <- vector(length=short.levels)
                       
				#perform cor test on wavelet coefficients per scale 
				for(level in 1:short.levels){
                	w1_level = w2_level = NULL;
                    w1_level <- (wave1.dwt[[level]]);
                    w2_level <- (wave2.dwt[[level]]);
                    tau.dwt[level] <- cor.test(w1_level, w2_level, method = method)\$estimate;
                }
                
                # CI bands by permutation of time series
                feature1 = feature2 = NULL;
                feature1 = data.short[, i];
                feature2 = data.long[, i];
                null = results = med = NULL; 
                cor_25 = cor_975 = NULL;
                
                for (k in 1:1000) {
                	nk_1 = nk_2 = NULL;
                    null.levels = NULL;
                    cor = NULL;
                    null_wave1 = null_wave2 = NULL;
                    
                    nk_1 <- sample(feature1, length(feature1), replace = FALSE);
                    nk_2 <- sample(feature2, length(feature2), replace = FALSE);
                    null.levels <- wd(nk_1, filter.number = filter, bc = bc)\$nlevels;
                    cor <- vector(length = null.levels);
                    null_wave1 <- dwt(nk_1, wf = wf, short.levels, boundary = boundary);
                    null_wave2 <- dwt(nk_2, wf = wf, short.levels, boundary = boundary);

                    for(level in 1:null.levels){
                    	null_level1 = null_level2 = NULL;
                        null_level1 <- (null_wave1[[level]]);
                        null_level2 <- (null_wave2[[level]]);
                        cor[level] <- cor.test(null_level1, null_level2, method = method)\$estimate;
                    }
                    null = rbind(null, cor);
                }
                
                null <- apply(null, 2, sort, na.last = TRUE);
                print(paste(\"NAs\", length(which(is.na(null))), sep = \" \"));
                cor_25 <- null[25,];
                cor_975 <- null[975,];
                med <- (apply(null, 2, median, na.rm = TRUE));

				# plot
                results <- cbind(tau.dwt, cor_25, cor_975);
                matplot(results, type = \"b\", pch = \"*\" , lty = 1, col = c(1, 2, 2), ylim = c(-1, 1), xlab = \"Wavelet Scale\", ylab = \"Wavelet Correlation Kendall's Tau\", main = (paste(test, names.short[i], sep = \" \")), cex.main = 0.75);
                abline(h = 0);

                # get pvalues by comparison to null distribution
 			    ### modify pval calculation for error type II of T test ####
                out <- (names.short[i]);
                for (m in 1:length(tau.dwt)){
                	print(paste(\"scale\", m, sep = \" \"));
                    print(paste(\"tau\", tau.dwt[m], sep = \" \"));
                    print(paste(\"med\", med[m], sep = \" \"));
					out <- c(out, format(tau.dwt[m], digits = 3));	
                    pv = NULL;
                    if(is.na(tau.dwt[m])){
                    	pv <- \"NA\"; 
                    } 
                    else {
                    	if (tau.dwt[m] >= med[m]){
                        	# R tail test
                            print(paste(\"R\"));
                            ### per sv ok to use inequality not strict
                            pv <- (length(which(null[, m] >= tau.dwt[m])))/(length(na.exclude(null[, m])));
                            if (tau.dwt[m] == med[m]){
								print(\"tau == med\");
                                print(summary(null[, m]));
                            }
                    	}
                        else if (tau.dwt[m] < med[m]){
                        	# L tail test
                            print(paste(\"L\"));
                            pv <- (length(which(null[, m] <= tau.dwt[m])))/(length(na.exclude(null[, m])));
                        }
					}
					out <- c(out, pv);
                    print(paste(\"pval\", pv, sep = \" \"));
                }
                final_pvalue <- rbind(final_pvalue, out);
				print(out);
        	}
        }
        colnames(final_pvalue) <- title;
        write.table(final_pvalue, file = table, sep = \"\\t\", quote = FALSE, row.names = FALSE)
        dev.off();
	}\n";

print Rcmd "
	# execute
	# read in data 
		
	inputData1 = inputData2 = NULL;
	inputData.short1 = inputData.short2 = NULL;
	inputDataNames.short1 = inputDataNames.short2 = NULL;
		
	inputData1 <- read.delim(\"$firstInputFile\");
	inputData.short1 <- inputData1[, +c(1:ncol(inputData1))];
	inputDataNames.short1 <- colnames(inputData.short1);
		
	inputData2 <- read.delim(\"$secondInputFile\");
	inputData.short2 <- inputData2[, +c(1:ncol(inputData2))];
	inputDataNames.short2 <- colnames(inputData.short2);
	
	# cor test for motif(a) in inputData1 vs motif(a) in inputData2
	dwt_cor(inputData.short1, inputDataNames.short1, inputData.short2, inputDataNames.short2, test = \"$test\", pdf = \"$secondOutputFile\", table = \"$firstOutputFile\");
	print (\"done with the correlation test\");
	
	#eof\n";
close Rcmd;

system("echo \"wavelet IvC test started on \`hostname\` at \`date\`\"\n");
system("R --no-restore --no-save --no-readline < $r_script > $r_script.out\n");
system("echo \"wavelet IvC test ended on \`hostname\` at \`date\`\"\n");

#close the input and output and error files
close(ERROR);
close(OUTPUT2);
close(OUTPUT1);
close(INPUT2);
close(INPUT1);

