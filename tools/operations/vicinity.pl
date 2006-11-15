#! /usr/bin/perl -w
use strict;
use warnings;

# vicinity.pl -i bed_file -pos <start|end> -up NN -down NN -o out_file
# creates a bed files containing coordinates around start or end for each entry of the original bed
# For example.
# if the original bed looked like this:
# chr1 10 200 exon1 0 +
# calling this command:
# vicinity.pl -i bed_file -pos start -up 10 -down 5 -o out_file
# will generate this output:
# chr1 0 15 exon1 0 +
# 
# calling this command using flag "end":
# vicinity.pl -i bed_file -pos end -up 10 -down 5 -o out_file
# will produce:
# chr1 10 190 205 exon1 0 +


my @bedFields = ();
my $strand    = "+";
my $start     = 0;
my $end       = 0;
my $up        = $ARGV[5];
my $down      = $ARGV[7];

die "Missing arguments <= check input" unless @ARGV == 10;


open (BED, "<$ARGV[1]") or die "Cannot open $ARGV[0]:$!\n";
open (OUT, ">$ARGV[9]") or die "Cannot create $ARGV[9]:$!\n";
while (<BED>) {
    chop;
    @bedFields = split /\t/;
    if (defined($bedFields[5])) {
      $strand = $bedFields[5];
    } else {
      $strand = "+";
    }

    $start = $bedFields[1];
    $end   = $bedFields[2];

    if ($ARGV[3] =~ m/start/i) {
	if ($strand eq "+") {
	    $start = $start - $up;
	    $start = 0 if ($start < 0);
	    $end = $bedFields[1] + $down;
	    $bedFields[1] = $start;
	    $bedFields[2] = $end;
	    print OUT join("\t", @bedFields) . "\n";
	} elsif ($strand eq "-") {
	    $start = $end - $down;
	    $start = 0 if ($start < 0);
	    $end = $bedFields[2] + $up;
	    $bedFields[1] = $start;
            $bedFields[2] = $end;
            print OUT join("\t", @bedFields) . "\n";
	}
    } elsif ($ARGV[3] =~ m/end/i) {
	if ($strand eq "+") {
            $start = $end - $up;
            $start = 0 if ($start < 0);
            $end = $bedFields[2] + $down;
            $bedFields[1] = $start;
            $bedFields[2] = $end;
            print OUT join("\t", @bedFields) . "\n";
        } elsif ($strand eq "-") {
            $start = $start - $down;
            $start = 0 if ($start < 0);
            $end = $bedFields[1] + $up;
            $bedFields[1] = $start;
            $bedFields[2] = $end;
            print OUT join("\t", @bedFields) . "\n";
        }
    }
}


	    
    
