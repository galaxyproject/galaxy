#! /usr/bin/perl -w

use strict;
use POSIX;


die "Usage: pileup_parser.pl <in_file> <ref_base_column> <read_bases_column> <base_quality_column> <coverage column> <qv cutoff> <coverage cutoff> <SNPs only?> <output bed?> <coord_column> <out_file> <total_diff> <print_qual_bases>\n" unless @ARGV == 13;

my $in_file = $ARGV[0];
my $ref_base_column = $ARGV[1]-1; # 1 based
my $read_bases_column = $ARGV[2]-1; # 1 based
my $base_quality_column = $ARGV[3]-1; # 1 based
my $cvrg_column = $ARGV[4]-1; # 1 based
my $quality_cutoff = $ARGV[5]; # phred scale integer
my $cvrg_cutoff = $ARGV[6]; # unsigned integer
my $SNPs_only = $ARGV[7]; # set to "Yes" to print only positions with SNPs; set to "No" to pring everything
my $bed = $ARGV[8]; #set to "Yes" to convert coordinates to bed format (0-based start, 1-based end); set to "No" to leave as is
my $coord_column = $ARGV[9]-1; #1 based 
my $out_file = $ARGV[10];
my $total_diff = $ARGV[11]; # set to "Yes" to print total number of deviant based
my $print_qual_bases = $ARGV[12]; #set to "Yes" to print quality and read base columns

my $invalid_line_counter = 0;
my $first_skipped_line = "";
my %SNPs = ('A',0,'T',0,'C',0,'G',0);
my $above_qv_bases = 0;
my $SNPs_exist = 0;
my $out_string = "";
my $diff_count = 0;

open (IN, "<$in_file") or die "Cannot open $in_file $!\n";
open (OUT, ">$out_file") or die "Cannot open $out_file $!\n";

while (<IN>) {
	chop;
	next if m/^\#/;
	my @fields = split /\t/;
	next if $fields[ $ref_base_column ] eq "*"; # skip indel lines
 	my $read_bases   = $fields[ $read_bases_column ];
 	die "Coverage column" . ($cvrg_column+1) . " contains non-numeric values. Check your input parameters as well as format of input dataset." if ( not isdigit $fields[ $cvrg_column ] );
    next if $fields[ $cvrg_column ] < $cvrg_cutoff;
	my $base_quality = $fields[ $base_quality_column ];
	if ($read_bases =~ m/[\$\^\+-]/) {
		$read_bases =~ s/\^.//g; #removing the start of the read segement mark
		$read_bases =~ s/\$//g; #removing end of the read segment mark
		while ($read_bases =~ m/[\+-]{1}(\d+)/g) {
			my $indel_len = $1;
			$read_bases =~ s/[\+-]{1}$indel_len.{$indel_len}//; # remove indel info from read base field
		}
	}
	if ( length($read_bases) != length($base_quality) ) {
        $first_skipped_line = $. if $first_skipped_line eq "";
        ++$invalid_line_counter;
        next;
	}
	# after removing read block and indel data the length of read_base 
	# field should identical to the length of base_quality field
	
	my @bases = split //, $read_bases;
	my @qv    = split //, $base_quality;
	
	for my $base ( 0 .. @bases - 1 ) {
		if ( ord( $qv[ $base ] ) - 33 >= $quality_cutoff and $bases[ $base ] ne '*')
		{
			++$above_qv_bases;
			
			if ( $bases[ $base ] =~ m/[ATGC]/i )
			{
				$SNPs_exist = 1;	
				$SNPs{ uc( $bases[ $base ] ) } += 1;
				$diff_count += 1;
			} elsif ( $bases[ $base ] =~ m/[\.,]/ ) {
			    $SNPs{ uc( $fields[ $ref_base_column ] ) } += 1;
		    }		 	
		}
	} 
	
	if ($bed eq "Yes") {
	       my $start = $fields[ $coord_column ] - 1;
	       my $end   = $fields[ $coord_column ];
	       $fields[ $coord_column ] = "$start\t$end";
	} 
	
	if ($print_qual_bases ne "Yes") {
	       $fields[ $base_quality_column ] = "";
	       $fields[ $read_bases_column ] = "";
	}
	       
	
	$out_string = join("\t", @fields); # \t$read_bases\t$base_quality";
	foreach my $SNP (sort keys %SNPs) {
			$out_string .= "\t$SNPs{$SNP}";
	}
	
	if ($total_diff eq "Yes") {
	   $out_string .= "\t$above_qv_bases\t$diff_count\n";
	} else {
	   $out_string .= "\t$above_qv_bases\n";
	}	
	
	$out_string =~ s/\t+/\t/g;
	
	if ( $SNPs_only eq "Yes" ) {
		print OUT $out_string if $SNPs_exist == 1;
	} else {
		print OUT $out_string;
	}

		
	%SNPs = ();
	%SNPs = ('A',0,'T',0,'C',0,'G',0);
	$above_qv_bases = 0;
	$SNPs_exist = 0;
	$diff_count = 0;
	

}

print "Skipped $invalid_line_counter invalid line(s) beginning with line $first_skipped_line\n" if $invalid_line_counter > 0;
close IN;
close OUT;
