#!/usr/bin/env perl

##
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
# The paired-end data is made by (a) changing to the reads subdirectory and (b)
# running 'perl simulate.pl --ref=../reference/lambda_virus.fa'.
#

#
# The long-read data is made by (a) changing to the reads subdirectory and (b)
# running 'perl simulate.pl --ref=../reference/lambda_virus.fa --long
# --unpaired --prefix=longreads'.
#

use strict;
use warnings;
use Carp;
use Math::Random qw(random_normal random_exponential);
use Getopt::Long;
use List::Util qw(max min);

my @fa_fn = ();        # files with reference FASTA
my $rf = "";           # reference sequence
my $long = 0;          # 1 -> generate long reads
my $paired = 1;        # 1 -> generate paired-end reads
my $prefix = "reads";  # output files start with this string
my $nreads    = undef; # # reads
my $rdlen_av  = undef; # average to use when drawing from exponential
my $rdlen_exact = undef; # exact length for all reads, overrides randomness
my $rdlen_min = undef; # minimum read length (added to exponential draw)
my $frag_av   = undef; # mean fragment len
my $frag_sd   = undef; # s.d. to use when drawing frag len from normal dist
my $verbose   = 0;     # be talkative

GetOptions (
	"fasta|reference=s" => \@fa_fn,
	"long"              => \$long,
	"verbose"           => \$verbose,
	"nreads=i"          => \$nreads,
	"read-avg=i"        => \$rdlen_av,
	"read-len=i"        => \$rdlen_exact,
	"read-min=i"        => \$rdlen_min,
	"frag-avg=i"        => \$frag_av,
	"frag-sd=i"         => \$frag_sd,
	"unpaired"          => sub { $paired = 0; },
	"prefix=s"          => \$prefix
) || die "Bad option";

scalar(@fa_fn) > 0 || die "Must specify at least one reference FASTA file with --fasta";

print STDERR "Loading reference files...\n";
for my $fn (@fa_fn) {
	open(FN, $fn) || confess;
	my $name = "";
	while(<FN>) {
		chomp;
		$rf .= $_ if substr($_, 0, 1) ne ">";
	}
	close(FN);
}

my %revcompMap = (
	"A" => "T", "T" => "A", "a" => "t", "t" => "a",
	"C" => "G", "G" => "C", "c" => "g", "g" => "c",
	"R" => "Y", "Y" => "R", "r" => "y", "y" => "r",
	"M" => "K", "K" => "M", "m" => "k", "k" => "m",
	"S" => "S", "W" => "W", "s" => "s", "w" => "w",
	"B" => "V", "V" => "B", "b" => "v", "v" => "b",
	"H" => "D", "D" => "H", "h" => "d", "d" => "h",
	"N" => "N", "." => ".", "n" => "n" );

sub comp($) {
	my $ret = $revcompMap{$_[0]} || confess "Can't reverse-complement '$_[0]'";
	return $ret;
}

sub revcomp {
	my ($ret) = @_;
	$ret = reverse $ret;
	for(0..length($ret)-1) { substr($ret, $_, 1) = comp(substr($ret, $_, 1)); }
	return $ret;
}

$nreads    = $nreads    || 10000; # number of reads/end to generate
$rdlen_av  = $rdlen_av  || 75;    # average when drawing from exponential
$rdlen_min = $rdlen_min || 40;    # min read length (added to exponential draw)
$frag_av   = $frag_av   || 250;   # mean fragment len
$frag_sd   = $frag_sd   || 45;    # s.d. when drawing frag len from normal dist
my @fraglens  = ();     # fragment lengths (for paired)
my @readlens  = ();     # read/end lengths

if($long) {
	$nreads = 6000;
	$rdlen_av = 300;
	$rdlen_min = 40;
}

sub rand_dna($) {
	my $ret = "";
	for(1..$_[0]) { $ret .= substr("ACGT", int(rand(4)), 1); }
	return $ret;
}

#
# Mutate the reference
#

print STDERR "Adding single-base substitutions...\n";
my $nsnp = 0;
for(0..length($rf)-1) {
	if(rand() < 0.0012) {
		my $oldc = substr($rf, $_, 1);
		substr($rf, $_, 1) = substr("ACGT", int(rand(4)), 1);
		$nsnp++ if substr($rf, $_, 1) ne $oldc;
	}
}

print STDERR "Adding microindels...\n";
my $microgap = 0;
{
	my $newrf = "";
	my $nins = int(length($rf) * 0.0005 + 0.5);
	my $ndel = int(length($rf) * 0.0005 + 0.5);
	$microgap = $nins + $ndel;
	my %indel = ();
	for(1..$nins) {
		my $off = int(rand(length($rf)));
		$indel{$off}{ty} = "ins";
		$indel{$off}{len} = int(random_exponential(1, 3))+1;
	}
	for(1..$ndel) {
		my $off = int(rand(length($rf)));
		$indel{$off}{ty} = "del";
		$indel{$off}{len} = int(random_exponential(1, 3))+1;
	}
	my $lasti = 0;
	for my $rfi (sort {$a <=> $b} keys %indel) {
		if($rfi > $lasti) {
			$newrf .= substr($rf, $lasti, $rfi - $lasti);
			$lasti = $rfi;
		}
		if($indel{$rfi}{ty} eq "ins") {
			$newrf .= rand_dna($indel{$rfi}{len});
		} else {
			$lasti += $indel{$rfi}{len};
		}
	}
	if($lasti < length($rf)-1) {
		$newrf .= substr($rf, $lasti, length($rf) - $lasti - 1);
	}
	$rf = $newrf;
}

print STDERR "Adding larger rearrangements...\n";
my $nrearr = int(random_exponential(1, 3)+1);
for(0..$nrearr) {
	my $break = int(rand(length($rf)));
	my $before = substr($rf, 0, $break);
	my $after = substr($rf, $break);
	$after = revcomp($after) if int(rand()) == 0;
	$rf = $after.$before;
}

print STDERR "Added $nsnp SNPs\n";
print STDERR "Added $microgap Microindels\n";
print STDERR "Added $nrearr Rearrangements\n";

#
# Simulate reads
#

print STDERR "Picking read and fragment lengths...\n";
# Pick random read lengths
if(defined($rdlen_exact)) {
	@readlens = ($rdlen_exact) x ($nreads * ($paired ? 2 : 1));
} else {
	@readlens = random_exponential($nreads * ($paired ? 2 : 1), $rdlen_av);
	@readlens = map int, @readlens;
	@readlens = map { int($_ + $rdlen_min) } @readlens;
}
if($paired) {
	# Pick random fragment and read lengths
	@fraglens = random_normal($nreads, $frag_av, $frag_sd);
	@fraglens = map int, @fraglens;
	for(my $i = 0; $i < scalar(@readlens); $i += 2) {
		$fraglens[$i/2] = max($fraglens[$i/2], $readlens[$i] + $readlens[$i+1]);
	}
}

sub rand_quals($) {
	my $ret = "";
	my $upper = (rand() < 0.2 ? 11 : 40);
	$upper = 4 if rand() < 0.02;
	for(1..$_[0]) {
		$ret .= chr(33+int(rand($upper)));
	}
	return $ret;
}

sub add_seq_errs($$) {
	my($rd, $qu) = @_;
	my $origLen = length($rd);
	for(0..length($rd)-1) {
		my $c = substr($rd, $_, 1);
		my $q = substr($qu, $_, 1);
		$q = ord($q)-33;
		my $p = 10 ** (-0.1 * $q);
		if(rand() < $p) {
			$c = substr("ACGTNNNNNN", int(rand(10)), 1);
		}
		substr($rd, $_, 1) = $c;
		substr($qu, $_, 1) = $q;
	}
	length($rd) == $origLen || die;
	return $rd;
}

# Now simulate 
print STDERR "Simulating reads...\n";
my $rflen = length($rf);
if($paired) {
	open(RD1, ">${prefix}_1.fq") || die;
	open(RD2, ">${prefix}_2.fq") || die;
	for(my $i = 0; $i < scalar(@fraglens); $i++) {
		# Extract fragment
		my $flen = $fraglens[$i];
		my $off = int(rand($rflen - ($flen-1)));
		my $fstr = substr($rf, $off, $flen);
		# Check if it has too many Ns
		my %ccnt = ();
		for my $j (1..$flen) {
			my $c = uc substr($fstr, $j, 1);
			$ccnt{tot}++;
			$ccnt{non_acgt}++ if ($c ne "A" && $c ne "C" && $c ne "G" && $c ne "T");
			$ccnt{$c}++;
		}
		# Skip if it has >10% Ns
		if(1.0 * $ccnt{non_acgt} / $ccnt{tot} > 0.10) {
			$i--;
			next;
		}
		# Possibly reverse complement
		$fstr = revcomp($fstr) if (int(rand(2)) == 0);
		# Get reads 1 and 2
		my $rdlen1 = min($readlens[2*$i], $flen);
		my $rdlen2 = min($readlens[2*$i+1], $flen);
		my $rd1 = substr($fstr, 0, $rdlen1);
		my $rd2 = substr($fstr, length($fstr)-$rdlen2);
		length($rd2) == $rdlen2 || die "Got ".length($rd2)." expected $rdlen2";
		# Reverse complement 2 to simulate --fr orientation
		$rd2 = revcomp($rd2);
		# Generate random quality values
		my $qu1 = rand_quals($rdlen1);
		$rd1 = add_seq_errs($rd1, $qu1);
		length($rd1) == length($qu1) || die;
		my $qu2 = rand_quals($rdlen2);
		$rd2 = add_seq_errs($rd2, $qu2);
		length($rd2) == length($qu2) || die;
		# Print
		print RD1 "\@r".($i+1)."\n$rd1\n+\n$qu1\n";
		print RD2 "\@r".($i+1)."\n$rd2\n+\n$qu2\n";
	}
	close(RD1);
	close(RD2);
	print STDERR "Made pairs: reads_1.fq/reads_2.fq\n";
} else {
	open(RD1, ">${prefix}.fq") || die;
	for(my $i = 0; $i < scalar(@readlens); $i++) {
		# Extract fragment
		my $rdlen = $readlens[$i];
		my $off = int(rand($rflen - ($rdlen-1)));
		my $rd = substr($rf, $off, $rdlen);
		# Check if it has too many Ns
		my %ccnt = ();
		for my $j (1..$rdlen) {
			my $c = uc substr($rd, $j, 1);
			$ccnt{tot}++;
			$ccnt{non_acgt}++ if ($c ne "A" && $c ne "C" && $c ne "G" && $c ne "T");
			$ccnt{$c}++;
		}
		# Skip if it has >10% Ns
		if(1.0 * $ccnt{non_acgt} / $ccnt{tot} > 0.10) {
			$i--;
			next;
		}
		length($rd) == $rdlen || die;
		# Possibly reverse complement
		$rd = revcomp($rd) if int(rand(2)) == 0;
		# Generate random quality values
		my $qu = rand_quals($rdlen);
		length($rd) == length($qu) || die "length(seq) = ".length($rd).", length(qual) = ".length($qu);
		$rd = add_seq_errs($rd, $qu);
		length($rd) == length($qu) || die "length(seq) = ".length($rd).", length(qual) = ".length($qu);
		# Print
		print RD1 "\@r".($i+1)."\n$rd\n+\n$qu\n";
	}
	close(RD1);
	print STDERR "Made unpaired reads: $prefix.fq\n";
}

print STDERR "DONE\n";
