#!/usr/bin/perl -w
use strict;

#convert from a vcf file to a pgSnp file with multiple sets of the allele
# specific columns
#frequency count = chromosome count

my $in;
my $stCol = 9;
my $endCol;
if (@ARGV && scalar @ARGV == 1) {
   $in = shift @ARGV;
}else {
   print "usage: vcf2pgSnpMult.pl file.vcf > file.pgSnpMult\n";
   exit;
}

if ($in =~ /.gz$/) {
   open(FH, "zcat $in |") or die "Couldn't open $in, $!\n";
}else {
   open(FH, $in) or die "Couldn't open $in, $!\n";
}
while (<FH>) {
   chomp; 
   if (/^\s*#/) { next; } #skip comments/headers
   if (/^\s*$/) { next; } #skip blank lines
   my @f = split(/\t/);
   #chr pos1base ID refNt altNt[,|D#|Int] quality filter info format geno1 ...
   my $a;
   my %nt;
   my %all;
   my $cnt = 0;
   my $var;
   if ($f[3] eq 'N') { next; } #ignore ref=N
   if ($f[4] =~ /[DI]/ or $f[3] =~ /[DI]/) { next; } #don't do microsatellite
   if ($f[6] && !($f[6] eq '.' or $f[6] eq 'PASS')) { next; } #filtered for some reason
   my $ind = 0;
   if ($f[8] ne 'GT') { #more than just genotype
      my @t = split(/:/, $f[8]);
      foreach (@t) { if ($_ eq 'GT') { last; } $ind++; }
      if ($ind == 0 && $f[8] !~ /^GT/) { die "ERROR couldn't find genotype in format $f[8]\n"; }
   }
   if (!$endCol) { $endCol = $#f; }
   #put f[3] => nt{0} and split f[4] for rest of nt{}
   $nt{0} = $f[3];
   my @t = split(/,/, $f[4]);
   for (my $i=0; $i<=$#t; $i++) {
      my $j = $i + 1;
      $nt{$j} = $t[$i];
   }
   if ($f[0] !~ /chr/) { $f[0] = "chr$f[0]"; }
   print "$f[0]\t", ($f[1]-1), "\t$f[1]"; #position info
   foreach my $col ($stCol .. $endCol) {  #add each individual (4 columns)
      if ($ind > 0) { 
         my @t = split(/:/, $f[$col]);
         $f[$col] = $t[$ind] . ":"; #only keep genotype part
      }
      print "\t";
      if ($f[$col] =~ /^(\d).(\d)/) {
          my $a1 = $1;
          my $a2 = $2;
          if (!exists $nt{$a1}) { die "ERROR bad allele $a1 in $f[3] $f[4]\n"; }
          if (!exists $nt{$a2}) { die "ERROR bad allele $a2 in $f[3] $f[4]\n"; }
          if ($a1 eq $a2) { #homozygous
             print "$nt{$a1}\t1\t2\t0"; 
          }else { #heterozygous
             print "$nt{$a1}/$nt{$a2}\t2\t1,1\t0,0";
          } 
      }elsif ($f[$col] =~ /^(\d):/) { #chrY or male chrX, single
          my $a1 = $1;
          if (!exists $nt{$a1}) { die "ERROR bad allele $a1 in $f[3] $f[4]\n"; }
          print "$nt{$a1}\t1\t1\t0";
      }else { #don't know how to parse
          die "ERROR unknown genotype $f[$col]\n";
      }
   }
   print "\n"; #end this SNP
}
close FH;

exit;
