#!/usr/bin/env perl

use strict;
use warnings;

#convert from a MAP and PED file to a genotype file (format desc from PLINK)
#assumes not many SNPs but lots of individuals
# transposed formats are used when lots of SNPs (TPED, TFAM)

if (!@ARGV or scalar @ARGV ne 2) {
   print "usage: lped_to_geno.pl infile.map infile.ped > outfile\n";
   exit;
}

my $map = shift @ARGV;
my $ped = shift @ARGV;

my @snp; #array to hold SNPs from map file
open(FH, $map) or die "Couldn't open $map, $!\n";
while (<FH>) {
   chomp; 
   my @f = split(/\s+/); #3 or 4 columns
   #chrom ID [distance|morgans] position
   if (!exists $f[3]) { $f[3] = $f[2]; } #only 3 columns
   #have to leave in so know which to skip later
   #if ($f[3] < 0) { next; } #way of excluding SNPs
   #if ($f[0] eq '0') { next; } #unplaced SNP
   if ($f[0] !~ /chr/) { $f[0] = "chr$f[0]"; }
   push(@snp, "$f[0]:$f[3]:$f[1]");
}
close FH or die "Couldn't finish $map, $!\n";

#rows are individuals, columns are SNPs (7 & up)
#familyId indId fatherId motherId sex phenotype(-9|0|1|2) alleles....
#need to print row per SNP
my @allele; #alleles to go with @snp
my @pheno;  #marker for phenotype
open(FH, $ped) or die "Couldn't open $ped, $!\n";
while (<FH>) {
   chomp;
   my @f = split(/\s+/);
   if (!defined $f[5]) { die "ERROR undefined phenotype $f[0] $f[1] $f[2] $f[3] $f[4]\n"; }
   #-9 is always unknown, 0 unknown or unaffected, 1|2 is affected
   #either -9|0|1 or 0|1|2
   push(@pheno, $f[5]);
   my $j = 0;
   for(my $i = 6; $i< $#f; $i+=2) {
      if (!$allele[$j]) { $allele[$j] = ''; }
      #can be ACTG or 1234 (for haploview etc) or 0 for missing
      if ($f[$i] eq '1') { $f[$i] = 'A'; }
      elsif ($f[$i] eq '2') { $f[$i] = 'C'; }
      elsif ($f[$i] eq '3') { $f[$i] = 'G'; }
      elsif ($f[$i] eq '4') { $f[$i] = 'T'; }
      if ($f[$i+1] eq '1') { $f[$i+1] = 'A'; }
      elsif ($f[$i+1] eq '2') { $f[$i+1] = 'C'; }
      elsif ($f[$i+1] eq '3') { $f[$i+1] = 'G'; }
      elsif ($f[$i+1] eq '4') { $f[$i+1] = 'T'; }
      $f[$i] = uc($f[$i]);
      $f[$i+1] = uc($f[$i+1]);
      $allele[$j] .= " $f[$i]$f[$i+1]"; 
      $j++;
   }
   if ($j > scalar @snp) { 
      die "ERROR: more allele columns in the ped file than there are SNP positions in the map file.\n";
   }
}
close FH or die "Couldn't close $ped, $!\n";

print "ID Chr Pos";
my $max = 0;
foreach (@pheno) { if ($_ > $max) { $max = $_; } } 
if ($max > 1) {
   foreach (@pheno) { if ($_ > 0) { print " ", $_ - 1; }} #go from 1/2 to 0/1
}else {
   foreach (@pheno) { print " $_"; }
}
print "\n";
for(my $i =0; $i <= $#snp; $i++) { #foreach snp
   $allele[$i] =~ /(\w)/;
   my $nt = $1;
   my $j = 0;
   my @t = split(/:/, $snp[$i]);
   if ($t[0] eq 'chr0' or $t[1] < 0) { next; } #skip this SNP
   if ($t[0] eq 'chrX') { $t[0] = 'chr23'; }
   elsif ($t[0] eq 'chrY') { $t[0] = 'chr24'; }
   elsif ($t[0] eq 'chrXY') { $t[0] = 'chr23'; }
   elsif ($t[0] eq 'chrMT') { $t[0] = 'chr25'; }
   print "$t[2] $t[0] $t[1]";
   $allele[$i] =~ s/^\s+//;
my $test = 0;
   foreach my $p (split(/\s+/, $allele[$i])) {
      if ($pheno[$j] > 0 or ($max == 1 && $pheno[$j] > -1)) { #pheno 0 or -9 skip
          #change AA BB AB to 2 0 1
          if ($p eq "$nt$nt") { print " 2"; }
          elsif ($p =~ /$nt/) { print " 1"; }
          else { print " 0"; }
$test++;
      }
      $j++;
   }
   print "\n";
}

exit;
