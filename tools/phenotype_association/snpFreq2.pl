#!/usr/bin/env perl

use strict;
use warnings;

#using large SNP tables (~1G) may require large memory ~15G in R

#expected input: path to file, cols of counts (2 sets of 3), threshold
if (!@ARGV or scalar @ARGV != 11) {
   if (!@ARGV or scalar @ARGV != 6) { #snpTable usage
      print "usage for tab separated allele counts\n",
            "snpFreq.pl inputType #threshold /path/to/snps.txt outfile <6 column numbers(1 based) with counts for alleles, first one group then another>\n";
      print "OR for SNP tables\n";
      print "usage snpFreq.pl inputType #threshold /path/to/snpTable.txt outfile group1File group2File\n";
      exit 1;
   }
}

#get and verify inputs
my ($file, $a1, $a2, $a3, $b1, $b2, $b3, $thresh, $outfile);
if ($ARGV[0] eq 'tab') {
   shift @ARGV;
   $thresh = shift @ARGV;
   if ($thresh !~ /^\d*\.?\d+$/) {
      print "Error the threshold must be a number. Got $thresh\n";
      exit 1;
   }elsif ($thresh > .3) {
      print "Error the threshold can not be greater than 0.3 got $thresh\n";
      exit 1;
   }
   $file = shift @ARGV;
   $outfile = shift @ARGV;
   $a1 = shift @ARGV;
   if ($a1 =~ /\D/ or $a1 < 1) {
      print "Error the column number, must be an integer greater than or equal to 1. Got $a1\n";
      exit 1;
   }
   $a2 = shift @ARGV;
   if ($a2 =~ /\D/ or $a2 < 1) {
      print "Error the column number, must be an integer greater than or equal to 1. Got $a2\n";
      exit 1;
   }
   $a3 = shift @ARGV;
   if ($a3 =~ /\D/ or $a3 < 1) {
      print "Error the column number, must be an integer greater than or equal to 1. Got $a3\n";
      exit 1;
   }
   $b1 = shift @ARGV;
   if ($b1 =~ /\D/ or $b1 < 1) {
      print "Error the column number, must be an integer greater than or equal to 1. Got $b1\n";
      exit 1;
   }
   $b2 = shift @ARGV;
   if ($b2 =~ /\D/ or $b2 < 1) {
      print "Error the column number, must be an integer greater than or equal to 1. Got $b2\n";
      exit 1;
   }
   $b3 = shift @ARGV;
   if ($b3 =~ /\D/ or $b3 < 1) {
      print "Error the column number, must be an integer greater than or equal to 1. Got $b3\n";
      exit 1;
   }
}else { #snp table convert and assign variables
   #snpTable.txt #threshold outfile workingdir
   shift @ARGV;
   $thresh = shift @ARGV;
   if ($thresh !~ /^\d*\.?\d+$/) {
      print "Error the threshold must be a number. Got $thresh\n";
      exit 1;
   }elsif ($thresh > .3) {
      print "Error the threshold can not be greater than 0.3 got $thresh\n";
      exit 1;
   }
   $file = shift @ARGV;
   $outfile  = shift @ARGV;
   my $grpFile = shift @ARGV;
   my @g1;
   open(FH, $grpFile) or die "Couldn't open $grpFile, $!\n";
   while (<FH>) {
      chomp; 
      if (/^(\d+)\s/) { push(@g1, $1); }
   }
   close FH or die "Couldn't close $grpFile, $!\n";
   $grpFile = shift @ARGV;
   my @g2;
   open(FH, $grpFile) or die "Couldn't open $grpFile, $!\n";
   while (<FH>) {
      chomp;
      if (/^(\d+)\s/) { push(@g2, $1); }
   }
   close FH or die "Couldn't close $grpFile, $!\n";
   if ($file =~ /.gz$/) { 
      open(FH, "zcat $file |") or die "Couldn't read $file, $!\n";
   }else {
      open(FH, $file) or die "Couldn't read $file, $!\n";
   }
   open(OUT, ">", "snpTable.txt") or die "Couldn't open snpTable.txt, $!\n";
   my $size;
   while (<FH>) {
      chomp;
      if (/^#/) { next; } #header
      my @f = split(/\t/);
      $size = scalar @f;
      my @gc1 = (0, 0, 0);
      my @gc2 = (0, 0, 0);
      foreach my $g (@g1) { 
         my $i = $g+1; #g is 1 based first col want 0 based snp call column
         if ($i > $#f) { die "ERROR looking for index $i which is greater than the list $#f\n"; }
         if ($f[$i] == -1 or $f[$i] == 2) { #treat unknown as ref 
            $gc1[0]++;
         }elsif ($f[$i] == 1) { 
            $gc1[2]++;
         }elsif ($f[$i] == 0) {
            $gc1[1]++;
         }else { die "Unexpected value for genotype $f[$i] in ", join(" ", @f), "\n"; }
      }
      foreach my $g (@g2) {
         my $i = $g+1; #g is 1 based first col want 0 based snp call column
         if ($f[$i] == -1 or $f[$i] == 2) { #treat unknown as ref 
            $gc2[0]++;
         }elsif ($f[$i] == 1) {
            $gc2[2]++;
         }elsif ($f[$i] == 0) {
            $gc2[1]++;
         }else { die "Unexpected value for genotype $f[$i] in ", join(" ", @f), "\n"; }
      }
      print OUT join("\t", @f), "\t", join("\t", @gc1), "\t", join("\t", @gc2), 
         "\n";
   }
   close FH or die "Couldn't close $file, $!\n";
   close OUT or die "Couldn't close snpTable.txt, $!\n";
   my $i = $size + 1; #next 1 based column after input data
   $a1 = $i++;
   $a2 = $i++;
   $a3 = $i++;
   $b1 = $i++;
   $b2 = $i++;
   $b3 = $i++;
   $file = "snpTable.txt";
}

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

#my $cmd2 = qq|suppressPackageStartupMessages(library(lib.loc='/afs/bx.psu.edu/home/giardine/lib/R', qvalue))
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
