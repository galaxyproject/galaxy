#!/usr/bin/perl -w
use strict;
use warnings;
use Term::ANSIColor;
use Pod::Checker; 
use File::Basename;
use IO::Handle;
use Cwd;
use File::Path qw(make_path remove_tree);
use File::Temp qw/ tempfile tempdir /;
my $tdir = tempdir( CLEANUP => 0 );
chdir $tdir;
my $dir = getcwd;  
# print "current dit=$dir\n"; 
#<STDIN>;
use vars qw (%treesToReject %template $printer $interr_poscord $interrcord $no_of_interruptionscord $stringfile @tags 
$infocord $typecord $startcord $strandcord $endcord $microsatcord $motifcord $sequencepos $no_of_species 
$gapcord %thresholdhash $tree_decipherer @sp_ident %revHash %sameHash %treesToIgnore %alternate @exactspecies_orig @exactspecies @exacttags
$mono_flanksimplicityRepno $di_flanksimplicityRepno $prop_of_seq_allowedtoAT $prop_of_seq_allowedtoCG);
use FileHandle;
use IO::Handle;                     # 5.004 or higher

#my @ar = ("/Users/ydk/work/rhesus_microsat/results/galay/chr22_5sp.maf.txt", "/Users/ydk/work/rhesus_microsat/results/galay/dataset_11.dat",
#"/Users/ydk/work/rhesus_microsat/results/galay/chr22_5spec.maf.summ","hg18,panTro2,ponAbe2,rheMac2,calJac1","((((hg18, panTro2), ponAbe2), rheMac2), calJac1)","9,10,12,12",
#"10","0.8");
my @ar = @ARGV;
my ($maf, $orth, $summout, $species_set, $tree_definition, $thresholds, $FLANK_SUPPORT, $SIMILARITY_THRESH) = @ar;
$SIMILARITY_THRESH=$SIMILARITY_THRESH/100;
#########################
$SIMILARITY_THRESH = $SIMILARITY_THRESH/100;
my $EDGE_DISTANCE = 10; 
my $COMPLEXITY_SUPPORT = 20;
load_thresholds("9_10_12_12");
my $FLANKINDEL_MAXTHRESH = 0.3;

my $mono_flanksimplicityRepno=6;
my $di_flanksimplicityRepno=10;
my $prop_of_seq_allowedtoAT=0.5;
my $prop_of_seq_allowedtoCG=0.66;

#########################
my $tspecies_set = $species_set;

my %speciesReplacement = ();
my %speciesReplacementTag = ();
my %replacementArr= ();
my %replacementArrTag= ();
my %backReplacementArr= ();
my %backReplacementArrTag= ();

my $tree_definition_split = $tree_definition;
$tree_definition_split =~ s/[\(\)]//g;
my @gotSpecies = ($tree_definition_split =~ /(,)/g);
# print "gotSpecies = @gotSpecies\n";

if (scalar(@gotSpecies)+1 ==5){

	$speciesReplacement{1}="calJac1";
	$speciesReplacement{2}="rheMac2";
	$speciesReplacement{3}="ponAbe2";
	$speciesReplacement{4}="panTro2";
	$speciesReplacement{5}="hg18";

	$speciesReplacementTag{1}="M";
	$speciesReplacementTag{2}="R";
	$speciesReplacementTag{3}="O";
	$speciesReplacementTag{4}="C";
	$speciesReplacementTag{5}="H";
	$species_set="hg18,panTro2,ponAbe2,rheMac2,calJac1";

}
if (scalar(@gotSpecies)+1 ==4){

	$speciesReplacement{1}="rheMac2";
	$speciesReplacement{2}="ponAbe2";
	$speciesReplacement{3}="panTro2";
	$speciesReplacement{4}="hg18";

	$speciesReplacementTag{1}="R";
	$speciesReplacementTag{2}="O";
	$speciesReplacementTag{3}="C";
	$speciesReplacementTag{4}="H";
	$species_set="hg18,panTro2,ponAbe2,rheMac2";

}

#	$tree_definition = "((((hg18,panTro2),ponAbe2),rheMac2),calJac1)";
my $tree_definition_copy = $tree_definition;
my $tree_definition_orig = $tree_definition;
my $brackets = 0;

while (1){
	#last if $tree_definition_copy !~ /\(/;
	$brackets++;
# print "brackets = $brackets\n";
	last if $brackets > 6;
	$tree_definition_copy =~ s/^\(//g;
	$tree_definition_copy =~ s/\)$//g;
# print "tree_definition_copy = $tree_definition_copy\n";
	my @arr = ();

	if ($tree_definition_copy =~ /^([a-zA-Z0-9_]+),([a-zA-Z0-9_\(\),]+)\)$/){
		@arr = $tree_definition_copy =~ /^([a-zA-Z0-9_]+),([a-zA-Z0-9_\(\),]+)$/;
# print "arr = @arr\n";
		$tree_definition_copy = $2;
		$replacementArr{$1} = $speciesReplacement{$brackets};
		$backReplacementArr{$speciesReplacement{$brackets}}=$1;
		
		$replacementArrTag{$1} = $speciesReplacementTag{$brackets};
		$backReplacementArrTag{$speciesReplacementTag{$brackets}}=$1;
# print "replacing $1 with $replacementArr{$1}\n";
		
		$sp_ident[$brackets-1] = $1;
	
	}
	elsif ($tree_definition_copy =~ /^\(([a-zA-Z0-9_\(\),]+),([a-zA-Z0-9_]+)$/){
		@arr = $tree_definition_copy =~ /^([a-zA-Z0-9_\(\),]+),([a-zA-Z0-9_]+)$/;
# print "arr = @arr\n";
		$tree_definition_copy = $1;
		$replacementArr{$2} = $speciesReplacement{$brackets};
		$backReplacementArr{$speciesReplacement{$brackets}}=$2;

		$replacementArrTag{$2} = $speciesReplacementTag{$brackets};
		$backReplacementArrTag{$speciesReplacementTag{$brackets}}=$2;
# print "replacing $2 with $replacementArr{$2}\n";

		$sp_ident[$brackets-1] = $2;
	}
	elsif ($tree_definition_copy =~ /^([a-zA-Z0-9_]+),([a-zA-Z0-9_]+)$/){
		@arr = $tree_definition_copy =~ /^([a-zA-Z0-9_]+),([a-zA-Z0-9_]+)$/;
# print "arr = @arr .. TERMINAL\n";
		$tree_definition_copy = $1;
		$replacementArr{$2} = $speciesReplacement{$brackets};
		$replacementArr{$1} = $speciesReplacement{$brackets+1};
		$backReplacementArr{$speciesReplacement{$brackets}}=$2;
		$backReplacementArr{$speciesReplacement{$brackets+1}}=$1;

		$replacementArrTag{$1} = $speciesReplacementTag{$brackets+1};
		$backReplacementArrTag{$speciesReplacementTag{$brackets+1}}=$1;

		$replacementArrTag{$2} = $speciesReplacementTag{$brackets};
		$backReplacementArrTag{$speciesReplacementTag{$brackets}}=$2;
# print "replacing $1 with $replacementArr{$1}\n";
# print "replacing $2 with $replacementArr{$2}\n";
# print "replacing $1 with $replacementArrTag{$1}\n";
# print "replacing $2 with $replacementArrTag{$2}\n";

		$sp_ident[$brackets-1] = $2;
		$sp_ident[$brackets] = $1;


		last;

	}
	elsif ($tree_definition_copy =~ /^\(([a-zA-Z0-9_\(\),]+),([a-zA-Z0-9_\(\),]+)\)$/){
		$tree_definition_copy =~ s/^\(//g;
		$tree_definition_copy =~ s/\)$//g;
		$brackets--;
	}		
}

foreach my $key (keys %replacementArr){
	my $replacement = $replacementArr{$key};
	$tree_definition =~ s/$key/$replacement/g;
}
@sp_ident = reverse(@sp_ident);
# print "modified tree_definition = $tree_definition\n";
# print "done .. tree_definition = $tree_definition\n";
# print "sp_ident = @sp_ident\n";
#<STDIN>;


my $complexity=int($COMPLEXITY_SUPPORT * (1/40));

#print "complexity=$complexity\n";
#<STDIN>;

$printer = 1;

my $rando = int(rand(1000));
my $localdate = `date`;
$localdate =~ /([0-9]+):([0-9]+):([0-9]+)/;
my $info = $rando.$1.$2.$3;

#---------------------------------------------------------------------------
# GETTING INPUT INFORMATION AND OPENING INPUT AND OUTPUT FILES


my @thresharr = (0, split(/,/,$thresholds));
my $randno=int(rand(100000));
my $megamatch = $randno.".megamatch.net.axt"; #"/gpfs/home/ydk104/work/rhesus_microsat/axtNet/hg18.panTro2.ponAbe2.rheMac2.calJac1/chr1.hg18.panTro2.ponAbe2.rheMac2.calJac1.net.axt";
my $megamatchlck = $megamatch.".lck";
unlink $megamatchlck;

my $selected= $orth;
#my $eventfile = $orth;
 $selected = $selected."_SELECTED";
#$selected = $selected."_".$SIMILARITY_THRESH;
#my $runtime = $selected.".runtime";

my $inputtags = "H:C:O:R:M";
$inputtags = $ARGV[3] if exists $ARGV[3] && $ARGV[3] =~ /[A-Z]:[A-Z]/;

my @all_tags = split(/:/, $inputtags);
my $inputsp = "hg18:panTro2:ponAbe2:rheMac2:calJac1";
$inputsp = $ARGV[4] if exists $ARGV[4] && $ARGV[3] =~ /[0-9]+:/;
#@sp_ident = split(/:/,$inputsp);
my $junkfile = $orth."_junk";

my $sh = load_sameHash(1);
my $rh = load_revHash(1);

#print "inputs are : \n"; foreach(@ARGV){print $_,"\n";} 
open (SELECT, ">$selected") or die "Cannot open selected file: $selected: $!";
open (SUMMARY, ">$summout") or die "Cannot open summout file: $summout: $!";
#open (RUN, ">$runtime") or die "Cannot open orth file: $runtime: $!";
#my $ctlfile = "baseml\.ctl"; #$ARGV[4];
#my $treefile = "/gpfs/home/ydk104/work/rhesus_microsat/codes/lib/"; 	#1 THIS IS THE THE TREE UNDER CONSIDERATION, IN NEWICK 
my %registeredTrees = ();
my @removalReasons = 
("microsatellite is compound", 
"complex structure", 
"if no. if micros is more than no. of species", 
"if more than one micro per species ", 
"if microsat contains N", 
"different motif than required ", 
"more than zero interruptions", 
"microsat could not form key ", 
"orthologous microsats of different motif size ",
"orthologous microsats of different motifs ", 
"microsats belong to different alignment blocks altogether", 
"microsat near edge", 
"microsat in low complexity region", 
"microsat flanks dont align well", 
"phylogeny not informative");
my %allowedhash=();
#---------------------------------------------------------------------------
# WORKING ON MAKING THE MEGAMATCH FILE
my $chromt=int(rand(10000));
my $p_chr=$chromt;

my $tree_definition_orig_copy = $tree_definition_orig;

$tree_definition=~s/,/, /g;
$tree_definition =~ s/, +/, /g;
$tree_definition_orig=~s/,/, /g;
$tree_definition_orig =~ s/, +/, /g;
my @exactspeciesset_unarranged = split(/,/,$species_set);
my @exactspeciesset_unarranged_orig = split(/,/,$tspecies_set);
my $largesttree = "$tree_definition;";
my $largesttree_orig = "$tree_definition_orig;";
# print "largesttree = $largesttree\n";
$tree_definition =~ s/\(//g;
$tree_definition =~ s/\)//g;
$tree_definition=~s/[\)\(, ]/\t/g;
$tree_definition =~ s/\t+/\t/g;		

$tree_definition_orig =~ s/\(//g;
$tree_definition_orig =~ s/\)//g;
$tree_definition_orig =~s/[\)\(, ]/\t/g;
$tree_definition_orig =~ s/\t+/\t/g;		
# print "tree_definition = $tree_definition tree_definition_orig = $tree_definition_orig\n";

my @treespecies=split(/\t+/,$tree_definition);
my @treespecies_orig=split(/\t+/,$tree_definition_orig);
# print "tree_definition = $tree_definition .. treespecies=@treespecies ... treespecies_orig=@treespecies_orig\n";
#<STDIN>;

foreach my $spec (@treespecies){
	foreach my $espec (@exactspeciesset_unarranged){
# print "spec=$spec and espec=$espec\n";
		push @exactspecies, $spec if $spec eq $espec;
	}
}

foreach my $spec (@treespecies_orig){
	foreach my $espec (@exactspeciesset_unarranged_orig){
# print "spec=$spec and espec=$espec\n";
		push @exactspecies_orig, $spec if $spec eq $espec;
	}
}

my $focalspec = $exactspecies[0];
my $focalspec_orig = $exactspecies_orig[0];
# print "exactspecies=@exactspecies ... focalspec=$focalspec\n";
# print "texactspecies=@exactspecies_orig ... focalspec_orig=$focalspec_orig\n";
#<STDIN>;
my $arranged_species_set = join(".",@exactspecies);
my $arranged_species_set_orig = join(".",@exactspecies_orig);

@exacttags=@exactspecies;
my @exacttags_orig=@exactspecies_orig;

foreach my $extag (@exacttags){
	$extag =~ s/hg18/H/g;
	$extag =~ s/panTro2/C/g;
	$extag =~ s/ponAbe2/O/g;
	$extag =~ s/rheMac2/R/g;
	$extag =~ s/calJac1/M/g;
}

foreach my $extag (@exacttags_orig){
	$extag =~ s/hg18/H/g;
	$extag =~ s/panTro2/C/g;
	$extag =~ s/ponAbe2/O/g;
	$extag =~ s/rheMac2/R/g;
	$extag =~ s/calJac1/M/g;
}

my $chr_name = join(".",("chr".$p_chr),$arranged_species_set, "net", "axt");
#print "sending to maftoAxt_multispecies: $maf, $tree_definition, $chr_name, $species_set .. focalspec=$focalspec \n"; 

maftoAxt_multispecies($maf, $tree_definition_orig_copy, $chr_name, $tspecies_set);
#print "made files\n";
my @filterseqfiles= ($chr_name);
$largesttree =~ s/hg18/H/g;
$largesttree =~ s/panTro2/C/g;
$largesttree =~ s/ponAbe2/O/g;
$largesttree =~ s/rheMac2/R/g;
$largesttree =~ s/calJac1/M/g;
#<STDIN>;
#---------------------------------------------------------------------------

my ($lagestnodes, $largestbranches) = get_nodes($largesttree); 
shift (@$lagestnodes);
my @extendedtitle=();

my $title = ();
my $parttitle = ();
my @titlearr = ();
my @firsttitle=($focalspec_orig."chrom", $focalspec_orig."start", $focalspec_orig."end", $focalspec_orig."motif", $focalspec_orig."motifsize", $focalspec_orig."threshold");

my @finames= qw(chr	start	end	motif	motifsize	microsat	mutation	mutation.position	mutation.from	mutation.to	insertion.details	deletion.details);

my @fititle=();

foreach my $spec (split(",",$tspecies_set)){
	push @fititle, $spec;
	foreach my $name (@finames){
		push @fititle, $spec.".".$name;
	}
}


my @othertitle=qw(somechr somestart	somened	event source);

my @fnames = ();
push @fnames, qw(insertions_num  deletions_num  motinsertions_num  motinsertionsf_num  motdeletions_num  motdeletionsf_num  noninsertions_num  nondeletions_num) ;
push @fnames, qw(binsertions_num bdeletions_num bmotinsertions_num bmotinsertionsf_num bmotdeletions_num bmotdeletionsf_num bnoninsertions_num bnondeletions_num) ;
push @fnames, qw(dinsertions_num ddeletions_num dmotinsertions_num dmotinsertionsf_num dmotdeletions_num dmotdeletionsf_num dnoninsertions_num dnondeletions_num) ;
push @fnames, qw(ninsertions_num ndeletions_num nmotinsertions_num nmotinsertionsf_num nmotdeletions_num nmotdeletionsf_num nnoninsertions_num nnondeletions_num) ;
push @fnames, qw(substitutions_num bsubstitutions_num dsubstitutions_num nsubstitutions_num indels_num subs_num);

my @fullnames = ();
# print "revising\n";
# print "H = $backReplacementArrTag{H}\n";
# print "C = $backReplacementArrTag{C}\n";
# print "O = $backReplacementArrTag{O}\n";
# print "R = $backReplacementArrTag{R}\n";
# print "M = $backReplacementArrTag{M}\n";

foreach my $lnode (@$lagestnodes){
	my @pair = @$lnode;
	my @nodemutarr = ();
	for my $p (@pair){
# print "p = $p\n";
		$p =~ s/[\(\), ]+//g;
		$p =~ s/([A-Z])/$1./g;
		$p =~ s/\.$//g;
		
		$p =~ s/H/$backReplacementArrTag{H}/g;
		$p =~ s/C/$backReplacementArrTag{C}/g;
		$p =~ s/O/$backReplacementArrTag{O}/g;
		$p =~ s/R/$backReplacementArrTag{R}/g;
		$p =~ s/M/$backReplacementArrTag{M}/g;
		foreach my $n (@fnames) {	push @fullnames, $p.".".$n;}
	}
}

#print SUMMARY "#",join("\t", @firsttitle, @fititle, @othertitle);

#print SUMMARY "\t",join("\t", @fullnames);
my $header = join("\t",@firsttitle, @fititle, @othertitle,  @fullnames, @fnames, "tree", "cleancase");
# print "header= $header\n";
#<STDIN>;

#print SUMMARY "\t",join("\t", @fnames);
#$title=  $title."\t".join("\t", @fnames);

#print SUMMARY "\t","tree","\t", "cleancase", "\n";
#$title=  $title."\t"."tree"."\t"."cleancase". "\n";

#print $title; #<STDIN>;

#print "all_tags = @all_tags\n";

for my $no (3 ... $#all_tags+1){
#	print "no=$no\n"; #<STDIN>;
	@tags = @all_tags[0 ... $no-1];
# print "all_tags=>@all_tags< , tags = >@tags<\n" if $printer == 1; #<STDIN>;
	%template=();
	my @nextcounter = (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0);
	#next if scalar(@tags) < 4;
# print "now doing tags = @tags, no = $no\n"; 
	open (ORTH, "<$orth") or die "Cannot open orth file: $orth: $!";
	
#	print SUMMARY join "\t", qw (species chr start end branch motif microsat mutation position from to insertion deletion);
	
	
	##################### T E M P O R A R Y #####################
	my @finaltitle=();
	my @singletitle = qw (species chr start end motif motifsize microsat strand microsatsize col10 col11 col12 col13);
	my $endtitle = ();
	foreach my $tag (@tags){
		my @tempsingle = ();
		
		foreach my $single (@singletitle){
			push @tempsingle, $tag.$single;
		}
		@finaltitle = (@finaltitle, @tempsingle);	
	}

#	print SUMMARY join("\t",@finaltitle),"\n";
	
	#############################################################
	
	#---------------------------------------------------------------------------
	# GET THE TREE FROM TREE FILE
	my $tree = ();
	$tree = "((H, C), O)" if $no == 3;
	$tree = "(((H, C), O), R)" if $no == 4;
	$tree = "((((H, C), O), R), M)" if $no == 5;
#	$tree=~s/;$//g;
#	print "our tree = $tree\n";
	#---------------------------------------------------------------------------
	# LOADING HASH CONTAINING ALL POSSIBLE TREES:
	$tree_decipherer = "/gpfs/home/ydk104/work/rhesus_microsat/codes/lib/tree_analysis_".join("",@tags).".txt";
	%template=();
	%alternate=();
	load_allPossibleTrees($tree_decipherer, \%template, \%alternate);
	
	#---------------------------------------------------------------------------
	# LOADING THE TREES TO REJECT FOR BIRTH ANALYSIS
	%treesToReject=();
	%treesToIgnore=();
	load_treesToReject(@tags); 
	load_treesToIgnore(@tags);
	#---------------------------------------------------------------------------
	# LOADING INPUT DATA INTO HASHES AND ARRAYS
	
	
	#1 THIS IS THE POINT WHERE WE CAN FILTER OUT LARGE MICROSAT CLUSTERS 
	#2 AS WELL AS MULTIPLE-ALIGNMENT-BLOCKS-SPANNING MICROSATS (KIND OF
	#3 IMPLICIT IN THE FIRST PART OF THE SENTENCE ITSELF IN MOST CASES).
	
	my %orths=();
	my $counterm = 0;
	my $loaded = 0;
	my %seen = ();
	my @allowedchrs = ();
#	print "no = $no\n"; #<STDIN>;

	while (my $line = <ORTH>){
	#	print "line=$line\n";
		my $register1 = $line =~ s/>$exactspecies_orig[0]/>$replacementArrTag{$exactspecies_orig[0]}/g;
		my $register2 = $line =~ s/>$exactspecies_orig[1]/>$replacementArrTag{$exactspecies_orig[1]}/g;
		my $register3 = $line =~ s/>$exactspecies_orig[2]/>$replacementArrTag{$exactspecies_orig[2]}/g;
		my $register4 = $line =~ s/>$exactspecies_orig[3]/>$replacementArrTag{$exactspecies_orig[3]}/g;
		my $register5 = $line =~ s/>$exactspecies_orig[4]/>$replacementArrTag{$exactspecies_orig[4]}/g if exists $exactspecies_orig[4];
		
	#	print "line = $line\n"; <STDIN>;
		
		
	#	next if $register1 + $register2 + $register3 + $register4 + $register5 > scalar(@tags);
		my @micros = split(/>/,$line); 									# LOADING ALL THE MICROSAT ENTRIES FROM THE CLUSTER INTO @micros
		#print "micros=",printarr(@micros),"\n"; #<STDIN>;
		shift @micros; 													# EMPTYING THE FIRST, EMTPY ELEMENT OF THE ARRAY
		
		$no_of_species = adjustCoordinates($micros[0]);
#		print "A: $no_of_species\n";
		next if $no_of_species != $no;
# print "no = $no ... no_of_species=$no_of_species\n";#<STDIN>;
		$counterm++;
		#------------------------------------------------
		$nextcounter[0]++  if $line =~ /compound/;
		next if $line =~ /compound/; 									# GETTING RID OF COMPOUND MICROSATS
		#------------------------------------------------
		#next if $line =~ /[A-Za-z]>[a-zA-Z]/;
		#------------------------------------------------
		chomp $line;
		my $match_count = ($line =~ s/>/>/g); 							# COUNTING THE NUMBER OF MICROSAT ENTRIES IN THE CLUSTER
		#print "number of species = $match_count\n";
		my $stopper = 0;	
		foreach my $mic (@micros){
			my @local = split(/\t/,$mic);
			if ($local[$typecord] =~ /\./ || exists($local[$no_of_interruptionscord+2])) {$stopper = 1; $nextcounter[1]++;
			last; } 
																		# REMOVING CLUSTERS WITH THE CYRPTIC, (UNRESOLVABLY COMPLEX) MICROSAT ENTRIES IN THEM
		}
		next if $stopper ==1;
		#------------------------------------------------
		$nextcounter[2]++ if (scalar(@micros) >$no_of_species);
	
		next if (scalar(@micros) >$no_of_species); 						#1 REMOVING MICROSAT CLUSTERS WITH MORE NUMBER OF MICROSAT ENTRIES THAN THE NUMBER OF SPECIES IN THE DATASET.
																		#2 THIS IS SO BECAUSE SUCH CLUSTERS IMPLY THAT IN AT LEAST ONE SPECIES, THERE IS MORE THAN ONE MICROSAT ENTRY
																		#3 IN THE CLUSTER. THUS, HERE WE ARE GETTING RID OF MICROSATS CLUSTERS THAT INCLUDE MULTUPLE, NEIGHBORING
																		#4 MICROSATS, AND STICK TO CLEAN MICROSATS THAT DO NOT HAVE ANY MICROSATS IN NEIGHBORHOOD.
																		#5 THIS 'NEIGHBORHOOD-RANGE' HAD BEEN DECIDED PREVIOUSLY IN OUR CODE multiSpecies_orthFinder4.pl
		my $nexter = 0;
		foreach my $tag (@tags){
			my $tagcount = ($line =~ s/>$tag\t/>$tag\t/g);
			if ($tagcount > 1) { $nexter =1; #print colored ['red'],"multiple entires per species : $tagcount of $tag\n" if $printer == 1; 
				next; 
			}
		}
		
		if ($nexter == 1){
			$nextcounter[3]++;
			next;
		}
		#------------------------------------------------
		foreach my $mic (@micros){										#1	REMOVING MICROSATELLITES WITH ANY 'N's IN THEM
			my @local = split(/\t/,$mic);								
			if ($local[$microsatcord] =~ /N/) {$stopper =1; 		$nextcounter[4]++;
			last;}			
		}
		next if $stopper ==1;
		#print "till here 1\n"; #<STDIN>;
		#------------------------------------------------
		my @micros_copy = @micros;
		
		my $tempmicro = shift(@micros_copy);							#1 CURRENTLY OBTAINING INFORMATION FOR THE FIRST 
																		#2 MICROSAT IN THE CLUSTER.
		my @tempfields = split(/\t/,$tempmicro);
		my $prevtype = $tempfields[$typecord];
		my $tempmotif = $tempfields[$motifcord];
		
		my $tempfirstmotif = ();
		if (scalar(@tempfields) > $microsatcord + 2){
			if ($tempfields[$no_of_interruptionscord] >= 1) {			#1	DISCARDING MICROSATS WITH MORE THAN ZERO INTERRUPTIONS
																		#2	IN THE FIRST MICROSAT OF THE CLUSTER
				$nexter =1; #print colored ['blue'],"more than one interruptions \n" if $printer == 1; 
			}
		}
		if ($nexter == 1){
			$nextcounter[6]++;
			next;
		}															#1	DONE OBTAINING INFORMATION REGARDING 
																		#2	THE FIRST MICROSAT FROM THE CLUSTER
		
		if ($tempmotif =~ /^\[/){
			$tempmotif =~ s/^\[//g;
			$tempmotif =~ /([a-zA-Z]+)\].*/;
			$tempfirstmotif = $1;										#1 OBTAINING THE FIRTS MOTIF OF MICROSAT
		}
		else {$tempfirstmotif = $tempmotif;}
		my $prevmotif = $tempfirstmotif;
		
		my $key = ();
	#	print "searching temp micro for 0-9 $focalspec chr0-9a-zA-Z 0-9 0-9 \n";
	#	print "tempmicro = $tempmicro .. looking for ([0-9]+)\s+($focalspec_orig)\s(chr[0-9a-zA-Z]+)\s([0-9]+)\s([0-9]+)\n"; <STDIN>;
		if ($tempmicro =~ /([0-9]+)\s+($focalspec_orig)\s(chr[0-9a-zA-Z]+)\s([0-9]+)\s([0-9]+)/ ) {
	#		print "B: $no_of_species\n";
			$key = join("_",$2, $3,  $4, $5);
		}
		else{
# print "counld not form  a key for temp\n"; # if $printer == 1;
			$nextcounter[7]++;
			next;
		}
		#-----------------												#1	NOW, AFTER OBTAINING INFORMATION ABOUT
																		#2	THE FIRST MICROSAT IN THE CLUSTER, THE
																		#3	FOLLOWING LOOP GOES THROUGH THE OTHER MICROSATS
																		#4	TO SEE IF THEY SHARE THE REQUIRED FEATURES (BELOW)
	
		foreach my $micro (@micros_copy){
			my @fields = split(/\t/,$micro);
			#-----------------	
			if (scalar(@fields) > $microsatcord + 2){					#1	DISCARDING MICROSATS WITH MORE THAN ONE INTERRUPTIONS
				if ($fields[$no_of_interruptionscord] >= 1) {$nexter =1; #print colored ['blue'],"more than one interruptions \n" if $printer == 1; 
				$nextcounter[6]++;
				last; }											
			}
			#-----------------	
			if (($prevtype ne "0") && ($prevtype ne $fields[$typecord])) { 
				$nexter =1; #print colored ['yellow'],"microsat of different type \n" if $printer == 1; 
				$nextcounter[8]++;
				last; }														#1 DISCARDING MICROSAT CLUSTERS WHERE MICROSATS BELONG
			#-----------------											#2 TO DIFFERENT TYPES (MONOS, DIS, TRIS ETC.)
			$prevtype = $fields[$typecord];
			
			my $motif = $fields[$motifcord];
			my $firstmotif = ();
		
			if ($motif =~ /^\[/){
				$motif =~ s/^\[//g;
				$motif =~ /([a-zA-Z]+)\].*/;
				$firstmotif = $1;
			}
			else {$firstmotif = $motif;}
			
			my $motifpattern = $firstmotif.$firstmotif;
			my $prevmotifpattern = $prevmotif.$prevmotif;
			
			if (($prevmotif ne "0")&&(($motifpattern !~ /$prevmotif/i)||($prevmotifpattern !~ /$firstmotif/i)) ) {  
				$nexter =1; #print colored ['green'],"different motifs used \n$line\n" if $printer == 1;
				$nextcounter[9]++;
				last; 
			}														#1	DISCARDING MICROSAT CLUSTERS WHERE MICROSATS BELONG
																	#2	TO DIFFERENT MOTIFS
			my $prevmotif = $firstmotif;
			#-----------------			
			
			for my $t (0 ... $#tags){								#1	DISCARDING MICROSAT CLUSTERS WHERE MICROSAT ENTRIES BELONG
																	#2	DIFFERENT ALIGNMENT BLOCKS
				if ($micro =~ /([0-9]+)\s+($focalspec_orig)\s([_0-9a-zA-Z]+)\s([0-9]+)\s([0-9]+)/ ) {
					my $key2 = join("_",$2, $3, $4, $5);
# print "key = $key .. key2 = $key2\n"; #<STDIN>;
					if ($key2 ne $key){
#						print "microsats belong to diffferent alignment blocks altogether\n" if $printer == 1;
						$nextcounter[10]++;
						$nexter = 1; last;
					}
				}
				else{
# print "counld not form  a key for $line\n"; # if $printer == 1; 
					#<STDIN>;
					$nexter = 1; last;
				}
			}
		}
		#print "D2: $no_of_species\n";

		#####################
		if ($nexter == 1){
# print "nexting\n"; # if $printer == 1; 
				next;
			}
		else{
# print "^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n$key:\n$line\nvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv\n"  if $printer == 1;
			push (@{$orths{$key}},$line);	
			$loaded++;
			if ($line =~ /($focalspec_orig)\s([_a-zA-Z0-9]+)\s([0-9]+)\s([0-9]+)/ ) {
				
#				print "$line\n"  if $printer == 1; #if $line =~ /Contig/;
#				print "################ ################\n" if $printer == 1;
				push @allowedchrs, $2 if !exists $allowedhash{$2};
				$allowedhash{$2} = 1; 
				my $key = join("\t",$1, $2, $3, $4);
#				print "C: $no_of_species .. key = $key\n";#<STDIN>;
# print "print the shit: $key\n" ; #if $printer  == 1;
				$seen{$key} = 1;
			}
			else { #print "Key could not be formed in SPUT for ($focalspec_orig) (chrom) ([0-9]+) ([0-9]+)\n";
			}
		}
	}
	close ORTH;
# print "now studying where we lost microsatellites: @nextcounter\n";
	for my $reason (0 ... $#nextcounter){
		#print $removalReasons[$reason]."\t".$nextcounter[$reason],"\n";
	}
# print "\ntotal number of keys formed = ", scalar(keys %orths), " = \n";
# print "done filtering .. counterm = $counterm and loaded = $loaded\n"; 
	#----------------------------------------------------------------------------------------------------------------
	# NOW GENERATING THE ALIGNMENT FILE WITH RELELEVENT ALIGNMENTS STORED ONLY.
# print "adding files @filterseqfiles \n";
	#<STDIN>;
	
	while (1){
		if (-e $megamatchlck){
# print "waiting to write into $megamatchlck\n";
			sleep 10;
		}
		else{
			open (MEGAMLCK, ">$megamatchlck") or die "Cannot open megamatchlck file $megamatchlck: $!";	
			open (MEGAM, ">$megamatch") or die "Cannot open megamatch file $megamatch: $!";
			last;
		}
	}
	
	foreach my $seqfile (@filterseqfiles){
		my $fullpath = $seqfile;
  		#print "opening file: $fullpath\n"; <STDIN>;
		open (MATCH, "<$fullpath") or die "Cannot open MATCH file $fullpath: $!";
		my $matchlines = 0;

		while (my $line = <MATCH>)	{
			#print "checking $line";
			if ($line =~ /($focalspec_orig)\s([a-zA-Z0-9]+)\s([0-9]+)\s([0-9]+)/ ) {
				my $key = join("\t",$1, $2, $3, $4);
# print "key = $key\n";
				#print "------------------------------------------------------\n";
				#print "asking $line\n";
				if (exists $seen{$key}){
				
				#print "seen $line \n"; <STDIN>;
					while (1){
						$matchlines++;
						print MEGAM $line;
						$line = <MATCH>;
						print MEGAM "\n" if $line !~/[0-9a-zA-Z]/;
						last if $line !~/[0-9a-zA-Z]/;
					}
				}
				else{
# print "not seen\n";
				}
			}
		}
#		print "matchlines = $matchlines\n";
		close MATCH;
	}
	close MEGAMLCK;
	
	unlink $megamatchlck;
	close MEGAM;
	undef %seen;
# print "done writitn to $megamatch\n";#<STDIN>;
	#----------------------------------------------------------------------------------------------------------------
	#<STDIN>;
	#---------------------------------------------------------------------------
	# NOW, AFTER FILTERING MANY MICROSATS, AND LOADING THE FILTERED ONES INTO
	# THE HASH %orths , WE GO THROUGH THE ALIGNMENT FILE, AND STUDY THE 
	# FLANKING SEQUENCES OF ALL THESE MICROSATS, TO FILTER THEM FURTHER
	#$printer = 1;
	
	my $microreadcounter=0;
	my $contigsentered=0;
	my $contignotrightcounter=0;
	my $keynotformedcounter=0;
	my $keynotfoundcounter= 0;
	my $dotcounter = 0;

#	print "opening $megamatch\n";

	open (BO, "<$megamatch") or die "Cannot open alignment file: $megamatch: $!";
# print "doing  $megamatch\n " ;

	#<STDIN>;
	
	while (my $line = <BO>){
#		print $line; #<STDIN>;
# print "." if $dotcounter % 100 ==0;
#		print "\n" if $dotcounter % 5000 ==0;
# print "dotcounter = $dotcounter\n " if $printer == 1;
		next if $line !~ /^[0-9]+/;
		$dotcounter++;
#		print colored ['green'], "~" x 60, "\n" if $printer == 1;
#		print colored ['green'], $line;# if $printer == 1;
		chomp $line;
		my @fields2 = split(/\t/,$line);
		my $key2 = ();
		my $alignment_no = ();										#1 TEMPORARY
		if ($line =~ /([0-9]+)\s+($focalspec_orig)\s([_\-s0-9a-zA-Z]+)\s([0-9]+)\s([0-9]+)/ ) {
#			$key2 = join("\t",$1, $2,  $4, $5);
			$key2 = join("_",$2, $3,  $4, $5);
#			print "key = $key2\n";

# print "key = $key2\n";
			$alignment_no=$1;
		}
		else {print "seq line $line incompatible\n"; $keynotformedcounter++; next;}
		
		$no_of_species = adjustCoordinates($line);

		$contignotrightcounter++  if $no_of_species != $no;
# print "contignotrightcounter=$contignotrightcounter\n";
# print "no_of_species=$no_of_species\n";
# print "no=$no\n";
		
		next if $no_of_species != $no;
#		print "D: $no_of_species\n";
#		print "E: $no_of_species\n";
		#<STDIN>;
	#	print "key = $key2\n" if $printer == 1;
		my @clusters = ();											#1 EXTRACTING MICROSATS CORRESPONDING TO THIS 
																	#2 ALIGNMENT BLOCK
		if (exists($orths{$key2})){
			@clusters = @{$orths{$key2}};
			$contigsentered++;
			delete $orths{$key2};
		}
		else{
#			 print "orth does not exist\n";
			$keynotfoundcounter++;
			next;
		}
		
		my %sequences=();											#1 WILL STORE SEQUENCES IN THE CURRENT ALIGNMENT BLOCK
		my $humseq = ();
		foreach my $tag (@tags){									#1 READING THE ALIGNMENT FILE AND CAPTURING SEQUENCES
			my $seq = <BO>;											#2 OF ALL SPECIES.
			chomp $seq;
			$sequences{$tag} =  " ".$seq;
			#print "sequences = $sequences{$tag}\n" if $printer == 1;
			$humseq = $seq if $tag =~ /H/;
		}
		
		
		foreach my $cluster (@clusters){							#1 NOW, GOING THROUGH THE CLUSTER OF MICROSATS
# print "x" x 60, "\n" if $printer == 1;
#			print colored ['red'],"cluster = $cluster\n";
			$largesttree =~ s/hg18/H/g;
			$largesttree =~ s/panTro2/C/g;
			$largesttree =~ s/ponAbe2/O/g;
			$largesttree =~ s/rheMac2/R/g;
			$largesttree =~ s/calJac1/M/g;

			$microreadcounter++;
			my @micros = split(/>/,$cluster);
			
			
			
			
			
			
			shift @micros;
	
			my $edge_microsat=0;									#1 THIS WILL HAVE VALUE "1" IF MICROSAT IS FOUND
																	#2 TO BE TOO CLOSE TO THE EDGES OF ALIGNMENT BLOCK
			
			my @starts= ();	my %start_hash=();						#1 STORES THE START AND END COORDINATES OF MICROSATELLITES
			my @ends = ();	my %end_hash=();						#2 SO THAT LATER, WE WILL BE ABLE TO FIND THE EXTREME 
																	#3 COORDINATE VALUES OF THE ORTHOLOGOUS MIROSATELLITES.
			
			my %microhash=();
			my %microsathash=();
			my %nonmicrosathash=();
			my $motif=();											#1 BASIC MOTIF OF THE MICROSATELLITE.. THERE'S ONLY 1
# print "tags=@tags\n";
			for my $i (0 ... $#tags){								#1	FINDING THE MICROSAT, AND THE ALIGNMENT SEQUENCE
																	#2	CORRESPONDING TO THE PARTICULAR SPECIES (AS PER 
																	#3	THE VARIABLE $TAG;
				my $tag = $tags[$i];
			#		print $seq;
				my $locus="NULL";										#1	THIS WILL STORE THE MICROSAT OF THIS SPECIES.
																		#2	IF THERE IS NO MICROSAT, IT WILL REMAIN "NULL"
					
				foreach my $micro (@micros){	
				#	print "micro=$micro, tag=$tag\n";
					if ($micro =~ /^$tag/){								#1	MICROSAT OF THIS SPECIES FOUND..
						$locus  = $micro;
						my @fields = split(/\t/,$micro);
						$motif = $fields[$motifcord];
						$microsathash{$tag}=$fields[$microsatcord];
				#		print "fields=@fields, and startcord=$startcord = $fields[$startcord]\n";
						push(@starts, $fields[$startcord]);
						push(@ends, $fields[$endcord]);
						$start_hash{$tag}=$fields[$startcord];
						$end_hash{$tag}=$fields[$endcord];
						last;
					}
					else{$microsathash{$tag}="NULL"}
				}
				$microhash{$tag}=$locus;
		
			}	
			
			
			
			my $extreme_start  = smallest_number(@starts);		#1 THESE TWO ARE THE EXTREME COORDINATES OF THE 
			my $extreme_end  = largest_number(@ends);			#2 MICROSAT CLUSTER ACCROSS ALL THE SPECIES IN 
																#3 WHOM IT IS FOUND TO BE ORTHOLOGOUS.
			
#			print "starts=@starts... ends=@ends\n";
				
			my %up_flanks = ();									#1	CONTAINS UPSTEAM FLANKING REGIONS FOR EACH SPECIES
			my %down_flanks = ();								#1	CONTAINS DOWNDTREAM FLANKING REGIONS FOR EACH SPECIES
			
			my %up_largeflanks = ();
			my %down_largeflanks = ();
			
			my %locusandflanks = ();
			my %locusandlargeflanks = ();			
			
			my %up_internal_flanks=();							#1	CONTAINS SEQUENCE BETWEEN THE $extreme_start and the 
																#2	ACTUAL START OF MICROSATELLITE IN THE SPECIES
			my %down_internal_flanks=();						#1	CONTAINS SEQUENCE BETWEEN THE $extreme_end and the 
																#2	ACTUAL end OF MICROSATELLITE IN THE SPECIES
			
			my %alignment=();									#1 CONTAINS ACTUAL ALIGNMENT SEQUENCE BETWEEN THE TWO
																#2 EXTEME VALUES.
			
			my %microsatstarts=();										#1 WITHIN EACH ALIGNMENT, IF THERE EXISTS A MICROSATELLITE
																#2 THIS HASH CONTAINS THE START SITE OF THE MICROSATELLITE
																#3 WIHIN THE ALIGNMENT
			next if !defined $extreme_start;
			next if !defined $extreme_end;
			next if $extreme_start > length($sequences{$tags[0]});
			next if $extreme_start < 0;
			next if $extreme_end > length($sequences{$tags[0]});
			
			for my $i (0 ... $#tags){							#1 NOW THAT WE HAVE GATHERED INFORMATION REGARDING
																#2 SEQUENCE ALIGNMENT AND MICROSATELLITE COORDINATES
																#3 AS WELL AS THE EXTREME COORDINATES OF THE 
																#4 MICROSAT CLUSTER, WE WILL PROCEED TO EXTRACT THE
																#5 FLANKING SEQUENCE OF ALL ORGS, AND STUDY IT IN 
																#6 MORE DETAIL.
				my $tag = $tags[$i];		
#				print "tag=$tag.. seqlength = ",length($sequences{$tag})," extreme_start=$extreme_start and extreme_end=$extreme_end\n";
				my $upstream_gaps = (substr($sequences{$tag}, 0, $extreme_start) =~ s/\-/-/g);		#1	NOW MEASURING THE NUMBER OF GAPS IN THE UPSTEAM 
																										#2	AND DOWNSTREAM SEQUENCES OF THE MICROSATs IN THIS
																										#3	CLUSTER.
	
				my $downstream_gaps = (substr($sequences{$tag}, $extreme_end) =~ s/\-/-/g);
				if (($extreme_start - $upstream_gaps )< $EDGE_DISTANCE || (length($sequences{$tag}) - $extreme_end - $downstream_gaps) <  $EDGE_DISTANCE){
					$edge_microsat=1;
					
					last;
				}
				else{
					$up_flanks{$tag} = substr($sequences{$tag}, $extreme_start - $FLANK_SUPPORT, $FLANK_SUPPORT);
					$down_flanks{$tag} = substr($sequences{$tag}, $extreme_end+1, $FLANK_SUPPORT);

					$up_largeflanks{$tag} = substr($sequences{$tag}, $extreme_start - $COMPLEXITY_SUPPORT, $COMPLEXITY_SUPPORT);
					$down_largeflanks{$tag} = substr($sequences{$tag}, $extreme_end+1, $COMPLEXITY_SUPPORT);


					$alignment{$tag} = substr($sequences{$tag}, $extreme_start, $extreme_end-$extreme_start+1);
					$locusandflanks{$tag} = $up_flanks{$tag}."[".$alignment{$tag}."]".$down_flanks{$tag};
					$locusandlargeflanks{$tag} = $up_largeflanks{$tag}."[".$alignment{$tag}."]".$down_largeflanks{$tag};
					
					if ($microhash{$tag} ne "NULL"){
						$up_internal_flanks{$tag} = substr($sequences{$tag}, $extreme_start , $start_hash{$tag}-$extreme_start);
						$down_internal_flanks{$tag} = substr($sequences{$tag}, $end_hash{$tag} , $extreme_end-$end_hash{$tag});
						$microsatstarts{$tag}=$start_hash{$tag}-$extreme_start;
#						print "tag = $tag, internal flanks = $up_internal_flanks{$tag} and $down_internal_flanks{$tag} and start = $microsatstarts{$tag}\n" if $printer == 1;
					}
					else{
						$nonmicrosathash{$tag}=substr($sequences{$tag}, $extreme_start, $extreme_end-$extreme_start+1);
					
					}
			#		print "up flank for species $tag = $up_flanks{$tag} \ndown flank for species $tag = $down_flanks{$tag} \n" if $printer == 1;
										
				}
	
			}
			$nextcounter[11]++  if $edge_microsat==1;
			next if $edge_microsat==1;
			
			
			my $low_complexity = 0; 								#1 VALUE WILL BE 1 IF ANY OF THE FLANKING REGIONS
																	#2 IS FOUND TO BE OF LOW COMPLEXITY, BY USING THE
																	#3 FUNCTION sub test_complexity
			
			
			for my $i (0 ... $#tags){
#				print "i = $tags[$i]\n" if $printer == 1;
				if (test_complexity($up_largeflanks{$tags[$i]}, $COMPLEXITY_SUPPORT) eq "LOW" || test_complexity($down_largeflanks{$tags[$i]}, $COMPLEXITY_SUPPORT) eq "LOW"){
#					print "i = $i, low complexity regions: $up_largeflanks{$tags[$i]}: ",test_complexity($up_largeflanks{$tags[$i]}, $COMPLEXITY_SUPPORT), "  and $down_largeflanks{$tags[$i]} = ",test_complexity($down_largeflanks{$tags[$i]}, $COMPLEXITY_SUPPORT),"\n" if $printer == 1;
					$low_complexity =1; last;
				}
			}
			
			$nextcounter[12]++  if $low_complexity==1;
			next if $low_complexity == 1;
			
			
			my $sequence_dissimilarity = 0;										#1 THIS VALYE WILL BE 1 IF THE SEQUENCE SIMILARITY
																	#2 BETWEEN ANY OF THE SPECIES AGAINST THE HUMAN
																	#3 FLANKING SEQUENCES IS BELOW A CERTAIN THRESHOLD
																	#4 AS DESCRIBED IN FUNCTION sub sequence_similarity
			my %donepair = ();
			for my $i (0 ... $#tags){
			#	print "i = $tags[$i]\n" if $printer == 1;
#				next if $i == 0;
			#	print colored ['magenta'],"THIS IS UP\n" if $printer == 1;

				for my $b (0 ... $#tags){
					next if $b == $i;
					my $pair = ();
					$pair = $i."_".$b if $i < $b;
					$pair = $b."_".$i if $b < $i;
					next if exists $donepair{$pair};
					my ($up_similarity,$upnucdiffs, $upindeldiffs) = sequence_similarity($up_flanks{$tags[$i]}, $up_flanks{$tags[$b]}, $SIMILARITY_THRESH, $info);
					my ($down_similarity,$downnucdiffs, $downindeldiffs) = sequence_similarity($down_flanks{$tags[$i]}, $down_flanks{$tags[$b]}, $SIMILARITY_THRESH, $info);				
					$donepair{$pair} = $up_similarity."_".$down_similarity;
					
#					print RUN "$up_similarity	$upnucdiffs	$upindeldiffs	$down_similarity	$downnucdiffs	$downindeldiffs\n";
					
					if ( $up_similarity < $SIMILARITY_THRESH || $down_similarity < $SIMILARITY_THRESH){
						$sequence_dissimilarity =1; 
						last;
					}
				}
			}
			$nextcounter[13]++  if $sequence_dissimilarity==1;

			next if $sequence_dissimilarity == 1;
			my ($simplified_microsat, $Hchrom, $Hstart, $Hend, $locusmotif, $locusmotifsize) = summarize_microsat($cluster, $humseq);
#			print "simplified_microsat=$simplified_microsat\n"; 
			my ($tree_analysis,  $conformation) = treeStudy($simplified_microsat);
# print "tree_analysis = $tree_analysis .. conformation=$conformation\n"; 
			#<STDIN>;
			
			print SELECT "\"$conformation\"\t$tree_analysis\n";
			
			next if $tree_analysis =~ /DISCARD/;
			if (exists $treesToReject{$tree_analysis}){
				$nextcounter[14]++;
				next;
			}

#			print "F: $no_of_species\n";

# 			my $adjuster=();
# 			if ($no_of_species == 4){
# 				my @sields = split(/\t/,$simplified_microsat);
# 				my $somend = pop(@sields);
# 				my $somestart = pop(@sields);
# 				my $somechr = pop(@sields);
# 				$adjuster = "NA\t" x 13 ;
# 				$simplified_microsat = join ("\t", @sields, $adjuster).$somechr."\t".$somestart."\t".$somend;
# 			}
# 			if ($no_of_species == 3){
# 				my @sields = split(/\t/,$simplified_microsat);
# 				my $somend = pop(@sields);
# 				my $somestart = pop(@sields);
# 				my $somechr = pop(@sields);
# 				$adjuster = "NA\t" x 26 ;
# 				$simplified_microsat = join ("\t", @sields, $adjuster).$somechr."\t".$somestart."\t".$somend;
# 			}
# 			
			$registeredTrees{$tree_analysis} = 1 if !exists $registeredTrees{$tree_analysis};
			$registeredTrees{$tree_analysis}++ if exists $registeredTrees{$tree_analysis};
				
			if (exists $treesToIgnore{$tree_analysis}){
				my @appendarr = ();

#				print SUMMARY $Hchrom,"\t",$Hstart,"\t",$Hend,"\t",$locusmotif,"\t",$locusmotifsize,"\t", $thresharr[$locusmotifsize], "\t", $simplified_microsat,"\t", $tree_analysis,"\t", join("",@tags), "\t";
				#print "SUMMARY ",$Hchrom,"\t",$Hstart,"\t",$Hend,"\t",$locusmotif,"\t",$locusmotifsize,"\t", $thresharr[$locusmotifsize], "\t", $simplified_microsat,"\t", $tree_analysis,"\t", join("",@tags), "\t";
#				print SELECT $Hchrom,"\t",$Hstart,"\t",$Hend,"\t","NOEVENT", "\t\t", $cluster,"\n";
				
				foreach my $lnode (@$lagestnodes){
					my @pair = @$lnode;
					my @nodemutarr = ();
					for my $p (@pair){
						my @mutinfoarray1 = ();
						for (1 ... 38){
#							push (@mutinfoarray1, "NA")
						}
#						print SUMMARY join ("\t", @mutinfoarray1[0...($#mutinfoarray1)] ),"\t"; 			
#						print  join ("\t", @mutinfoarray1[0...($#mutinfoarray1)] ),"\t"; 			
					}
	
				}
				for (1 ... 38){
					push (@appendarr, "NA")
				}
#				print SUMMARY join ("\t", @appendarr,"NULL", "NULL"),"\n"; 
#				print  join ("\t", @appendarr,"NULL", "NULL"),"\n"; 
		#		print "SUMMARY ",join ("\t", @appendarr,"NULL", "NULL"),"\n"; #<STDIN>;
				next;
			}
#			print colored ['blue'],"cluster = $cluster\n";
			
			my ($mutations_array, $nodes, $branches_hash, $alivehash, $primaryalignment) = peel_onion($tree, \%sequences, \%alignment, \@tags, \%microsathash, \%nonmicrosathash, $motif, $tree_analysis, $thresholdhash{length($motif)}, \%microsatstarts);
	
			if ($mutations_array eq "NULL"){
			#	print "cluster = $cluster \n"; <STDIN>;
				my @appendarr = ();

			#	print SUMMARY $Hchrom,"\t",$Hstart,"\t",$Hend,"\t",$locusmotif,"\t",$locusmotifsize, "\t";

			#	foreach my $lnode (@$lagestnodes){
			#		my @pair = @$lnode;
			#		my @nodemutarr = ();
			#		for my $p (@pair){
			#			my @mutinfoarray1 = ();
			#			for (1 ... 38){
			#				push (@mutinfoarray1, "NA")
			#			}
			#			print SUMMARY join ("\t", @mutinfoarray1[0...($#mutinfoarray1)] ),"\t"; 			
			#			print  join ("\t", @mutinfoarray1[0...($#mutinfoarray1)] ),"\t"; 			
			#		}
			#	}
			#	for (1 ... 38){
			#		push (@appendarr, "NA")
			#	}
			#	print SUMMARY join ("\t", @appendarr,"NULL", "NULL"),"\n"; 
			#	print  join ("\t", @appendarr,"NULL", "NULL"),"\n"; 
			#	print  join ("\t","SUMMARY", @appendarr,"NULL", "NULL"),"\n"; #<STDIN>;
				next;
			}
			
			
#			print "sent: \n" if $printer == 1;
#			print "nodes = @$nodes,  branches array:\n" if $mutations_array ne "NULL" &&  $printer == 1;

			my ($newstatus, $newmutations_array, $newnodes, $newbranches_hash, $newalivehash, $finalalignment) = fillAlignmentGaps($tree, \%sequences, \%alignment, \@tags, \%microsathash, \%nonmicrosathash, $motif, $tree_analysis, $thresholdhash{length($motif)}, \%microsatstarts);
#			print "newmutations_array returned = \n",join("\n",@$newmutations_array),"\n" if $newmutations_array ne "NULL" &&  $printer == 1;
			my @finalmutations_array= ();
			@finalmutations_array = selectMutationArray($mutations_array, $newmutations_array, \@tags, $alivehash, \%alignment, $motif) if $newmutations_array ne "NULL";
			@finalmutations_array = selectMutationArray($mutations_array, $mutations_array, \@tags, $alivehash, \%alignment, $motif) if $newmutations_array eq "NULL";
# print "alt = $alternate{$conformation}\n";

			my ($besttree, $treescore) = selectBetterTree($tree_analysis, $alternate{$conformation}, \@finalmutations_array);
			my $cleancase = "UNCLEAN";
			$cleancase = checkCleanCase($besttree, $finalalignment) if $treescore > 0 && $finalalignment ne "NULL" && $finalalignment =~ /\!/;
			$cleancase = checkCleanCase($besttree, $primaryalignment) if $treescore > 0 && $finalalignment eq "NULL" && $primaryalignment =~ /\!/ && $primaryalignment ne "NULL";
			$cleancase = "CLEAN" if $finalalignment eq "NULL" && $primaryalignment !~ /\!/ && $primaryalignment ne "NULL";
			$cleancase = "CLEAN" if $finalalignment ne "NULL" && $finalalignment !~ /\!/ ;
# print "besttree = $besttree ... cleancase=$cleancase\n"; #<STDIN>;

			my @selects = ("-C","+C","-H","+H","-HC","+HC","-O","+O","-H.-C","-H.-O","-HC,+C","-HC,+H","-HC.-O","-HCO,+HC","-HCO,+O","-O.-C","-O.-H",
			"+C.+O","+H.+C","+H.+O","+HC,-C","+HC,-H","+HC.+O","+HCO,-C","+HCO,-H","+HCO,-HC","+HCO,-O","+O.+C","+O.+H","+H.+C.+O","-H.-C.-O","+HCO","-HCO");
			next if (oneOf(@selects, $besttree) == 0);
			if ( ($besttree =~ /,/ || $besttree =~ /\./) && $cleancase eq "UNCLEAN"){
				$besttree = "$besttree / $tree_analysis";				
			}

			$besttree = "NULL" if $treescore <= 0;
			
			while ($besttree =~ /[A-Z][A-Z]/){
				$besttree =~ s/([A-Z])([A-Z])/$1:$2/g;
			}
			
			if ($besttree !~ /NULL/){			
				my @elements = ($besttree =~ /([A-Z])/g);
				
				foreach my $ele (@elements){
#					 print "replacing $ele with $backReplacementArrTag{$ele}\n";
					$besttree =~ s/$ele/$backReplacementArrTag{$ele}/g if exists $backReplacementArrTag{$ele};
				}
			}
			my $endendstate = $focalspec_orig.".".$Hchrom."\t".$Hstart."\t".$Hend."\t".$locusmotif."\t".$locusmotifsize."\t".$tree_analysis."\t";
			next if $endendstate =~ /NA\tNA\tNA/;
			
			print SUMMARY $focalspec_orig,".",$Hchrom,"\t",$Hstart,"\t",$Hend,"\t",$locusmotif,"\t",$locusmotifsize,"\t";
# print "SUMMARY\t", $focalspec_orig,".",$Hchrom,"\t",$Hstart,"\t",$Hend,"\t",$locusmotif,"\t",$locusmotifsize,"\t",$tree_analysis,"\t" ;
			
			my @mutinfoarray =();
			
			foreach my $lnode (@$lagestnodes){
				my @pair = @$lnode;
				my $joint = "(".join(", ",@pair).")";
				my @nodemutarr = ();

				for my $p (@pair){
						foreach my $mut (@finalmutations_array){
						$mut =~ /node=([A-Z, \(\)]+)/;
						push @nodemutarr, $mut if $p eq $1;
					}
					@mutinfoarray = summarizeMutations(\@nodemutarr, $besttree);
					
				#	print SUMMARY join ("\t", @mutinfoarray[0...($#mutinfoarray-1)] ),"\t"; 			
				#	print  join ("\t", @mutinfoarray[0...($#mutinfoarray-1)] ),"\t"; 			
				}
			}
			
#			print "G: $no_of_species\n";
			
			my @alignmentarr = ();
			
			foreach my $key (keys %alignment){
				push @alignmentarr, $backReplacementArrTag{$key}.":".$alignment{$key};
				
			}
#			print "alignmentarr = @alignmentarr"; <STDIN>;
			
			@mutinfoarray = summarizeMutations(\@finalmutations_array, $besttree);
			print SUMMARY join ("\t", @mutinfoarray ),"\t"; 			
			print SUMMARY join(",",@alignmentarr),"\n";
#			print join("\t","--------------","\n",$besttree, join("",@tags)),"\n" if scalar(@tags) < 5;
#			<STDIN> if scalar(@tags) < 5;
#			print   $cleancase, "\n";
#			print join ("\t", @mutinfoarray,$cleancase,join(",",@alignmentarr)),"\n"; #<STDIN>; 			
# print "summarized\n"; #<STDIN>;
	
	
	
			my %indelcatch = ();
			my %substcatch = ();
			my %typecatch = ();
			my %nodescatch = ();
			my $mutconcat = join("\t", @finalmutations_array)."\n";
			my %indelposcatch = ();
			my %subsposcatch = ();
			
				foreach my $fmut ( @finalmutations_array){
#					next if $fmut !~ /indeltype=[a-zA-Z]+/;
					#print RUN $fmut, "\n";
					$fmut =~ /node=([a-zA-Z, \(\)]+)/;
					my $lnode = $1;
					$nodescatch{$1}=1;
					
					if ($fmut =~ /type=substitution/){
		#				print "fmut=$fmut\n";
						$fmut =~ /from=([a-zA-Z\-]+)\tto=([a-zA-Z\-]+)/;
						my $from=$1;
		#				print "from=$from\n";
						my $to=$2;
		#				print "to=$to\n";	
						push @{$substcatch{$lnode}} , ("from:".$from." to:".$to);
						$fmut =~ /position=([0-9]+)/;
						push @{$subsposcatch{$lnode}}, $1;
					}
					
					if ($fmut =~ /insertion=[a-zA-Z\-]+/){
						$fmut =~ /insertion=([a-zA-Z\-]+)/;
						push @{$indelcatch{$lnode}} , $1;
						$fmut =~ /indeltype=([a-zA-Z]+)/;
						push @{$typecatch{$lnode}}, $1;
						$fmut =~ /position=([0-9]+)/;
						push @{$indelposcatch{$lnode}}, $1;
					}
					if ($fmut =~ /deletion=[a-zA-Z\-]+/){
						$fmut =~ /deletion=([a-zA-Z\-]+)/;
						push @{$indelcatch{$lnode}} , $1;
						$fmut =~ /indeltype=([a-zA-Z]+)/;
						push @{$typecatch{$lnode}}, $1;
						$fmut =~ /position=([0-9]+)/;
						push @{$indelposcatch{$lnode}}, $1;
					}
				}
							
		#	print  $simplified_microsat,"\t", $tree_analysis,"\t", join("",@tags), "\t" if $printer == 1;
		#	print join ("<\t>", @mutinfoarray),"\n" if $printer == 1; 
		#	print "where mutinfoarray = @mutinfoarray\n"  if $printer == 1;
		#	#print RUN ".";
			
		#	print colored ['red'], "-------------------------------------------------------------\n" if $printer == 1;
		#	print colored ['red'], "-------------------------------------------------------------\n" if $printer == 1;

		#	print colored ['red'],"finalmutations_array=\n" if $printer == 1;
#			foreach (@finalmutations_array) {
#				print colored ['red'], "$_\n" if $_ =~ /type=substitution/ && $printer == 1  ;
#				print colored ['yellow'], "$_\n" if $_ !~ /type=substitution/ && $printer == 1  ;
				
#			}# if $line =~ /cal/;# && $line =~ /chr4/;
			
#			print colored ['red'], "-------------------------------------------------------------\n" if $printer == 1;
#			print colored ['red'], "-------------------------------------------------------------\n" if $printer == 1;
#			print "tree analysis = $tree_analysis\n" if $printer == 1;
			
		#	my $mutations = "@$mutations_array";


			next;
			for my $keys (@$nodes) {foreach my $key (@$keys){
										#print "key = $key, => $branches_hash->{$key}\n";
									} 
								#	print "x" x 50, "\n";
								}
			my ($birth_steps, $death_steps) = decipher_history($mutations_array,join("",@tags),$nodes,$branches_hash,$tree_analysis,$conformation, $alivehash, $simplified_microsat);
		}
	}
	close BO;
# print "now studying where we lost microsatellites:\n";
# print "x" x 60,"\n";
	for my $reason (0 ... $#nextcounter){
#		print $removalReasons[$reason]."\t".$nextcounter[$reason],"\n";
	}
# print "x" x 60,"\n";
# print "In total we read $microreadcounter microsatellites after reading through $contigsentered contigs\n";
# print " we lost $keynotformedcounter contigs as they did not form the key, \n";
# print "$contignotrightcounter contigs as they were not of the right species configuration\n";  
# print "$keynotfoundcounter contigs as they did not contain the microsats\n";  
# print "... In total we went through a file that had $dotcounter contigs...\n";  
#	print join ("\n","remaining orth keys = ", (keys %orths),"");
# print "------   ------   ------   ------   ------   ------   ------   ------   ------   ------   ------   \n";
#	print "now printing counted trees: \n";
		if (scalar(keys %registeredTrees) > 0){
		foreach my $keyb ( sort (keys %registeredTrees) )
		{
#			print "$keyb : $registeredTrees{$keyb}\n";
		}
	}
	
	
}	

close SUMMARY;

my @summarizarr = ("+C=+C +R.+C -HCOR,+C",
"+H=+H +R.+H -HCOR,+H",
"-C=-C -R.-C +HCOR,-C",
"-H=-H -R.-H +HCOR,-H",
"+HC=+HC",
"-HC=-HC",
"+O=+O -HCOR,+O",
"-O=-O +HCOR,-O",
"+HCO=+HCO",
"-HCO=-HCO",
"+R=+R +R.+C +R.+H",
"-R=-R -R.-C -R.-H");

foreach my $line (@summarizarr){
	next if $line !~ /[A-Za-z0-9]/;
#	print $line;
	chomp $line;
	my @fields = split(/=/,$line);
#	print "title = $fields[0]\n";
	my @parts=split(/ +/, $fields[1]);
	my %partshash = ();
	 foreach my $part (@parts){$partshash{$part}=1;}
	my $count=0;	
	foreach my $key ( sort keys %registeredTrees ){
		next if !exists $partshash{$key};
#		print "now adding $registeredTrees{$key} from $key\n";
		$count+=$registeredTrees{$key};
	}
#	print "$fields[0] : $count\n";
}
#--------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------
sub largest_number{
	my $counter = 0;
	my($max) = shift(@_);
    foreach my $temp (@_) {
    	
    	#print "finding largest array: $maxcounter \n";
    	if($temp > $max){
        	$max = $temp;
        }
    }
    return($max);
}

sub smallest_number{
	my $counter = 0;
	my($min) = shift(@_);
    foreach my $temp (@_) {
    	#print "finding largest array: $maxcounter \n";
    	if($temp < $min){
        	$min = $temp;
        }
    }
    return($min);
}
#--------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------
sub baseml_parser{
	my $outputfile = $_[0];
	open(BOUT,"<$outputfile") or die "Cannot open output of upstream baseml $outputfile: $!";
	my @info = ();
	my @branchields = ();
	my @distanceields = ();
	my @bout = <BOUT>;
	#print colored ['red'], @bout ,"\n";
	for my $b (0 ... $#bout){
		my $bine=$bout[$b];
		#print  colored ['yellow'], "sentence = ",$bine;
		if ($bine =~ /TREE/){
			$bine=$bout[$b++];
			$bine=$bout[$b++];
			$bine=$bout[$b++];
			#print "FOUND",$bine;
			chomp $bine;
			$bine =~ s/^\s+//g;
			@branchields = split(/\s+/,$bine);
			$bine=$bout[$b++];
			chomp $bine;
			$bine =~ s/^\s+//g;
			@distanceields = split(/\s+/,$bine);
			#print "LASTING..............\n";
			last;
		}
		else{		
		}
	}
	
	close BOUT;
#			print "branchfields = @branchields and distanceields = @distanceields\n"  if $printer == 1; 
	my %distance_hash=();
	for my $d (0 ... $#branchields){
		$distance_hash{$branchields[$d]} = $distanceields[$d];
	}
	
	$info[0] = $distance_hash{"9..1"} + $distance_hash{"9..2"};
	$info[1] = $distance_hash{"9..1"} + $distance_hash{"8..9"}+ $distance_hash{"8..3"};
	$info[2] = $distance_hash{"9..1"} + $distance_hash{"8..9"}+$distance_hash{"7..8"}+$distance_hash{"7..4"};
	$info[3] = $distance_hash{"9..1"} + $distance_hash{"8..9"}+$distance_hash{"7..8"}+$distance_hash{"6..7"}+$distance_hash{"6..5"};
	
#	print "\nsending back: @info\n" if $printer == 1;
	
	return join("\t",@info);
	
}


#--------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------
sub test_complexity{
	my $printer = 0;
	my $sequence = $_[0];
	#print "sequence = $sequence\n";
	my $COMPLEXITY_SUPPORT = $_[1];
	my $complexity=int($COMPLEXITY_SUPPORT * (1/40));				#1	THIS IS AN ARBITRARY THRESHOLD SET FOR LOW COMPLEXITY.
																	#2	THE INSPIRATION WAS WEB MILLER'S MAIL SENT ON 
																	#3	19 Apr 2008 WHERE HE CLASSED AS HIGH COMPLEXITY
																	#4	REGION, IF 40 BP OF SEQUENCE HAS AT LEAST 3 OF
																	#5	EACH NUCLEOTIDE. HENCE, I NORMALIZE THIS PARAMETER
																	#6	FOR THE ACTUAL LENGTH OF $FLANK_SUPPORT SET BY
																	#7	THE USER.
																	#8	WEB MILLER SENT THE MAIL TO YDK104@PSU.EDU
	
	
	
	my $As = ($sequence=~ s/A/A/gi);
	my $Ts = ($sequence=~ s/T/T/gi);
	my $Gs = ($sequence=~ s/G/G/gi);
	my $Cs = ($sequence=~ s/C/C/gi);
	my $dashes = ($sequence=~ s/\-/-/gi);
	$dashes = 0 if $sequence !~ /\-/;
# print "seq = $sequence, As=$As, Ts=$Ts, Gs=$Gs, Cs=$Cs, dashes=$dashes\n";
	return "LOW" if $dashes > length($sequence)/2;
	
	my $ans = ();

	return "HIGH" if $As >= $complexity && $Ts >= $complexity && $Cs >= $complexity && $Gs >= $complexity;

	my @nts = ("A","T","G","C","-");
	
	my $lowcomplex = 0;
	
	foreach my $nt (@nts){
		$lowcomplex =1 if $sequence =~ /(($nt\-*){$mono_flanksimplicityRepno,})/i;
		$lowcomplex =1 if $sequence =~ /(($nt[A-Za-z]){$di_flanksimplicityRepno,})/i;
		$lowcomplex =1 if $sequence =~ /(([A-Za-z]$nt){$di_flanksimplicityRepno,})/i;
		my $nont = ($sequence=~ s/$nt/$nt/gi);
		$lowcomplex = 1 if $nont > (length($sequence)  * $prop_of_seq_allowedtoAT) && ($nt =~ /[AT\-]/);
		$lowcomplex = 1 if $nont > (length($sequence)  * $prop_of_seq_allowedtoCG) && ($nt =~ /[CG]/);
	}
#	print "leaving for now.. $sequence\n" if $printer == 1 && $lowcomplex == 0;
	#<STDIN>;
	return "HIGH" if $lowcomplex == 0;
	return "LOW" ;
}
#--------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------
sub sequence_similarity{
	my $printer = 0;
	my @seq1 = split(/\s*/, $_[0]);
	my @seq2 = split(/\s*/, $_[1]);
	my $similarity_thresh = $_[2];
	my $info = $_[3];
#	print "input = @_\n" if $printer == 1;
	my $seq1str = $_[0];
	my $seq2str = $_[1];
	$seq1str=~s/\-//g; 	$seq2str=~s/\-//g;
	my $similarity=0;
	
	my $nucdiffs=0;
	my $nucsims=0;
	my $indeldiffs=0;
	
	for my $i (0...$#seq1){
		$similarity++ if $seq1[$i] =~ /$seq2[$i]/i  ; #|| $seq1[$i] =~ /\-/i || $seq2[$i] =~ /\-/i ;
		$nucsims++ if $seq1[$i] =~ /$seq2[$i]/i && ($seq1[$i] =~ /[a-zA-Z]/i && $seq2[$i] =~ /[a-zA-Z]/i);
		$nucdiffs++ if $seq1[$i] !~ /$seq2[$i]/i && ($seq1[$i] =~ /[a-zA-Z]/i && $seq2[$i] =~ /[a-zA-Z]/i);
		$indeldiffs++ if $seq1[$i] !~ /$seq2[$i]/i && $seq1[$i] =~ /\-/i || $seq2[$i] =~ /\-/i;
	}
	my $sim = $similarity/length($_[0]);
	return ( $sim, $nucdiffs, $indeldiffs ); #<=  $similarity_thresh;
}
#--------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------

sub load_treesToReject{
	my @rejectlist = ();
	my $alltags = join("",@_);
	@rejectlist = qw (-HCOR +HCOR) if $alltags eq "HCORM";
	@rejectlist = qw ( -HCO|+R +HCO|-R) if $alltags eq "HCOR";
	@rejectlist = qw ( -HC|+O +HC|-O) if $alltags eq "HCO";

	%treesToReject=();
	$treesToReject{$_} = $_ foreach (@rejectlist);
	#print "loaded to reject for $alltags; ", $treesToReject{$_},"\n" foreach (@rejectlist); #<STDIN>;
}
#--------------------------------------------------------------------------------------------------------
sub load_treesToIgnore{
	my @rejectlist = ();
	my $alltags = join("",@_);
	@rejectlist = qw (-HCOR +HCOR +HCORM -HCORM) if $alltags eq "HCORM";
	@rejectlist = qw ( -HCO|+R +HCO|-R +HCOR -HCOR) if $alltags eq "HCOR";
	@rejectlist = qw ( -HC|+O +HC|-O +HCO -HCO) if $alltags eq "HCO";

	%treesToIgnore=();
	$treesToIgnore{$_} = $_ foreach (@rejectlist);
	#print "loaded ", $treesToIgnore{$_},"\n" foreach (@rejectlist);
}
#--------------------------------------------------------------------------------------------------------
sub load_thresholds{
	my @threshold_array=split(/[,_]/,$_[0]);
	unshift @threshold_array, "0";
	for my $size (1 ... 4){
		$thresholdhash{$size}=$threshold_array[$size];
	}
}
#--------------------------------------------------------------------------------------------------------
sub load_allPossibleTrees{
	#1 THIS FILE STORES ALL POSSIBLE SCENARIOS OF MICROSATELLITE
	#2 BIRTH AND DEATH EVENTS ON A 5-PRIMATE TREE OF H,C,O,R,M
	#3 IN FORM OF A TEXT FILE. THIS WILL BE USED AS A TEMPLET
	#4 TO COMPARE EACH MICROSATELLITE CLUSTER TO UNDERSTAND THE
	#5 EVOLUTION OF EACH LOCUS. WE WILL THEN DISCARD SOME 
	#6 MICROSATS ACCRODING TO THEIR EVOLUTIONARY BEHAVIOUR ON 
	#7 THE TREE. MOST PROBABLY WE WILL REMOVE THOSE MICROSATS
	#8 THAT ARE NOT SUFFICIENTLY INFORMATIVE, LIKE IN CASE OF
	#9 AN OUTGROUP MICROSATELLITE BEING DIFFERENT FRON ALL OTHER
	#10 SPECIES IN THE TREE.
	my $tree_list = $_[0];	
#	print "file to be loaded: $tree_list\n";

	my @trarr = ();
	@trarr = ("#H C O	CONCLUSION	ALTERNATE",
"+ + +	+HCO	NA",
"+ _ _	+H	NA",
"_ + _	+C	NA",
"_ _ +	-HC|+O	NA",
"+ _ +	-C	+H",
"_ + +	-H	+C",
"+ + _	+HC|-O	NA",
"_ _ _	-HCO	NA") if $tree_list =~ /_HCO\.txt/;
	@trarr = ("#H C O R	CONCLUSION	ALTERNATE",
"_ _ _ _	-HCOR	NA",
"+ + + +	+HCOR	NA",
"+ + + _	+HCO|-R	+H.+C.+O",
"+ + _ _	+HC	+H.+C;-O",
"+ _ _ _	+H	+HC,-C;+HC,-C",
"_ + _ _	+C	+HC,-H;+HC,-H",
"_ _ + _	+O	-HC|-H.-C",
"_ _ + +	-HC	-H.-C",
"+ _ _ +	+H|-C.-O	+HC,-C",
"_ + _ +	+C	-H.-O",
"_ + + _	-H	+C.+O",
"_ _ _ +	-HCO|+R	NA",
"+ _ + _	+H.+O|-C	NA",
"_ + + +	-H	-HC,+C",
"+ _ + +	-C	-HC,+H",
"+ + _ +	-O	+HC") if $tree_list =~ /_HCOR\.txt/;

		@trarr = ("#H C O R M	CONCLUSION	ALTERNATE",
"+ + _ + +	-O	-HCO,+HC|-HCO,+HC;-HCO,(+H.+C)",
"+ _ + + +	-C	-HC,+H;+HCO,(+H.+O)",
"_ + + + +	-H	-HC,+C;-HCO,(+C.+O)",
"_ _ + _ _	+O	+HCO,-HC;+HCO,(-H.-C)",
"_ + _ _ _	+C	+HC,-H;+HCO,(-H.-O)",
"+ _ _ _ _	+H	+HC,-C;+HCO,(-C.-O)",
"+ + + _ _	+HCO	+H.+C.+O",
"_ _ _ + +	-HCO	-HC.-O;-H.-C.-O",
"+ _ _ + +	-O.-C|-HCO,+H	+R.+H;-HCO,(+R.+H)",
"_ + _ + +	-O.-H|-HCO,+C	+R.+C;-HCO,(+R.+C)",
"_ + + _ _	+HCO,-H|+O.+C	NA",
"+ _ + _ _	+HCO,-C|+O.+H	NA",
"_ _ + + +	-HC	-H.-C|-HCO,+O",
"+ + _ _ _	+HC	+H.+C|+HCO,-O|-HCO,+HC;-HCO,(+H.+C)",
"+ + + + +	+HCORM	NA",
"_ _ + _ +	DISCARD	+O;+HCO,-HC;+HCO,(-H.-C)",
"_ + _ _ +	+C	+HC,-H;+HCO,(-H.-O)",
"+ _ _ _ +	+H	+HC,-C;+HCO,(-C.-O)",
"+ + _ _ +	+HC	-R.-O|+HCO,-O|+H.+C;-HCO,+HC;-HCO,(+H.+C)",
"+ _ + _ +	DISCARD	-R.-C|+HCO,-C|+H.+O	NA",
"_ + + _ +	DISCARD	-R.-H|+HCO,-H|+C.+O	NA",
"_ _ _ _ +	DISCARD	-HCOR	NA",
"_ _ _ + _	DISCARD	+R;-HC.-O;-H.-C.-O",
"+ + _ + _	-O	+R.+HC|-HCO,+HC;+H.+C.+R|-HCO,(+H.+C)",
"+ + + + _	+HCOR	NA",
"+ + + _ +	DISCARD	-R;+HCO;+HC.+O;+H.+C.+O",
"+ _ + + _	-C	-HC,+H;+H.+O.+R|-HCO,(+H.+O)",
"_ + + + _	-H	-HC,+C;+C.+O.+R|-HCO,(+C.+O)",
"_ _ + + _	-HC	+R.+O|-HCO,+O|+HCO,-HC",
"_ + _ + _	+C	+R.+C|-HCO,+C|-HC,+C	+HCO,(-H.-O)",
"+ _ _ + _	+H	+R.+H|-C.-O	+HCO,(-C.-O)"
) if $tree_list =~ /_HCORM\.txt/;

	
	my $template_p = $_[1];
	my $alternate_p = $_[2];
																	#1 THIS IS THE HASH IN WHICH INFORMATION FROM THE ABOVE FILE
																	#2 GETS STORED, USING THE WHILE LOOP BELOW. HERE, THE KEY
																	#3 OF EACH ROW IS THE EVOLUTIONARY CONFIGURATION OF A LOCUS
																	#4 ON THE PRIMATE TREE, BASED ON PRESENCE/ABSENCE OF A MICROSAT
																	#5 AT THAT LOCUS, LIKE SAY "+ + + _ _" .. EACH COLUMN BELONGS 
																	#6 TO ONE SPECIES; HERE THE COLUMN NAMES ARE "H C O R M".
																	#7 THE VALUE FOR EACH ENTRY IS THE MEANING OF THE ABOVE 
																	#8 CONFIGURATION (I.E., CONFIGURAION OF THE KEY. HERE, THE
																	#9 VALUE WILL BE +HCO, SIGNIFYING A BIRTH IN HUMAN-CHIMP-ORANG
																	#10 COMMON ANCESTOR. THIS HASH HAS BEEN LOADED HERE TO BE USED
																	#11 LATER BY THE SUBROUTINE sub treeStudy{} THAT STUDIES
																	#12 EVOLUTIONARY CONFIGURAION OF EACH MICROSAT LOCUS, AS
																	#13 MENTIONED ABOVE.	
	my @keys_array=();
	foreach my $line (@trarr){
#		print $line,"\n";
		next if $line =~ /^#/;
		chomp $line;
		my @fields = split("\t", $line);
		push @keys_array, $fields[0];
#		print "loading: $fields[0]\n";
		$template_p->{$fields[0]}[0] = $fields[1];
		$template_p->{$fields[0]}[1] = 0;
		$alternate_p->{$fields[0]} = $fields[2];
#		$alternate_p->{$fields[1]} = $fields[2];
# print "loading alternate_p $fields[1] $fields[2]\n"; #<STDIN> if $fields[1] eq "+H";
	}
#	print "loaded the trees with keys: @keys_array\n";
	return $template_p, \@keys_array, $alternate_p;
}

#--------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------
sub checkCleanCase{
	my $printer = 0;
	my $tree = $_[0];
	my $finalalignment = $_[1];
	
	#print "IN checkCleanCase: @_\n";
	#<STDIN>;
	my @indivspecies = $tree =~ /[A-Z]/g;
	$finalalignment =~ s/\./_/g;
	my @captured = $finalalignment =~ /[A-Za-z, \(\):]+\![:A-Za-z, \(\)]/g;
	
	my $unclean = 0;
	
	foreach my $sp (@indivspecies){
		foreach my $cap (@captured){
			$cap =~ s/:[A-Za-z\-]+//g;
			my @sps = $cap =~ /[A-Z]+/g;		
			my $spsc = join("", @sps);
#			print "checking whether imp species $sp is present in $cap i.e, in $spsc\n " if $printer == 1;
			if ($spsc =~ /$sp/){
#				print "foind : $sp\n";
				$unclean = 1; last;
			}
		}
		last if $unclean == 1;
	}
	#<STDIN>;
	return "CLEAN" if $unclean == 0;
	return "UNCLEAN";
}

#--------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------
#--------------------------------------------------------------------------------------------------------


sub adjustCoordinates{
	my $line = $_[0];
	return 0 if !defined $line;
	#print "------x------x------x------x------x------x------x------x------\n";
	#print $line,"\n\n";
	my $no_of_species = $line =~ s/(chr[0-9a-zA-Z]+)|(Contig[0-9a-zA-Z\._\-]+)|(scaffold[0-9a-zA-Z\._\-]+)|(supercontig[0-9a-zA-Z\._\-]+)/x/ig;
	#print $line,"\n";
	#print "------x------x------x------x------x------x------x------x------\n\n\n";
#	my @got = ($line =~ s/(chr[0-9a-zA-Z]+)|(Contig[0-9a-zA-Z\._\-]+)/x/g);
# print "line = $line\n";
	$infocord = 2 + (4*$no_of_species) - 1;
	$typecord = 2 + (4*$no_of_species) + 1 - 1;
	$motifcord = 2 + (4*$no_of_species) + 2 - 1;
	$gapcord = $motifcord+1;
	$startcord = $gapcord+1;
	$strandcord = $startcord+1;
	$endcord = $strandcord + 1;
	$microsatcord = $endcord + 1;
	$sequencepos = 2 + (5*$no_of_species) + 1 -1 ; 
	$interr_poscord = $microsatcord + 3;
	$no_of_interruptionscord = $microsatcord + 4;
	$interrcord = $microsatcord + 2;
#	print "$line\n startcord = $startcord, and endcord = $endcord and no_of_species = $no_of_species\n" if $line !~ /calJac/i;
	
	return $no_of_species;
}


sub printhash{
	my $alivehash = $_[0];
	my @tags = @$_[1];
#	print "print hash\n";
	foreach my $tag (@tags){
#		print "$tag=",$alivehash->{$tag},"\n" if exists $alivehash->{$tag};
	}
		
	return "\n"
}
sub peel_onion{
	my $printer = 0;
#	print "received: @_\n" ; #<STDIN>;
	$printer = 0;
	my ($tree, $sequences, $alignment, $tagarray, $microsathash, $nonmicrosathash, $motif, $tree_analysis, $threshold, $microsatstarts) = @_;
#	print "in peel onion.. tree = $tree \n" if $printer == 1;
	my %sequence_hash=();


#	for my $i (0 ... $#sequences){ $sequence_hash{$species[$i]}=$sequences->[$i]; }


	my %node_sequences=();
	
	my %node_alignments = ();			#NEW, Nov 28 2008
	my @tags=();
	my @locus_sequences=();
	my %alivehash=();
	foreach my $tag (@$tagarray) { 
		#print "adding: $tag\n";
		push(@tags, $tag);
		$node_sequences{$tag}=join ".",split(/\s*/,$microsathash->{$tag}) if $microsathash->{$tag} ne "NULL"; 
		$alivehash{$tag}= $tag if $microsathash->{$tag} ne "NULL";
		$node_sequences{$tag}=join ".",split(/\s*/,$nonmicrosathash->{$tag}) if $microsathash->{$tag} eq "NULL";
		$node_alignments{$tag}=join ".",split(/\s*/,$alignment->{$tag}) ;
		push @locus_sequences, $node_sequences{$tag};
# print "adding to node_seq: $tag = ",$node_alignments{$tag},"\n";
	}
	
	#<STDIN>;
	
	my ($nodes_arr, $branches_hash) = get_nodes($tree);
	my @nodes=@$nodes_arr;
#	print "recieved nodes = " if $printer == 1; 
#	foreach my $key (@nodes) {print "@$key "  if $printer == 1;}
	
#	print "\n" if $printer == 1;
	
	#POPULATE branches_hash WITH INFORMATION ABOUT LIVESTATUS
	foreach my $keys (@nodes){
		my @pair = @$keys;
		my $joint = "(".join(", ",@pair).")";
		my $copykey = join "", @pair;
		$copykey =~ s/[\W ]+//g;
#		print "for node: $keys, copykey = $copykey and joint = $joint\n" if $printer == 1;
		my $livestatus = 1;
		foreach my $copy (split(/\s*/,$copykey)){
			$livestatus = 0 if !exists $alivehash{$copy};
		}
		$alivehash{$joint} = $joint if !exists $alivehash{$joint} && $livestatus == 1;
#		print "alivehash = $alivehash{$joint}\n" if exists $alivehash{$joint} && $printer == 1;
	}
		
	@nodes = reverse(@nodes); #1 THIS IS IN ORDER TO GO THROUGH THE TREE FROM LEAVES TO ROOT.

	my @mutations_array=();

	my $joint = ();
	foreach my $node (@nodes){
		my @pair = @$node; 
#		print "now in the nodes for loop, pair = @pair\n and sequences=\n" if $printer == 1;
		$joint = "(".join(", ",@pair).")"; 	
		my @pair_sequences=();

		foreach my $tag (@pair){
#			print "$tag:  $node_alignments{$tag}\n" if $printer == 1;
#			print $node_alignments{$tag},"\n" if $printer == 1;
			push @pair_sequences, $node_alignments{$tag};
		}
#		print "ppeel onion joint = $joint , pair_sequences=>@pair_sequences< , pair=>@pair<\n" if $printer == 1; 
		
		my ($compared, $substitutions_list) = base_by_base_simple($motif,\@pair_sequences, scalar(@pair_sequences), @pair, $joint);
		$node_alignments{$joint}=$compared;
		push(  @mutations_array,split(/:/,$substitutions_list));
#		print "newly added to node_sequences: $node_alignments{$joint} and list of mutations =\n", join("\n",@mutations_array),"\n" if $printer == 1;
	}
	
	
	my $analayzed_mutations = analyze_mutations(\@mutations_array, \@nodes, $branches_hash, $alignment, \@tags, \%alivehash, \%node_sequences, $microsatstarts, $motif);

	return ($analayzed_mutations, \@nodes, $branches_hash, \%alivehash, $node_alignments{$joint}) if scalar @mutations_array > 0;
	return ("NULL",\@nodes,$branches_hash, \%alivehash, "NULL") if scalar @mutations_array == 0;
}

#+++++++++++#+++++++++++#+++++++++++#+++++++++++#+++++++++++#+++++++++++#+++++++++++#+++++++++++#
#+++++++++++#+++++++++++#+++++++++++#+++++++++++#+++++++++++#+++++++++++#+++++++++++#+++++++++++#

#+++++++++++#+++++++++++#+++++++++++#+++++++++++#+++++++++++#+++++++++++#+++++++++++#+++++++++++#
#+++++++++++#+++++++++++#+++++++++++#+++++++++++#+++++++++++#+++++++++++#+++++++++++#+++++++++++#

sub get_nodes{
	my $printer = 0;

	my $tree=$_[0];
	#$tree =~ s/ +//g;
	$tree =~ s/\t+//g;
	$tree=~s/;//g;
# print "tree=$tree\n" if $printer == 1; 
	my @nodes = ();
	my @onions=($tree);
	my %branches=();
	foreach my $bite (@onions){
		$bite=~ s/^\(|\)$//g;
		chomp $bite;
#		print "tree = $bite \n"; 
#		<STDIN>;
		$bite=~ /([ ,\(\)A-Z]+)\,\s*([ ,\(\)A-Z]+)/;
		#$tree =~ /(\(\(\(H, C\), O\), R\))\, (M)/;
		my @raw_nodes = ($1, $2);
# print "raw nodes =  $1 and $2\n" if $printer == 1;
		push(@nodes, [@raw_nodes]);
		foreach my $node (@raw_nodes) {push (@onions, $node) if $node =~ /,/;}
		foreach my $node (@raw_nodes) {$branches{$node}="(".$bite.")"; }
#		print "onions = @onions\n" if $printer == 1;<STDIN> if $printer == 1;
	}
	$printer = 0;
	return \@nodes, \%branches;
}


#+++++++++++#+++++++++++#+++++++++++#+++++++++++#+++++++++++#+++++++++++#+++++++++++#+++++++++++#
#+++++++++++#+++++++++++#+++++++++++#+++++++++++#+++++++++++#+++++++++++#+++++++++++#+++++++++++#
#+++++++++++#+++++++++++#+++++++++++#+++++++++++#+++++++++++#+++++++++++#+++++++++++#+++++++++++#
#+++++++++++#+++++++++++#+++++++++++#+++++++++++#+++++++++++#+++++++++++#+++++++++++#+++++++++++#
sub analyze_mutations{
	my ($mutations_array, $nodes, $branches_hash, $alignment, $tags, $alivehash, $node_sequences, $microsatstarts, $motif) = @_;
	my $locuslength = length($alignment->{$tags->[0]});
	my $printer = 0;
	
	
#	print " IN analyzed_mutations....\n" if $printer == 1; #  \n mutations array = @$mutations_array, \nAND locuslength = $locuslength\n" if $printer == 1;
	my %mutation_hash=();
	my %froms_megahash=();
	my %tos_megahash=();
	my %position_hash=();
	my @solutions_array=();
	foreach  my $mutation (@$mutations_array){
#		print "loadin mutation: $mutation\n" if $printer == 1;
		my %localhash= $mutation =~ /([\S ]+)=([\S ]+)/g;
		$mutation_hash{$localhash{"position"}} = {%localhash};
		push @{$position_hash{$localhash{"position"}}},$localhash{"node"};
#		print "feeding position hash with $localhash{position}: $position_hash{$localhash{position}}[0]\n" if $printer == 1;
		$froms_megahash{$localhash{"position"}}{$localhash{"node"}}=$localhash{"from"};
		$tos_megahash{$localhash{"position"}}{$localhash{"node"}}=$localhash{"to"};
#		print "just a trial: $mutation_hash{$localhash{position}}{position}\n" if $printer == 1;
#		print "loadin in tos_megahash: $localhash{position} {$localhash{node} = $localhash{to}\n" if $printer == 1;
#		print "loadin in from: $localhash{position} {$localhash{node} = $localhash{from}\n" if $printer == 1;
	}
	
#	print "now going through each position in loculength:\n" if $printer == 1;
	## <STDIN> if $printer == 1;
	
	for my $pos (0 ... $locuslength-1){
#		print "at position: $pos\n" if $printer == 1;

		if (exists($mutation_hash{$pos})){
			my @local_nodes=@{$position_hash{$pos}};
#			print "found mutation: @{$position_hash{$pos}} :  @local_nodes\n" if $printer == 1;
			
			foreach my $local_node (@local_nodes){
#				print "at local node: $local_node ... from state = $froms_megahash{$pos}{$local_node}\n" if $printer == 1;
				my $open_insertion=();
				my $open_deletion=();
				my $open_to_substitution=();
				my $open_from_substitution=();
				if ($froms_megahash{$pos}{$local_node} eq "-"){
				#	print "here exists a microsatellite from $local_node to $branches_hash->{$local_node}\n" if $printer == 1 &&  exists $alivehash->{$local_node} && exists $alivehash->{$branches_hash->{$local_node}};;
				#	print "for localnode $local_node, amd the realated branches_hash:$branches_hash->{$local_node},  nexting as exists $alivehash->{$local_node} && exists $alivehash->{$branches_hash->{$local_node}}\n" if exists $alivehash->{$local_node} && exists $alivehash->{$branches_hash->{$local_node}} && $printer == 1;
					#next if exists $alivehash->{$local_node} && exists $alivehash->{$branches_hash->{$local_node}};
					$open_insertion=$tos_megahash{$pos}{$local_node};
					for my $posnext ($pos+1 ... $locuslength-1){
#						print "in first if  .... studying posnext: $posnext\n" if $printer == 1;
						last if !exists ($froms_megahash{$posnext}{$local_node});
#						print "for posnext: $posnext, there exists $froms_megahash{$posnext}{$local_node}.. already, open_insertion = $open_insertion.. checking is $froms_megahash{$posnext}{$local_node} matters\n" if $printer == 1;
						$open_insertion = $open_insertion.$tos_megahash{$posnext}{$local_node} if $froms_megahash{$posnext}{$local_node} eq "-";
#						print "now open_insertion=$open_insertion\n" if $printer == 1;
						delete $mutation_hash{$posnext} if $froms_megahash{$posnext}{$local_node} eq "-";
					}					
# print "1 Feeding in: ", join("\t", "node=$local_node","type=insertion" ,"position=$pos", "from=", "to=", "insertion=$open_insertion", "deletion="),"\n" if $printer == 1;
					push (@solutions_array, join("\t", "node=$local_node","type=insertion" ,"position=$pos", "from=", "to=", "insertion=$open_insertion", "deletion="));
				}
				elsif ($tos_megahash{$pos}{$local_node} eq "-"){
				#	print "here exists a microsatellite to $local_node from $branches_hash->{$local_node}\n" if $printer == 1 && exists $alivehash->{$local_node} && exists $alivehash->{$branches_hash->{$local_node}};;
				#	print "for localnode $local_node, amd the realated branches_hash:$branches_hash->{$local_node},  nexting as exists $alivehash->{$local_node} && exists $alivehash->{$branches_hash->{$local_node}}\n" if exists $alivehash->{$local_node} && exists $alivehash->{$branches_hash->{$local_node}};
					#next if exists $alivehash->{$local_node} && exists $alivehash->{$branches_hash->{$local_node}};
					$open_deletion=$froms_megahash{$pos}{$local_node};
					for my $posnext ($pos+1 ... $locuslength-1){
# print "in 1st elsif studying posnext: $posnext\n" if $printer == 1;
# print "nexting as nextpos does not exist\n" if !exists ($tos_megahash{$posnext}{$local_node}) && $printer == 1;
						last if !exists ($tos_megahash{$posnext}{$local_node});
# print "for posnext: $posnext, there exists $tos_megahash{$posnext}{$local_node}\n" if $printer == 1;
						$open_deletion = $open_deletion.$froms_megahash{$posnext}{$local_node} if $tos_megahash{$posnext}{$local_node} eq "-";
						delete $mutation_hash{$posnext} if $tos_megahash{$posnext}{$local_node} eq "-";
					}					
# print "2 Feeding in:",  join("\t", "node=$local_node","type=deletion" ,"position=$pos", "from=", "to=", "insertion=", "deletion=$open_deletion"), "\n" if $printer == 1;
					push (@solutions_array, join("\t", "node=$local_node","type=deletion" ,"position=$pos", "from=", "to=", "insertion=", "deletion=$open_deletion"));
				}
				elsif ($tos_megahash{$pos}{$local_node} ne "-"){
				#	print "here exists a microsatellite from $local_node to $branches_hash->{$local_node}\n" if $printer == 1 && exists $alivehash->{$local_node} && exists $alivehash->{$branches_hash->{$local_node}};;
				#	print "for localnode $local_node, amd the realated branches_hash:$branches_hash->{$local_node},  nexting as exists $alivehash->{$local_node} && exists $alivehash->{$branches_hash->{$local_node}}\n" if exists $alivehash->{$local_node} && exists $alivehash->{$branches_hash->{$local_node}};
					#next if exists $alivehash->{$local_node} && exists $alivehash->{$branches_hash->{$local_node}};
				#	print "microsatstart = $microsatstarts->{$local_node}  \n" if exists $microsatstarts->{$local_node} && $pos < $microsatstarts->{$local_node} && $printer == 1;
					next if exists $microsatstarts->{$local_node} && $pos < $microsatstarts->{$local_node};
					$open_to_substitution=$tos_megahash{$pos}{$local_node};
					$open_from_substitution=$froms_megahash{$pos}{$local_node};
# print "open from substitution: $open_from_substitution \n" if $printer == 1;
					for my $posnext ($pos+1 ... $locuslength-1){
						#print "in last elsif studying posnext: $posnext\n";
						last if !exists ($tos_megahash{$posnext}{$local_node});
# print "for posnext: $posnext, there exists $tos_megahash{$posnext}{$local_node}\n" if $printer == 1;
						$open_to_substitution = $open_to_substitution.$tos_megahash{$posnext}{$local_node} if $tos_megahash{$posnext}{$local_node} ne "-";
						$open_from_substitution = $open_from_substitution.$froms_megahash{$posnext}{$local_node} if $tos_megahash{$posnext}{$local_node} ne "-";
						delete $mutation_hash{$posnext} if $tos_megahash{$posnext}{$local_node} ne "-" && $froms_megahash{$posnext}{$local_node} ;
					}	
# print "open from substitution: $open_from_substitution \n" if $printer == 1;
					
					#IS THE STRETCH OF SUBSTITUTION MICROSATELLITE-LIKE?
					my @motif_parts=split(/\s*/,$motif);
					#GENERATING THE FLEXIBLE LEFT END
					my $left_query=();
					for my $k (1 ... $#motif_parts) {
						$left_query= $motif_parts[$k]."|)";
						$left_query="(".$left_query;
					}
					$left_query=$left_query."?";
# print "left_quewry = $left_query\n" if $printer == 1;
					#GENERATING THE FLEXIBLE RIGHT END	
					my $right_query=();
					for my $k (0 ... ($#motif_parts-1)) {
						$right_query= "(|".$motif_parts[$k];
						$right_query=$right_query.")";
					}
					$right_query=$right_query."?";
# print "right_query = $right_query\n" if $printer == 1;
# print "Hence, searching for: ^$left_query($motif)+$right_query\$\n" if $printer == 1;
					
					my $motifcomb=$motif x 50;
# print "motifcomb = $motifcomb\n" if $printer == 1;
					if ( ($motifcomb =~/$open_to_substitution/i) && (length ($open_to_substitution) >= length($motif)) ){
# print "sequence microsat-like\n" if $printer == 1;
						my $all_microsat_like = 0;
# print "3 feeding in: ", join("\t", "node=$local_node","type=deletion" ,"position=$pos", "from=", "to=", "insertion=", "deletion=$open_from_substitution"), "\n" if $printer == 1;
						push (@solutions_array, join("\t", "node=$local_node","type=deletion" ,"position=$pos", "from=", "to=", "insertion=", "deletion=$open_from_substitution"));
# print "4 feeding in: ", join("\t", "node=$local_node","type=insertion" ,"position=$pos", "from=", "to=", "insertion=$open_to_substitution", "deletion="), "\n" if $printer == 1;
						push (@solutions_array, join("\t", "node=$local_node","type=insertion" ,"position=$pos", "from=", "to=", "insertion=$open_to_substitution", "deletion="));
						
					}
					else{
# print "5 feeding in: ", join("\t", "node=$local_node","type=substitution" ,"position=$pos", "from=$open_from_substitution", "to=$open_to_substitution", "insertion=", "deletion="), "\n" if $printer == 1;
						push (@solutions_array, join("\t", "node=$local_node","type=substitution" ,"position=$pos", "from=$open_from_substitution", "to=$open_to_substitution", "insertion=", "deletion="));
					}
					#IS THE FROM-SEQUENCE MICROSATELLITE-LIKE?

				}
				#<STDIN> if $printer ==1;
			}
			#<STDIN> if $printer ==1;
		}
	}
# print "\n", "#" x 50, "\n"  if $printer == 1;
	foreach my $tag (@$tags){
# print "$tag: $alignment->{$tag}\n" if $printer == 1;	
	}
# print "\n", "#" x 50, "\n" if $printer == 1;
# print "returning SOLUTIONS ARRAY : \n",join("\n", @solutions_array),"\n" if $printer == 1; 
	#print "end\n";
	#<STDIN> if 
	return \@solutions_array;
}
#+++++++++++#+++++++++++#+++++++++++#+++++++++++#+++++++++++#+++++++++++#+++++++++++#+++++++++++#
#+++++++++++#+++++++++++#+++++++++++#+++++++++++#+++++++++++#+++++++++++#+++++++++++#+++++++++++#
#+++++++++++#+++++++++++#+++++++++++#+++++++++++#+++++++++++#+++++++++++#+++++++++++#+++++++++++#
#+++++++++++#+++++++++++#+++++++++++#+++++++++++#+++++++++++#+++++++++++#+++++++++++#+++++++++++#

sub base_by_base_simple{
	my $printer = 0;
	my ($motif, $locus, $no, $pair0, $pair1, $joint) = @_;
	my @seq_array=();
# print "IN SUBROUTUNE base_by_base_simple.. information received = @_\n" if $printer == 1;
# print "pair0 = $pair0 and pair1  = $pair1\n" if $printer == 1;

	my @example=split(/\./,$locus->[0]);
# print "example, for length = @example\n" if $printer == 1;
	for my $i (0...$no-1){push(@seq_array, [split(/\./,$locus->[$i])]); }

	my @compared_sequence=();
	my @substitutions_list;
	for my $i (0...scalar(@example)-1){

		#print "i = $i\n" if $printer == 1;
		#print "comparing $seq_array[0][$i] and  $seq_array[1][$i] \n" ;#if $printer == 1;
		if ($seq_array[0][$i] =~ /!/ && $seq_array[1][$i] !~ /!/){

			my $resolution= resolve_base($seq_array[0][$i],$seq_array[1][$i], $pair1 ,"keep" );
		#	print "ancestral = $resolution\n" if $printer == 1;

			if ($resolution =~ /$seq_array[1][$i]/i && $resolution !~ /!/){
				push @substitutions_list, add_mutation($i, $pair0,  $seq_array[0][$i], $resolution );
			}
			elsif ( $resolution !~ /!/){
				push @substitutions_list, add_mutation($i, $pair1,  $seq_array[1][$i], $resolution);			
			}
			push @compared_sequence,$resolution;
		}
		elsif ($seq_array[0][$i] !~ /!/ && $seq_array[1][$i] =~ /!/){

			my $resolution=  resolve_base($seq_array[1][$i],$seq_array[0][$i], $pair0, "invert" );		
		#	print "ancestral = $resolution\n" if $printer == 1;

			if ($resolution =~ /$seq_array[0][$i]/i && $resolution !~ /!/){
				push @substitutions_list, add_mutation($i, $pair1, $seq_array[1][$i], $resolution);
			}
			elsif ( $resolution !~ /!/){
				push @substitutions_list, add_mutation($i, $pair0,  $seq_array[0][$i], $resolution);			
			}
			push @compared_sequence,$resolution;
		}
		elsif($seq_array[0][$i] =~ /!/ && $seq_array[1][$i] =~ /!/){
			push @compared_sequence, add_bases($seq_array[0][$i],$seq_array[1][$i], $pair0, $pair1, $joint );
		}
		else{
			if($seq_array[0][$i] !~ /^$seq_array[1][$i]$/i){
				push @compared_sequence, $pair0.":".$seq_array[0][$i]."!".$pair1.":".$seq_array[1][$i];
			}
			else{
		#		print "perfect match\n" if $printer == 1;
				push @compared_sequence, $seq_array[0][$i];
			}
		}		
	}
# print "returning: comared = @compared_sequence \nand substitutions list =\n", join("\n",@substitutions_list),"\n" if $printer == 1; 
	return join(".",@compared_sequence), join(":", @substitutions_list) if scalar (@substitutions_list) > 0;
	return join(".",@compared_sequence), "" if scalar (@substitutions_list) == 0;
}


sub resolve_base{
	my $printer = 0;
# print "IN SUBROUTUNE resolve_base.. information received = @_\n" if $printer == 1;
	my ($optional, $single, $singlesp, $arg) = @_;
	my @options=split(/!/,$optional);
	foreach my $option(@options) { 
		$option=~s/[A-Z\(\) ,]+://g;
		if ($option =~ /$single/i){
# print "option = $option , returning single: $single\n" if $printer == 1;
			return $single;
		}
	}
# print "returning ",$optional."!".$singlesp.":".$single. "\n" if $arg eq "keep" && $printer == 1; 
# print "returning ",$singlesp.":".$single."!".$optional. "\n" if $arg eq "invert" && $printer == 1; 
	return $optional."!".$singlesp.":".$single if $arg eq "keep";
	return $singlesp.":".$single."!".$optional if $arg eq "invert";

}

sub same_length{
	my $printer = 0;
	my @locus = @_;
	my $temp = shift @locus;
	$temp=~s/-|,//g;
	foreach my $l (@locus){
		$l=~s/-|,//g;
		return 0 if length($l) != length($temp);
		$temp = $l;
	}
	return 1;
}
sub treeStudy{
	my $printer = 1;
#	print "template DEFINED.. received: @_\n" if defined %template; 
#	print "only received = @_" if !defined %template; 
	my $stopper = 0;
	if (!defined %template){
		$stopper = 1;
		%template=();
# print "tree decipherer = $tree_decipherer\n" if $printer == 1; 
		my ( $template_ref, $keys_array)=load_allPossibleTrees($tree_decipherer, \%template);
# print "return = $template_ref and @{$keys_array}\n" if $printer == 1;
		foreach my $key (@$keys_array){
# print "addding : $template_ref->{$key} for $key\n" if $printer == 1;
			$template{$key} = $template_ref->{$key};
		}
	}
#	<STDIN>;
	for my $templet ( keys %template ) {
	#	print "$templet => @{$template{$templet}}\n";
	}
#	<STDIN> if !defined %template;

	my $strict = 0;

    my $H = 0;
    my $Hchr = 1;
    my $Hstart = 2;
    my $Hend = 3;    
	my $Hmotif = 4;
	my $Hmotiflen = 5;
	my $Hmicro = 6;
	my $Hstrand = 7;
	my $Hmicrolen = 8;
	my $Hinterpos = 9;
	my $Hrelativepos = 10;
	my $Hinter = 11;
	my $Hinterlen = 12;
	
	my $C = 13;
    my $Cchr = 14;
    my $Cstart = 15;
    my $Cend = 16;    
	my $Cmotif = 17;
	my $Cmotiflen = 18;
	my $Cmicro = 19;
	my $Cstrand = 20;
	my $Cmicrolen = 21;
	my $Cinterpos = 22;
	my $Crelativepos = 23;
	my $Cinter = 24;
	my $Cinterlen = 25;
	
	my $O = 26;
    my $Ochr = 27;
    my $Ostart = 28;
    my $Oend = 29;    
	my $Omotif = 30;
	my $Omotiflen = 31;
	my $Omicro = 32;
	my $Ostrand = 33;
	my $Omicrolen = 34;
	my $Ointerpos = 35;
	my $Orelativepos = 36;
	my $Ointer = 37;
	my $Ointerlen = 38;
	
	my $R = 39;
    my $Rchr = 40;
    my $Rstart = 41;
    my $Rend = 42;    
	my $Rmotif = 43;
	my $Rmotiflen = 44;
	my $Rmicro = 45;
	my $Rstrand = 46;
	my $Rmicrolen = 47;
	my $Rinterpos = 48;
	my $Rrelativepos = 49;
	my $Rinter = 50;
	my $Rinterlen = 51;
	
    my $Mchr = 52;
    my $Mstart = 53;
    my $Mend = 54;    
	my $M = 55;
	my $Mmotif = 56;
	my $Mmotiflen = 57;
	my $Mmicro = 58;
	my $Mstrand = 59;
	my $Mmicrolen = 60;
	my $Minterpos = 61;
	my $Mrelativepos = 62;
	my $Minter = 63;
	my $Minterlen = 64;
	
	#-------------------------------------------------------------------------------#
	my @analysis=();
	
	
	my %speciesOrder = ();
	$speciesOrder{"H"} = 0;
	$speciesOrder{"C"} = 1;
	$speciesOrder{"O"} = 2;
	$speciesOrder{"R"} = 3;
	$speciesOrder{"M"} = 4;
	#-------------------------------------------------------------------------------#

	my $line = $_[0];
	chomp $line;
	
	my @f = split(/\t/,$line);
# print "received array : @f.. recieved tags = @tags\n" if $printer == 1;
	
	# collect all motifs
	my @motifs=();
	 @motifs = ($f[$Hmotif], $f[$Cmotif], $f[$Omotif], $f[$Rmotif], $f[$Mmotif]) if $tags[$#tags] =~ /M/;
	 @motifs = ($f[$Hmotif], $f[$Cmotif], $f[$Omotif], $f[$Rmotif]) if $tags[$#tags] =~ /R/;
	 @motifs = ($f[$Hmotif], $f[$Cmotif], $f[$Omotif]) if $tags[$#tags] =~ /O/;
#	print "motifs in the array = $f[$Hmotif], $f[$Cmotif], $f[$Omotif], $f[$Rmotif]\n" if $tags[$#tags] =~ /R/;;
# print "motifs = @motifs\n" if $printer == 1;
	my @translation = ();
	foreach my $motif (@motifs){
		push(@translation, "_") if $motif eq "NA";
		push(@translation, "+") if $motif ne "NA";
	}
	my $translate = join(" ", @translation);
#	print "translate = >$translate< and analysis = $template{$translate}[0].. on the other hand, ",$template{"- - +"}[0],"\n"; 
	my @analyses = split(/\|/,$template{$translate}[0]);
# print "motifs = @motifs, analyses = @analyses\n" if $printer == 1; 

	if (scalar(@analyses) == 1) {
		#print "analysis = $analyses[0]\n"; 
		if ($analyses[0] !~ /,|\./ ){
			if ($analyses[0] =~ /\+/){
				my $analysis = $analyses[0];
				$analysis =~ s/\+|\-//g;
				my @species = split(/\s*/,$analysis);
				my @currentMotifs = ();
				foreach my $specie (@species){	push(@currentMotifs, $motifs[$speciesOrder{$specie}]); #print "pushing into currentMotifs: $speciesOrder{$specie}: $motifs[$speciesOrder{$specie}]\n" if $printer == 1;
					}
# print "current motifs = @currentMotifs and consistency? ", (consistency(@currentMotifs))," \n" if $printer == 1;
				$template{$translate}[1]++ if $strict == 1 && consistency(@currentMotifs) ne "NULL";
				$template{$translate}[1]++ if $strict == 0;
# print "adding to template $translate: $template{$translate}[1]\n" if $printer == 1;
			}
			else{
				my $analysis = $analyses[0];
				$analysis =~ s/\+|\-//g;
				my @species = split(/\s*/,$analysis);
				my @currentMotifs = ();
				my @complementarySpecies = ();
				my $allSpecies = join("",@tags);
				foreach my $specie (@species){	$allSpecies =~	s/$specie//g; }
				foreach my $specie (split(/\s*/,$allSpecies)){	push(@currentMotifs, $motifs[$speciesOrder{$specie}]); #print "pushing into currentMotifs: $speciesOrder{$specie}: $motifs[$speciesOrder{$specie}]\n" if $printer == 1;;
					}
# print "current motifs = @currentMotifs and consistency? ", (consistency(@currentMotifs))," \n" if $printer == 1;
				$template{$translate}[1]=$template{$translate}[1]+1 if $strict == 1 && consistency(@currentMotifs) ne "NULL";
				$template{$translate}[1]=$template{$translate}[1]+1  if $strict == 0;
# print "adding to template $translate: $template{$translate}[1]\n" if $printer == 1;
			}
		}

		elsif ($analyses[0] =~ /,/) {
			my @events = split(/,/,$analyses[0]);	
# print "events = @events \n " if $printer == 1;
			if ($events[0] =~ /\+/){
				my $analysis1 = $events[0];
				$analysis1 =~ s/\+|\-//g;
				my $analysis2 = $events[1];
				$analysis2 =~ s/\+|\-//g;
				my @nSpecies = split(/\s*/,$analysis2);
# print "original anslysis = $analysis1 " if $printer == 1;
				foreach my $specie (@nSpecies){ $analysis1=~ s/$specie//g;}
# print "processed anslysis = $analysis1 \n" if $printer == 1; 
				my @currentMotifs = ();
				foreach my $specie (split(/\s*/,$analysis1)){push(@currentMotifs, $motifs[$speciesOrder{$specie}]); }
# print "current motifs = @currentMotifs and consistency? ", (consistency(@currentMotifs))," \n" if $printer == 1;
				$template{$translate}[1]=$template{$translate}[1]+1 if $strict == 1 && consistency(@currentMotifs) ne "NULL";
				$template{$translate}[1]=$template{$translate}[1]+1  if $strict == 0;
# print "adding to template $translate: $template{$translate}[1]\n" if $printer == 1;
			}
			else{
				my $analysis1 = $events[0];
				$analysis1 =~ s/\+|\-//g;
				my $analysis2 = $events[1];
				$analysis2 =~ s/\+|\-//g;
				my @pSpecies = split(/\s*/,$analysis2);
				my @currentMotifs = ();
				foreach my $specie (@pSpecies){	push(@currentMotifs, $motifs[$speciesOrder{$specie}]); }
# print "current motifs = @currentMotifs and consistency? ", (consistency(@currentMotifs))," \n" if $printer == 1;
				$template{$translate}[1]=$template{$translate}[1]+1 if $strict == 1 && consistency(@currentMotifs) ne "NULL";
				$template{$translate}[1]=$template{$translate}[1]+1 if $strict == 0;
# print "adding to template $translate: $template{$translate}[1]\n" if $printer == 1;
			
			}
			
		}
		elsif ($analyses[0] =~ /\./) {
			my @events = split(/\./,$analyses[0]);	
			foreach my $event (@events){
# print "event = $event \n" if $printer == 1;
				if ($event =~ /\+/){
					my $analysis = $event;
					$analysis =~ s/\+|\-//g;
					my @species = split(/\s*/,$analysis);
					my @currentMotifs = ();
					foreach my $specie (@species){	push(@currentMotifs, $motifs[$speciesOrder{$specie}]); }
					#print consistency(@currentMotifs),"<- \n"; 
# print "current motifs = @currentMotifs and consistency? ", (consistency(@currentMotifs))," \n" if $printer == 1;
					$template{$translate}[1]=$template{$translate}[1]+1 if $strict == 1 && consistency(@currentMotifs) ne "NULL";
					$template{$translate}[1]=$template{$translate}[1]+1 if $strict == 0;
# print "adding to template $translate: $template{$translate}[1]\n" if $printer == 1;
				}
				else{
					my $analysis = $event;
					$analysis =~ s/\+|\-//g;
					my @species = split(/\s*/,$analysis);
					my @currentMotifs = ();
					my @complementarySpecies = ();
					my $allSpecies = join("",@tags);
					foreach my $specie (@species){	$allSpecies =~	s/$specie//g; }
					foreach my $specie (split(/\s*/,$allSpecies)){	push(@currentMotifs, $motifs[$speciesOrder{$specie}]); }
					#print consistency(@currentMotifs),"<- \n"; 
# print "current motifs = @currentMotifs and consistency? ", (consistency(@currentMotifs))," \n" if $printer == 1;
					$template{$translate}[1]=$template{$translate}[1]+1 if $strict == 1 && consistency(@currentMotifs) ne "NULL";
					$template{$translate}[1]=$template{$translate}[1]+1 if $strict == 0;
# print "adding to template $translate: $template{$translate}[1]\n" if $printer == 1;
				}
			}	
		
		}
	}
	else{		
		my $finalanalysis = ();
		$template{$translate}[1]++;
		foreach my $analysis (@analyses){ ;}
	}
	# test if motifs where microsats are present, as indeed of same the motif composition
	
	
	
	for my $templet ( keys %template ) {
		if (@{ $template{$templet} }[1] > 0){
			
			$template{$templet}[1] = 0;
# print "now returning: @{$template{$templet}}[0], $templet\n";
			return 	(@{$template{$templet}}[0], $templet);
		}
	}
	undef %template;
# print "sending NULL\n" if $printer == 1;
	return ("NULL", "NULL");
	
}


sub consistency{
	my @motifs = @_;
# print "in consistency \n" if $printer == 1;
# print "motifs sent = >",join("|",@motifs),"< \n" if $printer == 1; 
	return $motifs[0] if scalar(@motifs) == 1;
	my $prevmotif = shift(@motifs);
	my $stopper = 0;
	for my $i (0 ... $#motifs){
		next if $motifs[$i] eq "NA";
		my $templet = $motifs[$i].$motifs[$i];
		if ($templet !~ /$prevmotif/i){
			$stopper = 1; last;
		}
	}
	return $prevmotif if $stopper == 0;
	return "NULL" if $stopper == 1;
}
sub summarize_microsat{
	my $printer = 1;
	my $line = $_[0];	
	my $humseq = $_[1];

	my @gaps = $line =~ /[0-9]+\t[0-9]+\t[\+\-]/g;
	my @starts = $line =~ /[0-9]+\t[\+\-]/g;
	my @ends = $line =~ /[\+\-]\t[0-9]+/g;
# print "starts = @starts\tends = @ends\n" if $printer == 1;
	for my $i (0 ... $#gaps) {$gaps[$i] =~ s/\t[0-9]+\t[\+\-]//g;}
	for my $i (0 ... $#starts) {$starts[$i] =~ s/\t[\+\-]//g;}
	for my $i (0 ... $#ends) {$ends[$i] =~ s/[\+\-]\t//g;}

	my $minstart = array_smallest_number(@starts);
	my $maxend = array_largest_number(@ends);

	my $humupstream_st = substr($humseq, 0, $minstart);
	my $humupstream_en = substr($humseq, 0, $maxend);
	my $no_of_gaps_to_start = 0;
	my $no_of_gaps_to_end = 0;
	$no_of_gaps_to_start = ($humupstream_st =~ s/\-/x/g) if $humupstream_st=~/\-/;
	$no_of_gaps_to_end = ($humupstream_en =~ s/\-/x/g) if $humupstream_en=~/\-/;

	my $locusmotif = ();
# print "IN SUB SUMMARIZE_MICROSAT $line\n" if $printer == 1;
	#return "NULL" if $line =~ /compound/;
	my $Hstart = "NA";
	my $Hend = "NA";
	chomp $line;
	my $match_count = ($line =~ s/>/>/g);
	#print "number of species = $match_count\n";
	my @micros = split(/>/,$line);
	shift @micros;
	my $stopper = 0;
	
	
	foreach my $mic (@micros){
		my @local = split(/\t/,$mic);
		if ($local[$microsatcord] =~ /N/) {$stopper =1; last;}
	}
	return "NULL" if $stopper ==1;
	
	#------------------------------------------------------

	my @arranged = ();
	for my $arr (0 ... $#exacttags) {$arranged[$arr] = '0';}
		
	foreach my $micro (@micros){
		for my $i (0 ... $#exacttags){
			if ($micro =~ /^$exacttags[$i]/){
				$arranged[$i] = $micro;
				last;
			}
		}
	}
#	print "arranged = @arranged \n" ; <STDIN>;;
	
	my @endstatement = ();
	my $turn = 0;
	my $species_counter = 0;
	#	print scalar(@arranged),"\n";
	
	my $species_no=0;
	
	my $orthHchr = 0;

	foreach my $micro (@arranged) {
		$micro =~ s/\t\t/\t \t/g;
		$micro =~ s/\t,/\t ,/g;
		$micro =~ s/,\t/, \t/g;
# print "------------------------------------------------------------------------------------------\n" if $printer == 1;
		chomp $micro;
		if ($micro eq '0'){
			push(@endstatement, join("\t",$exacttags[$species_counter],"NA","NA","NA","NA",0 ,"NA", "NA", 0,"NA","NA","NA", "NA" ));
			$species_counter++;
		#	print join("|","ENDSTATEMENT:",@endstatement),"\n" if $printer == 1;
			next;
		}
	#		print $micro,"\n";
# print "micro  = $micro \n" if $printer == 1;
		my @fields  = split(/\t/,$micro);
		my $microcopy = $fields[$microsatcord];
		$microcopy =~ s/\[|\]|-//g;
		my $microsatlength = length($microcopy);
# print "microsat = $fields[$microsatcord] and microsatlength = $microsatlength\n" if $printer == 1;
#		print "sp_ident = @sp_ident.. species_no=$species_no\n";
		$micro =~ /$sp_ident[$species_no]\s([0-9a-zA-Z_]+)\s([0-9]+)\s([0-9]+)/;
# print "$micro =~ /$sp_ident[$species_no] ([0-9a-zA-Z_]+) ([0-9]+) ([0-9]+)/\n";
		my $sp_chr=$1;
		my $sp_start=$2 + $fields[$startcord] - $fields[$gapcord];
		my $sp_end= $sp_start + $microsatlength - 1;
		
		$species_no++;
	
		$micro =~ /$focalspec_orig\s(\S+)\s([0-9]+)\s([0-9]+)/;
		$orthHchr=$1;
		$Hstart=$2+$minstart-$no_of_gaps_to_start;
		$Hend=$2+$maxend-$no_of_gaps_to_end;
# print "Hstart = $Hstart = $fields[4] + $fields[$startcord] - $fields[$gapcord]\n" if $printer == 1;
	
		my $motif = $fields[$motifcord];
		my $firstmotif = ();
		my $strand = $fields[$strandcord];
	#		print "strand = $strand\n";
		
	
		if ($motif =~ /^\[/){
			$motif =~ s/^\[//g;
			$motif =~ /([a-zA-Z]+)\].*/;
			$firstmotif = $1;
		}
		
		else {$firstmotif = $motif;}
# print "firstmotif =$firstmotif : \n" if $printer == 1;
		$firstmotif = allCaps($firstmotif);

		if (exists $revHash{$firstmotif} && $turn == 0) {
			$turn=1 if $species_counter==0;
			$firstmotif = $revHash{$firstmotif};
		}
		
		elsif (exists $revHash{$firstmotif} && $turn == 1) {$firstmotif = $revHash{$firstmotif}; $turn = 1;}
# print "changed firstmotif =$firstmotif\n" if $printer == 1;
	#		<STDIN>;
		$locusmotif = $firstmotif;
		
		if (scalar(@fields) > $microsatcord + 2){
# print "fields = @fields ... interr_poscord=$interr_poscord=$fields[$interr_poscord] .. interrcord=$interrcord=$fields[$interrcord]\n" if $printer == 1; 

			my @interposes = ();
			@interposes = split(",",$fields[$interr_poscord]) if $fields[$interr_poscord] =~ /,/; 
			$interposes[0] = $fields[$interr_poscord] if $fields[$interr_poscord] !~ /,/ ;
# print "interposes=@interposes\n" if $printer == 1;
			my @relativeposes = (); 
			my @interruptions = ();
			@interruptions = split(",",$fields[$interrcord]) if $fields[$interrcord] =~ /,/; 
			$interruptions[0] = $fields[$interrcord]  if $fields[$interrcord] !~ /,/;
			my @interlens = ();

			
			for my $i (0 ... $#interposes){
			
				my $interpos = $interposes[$i];
				my $nexter = 0;
				my $interruption = $interruptions[$i];
				my $interlen = length($interruption);
				push (@interlens, $interlen);
			
				
				my $relativepos = (100 * $interpos) / $microsatlength;
# print "relativepos  = $relativepos ,interpos=$interpos, interruption=$interruption, interlen=$interlen \n" if $printer == 1;
				$relativepos = (100 * ($interpos-$interlen)) / $microsatlength if $relativepos > 50;
# print "-->  = $relativepos\n" if $printer == 1;
				$interruption = "IND" if length($interruption) < 1;
		
				if ($turn == 1){
					$fields[$microsatcord] = switch_micro($fields[$microsatcord]);
					$interruption = switch_nucl($interruption) unless $interruption eq "IND";
					$interpos = ($microsatlength - $interpos) - $interlen + 2;
# print "turn interpos = $interpos for $fields[$microsatcord]\n" if $printer == 1;
					$relativepos = (100 * $interpos) / $microsatlength;
					$relativepos = (100 * ($interpos-$interlen)) / $microsatlength if $relativepos > 50;
		
		
					$strand = '+' if $strand eq '-';
					$strand = '-' if $strand eq '+';
				}
# print "final relativepos = $relativepos\n" if $printer == 1;
				push(@relativeposes, $relativepos);
			}
			push(@endstatement,join("\t",($exacttags[$species_counter],$sp_chr, $sp_start, $sp_end, $firstmotif,length($firstmotif),$fields[$microsatcord],$strand,$microsatlength,join(",",@interposes),join(",",@relativeposes),join(",",@interruptions), join(",",@interlens))));
		}
		
		else{
			push(@endstatement, join("\t",$exacttags[$species_counter],$sp_chr, $sp_start, $sp_end, $firstmotif,length($firstmotif),$fields[$microsatcord],$strand,$microsatlength,"NA","NA","NA", "NA"));
		}
		
		$species_counter++;
	}
	
		$locusmotif = $sameHash{$locusmotif} if exists $sameHash{$locusmotif};
		$locusmotif = $revHash{$locusmotif} if exists $revHash{$locusmotif};
	
		my $endst =  join("\t", @endstatement, $orthHchr, $Hstart, $Hend);
#		print join("\t", @endstatement, $orthHchr,  $Hstart, $Hend), "\n" if $printer == 1; 
	
	
	return (join("\t", @endstatement, $orthHchr, $Hstart, $Hend), $orthHchr, $Hstart, $Hend, $locusmotif, length($locusmotif));
	
}

sub switch_nucl{
	my @strand = split(/\s*/,$_[0]);
	for my $i (0 ... $#strand){
		if ($strand[$i] =~ /c/i) {$strand[$i] = "G";next;}
		if ($strand[$i] =~ /a/i) {$strand[$i] = "T";next;}
		if ($strand[$i] =~ /t/i) { $strand[$i] = "A";next;}
		if ($strand[$i] =~ /g/i) {$strand[$i] = "C";next;}
	}
	return join("",@strand);
}


sub switch_micro{
	my $micro = reverse($_[0]);
	my @strand = split(/\s*/,$micro);
	for my $i (0 ... $#strand){
		if ($strand[$i] =~ /c/i) {$strand[$i] = "G";next;}
		if ($strand[$i] =~ /a/i) {$strand[$i] = "T";next;}
		if ($strand[$i] =~ /t/i) { $strand[$i] = "A";next;}
		if ($strand[$i] =~ /g/i) {$strand[$i] = "C";next;}
		if ($strand[$i] =~ /\[/i) {$strand[$i] = "]";next;}
		if ($strand[$i] =~ /\]/i) {$strand[$i] = "[";next;}
	}
	return join("",@strand);
}
sub decipher_history{
	my $printer = 0;
	my ($mutations_array, $tags_string, $nodes, $branches_hash, $tree_analysis, $confirmation_string, $alivehash) = @_;
	my %mutations_hash=();
	foreach my $mutation (@$mutations_array){
# print "mutation = $mutation\n" if $printer == 1;
		my %local = $mutation =~ /([\S ]+)=([\S ]+)/g;
		push @{$mutations_hash{$local{"node"}}},$mutation; 
# print "just for confirmation: $local{node} pushed as: $mutation\n" if $printer == 1;
	}
	my @nodes;
	my @birth_steps=();
	my @death_steps=();
	
	my @tags=split(/\s*/,$tags_string);
	my @confirmation=split(/\s+/,$confirmation_string);
	my %info=();
	
	for my $i (0 ... $#tags){
		$info{$tags[$i]}=$confirmation[$i];
# print "feeding info: $tags[$i] = $info{$tags[$i]}\n" if $printer == 1;
	}
	
	for my $keys (@$nodes) {
		foreach my $key (@$keys){
#			print "current key  = $key\n";
			my $copykey = $key;
			$copykey =~ s/[\W ]+//g;
			my @copykeys=split(/\s*/,$copykey);
			my $states=();
			foreach my $copy (@copykeys){
				$states=$states.$info{$copy};
			}
# print "reduced key = $copykey and state = $states\n" if $printer == 1;
			
			if (exists $mutations_hash{$key}) {
				
				if ($states=~/\+/){
					push @birth_steps, @{$mutations_hash{$key}};
					$birth_steps[$#birth_steps] =~ s/\S+=//g;
					delete $mutations_hash{$key};
				}
				else{
					push @death_steps, @{$mutations_hash{$key}};	
					$death_steps[$#death_steps] =~ s/\S+=//g;
					delete $mutations_hash{$key};
				}
			}
		}
	}
# print "conformation = $confirmation_string\n" if $printer == 1;
	push (@birth_steps, "NULL") if scalar(@birth_steps) == 0;
	push (@death_steps, "NULL") if scalar(@death_steps) == 0;
# print "birth steps = ",join("\n",@birth_steps)," and death steps = ",join("\n",@death_steps),"\n" if $printer == 1;
	return \@birth_steps, \@death_steps;
}

sub fillAlignmentGaps{
	my $printer = 0;
# print "received: @_\n" if $printer == 1;
	my ($tree, $sequences, $alignment, $tagarray, $microsathash, $nonmicrosathash, $motif, $tree_analysis, $threshold, $microsatstarts) = @_;
# print "in fillAlignmentGaps.. tree = $tree \n" if $printer == 1;
	my %sequence_hash=();

	my @phases = ();
	my $concat = $motif.$motif;
	my $motifsize = length($motif);
	
	for my $i (1 ... $motifsize){
		push @phases, substr($concat, $i, $motifsize);
	}

	my $concatalignment = ();
	foreach my $tag (@tags){
		$concatalignment = $concatalignment.$alignment->{$tag};
	}
#	print "returningg NULL","NULL","NULL", "NULL\n" if $concatalignment !~ /-/;
	return 0, "NULL","NULL","NULL", "NULL","NULL" if $concatalignment !~ /-/;
	
	

	my %node_sequences_temp=();
	my %node_alignments_temp =();			#NEW, Nov 28 2008
	
	my @tags=();
	my @locus_sequences=();
	my %alivehash=();

#	print "IN fillAlignmentGaps\n";# <STDIN>;
	my %fillrecord = ();
	
	my $change = 0;
	foreach my $tag (@$tagarray) { 
		#print "adding: $tag\n";
		push(@tags, $tag);
		if (exists $microsathash->{$tag}){
			my $micro = $microsathash->{$tag};
			my $orig_micro = $micro;
			($micro, $fillrecord{$tag}) = fillgaps($micro, \@phases);
			$change = 1 if uc($micro) ne uc($orig_micro);
			$node_sequences_temp{$tag}=$micro if $microsathash->{$tag} ne "NULL"; 
		}
		if (exists $nonmicrosathash->{$tag}){
			my $micro = $nonmicrosathash->{$tag};
			my $orig_micro = $micro;
			($micro, $fillrecord{$tag}) = fillgaps($micro, \@phases);
			$change = 1 if uc($micro) ne uc($orig_micro);
			$node_sequences_temp{$tag}=$micro if $nonmicrosathash->{$tag} ne "NULL"; 
		}
		
		if (exists $alignment->{$tag}){
			my $micro = $alignment->{$tag};
			my $orig_micro = $micro;
			($micro, $fillrecord{$tag}) = fillgaps($micro, \@phases);
			$change = 1 if uc($micro) ne uc($orig_micro);
			$node_alignments_temp{$tag}=$micro if $alignment->{$tag} ne "NULL"; 			
		}
		
		#print "adding to node_sequences: $tag = ",$node_sequences_temp{$tag},"\n" if $printer == 1;
		#print "adding to node_alignments: $tag = ",$node_alignments_temp{$tag},"\n" if $printer == 1;
	}


	my %node_sequences=();
	my %node_alignments =();			#NEW, Nov 28 2008
	foreach my $tag (@$tagarray) { 
		$node_sequences{$tag} = join ".",split(/\s*/,$node_sequences_temp{$tag});
		$node_alignments{$tag} = join ".",split(/\s*/,$node_alignments_temp{$tag});		
	}	
# print "\n", "#" x 50, "\n" if $printer == 1;
	foreach my $tag (@tags){
# print "$tag: $alignment->{$tag} = $node_alignments{$tag}\n" if $printer == 1;	
	}
# print "\n", "#" x 50, "\n" if $printer == 1;
#	print "change = $change\n";
	#<STDIN> if $concatalignment=~/\-/;
	
#	<STDIN> if $printer == 1 && $concatalignment =~ /\-/;

	return 0, "NULL","NULL","NULL", "NULL", "NULL" if $change == 0;
	
	my ($nodes_arr, $branches_hash) = get_nodes($tree);
	my @nodes=@$nodes_arr;
# print "recieved nodes = @nodes\n" if $printer == 1; 
	
	
	#POPULATE branches_hash WITH INFORMATION ABOUT LIVESTATUS
	foreach my $keys (@nodes){
		my @pair = @$keys;
		my $joint = "(".join(", ",@pair).")";
		my $copykey = join "", @pair;
		$copykey =~ s/[\W ]+//g;
# print "for node: $keys, copykey = $copykey and joint = $joint\n" if $printer == 1;
		my $livestatus = 1;
		foreach my $copy (split(/\s*/,$copykey)){
			$livestatus = 0 if !exists $alivehash{$copy};
		}
		$alivehash{$joint} = $joint if !exists $alivehash{$joint} && $livestatus == 1;
# print "alivehash = $alivehash{$joint}\n" if exists $alivehash{$joint} && $printer == 1;
	}
	

	
	@nodes = reverse(@nodes); #1 THIS IS IN ORDER TO GO THROUGH THE TREE FROM LEAVES TO ROOT.

	my @mutations_array=();

	my $joint = ();
	foreach my $node (@nodes){
		my @pair = @$node; 
# print "now in the nodes for loop, pair = @pair\n and sequences=\n" if $printer == 1;
		$joint = "(".join(", ",@pair).")"; 	
# print "joint = $joint \n" if $printer == 1; 
		my @pair_sequences=();

		foreach my $tag (@pair){
# print "tag = $tag: " if $printer == 1;
#			print $node_alignments{$tag},"\n" if $printer == 1;
			push @pair_sequences, $node_alignments{$tag};
		}
#		print "fillgap\n";
		my ($compared, $substitutions_list) = base_by_base_simple($motif,\@pair_sequences, scalar(@pair_sequences), @pair, $joint);
		$node_alignments{$joint}=$compared;
		push(  @mutations_array,split(/:/,$substitutions_list));
# print "newly added to node_sequences: $node_alignments{$joint} and list of mutations = @mutations_array\n" if $printer == 1;
	}
# print "now sending for analyze_mutations: mutation_array=@mutations_array, nodes=@nodes, branches_hash=$branches_hash, alignment=$alignment, tags=@tags, alivehash=%alivehash, node_sequences=\%node_sequences, microsatstarts=$microsatstarts, motif=$motif\n" if $printer == 1;
#	<STDIN> if $printer == 1;
	
	my $analayzed_mutations = analyze_mutations(\@mutations_array, \@nodes, $branches_hash, $alignment, \@tags, \%alivehash, \%node_sequences, $microsatstarts, $motif);

#	print "returningt: ", $analayzed_mutations, \@nodes,"\n" if scalar @mutations_array > 0;;
#	print "returningy: NULL, NULL, NULL " if scalar @mutations_array == 0 && $printer == 1;
# print "final node alignment after filling for $joint= " if $printer == 1;
# print "$node_alignments{$joint}\n" if $printer == 1;
	

	return 1, $analayzed_mutations, \@nodes, $branches_hash, \%alivehash, $node_alignments{$joint} if scalar @mutations_array > 0 ;
	return 1, "NULL","NULL","NULL", "NULL", "NULL" if scalar @mutations_array == 0;
}



sub add_mutation{
	my $printer = 0;
# print "IN SUBROUTUNE add_mutation.. information received = @_\n" if $printer == 1;
	my ($i , $bite, $to, $from) = @_;
# print "bite = $bite.. all received info = ",join("^", @_),"\n" if $printer == 1;
# print "to=$to\n" if $printer == 1;
# print "tis split = ",join(" and ",split(/!/,$to)),"\n" if $printer == 1;
	my @toields = split "!",$to;
# print "toilds  = @toields\n" if $printer == 1;
	my @mutations=();
	
	foreach my $toield (@toields){
		my @toinfo=split(":",$toield);
# print " at toinfo=@toinfo \n" if $printer == 1;
		next if  $toinfo[1] =~ /$from/i;
		my @mutation = @toinfo if $toinfo[1] !~ /$from/i;
# print "adding to mutaton list: ", join(",", "node=$mutation[0]","type=substitution" ,"position=$i", "from=$from", "to=$mutation[1]", "insertion=", "deletion="),"\n" if $printer == 1;
		push (@mutations, join("\t", "node=$mutation[0]","type=substitution" ,"position=$i", "from=$from", "to=$mutation[1]", "insertion=", "deletion="));
	}
	return @mutations;
}


sub add_bases{

	my $printer = 0;
# print "IN SUBROUTUNE add_bases.. information received = @_\n" if $printer == 1;
	my ($optional0, $optional1, $pair0, $pair1,$joint) = @_;
	my $total_list=();

	my @total_list0=split(/!/,$optional0);
	my @total_list1=split(/!/,$optional1);
	my @all_list=();
	my %total_hash0=();
	foreach my $entry (@total_list0) { 		
		$entry = uc $entry; 
		$entry =~ /(\S+):(\S+)/; 
		$total_hash0{$2}=$1;
		push @all_list, $2; 
	}

	my %total_hash1=();
	foreach my $entry (@total_list1) { 		
		$entry = uc $entry; 
		$entry =~ /(\S+):(\S+)/; 
		$total_hash1{$2}=$1;
		push @all_list, $2; 
	}

	my %alphabetical_hash=();
	my @return_options=();	

	for my $i (0 ... $#all_list){
		my $alph = $all_list[$i];
		if (exists $total_hash0{$alph} && exists $total_hash1{$alph}){
			push(@return_options, $joint.":".$alph);
			delete $total_hash0{$alph}; delete $total_hash1{$alph};
		}
		if (exists $total_hash0{$alph} && !exists $total_hash1{$alph}){
			push(@return_options, $pair0.":".$alph);
			delete $total_hash0{$alph};
		}
		if (!exists $total_hash0{$alph} && exists $total_hash1{$alph}){
			push(@return_options, $pair1.":".$alph);
			delete $total_hash1{$alph};
		}

	}
# print "returning ",join "!",@return_options,"\n" if $printer == 1; 
	return join "!",@return_options;

}


sub fillgaps{
#	print "IN fillgaps: @_\n";	
	my ($micro, $phasesinput) = @_;
	#print "in microsathash ,,.. micro = $micro\n";
	return $micro if $micro !~ /\-/;
	my $orig_micro = $micro;
	my @phases = @$phasesinput;
	
	my %tested_patterns = ();
	
	foreach my $phase (@phases){
	#	print "considering phase: $phase\n";
		my @phase_prefixes = ();
		my @prephase_left_contexts = ();
		my @prephase_right_contexts = ();
		my @pregapsize = ();
		my @prepostfilins = ();
	
		my @phase_suffixes;
		my @suffphase_left_contexts;
		my @suffphase_right_contexts;
		my @suffgapsize;
		my @suffpostfilins;
	
		my @postfilins = ();
		my $motifsize = length($phases[0]);
		
		my $change = 0;
	
		for my $u (0 ... $motifsize-1){
			my $concat = $phase.$phase.$phase.$phase;
			my @concatarr = split(/\s*/, $concat);
			my $l = 0;
			while ($l < $u){
				shift @concatarr;
				$l++;
			}
			$concat = join ("", @concatarr);
			
			for my $t (0 ... $motifsize-1){
				for my $k (1 ... $motifsize-1){
					push @phase_prefixes, substr($concat, $motifsize+$t, $k);
					push @prephase_left_contexts, substr ($concat, $t, $motifsize);
					push @prephase_right_contexts, substr ($concat, $motifsize+$t+$k+($motifsize-$k), 1);
					push @pregapsize, $k;
					push @prepostfilins, substr($concat,  $motifsize+$t+$k, ($motifsize-$k));
				#	print "reading: $concat, t=$t, k=$k prefix: $prephase_left_contexts[$#prephase_left_contexts] $phase_prefixes[$#phase_prefixes] -x$pregapsize[$#pregapsize] $prephase_right_contexts[$#prephase_right_contexts]\n";
				#	print "phase_prefixes = $phase_prefixes[$#phase_prefixes]\n";
				#	print "prephase_left_contexts = $prephase_left_contexts[$#prephase_left_contexts]\n";
				#	print "prephase_right_contexts = $prephase_right_contexts[$#prephase_right_contexts]\n";
				#	print "pregapsize = $pregapsize[$#pregapsize]\n";
				#	print "prepostfilins = $prepostfilins[$#prepostfilins]\n";
				}
			}
		}
	
	#	print "looking if $micro =~ /($phase\-{$motifsize})/i || $micro =~ /^(\-{$motifsize,}$phase)/i\n";
		if ($micro =~ /($phase\-{$motifsize,})$/i || $micro =~ /^(\-{$motifsize,}$phase)/i){
	#			print "micro: $micro needs further gap removal: $1\n";
			while ($micro =~ /$phase(\-{$motifsize,})$/i || $micro =~ /^(\-{$motifsize,})$phase/i){
			#	print "micro: $micro needs further gap removal: $1\n";
			
			#	print "phase being considered = $phase\n";
				my $num = ();
				$num = $micro =~ s/$phase\-{$motifsize}/$phase$phase/gi if $micro =~ /$phase\-{$motifsize,}/i;
				$num = $micro =~ s/\-{$motifsize}$phase/$phase$phase/gi if $micro =~ /\-{$motifsize,}$phase/i;
			#	print "num = $num\n";
				$change = 1 if $num == 1;
			}				
		}
	
		elsif ($micro =~ /(($phase)+)\-{$motifsize,}(($phase)+)/i){
			while ($micro =~ /(($phase)+)\-{$motifsize,}(($phase)+)/i){
		#		print "checking lengths of $1 and $3 for $micro... \n";
				my $num = ();
				if (length($1) >= length($3)){
		#			print "$micro matches (($phase)+)\-{$motifsize,}(($phase)+) = $1, >= , $3 \n";				
					$num = $micro =~ s/$phase\-{$motifsize}/$phase$phase/gi ;				
				}
				if (length($1) < length($3)){
		#			print "$micro matches (($phase)+)\-{$motifsize,}(($phase)+) = $1, < , $3 \n";
					$num = $micro =~ s/\-{$motifsize}$phase/$phase$phase/gi ;
				}		
	#			print "micro changed to $micro\n";
			}
		}
		elsif ($micro =~ /([A-Z]+)\-{$motifsize,}(($phase)+)/i){
			while ($micro =~ /([A-Z]+)\-{$motifsize,}(($phase)+)/i){		
		#			print "$micro matches ([A-Z]+)\-{$motifsize}(($phase)+) = 1=$1, - , 3=$3 \n";
					my $num = 0;
					$num = $micro =~ s/\-{$motifsize}$phase/$phase$phase/gi ;
			}
		}
		elsif ($micro =~ /(($phase)+)\-{$motifsize,}([A-Z]+)/i){
			while ($micro =~ /(($phase)+)\-{$motifsize,}([A-Z]+)/i){		
			#		print "$micro matches (($phase)+)\-{$motifsize,}([A-Z]+) = 1=$1, - , 3=$3 \n";
					my $num = 0;
					$num = $micro =~ s/$phase\-{$motifsize}/$phase$phase/gi ;				
			}	
		}
	
	#	print "$orig_micro to $micro\n";
		
	#s	<STDIN>;
		
		for my $h (0 ... $#phase_prefixes){
	#		print "searching using prefix : $prephase_left_contexts[$h]$phase_prefixes[$h]\-{$pregapsize[$h]}$prephase_right_contexts[$h]\n";
			my $pattern = $prephase_left_contexts[$h].$phase_prefixes[$h].$pregapsize[$h].$prephase_right_contexts[$h];
	#		print "returning orig_micro = $orig_micro, micro = $micro \n" if exists $tested_patterns{$pattern};
			if ($micro =~ /$prephase_left_contexts[$h]$phase_prefixes[$h]\-{$pregapsize[$h]}$prephase_right_contexts[$h]/i){
				return $orig_micro if exists $tested_patterns{$pattern};
				while ($micro =~ /($prephase_left_contexts[$h]$phase_prefixes[$h]\-{$pregapsize[$h]}$prephase_right_contexts[$h])/i){
					$tested_patterns{$pattern} = $pattern;
	#				print "micro: $micro needs further gap removal: $1\n";
				
	#				print "prefix being considered = $phase_prefixes[$h]\n";
					my $num = ();
					$num = ($micro =~ s/$prephase_left_contexts[$h]$phase_prefixes[$h]\-{$pregapsize[$h]}$prephase_right_contexts[$h]/$prephase_left_contexts[$h]$phase_prefixes[$h]$prepostfilins[$h]$prephase_right_contexts[$h]/gi) ;
	#				print "num = $num, micro = $micro\n";
					$change = 1 if $num == 1;
					
					return $orig_micro if $num > 1;
				}				
			}
		
		}
	}
	return $orig_micro if length($micro) != length($orig_micro);
	return $micro;
}

sub selectMutationArray{
	my $printer =0;

	my $oldmutspt  = $_[0];
	my $newmutspt  = $_[1];
	my $tagstringpt = $_[2];
	my $alivehashpt = $_[3];
	my $alignmentpt = $_[4];
	my $motif = $_[5];

	my @alivehasharr=();
	
	my @tags = @$tagstringpt;
	my $alignmentln = length($alignmentpt->{$tags[0]});
	
	foreach my $key (keys %$alivehashpt) { push @alivehasharr, $key; }
	
	my %newside = ();
	my %oldside = ();
	my %newmuts = ();
	
	my %commons = ();
	my %olds = ();
	foreach my $old (@$oldmutspt){
		$olds{$old} = 1;
	}
	foreach my $new (@$newmutspt){
		$commons{$new} = 1 if exists $olds{$new};;
	}
		
	
	foreach my $pos ( 0 ... $alignmentln){
		#print "pos = $pos\n" if $printer == 1;
		my $newyes = 0;
		foreach my $mut (@$newmutspt){
			$newmuts{$mut} = 1;
			chomp $mut;
			$newyes++;
			 $mut =~ s/=\t/= \t/g;
			 $mut =~ s/=$/= /g;

			 $mut =~ /node=([A-Z\(\), ]+)\stype=([a-zA-Z ]+)\sposition=([0-9 ]+)\sfrom=([a-zA-Z\- ]+)\sto=([a-zA-Z\- ]+)\sinsertion=([a-zA-Z\- ]+)\sdeletion=([a-zA-Z\- ]+)/;
			my $node = $1;
			next if $3 != $pos;
# print "new mut = $mut\n" if $printer == 1;
# print "node = $node, pos = $3 ... and alivehasharr = >@alivehasharr<\n" if $printer == 1;
			my $alivenode = 0;
			foreach my $key (@alivehasharr){
				$alivenode = 1 if $key =~ /$node/;
			}
		#	next if $alivenode == 0;
			my $indel_type = " ";
			if ($2 eq "insertion" || $2 eq "deletion"){
				my $thisindel = ();
				$thisindel = $6 if $2 eq "insertion";
				$thisindel = $7 if $2 eq "deletion";
				
				$indel_type = "i".checkIndelType($node, $thisindel, $motif,$alignmentpt,$3, $2) if $2 eq "insertion";
				$indel_type = "d".checkIndelType($node, $thisindel, $motif,$alignmentpt, $3, $2) if $2 eq "deletion";
				$indel_type = $indel_type."f" if $indel_type =~ /mot/ && length($thisindel) >= length($motif);
			}
# print "indeltype = $indel_type\n" if $printer == 1;
			my $added = 0;
			
			if (exists $newside{$pos} && $indel_type =~ /[a-z]+/){
# print "we have a preexisting one for $pos\n" if $printer == 1;
				my @preexisting = @{$newside{$pos}};
				foreach my $pre (@preexisting){
# print "looking at $pre\n" if $printer == 1;
					next if $pre !~ /node=$node/;
					next if $pre !~ /indeltype=([a-z]+)/;
					my $currtype = $1;
					
					if ($currtype =~ /inon/ && $indel_type =~ /dmot/){
						delete $newside{$pos};
						push @{$newside{$pos}}, $pre;
						$added = 1;
					}
					if ($currtype =~ /dnon/ && $indel_type =~ /imot/){
						delete $newside{$pos};
						push @{$newside{$pos}}, $pre;
						$added = 1;
					}
					if ($currtype =~ /dmot/ && $indel_type =~ /inon/){
						delete $newside{$pos};
						push @{$newside{$pos}}, $mut."\tindeltype=$indel_type";
						$added = 1;
					}
					if ($currtype =~ /imot/ && $indel_type =~ /dnon/){
						delete $newside{$pos};
						push @{$newside{$pos}}, $mut."\tindeltype=$indel_type";
						$added = 1;
					}					
				}
			}
# print "added = $added\n" if $printer == 1;
			push @{$newside{$pos}}, $mut."\tindeltype=$indel_type" if $added == 0;
# print "for new pos,: $pos we have: @{$newside{$pos}}\n " if $printer == 1;
		}
	}
	
	foreach my $pos ( 0 ... $alignmentln){
		my $oldyes = 0;
		foreach my $mut (@$oldmutspt){
			chomp $mut;
			$oldyes++;
			 $mut =~ s/=\t/= \t/g;
			 $mut =~ s/=$/= /g;
			$mut =~ /node=([A-Z\(\), ]+)\ttype=([a-zA-Z ]+)\tposition=([0-9 ]+)\tfrom=([a-zA-Z\- ]+)\tto=([a-zA-Z\- ]+)\tinsertion=([a-zA-Z\- ]+)\tdeletion=([a-zA-Z\- ]+)/;
			my $node = $1;
			next if $3 != $pos;
# print "old mut = $mut\n" if $printer == 1;
			my $alivenode = 0;
			foreach my $key (@alivehasharr){
				$alivenode = 1 if $key =~ /$node/;
			}
			#next if $alivenode == 0;
			my $indel_type = " ";
			if ($2 eq "insertion" || $2 eq "deletion"){
				$indel_type = "i".checkIndelType($node, $6, $motif,$alignmentpt, $3, $2) if $2 eq "insertion";
				$indel_type = "d".checkIndelType($node, $7, $motif,$alignmentpt, $3, $2) if $2 eq "deletion";
				next if $indel_type =~/non/;
			}
			else{ next;}

			my $imp=0;
			$imp = 1 if $indel_type =~ /dmot/ && $alivenode == 0;
			$imp = 1 if $indel_type =~ /imot/ && $alivenode == 1;
			
			
			if (exists $newside{$pos} && $indel_type =~ /[a-z]+/){
				my @preexisting = @{$newside{$pos}};
# print "we have a preexisting one for $pos: @preexisting\n" if $printer == 1;
				next if $imp == 0;
				
				if (scalar(@preexisting) == 1){
					my $foundmut = $preexisting[0];
					$foundmut=~ /node=([A-Z, \(\)]+)/;
					next if $1 eq $node;
					
					if (exists $oldside{$pos} || exists $commons{$foundmut}){
# print "not replacing, but just adding\n" if $printer == 1;
						push @{$newside{$pos}}, $mut."\tindeltype=$indel_type";
						push @{$oldside{$pos}}, $mut."\tindeltype=$indel_type";
						next;
					}
					
					delete $newside{$pos};
					push @{$oldside{$pos}}, $mut."\tindeltype=$indel_type";
					push @{$newside{$pos}}, $mut."\tindeltype=$indel_type";
# print "now  new one is : @{$newside{$pos}}\n" if $printer == 1;
				}
# print "for pos: $pos: @{$newside{$pos}}\n" if $printer == 1;
				next;
			}

			
			my @news = @{$newside{$pos}} if exists $newside{$pos};
# print "mut = $mut and news = @news\n" if $printer == 1; 
			push @{$oldside{$pos}}, $mut."\tindeltype=$indel_type";
			push @{$newside{$pos}}, $mut."\tindeltype=$indel_type";
		}
	}
# print "in the end, our collected mutations = \n" if $printer == 1;
	my @returnarr = ();
	foreach my $key (keys %newside) {push @returnarr,@{$newside{$key}};}
#	print join("\n", @returnarr),"\n" if $printer == 1;
	#<STDIN>;
	return @returnarr;

}


sub checkIndelType{
	my $printer  = 0;
	my $node = $_[0];
	my $indel = $_[1];
	my $motif = $_[2];
	my $alignmentpt = $_[3];
	my $posit = $_[4];
	my $type = $_[5];
	my @phases =();
	my %prephases = ();
	my %postphases = ();
	#print "motif = $motif\n";
# print "IN checkIndelType ... received: @_\n" if $printer == 1;
	my $concat = $motif.$motif.$motif.$motif;
	my $motiflength = length($motif);
	
	if ($motiflength > length ($indel)){
		return "non" if $motif !~ /$indel/i;
		return checkIndelType_ComplexAnalysis($node, $indel, $motif, $alignmentpt, $posit, $type);
	}
	
	my $firstpass = 0;
	for my $y (0 ... $motiflength-1){
		my $phase = substr($concat, $motiflength+$y, $motiflength);
		push @phases, $phase;
		$firstpass = 1 if $indel =~ /$phase/i;
		for my $k (0 ... length($motif)-1){
# print "at: motiflength=$motiflength , y=$y , k=$k.. for pre: $motiflength+$y-$k and post: $motiflength+$y-$k+$motiflength in $concat\n" if $printer == 1;
			my $pre = substr($concat, $motiflength+$y-$k, $k );
			my $post = substr($concat, $motiflength+$y+$motiflength, $k);
# print "adding to phases : $phase - $pre and $post\n" if $printer == 1;
			push @{$prephases{$phase}} , $pre;
			push @{$postphases{$phase}} , $post;			
		}
		
	}
# print "firstpass 1= $firstpass\n" if $printer == 1;
	return "non" if $firstpass ==0;
	$firstpass =0;
	
	foreach my $phase (@phases){
		my @pres = @{$prephases{$phase}};
		my @posts = @{$postphases{$phase}};
		
		foreach my $pre (@pres){
			foreach my $post (@posts){
				
				$firstpass = 1 if $indel =~ /($pre)?($phase)+($post)?/i && length($indel) > (3 * length($motif));
				$firstpass = 1 if $indel =~ /^($pre)?($phase)+($post)?$/i && length($indel) < (3 * length($motif));
# print "matched here : ($pre)?($phase)+($post)?\n" if $printer == 1;
				last if $firstpass == 1;
			}
			last if $firstpass == 1;
		}
		last if $firstpass == 1;
	}
# print "firstpass 2= $firstpass\n" if $printer == 1;
	return "non" if $firstpass ==0;
	return "mot" if $firstpass ==1;	
}


sub checkIndelType_ComplexAnalysis{
	my $printer = 0;
	my $node = $_[0];
	my $indel = $_[1];
	my $motif = $_[2];
	my $alignmentpt = $_[3];
	my $pos = $_[4];
	my $type = $_[5];
	my @speciesinvolved = $node =~ /[A-Z]+/g;
	
	my @seqs = ();
	my $residualseq = length($motif) - length($indel);
# print "IN COMPLEX ANALYSIS ... received: @_  .... speciesinvolved = @speciesinvolved\n" if $printer == 1;
# print "we have position = $pos, sseq = $alignmentpt->{$speciesinvolved[0]}\n" if $printer == 1;
# print "residualseq = $residualseq\n" if $printer == 1;
# print "pos=$pos... got: @_\n" if $printer == 1;
	foreach my $sp (@speciesinvolved){
		my $spseq = $alignmentpt->{$sp};
		#print "orig spseq = $spseq\n";
		my $subseq = ();
		
		if ($type eq "deletion"){
			my @indelparts = split(/\s*/,$indel);
			my @seqparts = split(/\s*/,$spseq);
			
			for my $p ($pos ... $pos+length($indel)-1){
				$seqparts[$p] = shift @indelparts;
			}
			$spseq = join("",@seqparts);
		}
		#print "mod spseq = $spseq\n";
	#	$spseq=~ s/\-//g if $type !~ /deletion/;
# print "substr($spseq, $pos-($residualseq), length($indel)+$residualseq+$residualseq)\n" if $pos > 0 && $pos < (length($spseq) - length($motif))  && $printer == 1;
# print "substr($spseq, 0, length($indel)+$residualseq)\n" if $pos == 0 && $printer == 1;
# print "substr($spseq, $pos - $residualseq, length($indel)+$residualseq)\n" if $pos >= (length($spseq) - length($motif))  && $printer == 1;
		
		$subseq = substr($spseq, $pos-($residualseq), length($indel)+$residualseq+$residualseq) if $pos > 0 && $pos < (length($spseq) - length($motif))  ;
		$subseq = substr($spseq, 0, length($indel)+$residualseq) if $pos == 0;
		$subseq = substr($spseq, $pos - $residualseq, length($indel)+$residualseq) if $pos >= (length($spseq) - length($motif))  ;
# print "spseq = $spseq . subseq=$subseq . type = $type\n" if $printer == 1;
		#<STDIN> if $subseq !~ /[a-z\-]/i; 
		$subseq =~ s/\-/$indel/g if $type =~ /insertion/;
		push @seqs, $subseq;
# print "seqs = @seqs\n" if $printer == 1;
	}
	return "non" if checkIfSeqsIdentical(@seqs) eq "NO";
# print "checking for $seqs[0] \n" if $printer == 1;
	
	my @phases =();
	my %prephases = ();
	my %postphases = ();
	my $concat = $motif.$motif.$motif.$motif;
	my $motiflength = length($motif);
	
	my $firstpass = 0;
	
	for my $y (0 ... $motiflength-1){
		my $phase = substr($concat, $motiflength+$y, $motiflength);
		push @phases, $phase;
		$firstpass = 1 if $seqs[0] =~ /$phase/i;
		for my $k (0 ... length($motif)-1){
			my $pre = substr($concat, $motiflength+$y-$k, $k );
			my $post = substr($concat, $motiflength+$y+$motiflength, $k);
# print "adding to phases : $phase - $pre and $post\n" if $printer == 1;
			push @{$prephases{$phase}} , $pre;
			push @{$postphases{$phase}} , $post;			
		}
		
	}
# print "firstpass 1= $firstpass.. also, res-d = ",(length($seqs[0]))%(length($motif)),"\n" if $printer == 1;
	return "non" if $firstpass ==0;
	$firstpass =0;
	foreach my $phase (@phases){
		
		$firstpass = 1 if $seqs[0] =~ /^($phase)+$/i && ((length($seqs[0]))%(length($motif))) == 0;

		if (((length($seqs[0]))%(length($motif))) != 0){
			my @pres = @{$prephases{$phase}};
			my @posts = @{$postphases{$phase}};
			foreach my $pre (@pres){
				foreach my $post (@posts){
					next if $pre !~ /\S/ && $post !~ /\S/;
					$firstpass = 1 if ($seqs[0] =~ /^($pre)($phase)+($post)$/i || $seqs[0] =~ /^($pre)($phase)+$/i || $seqs[0] =~ /^($phase)+($post)$/i);
# print "caught with $pre $phase $post\n" if $printer == 1;
					last if $firstpass == 1;
				}
				last if $firstpass == 1;
			}
		}
		
		last if $firstpass == 1;
	}
	
	#print "indel = $indel.. motif = $motif.. firstpass 2= mot\n" if $firstpass ==1;	
	#print "indel = $indel.. motif = $motif.. firstpass 2= non\n" if $firstpass ==0;	
	#<STDIN>;# if $firstpass ==1;
	return "non" if $firstpass ==0;
	return "mot" if $firstpass ==1;	

}

sub checkIfSeqsIdentical{
	my @seqs = @_;
	my $identical = 1;
	
	for my $j (1 ... $#seqs){
		$identical = 0 if uc($seqs[0]) ne uc($seqs[$j]); 
	}
	return "NO" if $identical == 0;
	return "YES" if $identical == 1;

}

sub summarizeMutations{
	my $mutspt = $_[0];
	my @muts = @$mutspt;
	my $tree = $_[1];
	
	my @returnarr = ();
	
	for (1 ... 38){
		push @returnarr, "NA";
	}
	push @returnarr, "NULL";
	return @returnarr if $tree eq "NULL" || scalar(@muts) < 1;
	
	
	my @bspecies = ();
	my @dspecies = ();
	my $treecopy = $tree;
	$treecopy =~ s/[\(\)]//g;
	my @treeparts  = split(/[\.,]+/, $treecopy);
	
	for my $part (@treeparts){
		if ($part =~ /\+/){
			$part =~ s/\+//g;
			#my @sp = split(/\s*/, $part);
			#foreach my $p (@sp) {push @bspecies, $p;}
			push @bspecies, $part;
		}
		if ($part =~ /\-/){
			$part =~ s/\-//g;
			#my @sp = split(/\s*/, $part);
			#foreach my $p (@sp) {push @dspecies,  $p;}		
			push @dspecies, $part;			
		}
		
	}
	#print "-------------------------------------------------------\n";
	
	my ($insertions, $deletions, $motinsertions, $motinsertionsf, $motdeletions, $motdeletionsf, $noninsertions, $nondeletions) = (0,0,0,0,0,0,0,0);
	my ($binsertions, $bdeletions, $bmotinsertions,$bmotinsertionsf, $bmotdeletions, $bmotdeletionsf, $bnoninsertions, $bnondeletions) = (0,0,0,0,0,0,0,0);
	my ($dinsertions, $ddeletions, $dmotinsertions,$dmotinsertionsf, $dmotdeletions, $dmotdeletionsf, $dnoninsertions, $dnondeletions) = (0,0,0,0,0,0,0,0);
	my ($ninsertions, $ndeletions, $nmotinsertions,$nmotinsertionsf, $nmotdeletions, $nmotdeletionsf, $nnoninsertions, $nnondeletions) = (0,0,0,0,0,0,0,0);
	my ($substitutions, $bsubstitutions, $dsubstitutions, $nsubstitutions, $indels, $subs) = (0,0,0,0,"NA","NA");

	my @insertionsarr = (" ");
	my @deletionsarr = (" ");
	
	my @substitutionsarr = (" ");
	
	
	foreach my $mut (@muts){
	#	print "mut = $mut\n";
		chomp $mut;
		$mut =~ s/=\t/= /g;
		$mut =~ s/=$/= /g;
		my %mhash = ();
		my @mields = split(/\t/,$mut);
		
		foreach my $m (@mields){
			my @fields = split(/=/,$m);
			next if $fields[1] eq " ";
			$mhash{$fields[0]} = $fields[1];
		}
		
		my $myutype = ();
		my $decided = 0;
		
		my $localnode  = $mhash{"node"};
		$localnode =~ s/[\(\)\. ,]//g;

		
		foreach my $s (@bspecies){
			if ($localnode eq $s)		{
				$decided = 1; $myutype = "b";
			}
		}
		
		foreach my $s (@dspecies){
			if ($localnode eq $s)		{
				$decided = 1; $myutype = "d";
			}
		}

		$myutype = "n" if $decided != 1;
		
		
	#	print "tree=$tree, birth species=@bspecies, death species=@dspecies, node=$mhash{node}  .. myutype=$myutype .. \n";		
	#	<STDIN> if $mhash{"type"} eq "insertion" && $myutype eq "b";
		
		
		if ($mhash{"type"} eq "substitution"){
			$substitutions++;
			$bsubstitutions++ if $myutype eq "b";
			$dsubstitutions++ if $myutype eq "d";
			$nsubstitutions++ if $myutype eq "n";
	#		print "substitution: from= $mhash{from}, to = $mhash{to}, and type = myutype\n";
			push @substitutionsarr, "$mhash{position}:".$mhash{"from"}.">".$mhash{"to"} if $myutype eq "b";
			push @substitutionsarr, "$mhash{position}:".$mhash{"from"}.">".$mhash{"to"} if $myutype eq "d";
			push @substitutionsarr, "$mhash{position}:".$mhash{"from"}.">".$mhash{"to"} if $myutype eq "n";
	#		print "substitutionsarr = @substitutionsarr\n";
	#		<STDIN>;
		}
		else{
			#print "tree=$tree, birth species=@bspecies, death species=@dspecies, node=$mhash{node}  .. myutype=$myutype .. indeltype=$mhash{indeltype}\n";		
			if ($mhash{"type"} eq "deletion"){
				$deletions++;
				
				$motdeletions++ if $mhash{"indeltype"} =~ /dmot/;
				$motdeletionsf++ if $mhash{"indeltype"} =~ /dmotf/;
				
				$nondeletions++ if $mhash{"indeltype"} =~ /dnon/;
				
				$bdeletions++ if $myutype eq "b";
				$ddeletions++ if $myutype eq "d";
				$ndeletions++ if $myutype eq "n";

				$bmotdeletions++ if $mhash{"indeltype"} =~ /dmot/ && $myutype eq "b";
				$bmotdeletionsf++ if $mhash{"indeltype"} =~ /dmotf/ && $myutype eq "b";
				$bnondeletions++ if $mhash{"indeltype"} =~ /dnon/ && $myutype eq "b";

				$dmotdeletions++ if $mhash{"indeltype"} =~ /dmot/ && $myutype eq "d";
				$dmotdeletionsf++ if $mhash{"indeltype"} =~ /dmotf/ && $myutype eq "d";
				$dnondeletions++ if $mhash{"indeltype"} =~ /dnon/ && $myutype eq "d"; 

				$nmotdeletions++ if $mhash{"indeltype"} =~ /dmot/ && $myutype eq "n";
				$nmotdeletionsf++ if $mhash{"indeltype"} =~ /dmotf/ && $myutype eq "n";
				$nnondeletions++ if $mhash{"indeltype"} =~ /dnon/ && $myutype eq "n";
				
				push @deletionsarr, "$mhash{indeltype}:$mhash{position}:".$mhash{"deletion"} if $myutype eq "b";
				push @deletionsarr, "$mhash{indeltype}:$mhash{position}:".$mhash{"deletion"} if $myutype eq "d";
				push @deletionsarr, "$mhash{indeltype}:$mhash{position}:".$mhash{"deletion"} if $myutype eq "n";
			}

			if ($mhash{"type"} eq "insertion"){
				$insertions++;
				
				$motinsertions++ if $mhash{"indeltype"} =~ /imot/;
				$motinsertionsf++ if $mhash{"indeltype"} =~ /imotf/;
				$noninsertions++ if $mhash{"indeltype"} =~ /inon/;
				
				$binsertions++ if $myutype eq "b";
				$dinsertions++ if $myutype eq "d";
				$ninsertions++ if $myutype eq "n";

				$bmotinsertions++ if $mhash{"indeltype"} =~ /imot/ && $myutype eq "b";
				$bmotinsertionsf++ if $mhash{"indeltype"} =~ /imotf/ && $myutype eq "b";
				$bnoninsertions++ if $mhash{"indeltype"} =~ /inon/ && $myutype eq "b";

				$dmotinsertions++ if $mhash{"indeltype"} =~ /imot/ && $myutype eq "d";
				$dmotinsertionsf++ if $mhash{"indeltype"} =~ /imotf/ && $myutype eq "d";
				$dnoninsertions++ if $mhash{"indeltype"} =~ /inon/ && $myutype eq "d"; 

				$nmotinsertions++ if $mhash{"indeltype"} =~ /imot/ && $myutype eq "n";
				$nmotinsertionsf++ if $mhash{"indeltype"} =~ /imotf/ && $myutype eq "n";
				$nnoninsertions++ if $mhash{"indeltype"} =~ /inon/ && $myutype eq "n";

				push @insertionsarr, "$mhash{indeltype}:$mhash{position}:".$mhash{"insertion"} if $myutype eq "b";
				push @insertionsarr, "$mhash{indeltype}:$mhash{position}:".$mhash{"insertion"} if $myutype eq "d";
				push @insertionsarr, "$mhash{indeltype}:$mhash{position}:".$mhash{"insertion"} if $myutype eq "n";
				
			}
		}
	}
	
	
	
	$indels = "ins=".join(",",@insertionsarr).";dels=".join(",",@deletionsarr) if scalar(@insertionsarr) > 1 || scalar(@deletionsarr) > 1 ;
	$subs = join(",",@substitutionsarr) if scalar(@substitutionsarr) > 1;
	$indels =~ s/ //g;
	$subs =~ s/ //g  ;
 	
 	#print "indels = $indels, subs=$subs\n";
 	##<STDIN> if $indels =~ /[a-zA-Z0-9]/ || $subs =~ /[a-zA-Z0-9]/ ;
	#print "tree = $tree, indels = $indels, subs = $subs, bspecies = @bspecies, dspecies = @dspecies \n";
	my @returnarray = ();
	
	push (@returnarray, $indels, $subs) ;
		
	push @returnarray, $tree;
	
	my @copy = @returnarray;
	#print "\n\nreturnarray = @returnarray ... binsertions=$binsertions dinsertions=$dinsertions bsubstitutions=$bsubstitutions dsubstitutions=$dsubstitutions\n";
	#<STDIN>;
	return (@returnarray);
	
}

sub selectBetterTree{
	my $printer = 1;
	my $treestudy = $_[0];
	my $alt = $_[1];
	my $mutspt = $_[2];
	my @muts = @$mutspt;
	my @trees = (); my @alternatetrees=();

	@trees  = split(/\|/,$treestudy) if $treestudy =~ /\|/;
	@alternatetrees  = split(/[\|;]/,$alt) if $alt =~ /[\|;\(\)]/;

	$trees[0]  = $treestudy if $treestudy !~ /\|/;
	$alternatetrees[0]  = $alt if $alt !~ /[\|;\(\)]/;
	
	my @alltrees = (@trees, @alternatetrees);
#	push(@alltrees,@alternatetrees);
	
	my %mutspecies = ();
# print "IN selectBetterTree..treestudy=$treestudy. alt=$alt. for: @_. trees=@trees<. alternatetrees=@alternatetrees\n" if $printer == 1;
	#<STDIN>;
	foreach my $mut (@muts){
#		print colored ['green'],"mut = $mut\n" if $printer == 1;
		$mut =~ /node=([A-Z,\(\) ]+)/;
		my $node  = $1;
		$node =~s/[,\(\) ]+//g;
		my @indivspecies = $node =~ /[A-Z]+/g;
		#print "adding node: $node\n" if $printer == 1;
		$mutspecies{$node} = $node;
		
	}
	
	my @treerecords = ();
	my $treecount = -1;
	foreach my $tree (@alltrees){
# print "checking with tree $tree\n" if $printer == 1;
		$treecount++;
		$treerecords[$treecount] = 0;
		my @indivspecies = ($tree =~ /[A-Z]+/g);
# print "indivspecies=@indivspecies\n" if $printer == 1;
		foreach my $species (@indivspecies){
# print "checkin if exists species: $species\n" if $printer == 1;
			$treerecords[$treecount]+=2 if exists $mutspecies{$species} && $mutspecies{$species} !~ /indeltype=[a-z]mot/;
			$treerecords[$treecount]+=1.5 if exists $mutspecies{$species} && $mutspecies{$species} =~ /indeltype=[a-z]mot/;
			$treerecords[$treecount]-- if !exists $mutspecies{$species};
		}
# print "for tree $tree, our treecount = $treerecords[$treecount]\n" if $printer == 1;
	}
	
	my @best_tree = array_largest_number_arrayPosition(@treerecords);
# print "treerecords = @treerecords. hence, best tree = @best_tree = $alltrees[$best_tree[0]], $treerecords[$best_tree[0]]\n" if $printer == 1;
	#<STDIN>;	
	return ($alltrees[$best_tree[0]], $treerecords[$best_tree[0]]) if scalar(@best_tree) == 1;
# print "best_tree[0] = $best_tree[0], and treerecords = $treerecords[$best_tree[0]]\n" if $printer == 1;
	return ("NULL", -1) if $treerecords[$best_tree[0]] < 1;
	my $rando = int(rand($#trees));
	return ($alltrees[$rando], $treerecords[$rando]) if scalar(@best_tree) > 1;
	
}




sub load_sameHash{
	#my $g = %$_[0];
	$sameHash{"CAGT"}="AGTC";
	$sameHash{"ATGA"}="AATG";
	$sameHash{"CAAC"}="AACC";
	$sameHash{"GGAA"}="AAGG";
	$sameHash{"TAAG"}="AAGT";
	$sameHash{"CGAG"}="AGCG";
	$sameHash{"TAGG"}="AGGT";
	$sameHash{"GCAG"}="AGGC";
	$sameHash{"TAGA"}="ATAG";
	$sameHash{"TGA"}="ATG";
	$sameHash{"CAAG"}="AAGC";
	$sameHash{"CTAA"}="AACT";
	$sameHash{"CAAT"}="AATC";
	$sameHash{"GTAG"}="AGGT";
	$sameHash{"GAAG"}="AAGG";
	$sameHash{"CGA"}="ACG";
	$sameHash{"GTAA"}="AAGT";
	$sameHash{"ACAA"}="AAAC";
	$sameHash{"GCGG"}="GGGC";
	$sameHash{"ATCA"}="AATC";
	$sameHash{"TAAC"}="AACT";
	$sameHash{"GGCA"}="AGGC";
	$sameHash{"TGAG"}="AGTG";
	$sameHash{"AACA"}="AAAC";
	$sameHash{"GAGC"}="AGCG";
	$sameHash{"ACCA"}="AACC";
	$sameHash{"TGAA"}="AATG";
	$sameHash{"ACA"}="AAC";
	$sameHash{"GAAC"}="AACG";
	$sameHash{"GCA"}="AGC";
	$sameHash{"CCAC"}="ACCC";
	$sameHash{"CATA"}="ATAC";
	$sameHash{"CAC"}="ACC";
	$sameHash{"TACA"}="ATAC";
	$sameHash{"GGAC"}="ACGG";
	$sameHash{"AGA"}="AAG";
	$sameHash{"ATAA"}="AAAT";
	$sameHash{"CA"}="AC";
	$sameHash{"CCCA"}="ACCC";
	$sameHash{"TCAA"}="AATC";
	$sameHash{"CAGA"}="AGAC";
	$sameHash{"AATA"}="AAAT";
	$sameHash{"CCA"}="ACC";
	$sameHash{"AGAA"}="AAAG";
	$sameHash{"AGTA"}="AAGT";
	$sameHash{"GACG"}="ACGG";
	$sameHash{"TCAG"}="AGTC";
	$sameHash{"ACGA"}="AACG";
	$sameHash{"CGCA"}="ACGC";
	$sameHash{"GAGT"}="AGTG";
	$sameHash{"GA"}="AG";
	$sameHash{"TA"}="AT";
	$sameHash{"TAA"}="AAT";
	$sameHash{"CAG"}="AGC";
	$sameHash{"GATA"}="ATAG";
	$sameHash{"GTA"}="AGT";
	$sameHash{"CCAA"}="AACC";
	$sameHash{"TAG"}="AGT";
	$sameHash{"CAAA"}="AAAC";
	$sameHash{"AAGA"}="AAAG";
	$sameHash{"CACG"}="ACGC";
	$sameHash{"GTCA"}="AGTC";
	$sameHash{"GGA"}="AGG";
	$sameHash{"GGAT"}="ATGG";
	$sameHash{"CGGG"}="GGGC";
	$sameHash{"CGGA"}="ACGG";
	$sameHash{"AGGA"}="AAGG";
	$sameHash{"TAAA"}="AAAT";
	$sameHash{"GAGA"}="AGAG";
	$sameHash{"ACTA"}="AACT";
	$sameHash{"GCGA"}="AGCG";
	$sameHash{"CACA"}="ACAC";
	$sameHash{"AGAT"}="ATAG";
	$sameHash{"GAGG"}="AGGG";
	$sameHash{"CGAC"}="ACCG";
	$sameHash{"GGAG"}="AGGG";
	$sameHash{"GCCA"}="AGCC";
	$sameHash{"CCAG"}="AGCC";
	$sameHash{"GAAA"}="AAAG";
	$sameHash{"CAGG"}="AGGC";
	$sameHash{"GAC"}="ACG";
	$sameHash{"CAA"}="AAC";
	$sameHash{"GACC"}="ACCG";
	$sameHash{"GGCG"}="GGGC";
	$sameHash{"GGTA"}="AGGT";
	$sameHash{"AGCA"}="AAGC";
	$sameHash{"GATG"}="ATGG";
	$sameHash{"GTGA"}="AGTG";
	$sameHash{"ACAG"}="AGAC";
	$sameHash{"CGG"}="GGC";
	$sameHash{"ATA"}="AAT";
	$sameHash{"GACA"}="AGAC";
	$sameHash{"GCAA"}="AAGC";
	$sameHash{"CAGC"}="AGCC";
	$sameHash{"GGGA"}="AGGG";
	$sameHash{"GAG"}="AGG";
	$sameHash{"ACAT"}="ATAC";
	$sameHash{"GAAT"}="AATG";
	$sameHash{"CACC"}="ACCC";
	$sameHash{"GAT"}="ATG";
	$sameHash{"GCG"}="GGC";
	$sameHash{"GCAC"}="ACGC";
	$sameHash{"GAA"}="AAG";
	$sameHash{"TGGA"}="ATGG";
	$sameHash{"CCGA"}="ACCG";
	$sameHash{"CGAA"}="AACG";
}



sub load_revHash{
	$revHash{"CTGA"}="AGTC";
	$revHash{"TCTT"}="AAAG";
	$revHash{"CTAG"}="AGCT";
	$revHash{"GGTG"}="ACCC";
	$revHash{"GCC"}="GGC";
	$revHash{"GCTT"}="AAGC";
	$revHash{"GCGT"}="ACGC";
	$revHash{"GTTG"}="AACC";
	$revHash{"CTCC"}="AGGG";
	$revHash{"ATC"}="ATG";
	$revHash{"CGAT"}="ATCG";
	$revHash{"TTAA"}="AATT";
	$revHash{"GTTC"}="AACG";
	$revHash{"CTGC"}="AGGC";
	$revHash{"TCGA"}="ATCG";
	$revHash{"ATCT"}="ATAG";
	$revHash{"GGTT"}="AACC";
	$revHash{"CTTA"}="AAGT";
	$revHash{"TGGC"}="AGCC";
	$revHash{"CCG"}="GGC";
	$revHash{"CGGC"}="GGCC";
	$revHash{"TTAG"}="AACT";
	$revHash{"GTG"}="ACC";
	$revHash{"CTTT"}="AAAG";
	$revHash{"TGCA"}="ATGC";
	$revHash{"CGCT"}="AGCG";
	$revHash{"TTCC"}="AAGG";
	$revHash{"CT"}="AG";
	$revHash{"C"}="G";
	$revHash{"CTCT"}="AGAG";
	$revHash{"ACTT"}="AAGT";
	$revHash{"GGTC"}="ACCG";
	$revHash{"ATTC"}="AATG";
	$revHash{"GGGT"}="ACCC";
	$revHash{"CCTA"}="AGGT";
	$revHash{"CGCG"}="GCGC";
	$revHash{"GTGT"}="ACAC";
	$revHash{"GCCC"}="GGGC";
	$revHash{"GTCG"}="ACCG";
	$revHash{"TCCC"}="AGGG";
	$revHash{"TTCA"}="AATG";
	$revHash{"AGTT"}="AACT";
	$revHash{"CCCT"}="AGGG";
	$revHash{"CCGC"}="GGGC";
	$revHash{"CTT"}="AAG";
	$revHash{"TTGG"}="AACC";
	$revHash{"ATT"}="AAT";
	$revHash{"TAGC"}="AGCT";
	$revHash{"ACTG"}="AGTC";
	$revHash{"TCAC"}="AGTG";
	$revHash{"CTGT"}="AGAC";
	$revHash{"TGTG"}="ACAC";
	$revHash{"ATCC"}="ATGG";
	$revHash{"GTGG"}="ACCC";
	$revHash{"TGGG"}="ACCC";
	$revHash{"TCGG"}="ACCG";
	$revHash{"CGGT"}="ACCG";
	$revHash{"GCTC"}="AGCG";
	$revHash{"TACG"}="ACGT";
	$revHash{"GTTT"}="AAAC";
	$revHash{"CAT"}="ATG";
	$revHash{"CATG"}="ATGC";
	$revHash{"GTTA"}="AACT";
	$revHash{"CACT"}="AGTG";
	$revHash{"TCAT"}="AATG";
	$revHash{"TTA"}="AAT";
	$revHash{"TGTA"}="ATAC";
	$revHash{"TTTC"}="AAAG";
	$revHash{"TACT"}="AAGT";
	$revHash{"TGTT"}="AAAC";
	$revHash{"CTA"}="AGT";
	$revHash{"GACT"}="AGTC";
	$revHash{"TTGC"}="AAGC";
	$revHash{"TTC"}="AAG";
	$revHash{"GCT"}="AGC";
	$revHash{"GCAT"}="ATGC";
	$revHash{"TGGT"}="AACC";
	$revHash{"CCT"}="AGG";
	$revHash{"CATC"}="ATGG";
	$revHash{"CCAT"}="ATGG";
	$revHash{"CCCG"}="GGGC";
	$revHash{"TGCC"}="AGGC";
	$revHash{"TG"}="AC";
	$revHash{"TGCT"}="AAGC";
	$revHash{"GCCG"}="GGCC";
	$revHash{"TCTG"}="AGAC";
	$revHash{"TGT"}="AAC";
	$revHash{"TTAT"}="AAAT";
	$revHash{"TAGT"}="AACT";
	$revHash{"TATG"}="ATAC";
	$revHash{"TTTA"}="AAAT";
	$revHash{"CGTA"}="ACGT";
	$revHash{"TA"}="AT";
	$revHash{"TGTC"}="AGAC";
	$revHash{"CTAT"}="ATAG";
	$revHash{"TATA"}="ATAT";
	$revHash{"TAC"}="AGT";
	$revHash{"TC"}="AG";
	$revHash{"CATT"}="AATG";
	$revHash{"TCG"}="ACG";
	$revHash{"ATTT"}="AAAT";
	$revHash{"CGTG"}="ACGC";
	$revHash{"CTG"}="AGC";
	$revHash{"TCGT"}="AACG";
	$revHash{"TCCG"}="ACGG";
	$revHash{"GTT"}="AAC";
	$revHash{"ATGT"}="ATAC";
	$revHash{"CTTG"}="AAGC";
	$revHash{"CCTT"}="AAGG";
	$revHash{"GATC"}="ATCG";
	$revHash{"CTGG"}="AGCC";
	$revHash{"TTCT"}="AAAG";
	$revHash{"CGTC"}="ACGG";
	$revHash{"CG"}="GC";
	$revHash{"TATT"}="AAAT";
	$revHash{"CTCG"}="AGCG";
	$revHash{"TCTC"}="AGAG";
	$revHash{"TCCT"}="AAGG";
	$revHash{"TGG"}="ACC";
	$revHash{"ACTC"}="AGTG";
	$revHash{"CTC"}="AGG";
	$revHash{"CGC"}="GGC";
	$revHash{"TTG"}="AAC";
	$revHash{"ACCT"}="AGGT";
	$revHash{"TCTA"}="ATAG";
	$revHash{"GTAC"}="ACGT";
	$revHash{"TTGA"}="AATC";
	$revHash{"GTCC"}="ACGG";
	$revHash{"GATT"}="AATC";
	$revHash{"T"}="A";
	$revHash{"CGTT"}="AACG";
	$revHash{"GTC"}="ACG";
	$revHash{"GCCT"}="AGGC";
	$revHash{"TGC"}="AGC";
	$revHash{"TTTG"}="AAAC";
	$revHash{"GGCT"}="AGCC";
	$revHash{"TCA"}="ATG";
	$revHash{"GTGC"}="ACGC";
	$revHash{"TGAT"}="AATC";
	$revHash{"TAT"}="AAT";
	$revHash{"CTAC"}="AGGT";
	$revHash{"TGCG"}="ACGC";
	$revHash{"CTCA"}="AGTG";
	$revHash{"CTTC"}="AAGG";
	$revHash{"GCTG"}="AGCC";
	$revHash{"TATC"}="ATAG";
	$revHash{"TAAT"}="AATT";
	$revHash{"ACT"}="AGT";
	$revHash{"TCGC"}="AGCG";
	$revHash{"GGT"}="ACC";
	$revHash{"TCC"}="AGG";
	$revHash{"TTGT"}="AAAC";
	$revHash{"TGAC"}="AGTC";
	$revHash{"TTAC"}="AAGT";
	$revHash{"CGT"}="ACG";
	$revHash{"ATTA"}="AATT";
	$revHash{"ATTG"}="AATC";
	$revHash{"CCTC"}="AGGG";
	$revHash{"CCGG"}="GGCC";
	$revHash{"CCGT"}="ACGG";
	$revHash{"TCCA"}="ATGG";
	$revHash{"CGCC"}="GGGC";
	$revHash{"GT"}="AC";
	$revHash{"TTCG"}="AACG";
	$revHash{"CCTG"}="AGGC";
	$revHash{"TCT"}="AAG";
	$revHash{"GTAT"}="ATAC";
	$revHash{"GTCT"}="AGAC";
	$revHash{"GCTA"}="AGCT";
	$revHash{"TACC"}="AGGT";
}


sub allCaps{
	my $motif = $_[0];
	$motif =~ s/a/A/g;
	$motif =~ s/c/C/g;
	$motif =~ s/t/T/g;
	$motif =~ s/g/G/g;
	return $motif;
}


sub all_caps{
	my @strand = split(/\s*/,$_[0]);
	for my $i (0 ... $#strand){
		if ($strand[$i] =~ /c/) {$strand[$i] = "C";next;}
		if ($strand[$i] =~ /a/) {$strand[$i] = "A";next;}
		if ($strand[$i] =~ /t/) { $strand[$i] = "T";next;}
		if ($strand[$i] =~ /g/) {$strand[$i] = "G";next;}
	}
	return join("",@strand);
}
sub array_mean{
	return "NA" if scalar(@_) == 0;
	my $sum = 0;
	foreach my $val (@_){
		$sum = $sum + $val;
	}
	return ($sum/scalar(@_));
}
sub array_sum{
	return "NA" if scalar(@_) == 0;
	my $sum = 0;
	foreach my $val (@_){
		$sum = $sum + $val;
	}
	return ($sum);
}

sub variance{
	return "NA" if scalar(@_) == 0;
	return 0 if scalar(@_) == 1;
	my $mean = 	array_mean(@_);
	my $num = 0;
	return 0 if scalar(@_) == 1;
#	print "mean = $mean .. array = >@_<\n";
	foreach my $ele (@_){
	#	print "$num = $num + ($ele-$mean)*($ele-$mean)\n";
		$num = $num + ($ele-$mean)*($ele-$mean);
	}
	my $var = $num / scalar(@_);
	return $var;
}

sub array_95confIntervals{
	return "NA" if scalar(@_) <= 0;
	my @sorted = sort { $a <=> $b } @_;
#	print  "@sorted=",scalar(@sorted), "\n";
	my $aDeechNo = int((scalar(@sorted) * 2.5) / 100);
	my $saaDeNo = int((scalar(@sorted) * 97.5) / 100);
	
	return ($sorted[$aDeechNo], $sorted[$saaDeNo]);
}

sub array_median{
	return "NA" if scalar(@_) == 0;
	return $_[0] if scalar(@_) == 1;
	my @sorted = sort { $a <=> $b } @_;
	my $totalno = scalar(@sorted);
	
	#print "sorted = @sorted\n";
	
	my $pick = ();
	if ($totalno % 2 == 1){
		#print "odd set .. totalno = $totalno\n";
		my $mid = $totalno / 2;
		my $onehalfno = $mid - $mid % 1;
		my $secondhalfno = $onehalfno + 1;
		my $onehalf = $sorted[$onehalfno-1];
		my $secondhalf = $sorted[$secondhalfno-1];
		#print "onehalfno = $onehalfno and secondhalfno = $secondhalfno \n onehalf = $onehalf and secondhalf = $secondhalf\n";
		
		$pick =  $secondhalf;
	}
	else{
		#print "even set .. totalno = $totalno\n";
		my $mid = $totalno / 2;
		my $onehalfno = $mid;
		my $secondhalfno = $onehalfno + 1;
		my $onehalf = $sorted[$onehalfno-1];
		my $secondhalf = $sorted[$secondhalfno-1];
		#print "onehalfno = $onehalfno and secondhalfno = $secondhalfno \n onehalf = $onehalf and secondhalf = $secondhalf\n";
		$pick = ($onehalf + $secondhalf )/2;
		
	}
	#print "pick = $pick..\n";
	return $pick;

}


sub array_numerical_sort{
		return "NA" if scalar(@_) == 0;
        my @sorted = sort { $a <=> $b } @_;
        return (@sorted);
}

sub array_smallest_number{
	return "NA" if scalar(@_) == 0;
	return $_[0] if scalar(@_) == 1;
	my @sorted = sort { $a <=> $b } @_;
	return $sorted[0];
}


sub array_largest_number{
	return "NA" if scalar(@_) == 0;
	return $_[0] if scalar(@_) == 1;
	my @sorted = sort { $a <=> $b } @_;
	return $sorted[$#sorted];
}


sub array_largest_number_arrayPosition{
	return "NA" if scalar(@_) == 0;
	return 0 if scalar(@_) == 1;
	my $maxpos = 0;
	my @maxposes = ();
	my @maxvals = ();
	my $maxval = array_smallest_number(@_);
	for my $i (0 ... $#_){
		if ($_[$i] > $maxval){
			$maxval = $_[$i];
			$maxpos = $i;
		}
		if ($_[$i] == $maxval){
			$maxval = $_[$i];
			if (scalar(@maxposes) == 0){
				push @maxposes, $i;
				push @maxvals, $_[$i];
				
			}
			elsif ($maxvals[0] == $maxval){
				push @maxposes, $i;
				push @maxvals, $_[$i];
			}
			else{
				@maxposes = (); @maxvals = ();
				push @maxposes, $i;
				push @maxvals, $_[$i];
			}
			
		}
		
	}
	return $maxpos  if scalar(@maxposes) < 2;
	return (@maxposes);
}

sub array_smallest_number_arrayPosition{
	return "NA" if scalar(@_) == 0;
	return 0 if scalar(@_) == 1;
	my $minpos = 0;
	my @minposes = ();
	my @minvals = ();
	my $minval = array_largest_number(@_);
	my $maxval = array_smallest_number(@_);
	#print "starting with $maxval, ending with $minval\n";
	for my $i (0 ... $#_){
		if ($_[$i] < $minval){
			$minval = $_[$i];
			$minpos = $i;
		}
		if ($_[$i] == $minval){
			$minval = $_[$i];
			if (scalar(@minposes) == 0){
				push @minposes, $i;
				push @minvals, $_[$i];
				
			}
			elsif ($minvals[0] == $minval){
				push @minposes, $i;
				push @minvals, $_[$i];
			}
			else{
				@minposes = (); @minvals = ();
				push @minposes, $i;
				push @minvals, $_[$i];
			}
			
		}
		
	}
	#print "minposes=@minposes\n";

	return $minpos  if scalar(@minposes) < 2;
	return (@minposes);
}

sub basic_stats{
	my @arr = @_;
#	print " array_smallest_number= ", array_smallest_number(@arr)," array_largest_number= ", array_largest_number(@arr), " array_mean= ",array_mean(@arr),"\n";
	return ":";
}
#xxxxxxx maftoAxt_multispecies xxxxxxx xxxxxxx maftoAxt_multispecies xxxxxxx xxxxxxx maftoAxt_multispecies xxxxxxx 

sub maftoAxt_multispecies {
	my $printer = 0;
	#print "in maftoAxt_multispecies : got @_\n";
	my $fname=$_[0];
	open(IN,"<$_[0]") or die "Cannot open $_[0]: $! \n";
	my $treedefinition = $_[1];
	#print "treedefinition= $treedefinition\n";
	
	my @treedefinitions = MakeTrees($treedefinition);
	
	
	open(OUT,">$_[2]") or die "Cannot open $_[2]: $! \n";
	my $counter = 0;
	my $exactspeciesset = $_[3];
	my @exactspeciesset_unarranged = split(/,/,$exactspeciesset);
	
	$treedefinition=~s/[\)\(, ]/\t/g;
	my @species=split(/\t+/,$treedefinition);
	@exactspeciesset_unarranged = @species;
#	print "species=@species\n";
	
	my @exactspeciesarr=();

	
	foreach my $def (@treedefinitions){
		$def=~s/[\)\(, ]/\t/g;
		my @specs = split(/\t+/,$def);
		my @exactspecies=();
		foreach my $spec (@specs){
			foreach my $espec (@exactspeciesset_unarranged){
			#	print "pushing >$spec< nd >$espec<\n"  if $spec eq $espec && $espec =~ /[a-zA-Z0-9]/;
				push @exactspecies, $spec if $spec eq $espec && $espec =~ /[a-zA-Z0-9]/;
			}
			
		}
			#print "exactspecies = >@exactspecies<\n";
			push @exactspeciesarr, [@exactspecies];
	}
	#<STDIN>;
	#print "exactspeciesarr=@exactspeciesarr\n";
	
	###########
	my $select = 2;  
	#select = 1 if all species need sequences to be present for each block otherwise, it is 0
	#select = 2 only the allowed set make up the alignment. use the removeset
	# information to detect alignmenets that have other important genomes aligned.
	###########
	my @allowedset = ();
	@allowedset = split(/;/,allowedSetOfSpecies(join("_",@species))) if $select == 0;
	@allowedset = join("_",0,@species) if $select == 1;
	#print "species = @species , allowedset =",join("\n", @allowedset) ," \n";
	
	
	foreach my $set (@exactspeciesarr){
		my @openset = @$set;
		push @allowedset, join("_",0,@openset) if $select == 2;
	#	print "openset = >@openset<, allowedset = @allowedset and exactspecies = @exactspecies\n";
	}
#	<STDIN>;
	my $start = 0;
	my @sequences = ();
	my @titles = ();
	my $species_counter = "0";
	my $countermatch = 0;
	my $outsideSpecies=0;
	
	while(my $line = <IN>){
		next if $line =~ /^#/;
		next if $line =~ /^i/;
	#	print "$line .. species = @species\n";
		chomp $line;
		my @fields = split(/\s+/,$line);
		chomp $line;
		if ($line =~ /^a /){
			$start = 1;
		}
		
		if ($line =~ /^s /){
		#	print "fields1 = $fields[1] , start = $start\n";
		
			foreach my $sp (@species){
				if ($fields[1] =~ /$sp/){
					$species_counter = $species_counter."_".$sp;
					push(@sequences, $fields[6]);
					my @sp_info = split(/\./,$fields[1]);
					my $title = join(" ",@sp_info, $fields[2], ($fields[2]+$fields[3]), $fields[4]);
					push(@titles, $title);				
					
				}
			}
		}
		
		if (($line !~ /^a/) && ($line !~ /^s/) && ($line !~ /^#/) && ($line !~ /^i/) && ($start = 1)){
			
			my $arranged = reorderSpecies($species_counter, @species);
#			print "species_counter=$species_counter .. arranged = $arranged\n";
			
			my $stopper = 1;
			my $arrno = 0;
			foreach my $set (@allowedset){
#					print "checking $set with $arranged\n";
				if ($arranged eq $set){
#					print "checked $set with $arranged\n";
					$stopper = 0; last;
				}
				$arrno++;
			}
	
			if ($stopper == 0) {
			#	print "    accepted\n";
				@titles = split ";", orderInfo(join(";", @titles), $species_counter, $arranged) if $species_counter ne $arranged;
				
				@sequences = split ";", orderInfo(join(";", @sequences), $species_counter, $arranged) if $species_counter ne $arranged;
				my $filteredseq = filter_gaps(@sequences);
				
				if ($filteredseq ne "SHORT"){
					$counter++;
					print OUT join (" ",$counter, @titles), "\n";
					print OUT $filteredseq, "\n";
					print OUT "\n"; 
					$countermatch++;
				}
			#	my @filtered_seq = split(/\t/,filter_gaps(@sequences) );
			}
			else{#print "\n";
			}
	
			@sequences = (); @titles = (); $start = 0;$species_counter = "0";
			next;		
			
		}
	}
#	print "countermatch = $countermatch\n";
#	<STDIN>;
}

sub reorderSpecies{
	my @inarr=@_;
	my $currSpecies = shift (@inarr);
	my $ordered_species = 0;
	my @species=@inarr;
	foreach my $order (@species){
		$ordered_species = $ordered_species."_".$order	if	$currSpecies=~ /$order/;
	}
	return $ordered_species;

}

sub filter_gaps{
	my @sequences = @_;
#	print "sequences sent are @sequences\n";
	my $seq_length = length($sequences[0]);
	my $seq_no = scalar(@sequences);
	my $allgaps = ();
	for (1 ... $seq_no){
		$allgaps = $allgaps."-";
	}
	
	my @seq_array = ();
	my $seq_counter = 0;
	foreach my $seq (@sequences){
#		my @sequence = split(/\s*/,$seq);
		$seq_array[$seq_counter] = [split(/\s*/,$seq)];
#		push @seq_array, [@sequence];
		$seq_counter++;
	}
	my $g = 0;
	while ( $g < $seq_length){
		last if (!exists $seq_array[0][$g]);
		my $bases = ();
		for my $u (0 ... $#seq_array){
			$bases = $bases.$seq_array[$u][$g];
		}	
#		print $bases, "\n";
		if ($bases eq $allgaps){
#			print "bases are $bases, position is $g \n";
			for my $seq (@seq_array){
				splice(@$seq , $g, 1);
			}
		}
		else {
			$g++;
		}
	}
	
	my @outs = ();
	
	foreach my $seq (@seq_array){
		push(@outs, join("",@$seq));
	}
	return "SHORT" if length($outs[0]) <=100;
	return (join("\n", @outs));	
}


sub allowedSetOfSpecies{
	my @allowed_species = split(/_/,$_[0]);
	unshift @allowed_species, 0;
#	print "allowed set = @allowed_species \n";
	my @output = ();
	for (0 ... scalar(@allowed_species) - 4){
		push(@output, join("_",@allowed_species));
		pop @allowed_species;
	}
	return join(";",reverse(@output));

}


sub orderInfo{
	my @info = split(/;/,$_[0]);
#	print "info = @info";
	my @old = split(/_/,$_[1]);
	my @new = split(/_/,$_[2]);
	shift @old; shift @new;
	my @outinfo = ();
	foreach my $spe (@new){
		for my $no (0 ... $#old){
			if ($spe eq $old[$no]){
				push(@outinfo, $info[$no]);
			}
		}
	}
#	print "outinfo = @outinfo \n"; 
	return join(";", @outinfo);
}

#xxxxxxx maftoAxt_multispecies xxxxxxx xxxxxxx maftoAxt_multispecies xxxxxxx xxxxxxx maftoAxt_multispecies xxxxxxx 

sub printarr {
# print ">::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::\n";
#	foreach my $line (@_) {print "$line\n";}
# print "::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::<\n";
}

sub oneOf{
	my @arr = @_;
	my $element = $arr[$#arr];
	@arr = @arr[0 ... $#arr-1];
	my $present = 0;
	
	foreach my $el (@arr){
		$present = 1 if $el eq $element;		
	}
	return $present;
}

#xxxxxxxxxxxxxx MakeTrees xxxxxxxxxxxxxxxxxxxxxxxxxxxx  MakeTrees xxxxxxxxxxxxxxxxxxxxxxxxxxxx  MakeTrees xxxxxxxxxxxxxxxxxxxxxxxxxxxx 

sub MakeTrees{
	my $tree = $_[0];
#	my @parts=($tree);
	my @parts=();
	
#	print "parts=@parts\n";
	
	while (1){
		$tree =~ s/^\(//g;
		$tree =~ s/\)$//g;
		my @arr = ();
	
		if ($tree =~ /^([a-zA-Z0-9_]+),([a-zA-Z0-9_\(\),]+)\)$/){
			@arr = $tree =~ /^([a-zA-Z0-9_]+),([a-zA-Z0-9_\(\),]+)$/;
			push @parts, "(".$tree.")";
			$tree = $2;
		}
		elsif ($tree =~ /^\(([a-zA-Z0-9_\(\),]+),([a-zA-Z0-9_]+)$/){
			@arr = $tree =~ /^([a-zA-Z0-9_\(\),]+),([a-zA-Z0-9_]+)$/;
			push @parts, "(".$tree.")";
			$tree = $1;
		}
		elsif ($tree =~ /^([a-zA-Z0-9_]+),([a-zA-Z0-9_]+)$/){
			last;
		}
	}	
	#print "parts=@parts\n";
	return @parts;
}


