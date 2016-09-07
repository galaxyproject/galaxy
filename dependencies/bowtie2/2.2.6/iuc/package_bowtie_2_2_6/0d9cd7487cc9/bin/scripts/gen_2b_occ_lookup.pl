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
# Generate lookup table that, given two packed DNA bytes (eight bases)
# and a character (A, C, G or T), returns how many times that character
# occurs in that packed pair of bytes.  Useful for quickly counting
# character occurrences in long strings.  The LUT is indexed first by
# character (0 - 3) then by byte (0 - 2^16-1).
#
# See ebwt.h. 
#

my @as = ();
my @cs = ();
my @gs = ();
my @ts = ();

# Compile character arrays
my $i;
for($i = 0; $i < (256*256); $i++) {
	
	my $b01   = ($i >> 0) & 3;
	my $b23   = ($i >> 2) & 3;
	my $b45   = ($i >> 4) & 3;
	my $b67   = ($i >> 6) & 3;
	my $b89   = ($i >> 8) & 3;
	my $b1011 = ($i >> 10) & 3;
	my $b1213 = ($i >> 12) & 3;
	my $b1415 = ($i >> 14) & 3;

	my $a = ($b01 == 0) + ($b23 == 0) + ($b45 == 0) + ($b67 == 0) +
	        ($b89 == 0) + ($b1011 == 0) + ($b1213 == 0) + ($b1415 == 0);
	my $c = ($b01 == 1) + ($b23 == 1) + ($b45 == 1) + ($b67 == 1) +
	        ($b89 == 1) + ($b1011 == 1) + ($b1213 == 1) + ($b1415 == 1);
	my $g = ($b01 == 2) + ($b23 == 2) + ($b45 == 2) + ($b67 == 2) +
	        ($b89 == 2) + ($b1011 == 2) + ($b1213 == 2) + ($b1415 == 2);
	my $t = ($b01 == 3) + ($b23 == 3) + ($b45 == 3) + ($b67 == 3) +
	        ($b89 == 3) + ($b1011 == 3) + ($b1213 == 3) + ($b1415 == 3);

	push @as, $a;
	push @cs, $c;
	push @gs, $g;
 	push @ts, $t;
}

my $entsPerLine = 16;

# Count occurrences in all 4 bit pairs 

print "uint8_t cCntLUT_16b_4[4][256*256] = {\n";

# Print As array
print "\t/* As */ {\n";
for($i = 0; $i < (256*256); $i++) {
	print "\t\t" if(($i % $entsPerLine) == 0);
	print "$as[$i], ";
	print "\n" if(($i % $entsPerLine) == ($entsPerLine-1));
}
print "\t},\n";

# Print Cs array
print "\t/* Cs */ {\n";
for($i = 0; $i < (256*256); $i++) {
	print "\t\t" if(($i % $entsPerLine) == 0);
	print "$cs[$i], ";
	print "\n" if(($i % $entsPerLine) == ($entsPerLine-1));
}
print "\t},\n";

# Print Gs array
print "\t/* Gs */ {\n";
for($i = 0; $i < (256*256); $i++) {
	print "\t\t" if(($i % $entsPerLine) == 0);
	print "$gs[$i], ";
	print "\n" if(($i % $entsPerLine) == ($entsPerLine-1));
}
print "\t},\n";

# Print Ts array
print "\t/* Ts */ {\n";
for($i = 0; $i < (256*256); $i++) {
	print "\t\t" if(($i % $entsPerLine) == 0);
	print "$ts[$i], ";
	print "\n" if(($i % $entsPerLine) == ($entsPerLine-1));
}
print "\t}\n";
print "};\n";
