#!/usr/bin/perl

###########################################################################
# Purpose: To calculate the correlation of two sets of scores in one file.
# Usage: correlation.pl infile.bed output.txt column1 column2
#        (column start from 1)
# Written by: Yi Zhang  (June, 2005)
###########################################################################
if (!$ARGV[0] || !$ARGV[1] || !defined($ARGV[2]) || !defined($ARGV[3]) ) {
   print STDERR "Usage: correlation.pl infile.bed output.txt column1 column2\n";
   print STDERR "       (column start from 1)\n"; 
   exit;
}
my $file = $ARGV[0];
my $out = $ARGV[1];

die "<font color=\"yellow\">The input columns contain numerical values: $ARGV[2], $ARGV[3]</font>.\n" if ($ARGV[2] =~ /[a-zA-Z]+/ || $ARGV[3] =~ /[a-zA-Z]+/);

my $col1 = $ARGV[2] - 1;
my $col2 = $ARGV[3] - 1;

my ($f, $o);
my (@a, @b);

my $n_t = 0;
open($f, $file) or die "Could't open $file, $!\n";
while(<$f>) {
  chomp;
  my @t = split(/\t/);
  if ($n_t == 0) { 
     $n_t = scalar(@t) - 1; 
     die "<font color=\"yellow\">The input column number exceeds the size of the file: $col1, $col2, $n_t</font>\n" if ( $col1 > $n_t || $col2 > $n_t );
  }
  die "<font color=\"yellow\">The columns you have selected contain non numeric characters:$t[$col1] and $t[$col2] \n</font>" if ($t[$col1] =~ /[a-zA-Z]+/ || $t[$col2] =~ /[a-zA-Z]+/);  
  push(@a, $t[$col1]);
  push(@b, $t[$col2]);
}
close($f);

my $result = correlation(\@a, \@b);

open($o, ">$out") or die "Couldn't open $out, $!\n";
$col1 = $col1 + 1;
$col2 = $col2 + 1;
print $o "The correlation of column $col1 and $col2 is $result\n";
close($o);
print "The correlation of column $col1 and $col2 is $result\n";

sub correlation {
   my ($array1ref, $array2ref) = @_;
   my ($sum1, $sum2);
   my ($sum1_squared, $sum2_squared); 
   foreach (@$array1ref) { $sum1 += $_;  $sum1_squared += $_**2; }
   foreach (@$array2ref) { $sum2 += $_;  $sum2_squared += $_**2; }
   my $numerator = (@$array1ref**2) * covariance($array1ref, $array2ref);
   my $denominator = sqrt(((@$array1ref * $sum1_squared) - ($sum1**2)) *
                          ((@$array1ref * $sum2_squared) - ($sum2**2)));
   my $r;
   if ($denominator == 0) {
     print STDERR "The denominator is 0.\n";
	 exit 0; 
   } else {
      $r = $numerator / $denominator;
   }
    return $r;
}

sub covariance {
   my ($array1ref, $array2ref) = @_;
   my ($i, $result);
   for ($i = 0; $i < @$array1ref; $i++) {
       $result += $array1ref->[$i] * $array2ref->[$i];
   }
   $result /= @$array1ref;
   $result -= mean($array1ref) * mean($array2ref);
}

sub mean {
  my ($arrayref) = @_;
  my $result;
  foreach (@$arrayref) { $result += $_; }
  return $result/@$arrayref;
}

