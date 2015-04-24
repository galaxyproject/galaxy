#!/usr/bin/perl  

my $usage = <<EOF; 

 makebicseqconfig.pl  

 Suzi Fei 
 4/22/14

 makes a config file for BIC-seq  

 usage:

 perl makebicseqconfig.pl <name of tumor bam> <name of normal bam> 
 perl makebicseqconfig.pl UT11-0749_LP6007477_realigned.bam UT11-0749_LP6007455_realigned.bam
 
EOF

use File::Basename;
use File::Spec;

die "\nERROR: missing arguments\n\n$usage" if (@ARGV < 4); 
$tumorbamname = @ARGV[0];
$normalbamname = @ARGV[1];
$tumorfile = @ARGV[2];
$normalfile = @ARGV[3];

if ($tumorbamname =~ /(.*).bam/) { $tumorname = basename$1.".bam"; $dirname = dirname$1;}
else { die "Ill-formatted tumor bam name $tumorbamname"; } 

print $dirname;
if ($normalbamname =~ /(.*).bam/) { $normalname = basename$1.".bam";}
else { die "Ill-formatted normal bam name $normalbamname"; } 

#$1_vs_$2_config.txt
$out = $tumorname . "_vs_" . $normalname . "_config.txt"; 
open(OUT, "> $out" ) or die "Can't open $out : $!";
select OUT; $| = 1; select STDOUT;

print OUT "chrom\tcase\tcontrol\n";

#use samtools view -H $tumorbamname to see how your chromosomes are named then choose accordingly
#@chrs = qw(1 10 11 12 13 14 15 16 17 18 19 2 20 21 22 3 4 5 6 7 8 9 GL000191.1 GL000192.1 GL000193.1 GL000194.1 GL000195.1 GL000196.1 GL000197.1 GL000198.1 GL000199.1 GL000200.1 GL000201.1 GL000202.1 GL000203.1 GL000204.1 GL000205.1 GL000206.1 GL000207.1 GL000208.1 GL000209.1 GL000210.1 GL000211.1 GL000212.1 GL000213.1 GL000214.1 GL000215.1 GL000216.1 GL000217.1 GL000218.1 GL000219.1 GL000220.1 GL000221.1 GL000222.1 GL000223.1 GL000224.1 GL000225.1 GL000226.1 GL000227.1 GL000228.1 GL000229.1 GL000230.1 GL000231.1 GL000232.1 GL000233.1 GL000234.1 GL000235.1 GL000236.1 GL000237.1 GL000238.1 GL000239.1 GL000240.1 GL000241.1 GL000242.1 GL000243.1 GL000244.1 GL000245.1 GL000246.1 GL000247.1 GL000248.1 GL000249.1 MT X Y);
#@chrs = qw(1 10 11 12 13 14 15 16 17 18 19 2 20 21 22 3 4 5 6 7 8 9 MT X Y);
#@chrs = qw(1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 X Y MT);
#@chrs = qw(chr1 chr2 chr3 chr4 chr5 chr6 chr7 chr8 chr9 chr10 chr11 chr12 chr13 chr14 chr15 chr16 chr17 chr18 chr19 chr20 chr21 chr22 chrX chrY chrM);

@chrs = ();
$command = "samtools view -H $tumorbamname";
$header = `$command`;
@header = split(/\n/, $header);
foreach $line (@header) {
	if ($line =~ /@SQ\tSN:([^\t]*)\tLN/) { 	
		unless ($1 =~ /^GL0/) { push(@chrs, $1); }
	}
}

#sample line looks like this:
#1	mappings/UT02-0086_LP6007471_realigned.bam/1.seq	mappings/UT02-0086_LP6007454_realigned.bam/1.seq
foreach $chr (@chrs) {
	#print OUT "$chr\tmappings/$tumorbamname/$chr.seq\tmappings/$normalbamname/$chr.seq\n";
	#print OUT "$chr\t$dirname/mappings/tumor_sorted.bam/$chr.seq\t$dirname/mappings/normal_sorted.bam/$chr.seq\n";
	print OUT "$chr\t$tumorfile\t$normalfile\n";
}

close(OUT); 

