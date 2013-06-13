#!/usr/bin/perl -w
use strict;

#convert from pgSnp file to snp table (Webb format?)

#snp table format:
#1. chr
#2. position (0 based)
#3. ref allele
#4. second allele
#5. overall quality
#foreach individual (6-9, 10-13, ...)
#a. count of allele in 3
#b. count of allele in 4
#c. genotype call (-1, or count of ref allele)
#d. quality of genotype call (quality of non-ref allele from masterVar)

if (!@ARGV) {
   print "usage: pgSnp2gd_snp.pl file.pgSnp[.gz|.bz2] [-tab=snpTable.txt -addColsOnly -build=hg19 -name=na -ref=#1based -chr=#1based ] > newSnpTable.txt\n";
   exit;
}

my $in = shift @ARGV;
my $tab;
my $tabOnly;
my $build;
my $name;
my $ref;
my $binChr = 1; #position of chrom column, indicates if bin is added
foreach (@ARGV) {
   if (/-tab=(.*)/) { $tab = $1; }
   elsif (/-addColsOnly/) { $tabOnly = 1; }
   elsif (/-build=(.*)/) { $build = $1; }
   elsif (/-name=(.*)/) { $name = $1; }
   elsif (/-ref=(\d+)/) { $ref = $1 - 1; } #go to index
   elsif (/-chr=(\d+)/) { $binChr = $1; }
}

if ($binChr == 2 && $ref) { $ref--; } #shift over by 1, we will delete bin
if ((!$tab or !$tabOnly) && !$ref) {
   print "Error the reference allele must be in a column in the file if not just adding to a previous SNP table.\n";
   exit;
}
   
#WARNING loads snp table in memory, this could take > 1G ram
my %old;
my $colcnt = 0;
my @head;
if ($tab) {
   open(FH, $tab) or die "Couldn't open $tab, $!\n";
   while (<FH>) {
      chomp;
      if (/^#/) { push(@head, $_); next; }
      my @f = split(/\t/);
      $old{"$f[0]:$f[1]"} = join("\t", @f);
      $colcnt = scalar @f;
   }
   close FH or die "Couldn't close $tab, $!\n";
}

if ($in =~ /.gz$/) { 
   open(FH, "zcat $in |") or die "Couldn't open $in, $!\n";
}elsif ($in =~ /.bz2$/) {
   open(FH, "bzcat $in |") or die "Couldn't open $in, $!\n";
}else {
   open(FH, $in) or die "Couldn't open $in, $!\n";
}
prepHeader();
if (@head) { #keep old header, add new?
   print join("\n", @head), "\n";
}
while (<FH>) {
   chomp;
   if (/^#/) { next; }
   if (/^\s*$/) { next; } 
   my @f = split(/\t/);
   if ($binChr == 2) { #must have a bin column prepended on the beginning
     shift @f; #delete it
   }
   if (!$f[3]) { next; } #WHAT? most likely still zipped?
   if ($f[4] > 2) { next; } #can only do cases of 2 alleles
   if ($f[2] == $f[1] or $f[2] - $f[1] != 1) { next; } #no indels
   if ($f[3] =~ /-/) { next; } #no indels
   #if creating a new table need the reference allele in a column
   if (%old && $old{"$f[0]:$f[1]"}) {
      my @o = split(/\t/, $old{"$f[0]:$f[1]"});
      my $freq = 0;
      my $freq2 = 0;
      my $sc;
      my $g = 1; #genotype == ref allele count
      if ($f[4] == 1) { #should be homozygous
         if ($f[3] eq $o[2]) { $g = 2; $freq = $f[5]; }
         elsif ($f[3] eq $o[3]) { $g = 0; $freq2 = $f[5]; }
         else { next; } #doesn't match either allele, skip
         $sc = $f[6];
      }else {
         my $a = 0;  #index of a alleles, freq, scores
         my $b = 1;  #same for b
         my @all = split(/\//, $f[3]);
         if ($o[2] ne $all[0] && $o[2] ne $all[1]) { next; } #must match one
         if ($o[3] ne $all[0] && $o[3] ne $all[1]) { next; }
         if ($o[2] eq $all[1]) { #switch indexes
            $a = 1;
            $b = 0;
         }
         my @fr = split(/,/, $f[5]);
         $freq = $fr[$a];
         $freq2 = $fr[$b];
         my @s = split(/,/, $f[6]);
         $sc = $s[$b];
      }
      #print old
      print $old{"$f[0]:$f[1]"};
      #add new columns
      print "\t$freq\t$freq2\t$g\t$sc\n";
      $old{"$f[0]:$f[1]"} = '';
   }elsif (!$tabOnly) { #new table, or don't have this SNP
      #need reference allele
      if ($f[3] !~ /$f[$ref]/ && $f[4] == 2) { next; } #no reference allele
      my $freq = 0;
      my $freq2 = 0;
      my $sc;
      my $g = 1; #genotype == ref allele count
      my $alt; 
      if ($f[4] == 1) { #should be homozygous
         if ($f[3] eq $f[$ref]) { $g = 2; $freq = $f[5]; $alt = 'N'; }
         else { $g = 0; $freq2 = $f[5]; $alt = $f[3]; } #matches alternate
         $sc = $f[6];
      }else {
         my $a = 0;  #index of a alleles, freq, scores
         my $b = 1;  #same for b
         my @all = split(/\//, $f[3]);
         if ($f[$ref] ne $all[0] && $f[$ref] ne $all[1]) { next; } #must match one
         if ($f[$ref] eq $all[1]) { #switch indexes
            $a = 1;
            $b = 0;
         }
         my @fr = split(/,/, $f[5]);
         $freq = $fr[$a];
         $freq2 = $fr[$b];
         my @s = split(/,/, $f[6]);
         $sc = $s[$b];
         $alt = $all[$b];
      }
      #print initial columns
      print "$f[0]\t$f[1]\t$f[$ref]\t$alt\t-1";
      #pad for other individuals if needed
      my $i = 5;
      while ($i < $colcnt) {
         print "\t-1\t-1\t-1\t-1";
         $i += 4;
      }
      #add new columns
      print "\t$freq\t$freq2\t$g\t$sc\n";
   }
}
close FH or die "Couldn't close $in, $!\n";

#if adding to a snp table, now we need to finish those not in the latest set
foreach my $k (keys %old) {
   if ($old{$k} ne '') { #not printed yet
      print $old{$k}, "\t-1\t-1\t-1\t-1\n"; #plus blank for this one
   }
}

exit;

#parse old header and add or create new
sub prepHeader {
   if (!$build) { $build = 'hg19'; } #set default
   my @cnames;
   my @ind;
   my $n;
   if (@head) { #parse previous header
      my $h = join("", @head); #may split between lines
      if ($h =~ /"column_names":\[(.*?)\]/) {
         my @t = split(/,/, $1);
         foreach (@t) { s/"//g; }
         @cnames = @t;
         $n = $cnames[$#cnames];
         $n =~ s/Q//;
         $n++;
      }
      if ($h =~ /"dbkey":"(.*?)"/) { $build = $1; }
      if ($h =~ /"individuals":\[(.*)\]/) {
         my $t = $1;
         $t =~ s/\]\].*/]/; #remove if there is more categories
         @ind = split(/,/, $t);
      } 
   }else { #start new header
      @cnames = ("chr", "pos", "A", "B", "Q");   
      $n = 1;
   }
   #add current
   if (!$name) { $name= 'na'; }
   my $stcol = $colcnt + 1;
   if ($stcol == 1) { $stcol = 6; } #move past initial columns
   push(@ind, "[\"$name\",$stcol]");
   push(@cnames, "${n}A", "${n}B", "${n}G", "${n}Q");
   #reassign head
   undef @head;
   foreach (@cnames) { $_ = "\"$_\""; } #quote name
   $head[0] = "#{\"column_names\":[" . join(",", @cnames) . "],";
   $head[1] = "#\"individuals\":[" . join(",", @ind) . "],"; 
   $head[2] = "#\"dbkey\":\"$build\",\"pos\":2,\"rPos\":2,\"ref\":1,\"scaffold\":1,\"species\":\"$build\"}";
}
####End

