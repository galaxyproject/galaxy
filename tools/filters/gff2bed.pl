#! /usr/bin/perl -w

# $URL: file://localhost/var/local/svn/repos/elliott/annotations/gff2bed.pl $
# $Id: gff2bed.pl 600 2005-12-08 18:09:34Z elliott $
# Midified by Anton Nekrutenko to print strand as well

use strict;
use Pod::Usage;
use Getopt::Long;

=head1 NAME

gff2bed.pl - convert GFF to BED files.

=head1 SYNOPSIS

gff2bed.pl [--help] [GFF file]

=head1 DESCRIPTION

Converts files in GFF format to BED files. In reality, it only looks at the
chrom, start, stop, and feature fields of the GFF file and converts to chrom,
start, stop, name fields of the BED file. This isn't rocket science.

=head1 AUTHOR

Elliott H. Margulies -- elliott@nhgri.nih.gov
    initiated on 03/14/2005

=head1 OPTIONS

=over 8

=item B<--help>

Display full documentation.

=back

=cut

GetOptions('help' => sub { pod2usage( verbose => 2) });

unless ($ARGV[0]) {
    pod2usage(1);
}

open (IN, $ARGV[0]);

while (my $line = <IN>) {
    next if ($line =~ /^\#/ || $line =~ /^$/);
    my @data   = split /\t/, $line;
    my $chrom  = $data[0];
    my $start  = $data[3];
    my $stop   = $data[4];
    my $name   = $data[2];
    my $strand = $data[6];
    $strand = "+" if $strand eq ".";
    $start--;
    print "$chrom\t$start\t$stop\t$name\t0\t$strand\n";
}

    
