#!/usr/bin/perl -w
# Author: Erika Kvikstad

use warnings;
use IO::Handle;
use POSIX qw(floor ceil);

$usage = "execute_dwt_var_perFeature.pl [TABULAR.in] [FEATURE] [ALPHA] [TABULAR.out] [PDF.out] \n";
die $usage unless @ARGV == 5;

#get the input arguments
my $inputFile = $ARGV[0];
my @features = split(/,/,$ARGV[1]);
my $features_count = scalar(@features);
my $alpha = $ARGV[2];
my $outFile1 = $ARGV[3];
my $outFile2 = $ARGV[4];

open (INPUT, "<", $inputFile) || die("Could not open file $inputFile \n");
open (OUTPUT2, ">", $outFile1) || die("Could not open file $outFile1 \n");
open (OUTPUT3, ">", $outFile2) || die("Could not open file $outFile2 \n");
#open (ERROR,  ">", "error.txt")  or die ("Could not open file error.txt \n");

# choosing meaningful names for the output files
$pvalue = $outFile1; 
$pdf = $outFile2; 

# write R script
$r_script = "get_dwt_varPermut.r"; 

open(Rcmd, ">", "$r_script") or die "Cannot open $r_script \n\n";

print Rcmd "
	######################################################################
	# plot multiscale wavelet variance 
	# create null bands by permuting the original data series
	# generate plots and table of wavelet variance including p-values
	######################################################################
	options(echo = FALSE)
	#library(\"Rwave\");
	#library(\"wavethresh\");
	#library(\"waveslim\");
	# turn off diagnostics for de-bugging only, turn back on for functional tests on test
	suppressMessages(require(\"Rwave\",quietly=TRUE,warn.conflicts = FALSE));
	suppressMessages(require(\"wavethresh\",quietly=TRUE,warn.conflicts = FALSE));
	suppressMessages(require(\"waveslim\",quietly=TRUE,warn.conflicts = FALSE));
	suppressMessages(require(\"bitops\",quietly=TRUE,warn.conflicts = FALSE));

	# to determine if data is properly formatted 2^N observations
	is.power2<- function(x){x && !(bitAnd(x,x - 1));}

	# dwt : discrete wavelet transform using Haar wavelet filter, simplest wavelet function but later can modify to let user-define the wavelet filter function
	dwt_var_permut_getMax <- function(data, names, alpha, filter = 1,family=\"DaubExPhase\", bc = \"symmetric\", method = \"kendall\", wf = \"haar\", boundary = \"reflection\") {
		max_var = NULL;
    		matrix = NULL;
		title = NULL;
    		final_pvalue = NULL;
		J = NULL;
		scale = NULL;
		out = NULL;
	
	print(class(data));	
    	print(names);
	print(alpha);
    	
	par(mar=c(5,4,4,3),oma = c(4, 4, 3, 2), xaxt = \"s\", cex = 1, las = 1);
   
	title<-c(\"Wavelet\",\"Variance\",\"Pvalue\",\"Test\");
	print(title);

    	for(i in 1:length(names)){
		temp = NULL;
		results = NULL;
		wave1.dwt = NULL;
	
		# if data fails formatting check, do something
				
		print(is.numeric(as.matrix(data)[, i]));
		if(!is.numeric(as.matrix(data)[, i]))
			stop(\"data must be a numeric vector\");
		
		print(length(as.matrix(data)[, i]));
		print(is.power2(length(as.matrix(data)[, i])));
		if(!is.power2(length(as.matrix(data)[, i])))	
			stop(\"data length must be a power of two\");


    		J <- wd(as.matrix(data)[, i], filter.number = filter, family=family, bc = bc)\$nlevels;
		print(J);
            	temp <- vector(length = J);
               	wave1.dwt <- dwt(as.matrix(data)[, i], wf = wf, J, boundary = boundary); 
		#print(wave1.dwt);
                		
                temp <- wave.variance(wave1.dwt)[-(J+1), 1];
		print(temp);

                #permutations code :
                feature1 = NULL;
		null = NULL;
		var_lower=limit_lower=NULL;
		var_upper=limit_upper=NULL;
		med = NULL;

		limit_lower = alpha/2*1000;
		print(limit_lower);
		limit_upper = (1-alpha/2)*1000;
		print(limit_upper);
		
		feature1 = as.matrix(data)[,i];
                for (k in 1:1000) {
			nk_1 = NULL;
			null.levels = NULL;
			var = NULL;
			null_wave1 = NULL;

                       	nk_1 = sample(feature1, length(feature1), replace = FALSE);
                       	null.levels <- wd(nk_1, filter.number = filter,family=family ,bc = bc)\$nlevels;
                       	var <- vector(length = length(null.levels));
                       	null_wave1 <- dwt(nk_1, wf = wf, J, boundary = boundary);
                       	var<- wave.variance(null_wave1)[-(null.levels+1), 1];
                       	null= rbind(null, var);
               }
               null <- apply(null, 2, sort, na.last = TRUE);
               var_lower <- null[limit_lower, ];
               var_upper <- null[limit_upper, ];
               med <- (apply(null, 2, median, na.rm = TRUE));

               # plot
               results <- cbind(temp, var_lower, var_upper);
		print(results);
                matplot(results, type = \"b\", pch = \"*\", lty = 1, col = c(1, 2, 2),xaxt='n',xlab=\"Wavelet Scale\",ylab=\"Wavelet variance\" );
		mtext(names[i], side = 3, line = 0.5, cex = 1);
		axis(1, at = 1:J , labels=c(2^(0:(J-1))), las = 3, cex.axis = 1);

                # get pvalues by comparison to null distribution
		#out <- (names[i]);
                for (m in 1:length(temp)){
                    	print(paste(\"scale\", m, sep = \" \"));
                       	print(paste(\"var\", temp[m], sep = \" \"));
                       	print(paste(\"med\", med[m], sep = \" \"));
                       	pv = tail =scale = NULL;
			scale=2^(m-1);
			#out <- c(out, format(temp[m], digits = 3));	
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
			print(pv);
			out<-rbind(out,c(paste(\"Scale\", scale, sep=\"_\"),format(temp[m], digits = 3),pv,tail));
                }
		final_pvalue <-rbind(final_pvalue, out);
  	}
	colnames(final_pvalue) <- title;
    	return(final_pvalue);
}\n";

print Rcmd "
# execute
# read in data 
data_test = final = NULL;
sub = sub_names = NULL;
data_test <- read.delim(\"$inputFile\",header=FALSE);
pdf(file = \"$pdf\", width = 11, height = 8)\n";

for ($x=0;$x<$features_count;$x++){	
	$feature=$features[$x];
print Rcmd "
	if ($feature > ncol(data_test))
		stop(\"column $feature doesn't exist\");	
	sub<-data_test[,$feature];
	#sub_names <- colnames(data_test);
	sub_names<-colnames(data_test)[$feature];
	final <- rbind(final,dwt_var_permut_getMax(sub, sub_names,$alpha));\n";
}

print Rcmd "

	dev.off();
	write.table(final, file = \"$pvalue\", sep = \"\\t\", quote = FALSE, row.names = FALSE);

#eof\n";

close Rcmd;
system("R --no-restore --no-save --no-readline < $r_script > $r_script.out");

#close the input and output and error files
close(OUTPUT3);
close(OUTPUT2);
close(INPUT);
