#!/usr/bin/env perl
use strict;

#convert from master variant file to snp table (Webb format?)
#new format for version 2.0, also different format for cancer normal pairs
#set columns for 2.0 version Cancer format
my $aCnt1 = 21;
my $aCnt2 = 22;

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
   print "usage: master2gd_snp.pl masterVar.txt[.gz|.bz2] [-tab=snpTable.txt -addColsOnly -build=hg19 -name=na ] > newSnpTable.txt\n";
   exit;
}

my $in = shift @ARGV;
my $tab;
my $tabOnly;
my $build;
my $name;
foreach (@ARGV) {
   if (/-tab=(.*)/) { $tab = $1; }
   elsif (/-addColsOnly/) { $tabOnly = 1; }
   elsif (/-build=(.*)/) { $build = $1; }
   elsif (/-name=(.*)/) { $name = $1; }
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
   #FORMAT_VERSION 2.0
   if (/^#FORMAT_VERSION\s+1\./) { 
      $aCnt1 = 16;
      $aCnt2 = 17;
   }
   if (/^#/) { next; }
   if (/^>/) { next; } #headers
   if (/^\s*$/) { next; } 
   my @f = split(/\t/);
   if (!$f[6]) { next; } #WHAT? most likely still zipped?
   if ($f[6] ne 'snp') { next; } #table only has substitutions
   if ($f[5] eq 'het-alt') { next; } #skip heterozygous with no ref match
   if ($f[5] =~ /(hom|het)/) { #zygosity #haploid chrX and chrY?
         my $a = $f[7];  #reference allele
         my $a2;
         my $freq;
         my $freq2;
         my $sc;
         my $alt;
         my $g = 1; #genotype == ref allele count
         if ($f[8] eq $f[9]) { #should be homozygous?
            $a2 = $f[8];
            $g = 0;
            $sc = $f[10]; #is this the best one to use? or smallest?
         }else {
            if ($a ne $f[8]) { $a2 = $f[8]; $alt = 8; }
            elsif ($a ne $f[9]) { $a2 = $f[9]; $alt = 9; }
         }
         if (defined $f[10] && defined $f[11] && $alt) { #VAF score in 2.0 format
            $sc = $f[$alt+2];
         }
	 #version 1.12 columns 16 & 17, version 2.0 Cancer columns 21 & 22
         if (defined $f[$aCnt1] && defined $f[$aCnt2] && $alt) {
            if ($alt == 8) { 
                $freq = $f[$aCnt2];
                $freq2 = $f[$aCnt1];
            }elsif ($alt == 9) {
                $freq = $f[$aCnt1];
                $freq2 = $f[$aCnt2];
            }
         }elsif (defined $f[$aCnt1]) {
            $freq = 0;
            $freq2 = $f[$aCnt1];
         }
         #if starting a new table or new SNP in old table
         #add option to only build on current table?
	 if (!$tab) { 
            print "$f[2]\t$f[3]\t$a\t$a2\t-1"; 
         }elsif (!$tabOnly && !exists $old{"$f[2]:$f[3]"}) {
            print "$f[2]\t$f[3]\t$a\t$a2\t-1";
         }elsif (exists $old{"$f[2]:$f[3]"}) {
            print $old{"$f[2]:$f[3]"};
            $old{"$f[2]:$f[3]"} = ''; #unset so we know it is printed
         }elsif ($tabOnly && !exists $old{"$f[2]:$f[3]"}) {
            next; #skip this one entirely
         }
         if ($colcnt && !exists $old{"$f[2]:$f[3]"}) { 
            #new SNP pad for missing individuals
            my $i = 5;
            while ($i < $colcnt) {
               print "\t-1\t-1\t-1\t-1";
               $i += 4;
            }
         }
         #add columns for individual
         print "\t$freq\t$freq2\t$g\t$sc\n";
   }elsif ($f[5] eq 'hap') {
      my $g = 0;
      my $freq = 0;
      my $freq2 = 0; 
      if (defined $f[10]) { $freq2 = $f[10]; }
      my $sc = -1;
      if (defined $f[$aCnt1]) { $sc = $f[$aCnt1]; }
      if ($f[8]) {
         if (!$tab) {
            print "$f[2]\t$f[3]\t$f[7]\t$f[8]\t-1";
         }elsif (!$tabOnly && !exists $old{"$f[2]:$f[3]"}) {
            print "$f[2]\t$f[3]\t$f[7]\t$f[8]\t-1";
         }elsif (exists $old{"$f[2]:$f[3]"}) {
            print $old{"$f[2]:$f[3]"};
            $old{"$f[2]:$f[3]"} = ''; #unset so we know it is printed
         }elsif ($tabOnly && !exists $old{"$f[2]:$f[3]"}) {
            next; #skip this one entirely
         }
         if ($colcnt && !exists $old{"$f[2]:$f[3]"}) {
            #new SNP pad for missing individuals
            my $i = 5;
            while ($i < $colcnt) {
               print "\t-1\t-1\t-1\t-1";
               $i += 4;
            }
         }
         #add columns for individual
         print "\t$freq\t$freq2\t$g\t$sc\n";
      }   
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

##example header 
#{"column_names":["chr","pos","A","B","Q","1A","1B","1G","1Q","2A","2B","2G","2Q","3A","3B","3G","3Q","4A","4B","4G","4Q","5A","5B","5G","5Q","6A","6B","6G","6Q","7A","7B","7G","7Q","8A","8B","8G",
#"8Q","9A","9B","9G","9Q","10A","10B","10G","10Q"],"dbkey":"hg19","individuals":[["Boh_15M",6],["Boh_19M",10],["Paya_27F",14],["Paya_2F",18],["Paya_32F",22],["Ruil_2M",26],["Ruil_36M",30],["Ruil_3M",
#34],["Ruil_40",38],["Ruil_47F",42]],"pos":2,"rPos":2,"ref":1,"scaffold":1,"species":"hg19"}
#chr1	10290	C	T	46.4	0	2	0	7	1	2	0	4	3	2	1	22	0	0	-1	0	1	0	1	4	0	2	0	7	0	0	-1	0	2	3	1	14	0	1	0	4	1	1	1	6
