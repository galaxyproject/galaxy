#!/usr/bin/perl -w 
use strict;

#########################################################################
#	codingSnps.pl
#	This takes a bed file with the names being / separated nts
#	and a gene bed file with cds start and stop.
#	It then checks for changes in coding regions, reporting
#	those that cause a frameshift or substitution in the amino acid.
#	Output columns:
#		chrom, start, end, allele as given (amb code translated)
#		Gene ID from genes file, ref amino acid:variant amino acids,
#		codon number, (in strand of gene)ref nt, refCodon:variantCodons
#########################################################################

my $seqFlag = "2bit"; #flag to set sequence type 2bit|nib
if (!@ARGV or scalar @ARGV < 3) {
   print "Usage: codingSnps.pl snps.bed genes.bed (/dir/*$seqFlag|Galaxy build= loc=) [chr=# start=# end=# snp=# strand=#|-|+ keepColumns=1 synon=1 unique=1] > codingSnps.txt\n";
   exit;
}
my $uniq = 0; #flag for whether want uniq positions
my $syn = 0;  #flag for if want synonomous changes rather than non-syn
my $keep = 0; #keep old columns and append new ones
my $snpFile = shift @ARGV;
my $geneFile = shift @ARGV;
my $nibDir = shift @ARGV;  #2bit or nib, depending on flag above
if ($nibDir eq 'Galaxy') { getGalaxyInfo(); }
my $col0 = 0; #bed like columns in default positions
my $col1 = 1;
my $col2 = 2;
my $col3 = 3;
my $strand = -1;
#column positions 1 based coming in (for Galaxy)
foreach (@ARGV) {
   if (/chr=(\d+)/) { $col0 = $1 -1; }
   elsif (/start=(\d+)/) { $col1 = $1 -1; }
   elsif (/end=(\d+)/) { $col2 = $1 -1; }
   elsif (/snp=(\d+)/) { $col3 = $1 -1; }
   elsif (/keepColumns=1/) { $keep = 1; }
   elsif (/synon=1/) { $syn = 1; }
   elsif (/unique=1/) { $uniq = 1; }
   elsif (/strand=(\d+)/) { $strand = $1 -1; } #0 based column
   elsif (/strand=-/) { $strand = -99; }  #special case of all minus
}
if ($col0 < 0 || $col1 < 0 || $col2 < 0 || $col3 < 0) {
   print STDERR "ERROR column numbers are given with origin 1\n";
   exit 1;
}
my @genes; #bed lines for genes, sorted by chrom and start
my %chrSt; #index in array where each chrom starts
my %codon; #hash of codon amino acid conversions
my $ends = 0; #ends vs sizes in bed 11 position, starts relative to chrom
my $ignoreN = 1; #skip N
my $origAll; #alleles from input file (before changes for strand)

my %amb = (
"R" => "A/G",
"Y" => "C/T",
"S" => "C/G",
"W" => "A/T",
"K" => "G/T",
"M" => "A/C",
"B" => "C/G/T",
"D" => "A/G/T",
"H" => "A/C/T",
"V" => "A/C/G",
"N" => "A/C/G/T"
);
fill_codon();
open(FH, "cat $geneFile | sort -k1,1 -k2,2n |") 
   or die "Couldn't open and sort $geneFile, $!\n";
my $i = 0;
while(<FH>) {
   chomp;
   if (/refGene.cdsEnd|ccdsGene.exonEnds/) { $ends = 1; next; }
   push(@genes, "$_");
   my @f = split(/\t/);
   if (!exists $chrSt{$f[0]}) { $chrSt{$f[0]} = $i; }
   $i++;
}
close FH or die "Couldn't close $geneFile, $!\n";

if ($ends) { print STDERR "WARNING using block ends rather than sizes\n"; }

#open snps sorted as well
my $s1 = $col0 + 1; #sort order is origin 1
my $s2 = $col1 + 1; 
open(FH, "cat $snpFile | sort -k$s1,$s1 -k$s2,${s2}n |")
   or die "Couldn't open and sort $snpFile, $!\n";
$i = 0;
my @g; #one genes fields, should be used repeatedly
my %done;
while(<FH>) {
   chomp;
   if (/^\s*#/) { next; } #comment
   my @s = split(/\t/); #SNP fields
   if (!@s or !$s[$col0]) { die "ERROR missing SNP data, $_\n"; }
   my $size = $#s;
   if ($col0 > $size || $col1 > $size || $col2 > $size || $col3 > $size) {
      print STDERR "ERROR file has fewer columns than requested, requested columns (0 based) $col0 $col1 $col2 $col3, file has $size\n";
      exit 1;
   }
   if ($strand >= 0 && $strand > $size) { 
      print STDERR "ERROR file has fewer columns than requested, requested strand in $strand (0 based), file has $size\n";
      exit 1;
   }
   if ($s[$col1] =~ /\D/) { 
      print STDERR "ERROR the start point must be an integer not $s[$col1]\n";
      exit 1;
   }
   if ($s[$col2] =~ /\D/) {
      print STDERR "ERROR the start point must be an integer not $s[$col2]\n";
      exit 1;
   }
   if ($s[$col3] eq 'N' && $ignoreN) { next; }
   if (exists $amb{$s[$col3]}) { $s[$col3] = $amb{$s[$col3]}; }
   if (($strand >= 0 && $s[$strand] eq '-') or $strand == -99) { 
      #reverse complement nts
      $origAll = $s[$col3];
      $s[$col3] = reverseCompAlleles($s[$col3]);
   }else { undef $origAll }
   if (!@g && exists $chrSt{$s[$col0]}) { #need to fetch first gene row
      $i = $chrSt{$s[$col0]};
      @g = split(/\t/, $genes[$i]);
      if (scalar @g < 12) {  
         print STDERR "ERROR the gene file must be the whole genes in BED format\n";
         exit 1;
      }
   }elsif (!@g) { 
      next; #no gene for this chrom
   }elsif ($s[$col0] ne $g[0] && exists $chrSt{$s[$col0]}) { #new chrom 
      $i = $chrSt{$s[$col0]};
      @g = split(/\t/, $genes[$i]);
   }elsif ($s[$col0] ne $g[0]) {
      next; #no gene for this chrom
   }elsif ($s[$col1] < $g[1] && $i == $chrSt{$s[$col0]}) {
      next; #before any genes
   }elsif ($s[$col1] > $g[2] && ($i == $#genes or $genes[$i+1] !~ $s[$col0])) {
      next; #after all genes on chr
   }else {
      while ($s[$col1] > $g[2] && $i < $#genes) {
         $i++;
         @g = split(/\t/, $genes[$i]);
         if ($s[$col0] ne $g[0]) { last; } #end of gene
      }
      if ($s[$col0] ne $g[0] or $s[$col1] < $g[1] or $s[$col1] > $g[2]) {
         next; #no overlap with genes
      }
   }

   processSnp(\@s, \@g);
   if ($uniq && exists $done{"$s[$col0] $s[$col1] $s[$col2]"}) { next; }

   my $k = $i + 1; #check for more genes without losing data of first
   if ($k <= $#genes) {
      my @g2 = split(/\t/, $genes[$k]);
      while (@g2 && $k <= $#genes) {
         @g2 = split(/\t/, $genes[$k]);
         if ($s[$col0] ne $g2[0]) {
            undef @g2;
            last; #not same chrom
         }else {
            while ($s[$col1] > $g2[2] && $k <= $#genes) {
               $k++;
               @g2 = split(/\t/, $genes[$k]);
               if ($s[$col0] ne $g2[0]) { last; } #end of chrom
            }
            if ($s[$col0] ne $g2[0] or $s[$col1] < $g2[1] or $s[$col1] > $g2[2]) {
               undef @g2;
               last; #no overlap with more genes
            }
            processSnp(\@s, \@g2);
            if ($uniq && exists $done{"$s[$col0] $s[$col1] $s[$col2]"}) { last; }
         }      
         $k++;
      }
   }
}
close FH or die "Couldn't close $snpFile, $!\n";

exit;

########################################################################
sub processSnp {
   my $sref = shift;
   my $gref = shift;
   #overlaps gene, but maybe not coding seq
   #inside cds
   if ($sref->[$col1] + 1 < $gref->[6] or $sref->[$col2] > $gref->[7]) {
      return; #outside of coding 
   }
   #now check exon
   my $i = 0;
   my @st = split(/,/, $gref->[11]);
   my @size = split(/,/, $gref->[10]);
   if (scalar @st ne $gref->[9]) { return; } #cant do this gene #die "bad gene $gref->[3]\n"; }
   my @pos;
   my $in = 0;
   for($i = 0; $i < $gref->[9]; $i++) {
      my $sta = $gref->[1] + $st[$i] + 1; #1 based position
      my $end = $sta + $size[$i] - 1; #
      if ($ends) { $end = $size[$i]; $sta = $st[$i] + 1; } #ends instead of sizes
      if ($end < $gref->[6]) { next; } #utr only
      if ($sta > $gref->[7]) { next; } #utr only
      #shorten to coding only
      if ($sta < $gref->[6]) { $sta = $gref->[6] + 1; }
      if ($end > $gref->[7]) { $end = $gref->[7]; }
      if ($sref->[$col1] + 1 >= $sta && $sref->[$col2] <= $end) { $in = 1; }
      elsif ($sref->[$col1] == $sref->[$col2] && $sref->[$col2] <= $end && $sref->[$col2] >= $sta) { $in = 1; }
      push(@pos, ($sta .. $end)); #add exon worth of positions
   }
   #@pos has coding positions for whole gene (chr coors), 
   #and $in has whether we need to continue
   if (!$in) { return; } #not in coding exon
   if ((scalar @pos) % 3 != 0) { return; } #partial gene? not even codons
   if ($sref->[$col3] =~ /^-+\/[ACTG]+$/ or $sref->[$col3] =~ /^[ACTG]+\/-+$/ or
       $sref->[$col3] =~ /^-+$/) { #indel or del
      my $copy = $sref->[$col3];
      my $c = ($copy =~ tr/-//);
      if ($c % 3 == 0) { return; } #not frameshift 
      #handle bed4 or any interval file
      if (!$keep) {
         print "$sref->[$col0]\t$sref->[$col1]\t$sref->[$col2]\t$sref->[$col3]";
         print "\t$gref->[3]\tframeshift\n";
      }else {
         my @s = @{$sref};
         print join("\t", @s), "\t$gref->[3]\tframeshift\n";
      }
      $done{"$sref->[$col0] $sref->[$col1] $sref->[$col2]"}++;
      return;
   }elsif ($sref->[$col1] == $sref->[$col2]) { #insertion
      my $copy = $sref->[$col3];
      my $c = ($copy =~ tr/\[ACTG]+//);
      if ($c % 3 == 0) { return; } #not frameshift
      #handle bed4 or any interval file
      if (!$keep) {
         print "$sref->[$col0]\t$sref->[$col1]\t$sref->[$col2]\t$sref->[$col3]";
         print "\t$gref->[3]\tframeshift\n";
      }else {
         my @s = @{$sref};
         print join("\t", @s), "\t$gref->[3]\tframeshift\n";
      }
      $done{"$sref->[$col0] $sref->[$col1] $sref->[$col2]"}++;
      return;
   }elsif ($sref->[$col3] =~ /-/) { #indel and sub?
      return; #skip
   }
   #check for amino acid substitutions
   my $s = $sref->[$col1] + 1;
   my $e = $sref->[$col2];
   my $len = $sref->[$col2] - $sref->[$col1];
   if ($gref->[5] eq '-') { 
      @pos = reverse(@pos); 
      my $t = $s;
      $s = $e;
      $e = $t;
   }
   $i = 0;
   my $found = 0;
   foreach (@pos) {
      if ($s == $_) {
         $found = 1;
         last;
      }
      $i++;
   }
   if ($found) {
      my $fs = $i; #keep original start index
      #have index where substitution starts
      my $cp = $i % 3; 
      $i -= $cp; #i is now first position in codon
      my $cdNum = int($i / 3) + 1;
      my $ls = $i;
      if (!defined $ls) { die "ERROR not defined ls for $fs $sref->[$col2]\n"; }
      if (!@pos) { die "ERROR not defined array pos\n"; }
      if (!defined $pos[$ls]) { die "ERROR not defined pos at $ls\n"; }
      if (!defined $e) { die "ERROR not defined e for $pos[0] $pos[1] $pos[2]\n"; }
      while ($ls <= $#pos && $pos[$ls] ne $e) { 
         $ls++; 
      }
      my $i2 = $ls + (2 - ($ls % 3));
      if ($i2 > $#pos) { return; } #not a full codon, partial gene?

      if ($i2 - $i < 2) { die "not a full codon positions $i to $i2 for $sref->[3]\n"; }
      my $oldnts = getnts($sref->[$col0], @pos[$i..$i2]);
      if (!$oldnts) { die "Failed to get sequence for $sref->[$col0] $pos[$i] .. $pos[$i2]\n"; }
      my @vars = split(/\//, $sref->[$col3]);
      if ($gref->[5] eq '-') { #complement oldnts and revcomp vars
         $oldnts = compl($oldnts);
         if (!$oldnts) { return; } #skip this one
         $oldnts = join('', (reverse(split(/ */, $oldnts))));
         foreach (@vars) {
            $_ = reverse(split(/ */)); #needed for indels
            $_ = compl($_);
         }
      }
      my $r = $fs - $i; #difference in old indexes gives new index
      my @newnts;
      my $changed = '';
      foreach my $v (@vars) {
         if (!$v or length($v) != 1) { return; } #only simple changes
         my @new = split(/ */, $oldnts);
         $changed = splice(@new, $r, $len, split(/ */, $v));
         #should only change single nt
         push(@newnts, join("", @new));
      }
      #now compute amino acids
      my $oldaa = getaa($oldnts);
      my $codon = "$oldnts:";
      my @newaa;
      my $change = 0; #flag for if there is a change
      foreach my $v (@newnts) {
         my $t = getaa($v);
         if ($t ne $oldaa) { $change = 1; }
         push(@newaa, "$t");
         $codon .= "$v/";
      }
      $codon =~ s/\/$//; 
      if (!$change && $syn) { 
          if (!$keep) {
             print "$sref->[$col0]\t$sref->[$col1]\t$sref->[$col2]\t$sref->[$col3]";
             print "\t$gref->[3]\t$oldaa:", join("/", @newaa), "\t$cdNum\t$changed\t$codon\n";
          }else {
             my @s = @{$sref};
             print join("\t", @s), 
                   "\t$gref->[3]\t$oldaa:", join("/", @newaa), "\t$cdNum\t$changed\t$codon\n";
          }
          $done{"$sref->[$col0] $sref->[$col1] $sref->[$col2]"}++;
          return;
      }elsif ($syn) { return; } #only want synonymous changes
      if (!$change) { return; } #no change in amino acids
      if (!$keep) {
         my $a = $sref->[$col3];
         if (($strand >= 0 && $origAll) or $strand == -99) { $a = $origAll; }
         print "$sref->[$col0]\t$sref->[$col1]\t$sref->[$col2]\t$a";
         #my $minus = $changed; #in case minus strand and change back
         #if ($gref->[5] eq '-') { $changed = compl($changed); } #use plus for ref
         if (!$changed) { return; } #skip this one
         print "\t$gref->[3]\t$oldaa:", join("/", @newaa), "\t$cdNum\t$changed\t$codon\n";
      }else {
         my @s = @{$sref};
         if (($strand >= 0 && $origAll) or $strand == -99) { $s[$col3] = $origAll; }
         print join("\t", @s);
         #my $minus = $changed; #in case minus strand and change back
         #if ($gref->[5] eq '-') { $changed = compl($changed); } #use plus for ref
         if (!$changed) { return; } #skip this one
         print "\t$gref->[3]\t$oldaa:", join("/", @newaa), "\t$cdNum\t$changed\t$codon\n";
      }
      $done{"$sref->[$col0] $sref->[$col1] $sref->[$col2]"}++;
   }
}

sub getnts {
   my $chr = shift;
   my @pos = @_; #list of positions not necessarily in order
   #list may be reversed or have gaps(introns), at least 3 bps
   my $seq = '';
   if (scalar @pos < 3) { die "too small region for $chr $pos[0]\n"; }
   if ($pos[0] < $pos[1]) { #not reversed
      my $s = $pos[0];
      for(my $i = 1; $i <= $#pos; $i++) {
         if ($pos[$i] == $pos[$i-1] + 1) { next; }
         if ($seqFlag eq '2bit') { 
            $seq .= fetchSeq2bit($chr, $s, $pos[$i-1]);
         }else {
            $seq .= fetchSeqNib($chr, $s, $pos[$i-1]);
         }
         $s = $pos[$i];
      }
      if (length $seq != scalar @pos) { #still need to fetch seq
         if ($seqFlag eq '2bit') {
            $seq .= fetchSeq2bit($chr, $s, $pos[$#pos]);
         }else {
            $seq .= fetchSeqNib($chr, $s, $pos[$#pos]);
         }
      }
   }else { #reversed
      my $s = $pos[$#pos];
      for(my $i = $#pos -1; $i >= 0; $i--) {
         if ($pos[$i] == $pos[$i+1] + 1) { next; }
         if ($seqFlag eq '2bit') {
            $seq .= fetchSeq2bit($chr, $s, $pos[$i+1]);
         }else {
            $seq .= fetchSeqNib($chr, $s, $pos[$i+1]);
         }
         $s = $pos[$i];
      }
      if (length $seq != scalar @pos) { #still need to fetch seq
         if ($seqFlag eq '2bit') {
            $seq .= fetchSeq2bit($chr, $s, $pos[0]);
         }else {
            $seq .= fetchSeqNib($chr, $s, $pos[0]);
         }
      }
   }
}

sub fetchSeq2bit {
   my $chr = shift;
   my $st = shift;
   my $end = shift;
   my $strand = '+';
   $st--; #change to UCSC numbering
   open (BIT, "twoBitToFa -seq=$chr -start=$st -end=$end $nibDir stdout |") or
      die "Couldn't run twoBitToFa, $!\n";
   my $seq = '';
   while (<BIT>) {
      chomp;
      if (/^>/) { next; } #header
      $seq .= uc($_);
   }
   close BIT or die "Couldn't finish twoBitToFa on $chr $st $end, $!\n";
   return $seq;
}

sub fetchSeqNib {
   my $chr = shift;
   my $st = shift;
   my $end = shift;
   my $strand = '+';
   $st--; #change to UCSC numbering
   open (NIB, "nibFrag -upper $nibDir/${chr}.nib $st $end $strand stdout |") or die "Couldn't run nibFrag, $!\n";
   my $seq = '';
   while (<NIB>) {
      chomp;
      if (/^>/) { next; } #header
      $seq .= $_;
   }
   close NIB or die "Couldn't finish nibFrag on $chr $st $end, $!\n";
   return $seq;
}

sub compl {
   my $nts = shift;
   my $comp = '';
   if (!$nts) { die "ERROR called compl with nts undefined"; }
   foreach my $n (split(/ */, $nts)) {
      if ($n eq 'A') { $comp .= 'T'; }
      elsif ($n eq 'T') { $comp .= 'A'; }
      elsif ($n eq 'C') { $comp .= 'G'; }
      elsif ($n eq 'G') { $comp .= 'C'; }
      elsif ($n eq 'N') { $comp .= 'N'; }
      elsif ($n eq '-') { $comp .= '-'; } #deletion
      else { $comp = undef; }
   }
   return $comp;
}

sub reverseCompAlleles {
   my $all = shift;
   my @nt = split(/\//, $all);
   my $rv = '';
   foreach my $n (@nt) {
      $n = reverse(split(/ */, $n)); #needed for indels
      $n = compl($n);
      $rv .= "$n/";
   }
   $rv =~ s/\/$//;
   return $rv;
}

sub getaa {
   my $nts = shift;  #in multiples of 3
   my $aa = '';
   my @n = split(/ */, $nts);
   while (@n) {
      my @t = splice(@n, 0, 3);
      my $n = uc(join("", @t));
      if (!exists $codon{$n}) { $aa .= 'N'; next; }
      $aa .= $codon{$n};
   }
   return $aa;
}

sub fill_codon {
$codon{GCA} = 'Ala';
$codon{GCC} = 'Ala';
$codon{GCG} = 'Ala';
$codon{GCT} = 'Ala';
$codon{CGG} = 'Arg';
$codon{CGT} = 'Arg';
$codon{CGC} = 'Arg';
$codon{AGA} = 'Arg';
$codon{AGG} = 'Arg';
$codon{CGA} = 'Arg';
$codon{AAC} = 'Asn';
$codon{AAT} = 'Asn';
$codon{GAC} = 'Asp';
$codon{GAT} = 'Asp';
$codon{TGC} = 'Cys';
$codon{TGT} = 'Cys';
$codon{CAG} = 'Gln';
$codon{CAA} = 'Gln';
$codon{GAA} = 'Glu';
$codon{GAG} = 'Glu';
$codon{GGG} = 'Gly';
$codon{GGA} = 'Gly';
$codon{GGC} = 'Gly';
$codon{GGT} = 'Gly';
$codon{CAC} = 'His';
$codon{CAT} = 'His';
$codon{ATA} = 'Ile';
$codon{ATT} = 'Ile';
$codon{ATC} = 'Ile';
$codon{CTA} = 'Leu';
$codon{CTC} = 'Leu';
$codon{CTG} = 'Leu';
$codon{CTT} = 'Leu';
$codon{TTG} = 'Leu';
$codon{TTA} = 'Leu';
$codon{AAA} = 'Lys';
$codon{AAG} = 'Lys';
$codon{ATG} = 'Met';
$codon{TTC} = 'Phe';
$codon{TTT} = 'Phe';
$codon{CCT} = 'Pro';
$codon{CCA} = 'Pro';
$codon{CCC} = 'Pro';
$codon{CCG} = 'Pro';
$codon{TCA} = 'Ser';
$codon{AGC} = 'Ser';
$codon{AGT} = 'Ser';
$codon{TCC} = 'Ser';
$codon{TCT} = 'Ser';
$codon{TCG} = 'Ser';
$codon{TGA} = 'Stop';
$codon{TAG} = 'Stop';
$codon{TAA} = 'Stop';
$codon{ACT} = 'Thr';
$codon{ACA} = 'Thr';
$codon{ACC} = 'Thr';
$codon{ACG} = 'Thr';
$codon{TGG} = 'Trp';
$codon{TAT} = 'Tyr';
$codon{TAC} = 'Tyr';
$codon{GTC} = 'Val';
$codon{GTA} = 'Val';
$codon{GTG} = 'Val';
$codon{GTT} = 'Val';
}

sub getGalaxyInfo {
   my $build;
   my $locFile;
   foreach (@ARGV) {
      if (/build=(.*)/) { $build = $1; }
      elsif (/loc=(.*)/) { $locFile = $1; }
   }
   if (!$build or !$locFile) {
      print STDERR "ERROR missing build or locfile for Galaxy input\n";
      exit 1;
   }
   # read $locFile to get $nibDir (ignoring commets)
   open(LF, "< $locFile") || die "open($locFile): $!\n";
   while(<LF>) {
      s/#.*$//;
      s/(?:^\s+|\s+$)//g;
      next if (/^$/);
   
      my @t = split(/\t/);
      if ($t[0] eq $build) { $nibDir = $t[1]; }
   }
   close(LF);
   if ($nibDir eq 'Galaxy') {
      print STDERR "Failed to find sequence directory in locfile $locFile\n";
   }
   $nibDir .= "/$build.2bit";  #we want full path and filename
}

