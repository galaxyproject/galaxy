#! /usr/bin/perl -w

# A Galaxy (universe) Wrapper for fasta-subseq 
# fasta-subseq seqfile start end [-]
# fasta-subseq-wrapper.pl -i BED_file -o FASTA_file -p chr start_column end_column srand_column -g genome_build
# Requires $PATH to point to fasta-subseq
# Location of sequence files is read from /depot/data2/galaxy/alignseq.loc

use strict;
use warnings; 

my @columns = ();
my $alignseqLoc = "/depot/data2/galaxy/alignseq.loc";
my @bedData = ();
my @errors = ();
my $call = "";
my %seen = ();
my @locFields = ();
my %seqLocation = ();

die "Cannot fetch sequences for unspecified genome\n" unless @ARGV == 11;
die "Please specify genome build by clicking on pencil icon in the original dataset\n" if $ARGV[10] =~ m/\?/;

# Read /depot/data2/galaxy/alignseq.loc

open (LOC, "<$alignseqLoc") or die "Cannot open $alignseqLoc:$!\n";
while (<LOC>) {
  if (m/^seq/) {
    chop;
    @locFields = split " ";
#    $locFields[1] = lc("$1$2$3") if $locFields[1] =~ m/(\w)\w\w(\w)\w\w(\d)/;
    $seqLocation{$locFields[1]} = "$locFields[2]/";
  }
}
close LOC;

$ARGV[10] = "musMus$1" if ($ARGV[10]=~ m/^mm(\d)$/);
$ARGV[10] = "ratNor$1" if ($ARGV[10]=~ m/^rn(\d)$/);


$ARGV[5] = $ARGV[5]-1;
$ARGV[6] = $ARGV[6]-1;
$ARGV[7] = $ARGV[7]-1;
if ($ARGV[8] > 0) {
	$ARGV[8] = $ARGV[8]-1;
} else {
	$ARGV[8] = 1000000;
}



open (BED,  "<$ARGV[1]") or die "Cannot open $ARGV[1] for reading :$!\n";
open (FASTA,">$ARGV[3]") or die "Cannot open $ARGV[3] for writing :$!\n";
while (<BED>) {
  if (!m/^#/) {
    chop;
    @columns = split /\t/;
    
    # Check for field consitency below:
    $columns[$ARGV[8]] = "+" if !defined($columns[$ARGV[8]]);
    if (defined($columns[$ARGV[5]]) and defined($columns[$ARGV[6]]) and defined($columns[$ARGV[7]]) and defined($columns[$ARGV[8]])) {
      if ($columns[$ARGV[5]] =~ m/\w/ and $columns[$ARGV[6]] =~ m/^\d+$/ and $columns[$ARGV[7]] =~ m/^\d+$/ and $columns[$ARGV[8]] =~ m/^-|\+$/) {
	if (exists $seqLocation{$ARGV[10]}) {
	  if (-e "$seqLocation{$ARGV[10]}$columns[$ARGV[5]].nib") {
	    $call = "fasta-subseq $seqLocation{$ARGV[10]}$columns[$ARGV[5]].nib ".($columns[$ARGV[6]]+1)." $columns[$ARGV[7]] $columns[$ARGV[8]]"; #+1 to start position to fix coordinate system
	    open (GET_SUBSEQ, "$call |") or die "Cannot start fasta-subseq:$!\n";
	    while (<GET_SUBSEQ>) {
	      if (!m/\>/) {  # unless header print seq
		print FASTA;
	      } else { # if header replace with seqdata
		print FASTA ">$ARGV[10]_$columns[$ARGV[5]]_$columns[$ARGV[6]]_$columns[$ARGV[7]]_$columns[$ARGV[8]]\n";
	      }
	    }
	    close (GET_SUBSEQ);
	  } else {
	    push (@errors, "Sequence $columns[$ARGV[5]] was not found for genome build $ARGV[10]\nMost likely your data lists wrong chromosome number for this organism\nCheck your genome build selection");
	  }
	} else {
	  push (@errors, "No sequences are available for $ARGV[10]. Request them by reporting this error");
	}
      } else {
	push (@errors, "Bad BED fields: $columns[$ARGV[5]], $columns[$ARGV[6]], $columns[$ARGV[7]], $columns[$ARGV[8]]");
      }
    } else {
      push (@errors, "BED fields are missing. Possibly no strand information is present");
    }
  }
}
close (BED);
close (FASTA);

if (@errors > 0) {
  @errors = grep { ! $seen{$_} ++ } @errors;
  foreach (@errors) {
    print STDERR "$_\n";
  }
}

