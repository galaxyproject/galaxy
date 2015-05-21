#!/usr/bin/env perl
use strict;

use FindBin qw($Bin);
my $path = $Bin;
#print "The home directory of this Perl script is $path.\n\n";

#my $BICseq = "$path/BIC-seq-choose-lambda/BIC-seq";
my $BICseq = "$path/BICseq/BIC-seq";
my $BIC_post = "$path/R/BIC-postprocessing.R";

if(!(-e $BICseq)){
        die("$BICseq not found.\n");
        }

if($path =~/\ / || $path =~/\t/) {print("Error: No space or tab is allowed in the path of this perl pipeline\n"); die("The current path is: $path\n");}

use Getopt::Long;

my $out_dir;
my $help;
my $lambda;
my $bin_size;
my $numTypeI="";
my $description;
my $multiplicity = 2;
my $window = 200;
my $bootstrap = 0;
my $insert = "";
my $paired = "";

my $invalid;
$invalid = GetOptions("help"=>\$help,"lambda=f"=>\$lambda, "bin_size=i"=>\$bin_size,"multiplicity=i"=>\$multiplicity,"window=i"=>\$window, "f=f"=>\$numTypeI,"B=i"=>\$bootstrap, "paired"=>\$paired, "I=s"=>\$insert);

my $size = $#ARGV+1;

if($help|!$invalid||$size!=3) {
	print "Usage: BIC-seq.pl [options] <ConfigFile> <OutputDir> <Description>\n";
	print "Options:\n";
	print "        --help\n";
	print "        --lambda=<float>: default 2.\n";
	print "        --bin_size=<int>: default 100.\n";
	print "        --multiplicity=<float>: default 2\n";
	print "        --window=<int>: the window for removing the outliers; default 200.\n";
	print "        --f=<float>: expected number of type I errors in the merging process; An alternative way to specify lambda.\n";
	print "        --B=<int>: number of permutations for FDR estimate. default 0.\n";
	print "        --paired: if specified the data is treated as paired-end data.\n";
	print "        --I=<Insert,SDofInsert>: specify the insert size and standard deviation of insert size. Default <200,20>.\n";
	die("Remove outliers, bin, run BIC-seq and postprocessing.\n");
	}

my $bicinfofile = $ARGV[0];
my $out_dir = $ARGV[1];
my $description = $ARGV[2];

if($lambda<0) {die("lambda must be positive.\n");}
if($bin_size<0) {die("Bin size must be positive.\n");}
if($bootstrap<0) {die("The value for option --B must be nonnegative\n");}
if($numTypeI<=0 && $numTypeI ne "") {die("The value for option --f must be positive\n");}

if(!$bin_size) {$bin_size = 100;}
if(!$lambda) {$lambda = 2;}

if($paired) {$paired = "-2";}
if($insert) {
	my @tmp=split(/,/,$insert);
	if($#tmp+1!=2) {die("incorrect format of option --I\n");}
	if($tmp[0]<=0||$tmp[1]<=0) {die "Insert size and its standard deviation must be positive\n";}
	$insert = "-I $insert";
	}


if(!(-e $bicinfofile)){
	die("No such file or directory: $bicinfofile\n");
	}


## test if the files exists
open(INFOIN, "<$bicinfofile");
my $i = 1;
my $num_chrom = 0;
while(<INFOIN>){
	chomp;
	my @row = split(/\t/);
	my $num_elem = $#row+1;
	if($num_elem!=3 && $num_elem!=0) {die("<ConfigFile> must be a tab-delimited three column file\n");}
	if($i>1&& $num_elem>3){
		my $chrom = $row[0];
		my $tumor_file = $row[1];
		my $normal_file = $row[2];
		if(!(-e $tumor_file)) {die("No such file $tumor_file\n");}
		if(!(-e $normal_file)) {die("No such file $normal_file\n");}
		$num_chrom = $num_chrom +1;
		}
	$i = $i+1;
	}

close(INFOIN);


if(-d $out_dir) {die("Cannot create the directory $out_dir:  the directory already exists.\n");}
else {mkdir $out_dir or die("Cannot create the directory: $out_dir\n");}

if($out_dir!~/\/$/) {$out_dir = $out_dir."/";}
#my $bin_dir = $out_dir."bin/";
my $bic_dir = $out_dir."bic/";
my $Bbic_dir = $out_dir."Permbic/";

#mkdir $bin_dir or die("Cannot create the dircectory $bin_dir\n");
mkdir $bic_dir or die("Cannot create the dircectory $bic_dir\n");
mkdir $Bbic_dir or die("Cannot create the dircectory $Bbic_dir\n");


open(INFOIN, "<$bicinfofile");
my $i = 1;
my $bic_files="";
my $chromosomes="";
while(<INFOIN>){
        chomp;
        my @row = split(/\t/);
        my $num_elem = $#row+1;
        if($num_elem!=3 && $num_elem!=0) {die("<ConfigFile> must be a tab-delimited three column file\n");}
        if($i>1 && $num_elem>0){
                my $chrom = $row[0];
                my $tumor_file = $row[1];
                my $normal_file = $row[2];
                if(!(-e $tumor_file)) {die("No such file $tumor_file\n");}
                if(!(-e $normal_file)) {die("No such file $normal_file\n");}

		#my $bin_out = $bin_dir.$chrom."\.bin";
		my $bic_out = $bic_dir.$chrom.".bic";
		

	        my $cmd = "$BICseq $paired -o $bic_out -w $window --multiplicity $multiplicity -b $bin_size -l $lambda $tumor_file $normal_file";
		if($numTypeI) { 
			my $fmerge = $numTypeI/$num_chrom;
			$cmd = "$BICseq $paired -o $bic_out -w $window --multiplicity $multiplicity -b $bin_size -f $fmerge $tumor_file $normal_file";
			}
	        print $cmd."\n";
	        if(system($cmd)!=0) {die("\n");}
	        print "\n";		

		$chromosomes = $chromosomes.$chrom.",";
		$bic_files = $bic_files.$bic_out.",";
                }
        $i = $i+1;
        }

close(INFOIN);

chop($bic_files);
chop($chromosomes);

####postprocessing

my $R_bic = $out_dir.$description.".bicseg";
my $wig_file = $out_dir.$description."\.wig";

my $cmd = "R --slave --args $bic_files $chromosomes $out_dir $description <  $BIC_post";
print $cmd."\n";
if(system($cmd)!=0){die("\n");};
print "\n";



## get the overall frequency
open(INRBIC,"<$R_bic");
my $total_tumor=0;
my $total_normal=0;

my $i = 1;
while(<INRBIC>){
	chomp;
	my @row = split(/\t/);
	if($i>1){
		$total_tumor = $total_tumor + $row[3];
		$total_normal = $total_normal + $row[4];
		}
	$i = $i+1;
	}

#die("tumor =  $total_tumor\nnormal = $total_normal\n");

my $resampled_bic = "";
if($bootstrap>0){
	my $tumor_freq = $total_tumor/($total_tumor+$total_normal);
	open(INFOIN, "<$bicinfofile");
	my $i = 1;
	
	while(<INFOIN>){
	        chomp;
	        my @row = split(/\t/);
	        my $num_elem = $#row+1;
	        if($num_elem!=3 && $num_elem!=0) {die("<ConfigFile> must be a tab-delimited three column file\n");}
	        if($i>1 && $num_elem>0){
	                my $chrom = $row[0];
	                my $tumor_file = $row[1];
	                my $normal_file = $row[2];
	                if(!(-e $tumor_file)) {die("No such file $tumor_file\n");}
	                if(!(-e $normal_file)) {die("No such file $normal_file\n");}


	                #my $bin_out = $bin_dir.$chrom."\.bin";
			my $boostrapped_bicout = $Bbic_dir.$chrom."_Perm$bootstrap\.Bbic";

			my $cmd = "$BICseq $paired $insert -B $bootstrap -p $tumor_freq -o $boostrapped_bicout -w $window --multiplicity $multiplicity -b $bin_size -l $lambda $tumor_file $normal_file";
	                if($numTypeI) {
	                        my $fmerge = $numTypeI/$num_chrom;
				$cmd = "$BICseq $paired $insert -w $window --multiplicity $multiplicity -b $bin_size -f $fmerge -B $bootstrap -p $tumor_freq -o $boostrapped_bicout $tumor_file $normal_file";
	                        }
	                print $cmd."\n";
	                if(system($cmd)!=0){die("\n");}
	                print "\n";
			$resampled_bic = $resampled_bic.$boostrapped_bicout.",";
                	}
	        $i = $i+1;
	        }
	chop($resampled_bic);
	close(INFOIN);

	my $R_bic = $out_dir.$description."\.resampled\.bicseg";
	my $cmd = "R --slave --args $resampled_bic $chromosomes $R_bic < $BIC_post";
	print "$cmd\n";
	system($cmd);
	}
