#!/usr/bin/env perl

use strict;
use warnings;

#expected input: path to file, cols of counts (2 sets of 3), threshold
if (!@ARGV or scalar @ARGV != 9) {
   print "usage snpFreq.pl /path/to/snps.txt <6 column numbers(1 based) with counts for alleles, first one group then another> #threshold outfile\n";
   exit 1;
}

#get and verify inputs
my $file = shift @ARGV;
my $a1 = shift @ARGV;
if ($a1 =~ /\D/ or $a1 < 1) {
   print "Error the column number, must be an integer greater than or equal to 1. Got $a1\n";
   exit 1;
}
my $a2 = shift @ARGV;
if ($a2 =~ /\D/ or $a2 < 1) {
   print "Error the column number, must be an integer greater than or equal to 1. Got $a2\n";
   exit 1;
}
my $a3 = shift @ARGV;
if ($a3 =~ /\D/ or $a3 < 1) {
   print "Error the column number, must be an integer greater than or equal to 1. Got $a3\n";
   exit 1;
}
my $b1 = shift @ARGV;
if ($b1 =~ /\D/ or $b1 < 1) {
   print "Error the column number, must be an integer greater than or equal to 1. Got $b1\n";
   exit 1;
}
my $b2 = shift @ARGV;
if ($b2 =~ /\D/ or $b2 < 1) {
   print "Error the column number, must be an integer greater than or equal to 1. Got $b2\n";
   exit 1;
}
my $b3 = shift @ARGV;
if ($b3 =~ /\D/ or $b3 < 1) {
   print "Error the column number, must be an integer greater than or equal to 1. Got $b3\n";
   exit 1;
}
my $thresh = shift @ARGV;
if ($thresh !~ /^\d*\.?\d+$/) {
   print "Error the threshold must be a number. Got $thresh\n"; 
   exit 1;
}elsif ($thresh > .3) {
   print "Error the threshold can not be greater than 0.3 got $thresh\n";
   exit 1;
}
my $outfile = shift @ARGV;

#run a fishers exact test (using R) on whole table
my $cmd = qq|options(warn=-1)
           tab <- read.table('$file', sep="\t")
           size <- length(tab[,1])
           width <- length(tab[1,])
           x <- 1:size
           y <- matrix(data=0, nr=size, nc=6)
           for(i in 1:size) {
              m <- matrix(c(tab[i,$a1], tab[i,$b1], tab[i,$a2], tab[i,$b2], tab[i,$a3], tab[i,$b3]), nrow=2)
              t <- fisher.test(m)
              x[i] <- t\$p.value
              if (x[i] >= 1) {
                  x[i] <- .999
              }
              n <- (tab[i,$a1] + tab[i,$a2] + tab[i,$a3] + tab[i,$b1] + tab[i,$b2] + tab[i,$b3])
              n_a <- (tab[i,$a1] + tab[i,$a2] + tab[i,$a3])
              y[i,1] <- ((tab[i,$a1] + tab[i,$b1])*(n_a))/n
              y[i,1] <- round(y[i,1],3)
              y[i,2] <- ((tab[i,$a2] + tab[i,$b2])*(n_a))/n
              y[i,2] <- round(y[i,2],3)
              y[i,3] <- ((tab[i,$a3] + tab[i,$b3])*(n_a))/n
              y[i,3] <- round(y[i,3],3)
              n_b <- (tab[i,$b1] + tab[i,$b2] + tab[i,$b3])
              y[i,4] <- ((tab[i,$a1] + tab[i,$b1])*(n_b))/n
              y[i,4] <- round(y[i,4],3)
              y[i,5] <- ((tab[i,$a2] + tab[i,$b2])*(n_b))/n
              y[i,5] <- round(y[i,5],3)
              y[i,6] <- ((tab[i,$a3] + tab[i,$b3])*(n_b))/n
              y[i,6] <- round(y[i,6],3)
           }|;
           #results <- data.frame(tab[1:size,1:width], x[1:size])
           #write.table(results, file="$outfile", row.names = FALSE ,col.names = FALSE,quote = FALSE, sep="\t")
           #q()|;

my $cmd2 = qq|suppressPackageStartupMessages(library(qvalue))
              qobj <- qvalue(x[1:size], lambda=seq(0,0.90,$thresh), pi0.method="bootstrap", fdr.level=0.1, robust=FALSE, smooth.log.pi0 = FALSE)
              q <- qobj\$qvalues
              results <- data.frame(tab[1:size,1:width], y[1:size,1:6], x[1:size], q[1:size])
              write.table(results, file="$outfile", row.names = FALSE ,col.names = FALSE,quote = FALSE, sep="\t")
              q()|;

#for TESTING
my $pr = qq|results <- data.frame(tab[1:size,1:width], y[1:size,1:6], x[1:size])
            write.table(results, file="$outfile", row.names = FALSE ,col.names = FALSE,quote = FALSE, sep="\t")
              q()|;

open(FT, "| R --slave --vanilla") 
   or die "Couldn't call fisher.text, $!\n";
print FT $cmd, "\n"; #fisher test
print FT $cmd2, "\n"; #qvalues and results
#print FT $pr, "\n";
close FT or die "Couldn't finish fisher.test, $!\n";

exit;
