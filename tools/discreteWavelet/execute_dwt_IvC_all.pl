#!/usr/bin/perl -w
use warnings;
use IO::Handle;

$usage = "execute_dwt_IvC_all.pl [TABULAR.in] [TABULAR.in] [TABULAR.out] [PDF.out]  \n";
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
$test = "IvC";

# construct an R script to implement the IvC test
print "\n";

$r_script = "get_dwt_IvC_test.r"; 
print "$r_script \n";

# R script
open(Rcmd, ">", "$r_script") or die "Cannot open $r_script \n\n";
print Rcmd "
        ###########################################################################################
        # code to do wavelet Indel vs. Control
        # signal is the difference I-C; function is second moment i.e. variance from zero not mean
        # to perform wavelet transf. of signal, scale-by-scale analysis of the function 
        # create null bands by permuting the original data series
        # generate plots and table matrix of correlation coefficients including p-values
        ############################################################################################
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
        
        dwt_cor <- function(data.short, names.short, data.long, names.long, test, pdf, table, filter = 4, bc = \"symmetric\", wf = \"haar\", boundary = \"reflection\") {
            print(test);
            print(pdf);
            print(table);
            
            pdf(file = pdf);
            final_pvalue = NULL;
            title = NULL;
                
            short.levels <- wd(data.short[, 1], filter.number = filter, bc = bc)\$nlevels;
            title <- c(\"motif\");
            for (i in 1:short.levels){
            	title <- c(title, paste(i, \"moment2\", sep = \"_\"), paste(i, \"pval\", sep = \"_\"), paste(i, \"test\", sep = \"_\"));
            }
            print(title);
        
            # loop to compare a vs a
            for(i in 1:length(names.short)){
        		wave1.dwt = NULL;
        		m2.dwt = diff = var.dwt = NULL;
        		out = NULL;
                out <- vector(length = length(title));
        
        		print(names.short[i]);
        		print(names.long[i]);
                        
        		# need exit if not comparing motif(a) vs motif(a)
        		if (names.short[i] != names.long[i]){
                	stop(paste(\"motif\", names.short[i], \"is not the same as\", names.long[i], sep = \" \"));
        		}
        		else {
                	# signal is the difference I-C data sets
                    diff<-data.short[,i]-data.long[,i];
        
                    # normalize the signal
                    diff<-norm(diff);
        
                    # function is 2nd moment
                    # 2nd moment m_j = 1/N[sum_N(W_j + V_J)^2] = 1/N sum_N(W_j)^2 + (X_bar)^2 
            		wave1.dwt <- dwt(diff, wf = wf, short.levels, boundary = boundary);
            		var.dwt <- wave.variance(wave1.dwt);
                	m2.dwt <- vector(length = short.levels)
                    for(level in 1:short.levels){
                    	m2.dwt[level] <- var.dwt[level, 1] + (mean(diff)^2);
                    }
                                
            		# CI bands by permutation of time series
            		feature1 = feature2 = NULL;
            		feature1 = data.short[, i];
            		feature2 = data.long[, i];
            		null = results = med = NULL; 
            		m2_25 = m2_975 = NULL;
            
            		for (k in 1:1000) {
                		nk_1 = nk_2 = NULL;
                		m2_null = var_null = NULL;
                		null.levels = null_wave1 = null_diff = NULL;
                		nk_1 <- sample(feature1, length(feature1), replace = FALSE);
                		nk_2 <- sample(feature2, length(feature2), replace = FALSE);
                		null.levels <- wd(nk_1, filter.number = filter, bc = bc)\$nlevels;
                		null_diff <- nk_1-nk_2;
                		null_diff <- norm(null_diff);
                		null_wave1 <- dwt(null_diff, wf = wf, short.levels, boundary = boundary);
                        var_null <- wave.variance(null_wave1);
                		m2_null <- vector(length = null.levels);
                		for(level in 1:null.levels){
                        	m2_null[level] <- var_null[level, 1] + (mean(null_diff)^2);
                		}
                		null= rbind(null, m2_null);
            		}
                
            		null <- apply(null, 2, sort, na.last = TRUE);
            		m2_25 <- null[25,];
            		m2_975 <- null[975,];
            		med <- apply(null, 2, median, na.rm = TRUE);

            		# plot
            		results <- cbind(m2.dwt, m2_25, m2_975);
            		matplot(results, type = \"b\", pch = \"*\", lty = 1, col = c(1, 2, 2), xlab = \"Wavelet Scale\", ylab = c(\"Wavelet 2nd Moment\", test), main = (names.short[i]), cex.main = 0.75);
            		abline(h = 1);

            		# get pvalues by comparison to null distribution
            		out <- c(names.short[i]);
            		for (m in 1:length(m2.dwt)){
                    	print(paste(\"scale\", m, sep = \" \"));
                        print(paste(\"m2\", m2.dwt[m], sep = \" \"));
                        print(paste(\"median\", med[m], sep = \" \"));
                        out <- c(out, format(m2.dwt[m], digits = 4));	
                        pv = NULL;
                        if(is.na(m2.dwt[m])){
                        	pv <- \"NA\"; 
                        } 
                        else {
                        	if (m2.dwt[m] >= med[m]){
                            	# R tail test
                                tail <- \"R\";
                                pv <- (length(which(null[, m] >= m2.dwt[m])))/(length(na.exclude(null[, m])));
                            }
                            else{
                                if (m2.dwt[m] < med[m]){
                                	# L tail test
                                    tail <- \"L\";
                                    pv <- (length(which(null[, m] <= m2.dwt[m])))/(length(na.exclude(null[, m])));
                                }
                            }
                        }
                        out <- c(out, pv);
                        print(pv);  
                        out <- c(out, tail);
                    }
                    final_pvalue <-rbind(final_pvalue, out);
                    print(out);
                }
            }
            
            colnames(final_pvalue) <- title;
            write.table(final_pvalue, file = table, sep = \"\\t\", quote = FALSE, row.names = FALSE);
            dev.off();
        }\n";

print Rcmd "
        # execute
        # read in data 
        
        inputData <- read.delim(\"$firstInputFile\");
        inputDataNames <- colnames(inputData);
        
        controlData <- read.delim(\"$secondInputFile\");
        controlDataNames <- colnames(controlData);
        
        # call the test function to implement IvC test
        dwt_cor(inputData, inputDataNames, controlData, controlDataNames, test = \"$test\", pdf = \"$secondOutputFile\", table = \"$firstOutputFile\");
        print (\"done with the correlation test\");
\n";

print Rcmd "#eof\n";

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