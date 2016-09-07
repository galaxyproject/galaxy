#!/usr/bin/env perl
use strict;
use File::Spec;
use Path::Class;

# A helper for debugging
my ($vol,$script_path,$prog);
$prog = File::Spec->rel2abs( __FILE__ );
($vol,$script_path,$prog) = File::Spec->splitpath($prog);
my $bw_path = dir(File::Spec->splitdir($script_path))->parent();

my $bw = File::Spec->catpath(
            $vol,
            $bw_path,
            'bowtie2'
            );

exec $bw, @ARGV or die ("Fail to exec! $bw\n");



