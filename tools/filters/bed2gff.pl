#! /usr/bin/perl -w

# $URL: file://localhost/var/local/svn/repos/elliott/annotations/bed2gff.pl $
# $Id: bed2gff.pl 601 2005-12-08 19:35:09Z elliott $

use strict;
use Pod::Usage;
use Getopt::Long;

=head1 NAME

bed2gff.pl - convert a BED file to a GFF file

=head1 SYNOPSIS

bed2gff.pl [--help] []

=head1 DESCRIPTION

Converts a BED file into GFF format. Makes the BED <score> column an
attribute/value in the last semi-colon delimited field of the GFF file.

=head1 AUTHOR

Elliott H. Margulies -- elliott@nhgri.nih.gov
    initiated 3/10/2005

=head1 OPTIONS

=over 8

=item B<--name>

feature name for third gff field. This will override the name field in the bed
file, if present.

=item B<--enhanced>

Will produce enhanced output from a very specific BED6+ input format designed by
James Taylor for the ENCODE project.

=item B<--help>

Display full documentation.

=back

=cut

my $name;
my $enhanced;

GetOptions('enhanced' => \$enhanced,
	   'name=s' => \$name,
	   'help' => sub { pod2usage( verbose => 2) });

unless ($ARGV[0]) {
    pod2usage(1);
}
my $file = $ARGV[0];
open (IN, $file);

my $localtime = localtime();
print "## gff-version 2\n" . 
    '## bed2gff.pl $Rev: 601 $' . "\n\n";
#    "## Date: $localtime\n" .
#    '## Input file: ' . $file . "\n\n";

while (my $line = <IN>) {
    next if ($line =~ /^\#/ || $line =~ /^track/ || $line =~ /^browser/ || $line =~ /^$/);
    my @d = split /\s+/, $line;
    if ($name) {
	$d[3] = $name;
    }
    $d[1]++;
    $d[4]+=0;
    print "$d[0]\tbed2gff\t$d[3]\t$d[1]\t$d[2]\t.\t+\t.";
    if ($enhanced) {
	print "\tpartition_score \"$d[5]\"; partition_name \"$d[6]\"; partition_frac_overlap \"$d[7]\";\n";
    } else {
	print "\tscore \"$d[4]\";\n";
    }
}

