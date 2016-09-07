#!/usr/bin/perl -w

#
# Copyright 2011, Ben Langmead <langmea@cs.jhu.edu>
#
# This file is part of Bowtie 2.
#
# Bowtie 2 is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Bowtie 2 is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Bowtie 2.  If not, see <http://www.gnu.org/licenses/>.
#

#
# convert_quals.pl
#
# Modify scale/encoding of quality values in a FASTQ file.
#
# Author: Ben Langmead
#   Date: 5/5/2009
#
# p = probability that base is miscalled
# Qphred = -10 * log10 (p)
# Qsolexa = -10 * log10 (p / (1 - p))
# See: http://en.wikipedia.org/wiki/FASTQ_format
#

use strict;
use warnings;
use Getopt::Long;

my $inphred   = 33;
my $insolexa  = 0;
my $outphred  = 0;
my $outsolexa = 64;

# Default: convert 33-based Phred quals into 64-based Solexa qualss

my $result =
	GetOptions ("inphred=i"   => \$inphred,
	            "insolexa=i"  => \$insolexa,
	            "outphred=i"  => \$outphred,
	            "outsolexa=i" => \$outsolexa);
$result == 1 || die "One or more errors parsing script arguments";

if($inphred > 0) {
	$inphred >= 33 || die "Input base must be >= 33, was $inphred";
} else {
	$insolexa >= 33 || die "Input base must be >= 33, was $insolexa";
}

sub log10($) {
	return log(shift) / log(10.0);
}

sub round {
    my($number) = shift;
    return int($number + .5 * ($number <=> 0));
}

# Convert from phred qual to probability of miscall
sub phredToP($) {
	my $phred = shift;
	my $p = (10.0 ** (($phred) / -10.0));
	($p >= 0.0 && $p <= 1.0) || die "Bad prob: $p, from sol $phred";
	return $p;
}

# Convert from solexa qual to probability of miscall
sub solToP($) {
	my $sol = shift;
	my $x = (10.0 ** (($sol) / -10.0));
	my $p = $x / (1.0 + $x);
	($p >= 0.0 && $p <= 1.0) || die "Bad prob: $p, from x $x, phred $sol";
	return $p;
}

# Convert from probability of miscall to phred qual
sub pToPhred($) {
	my $p = shift;
	($p >= 0.0 && $p <= 1.0) || die "Bad prob: $p";
	return round(-10.0 * log10($p));
}

# Convert from probability of miscall to solexa qual
sub pToSol($) {
	my $p = shift;
	($p >= 0.0 && $p <= 1.0) || die "Bad prob: $p";
	return 0.0 if $p == 1.0;
	return round(-10.0 * log10($p / (1.0 - $p)));
}

while(<>) {
	my $name = $_;  print $name;
	my $seq = <>;   print $seq;
	my $name2 = <>; print $name2;
	my $quals = <>;
	chomp($quals);
	my @qual = split(//, $quals);
	for(my $i = 0; $i <= $#qual; $i++) {
		my $co = ord($qual[$i]);
		my $p;
		# Convert input qual to p
		if($inphred > 0) {
			$co -= $inphred;
			$co >= 0 || die "Bad Phred input quality: $co";
			$p = phredToP($co);
		} else {
			$co -= $insolexa;
			$p = solToP($co);
		}
		# Convert p to output qual
		if($outphred > 0) {
			$co = pToPhred($p);
			$co >= 0 || die "Bad Phred output quality: $co";
			$co += $outphred;
		} else {
			$co = pToSol($p);
			$co += $outsolexa;
		}
		$co >= 33 || die "Error: Output qual " . $co . " char is less than 33.  Try a larger output base.";
		print chr($co);
	}
	print "\n";
}
