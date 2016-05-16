#! /usr/bin/perl -w

use strict;
use warnings;

my $columns = {};
my $del = "";
my @in = ();
my @out = ();
my $command = "";
my $field = 0;

# a wrapper for changing the case of columns from within galaxy
# isaChangeCase.pl [filename] [columns] [delim] [casing] [output]

die "Check arguments: $0 [filename] [columns] [delim] [casing] [output]\n" unless @ARGV == 5;

# process column input
$ARGV[1] =~ s/\s+//g;
foreach ( split /,/, $ARGV[1] ) {
  if (m/^c\d{1,}$/i) {
    s/c//ig;
    $columns->{$_} = --$_;
  }
}

die "No columns specified, columns are not preceeded with 'c', or commas are not used to separate column numbers: $ARGV[1]\n" if keys %$columns == 0;

my $column_delimiters_href = {
	'TAB' => q{\t},
	'COMMA' => ",",
	'DASH' => "-",
	'UNDERSCORE' => "_",
	'PIPE' => q{\|},
	'DOT' => q{\.},
	'SPACE' => q{\s+}
};
	
$del = $column_delimiters_href->{$ARGV[2]};

open (OUT, ">$ARGV[4]") or die "Cannot create $ARGV[4]:$!\n";
open (IN,  "<$ARGV[0]") or die "Cannot open $ARGV[0]:$!\n";
while (<IN>) {
  chop;
  @in = split /$del/; 
  for ( my $i = 0; $i <= $#in; ++$i) {
	if (exists $columns->{$i}) {
		push(@out, $ARGV[3] eq 'up' ? uc($in[$i]) : lc($in[$i]));
	} else {
		push(@out, $in[$i]);
	}
  }
  print OUT join("\t",@out), "\n";
  @out = ();
}
close IN;

close OUT;
