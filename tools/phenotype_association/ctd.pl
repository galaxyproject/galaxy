#!/usr/bin/perl -w
use strict;
use LWP::UserAgent;
require HTTP::Cookies;

#######################################################
# ctd.pl 
# Submit a batch query to CTD and fetch results into galaxy history
# usage: ctd.pl inFile idCol inputType resultType actionType outFile
#######################################################

if (!@ARGV or scalar @ARGV != 6) {
   print "usage: ctd.pl inFile idCol inputType resultType actionType outFile\n";
   exit;
}

my $in = shift @ARGV;
my $col = shift @ARGV;
if ($col < 1) {
   print "The column number is with a 1 start\n";
   exit 1;
}
my $type = shift @ARGV;
my $resType = shift @ARGV;
my $actType = shift @ARGV;
my $out = shift @ARGV;

my @data;
open(FH, $in) or die "Couldn't open $in, $!\n";
while (<FH>) {
   chomp;
   my @f = split(/\t/);
   if (scalar @f < $col) { 
      print "ERROR the requested column is not in the file $col\n";
      exit 1;
   }
   push(@data, $f[$col-1]);
}
close FH or die "Couldn't close $in, $!\n";

my $url = 'http://ctdbase.org/tools/batchQuery.go';
#my $url = 'http://ctd.mdibl.org/tools/batchQuery.go';
my $d = join("\n", @data);
#list maintains order, where hash doesn't
#order matters at ctd
#to use input file (gives error can't find file)
#my @form = ('inputType', $type, 'inputTerms', '', 'report', $resType, 
   #'queryFile', [$in, ''], 'queryFileColumn', $col, 'format', 'tsv', 'action', 'Submit');
my @form = ('inputType', $type, 'inputTerms', $d, 'report', $resType,
  'queryFile', '', 'format', 'tsv', 'action', 'Submit');
if ($resType eq 'cgixns') { #only add if this type
   push(@form, 'actionTypes', $actType);
}
if ($resType eq 'go' or $resType eq 'go_enriched') {
   push(@form, 'ontology', 'go_bp', 'ontology', 'go_mf', 'ontology', 'go_cc');
}
my $ua = LWP::UserAgent->new;
$ua->cookie_jar(HTTP::Cookies->new( () ));
$ua->agent('Mozilla/5.0');
my $page = $ua->post($url, \@form, 'Content_Type'=>'form-data');
if ($page->is_success) {
   open(FH, ">", $out) or die "Couldn't open $out, $!\n";
   print FH "#";
   print FH $page->content, "\n";
   close FH or die "Couldn't close $out, $!\n";
}else {
   print "ERROR failed to get page from CTD, ", $page->status_line, "\n";
   print $page->content, "\n";
   my $req = $page->request();
   print "Requested \n";
   foreach my $k(keys %$req) { 
      if ($k eq '_headers') {
         my $t = $req->{$k};
         foreach my $k2 (keys %$t) { print "$k2 => $t->{$k2}\n"; }
      }else { print "$k => $req->{$k}\n"; }
   }
   exit 1;
}
exit;

