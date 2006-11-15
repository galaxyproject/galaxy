#! /usr/bin/perl -w

# Accepts chrom, start, end, name, and strand
# If strand is void sets it to plus
# CreateInterval.pl $chrom $start $end $name $strand $output

my $strand = "+";

die "Not enough arguments\n" unless @ARGV == 6;

open OUT, ">$ARGV[5]" or die "Cannot open $ARGV[5]:$!\n";

$strand = "-" if $ARGV[4] eq "minus";
$ARGV[3] =~ s/\s+/_/g;
$ARGV[3] =~ s/\t+/_/g;

print OUT "$ARGV[0]\t$ARGV[1]\t$ARGV[2]\t$ARGV[3]\t0\t$strand\n";
close OUT;

