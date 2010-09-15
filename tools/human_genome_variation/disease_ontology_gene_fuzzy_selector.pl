#!/usr/bin/env perl

use strict;
use warnings;

##################################################################
# Select genes that are associated with the diseases listed in the
# disease ontology.
# ontology: http://do-wiki.nubic.northwestern.edu/index.php/Main_Page
# gene associations by FunDO: http://projects.bioinformatics.northwestern.edu/do_rif/
# Sept 2010, switch to doLite
# input: build outfile sourceFileLoc.loc term or partial term
##################################################################

if (!@ARGV or @ARGV < 3) { 
   print "usage: disease_ontology_gene_selector.pl build outfile.txt sourceFile.loc [list of terms]\n";
   exit;
}

my $build = shift @ARGV;
my $out = shift @ARGV;
my $in = shift @ARGV;
my $term = shift @ARGV;
$term =~ s/^'//; #remove quotes protecting from shell
$term =~ s/'$//; 
my $data;
open(LOC, $in) or die  "Couldn't open $in, $!\n";
while (<LOC>) {
   chomp;
   if (/^\s*#/) { next; }
   my @f = split(/\t/);
   if ($f[0] eq $build) { 
      if ($f[1] eq 'disease associated genes') { 
         $data = $f[2]; 
      }
   }
}
close LOC or die "Couldn't close $in, $!\n";
if (!$data) { 
   print "Error $build not found in $in\n";
   exit; 
}
if (!defined $term) { 
   print "No disease term entered\n";
   exit;
}

#start with just fuzzy term matches
open(OUT, ">", $out) or die "Couldn't open $out, $!\n";
open(FH, $data) or die "Couldn't open data file $data, $!\n";
$term =~ s/\s+/|/g; #use OR between words
while (<FH>) {
   chomp;
   my @f = split(/\t/); #chrom start end strand geneName geneID disease
   if ($f[6] =~ /($term)/i) { 
      print OUT join("\t", @f), "\n";
   }elsif ($term eq 'disease') { #print all with disease
      print OUT join("\t", @f), "\n";
   }
}
close FH or die "Couldn't close data file $data, $!\n";
close OUT or die "Couldn't close $out, $!\n";

exit;
