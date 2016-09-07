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

use warnings;
use strict;

sub log10($) {
	return log(shift) / log(10.0);
}

sub round {
    my($number) = shift;
    return int($number + .5 * ($number <=> 0));
}

# Convert from solexa qual to probability of miscall
sub phredToP($) {
	my $sol = shift;
	my $p = (10.0 ** (($sol) / -10.0));
	($p >= 0.0 && $p <= 1.0) || die "Bad prob: $p, from sol $sol";
	return $p;
}

# Convert from phred qual to probability of miscall
sub solToP($) {
	my $phred = shift;
	my $x = (10.0 ** (($phred) / -10.0));
	my $p = $x / (1.0 + $x);
	($p >= 0.0 && $p <= 1.0) || die "Bad prob: $p, from x $x, phred $phred";
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
	return 0 if($p == 1.0);
	return round(-10.0 * log10($p / (1.0 - $p)));
}

# Print conversion table from Phred to Solexa
print "uint8_t solToPhred[] = {";
my $cols = 10;
my $cnt = 0;
for(my $i = -10; $i < 256; $i++) {
	# Solexa qual = $i
	my $p = solToP($i);
	my $ph = pToPhred($p);
	print "\n\t/* $i */ " if($cnt == 0);
	$cnt++;
	$cnt = 0 if($cnt == 10);
	print "$ph";
	print ", " if($i < 255);
}
print "\n};\n";
