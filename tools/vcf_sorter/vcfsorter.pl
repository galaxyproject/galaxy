#!/usr/bin/perl
use strict;
use warnings;

######################################################
# vcfsorter.pl
#
# Copyright (C) 2011 German Gaston Leparc
#
# sorts VCF by reference genome
#
# usage:
#
# vcfsorter.pl genome.dict myvcf.file > mynewvcf.file
#
######################################################

my $usage = <<EOF;
sorts VCF by reference genome

usage:

vcfsorter.pl genome.ref myvcf > mynewvcf.file 2>STDERR
EOF


my $dict_file = $ARGV[0];
my $vcf_file = $ARGV[1];

die "\nERROR: missing an argument!\n\n$usage" if (@ARGV < 2);


#---------------------------------------- LOAD IN FASTA DICT INTO MEMORY
# Using the fasta file to access the dict file 
my $fasta_ext = ".fasta";
my $dict_ext = ".dict";
$dict_file =~ s/$fasta_ext/$dict_ext/g;

open(DICT,$dict_file) or die "Can't open $dict_file!\n";
my @contig_order;
my $c=0;
while(<DICT>)
{
if($_=~ /\@SQ/)
	{
	my ($contig) = $_ =~ /SN:(\S+)/;
	$contig_order[$c]=$contig;
	++$c; 
	#print $contig,"\n";
	}
}
close(DICT);

#---------------------------------------- PARSE VCF FILE & OUTPUT SORTED VCF

open(VCF,$vcf_file) or die "Can't open $vcf_file!\n";

my %vcf_hash;
my $header;

while(<VCF>)
{
if($_=~/^#/){ $header .= $_; next; } # store header and comment fields
chomp($_);

my @data = split(/\t/,$_);
my $contig = $data[0]; #CHROM
my $start = $data[1];  #POS
my $variant = $data[3]."to".$data[4];  #REF and ALT
my $line = $_; 

#print $contig,":",$start," ",$variant,"\n";

$vcf_hash{$contig}{$start}{$variant}=$line;

}
close(VCF);

#------------------ print out the VCF in the order of the reference genome

#print standard VCF header
print $header;


foreach my $contig (@contig_order) # sort by contig order
	{
	#print $contig,"\n";
	foreach my $start (sort {$a <=> $b} keys %{$vcf_hash{$contig}}) # sort numerically by coordinates
		{
		#print $start,"\n";
		foreach my $variant (keys %{$vcf_hash{$contig}{$start}}) # if overlapping mutation, print each variant
			{
			print $vcf_hash{$contig}{$start}{$variant},"\n";
			}	
		}
		
	}
