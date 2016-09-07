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

##
# infer_fraglen.pl
#
# Infer fragment length by looking for unique alignments for mates 
# (separately), then piecing those together and building a distribution.
#

use strict;
use warnings;
use Getopt::Long;
use FindBin qw($Bin); 

my $m1 = "";
my $m2 = "";
my $index = "";
my $bowtie_args = "";
my $bowtie2 = "$Bin/../bowtie2";
my $debug = 0;
my $binsz = 10;
my $mapq_cutoff = 30;
my $upto = undef;

sub dieusage {
	my $msg = shift;
	my $exitlevel = shift;
	$exitlevel = $exitlevel || 1;
	print STDERR "$msg\n";
	exit $exitlevel;
}

##
# Given a basename, return true iff all index files exist.
#
sub checkIndex($) {
	my $idx = shift;
	my $ext = "bt2";
	return -f "$idx.1.$ext" &&
	       -f "$idx.2.$ext" &&
	       -f "$idx.3.$ext" &&
	       -f "$idx.4.$ext" &&
	       -f "$idx.rev.1.$ext" &&
	       -f "$idx.rev.2.$ext";
}

GetOptions (
	"bowtie2=s"     => \$bowtie2,
	"index=s"       => \$index,
	"m1=s"          => \$m1,
	"m2=s"          => \$m2,
	"upto=i"        => \$upto,
	"mapq_cutoff=i" => \$mapq_cutoff,
	"debug"         => \$debug,
	"bowtie-args=s" => \$bowtie_args) || dieusage("Bad option", 1);

die "Must specify --m1" if $m1 eq "";
die "Must specify --m2" if $m2 eq "";
die "Must specify --index" if $index eq "";
$m1 =~ s/^~/$ENV{HOME}/;
$m2 =~ s/^~/$ENV{HOME}/;
$index =~ s/^~/$ENV{HOME}/;
die "Bad bowtie path: $bowtie2" if system("$bowtie2 --version >/dev/null 2>/dev/null") != 0;
die "Bad index: $index" if !checkIndex($index);

# Hash holding all the observed fragment orientations and lengths
my %fragments = ();
my $m1cmd = ($m1 =~ /\.gz$/) ? "gzip -dc $m1" : "cat $m1";
my $m2cmd = ($m2 =~ /\.gz$/) ? "gzip -dc $m2" : "cat $m2";
my $cmd1 = "$m1cmd | $bowtie2 $bowtie_args --sam-nohead -x $index - > .infer_fraglen.tmp";
my $cmd2 = "$m2cmd | $bowtie2 $bowtie_args --sam-nohead -x $index - |";
my $tot = 0;
system($cmd1) == 0 || die "Error running '$cmd1'";
open (M1, ".infer_fraglen.tmp") || die "Could not open '.infer_fraglen.tmp'";
open (M2, $cmd2) || die "Could not open '$cmd2'";
while(<M1>) {
	my $lm1 = $_;
	my $lm2 = <M2>;
	chomp($lm1); chomp($lm2);
	my @lms1 = split(/\t/, $lm1);
	my @lms2 = split(/\t/, $lm2);
	my ($name1, $flags1, $chr1, $off1, $mapq1, $slen1) = ($lms1[0], $lms1[1], $lms1[2], $lms1[3], $lms1[4], length($lms1[9]));
	my ($name2, $flags2, $chr2, $off2, $mapq2, $slen2) = ($lms2[0], $lms2[1], $lms2[2], $lms2[3], $lms2[4], length($lms2[9]));
	# One or both mates didn't align uniquely?
	next if $chr1 eq "*" || $chr2 eq "*";
	# Mates aligned to different chromosomes?
	next if $chr1 ne $chr2;
	# MAPQs too low?
	next if $mapq1 < $mapq_cutoff || $mapq2 < $mapq_cutoff;
	# This pairing can be used as an observation of fragment orientation and length
	my $fw1 = (($flags1 & 16) == 0) ? "F" : "R";
	my $fw2 = (($flags2 & 16) == 0) ? "F" : "R";
	my $frag = $off2 - $off1;
	# This can overestimate if one mate is entirely subsumed in the other
	if($frag > 0) { $frag += $slen2; }
	else          { $frag -= $slen1; }
	# Install into bin
	$frag = int(($frag + ($binsz/2))/$binsz); # Round to nearest bin
	$fragments{"$fw1$fw2"}{$frag}++;
	$tot++;
}
close(M1);
close(M2);
unlink(".infer_fraglen.tmp"); # ditch temporary file

# Print out the bins
for my $k (keys %fragments) {
	for my $k2 (sort {$a <=> $b} keys %{$fragments{$k}}) {
		print "$k, ".($k2*$binsz).", ".$fragments{$k}{$k2}."\n";
	}
}

print STDERR "DONE\n";
