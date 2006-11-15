#! /usr/bin/perl -w

use strict;
use warnings;
use Carp;

# Converts tab delimited file into BedLike format
# Text2BedLike [chrom col] [start col] [end col] [strand col] [inupt file] [output file]

my @fields = ();

die "Not enough arguments" unless @ARGV == 6;
    
open (IN,  "<$ARGV[4]") or die "Cannot open $ARGV[4]:$!";
open (OUT, ">$ARGV[5]") or die "Cannot create $ARGV[5]:$!";
while (<IN>) {
    die "This tool can only be used on a tab delimited file. If you think your file is delimited with space, comma, or some other non TAB character -> use Convert Characters tool (Edit Text Queries->Convert Characters) to change it to TAB\n" if !m/\t/;
    if (!m/^\#/) {
	s/\|/:/g;
	chop;
	@fields = split /\t/;

	for my $line ( 0 .. @fields-1 ) {
	    $fields[$line] =~ s/^\s+//g;
            $fields[$line] =~ s/\s+$//g;
	}

        $fields[$ARGV[0]-1] =~ s/^/chr/ if $fields[$ARGV[0]-1] !~ m/^chr/;
	print OUT "$fields[$ARGV[0]-1]\t$fields[$ARGV[1]-1]\t$fields[$ARGV[2]-1]\tBedLike|" . join("|", @fields) . "\t0";
	if ($ARGV[3] == 100) {
	    print OUT "\n";
	} else {
	    print OUT "\t$fields[$ARGV[3]-1]\n";
	}
    }
}

close IN;
close OUT;
