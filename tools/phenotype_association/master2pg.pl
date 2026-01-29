#!/usr/bin/env perl
use strict;

#convert from master variant file to pgSnp
my $snpsOnly = 1; #flag for if doing SNPs or indels
if (@ARGV && $ARGV[0] eq 'indel') { shift @ARGV; $snpsOnly = 0; }
my $in = shift @ARGV;
open(FH, $in) or die "Couldn't open input file $in, $!\n";

while (<FH>) {
   chomp;
   if (/^#/) { next; }
   if (/^>/) { next; } #headers
   if (/^\s*$/) { next; } 
   my @f = split(/\t/);
   if (!$f[5]) { next; } #WHAT? most likely still zipped?
   if ($f[5] =~ /(hom|het)/) { #zygosity #haploid chrX and chrY?
      #only get snps for now
      if ($snpsOnly && $f[6] eq 'snp') { #varType
         my $a;
         my $c = 2;
         my $freq;
         my $sc;
         if ($f[8] eq $f[9]) { #should be homozygous?
            $a = $f[8];
            $c = 1;
         }else {
            $a = "$f[8]/$f[9]";
         }
         if (defined $f[10] && $c == 1) {
            $sc = $f[10];
         }elsif (defined $f[10] && defined $f[11] && $c == 2) {
            $sc = "$f[10],$f[11]";
         }
         if (defined $f[16] && $c == 1) {
            $freq = $f[16];
         }elsif (defined $f[16] && defined $f[17] && $c == 2) {
            $freq = "$f[16],$f[17]";
         }
         print "$f[2]\t$f[3]\t$f[4]\t$a\t$c\t$freq\t$sc\n";
      }elsif (!$snpsOnly) {
         if ($f[8] =~ /^\s*$/) { undef $f[8]; }
         if ($f[9] =~ /^\s*$/) { undef $f[9]; }
         my $a;
         my $c = 2;
         #do indels
         if ($f[6] eq "ins") {
            if (defined $f[8] && defined $f[9] && $f[8] eq $f[9]) { $a = $f[8]; $c = 1; }
            elsif (defined $f[8] && defined $f[9] && $f[8] ne '?' && $f[9] ne '?') { 
               $a = "$f[8]/$f[9]";
            }elsif (!defined $f[8] && defined $f[9]) {
               $a = "$f[9]/-";
            }elsif (defined $f[8] && !defined $f[9]) {
               $a = "$f[8]/-";
            }
         }elsif ($f[6] eq "del") {
            if (!defined $f[8] && !defined $f[9]) {
               $a = '-'; #homozygous deletion
               $c = 1;
            }elsif (!defined $f[8] && defined $f[9]) {
               $a = "$f[9]/-";
            }elsif (defined $f[8] && !defined $f[9]) {
               $a = "$f[8]/-";
            }            
         }elsif ($f[6] eq "sub") { #multiple nt substitutions
            if ($f[8] eq $f[9]) {
               $a = $f[8];
               $c = 1;
            }else {
               $a = "$f[8]/$f[9]";
            }
         }elsif ($f[6] eq "complex") { #treat same as multi-nt sub
            if ($f[5] =~ /het-alt/ && !defined $f[8]) { $f[8] = '-'; }
            if ($f[5] =~ /het-alt/ && !defined $f[9]) { $f[9] = '-'; }
            if (defined $f[8] && defined $f[9] && $f[8] eq $f[9]) {
               $c = 1;
               $a = $f[8];
            }elsif (defined $f[8] && defined $f[9]) {
               $a = "$f[8]/$f[9]";
            }
         }
         my $sc = '';
         my $freq = '';
         if (defined $f[10] && $c == 1) {
            $sc = $f[10];
         }elsif (defined $f[10] && defined $f[11] && $c == 2) {
            $sc = "$f[10],$f[11]";
         }
         if (defined $f[16] && $c == 1) {
            $freq = $f[16];
         }elsif (defined $f[16] && defined $f[17] && $c == 2) {
            $freq = "$f[16],$f[17]";
         }
         if ($a) {
            print "$f[2]\t$f[3]\t$f[4]\t$a\t$c\t$freq\t$sc\n";
         }
      }
   }elsif ($f[5] eq 'hap' && $f[6] eq 'snp' && $snpsOnly) {
      my $c = 1;
      my $freq = '';
      if (defined $f[10]) { $freq = $f[10]; }
      my $sc = '';
      if (defined $f[16]) { $sc = $f[16]; }
      if ($f[8]) {
         print "$f[2]\t$f[3]\t$f[4]\t$f[8]\t$c\t$freq\t$sc\n";
      }   
   }elsif ($f[5] eq 'hap' && !$snpsOnly && $f[6] =~ /(del|ins|sub)/) {
      if ($f[8] =~ /^\s*$/) { undef $f[8]; }
      my $a;
      my $c = 1;
      #do indels
      if ($f[6] eq "ins") {
         $a = $f[8]; 
      }elsif ($f[6] eq "del") {
         $a = '-'; #deletion
      }elsif ($f[6] eq "sub") { #multiple nt substitutions
         $a = $f[8];
      }
      my $sc = '';
      my $freq = '';
      if (defined $f[10]) { $sc = $f[10]; }
      if (defined $f[16]) { $freq = $f[16]; }
      if ($a) {
         print "$f[2]\t$f[3]\t$f[4]\t$a\t$c\t$freq\t$sc\n";
      }
   }
}

close FH or die "Couldn't close $in, $!\n";

exit;
