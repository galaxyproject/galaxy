#!/usr/bin/perl
use strict;
use warnings;
use Term::ANSIColor;
use File::Basename;
use IO::Handle;
use Cwd;
use File::Path;
use vars qw($distance @thresholds @tags $species_set @allspecies $printer $treeSpeciesNum $focalspec $mergestarts $mergeends $mergemicros $interrtypecord $microscanned $interrcord $interr_poscord $no_of_interruptionscord $infocord $typecord $startcord $strandcord $endcord $microsatcord $motifcord $sequencepos $no_of_species $gapcord $prinkter);
use File::Path qw(make_path remove_tree);
use File::Temp qw/ tempfile tempdir /;
my $tdir = tempdir( CLEANUP => 1 );
chdir $tdir;
my $dir = getcwd;  
#print "dir = $dir\n";

#$ENV{'PATH'} .= ':' . dirname($0);
my $date = `date`;

my ($mafile, $mafile_sputt, $orthfile, $threshold_array,  $allspeciesin, $tree_definition_all, $separation) = @ARGV;
if (!$mafile or !$mafile_sputt or !$orthfile or !$threshold_array or !$separation or !$tree_definition_all or !$allspeciesin) { die "missing arguments\n"; }

$tree_definition_all =~ s/\s+//g;
$threshold_array =~ s/\s+//g;
$allspeciesin =~ s/\s+//g;
#-------------------------------------------------------------------------------
# WHICH SPUTNIK USED?
my $sputnikpath = ();
$sputnikpath = "sputnik_lowthresh_MATCH_MIN_SCORE3" ;
#$sputnikpath = "/Users/ydk/work/rhesus_microsat/codes/./sputnik_Mac-PowerPC";
#print "sputnik_Mac-PowerPC non-existant\n" if !-e $sputnikpath;
#exit if !-e $sputnikpath;
#$sputnikpath = "bx-sputnik" ;
#print "ARGV input = @ARGV\n";
#print "ARGV input :\n mafile=$mafile\n orthfile=$orthfile\n threshold_array=$threshold_array\n  species_set=$species_set\n tree_definition=$tree_definition\n separation=$separation\n";
#-------------------------------------------------------------------------------
# RUNFILE
#-------------------------------------------------------------------------------
$distance = 1; #bp
$distance++;
my @tree_definitions=MakeTrees($tree_definition_all);
my $allspeciesset = $tree_definition_all;
$allspeciesset =~ s/[\(\) ]+//g;
@allspecies = split(/,/,$allspeciesset);

my @outputfiles = ();
my $round = 0;
#my $tdir = tempdir( CLEANUP => 0 );
#chdir $tdir;

foreach my $tree_definition (@tree_definitions){
	my @commas = ($tree_definition =~ /,/g) ;
	#print "commas = @commas\n"; <STDIN>;
	next if scalar(@commas) <= 1;
	#print "species_set = $species_set\n";
	$treeSpeciesNum = scalar(@commas) + 1;
	$species_set = $tree_definition;
	$species_set =~ s/[\)\( ;]+//g;
	#print "species_set = $species_set\n"; <STDIN>;

	$round++;
	#-------------------------------------------------------------------------------
	# MICROSATELLITE THRESHOLD SETTINGS (LENGTH, BP)
	$threshold_array=~ s/,/_/g;
	my @thresharr = split("_",$threshold_array);
	@thresholds=@thresharr;
	#my $threshold_array = join("_",($mono_threshold, $di_threshold, $tri_threshold, $tetra_threshold));
	#print "current dit=$dir\n";
	#-------------------------------------------------------------------------------
	# CREATE AXT FILES IN FORWARD AND REVERSE ORDERS IF NECESSARY
	my @chrfiles=();
	
	#my $mafile =  "/Users/ydk/work/rhesus_microsat/results/galay/align.txt"; #$ARGV[0];
	my $chromt=int(rand(10000));
	my $p_chr=$chromt;
	
	
	my @exactspeciesset_unarranged = split(/,/,$species_set);
	$tree_definition=~s/[\)\(, ]/\t/g;
	my @treespecies=split(/\t+/,$tree_definition);
	my @exactspecies=();
	
	foreach my $spec (@treespecies){
		foreach my $espec (@exactspeciesset_unarranged){
			push @exactspecies, $spec if $spec eq $espec;
		}
	}
	#print "exactspecies=@exactspecies\n";
	$focalspec = $exactspecies[0];
	my $arranged_species_set=join(".",@exactspecies);
	my $chr_name = join(".",("chr".$p_chr),$arranged_species_set, "net", "axt");
	my $chr_name_sputt = join(".",("chr".$p_chr),$arranged_species_set, "net", "axt_sputt");
	#print "sending to maftoAxt_multispecies: $mafile, $tree_definition, $chr_name, $species_set .. focalspec=$focalspec \n"; 
	maftoAxt_multispecies($mafile, $tree_definition, $chr_name, $species_set);
	maftoAxt_multispecies($mafile_sputt, $tree_definition, $chr_name_sputt, $species_set);
	#print "done maf to axt conversion\n";
	my $reverse_chr_name = join(".",("chr".$p_chr."r"),$arranged_species_set, "net", "axt");
	artificial_axdata_inverter ($chr_name, $reverse_chr_name);
	#print "reverse_chr_name=$reverse_chr_name\n"; 
	#-------------------------------------------------------------------------------
	# FIND THE CORRESPONDING CHIMP CHROMOSOME FROM FILE ORTp_chrS.TXT
	foreach my $direct ("reverse_direction","forward_direction"){
		$p_chr=$chromt;
		#print "direction = $direct\n";
		$p_chr = $p_chr."r" if $direct eq "reverse_direction";
		$p_chr = $p_chr if $direct eq "forward_direction";
		my $config = $species_set;
		$config=~s/,/./g;
		my @orgs = split(/\./,$arranged_species_set);
		#print "ORGS= @orgs\n";
		my @tag=@orgs;
			
		
		my $tags = join(",", @tag);
		my @tags=@tag;
		chomp $p_chr;
		$tags = join("_", split(/,/, $tags));
		my $pchr = "chr".$p_chr;
		
		my $ptag = $orgs[0]."-".$pchr.".".join(".",@orgs[1 ... scalar(@orgs)-1])."-".$threshold_array;
		my @sp_tags = ();
		
#		print "$ptag _ orthfile\n"; <STDIN>;
		#print "orgs=@orgs, pchr=$pchr, hence, ptag = $ptag\n";
		foreach my $sp (@tag){
			push(@sp_tags, ($sp.".".$ptag));
		}
	
		my $preptag = $orgs[0]."-".$pchr.".".join(".",@orgs[1 ... scalar(@orgs)-1]);
		my @presp_tags = ();
		
		foreach my $sp (@tag){
			push(@presp_tags, ($sp.".".$preptag));
		}
	
		my $resultdir = "";
		my $orthdir = "";
		my $filtereddir = "";
		my $pipedir = "";
		
		my @title_queries = ();
		push(@title_queries, "^[0-9]+");
		my $sep="\\s";
		for my $or (0 ... $#orgs){
			my $title =  join($sep, ($orgs[$or],  "[A-Za-z_]+[0-9a-zA-Z]+", "[0-9]+", "[0-9]+", "[\\-\\+]"));
			#$title =~ s/chr\\+\\s+\+/chr/g;
			push(@title_queries, $title);
		}
		my $title_query = join($sep, @title_queries);
		#print "title_queries=@title_queries\n";
		#print "query = >$title_query<\n"; 
		#print "orgs = @orgs\n"; 
		#-------------------------------------------------------------------------------
		# GET AXTNET FILES, EDIT THEM AND SPLIT THEM INTO HUMAN AND CHIMP INPUT FILES
		my $t1input = $pchr.".".$arranged_species_set.".net.axt";
		
		my @t1outputs = ();
		
		foreach my $sp (@presp_tags){
			push(@t1outputs, $sp."_gap_op");
		}
		
		
		
		multi_species_t1($t1input,$tags,(join(",", @t1outputs)), $title_query); 
		#print "t1outputs=@t1outputs\n";
		#print "done t1\n"; <STDIN>;
		#-------------------------------------------------------------------------------
		#START T2.PL
		
		my $stag  = (); my $tag1 = (); my $tag2 = ();  my $schrs = ();
		
		for my $t (0 ... scalar(@tags)-1){
			multi_species_t2($t1outputs[$t], $tag[$t]);		
		}
		#-------------------------------------------------------------------------------
		#START T2.2.PL
		
		my @temp_tags = @tag;
		
		foreach my $sp (@presp_tags){
			my $t2input =  $sp."_nogap_op_unrand";
			multi_species_t2_2($t2input, shift(@temp_tags));
		}
		undef (@temp_tags);
		
		#-------------------------------------------------------------------------------
		#START SPUTNIK
		
		my @jobIDs = ();
		@temp_tags = @tag;
		my @sput_filelist = ();
		
		foreach my $sp (@presp_tags){
			#print "sp = $sp\n";
			my $sputnikoutput = $pipedir.$sp."_sput_op0";
			my $sputnikinput = $pipedir.$sp."_nogap_op_unrand";
			push(@sput_filelist, $sputnikinput);
			my $sputnikcommand = $sputnikpath." ".$sputnikinput." > ".$sputnikoutput;
		#	print "$sputnikcommand\n";
			my @sputnikcommand_system = $sputnikcommand;
			system(@sputnikcommand_system);
		}
	
		#-------------------------------------------------------------------------------
		#START SPUTNIK OUTPUT CORRECTOR
		
		foreach my $sp (@presp_tags){
			my $corroutput = $pipedir.$sp."_sput_op1";
			my $corrinput = $pipedir.$sp."_sput_op0";
			sputnikoutput_corrector($corrinput,$corroutput);
			
			my $t4output = $pipedir.$sp."_sput_op2";
			multi_species_t4($corroutput,$t4output);
		
			my $t5output = $pipedir.$sp."_sput_op3";
			multi_species_t5($t4output,$t5output);
			#print "done t5.pl for $sp\n";
		
			my $t6output = $pipedir.$sp."_sput_op4";
			multi_species_t6($t5output,$t6output,scalar(@orgs));
		}
		#-------------------------------------------------------------------------------
		#START T9.PL FOR T10.PL AND FOR INTERRUPTED HUNTING
		
		foreach my $sp (@presp_tags){
			my $t9output = $pipedir.$sp."_gap_op_unrand_match";
			my $t9sequence = $pipedir.$sp."_gap_op_unrand2";
			my $t9micro = $pipedir.$sp."_sput_op4";
			t9($t9micro,$t9sequence,$t9output);
			
			my $t9output2 = $pipedir.$sp."_nogap_op_unrand2_match";
			my $t9sequence2 = $pipedir.$sp."_nogap_op_unrand2";
			t9($t9micro,$t9sequence2,$t9output2);
		}
		#print "done both t9.pl for all orgs\n";
	
		#-------------------------------------------------------------------------------
		# FIND COMPOUND MICROSATELLITES
		
		@jobIDs = ();
		my $species_counter = 0;
		
		foreach my $sp (@presp_tags){
			my $simple_microsats=$pipedir.$sp."_sput_op4_simple";
			my $compound_microsats=$pipedir.$sp."_sput_op4_compound";
			my $input_micro = $pipedir.$sp."_sput_op4";
			my $input_seq = $pipedir.$sp."_nogap_op_unrand2_match";
			multiSpecies_compound_microsat_hunter3($input_micro,$input_seq,$simple_microsats,$compound_microsats,$orgs[$species_counter], scalar(@sp_tags), $threshold_array );
			$species_counter++;
		}
		
		#-------------------------------------------------------------------------------
		# READING  AND FILTERING SIMPLE MICROSATELLITES
		my $spcounter2=0;
		foreach my $sp (@sp_tags){
			my $presp = $presp_tags[$spcounter2];
			$spcounter2++;
			my $simple_microsats=$pipedir.$presp."_sput_op4_simple";
			my $simple_filterout = $pipedir.$sp."_sput_op4_simple_filtered";
			my $simple_residue = $pipedir.$sp."_sput_op4_simple_residue";
			multiSpecies_filtering_interrupted_microsats($simple_microsats, $simple_filterout, $simple_residue,$threshold_array,$threshold_array,scalar(@sp_tags));
		}
		
		#-------------------------------------------------------------------------------
		# ANALYZE  COMPOUND MICROSATELLITES FOR BEING INTERRUPTED MICROSATS
		
		$species_counter = 0;
		foreach my $sp (@sp_tags){
			my $presp = $presp_tags[$species_counter];
			my $compound_microsats = $pipedir.$presp."_sput_op4_compound";
			my $analyzed_simple_microsats=$pipedir.$presp."_sput_op4_compound_interrupted";
			my $analyzed_compound_microsats=$pipedir.$presp."_sput_op4_compound_pure";
			my $seq_file = $pipedir.$presp."_nogap_op_unrand2_match";
			multiSpecies_compound_microsat_analyzer($compound_microsats,$seq_file,$analyzed_simple_microsats,$analyzed_compound_microsats,$orgs[$species_counter], scalar(@sp_tags));
			$species_counter++;
		}
		#-------------------------------------------------------------------------------
		# REANALYZE COMPOUND MICROSATELLITES FOR PRESENCE OF SIMPLE ONES WITHIN THEM.. 
		$species_counter = 0;
		
		foreach my $sp (@sp_tags){
			my $presp = $presp_tags[$species_counter];
			my $compound_microsats = $pipedir.$presp."_sput_op4_compound_pure";
			my $compound_interrupted = $pipedir.$presp."_sput_op4_compound_clarifiedInterrupted";
			my $compound_compound = $pipedir.$presp."_sput_op4_compound_compound";
			my $seq_file = $pipedir.$presp."_nogap_op_unrand2_match";
			multiSpecies_compoundClarifyer($compound_microsats,$seq_file,$compound_interrupted,$compound_compound,$orgs[$species_counter], scalar(@sp_tags), "2_4_6_8", "3_4_6_8", "2_4_6_8");
			$species_counter++;
		}
		#-------------------------------------------------------------------------------
		# READING  AND FILTERING SIMPLE AND COMPOUND MICROSATELLITES
		$species_counter = 0;
		
		foreach my $sp (@sp_tags){
			my $presp = $presp_tags[$species_counter];
		
			my $simple_microsats=$pipedir.$presp."_sput_op4_compound_clarifiedInterrupted";
			my $simple_filterout = $pipedir.$sp."_sput_op4_compound_clarifiedInterrupted_filtered";
			my $simple_residue = $pipedir.$sp."_sput_op4_compound_clarifiedInterrupted_residue";
			multiSpecies_filtering_interrupted_microsats($simple_microsats, $simple_filterout, $simple_residue,$threshold_array,$threshold_array,scalar(@sp_tags));
		
			my $simple_microsats2 = $pipedir.$presp."_sput_op4_compound_interrupted";
			my $simple_filterout2 = $pipedir.$sp."_sput_op4_compound_interrupted_filtered";
			my $simple_residue2 = $pipedir.$sp."_sput_op4_compound_interrupted_residue";
			multiSpecies_filtering_interrupted_microsats($simple_microsats2, $simple_filterout2, $simple_residue2,$threshold_array,$threshold_array,scalar(@sp_tags));
		
			my $compound_microsats=$pipedir.$presp."_sput_op4_compound_compound";
			my $compound_filterout = $pipedir.$sp."_sput_op4_compound_compound_filtered";
			my $compound_residue = $pipedir.$sp."_sput_op4_compound_compound_residue";
			multispecies_filtering_compound_microsats($compound_microsats, $compound_filterout, $compound_residue,$threshold_array,$threshold_array,scalar(@sp_tags));
			$species_counter++;
		}
		#print "done filtering both simple and compound microsatellites \n";
		
		#-------------------------------------------------------------------------------
		
		my @combinedarray = ();
		my @combinedarray_indicators = ("mononucleotide", "dinucleotide", "trinucleotide", "tetranucleotide");
		my @combinedarray_tags = ("mono", "di", "tri", "tetra");
		$species_counter = 0;
		
		foreach my $sp (@sp_tags){
			my $simple_interrupted = $pipedir.$sp."_simple_analyzed_simple";
			push @{$combinedarray[$species_counter]}, $pipedir.$sp."_simple_analyzed_simple_mono", $pipedir.$sp."_simple_analyzed_simple_di", $pipedir.$sp."_simple_analyzed_simple_tri", $pipedir.$sp."_simple_analyzed_simple_tetra";
			$species_counter++;
		}
		
		#-------------------------------------------------------------------------------
		# PUT TOGETHER THE INTERRUPTED AND SIMPLE MICROSATELLITES BASED ON THEIR MOTIF SIZE FOR FURTHER EXTENTION	
		my $sp_counter = 0;
		foreach my $sp (@sp_tags){	
			my $analyzed_simple = $pipedir.$sp."_sput_op4_compound_interrupted_filtered";
			my $clarifyed_simple = $pipedir.$sp."_sput_op4_compound_clarifiedInterrupted_filtered";
			my $simple = $pipedir.$sp."_sput_op4_simple_filtered";
			my $simple_analyzed_simple = $pipedir.$sp."_simple_analyzed_simple";
			`cat $analyzed_simple $clarifyed_simple $simple > $simple_analyzed_simple`;
			for my $i (0 ... 3){
				`grep "$combinedarray_indicators[$i]" $simple_analyzed_simple > $combinedarray[$sp_counter][$i]`;	
			}
			$sp_counter++;		
		}
		#print "\ndone grouping interrupted & simple microsats based on their motif size for further extention\n";
		
		#-------------------------------------------------------------------------------
		# BREAK CHROMOSOME INTO PARTS OF CERTAIN NO. CONTIGS EACH, FOR FUTURE SEARCHING OF INTERRUPTED MICROSATELLITES
		# ESPECIALLY DI, TRI AND TETRANUCLEOTIDE MICROSATELLITES
		@temp_tags = @sp_tags;
		my $increment = 1000000;
		my @splist = ();
		my $targetdir = $pipedir;
		$species_counter=0;
		
		foreach my $sp (@sp_tags){
			my $presp = $presp_tags[$species_counter];
			$species_counter++;
			my $localtag = shift @temp_tags;
			my $locallist = $targetdir.$localtag."_".$p_chr."_list";
			push(@splist, $locallist);
			my $input = $pipedir.$presp."_nogap_op_unrand2_match";
			chromosome_unrand_breaker($input,$targetdir,$locallist,$increment, $localtag, $pchr);
		}
		
	
		my @unionarray = ();
		#print "splist=@splist\n";
		#-------------------------------------------------------------------------------
		# FIND INTERRUPTED MICROSATELLITES
		
		$species_counter = 0;		
		
		for my $i (0 .. $#combinedarray){
			
			@jobIDs = ();
			open (JLIST1, "$splist[$i]") or die "Cannot open file $splist[$i]: $!";
			
			while (my $sp1  = <JLIST1>){
				#print "$splist[$i]: sp1=$sp1\n";
				chomp $sp1;
				
				for my $j (0 ... $#combinedarray_tags){
					my $interr  = $sp1."_interr_".$combinedarray_tags[$j];
					my $simple  = $sp1."_simple_".$combinedarray_tags[$j];
					push @{$unionarray[$i]}, $interr, $simple;	
					multiSpecies_interruptedMicrosatHunter($combinedarray[$i][$j],$sp1,$interr ,$simple, $orgs[$species_counter], scalar(@sp_tags), "3_4_6_8"); 
				}		
			}
			$species_counter++;
		}
		close JLIST1;	
		#-------------------------------------------------------------------------------
		#	REUNION AND ZIPPING BEFORE T10.PL
		
		my @allarray = ();
		
		for my $i (0 ... $#sp_tags){	
			my $localfile = $pipedir.$sp_tags[$i]."_allmicrosats";
			unlink $localfile if -e $localfile;
			push(@allarray, $localfile);
		
			my $unfiltered_localfile= $localfile."_unfiltered";
			my $residue_localfile= $localfile."_residue";
			
			unlink $unfiltered_localfile;
			#unlink $unfiltered_localfile;
			for my $j (0 ... $#{$unionarray[$i]}){
				#print "listing files for species $i  and list number $j= \n$unionarray[$i][$j] \n";
				`cat $unionarray[$i][$j] >> $unfiltered_localfile`;
				unlink $unionarray[$i][$j];
			}
	
			multiSpecies_filtering_interrupted_microsats($unfiltered_localfile, $localfile, $residue_localfile,$threshold_array,$threshold_array,scalar(@sp_tags) );
			my $analyzed_compound = $pipedir.$sp_tags[$i]."_sput_op4_compound_compound_filtered";
			my $simple_residue = $pipedir.$sp_tags[$i]."_sput_op4_simple_residue";
			my $compound_residue = $pipedir.$sp_tags[$i]."_sput_op4_compound_residue";
			
			`cat $analyzed_compound >> $localfile`;
		}
		#-------------------------------------------------------------------------------
		# MERGING MICROSATELLITES THAT ARE VERY CLOSE TO EACH OTHER, INCLUDING THOSE FOUND BY SEARCHING IN 2 OPPOSIT DIRECTIONS
		
		my $toescape=0;
		
		
		for my $i (0 ... $#sp_tags){	
			my $localfile = $pipedir.$sp_tags[$i]."_allmicrosats";
			$localfile =~ /$focalspec\-(chr[0-9a-zA-Z]+)\./;
			my $direction = $1;
			#print "localfile = $localfile , direction = $direction\n"; 
	#		`gzip $reverse_chr_name` if $direction =~ /chr[0-9a-zA-Z]+r/ && $switchboard{"deleting_processFiles"} != 1;
			$toescape =1 if $direction =~ /chr[0-9a-zA-Z]+r/;
			last if $direction =~ /chr[0-9a-zA-Z]+r/;
			my $nogap_sequence = $pipedir.$presp_tags[$i]."_nogap_op_unrand2_match";
			my $gap_sequence = $pipedir.$presp_tags[$i]."_gap_op_unrand_match";
			my $reverselocal = $localfile;
			$reverselocal =~ s/\-chr([0-9a-zA-Z]+)\./-chr$1r./g;
			merge_interruptedMicrosats($nogap_sequence,$localfile, $reverselocal ,scalar(@sp_tags)); 
			#-------------------------------------------------------------------------------
			my $forward_separate = $localfile."_separate";
			my $reverse_separate = $reverselocal."_separate";
			my $diff = $forward_separate."_diff";
			my $miss = $forward_separate."_miss";
			my $common = $forward_separate."_common";
			forward_reverse_sputoutput_comparer($nogap_sequence,$forward_separate, $reverse_separate, $diff, $miss, $common ,scalar(@sp_tags)); 
			#-------------------------------------------------------------------------------
			my $symmetrical_file = $localfile."_symmetrical";
			my $merged_file = $localfile."_merged";
			#print "cating: $merged_file $common  into -> $symmetrical_file \n"; 
			`cat $merged_file $common > $symmetrical_file`;
			#-------------------------------------------------------------------------------
			my $t10output = $symmetrical_file."_fin_hit_all_2";
			new_multispecies_t10($gap_sequence, $symmetrical_file, $t10output, join(".", @orgs));
			#-------------------------------------------------------------------------------		
		}
		next if $toescape == 1;
		#------------------------------------------------------------------------------------------------
		# BRINGING IT ALL TOGETHER: FINDING ORTHOLOGOUS MICROSATELLITES AMONG THE SPECIES
		
		
		my @micros_array = ();
		my $sampletag = ();
		for my $i (0 ... $#sp_tags){
			my $finhitFile = $pipedir.$sp_tags[$i]."_allmicrosats_symmetrical_fin_hit_all_2";
			push(@micros_array, $finhitFile);
			$sampletag = $sp_tags[$i];
		}
		#$sampletag =~ s/^([A-Z]+\.)/ORTH_/;
		#$sampletag = $sampletag."_monoThresh-".$mono_threshold."bp";
		my $orthfiletemp = $ptag."_orthfile";
		my $orthanswer = multiSpecies_orthFinder4($t1input, join(":",@micros_array), $orthfiletemp, join(":", @orgs), $separation);

		my $maskedorthfiletemp = $ptag."_orthfile_masked";
		qualityFilter ($orthfiletemp, $chr_name_sputt, $maskedorthfiletemp);

		push @outputfiles , $maskedorthfiletemp;
	}
	$date = `date`;
}

`cat @outputfiles > $orthfile`;

my $rootdir = $dir;
$rootdir =~ s/\/[A-Za-z0-9\-_]+$//;
chdir $rootdir;
remove_tree($dir);

#print "date = $date\n";
#remove_tree($tdir);
#------------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------------------
#------------------------------------------------------------------------------------------------

#xxxxxxx maftoAxt_multispecies xxxxxxx xxxxxxx maftoAxt_multispecies xxxxxxx xxxxxxx maftoAxt_multispecies xxxxxxx 

sub maftoAxt_multispecies {
	#print "in maftoAxt_multispecies : got @_\n";
	my $fname=$_[0];
	open(IN,"<$_[0]") or die "Cannot open $_[0]: $! \n";
	my $treedefinition = $_[1];
	open(OUT,">$_[2]") or die "Cannot open $_[2]: $! \n";
	my $counter = 0;
	my $exactspeciesset = $_[3];
	my @exactspeciesset_unarranged = split(/,/,$exactspeciesset);
	
	$treedefinition=~s/[\)\(, ]/\t/g;
	my @species=split(/\t+/,$treedefinition);
	my @exactspecies=();
	
	foreach my $spec (@species){
		foreach my $espec (@exactspeciesset_unarranged){
			push @exactspecies, $spec if $spec eq $espec;
		}
	}
	#print "exactspecies=@exactspecies\n";
	
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
	@allowedset = join("_",0,@exactspecies) if $select == 2;
	#print "allowedset = @allowedset and exactspecies = @exactspecies\n";
	
	my $start = 0;
	my @sequences = ();
	my @titles = ();
	my $species_counter = "0";
	my $countermatch = 0;
	my $outsideSpecies=0;
	
	while(my $line = <IN>){
#		print $line;
		next if $line =~ /^#/;
		next if $line =~ /^i/;
		chomp $line;
		my @fields = split(/\s+/,$line);
		chomp $line;
		if ($line =~ /^a /){
			$start = 1;
		}
		
		if ($line =~ /^s /){
		
			foreach my $sp (@allspecies){
#				print "checking species $sp\n";
				if ($fields[1] =~ /$sp/){
					$species_counter = $species_counter."_".$sp;
					push(@sequences, $fields[6]);
					my @sp_info = split(/\./,$fields[1]);
					my $title = join(" ",@sp_info, $fields[2], ($fields[2]+$fields[3]), $fields[4]);
					push(@titles, $title);				
#					print "species_counter = $species_counter\n";
				}
			}
		}
		
		if (($line !~ /^a/) && ($line !~ /^s/) && ($line !~ /^#/) && ($line !~ /^i/) && ($start = 1)){
#			print "species_counter = $species_counter\n"; 
			my $arranged = reorderSpecies($species_counter, @allspecies);
			my $stopper = 1;
			my $arrno = 0;
			
#			print "checking if ", scalar(@sequences), " match @exactspecies allowedset=@allowedset\n";
			if (scalar(@sequences) == scalar(@exactspecies)){
				foreach my $set (@allowedset){
#					print "testing $arranged against $set\n";
					if ($arranged eq $set){
						$stopper = 0; last;
					}
					$arrno++;
				}
			}
			else{
				$stopper = 1;
			}
			
			
			if ($stopper == 0) {
				@titles = split ";", orderInfo(join(";", @titles), $species_counter, $arranged) if $species_counter ne $arranged;				
				@sequences = split ";", orderInfo(join(";", @sequences), $species_counter, $arranged) if $species_counter ne $arranged;				
				my $filteredseq = filter_gaps(@sequences);
				
				if ($filteredseq ne "SHORT"){
					#print "printing"; <STDIN>;
					$counter++;
					print OUT join (" ",$counter, @titles), "\n";
					print OUT $filteredseq, "\n";
					print OUT "\n"; 
					$countermatch++;
				}
			}
			else{ #print "nexting\n";<STDIN>;
			}
	
			@sequences = (); @titles = (); $start = 0;$species_counter = "0";
			next;		
			
		}
	}
#	print "countermatch = $countermatch\n";
}

sub reorderSpecies{
	my @inarr=@_;
	my $currSpecies = shift (@inarr);
	my $ordered_species = 0;
	my @species=@inarr;
	#print "species = @species\n";
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

#xxxxxxx artificial_axdata_inverter xxxxxxx xxxxxxx artificial_axdata_inverter xxxxxxx xxxxxxx artificial_axdata_inverter xxxxxxx 
sub artificial_axdata_inverter{
	open(IN,"<$_[0]") or die "Cannot open file $_[0]: $!";
	open(OUT,">$_[1]") or die "Cannot open file $_[1]: $!";
	my $linecounter=0;
	while (my $line = <IN>){
		$linecounter++;
		#print "$linecounter\n";
		chomp $line;	
		my $final_line = $line;	
		my $trycounter = 0;
		if ($line =~ /^[a-zA-Z\-]/){
		#	while ($final_line eq $line){
				my @fields = split(/\s*/,$line);
				
				$final_line = join("",reverse(@fields));
		#		print colored ['red'], "$line\n$final_line\n" if $final_line eq $line && $line !~ /chr/ && $line =~ /[a-zA-Z]/;
		#		$trycounter++;
		#		print "trying again....$trycounter : $final_line\n" if $final_line eq $line;
		#	}
		}
		
	#	print colored ['yellow'], "$line\n$final_line\n" if $final_line eq $line && $line !~ /chr/ && $line =~ /[a-zA-Z]/;
		if ($line =~ /^[0-9]/){
			$line =~ s/chr([A-Z0-9a-b]+)/chr$1r/g;
			$final_line = $line;
		}
		print OUT $final_line,"\n";
		#print "$line\n$final_line\n" if $final_line eq $line && $line !~ /chr/ && $line =~ /[a-zA-Z]/;
	}
	close OUT;
}
#xxxxxxx artificial_axdata_inverter xxxxxxx xxxxxxx artificial_axdata_inverter xxxxxxx xxxxxxx artificial_axdata_inverter xxxxxxx 


#xxxxxxx multi_species_t1 xxxxxxx xxxxxxx multi_species_t1 xxxxxxx xxxxxxx multi_species_t1 xxxxxxx 

sub multi_species_t1 {

	my $input1 = $_[0];
	#print "@_\n"; <STDIN>;
	my @tags = split(/_/, $_[1]);
	my @outputs = split(/,/, $_[2]);
	my $title_query = $_[3];
	my @handles = ();
	
	open(FILEB,"<$input1")or die "Cannot open file: $input1 $!";
	my $i = 0;
	foreach my $path (@outputs){
		$handles[$i] = IO::Handle->new();
		open ($handles[$i], ">$path") or die "Can't open $path : $!";
		$i++;
	}
	
	my $curdef;
	my $start = 0;
	
	while (my $line = <FILEB> ) {
		if ($line =~ /^\d/){
			$line =~ s/ +/\t/g;
			my @fields = split(/\s+/, $line);
			if (($line =~ /$title_query/)){
				my $title = $line;
				my $counter = 0;
				foreach my $tag (@tags){
					$line = <FILEB>;
					print {$handles[$counter]} ">",$tag,"\t",$title, " ",$line;  	
					$counter++;
				}
			}
			else{
					foreach my $tag (@tags){
					my $tine = <FILEB>;
				}		
			}
		
		}
	}
	
	foreach my $hand (@handles){
		$hand->close(); 
	}
	
	close FILEB;
}

#xxxxxxx multi_species_t1 xxxxxxx xxxxxxx multi_species_t1 xxxxxxx xxxxxxx multi_species_t1 xxxxxxx 

#xxxxxxx multi_species_t2 xxxxxxx xxxxxxx multi_species_t2 xxxxxxx xxxxxxx multi_species_t2 xxxxxxx 

sub multi_species_t2{
	
	my $input = $_[0];
	my $species = $_[1];
	my $output1 = $input."_unr";
	
	#------------------------------------------------------------------------------------------
	open (FILEF1, "<$input") or die "Cannot open file $input :$!";
	open (FILEF2, ">$output1") or die "Cannot open file $output1 :$!";
	
	my $line1 = <FILEF1>;
	
	while($line1){
	{
	#    chomp($line);
		if ($line1 =~ (m/^\>$species/)){
		chomp($line1);
		print FILEF2 $line1;
		$line1 = <FILEF1>;
		chomp($line1);
		print FILEF2 "\t", $line1,"\n";
	   }   
	}
	$line1 = <FILEF1>;
	}
	
	close FILEF1;
	close FILEF2;
	#------------------------------------------------------------------------------------------
	
	my $output2 = $output1."and";
	my $output3 = $output1."and2";
	open(IN,"<$output1");
	open (FILEF3, ">$output2");
	open (FILEF4, ">$output3");
	
	
	while (<IN>){
		my $line = $_;
		chomp($line);
		my @fields=split (/\t/, $line);
	  #  print $line,"\n"; <STDIN>;
		if($line !~ /random/){
			print FILEF3 join ("\t",@fields[0 ... scalar(@fields)-2]), "\n", $fields[scalar(@fields)-1], "\n";
			print FILEF4 join ("\t",@fields[0 ... scalar(@fields)-2]), "\t", $fields[scalar(@fields)-1], "\n";	
		}
	}
	
	
	close IN;
	close FILEF3;
	close FILEF4;
	unlink $output1;
	
	#------------------------------------------------------------------------------------------
	# OLD T3.PL RUDIMENT
	
	my $t3output = $output2;
	$t3output =~ s/gap_op_unrand/nogap_op_unrand/g;
	
	open(IN,"<$output2");
	open(OUTA,">$t3output");
	
	
	while (<IN>){
		s/-//g unless /^>/;
		print OUTA;
	}
	
	close IN;
	close OUTA;
	#------------------------------------------------------------------------------------------
}
#xxxxxxx multi_species_t2 xxxxxxx xxxxxxx multi_species_t2 xxxxxxx xxxxxxx multi_species_t2 xxxxxxx 


#xxxxxxx multi_species_t2_2 xxxxxxx xxxxxxx multi_species_t2_2 xxxxxxx xxxxxxxmulti_species_t2_2 xxxxxxx 
sub multi_species_t2_2{
	#print "IN multi_species_t2_2 : @_\n";
	my $input = $_[0];
	my $species = $_[1];
	my $output1 = $input."2";
	
	
	open (FILEF1, "<$input");
	open (FILEF2, ">$output1");
	
	my $line1 = <FILEF1>;
	
	while($line1){
	{
	#    chomp($line);
		if ($line1 =~ (m/^\>$species/)){
		chomp($line1);
		print FILEF2 $line1;
		$line1 = <FILEF1>;
		chomp($line1);
		print FILEF2 "\t", $line1,"\n";
	   }   
	}
	$line1 = <FILEF1>;
	}
	
	close FILEF1;
	close FILEF2;
}

#xxxxxxx multi_species_t2_2 xxxxxxx xxxxxxx multi_species_t2_2 xxxxxxx xxxxxxx multi_species_t2_2 xxxxxxx 


#xxxxxxx sputnikoutput_corrector xxxxxxx xxxxxxx sputnikoutput_corrector xxxxxxx xxxxxxx sputnikoutput_corrector xxxxxxx 
sub sputnikoutput_corrector{
	my $input = $_[0];
	my $output = $_[1];
	open(IN,"<$input") or die "Cannot open file $input :$!";
	open(OUT,">$output") or die "Cannot open file $output :$!";
	my $tine;
	while (my $line=<IN>){
		if($line =~/length /){
			$tine = $line;
			$tine =~ s/\s+/\t/g;
			my @fields = split(/\t/,$tine);	
			if ($fields[6] > 60){
				print OUT $line;
				$line = <IN>;
			
				while (($line !~ /nucleotide/) && ($line !~ /^>/)){
					chomp $line;
					print OUT $line;
					$line = <IN>;
				}
				print OUT "\n";
				print OUT $line;
			}
			else{
				print OUT $line;
			}
		}
		else{
			print OUT $line;
		}
	}
	close IN;
	close OUT;
}
#xxxxxxx sputnikoutput_corrector xxxxxxx xxxxxxx sputnikoutput_corrector xxxxxxx xxxxxxx sputnikoutput_corrector xxxxxxx 


#xxxxxxx multi_species_t4 xxxxxxx xxxxxxx multi_species_t4 xxxxxxx xxxxxxx multi_species_t4 xxxxxxx 
sub multi_species_t4{
#	print "multi_species_t4 : @_\n";
	my $input = $_[0];
	my $output = $_[1];
	open (FILEA, "<$input");
	open (FILEB, ">$output");
	
	my $line = <FILEA>;
	
	while ($line) {
	   # chomp $line;
		if ($line =~ />/) {
			chomp $line;
			print FILEB $line, "\n"; 
		}
	
		
		if ($line =~ /^m/ | $line =~ /^d/ | $line =~ /^t/ | $line =~ /^p/){
		chomp $line;
		print FILEB $line, " " ;
		$line = <FILEA>;
		chomp $line;
		print FILEB $line,"\n";
		}
	
		$line = <FILEA>;
	}
	
	
	close FILEA;
	close FILEB;

}

#xxxxxxx multi_species_t4 xxxxxxx xxxxxxx multi_species_t4 xxxxxxx xxxxxxx multi_species_t4 xxxxxxx 


#xxxxxxx multi_species_t5 xxxxxxx xxxxxxx multi_species_t5 xxxxxxx xxxxxxx multi_species_t5 xxxxxxx 
sub multi_species_t5{
	
	my $input = $_[0];
	my $output = $_[1];
	
	open(FILEB,"<$input");
	open(FILEC,">$output");
	
	my $curdef;
	
	while (my $line = <FILEB> ) {
	
		if ($line =~ /^>/){
		chomp $line;
		$curdef = $line;
		next;
	}
	
	if ($line =~ /^m/ | $line =~ /^d/ | $line =~ /^t/ | $line =~ /^p/){
		print  FILEC $curdef," ",$line;
	}
	
	}
	
	
	close FILEB;
	close FILEC;

}
#xxxxxxx multi_species_t5 xxxxxxx xxxxxxx multi_species_t5 xxxxxxx xxxxxxx multi_species_t5 xxxxxxx 


#xxxxxxx multi_species_t6 xxxxxxx xxxxxxx multi_species_t6 xxxxxxx xxxxxxx multi_species_t6 xxxxxxx 
sub multi_species_t6{
	my $input = $_[0];
	my $output = $_[1];	
	my $focalstrand=$_[3];
#	print "inpput = @_\n"; 
	open (FILE, "<$input");
	open (FILE_MICRO, ">$output");
	my $linecounter=0;	
	while (my $line = <FILE>){
		$linecounter++;
		chomp $line;
		#print "line = $line\n";
		#MONO#
		$line =~ /$focalspec\s[a-zA-Z]+[0-9a-zA-Z]+\s[0-9]+\s[0-9]+\s([+\-])/;
		my $strand=$1;
		my $no_of_species = ($line =~ s/\s+[+\-]\s+/ /g);
		#print "line = $line\n";
		my $specfieldsend = 2 + ($no_of_species*4) - 1;
		my @fields = split(/\s+/, $line);
		my @speciesdata = @fields[0 ... $specfieldsend];
		$line =~ /([a-z]+nucleotide)\s([0-9]+)\s:\s([0-9]+)/;
		my ($tide, $start, $end) = ($1, $2, $3);
		#print "no_of_species=$no_of_species.. speciesdata = @speciesdata and ($tide, $start, $end)\n";
		if($line  =~ /mononucleotide/){
			print FILE_MICRO join("\t",@speciesdata, $tide, $start, $strand,$end, $fields[$#fields],  mono($fields[$#fields]),),"\n";
		}
		#DI#	
		elsif($line =~ /dinucleotide/){
			print FILE_MICRO join("\t",@speciesdata, $tide, $start, $strand,$end, $fields[$#fields],  di($fields[$#fields]),),"\n";
		}
		#TRI#	
		elsif($line =~ /trinucleotide/ ){
			print FILE_MICRO join("\t",@speciesdata, $tide, $start, $strand,$end, $fields[$#fields],  tri($fields[$#fields]),),"\n";
		}
		#TETRA#
		elsif($line =~ /tetranucleotide/){
			print FILE_MICRO join("\t",@speciesdata, $tide, $start, $strand,$end, $fields[$#fields],  tetra($fields[$#fields]),),"\n";
		}
		#PENTA#
		elsif($line =~ /pentanucleotide/){
			#print FILE_MICRO join("\t",@speciesdata, $tide, $start, $strand,$end, $fields[$#fields],  penta($fields[$#fields]),),"\n";
		}
		else{
		#	print "not: @fields\n";
		}
	}
#	print "linecounter=$linecounter\n"; 
	close FILE;
	close FILE_MICRO;
}

sub mono {
	my $st = $_[0];
	my $tp = unpack "A1"x(length($st)/1),$st;
	my $var1 = substr($tp, 0, 1);
	return join ("\t", $var1);
}
sub di {
	my $st = $_[0];
	my $tp = unpack "A2"x(length($st)/2),$st;
	my $var1 = substr($tp, 0, 2);
	return join ("\t", $var1);
}
sub tri {
	my $st = $_[0];
	my $tp = unpack "A3"x(length($st)/3),$st;
	my $var1 = substr($tp, 0, 3);
	return join ("\t", $var1);
}
sub tetra {
	my $st = $_[0];
	my $tp = unpack "A4"x(length($st)/4),$st;
	my $var1 = substr($tp, 0, 4);
	return join ("\t", $var1);
}
sub penta {
	my $st = $_[0];
	my $tp = unpack "A5"x(length($st)/5),$st;
	my $var1 = substr($tp, 0, 5);
	return join ("\t", $var1);
}

#xxxxxxx multi_species_t6 xxxxxxx xxxxxxx multi_species_t6 xxxxxxx xxxxxxx multi_species_t6 xxxxxxx 


#xxxxxxxxxxxxxx t9 xxxxxxxxxxxxxx xxxxxxxxxxxxxx t9 xxxxxxxxxxxxxx xxxxxxxxxxxxxx t9 xxxxxxxxxxxxxx 
sub t9{
	my $input1 = $_[0];
	my $input2 = $_[1];
	my $output = $_[2];
	
	
	open(IN1,"<$input1") if -e $input1; 
	open(IN2,"<$input2") or die "cannot open file $_[1] : $!";
	open(OUT,">$output") or die "cannot open file $_[2] : $!"; 
	
	
	my %seen = ();
	my $prevkey = 0;
	
	if (-e $input1){
		while (my $line = <IN1>){
			chomp($line);
			my @fields = split(/\t/,$line);
			my $key1 = join ("_K10K1_",@fields[0,1,3,4,5]);
		#	print "key in t9 = $key1\n";
			$seen{$key1}++	if ($prevkey ne $key1) ;
			$prevkey = $key1;
		}
#		print "done first hash\n";
		close IN1;
	}
	
	while (my $line = <IN2>){
	#	print $line, "**\n";
		if (-e $input1){
			chomp($line);
			my @fields = split(/\t/,$line);
			my $key2 = join ("_K10K1_",@fields[0,1,3,4,5]);
			if (exists $seen{$key2}){
				print OUT "$line\n"	;
				delete $seen{$key2};
			}
		}
		else {
			print OUT "$line\n"	;		
#			print  "$line\n"	;		
		}
	}
	
	close IN2;
	close OUT;
}
#xxxxxxxxxxxxxx t9 xxxxxxxxxxxxxx xxxxxxxxxxxxxx t9 xxxxxxxxxxxxxx xxxxxxxxxxxxxx t9 xxxxxxxxxxxxxx 


#xxxxxxxxxxxxxx multiSpecies_compound_microsat_hunter3 xxxxxxxxxxxxxx  multiSpecies_compound_microsat_hunter3 xxxxxxxxxxxxxx  multiSpecies_compound_microsat_hunter3 xxxxxxxxxxxxxx 


sub multiSpecies_compound_microsat_hunter3{	
	
	my $input1 = $_[0];  ###### the *_sput_op4_ii file
	my $input2 = $_[1];  ###### looks like this: my $t8humanoutput = $pipedir.$ptag."_nogap_op_unrand2"
	my $output1 = $_[2]; ###### plain microsatellite file
	my $output2 = $_[3]; ###### compound microsatellite file
	my $org = $_[4]; ###### 1 or 2
	$no_of_species = $_[5];
	#print "IN multiSpecies_compound_microsat_hunter3: @_\n"; 
	#my @tags = split(/\t/,$info);
	sub compoundify;
	open(IN,"<$input1") or die "Cannot open file $input1 $!";
	open(SEQ,"<$input2") or die "Cannot open file $input2 $!";
	open(OUT,">$output1") or die "Cannot open file $output1 $!";
	open(OUT2,">$output2") or die "Cannot open file $output2 $!";
	$infocord = 2 + (4*$no_of_species) - 1;
	$startcord = 2 + (4*$no_of_species) + 2 - 1;
	$strandcord = 2 + (4*$no_of_species) + 3 - 1;
	$endcord = 2 + (4*$no_of_species) + 4 - 1;
	$microsatcord = 2 + (4*$no_of_species) + 5 - 1;
	$motifcord = 2 + (4*$no_of_species) + 6 - 1;
	my $sequencepos = 2 + (5*$no_of_species) + 1 -1 ; 
	
	my @thresholds = ("0");
	push(@thresholds, split(/_/,$_[6]));
	sub thresholdCheck;
	my %micros = ();
	while (my $line = <IN>){
	#	print "$org\t(chr[0-9]+)\t([0-9]+)\t([0-9])+\t \n";
		next if $line =~ /\t\t/;
		if ($line =~ /^>[A-Za-z0-9_]+\s+([0-9]+)\s+([a-zA-Z0-9]+)\s([a-zA-Z]+[0-9a-zA-Z]+)\s([0-9]+)\s([0-9]+)\s/ ) {
			my $key = join("\t",$1, $2, $3, $4, $5);
		#	print $key, "#-#-#-#-#-#-#-#\n";
			push (@{$micros{$key}},$line);		
		}
		else{
		}
	}
	close IN;
	my @deletedlines = ();
	
	my $linecount = 0;
	
	while(my $sine = <SEQ>){
		my %microstart=();
		my %microend=();
	
		my @sields = split(/\t/,$sine);
	
		my $key = ();
	
		if ($sine =~ /^>[A-Za-z0-9]+\s+([0-9]+)\s+([a-zA-Z0-9]+)\s([a-zA-Z]+[0-9a-zA-Z]+)\s([0-9]+)\s([0-9]+)\s/ ) {
			$key = join("\t",$1, $2, $3, $4, $5);
		#	print $key, "<-<-<-<-<-<-<-<\n";		
		}
		else{
		}
	
		if (exists $micros{$key}){
			$linecount++;	
			my @microstring = @{$micros{$key}};
			my @tempmicrostring = @{$micros{$key}};
			
			foreach my $line (@tempmicrostring){
				my @fields = split(/\t/,$line);
				my $start = $fields[$startcord];
				my $end = $fields[$endcord];
				push (@{$microstart{$start}},$line);
				push (@{$microend{$end}},$line);	
			}
			my $firstflag = 'down';
			while( my $line =shift(@microstring)){
	#			print "-----------\nline = $line ";
				chomp $line;
				my @fields = split(/\t/,$line);
				my $start = $fields[$startcord];
				my $end = $fields[$endcord];
				my $startmicro = $line;
				my $endmicro = $line;
	
			#	print "fields=@fields, start = $start end=$end, startcord=$startcord, endcord=$endcord\n";
	
				delete ($microstart{$start});
				delete ($microend{$end});
				my $flag = 'down';	
				my $startflag = 'down';
				my $endflag = 'down';
				my $prestart = $start - $distance;
				my $postend = $end + $distance;
				my @compoundlines = ();
				my %compoundhash = ();
				push (@compoundlines, $line);
				push (@{$compoundhash{$line}},$line);
				my $startrank = 1;
				my $endrank = 1;
				
				while( ($startflag eq "down") || ($endflag eq "down") ){
				if ((($prestart < 0) && $firstflag eq "up") || (($postend > length($sields[$sequencepos])) && $firstflag eq "up") ) {
#					print "coming to the end of sequence,prestart = $prestart &  post end = $postend and sequence length =", length($sields[$sequencepos])," so exiting\n";
					last;
				}
					
				$firstflag = "up";
				if ($startflag eq "down"){		
					for my $i ($prestart ... $start){
					
						if(exists $microend{$i}){	
							chomp $microend{$i}[0];
							if(exists $compoundhash{$microend{$i}[0]}) {next;}
	#						print "sending from microend $startmicro, $microend{$i}[0] |||\n";
							if (identityMatch_thresholdCheck($startmicro, $microend{$i}[0], $startrank) eq "proceed"){
								push(@compoundlines, $microend{$i}[0]);
	#							print "accepted\n";
								my @tields = split(/\t/,$microend{$i}[0]);
								$startmicro = $microend{$i}[0];
								chomp $startmicro;
								$start = $tields[$startcord];
								$flag = 'down';
								$startrank++;
	#							print "startcompund = $microend{$i}[0]\n";
								delete $microend{$i};
								delete $microstart{$start};
								$startflag = 'down';
								$prestart = $start - $distance;
								last;
							}	
							else{
								$flag = 'up';
								$startflag = 'up';							
							}
						}
						else{
							$flag = 'up';
							$startflag = 'up';
						}
					}
				}
					
				$endrank = $startrank;
				
				if ($endflag eq "down"){				
					for my $i ($end ... $postend){
					
						if(exists $microstart{$i} ){
							chomp $microstart{$i}[0];
							if(exists $compoundhash{$microstart{$i}[0]}) {next;}	
	#						print "sending from microstart $endmicro, $microstart{$i}[0] |||\n";
	
							if(identityMatch_thresholdCheck($endmicro,$microstart{$i}[0], $endrank) eq "proceed"){
								push(@compoundlines, $microstart{$i}[0]);
	#								print "accepted\n";
								my @tields = split(/\t/,$microstart{$i}[0]);
								$end = $tields[$endcord]-0;
								$endmicro = $microstart{$i}[0];
								$endrank++;
								chomp $endmicro;
								$flag = 'down';
	#							print "endcompund = $microstart{$i}[0]\n";
								delete $microstart{$i};
								delete $microend{$end};
								shift @microstring;
								$postend = $end + $distance;
								$endflag = 'down';
								last;								
							}
							else{
								$flag = 'up';
								$endflag = 'up';							
							}
						}
						else{
							$flag = 'up';
							$endflag = 'up';
						}
					}
				}
	#			print "for next turn, flag status: startflag = $startflag and endflag = $endflag \n";
			} 														#end while( $flag eq "down")
	#			print "compoundlines = @compoundlines \n";
			if (scalar (@compoundlines) == 1){
				print OUT $line,"\n";			
			}
			if (scalar (@compoundlines) > 1){
				my $compoundline = compoundify(\@compoundlines, $sields[$sequencepos]);
	#				print $compoundline,"\n";
				print OUT2 $compoundline,"\n";
			}
			} #end foreach my $line (@microstring){
		}	#if (exists $micros{$key}){
	
	
	}
	
	close OUT;
	close OUT2;
}


#------------------------------------------------------------------------------------------------
sub compoundify{
	my ($compoundlines, $sequence)  = @_;
#	print "\nfound to compound : @$compoundlines and$sequence \n";
	my $noOfComps = @$compoundlines;
#	print "Number of elements in hash is $noOfComps\n";
	my @starts;
	my @ends;
	foreach my $line (@$compoundlines){
#		print "compoundify.. line = $line \n";
		chomp $line;
		my @fields = split(/\t/,$line);
		my $start = $fields[$startcord];
		my $end = $fields[$endcord];
	#	print "start = $start, end = $end \n";
		push(@starts, $start);
		push(@ends,$end);		
	}
	my @temp = @$compoundlines;
	my $startline=$temp[0];
	my @mields  = split(/\t/,$startline);
	my $startcoord = $mields[$startcord];
	my $startgapsign=$mields[$endcord];
	my @startsorted = sort { $a <=> $b } @starts;
	my @endsorted = sort { $a <=> $b } @ends;
	my @intervals;
	for my $end (0 ... (scalar(@endsorted)-2)){
		my $interval = substr($sequence,($endsorted[$end]+1),(($startsorted[$end+1])-($endsorted[$end])-1));
		push(@intervals,$interval);
	#	print "interval = $interval =\n";
	#	print "substr(sequence,($endsorted[$end]+1),(($startsorted[$end+1])-($endsorted[$end])-1))\n";
	}
	push(@intervals,"");
	my $compoundmicrosat=();
	my $multiunit="";
	foreach my $line (@$compoundlines){
		my @fields = split(/\t/,$line);
		my $component="[".$fields[$microsatcord]."]".shift(@intervals);
		$compoundmicrosat=$compoundmicrosat.$component;
		$multiunit=$multiunit."[".$fields[$motifcord]."]";
#		print "multiunit = $multiunit\n";
	}
	my $compoundcopy = $compoundmicrosat;
	$compoundcopy =~ s/\[|\]//g;
	my $compoundlength = $mields[$startcord] + length($compoundcopy) - 1;
	
	
	my $compoundline = join("\t",(@mields[0 ... $infocord], "compound",@mields[$startcord ... $startcord+1],$compoundlength,$compoundmicrosat, $multiunit));
	return $compoundline;
}	

#------------------------------------------------------------------------------------------------

sub identityMatch_thresholdCheck{
	my $line1 = $_[0];
	my $line2 = $_[1];
	my $rank = $_[2];
	my @lields1 = split(/\t/,$line1);
	my @lields2 = split(/\t/,$line2);
#	print "recieved $line1 && $line2\n motif comparison: ", length($lields1[$motifcord])," : ",length($lields2[$motifcord]),"\n";
	
	if (length($lields1[$motifcord]) == length($lields2[$motifcord])){
		my $probe = $lields1[$motifcord].$lields1[$motifcord];
			#print "$probe :: $lields2[$motifcord]\n";
		return "proceed" if $probe =~ /$lields2[$motifcord]/;
			#print "line recieved\n";
		if ($rank ==1){
			return "proceed" if thresholdCheck($line1) eq "proceed" && thresholdCheck($line2) eq "proceed";
		}
		else {
			return "proceed" if thresholdCheck($line2) eq "proceed";
			return "stop";
		}
	}
	else{
		if ($rank ==1){
			return "proceed" if thresholdCheck($line1) eq "proceed" && thresholdCheck($line2) eq "proceed";
		}
		else {
			return "proceed" if thresholdCheck($line2) eq "proceed";
			return "stop";
		}
	}
	return "stop";
}
#------------------------------------------------------------------------------------------------

sub thresholdCheck{
	my @checkthresholds=(0,@thresholds);
	#print "IN thresholdCheck: @_\n";
	my $line = $_[0];
	my @lields = split(/\t/,$line);
	return "proceed" if length($lields[$microsatcord]) >= $checkthresholds[length($lields[$motifcord])];
	return "stop";
}
#xxxxxxxxxxxxxx multiSpecies_compound_microsat_hunter3 xxxxxxxxxxxxxx  multiSpecies_compound_microsat_hunter3 xxxxxxxxxxxxxx  multiSpecies_compound_microsat_hunter3 xxxxxxxxxxxxxx 


#xxxxxxxxxxxxxx multiSpecies_filtering_interrupted_microsats xxxxxxxxxxxxxx  multiSpecies_filtering_interrupted_microsats xxxxxxxxxxxxxx  multiSpecies_filtering_interrupted_microsats xxxxxxxxxxxxxx 

sub multiSpecies_filtering_interrupted_microsats{
#	print "IN multiSpecies_filtering_interrupted_microsats: @_\n";
	my $unfiltered = $_[0];
	my $filtered = $_[1];
	my $residue = $_[2];
	my $no_of_species = $_[5];
	open(UNF,"<$unfiltered") or die "Cannot open file $unfiltered: $!";
	open(FIL,">$filtered") or die "Cannot open file $filtered: $!";
	open(RES,">$residue") or die "Cannot open file $residue: $!";
		
	$infocord = 2 + (4*$no_of_species) - 1;
	$startcord = 2 + (4*$no_of_species) + 2 - 1;
	$strandcord = 2 + (4*$no_of_species) + 3 - 1;
	$endcord = 2 + (4*$no_of_species) + 4 - 1;
	$microsatcord = 2 + (4*$no_of_species) + 5 - 1;
	$motifcord = 2 + (4*$no_of_species) + 6 - 1;
	
	
	my @sub_thresholds = (0);
	
	push(@sub_thresholds, split(/_/,$_[3]));
	my @thresholds = (0);
	
	push(@thresholds, split(/_/,$_[4]));
	
	while (my $line = <UNF>) {
		next if $line !~ /[a-z]/;
		#print $line;
		chomp $line;
		my @fields = split(/\t/,$line);
		my $motif = $fields[$motifcord];
		my $realmotif = $motif;
		#print "motif = $motif\n";
		if ($motif =~ /^\[/){
			$motif =~ s/^\[//g;
			my @motifs = split(/\]/,$motif);
			$realmotif = $motifs[0];
		}
#		print "realmotif = $realmotif";
		my $motif_size = length($realmotif);
		
		my $microsat = $fields[$microsatcord];
#		print "microsat = $microsat\n";
		$microsat =~ s/^\[|\]$//sg;
		my @microsats = split(/\][a-zA-Z|-]*\[/,$microsat);
		
		$microsat = join("",@microsats);
		if (length($microsat) < $thresholds[$motif_size]) {
		#	print length($microsat)," < ",$thresholds[$motif_size],"\n"; 
			print RES $line,"\n"; next;
		}
		my @lengths = ();
		foreach my $mic (@microsats){
			push(@lengths, length($mic));
		}
		if (largest_microsat(@lengths) < $sub_thresholds[$motif_size]) {
	#		print largest_microsat(@lengths)," < ",$sub_thresholds[$motif_size],"\n"; 
			print RES $line,"\n"; next;}
			else {print FIL $line,"\n"; next;
		}
	}
	close FIL;
	close RES;

}

sub largest_microsat{
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

#xxxxxxxxxxxxxx multiSpecies_filtering_interrupted_microsats xxxxxxxxxxxxxx  multiSpecies_filtering_interrupted_microsats xxxxxxxxxxxxxx  multiSpecies_filtering_interrupted_microsats xxxxxxxxxxxxxx 


#xxxxxxxxxxxxxx multiSpecies_compound_microsat_analyzer xxxxxxxxxxxxxx  multiSpecies_compound_microsat_analyzer xxxxxxxxxxxxxx  multiSpecies_compound_microsat_analyzer xxxxxxxxxxxxxx 
sub multiSpecies_compound_microsat_analyzer{
	####### PARAMETER ########
	##########################
	
	my $input1 = $_[0];  ###### the *_sput_op4_ii file
	my $input2 = $_[1];  ###### looks like this: my $t8humanoutput = "*_nogap_op_unrand2_match"
	my $output1 = $_[2]; ###### interrupted microsatellite file, in new .interrupted format
	my $output2 = $_[3]; ###### the pure compound microsatellites
	my $org = $_[4];
	my $no_of_species = $_[5];
#	print "IN multiSpecies_compound_microsat_analyzer: $input1\n $input2\n $output1\n $output2\n $org\n $no_of_species\n";
	$infocord = 2 + (4*$no_of_species) - 1;
	$typecord = 2 + (4*$no_of_species) + 1 - 1;
	$startcord = 2 + (4*$no_of_species) + 2 - 1;
	$strandcord = 2 + (4*$no_of_species) + 3 - 1;
	$endcord = 2 + (4*$no_of_species) + 4 - 1;
	$microsatcord = 2 + (4*$no_of_species) + 5 - 1;
	$motifcord = 2 + (4*$no_of_species) + 6 - 1;
	
	open(IN,"<$input1") or die "Cannot open file $input1 $!";
	open(SEQ,"<$input2") or die "Cannot open file $input2 $!";
	
	open(OUT,">$output1") or die "Cannot open file $output1 $!";
	open(OUT2,">$output2") or die "Cannot open file $output2 $!";
	
	
#	print "opened files \n";
	my %micros = ();
	my $keycounter=0;
	my $linecounter=0;
	while (my $line = <IN>){
		$linecounter++;
		if ($line =~ /([0-9a-zA-Z]+)\s([0-9a-zA-Z_]+)\s([0-9]+)\s([0-9]+)\s([0-9a-zA-Z]+)\s([0-9a-zA-Z_]+)\s([0-9]+)\s([0-9]+)\s([0-9a-zA-Z]+)\s([0-9a-zA-Z_]+)\s([0-9]+)\s([0-9]+)\s/ ) {
			my $key = join("\t",$1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12);
			push (@{$micros{$key}},$line);		
			$keycounter++;
		}
		else{
	#		print "no key\n";
		}
	}
	close IN;
	my @deletedlines = ();
#	print "done hash . linecounter=$linecounter, keycounter=$keycounter\n";
	#---------------------------------------------------------------------------------------------------
	# NOW READING THE SEQUENCE FILE
	my $keyfound=0;
	my $keyexists=0;
	my $inter=0;
	my $pure=0;
	
	while(my $sine = <SEQ>){
		my %microstart=();
		my %microend=();
		my @sields = split(/\t/,$sine);
		my $key = 0;
		if ($sine =~ /([0-9a-zA-Z]+)\s([0-9a-zA-Z_]+)\s([0-9]+)\s([0-9]+)\s[\+|\-]\s([0-9a-zA-Z]+)\s([0-9a-zA-Z_]+)\s([0-9]+)\s([0-9]+)\s[\+|\-]\s([0-9a-zA-Z]+)\s([0-9a-zA-Z_]+)\s([0-9]+)\s([0-9]+)\s/ ) {
			$key = join("\t",$1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12);
		#	print $sine;
		#	print $key;
			$keyfound++;
		}
		else{
		
		}
		#<STDIN> if !defined $key;

		if (exists $micros{$key}){
			$keyexists++;
			my @microstring = @{$micros{$key}};
	
			my @filteredmicrostring;
			
			foreach my $line (@microstring){
				chomp $line;
				my $copy_line = $line;
				my @fields = split(/\t/,$line);
				my $start = $fields[$startcord];
				my $end = $fields[$endcord];				
				# FOR COMPOUND MICROSATELLITES	
				if ($fields[$typecord] eq "compound"){					
					$line = compound_microsat_analyser($line);	
					if ($line eq "NULL") {
						print OUT2 "$copy_line\n";
						$pure++;
						next;
					}
					else{
						print OUT "$line\n";
						$inter++;
						next;
					}
				}
			}
			
		}	#if (exists $micros{$key}){
	}
	close OUT;
	close OUT2;
#	print "keyfound=$keyfound, keyexists=$keyexists, pure=$pure, inter=$inter\n";
}
	
sub compound_microsat_analyser{
	my $line = $_[0];
	my @fields = split(/\t/,$line);
	my $motifline = $fields[$motifcord];
	my $microsat = $fields[$microsatcord];
	$motifline =~ s/^\[|\]$//g;
	$microsat =~ s/^\[|\]$//g;
	$microsat =~ s/-//g;
	my @interruptions = ();
	my @motields = split(/\]\[/,$motifline);
	my @microields = split(/\][a-zA-Z|-]*\[/,$microsat);
	my @inields = split(/[.*]/,$microsat);
	shift @inields;
	my @motifcount = scalar(@motields);
	my $prevmotif = $motields[0];
	my $prevmicro = $microields[0];
	my $prevphase = substr($microields[0],-(length($motields[0])),length($motields[0]));
	my $localflag = 'down';
	my @infoarray = ();
	
	for my $l (1 ... (scalar(@motields)-1)){
		my $probe = $prevmotif.$prevmotif;
		if (length $prevmotif != length $motields[$l]) {$localflag = "up"; last;}
		
		if ($probe =~ /$motields[$l]/i){ 
			my $curr_endphase = substr($microields[$l],-length($motields[$l]),length($motields[$l]));
			my $curr_startphase = substr($microields[$l],0,length($motields[$l]));
			if ($curr_startphase =~ /$prevphase/i) {
				$infoarray[$l-1] = "insertion";
			}
			else {
				$infoarray[$l-1] = "indel/substitution";
			}
		
			$prevmotif = $motields[$l]; $prevmicro = $microields[$l]; $prevphase = $curr_endphase;
			next;
		}
		else {$localflag = "up"; last;}
	}
	if ($localflag eq 'up') {return "NULL";}
	
	if (length($prevmotif) == 1) {$fields[$typecord] = "mononucleotide";}
	if (length($prevmotif) == 2) {$fields[$typecord] = "dinucleotide";}
	if (length($prevmotif) == 3) {$fields[$typecord] = "trinucleotide";}
	if (length($prevmotif) == 4) {$fields[$typecord] = "tetranucleotide";}
	if (length($prevmotif) == 5) {$fields[$typecord] = "pentanucleotide";}

	@microields = split(/[\[|\]]/,$microsat);
	my @microsats = ();
	my @positions = ();
	my $lengthtracker = 0;

	for my $i (0 ... (scalar(@microields ) - 1)){
		if ($i%2 == 0){
			push(@microsats,$microields[$i]);
			$lengthtracker = $lengthtracker + length($microields[$i]);

		}
		else{			
			push(@interruptions,$microields[$i]);
			push(@positions, $lengthtracker+1);
			$lengthtracker = $lengthtracker + length($microields[$i]);	
		}				
		
	}
	my $returnline = join("\t",(join("\t",@fields),join(",",(@infoarray)),join(",",(@interruptions)),join(",",(@positions)),scalar(@interruptions)));
	return($returnline);
}

#xxxxxxxxxxxxxx multiSpecies_compound_microsat_analyzer xxxxxxxxxxxxxx  multiSpecies_compound_microsat_analyzer xxxxxxxxxxxxxx  multiSpecies_compound_microsat_analyzer xxxxxxxxxxxxxx 


#xxxxxxxxxxxxxx multiSpecies_compoundClarifyer xxxxxxxxxxxxxx  multiSpecies_compoundClarifyer xxxxxxxxxxxxxx  multiSpecies_compoundClarifyer xxxxxxxxxxxxxx 

sub multiSpecies_compoundClarifyer{	
#	print "IN multiSpecies_compoundClarifyer: @_\n";
	my $input1 = $_[0];  ###### the *_sput_compound
	my $input2 = $_[1];  ###### looks like this: my $t8humanoutput = "*_nogap_op_unrand2_match"
	my $output1 = $_[2]; ###### interrupted microsatellite file, in new .interrupted format
	my $output2 = $_[3]; ###### compound file
	my $org = $_[4];
	my $no_of_species = $_[5];
	@thresholds = "0";
	push(@thresholds, split(/_/,$_[6]));
	
	
	$infocord = 2 + (4*$no_of_species) - 1;
	$typecord = 2 + (4*$no_of_species) + 1 - 1;
	$startcord = 2 + (4*$no_of_species) + 2 - 1;
	$strandcord = 2 + (4*$no_of_species) + 3 - 1;
	$endcord = 2 + (4*$no_of_species) + 4 - 1;
	$microsatcord = 2 + (4*$no_of_species) + 5 - 1;
	$motifcord = 2 + (4*$no_of_species) + 6 - 1;
	$sequencepos = 2 + (5*$no_of_species) + 1 -1 ; 
	
	$interr_poscord = $motifcord + 3;
	$no_of_interruptionscord = $motifcord + 4;
	$interrcord = $motifcord + 2;
	$interrtypecord = $motifcord + 1;
	
	
	open(IN,"<$input1") or die "Cannot open file $input1 $!";
	open(SEQ,"<$input2") or die "Cannot open file $input2 $!";
	
	open(INT,">$output1") or die "Cannot open file $output2 $!";
	open(COMP,">$output2") or die "Cannot open file $output2 $!";
	#open(CH,">changed") or die "Cannot open file changed $!";
		
#	print "opened files \n";
	my $linecounter = 0;
	my $microcounter = 0;
	
	my %micros = ();
	while (my $line = <IN>){
	#	print "$org\t(chr[0-9a-zA-Z]+)\t([0-9]+)\t([0-9])+\t \n";
		$linecounter++;
		if ($line =~ /($focalspec)\s+([0-9a-zA-Z_\-]+)\s+([0-9]+)\s+([0-9]+)/ ) {
			my $key = join("\t",$1, $2, $3, $4);
	#		print $key, "#-#-#-#-#-#-#-#\n";
	#		print "key = $key\n";
			push (@{$micros{$key}},$line);	
			$microcounter++;
		}
		else {#print $line," key not made\n"; <STDIN>;
			}
	}
#	print "number of microsatellites added to hash = $microcounter\nnumber of lines scanned = $linecounter\n";
	close IN;
	my @deletedlines = ();
#	print "done hash \n";
	$linecounter = 0;
	#---------------------------------------------------------------------------------------------------
	# NOW READING THE SEQUENCE FILE
	my @microsat_types = qw(_ mononucleotide dinucleotide trinucleotide tetranucleotide);
	 $printer = 0;
	
	while(my $sine = <SEQ>){
		my %microstart=();
		my %microend=();
		my @sields = split(/\t/,$sine);
		my $key = ();
		
#		print "sine = $sine. focalspec = $focalspec \n"; #<STDIN>;
		
		if ($sine =~ /($focalspec)\s+([0-9a-zA-Z_\-]+)\s+([0-9]+)\s+([0-9]+)/ ) {
			
#			if ($sine =~ /([a-z0-9A-Z]+)\s+([0-9a-zA-Z_]+)\s+([0-9]+)\s+([0-9]+)\s+[\+|\-]\s+([a-z0-9A-Z]+)\s+([0-9a-zA-Z_]+)\s+([0-9]+)\s+([0-9]+)\s+[\+|\-]\s+([a-z0-9A-Z]+)\s+([0-9a-zA-Z_]+)\s+([0-9]+)\s+([0-9]+)\s/ ) {
			$key = join("\t",$1, $2, $3, $4);
#			print "key = $key\n";
		}
		else{
#			print "no key in $sine\nfor pattern ([a-z0-9A-Z]+) (chr[0-9a-zA-Z]+) ([0-9]+) ([0-9]+) [\+|\-] (a-z0-9A-Z) (chr[0-9a-zA-Z]+) ([0-9]+) ([0-9]+) [\+|\-] (a-z0-9A-Z) (chr[0-9a-zA-Z]+) ([0-9]+) ([0-9]+)   / \n"; 
		}
	
		if (exists $micros{$key}){
			my @microstring = @{$micros{$key}};
			delete $micros{$key};
			
			foreach my $line (@microstring){
#				print "#---------#---------#---------#---------#---------#---------#---------#---------\n" if $printer == 1; 
#				print "microsat = $line" if $printer == 1; 
				$linecounter++; 
				my $copy_line = $line;
				my @mields = split(/\t/,$line);
				my @fields = @mields;
				my $start = $fields[$startcord];
				my $end = $fields[$endcord];
				my $microsat = $fields[$microsatcord];
				my $motifline = $fields[$motifcord];
				my $microsatcopy = $microsat;
				my $positioner = $microsat;
				$positioner =~ s/[a-zA-Z|-]/_/g;
				$microsatcopy =~ s/^\[|\]$//gs;
				chomp $microsatcopy;
				my @microields = split(/\][a-zA-Z|-]*\[/,$microsatcopy);
				my @inields = split(/\[[a-zA-Z|-]*\]/,$microsat);
				my $absolutstart = 1; my $absolutend = $absolutstart + ($end-$start);
#				print "absolut: start = $absolutstart, end = $absolutend\n" if $printer == 1;
				shift @inields;
				#print "inields =@inields<\n";
				$motifline =~ s/^\[|\]$//gs;
				chomp $motifline;
				#print "microsat = $microsat, its copy = $microsatcopy motifline = $motifline<\n";
				my @motields = split(/\]\[/,$motifline);
				my $seq = $microsatcopy;
				$seq =~ s/\[|\]//g;
				my $seqlen = length($seq);
				$seq = " ".$seq;
	
				my $longestmotif_no = longest_array_element(@motields);
				my $shortestmotif_no = shortest_array_element(@motields);
				#print "shortest motif = $motields[$shortestmotif_no], longest motif = $motields[$longestmotif_no] \n";
			
				my $search = $motields[$longestmotif_no].$motields[$longestmotif_no];
				if ((length($motields[$longestmotif_no]) == length($motields[$shortestmotif_no])) && ($search !~ /$motields[$shortestmotif_no]/) ){
					print COMP $line;
					next;
				}
			
				my @shortestmotif_nos = ();
				for my $m (0 ... $#motields){
					push(@shortestmotif_nos, $m) if (length($motields[$m]) == length($motields[$shortestmotif_no]) );
				}
				## LOOKING AT LEFT OF THE SHORTEST MOTIF------------------------------------------------
				my $newleft =();
				my $leftstopper = 0; my $rightstopper = 0;
				foreach my $shortmotif_no (@shortestmotif_nos){
					next if $shortmotif_no == 0;
					my $last_left =  $shortmotif_no; #$#motields;
					my $last_hitter = 0;
					for (my $i =($shortmotif_no-1); $i>=0; $i--){	
						my $search  = $motields[$shortmotif_no];
						if (length($motields[$shortmotif_no]) == 1){ $search = $motields[$shortmotif_no].$motields[$shortmotif_no] ;}
						if( (length($motields[$i]) > length($motields[$shortmotif_no])) && length($microields[$i]) > (2.5 * length($motields[$i])) ){
							$last_hitter = 1;
							$last_left = $i+1; last;				
						}
						my $probe = $motields[$i];
						if (length($motields[$shortmotif_no]) == length($motields[$i])) {$probe = $motields[$i].$motields[$i];}
	
						if ($probe !~ /$search/){
							$last_hitter = 1;
							$last_left = $i+1; 
	#						print "hit the last match: before $microields[$i]..last left = $last_left.. exiting.\n";
							last;
						}
						$last_left--;$last_hitter = 1;
	#					print "passed tests, last left = $last_left\n";
					}
	#				print "comparing whether $last_left < $shortmotif_no, lasthit = $last_hitter\n";
					if (($last_left) < $shortmotif_no && $last_hitter == 1) {$leftstopper=0; last;}
					else {$leftstopper = 1;
	#					print "leftstopper = 1\n";
					}
				}
				
				## LOOKING AT LEFT OF THE SHORTEST MOTIF------------------------------------------------
				my $newright =();
				foreach my $shortmotif_no (@shortestmotif_nos){
					next if $shortmotif_no == $#motields;
					my $last_right =  $shortmotif_no;# -1;
					for my $i ($shortmotif_no+1 ... $#motields){
						my $search  = $motields[$shortmotif_no];
						if (length($motields[$shortmotif_no]) == 1 ){ $search = $motields[$shortmotif_no].$motields[$shortmotif_no] ;}
						if ( (length($motields[$i]) > length($motields[$shortmotif_no])) && length($microields[$i]) > (2.5 * length($motields[$i])) ){
							$last_right = $i-1; last;			
						}
						my $probe = $motields[$i];
						if (length($motields[$shortmotif_no]) == length($motields[$i])) {$probe = $motields[$i].$motields[$i];}
						if (  $probe !~ /$search/){
							$last_right = $i-1; last;
						}
						$last_right++; 
					}
					if (($last_right) > $shortmotif_no) {$rightstopper=0; last;# print "rightstopper = 0\n";
					}
					else {$rightstopper = 1;
					}
				}
				
				
				if ($rightstopper == 1 && $leftstopper == 1){
					print COMP $line; 
#					print "rightstopper == 1 && leftstopper == 1\n" if $printer == 1; 
					next;
				}
	
#				print "pased initial testing phase \n" if $printer == 1; 
				my @outputs = ();
				my @orig_starts = ();
				my @orig_ends = ();
				for my $mic (0 ... $#microields){
					my $miclen = length($microields[$mic]);
					my $microleftlen = 0;
					#print "\nmic = $mic\n";
					if($mic > 0){
						for my $submin (0 ... $mic-1){
							my $interval = ();
							if (!exists $inields[$submin]) {$interval = "";}
							else {$interval = $inields[$submin];}
							#print "inield =$interval< and microield =$microields[$submin]<\n  ";
							$microleftlen = $microleftlen + length($microields[$submin]) + length($interval);
						}
					}
					push(@orig_starts,($microleftlen+1));
					push(@orig_ends, ($microleftlen+1 + $miclen -1));
				}				
	
	#############  F I N A L L Y   S T U D Y I N G   S E Q U E N C E S  #########@@@@#########@@@@#########@@@@#########@@@@#########@@@@
	
	
				for my $mic (0 ... $#microields){
					my $miclen = length($microields[$mic]);
					my $microleftlen = 0;
					if($mic > 0){
						for my $submin (0 ... $mic-1){
						#	if(!exists $inields[$submin]) {$inields[$submin] = "";}
							my $interval = ();
							if (!exists $inields[$submin]) {$interval = "";}
							else {$interval = $inields[$submin];}
							#print "inield =$interval< and microield =$microields[$submin]<\n  ";
							$microleftlen = $microleftlen + length($microields[$submin]) + length($interval);
						}
					}
					$fields[$startcord] = $microleftlen+1;
					$fields[$endcord] = $fields[$startcord] + $miclen -1;
					$fields[$typecord] = $microsat_types[length($motields[$mic])];
					$fields[$microsatcord] = $microields[$mic];
					$fields[$motifcord] = $motields[$mic];		
					my $templine = join("\t", (@fields[0 .. $motifcord]) );
					my $orig_templine = join("\t", (@fields[0 .. $motifcord]) );
					my $newline;
					my $lefter = 1; my $righter = 1;
					if ( $fields[$startcord] < 2){$lefter = 0;}
					if ($fields[$endcord] == $seqlen){$righter = 0;}
	
					while($lefter == 1){
						$newline = left_extender($templine, $seq,$org);
#						print "returned line from left extender= $newline \n" if $printer == 1; 
						if ($newline eq $templine){$templine = $newline; last;}
						else {$templine = $newline;}
						
						if (left_extention_permission_giver($templine) eq "no") {last;}
					}
					while($righter == 1){
						$newline = right_extender($templine, $seq,$org);
#						print "returned line from right extender= $newline \n" if $printer == 1; 
						if ($newline eq $templine){$templine = $newline; last;}
						else {$templine = $newline;}
						if (right_extention_permission_giver($templine) eq "no") {last;}
					}
					my @tempfields = split(/\t/,$templine);
					$tempfields[$microsatcord] =~ s/\]|\[//g;
					$tempfields[$motifcord] =~ s/^\[|\]$//gs;
					my @tempmotields = split(/\]\[/,$tempfields[$motifcord]);			
					
					if (scalar(@tempmotields) == 1 && $templine eq $orig_templine) { 
#						print "scalar ( tempmotields) = 1\n" if $printer == 1; 
						next;
					} 
					my $prevmotif = shift(@tempmotields);
					my $stopper = 0;
					
					foreach my $tempmot (@tempmotields){
						if (length($tempmot) != length($prevmotif)) {$stopper = 1; last;}
						my $search = $prevmotif.$prevmotif;
						if ($search !~ /$tempmot/) {$stopper = 1; last;}
						$prevmotif = $tempmot;
					}
					if ( $stopper == 1) { 
#						print "length tempmot  != length prevmotif\n" if $printer == 1; 
						next; 
					} 
					my $lastend  = 0;
					#----------------------------------------------------------
					my $left_captured = (); my $right_captured = ();
					my $left_bp = (); my $right_bp = ();
	#				print "new startcord = $tempfields[$startcord] , new endcord  = $tempfields[$endcord].. orig strts = @orig_starts and orig ends = @orig_ends\n";
					for my $o (0 ... $#orig_starts){
#						print "we are talking abut tempstart:$tempfields[$startcord] >= origstart:$lastend && tempstart:$tempfields[$startcord] <= origend: $orig_ends[$o] \n" if $printer == 1; 
#						print "we are talking abut tempend:$tempfields[$endcord] >= origstart:$lastend && tempstart:$tempfields[$endcord] >= origend: $orig_ends[$o] \n" if $printer == 1; 
	
						if (($tempfields[$startcord] > $lastend)  && ($tempfields[$startcord] <= $orig_ends[$o])){ # && ($tempfields[$startcord] != $fields[$startcord])
#							print "motif captured on left is $microields[$o] from $microsat\n" if $printer == 1; 
							$left_captured  = $o;
							$left_bp =  $orig_ends[$o] - $tempfields[$startcord] + 1;
						}
						elsif ($tempfields[$endcord] > $lastend  && $tempfields[$endcord] <= $orig_ends[$o]){ #&& $tempfields[$endcord] != $fields[$endcord])
#							print "motif captured on right is $microields[$o] from $microsat\n" if $printer == 1; 
							$right_captured  = $o;
							$right_bp = $tempfields[$endcord]  - $orig_starts[$o] + 1;
						}
						$lastend = $orig_ends[$o]
					}
#					print "leftcaptured = $left_captured, right = $right_captured\n" if $printer==1;
					my $leftmotif = (); my $left_trashed = ();
					if ($tempfields[$startcord] != $fields[$startcord]) {
						$leftmotif = $motields[$left_captured]; 
#						print "$left_captured in @microields: $motields[$left_captured]\n" if $printer == 1; 
						if ( $left_captured !~ /[0-9]+/) {#print $line,"\n", $templine,"\n"; 
						}
						 $left_trashed = length($microields[$left_captured]) - $left_bp;
					}
					my $rightmotif = (); my $right_trashed = ();
					if ($tempfields[$endcord] != $fields[$endcord]) {
#						print "$right_captured in @microields: $motields[$right_captured]\n" if $printer == 1; 
						$rightmotif = $motields[$right_captured];
						$right_trashed = length($microields[$right_captured]) - $right_bp;
					} 
					
					########## P A R A M S #####################@@@@#########@@@@#########@@@@#########@@@@#########@@@@#########@@@@#########@@@@
					$stopper = 0;
					my $deletioner = 0;
					#if($tempfields[$startcord] != $fields[$startcord]){
#						print "enter left: tempfields,startcord  : $tempfields[$startcord] != $absolutstart && left_captured: $left_captured != 0 \n" if $printer==1;
						if ($left_captured != 0){ 
#							print "at line 370, going: 0 ... $left_captured-1 \n" if $printer == 1;
							for my $e (0 ... $left_captured-1){
								if( length($motields[$e]) > 2 && length($microields[$e]) > (3* length($motields[$e]) )){
#									print "motif on left not included too big to be ignored : $microields[$e] \n" if $printer == 1;  
									$deletioner++; last;
								}
								if( length($motields[$e]) == 2 && length($microields[$e]) > (3* length($motields[$e]) )){
#									print "motif on left not included too big to be ignored : $microields[$e] \n" if $printer == 1;  
									$deletioner++; last;
								}
								if( length($motields[$e]) == 1 && length($microields[$e]) > (4* length($motields[$e]) )){
#									print "motif on left not included too big to be ignored : $microields[$e] \n" if $printer == 1; 
									$deletioner++; last;
								}
							}				
						}
					#}
#					print "after left search, deletioner = $deletioner\n" if $printer == 1;
					if ($deletioner >= 1) {  
#						print "deletioner = $deletioner\n" if $printer == 1;
						next; 
					} 
					
					$deletioner = 0;
	
					#if($tempfields[$endcord] != $fields[$endcord]){				
#						print "if tempfields endcord: $tempfields[$endcord] != absolutend: $absolutend\n and $right_captured != $#microields\n" if $printer==1;
						if ($right_captured != $#microields){ 
#							print "at line 394, going: $right_captured+1 ... $#microields \n" if $printer == 1;
							for my $e ($right_captured+1 ... $#microields){
								if( length($motields[$e]) > 2 &&  length($microields[$e]) > (3* length($motields[$e])) ){
#									print "motif on right not included too big to be ignored : $microields[$e] \n" if $printer == 1; 
									$deletioner++; last;
								}
								if( length($motields[$e]) == 2 && length($microields[$e]) > (3* length($motields[$e]) )){
#									print "motif on right not included too big to be ignored : $microields[$e] \n" if $printer == 1;
									$deletioner++; last;
								}
								if( length($motields[$e]) == 1 && length($microields[$e]) > (4* length($motields[$e]) )){
#									print "motif on right not included too big to be ignored : $microields[$e] \n" if $printer == 1;
									$deletioner++; last;
								}
							}				
						}
					#}
#					print "deletioner = $deletioner\n" if $printer == 1;
					if ($deletioner >= 1) {  
						next; 
					} 
					my $leftMotifs_notCaptured = ();
					my $rightMotifs_notCaptured = ();
									
					if ($tempfields[$startcord] != $fields[$startcord] ){
						#print "in left params: (length($leftmotif) == 1 && $tempfields[$startcord] != $fields[$startcord]) ... and .... $left_trashed > (1.5* length($leftmotif]) && ($tempfields[$startcord] != $fields[$startcord])\n";
						if (length($leftmotif) == 1 && $left_trashed > 3){
#							print "invaded left motif is long mononucleotide" if $printer == 1;
							 next;
	
						}
						elsif ((length($leftmotif) != 1 && $left_trashed > ( thrashallow($leftmotif)) && ($tempfields[$startcord] != $fields[$startcord]) ) ){
#							print "invaded left motif too long" if $printer == 1; 						
							 next; 
						}
					}
					if ($tempfields[$endcord] != $fields[$endcord] ){
						#print "in right params: after $tempfields[$endcord] != $fields[$endcord]  .....   (length($rightmotif)==1 && $tempfields[$endcord] != $fields[$endcord]) ... and ... $right_trashed > (1.5* length($rightmotif))\n";
						if (length($rightmotif)==1 && $right_trashed){
#							print "invaded right motif is long mononucleotide" if $printer == 1; 
							 next; 
	
						}
						elsif (length($rightmotif) !=1 && ($right_trashed > ( thrashallow($rightmotif))  && $tempfields[$endcord] != $fields[$endcord])){
#							print "invaded right motif too long" if $printer == 1;
							 next; 
	
						}
					}
					push @outputs, $templine;
				}
				if (scalar(@outputs) == 0){ print COMP $line; next;}
	#			print "outputs are:", join("\n",@outputs),"\n";
				if (scalar(@outputs) == 1){ 
					my @oields = split(/\t/,$outputs[0]);
					my $start = $oields[$startcord]+$mields[$startcord]-1;
					my $end = $start+($oields[$endcord]-$oields[$startcord]);
					$oields[$startcord] = $start; $oields[$endcord] = $end;
					print INT join("\t",@oields), "\n"; 
				#	print CH $line,;
				}
				if (scalar(@outputs) > 1){ 
					my $motif_min = 10;
					my $chosen_one = $outputs[0];
					foreach my $micro (@outputs){
						my @oields = split(/\t/,$micro);
						my $tempmotif = $oields[$motifcord];
						$tempmotif =~ s/^\[|\]$//gs;
						my @omots = split(/\]\[/, $tempmotif);
			#			print "motif_min  = $motif_min, current motif  = $tempmotif\n";
						my $start = $oields[$startcord]+$mields[$startcord]-1;
						my $end = $start+($oields[$endcord]-$oields[$startcord]);
						$oields[$startcord] = $start; $oields[$endcord] = $end;
						if(length($omots[0]) < $motif_min) {
							$chosen_one = join("\t",@oields); 
							$motif_min = length($omots[0]);
						}
					}
					print INT $chosen_one, "\n";
				#	print "chosen one is ".$chosen_one, "\n";
				#	print CH $line;
				
				
				}
				
			}
			
		}	#if (exists $micros{$key}){
		else{
		}
	}
	close INT;
	close COMP;
}
sub left_extender{
	#print "left extender\n";
	my ($line, $seq, $org) = @_;	
#	print "in left extender... line passed = $line and sequence is $seq\n";
	chomp $line;
	my @fields = split(/\t/,$line);
	my $rstart = $fields[$startcord];
	my $microsat = $fields[$microsatcord];
	$microsat =~ s/\[|\]//g;
	my $rend = $rstart + length($microsat)-1;
	$microsat =~ s/-//g;
	my $motif = $fields[$motifcord];
	my $firstmotif = ();

	if ($motif =~ /^\[/){
		$motif =~ s/^\[//g;
		$motif =~ /([a-zA-Z]+)\].*/;
		$firstmotif = $1;
	}
	else {$firstmotif = $motif;}
	
	#print "hacked microsat = $microsat, motif = $motif, firstmotif = $firstmotif\n";
	my $leftphase = substr($microsat, 0,length($firstmotif));
	my $phaser = $leftphase.$leftphase;
	my @phase = split(/\s*/,$leftphase);
	my @phases;
	my @copy_phases = @phases;
	my $crawler=0;
	for (0 ... (length($leftphase)-1)){
		push(@phases, substr($phaser, $crawler, length($leftphase)));
		$crawler++;
	}

	my $start = $rstart;
	my $end = $rend;
	
	my $leftseq = substr($seq, 0, $start);
#	print "left phases are @phases , start = $start left sequence = ",substr($leftseq, -10),"\n";	
	my @extentions = ();
	my @trappeds = ();
	my @intervalposs = ();
	my @trappedposs = ();
	my @trappedphases = ();
	my @intervals = ();
	my $firstmotif_length = length($firstmotif);
	foreach my $phase (@phases){
#		print "left phase\t",substr($leftseq, -10),"\t$phase\n";
#		print "search patter = (($phase)+([a-zA-Z|-]{0,$firstmotif_length})) \n";
		if ($leftseq =~ /(($phase)+([a-zA-Z|-]{0,$firstmotif_length}))$/i){
#			print "in left pattern\n";
			my $trapped = $1;
			my $trappedpos = length($leftseq)-length($trapped);
			my $interval = $3;
			my $intervalpos = index($trapped, $interval) + 1;
#			print "left trapped = $trapped, interval = $interval, intervalpos = $intervalpos\n";

			my $extention = substr($trapped, 0, length($trapped)-length($interval));
			my $leftpeep = substr($seq, 0, ($start-length($trapped)));
			my @passed_overhangs;
			
			for my $i (1 ... length($phase)-1){
				my $overhang = substr($phase, -length($phase)+$i);
#				print "current overhang = $overhang, leftpeep = ",substr($leftpeep,-10)," whole sequence = ",substr($seq, ($end - ($end-$start) - 20), (($end-$start)+20)),"\n";
				#TEMPORARY... BETTER METHOD NEEDED
				$leftpeep =~ s/-//g;
				if ($leftpeep =~ /$overhang$/i){
					push(@passed_overhangs,$overhang);
#					print "l overhang\n";
				}
			}
			
			if(scalar(@passed_overhangs)>0){
				my $overhang = $passed_overhangs[longest_array_element(@passed_overhangs)];
				$extention = $overhang.$extention;
				$trapped = $overhang.$trapped;
				#print "trapped extended to $trapped \n";
				$trappedpos = length($leftseq)-length($trapped);
			}
			
			push(@extentions,$extention);
#			print "extentions = @extentions \n";

			push(@trappeds,$trapped );
			push(@intervalposs,length($extention)+1);
			push(@trappedposs, $trappedpos);
#			print "trappeds = @trappeds\n";
			push(@trappedphases, substr($extention,0,length($phase)));
			push(@intervals, $interval);
		}
	}
	if (scalar(@trappeds == 0)) {return $line;}
	
	my $nikaal = shortest_array_element(@intervals);
	
	if ($fields[$motifcord] !~ /\[/i) {$fields[$motifcord] = "[".$fields[$motifcord]."]";}
	$fields[$motifcord] = "[".$trappedphases[$nikaal]."]".$fields[$motifcord];
	##print "new fields 9 = $fields[9]\n";
	$fields[$startcord] = $fields[$startcord]-length($trappeds[$nikaal]);

	if($fields[$microsatcord] !~ /^\[/i){
		$fields[$microsatcord] = "[".$fields[$microsatcord]."]";
	}
	
	$fields[$microsatcord] = "[".$extentions[$nikaal]."]".$intervals[$nikaal].$fields[$microsatcord];
	
	if (exists ($fields[$motifcord+1])){
		$fields[$motifcord+1] = "indel/deletion,".$fields[$motifcord+1];
	}
	else{$fields[$motifcord+1] = "indel/deletion";}
	##print "new fields 14 = $fields[14]\n";
	
	if (exists ($fields[$motifcord+2])){		
		$fields[$motifcord+2] = $intervals[$nikaal].",".$fields[$motifcord+2];
	}
	else{$fields[$motifcord+2] =  $intervals[$nikaal];}	
	my @seventeen=();	
	if (exists ($fields[$motifcord+3])){			
		@seventeen = split(/,/,$fields[$motifcord+3]);	
	#	#print "scalarseventeen =@seventeen<-\n";
		for (0 ... scalar(@seventeen)-1) {$seventeen[$_] = $seventeen[$_]+length($trappeds[$nikaal]);}
		$fields[$motifcord+3] = ($intervalposs[$nikaal]).",".join(",",@seventeen);
		$fields[$motifcord+4] = $fields[$motifcord+4]+1;
	}
	
	else {$fields[$motifcord+3] = $intervalposs[$nikaal]; $fields[$motifcord+4]=1}
	
	##print "new fields 16 = $fields[16]\n";
	##print "new fields 17 = $fields[17]\n";
	
	
	my $returnline =  join("\t",@fields);
	my $pastline  = $returnline;
	if ($fields[$microsatcord] =~ /\[/){
		$returnline = multiSpecies_compoundClarifyer_merge($returnline);
	}
	return $returnline;
}
sub right_extender{
	my ($line, $seq, $org) = @_;	
	chomp $line;
	my @fields = split(/\t/,$line);
	my $rstart = $fields[$startcord];
	my $microsat = $fields[$microsatcord];
	$microsat =~ s/\[|\]//g;
	my $rend = $rstart + length($microsat)-1;
	$microsat =~ s/-//g;
	my $motif = $fields[$motifcord];
	my $temp_lastmotif = ();

	if ($motif =~ /\]$/s){
		$motif =~ s/\]$//sg;
		$motif =~ /.*\[([a-zA-Z]+)/;
		$temp_lastmotif = $1;
	}
	else {$temp_lastmotif = $motif;}
	my $lastmotif = substr($microsat,-length($temp_lastmotif));
	##print "hacked microsat = $microsat, motif = $motif, lastmotif = $lastmotif\n";
	my $rightphase = substr($microsat, -length($lastmotif));
	my $phaser = $rightphase.$rightphase;
	my @phase = split(/\s*/,$rightphase);
	my @phases;
	my @copy_phases = @phases;
	my $crawler=0;
	for (0 ... (length($rightphase)-1)){
		push(@phases, substr($phaser, $crawler, length($rightphase)));
		$crawler++;
	}

	my $start = $rstart;
	my $end = $rend;
	
	my $rightseq = substr($seq, $end+1);
	my @extentions = ();
	my @trappeds = ();
	my @intervalposs = ();
	my @trappedposs = ();
	my @trappedphases = ();
	my @intervals = ();
	my $lastmotif_length = length($lastmotif);
	foreach my $phase (@phases){
		if ($rightseq =~ /^(([a-zA-Z|-]{0,$lastmotif_length}?)($phase)+)/i){
			my $trapped = $1;
			my $trappedpos = $end+1;
			my $interval = $2;
			my $intervalpos = index($trapped, $interval) + 1;

			my $extention = substr($trapped, length($interval));
			my $rightpeep = substr($seq, ($end+length($trapped))+1);
			my @passed_overhangs = "";
			
			#TEMPORARY... BETTER METHOD NEEDED
			$rightpeep =~ s/-//g;

			for my $i (1 ... length($phase)-1){
				my $overhang = substr($phase,0, $i);
#				#print "current extention = $extention, overhang = $overhang, rightpeep = ",substr($rightpeep,0,10),"\n";
				if ($rightpeep =~ /^$overhang/i){
					push(@passed_overhangs, $overhang);
#					#print "r overhang\n";
				}
			}
			if (scalar(@passed_overhangs) > 0){			
				my $overhang = @passed_overhangs[longest_array_element(@passed_overhangs)];
				$extention = $extention.$overhang;
				$trapped = $trapped.$overhang;
#				#print "trapped extended to $trapped \n";
			}
		
			push(@extentions,$extention);
			##print "extentions = @extentions \n";

			push(@trappeds,$trapped );
			push(@intervalposs,$intervalpos);
			push(@trappedposs, $trappedpos);
#			#print "trappeds = @trappeds\n";
			push(@trappedphases, substr($extention,0,length($phase)));
			push(@intervals, $interval);
		}
	}
	if (scalar(@trappeds == 0)) {return $line;}
	
#	my $nikaal = longest_array_element(@trappeds);
	my $nikaal = shortest_array_element(@intervals);
	
#	#print "longest element found = $nikaal \n";
	
	if ($fields[$motifcord] !~ /\[/i) {$fields[$motifcord] = "[".$fields[$motifcord]."]";}
	$fields[$motifcord] = $fields[$motifcord]."[".$trappedphases[$nikaal]."]";
	##print "new fields 9 = $fields[9]";
	$fields[$endcord] = $fields[$endcord] + length($trappeds[$nikaal]);

	##print "new fields 11 = $fields[11]\n";

	if($fields[$microsatcord] !~ /^\[/i){
		$fields[$microsatcord] = "[".$fields[$microsatcord]."]";
	}
	
	$fields[$microsatcord] = $fields[$microsatcord].$intervals[$nikaal]."[".$extentions[$nikaal]."]";
	##print "new fields 12 = $fields[12]\n";
	
	##print "scalar of fields = ",scalar(@fields),"\n";
	if (exists ($fields[$motifcord+1])){
#		print " print fields = @fields.. scalar=", scalar(@fields),".. motifcord+1 = $motifcord + 1 \n " if !exists $fields[$motifcord+1];
#		<STDIN> if !exists $fields[$motifcord+1];
		$fields[$motifcord+1] = $fields[$motifcord+1].",indel/deletion";
	}
	else{$fields[$motifcord+1] = "indel/deletion";}
	##print "new fields 14 = $fields[14]\n";
	
	if (exists ($fields[$motifcord+2])){
		$fields[$motifcord+2] = $fields[$motifcord+2].",".$intervals[$nikaal];
	}
	else{$fields[$motifcord+2] =  $intervals[$nikaal];}	
	##print "new fields 15 = $fields[15]\n";

	my @seventeen=();
	if (exists ($fields[$motifcord+3])){
		##print "at 608 we are doing this:length($microsat)+$intervalposs[$nikaal]\n";
#		print " print fields = @fields\n " if !exists $fields[$motifcord+3];
		<STDIN> if !exists $fields[$motifcord+3];
		my $currpos = length($microsat)+$intervalposs[$nikaal];
		$fields[$motifcord+3] = $fields[$motifcord+3].",".$currpos;
		$fields[$motifcord+4] = $fields[$motifcord+4]+1;

	}
	
	else {$fields[$motifcord+3] = length($microsat)+$intervalposs[$nikaal]; $fields[$motifcord+4]=1}
	
	##print "new fields 16 = $fields[16]\n";
	
	##print "new fields 17 = $fields[17]\n";
	my $returnline = join("\t",@fields);
	my $pastline  = $returnline;
	if ($fields[$microsatcord] =~ /\[/){
		$returnline = multiSpecies_compoundClarifyer_merge($returnline);
	}
	#print "finally right-extended line = ",$returnline,"\n";
	return $returnline;
}
sub longest_array_element{
	my $counter = 0;
	my($max) = shift(@_);
	my $maxcounter = 0;
    foreach my $temp (@_) {
    	$counter++;
    	#print "finding largest array: $maxcounter \n" if $prinkter == 1;
    	if(length($temp) > length($max)){
        	$max = $temp;
        	$maxcounter = $counter;
        }
    }
    return($maxcounter);
}
sub shortest_array_element{
	my $counter = 0;
	my($min) = shift(@_);
	my $mincounter = 0;
    foreach my $temp (@_) {
    	$counter++;
    	#print "finding largest array: $mincounter \n" if $prinkter == 1;
    	if(length($temp) < length($min)){
        	$min = $temp;
        	$mincounter = $counter;
        }
    }
    return($mincounter);
}


sub left_extention_permission_giver{
	my @fields = split(/\t/,$_[0]);
	my $microsat = $fields[$microsatcord];
	$microsat =~ s/(^\[)|-//g;
	my $motif = $fields[$motifcord];
	my $firstmotif = ();
	my $firststretch = ();
	my @stretches=();
	if ($motif =~ /^\[/){
		$motif =~ s/^\[//g;
		$motif =~ /([a-zA-Z]+)\].*/;
		$firstmotif = $1;
		@stretches = split(/\]/,$microsat);
		$firststretch = $stretches[0];
		##print "firststretch = $firststretch\n";
	}
	else {$firstmotif = $motif;$firststretch = $microsat;}
	
	if (length($firststretch) < $thresholds[length($firstmotif)]){
		return "no";
	}
	else {return "yes";}

}
sub right_extention_permission_giver{
	my @fields = split(/\t/,$_[0]);
	my $microsat = $fields[$microsatcord];
	$microsat =~ s/-|(\]$)//sg;
	my $motif = $fields[$motifcord];
	my $temp_lastmotif = ();
	my $laststretch = ();
	my @stretches=();


	if ($motif =~ /\]/){
		$motif =~ s/\]$//gs;
		$motif =~ /.*\[([a-zA-Z]+)$/;
		$temp_lastmotif = $1;
		@stretches = split(/\[/,$microsat);
		$laststretch = pop(@stretches);
		##print "last stretch = $laststretch\n";
	}
	else {$temp_lastmotif = $motif; $laststretch = $microsat;}

	if (length($laststretch) < $thresholds[length($temp_lastmotif)]){
		return "no";
	}
	else { return "yes";}


}
sub multiSpecies_compoundClarifyer_merge{
	my $line = $_[0];
	#print "sent for mering: $line \n";
	my @mields = split(/\t/,$line);
	my @fields = @mields;
	my $microsat = $fields[$microsatcord];
	my $motifline = $fields[$motifcord];
	my $microsatcopy = $microsat;
	$microsatcopy =~ s/^\[|\]$//sg;
	my @microields = split(/\][a-zA-Z|-]*\[/,$microsatcopy);
	my @inields = split(/\[[a-zA-Z|-]*\]/,$microsat);
	shift @inields;
	#print "inields =@inields<\n";
	$motifline =~ s/^\[|\]$//sg;
	my @motields = split(/\]\[/,$motifline);
	my @firstmotifs = ();
	my @lastmotifs = ();
	for my $i  (0 ... $#microields){
		$firstmotifs[$i] =  substr($microields[$i],0,length($motields[$i]));
		$lastmotifs[$i] = substr($microields[$i],-length($motields[$i]));
	}
	#print "firstmotif = @firstmotifs... lastmotif = @lastmotifs\n";
	my @mergelist = ();
	my @inter_poses = split(/,/,$fields[$interr_poscord]);
	my $no_of_interruptions = $fields[$no_of_interruptionscord];
	my @interruptions = split(/,/,$fields[$interrcord]);
	my @interrtypes = split(/,/,$fields[$interrtypecord]);
	my $stopper = 0;
	for my $i (0 ... $#motields-1){
		#print "studying connection of $motields[$i] and $motields[$i+1], i = $i in $microsat\n";
		if (($lastmotifs[$i] eq $firstmotifs[$i+1]) && !exists $inields[$i]){
			$stopper = 1;
			push(@mergelist, ($i)."_".($i+1));
		}
	}
	
	return $line if scalar(@mergelist) == 0;
	
	foreach my $merging (@mergelist){
		my @sets = split(/_/, $merging);
		my @tempmicro = ();
		my @tempmot = ();
		for my $i (0 ... $sets[0]-1){
			push(@tempmicro, "[".$microields[$i]."]");
			push(@tempmicro, $inields[$i]);
			push(@tempmot, "[".$motields[$i]."]");
			#print "adding pre-motifs number $i\n";
		}
		my $pusher = "[".$microields[$sets[0]].$microields[$sets[1]]."]";
		push (@tempmicro, $pusher);
		push(@tempmot, "[".$motields[$sets[0]]."]");
		my $outcoming = -2;
		for my $i ($sets[1]+1 ... $#microields-1){
			push(@tempmicro, "[".$microields[$i]."]");
			push(@tempmicro, $inields[$i]);	
			push(@tempmot, "[".$motields[$i]."]");
			#print "adding post-motifs number $i\n";
			$outcoming  = $i;
		}
		if ($outcoming != -2){
			#print "outcoming = $outcoming \n";
			push(@tempmicro, "[".$microields[$outcoming+1 ]."]");
			push(@tempmot,"[". $motields[$outcoming+1]."]");
		}
		$fields[$microsatcord] = join("",@tempmicro);
		$fields[$motifcord] = join("",@tempmot);
		
		splice(@interrtypes, $sets[0], 1);
		$fields[$interrtypecord] = join(",",@interrtypes);
		splice(@interruptions, $sets[0], 1);
		$fields[$interrcord] = join(",",@interruptions);
		splice(@inter_poses, $sets[0], 1);
		$fields[$interr_poscord] = join(",",@inter_poses);
		$no_of_interruptions = $no_of_interruptions - 1;
	}	

	if ($no_of_interruptions == 0){
		$fields[$microsatcord] =~ s/^\[|\]$//sg;
		$fields[$motifcord] =~ s/^\[|\]$//sg;
		$line = join("\t", @fields[0 ... $motifcord]);		
	}
	else{
		$line = join("\t", @fields);
	}
	return $line;
}

sub thrashallow{
	my $motif = $_[0];
	return 4 if length($motif) == 2;
	return 6 if length($motif) == 3;
	return 8 if length($motif) == 4;
	
}

#xxxxxxxxxxxxxx multiSpecies_compoundClarifyer xxxxxxxxxxxxxx  multiSpecies_compoundClarifyer xxxxxxxxxxxxxx  multiSpecies_compoundClarifyer xxxxxxxxxxxxxx 


#xxxxxxxxxxxxxx multispecies_filtering_compound_microsats xxxxxxxxxxxxxx  multispecies_filtering_compound_microsats xxxxxxxxxxxxxx  multispecies_filtering_compound_microsats xxxxxxxxxxxxxx 
sub multispecies_filtering_compound_microsats{
	my $unfiltered = $_[0];
	my $filtered = $_[1];
	my $residue = $_[2];
	my $no_of_species = $_[5];
	open(UNF,"<$unfiltered") or die "Cannot open file $unfiltered: $!";
	open(FIL,">$filtered") or die "Cannot open file $filtered: $!";
	open(RES,">$residue") or die "Cannot open file $residue: $!";
	
	$infocord = 2 + (4*$no_of_species) - 1;
	$startcord = 2 + (4*$no_of_species) + 2 - 1;
	$strandcord = 2 + (4*$no_of_species) + 3 - 1;
	$endcord = 2 + (4*$no_of_species) + 4 - 1;
	$microsatcord = 2 + (4*$no_of_species) + 5 - 1;
	$motifcord = 2 + (4*$no_of_species) + 6 - 1;
	
	my @sub_thresholds = ("0");
	push(@sub_thresholds, split(/_/,$_[3]));
	my @thresholds = ("0");
	push(@thresholds, split(/_/,$_[4]));
	
	while (my $line = <UNF>) {
		if ($line !~ /compound/){
			print FIL $line,"\n"; next;
		}
		chomp $line;
		my @fields = split(/\t/,$line);
		my $motifline = $fields[$motifcord];
		$motifline =~ s/^\[|\]$//g;
		my @motifs = split(/\]\[/,$motifline);
		my $microsat = $fields[$microsatcord];
		$microsat =~ s/^\[|\]$|-//g;
		my @microsats = split(/\][a-zA-Z|-]*\[/,$microsat);		
		
		my $stopper = 0;
		for my $i (0 ... $#motifs){
			my @common = ();
			my $probe = $motifs[$i].$motifs[$i];
			my $motif_size = length($motifs[$i]);
		
			for my $j (0 ... $#motifs){	
				next if length($motifs[$i]) != length($motifs[$j]);
				push(@common, length($microsats[$j])) if $probe =~ /$motifs[$j]/i;
			}
			
			if (largest_microsat(@common) < $sub_thresholds[$motif_size]) {$stopper = 1; last;}
			else {next;}
		}
		
		if ($stopper  == 1){
			print RES $line,"\n";
		}
		else { print FIL $line,"\n"; }
	}
	close FIL;
	close RES;
}

#xxxxxxxxxxxxxx multispecies_filtering_compound_microsats xxxxxxxxxxxxxx  multispecies_filtering_compound_microsats xxxxxxxxxxxxxx  multispecies_filtering_compound_microsats xxxxxxxxxxxxxx 


#xxxxxxxxxxxxxx chromosome_unrand_breaker xxxxxxxxxxxxxx  chromosome_unrand_breaker xxxxxxxxxxxxxx  chromosome_unrand_breaker xxxxxxxxxxxxxx 

sub chromosome_unrand_breaker{
#	print "IN chromosome_unrand_breaker: @_\n ";
	my $input1 = $_[0];  ###### looks like this: my $t8humanoutput = "*_nogap_op_unrand2_match"
	my $dir = $_[1]; ###### directory where subsets are put
	my $output2 = $_[2]; ###### list of subset files
	my $increment = $_[3];
	my $info = $_[4];
	my $chr = $_[5];
	open(SEQ,"<$input1") or die "Cannot open file $input1 $!";
	
	open(OUT,">$output2") or die "Cannot open file $output2 $!";
	
	#---------------------------------------------------------------------------------------------------
	# NOW READING THE SEQUENCE FILE
	
	my $seed = 0;
	my $subset = $dir.$info."_".$chr."_".$seed."_".($seed+$increment);
	print OUT $subset,"\n";
	open(SUB,">$subset");
	
	while(my $sine = <SEQ>){
		$seed++;
		print SUB $sine;
		
		if ($seed%$increment == 0 ){
			close SUB;
			$subset = $dir.$info."_".$chr."_".$seed."_".($seed+$increment);
			open(SUB,">$subset");
			print SUB $sine;
			print OUT $subset,"\n";
	#		print $subset,"\n";
		}
	}
	close OUT;
	close SUB;
}
#xxxxxxxxxxxxxx chromosome_unrand_breaker xxxxxxxxxxxxxx  chromosome_unrand_breaker xxxxxxxxxxxxxx  chromosome_unrand_breaker xxxxxxxxxxxxxx 


#xxxxxxxxxxxxxx multiSpecies_interruptedMicrosatHunter xxxxxxxxxxxxxx  multiSpecies_interruptedMicrosatHunter xxxxxxxxxxxxxx  multiSpecies_interruptedMicrosatHunter xxxxxxxxxxxxxx 
sub multiSpecies_interruptedMicrosatHunter{
#	print "IN multiSpecies_interruptedMicrosatHunter: @_\n";
	my $input1 = $_[0];  ###### the *_sput_op4_ii file
	my $input2 = $_[1];  ###### looks like this: my $t8humanoutput = "*_nogap_op_unrand2_match"
	my $output1 = $_[2]; ###### interrupted microsatellite file, in new .interrupted format
	my $output2 = $_[3]; ###### uninterrupted microsatellite file
	my $org = $_[4];
	my $no_of_species = $_[5];
	
	my @thresholds = "0";
	push(@thresholds, split(/_/,$_[6]));
	
#	print "thresholds = @thresholds \n";
	$infocord = 2 + (4*$no_of_species) - 1;
	$typecord = 2 + (4*$no_of_species) + 1 - 1;
	$startcord = 2 + (4*$no_of_species) + 2 - 1;
	$strandcord = 2 + (4*$no_of_species) + 3 - 1;
	$endcord = 2 + (4*$no_of_species) + 4 - 1;
	$microsatcord = 2 + (4*$no_of_species) + 5 - 1;
	$motifcord = 2 + (4*$no_of_species) + 6 - 1;
	$sequencepos = 2 + (5*$no_of_species) + 1 -1 ; 
	
	$interr_poscord = $motifcord + 3;
	$no_of_interruptionscord = $motifcord + 4;
	$interrcord = $motifcord + 2;
	$interrtypecord = $motifcord + 1;
	
	
	$prinkter = 0;
#	print "prionkytet = $prinkter\n";
	
	open(IN,"<$input1") or die "Cannot open file $input1 $!";
	open(SEQ,"<$input2") or die "Cannot open file $input2 $!";
	
	open(INT,">$output1") or die "Cannot open file $output2 $!";
	open(UNINT,">$output2") or die "Cannot open file $output2 $!";
	
#	print "opened files !!\n";
	my $linecounter = 0;
	my $microcounter = 0;
	
	my %micros = ();
	while (my $line = <IN>){
	#	print "$org\t(chr[0-9a-zA-Z]+)\t([0-9]+)\t([0-9])+\t \n";
		$linecounter++;
		if ($line =~ /^>[A-Za-z0-9]+\s+([0-9]+)\s+([0-9a-zA-Z]+)\s+([0-9a-zA-Z_]+)\s([0-9]+)\s+([0-9]+)\s/ ) {
			my $key = join("\t",$1, $2, $3, $4, $5);
		#	print $key, "#-#-#-#-#-#-#-#\n" if $prinkter == 1;
			push (@{$micros{$key}},$line);	
			$microcounter++;
		}
		else {#print $line if $prinkter == 1;
		}
	}
#	print "number of microsatellites added to hash = $microcounter\nnumber of lines scanned = $linecounter\n";
	close IN;
	my @deletedlines = ();
#	print "done hash \n";
	$linecounter = 0;
	#---------------------------------------------------------------------------------------------------
	# NOW READING THE SEQUENCE FILE
	while(my $sine = <SEQ>){
		#print $linecounter,"\n" if $linecounter % 1000 == 0;
		my %microstart=();
		my %microend=();
		my @sields = split(/\t/,$sine);
		my $key = ();
		if ($sine =~ /^>[A-Za-z0-9]+\s+([0-9]+)\s+([0-9a-zA-Z]+)\s([0-9a-zA-Z_]+)\s([0-9]+)\s([0-9]+)\s/ ) {
			$key = join("\t",$1, $2, $3, $4, $5);
	#		print $key, "<-<-<-<-<-<-<-<\n";		
		}
	
	#	$prinkter = 1 if $sine =~ /^>H\t499\t/;
	
		if (exists $micros{$key}){
			my @microstring = @{$micros{$key}};
			delete $micros{$key};
			my @filteredmicrostring;
#			print "sequence = $sields[$sequencepos]" if $prinkter == 1;
			foreach my $line (@microstring){
				$linecounter++;
				my $copy_line = $line;
				my @fields = split(/\t/,$line);
				my $start = $fields[$startcord];
				my $end = $fields[$endcord];
				
#				print $line if $prinkter == 1;
				#LOOKING FOR LEFTWARD EXTENTION OF MICROSATELLITE 
				my $newline;
				while(1){
				#	print "\n before left sequence = $sields[$sequencepos]\n" if $prinkter == 1;
					if (multiSpecies_interruptedMicrosatHunter_left_extention_permission_giver($line) eq "no") {last;}
	
					$newline = multiSpecies_interruptedMicrosatHunter_left_extender($line, $sields[$sequencepos],$org);
					if ($newline eq $line){$line = $newline; last;}
					else {$line = $newline;}
					
					if (multiSpecies_interruptedMicrosatHunter_left_extention_permission_giver($line) eq "no") {last;}
#					print "returned line from left extender= $line \n" if $prinkter == 1;
				}
				while(1){
				#	print "sequence = $sields[$sequencepos]\n" if $prinkter == 1;
					if (multiSpecies_interruptedMicrosatHunter_right_extention_permission_giver($line) eq "no") {last;}
					
					$newline = multiSpecies_interruptedMicrosatHunter_right_extender($line, $sields[$sequencepos],$org);
					if ($newline eq $line){$line = $newline; last;}
					else {$line = $newline;}
					
					if (multiSpecies_interruptedMicrosatHunter_right_extention_permission_giver($line) eq "no") {last;}
#					print "returned line from right extender= $line \n" if $prinkter == 1;
				}
#				print "\n>>>>>>>>>>>>>>>>\n In the end, the line is: \n$line\n<<<<<<<<<<<<<<<<\n" if $prinkter == 1;
	
				my @tempfields = split(/\t/,$line);
				if ($tempfields[$microsatcord] =~ /\[/){
					print INT $line,"\n";
				}
				else{
					print UNINT $line,"\n";
				}
				
				if ($line =~ /NULL/){ next; }
				push(@filteredmicrostring, $line);
				push (@{$microstart{$start}},$line);
				push (@{$microend{$end}},$line);
			}
			
			my $firstflag = 'down';
	
		}	#if (exists $micros{$key}){
	}
	close INT;
	close UNINT;
#	print "final number of lines = $linecounter\n";
}

sub multiSpecies_interruptedMicrosatHunter_left_extender{
	my ($line, $seq, $org) = @_;	
#	print "left extender, like passed = $line\n" if $prinkter == 1;
#	print "in left extender... line passed = $line and sequence is $seq\n" if $prinkter == 1;
	chomp $line;
	my @fields = split(/\t/,$line);
	my $rstart = $fields[$startcord];
	my $microsat = $fields[$microsatcord];
	$microsat =~ s/\[|\]//g;
	my $rend = $rstart + length($microsat)-1;
	$microsat =~ s/-//g;
	my $motif = $fields[$motifcord];
	my $firstmotif = ();

	if ($motif =~ /^\[/){
		$motif =~ s/^\[//g;
		$motif =~ /([a-zA-Z]+)\].*/;
		$firstmotif = $1;
	}
	else {$firstmotif = $motif;}
	
#	print "hacked microsat = $microsat, motif = $motif, firstmotif = $firstmotif\n" if $prinkter == 1;
	my $leftphase = substr($microsat, 0,length($firstmotif));
	my $phaser = $leftphase.$leftphase;
	my @phase = split(/\s*/,$leftphase);
	my @phases;
	my @copy_phases = @phases;
	my $crawler=0;
	for (0 ... (length($leftphase)-1)){
		push(@phases, substr($phaser, $crawler, length($leftphase)));
		$crawler++;
	}

	my $start = $rstart;
	my $end = $rend;
	
	my $leftseq = substr($seq, 0, $start);
#	print "left phases are @phases , start = $start left sequence = ",substr($leftseq, -10),"\n" if $prinkter == 1;	
	my @extentions = ();
	my @trappeds = ();
	my @intervalposs = ();
	my @trappedposs = ();
	my @trappedphases = ();
	my @intervals = ();
	my $firstmotif_length = length($firstmotif);
	foreach my $phase (@phases){
#		print "left phase\t",substr($leftseq, -10),"\t$phase\n" if $prinkter == 1;
#		print "search patter = (($phase)+([a-zA-Z|-]{0,$firstmotif_length})) \n" if $prinkter == 1;
		if ($leftseq =~ /(($phase)+([a-zA-Z|-]{0,$firstmotif_length}))$/i){
#			print "in left pattern\n" if $prinkter == 1;
			my $trapped = $1;
			my $trappedpos = length($leftseq)-length($trapped);
			my $interval = $3;
			my $intervalpos = index($trapped, $interval) + 1;
#			print "left trapped = $trapped, interval = $interval, intervalpos = $intervalpos\n" if $prinkter == 1;

			my $extention = substr($trapped, 0, length($trapped)-length($interval));
			my $leftpeep = substr($seq, 0, ($start-length($trapped)));
			my @passed_overhangs;
			
			for my $i (1 ... length($phase)-1){
				my $overhang = substr($phase, -length($phase)+$i);
#				print "current overhang = $overhang, leftpeep = ",substr($leftpeep,-10)," whole sequence = ",substr($seq, ($end - ($end-$start) - 20), (($end-$start)+20)),"\n" if $prinkter == 1;
				#TEMPORARY... BETTER METHOD NEEDED
				$leftpeep =~ s/-//g;
				if ($leftpeep =~ /$overhang$/i){
					push(@passed_overhangs,$overhang);
#					print "l overhang\n" if $prinkter == 1;
				}
			}
			
			if(scalar(@passed_overhangs)>0){
				my $overhang = $passed_overhangs[longest_array_element(@passed_overhangs)];
				$extention = $overhang.$extention;
				$trapped = $overhang.$trapped;
#				print "trapped extended to $trapped \n" if $prinkter == 1;
				$trappedpos = length($leftseq)-length($trapped);
			}
			
			push(@extentions,$extention);
#			print "extentions = @extentions \n" if $prinkter == 1;

			push(@trappeds,$trapped );
			push(@intervalposs,length($extention)+1);
			push(@trappedposs, $trappedpos);
#			print "trappeds = @trappeds\n" if $prinkter == 1;
			push(@trappedphases, substr($extention,0,length($phase)));
			push(@intervals, $interval);
		}
	}
	if (scalar(@trappeds == 0)) {return $line;}
	
############################	my $nikaal = longest_array_element(@trappeds);
	my $nikaal = shortest_array_element(@intervals);
	
#	print "longest element found = $nikaal \n" if $prinkter == 1;
	
	if ($fields[$motifcord] !~ /\[/i) {$fields[$motifcord] = "[".$fields[$motifcord]."]";}
	$fields[$motifcord] = "[".$trappedphases[$nikaal]."]".$fields[$motifcord];
	#print "new fields 9 = $fields[9]\n" if $prinkter == 1;
	$fields[$startcord] = $fields[$startcord]-length($trappeds[$nikaal]);

	#print "new fields 9 = $fields[9]\n" if $prinkter == 1;

	if($fields[$microsatcord] !~ /^\[/i){
		$fields[$microsatcord] = "[".$fields[$microsatcord]."]";
	}
	
	$fields[$microsatcord] = "[".$extentions[$nikaal]."]".$intervals[$nikaal].$fields[$microsatcord];
	#print "new fields 14 = $fields[12]\n" if $prinkter == 1;
	
	#print "scalar of fields = ",scalar(@fields),"\n" if $prinkter == 1;

	
	if (scalar(@fields) > $motifcord+1){
		$fields[$motifcord+1] = "indel/deletion,".$fields[$motifcord+1];
	}
	else{$fields[$motifcord+1] = "indel/deletion";}
	#print "new fields 14 = $fields[14]\n" if $prinkter == 1;
	
	if (scalar(@fields)>$motifcord+2){		
		$fields[$motifcord+2] = $intervals[$nikaal].",".$fields[$motifcord+2];
	}
	else{$fields[$motifcord+2] =  $intervals[$nikaal];}	
	#print "new fields 15 = $fields[15]\n" if $prinkter == 1;

	my @seventeen=();
	
	if (scalar(@fields)>$motifcord+3){			
		@seventeen = split(/,/,$fields[$motifcord+3]);	
	#	print "scalarseventeen =@seventeen<-\n" if $prinkter == 1;
		for (0 ... scalar(@seventeen)-1) {$seventeen[$_] = $seventeen[$_]+length($trappeds[$nikaal]);}
		$fields[$motifcord+3] = ($intervalposs[$nikaal]).",".join(",",@seventeen);
		$fields[$motifcord+4] = $fields[$motifcord+4]+1;
	}
	
	else {$fields[$motifcord+3] = $intervalposs[$nikaal]; $fields[$motifcord+4]=1}
	
	#print "new fields 16 = $fields[16]\n" if $prinkter == 1;
	#print "new fields 17 = $fields[17]\n" if $prinkter == 1;
	
#	return join("\t",@fields);	
	my $returnline = join("\t",@fields);
	my $pastline  = $returnline;
	if ($fields[$microsatcord] =~ /\[/){
		$returnline = multiSpecies_interruptedMicrosatHunter_merge($returnline);
	}
#	print "finally left-extended line = ",$returnline,"\n" if $prinkter == 1;
	return $returnline;
}

sub multiSpecies_interruptedMicrosatHunter_right_extender{
#	print "right extender\n" if $prinkter == 1;
	my ($line, $seq, $org) = @_;	
#	print "in right extender... line passed = $line\n" if $prinkter == 1;
#	print "line = $line, sequence = ",$seq, "\n" if $prinkter == 1;
	chomp $line;
	my @fields = split(/\t/,$line);
	my $rstart = $fields[$startcord];
	my $microsat = $fields[$microsatcord];
	$microsat =~ s/\[|\]//g;
	my $rend = $rstart + length($microsat)-1;
	$microsat =~ s/-//g;
	my $motif = $fields[$motifcord];
	my $temp_lastmotif = ();

	if ($motif =~ /\]$/){
		$motif =~ s/\]$//g;
		$motif =~ /.*\[([a-zA-Z]+)/;
		$temp_lastmotif = $1;
	}
	else {$temp_lastmotif = $motif;}
	my $lastmotif = substr($microsat,-length($temp_lastmotif));
#	print "hacked microsat = $microsat, motif = $motif, lastmotif = $lastmotif\n" if $prinkter == 1;
	my $rightphase = substr($microsat, -length($lastmotif));
	my $phaser = $rightphase.$rightphase;
	my @phase = split(/\s*/,$rightphase);
	my @phases;
	my @copy_phases = @phases;
	my $crawler=0;
	for (0 ... (length($rightphase)-1)){
		push(@phases, substr($phaser, $crawler, length($rightphase)));
		$crawler++;
	}

	my $start = $rstart;
	my $end = $rend;
	
	my $rightseq = substr($seq, $end+1);
#	print "length of sequence  = " ,length($seq), "the coordinate to start from = ", $end+1, "\n" if $prinkter == 1;
#	print "right phases are @phases , end = $end right sequence = ",substr($rightseq,0,10),"\n" if $prinkter == 1;	
	my @extentions = ();
	my @trappeds = ();
	my @intervalposs = ();
	my @trappedposs = ();
	my @trappedphases = ();
	my @intervals = ();
	my $lastmotif_length = length($lastmotif);
	foreach my $phase (@phases){
#		print "right phase\t$phase\t",substr($rightseq,0,10),"\n" if $prinkter == 1;
#		print "search patter = (([a-zA-Z|-]{0,$lastmotif_length})($phase)+) \n" if $prinkter == 1;
		if ($rightseq =~ /^(([a-zA-Z|-]{0,$lastmotif_length}?)($phase)+)/i){
#			print "in right pattern\n" if $prinkter == 1;
			my $trapped = $1;
			my $trappedpos = $end+1;
			my $interval = $2;
			my $intervalpos = index($trapped, $interval) + 1;
#			print "trapped = $trapped, interval = $interval\n" if $prinkter == 1;

			my $extention = substr($trapped, length($interval));
			my $rightpeep = substr($seq, ($end+length($trapped))+1);
			my @passed_overhangs = "";
			
			#TEMPORARY... BETTER METHOD NEEDED
			$rightpeep =~ s/-//g;

			for my $i (1 ... length($phase)-1){
				my $overhang = substr($phase,0, $i);
#				print "current extention = $extention, overhang = $overhang, rightpeep = ",substr($rightpeep,0,10),"\n" if $prinkter == 1;
				if ($rightpeep =~ /^$overhang/i){
					push(@passed_overhangs, $overhang);
#					print "r overhang\n" if $prinkter == 1;
				}
			}
			if (scalar(@passed_overhangs) > 0){			
				my $overhang = @passed_overhangs[longest_array_element(@passed_overhangs)];
				$extention = $extention.$overhang;
				$trapped = $trapped.$overhang;
#				print "trapped extended to $trapped \n" if $prinkter == 1;
			}
		
			push(@extentions,$extention);
			#print "extentions = @extentions \n" if $prinkter == 1;

			push(@trappeds,$trapped );
			push(@intervalposs,$intervalpos);
			push(@trappedposs, $trappedpos);
#			print "trappeds = @trappeds\n" if $prinkter == 1;
			push(@trappedphases, substr($extention,0,length($phase)));
			push(@intervals, $interval);
		}
	}
	if (scalar(@trappeds == 0)) {return $line;}
	
###################################	my $nikaal = longest_array_element(@trappeds);
	my $nikaal = shortest_array_element(@intervals);
	
#	print "longest element found = $nikaal \n" if $prinkter == 1;
	
	if ($fields[$motifcord] !~ /\[/i) {$fields[$motifcord] = "[".$fields[$motifcord]."]";}
	$fields[$motifcord] = $fields[$motifcord]."[".$trappedphases[$nikaal]."]";
	$fields[$endcord] = $fields[$endcord] + length($trappeds[$nikaal]);


	if($fields[$microsatcord] !~ /^\[/i){
		$fields[$microsatcord] = "[".$fields[$microsatcord]."]";
	}
	
	$fields[$microsatcord] = $fields[$microsatcord].$intervals[$nikaal]."[".$extentions[$nikaal]."]";
	
	
	if (scalar(@fields) > $motifcord+1){
		$fields[$motifcord+1] = $fields[$motifcord+1].",indel/deletion";
	}
	else{$fields[$motifcord+1] = "indel/deletion";}
	
	if (scalar(@fields)>$motifcord+2){		
		$fields[$motifcord+2] = $fields[$motifcord+2].",".$intervals[$nikaal];
	}
	else{$fields[$motifcord+2] =  $intervals[$nikaal];}	

	my @seventeen=();
	if (scalar(@fields)>$motifcord+3){
		#print "at 608 we are doing this:length($microsat)+$intervalposs[$nikaal]\n" if $prinkter == 1;
		my $currpos = length($microsat)+$intervalposs[$nikaal];
		$fields[$motifcord+3] = $fields[$motifcord+3].",".$currpos;
		$fields[$motifcord+4] = $fields[$motifcord+4]+1;

	}
	
	else {$fields[$motifcord+3] = length($microsat)+$intervalposs[$nikaal]; $fields[$motifcord+4]=1}
	
#	print "finally right-extended line = ",join("\t",@fields),"\n" if $prinkter == 1;
#	return join("\t",@fields);

	my $returnline = join("\t",@fields);
	my $pastline  = $returnline;
	if ($fields[$microsatcord] =~ /\[/){
		$returnline = multiSpecies_interruptedMicrosatHunter_merge($returnline);
	}
#	print "finally right-extended line = ",$returnline,"\n" if $prinkter == 1;
	return $returnline;

}

sub multiSpecies_interruptedMicrosatHunter_left_extention_permission_giver{
	my @fields = split(/\t/,$_[0]);
	my $microsat = $fields[$microsatcord];
	$microsat =~ s/(^\[)|-//sg;
	my $motif = $fields[$motifcord];
	chomp $motif;
#	print $motif, "\n" if $motif !~ /^\[/;
	my $firstmotif = ();
	my $firststretch = ();
	my @stretches=();
	
#	print "motif = $motif, microsat = $microsat\n" if $prinkter == 1;
	if ($motif =~ /^\[/){
		$motif =~ s/^\[//sg;
		$motif =~ /([a-zA-Z]+)\].*/;
		$firstmotif = $1;
		@stretches = split(/\]/,$microsat);
		$firststretch = $stretches[0];
		#print "firststretch = $firststretch\n" if $prinkter == 1;
	}
	else {$firstmotif = $motif;$firststretch = $microsat;}
#	print "if length:firststretch - length($firststretch) < threshes length :firstmotif ($firstmotif) - $thresholds[length($firstmotif)]\n" if $prinkter == 1; 
	if (length($firststretch) < $thresholds[length($firstmotif)]){
		return "no";
	}
	else {return "yes";}

}
sub multiSpecies_interruptedMicrosatHunter_right_extention_permission_giver{
	my @fields = split(/\t/,$_[0]);
	my $microsat = $fields[$microsatcord];
	$microsat =~ s/-|(\]$)//sg;
	my $motif = $fields[$motifcord];
	chomp $motif;
	my $temp_lastmotif = ();
	my $laststretch = ();
	my @stretches=();


	if ($motif =~ /\]/){
		$motif =~ s/\]$//sg;
		$motif =~ /.*\[([a-zA-Z]+)$/;
		$temp_lastmotif = $1;
		@stretches = split(/\[/,$microsat);
		$laststretch = pop(@stretches);
		#print "last stretch = $laststretch\n" if $prinkter == 1;
	}
	else {$temp_lastmotif = $motif; $laststretch = $microsat;}

	if (length($laststretch) < $thresholds[length($temp_lastmotif)]){
		return "no";
	}
	else { return "yes";}


}
sub checking_substitutions{
	
	my ($line, $seq, $startprobes, $endprobes) = @_;
	#print "sequence = $seq \n" if $prinkter == 1;
	#print "COMMAND  = \n $line, \n $seq, \n $startprobes \n, $endprobes\n";
		#		<STDIN>;
	my @seqarray = split(/\s*/,$seq);
	my @startsubst_probes = split(/\|/,$startprobes); 
	my @endsubst_probes = split(/\|/,$endprobes);
	chomp $line;
	my @fields = split(/\t/,$line);
	my $start = $fields[11] - $fields[10];
	my $end = $fields[13] - $fields[10];
	my $motif = $fields[9]; #IN FUTURE, USE THIS AS A PROBE, LIKE MOTIF = $FIELDS[9].$FIELDS[9]
	$motif =~ s/\[|\]//g;
	my $microsat = $fields[14];
	$microsat =~ s/\[|\]//g;
	#------------------------------------------------------------------------
	# GETTING START AND END PHASES
	my $startphase = substr($microsat,0, length($motif));
	my $endphase = substr($microsat,-length($motif), length($motif));
	#print "start and end phases are  - $startphase and $endphase\n";
	my $startflag = 'down';
	my $endflag = 'down';
	my $substitution_distance = length($motif);
	my $prestart = $start - $substitution_distance;
	my $postend = $end + $substitution_distance;
	my @endadds = ();
	my @startadds = ();
		if (($prestart < 0) || ($postend > scalar(@seqarray))) {
			last;
		}
	#------------------------------------------------------------------------#------------------------------------------------------------------------
	# CHECKING FOR SUBSTITUTION PROBES NOW			
		
	if ($fields[8] ne "mononucleotide"){				
		while ($startflag eq "down"){		
			my $search = join("",@seqarray[$prestart...($start-1)]);
			#print "search is from $prestart...($start-1) = $search\n";
			foreach my $probe (@startsubst_probes){
				#print "\t\tprobe = $probe\n";				
				if ($search =~ /^$probe/){
					#print "\tfound addition to the left - $search \n";
					my $copyprobe = $probe;
					my $type;
					my $subspos = 0;
					my $interruption = "";
					if ($search eq $startphase) { $type = "NONE";}
					else{
						$copyprobe =~ s/\[a-zA-Z\]/^/g;
						$subspos = index($copyprobe,"^") + 1;
						$type = "substitution";
						$interruption  = substr($search, $subspos,1);
					}
					my $addinfo = join("\t",$prestart, $start, $search, $type, $interruption, $subspos);
					#print "adding information: $addinfo \n";
					push(@startadds, $addinfo);
					$prestart = $prestart - $substitution_distance;
					$start = $start-$substitution_distance;
					$startflag = 'down';
					
					last;
				}
				else{
					$startflag = 'up';
				}
			}
		}
		#<STDIN>;		
		while ($endflag eq "down"){									
			my $search = join("",@seqarray[($end+1)...$postend]);
			#print "search is from ($end+1)...$postend] = $search\n";

			foreach my $probe (@endsubst_probes){
				#print "\t\tprobe = $probe\n";
				if ($search =~ /$probe$/){
					my $copyprobe = $probe;
					my $type;
					my $subspos = 0;
					my $interruption = "";
					if ($search eq $endphase) { $type = "NONE";}
					else{
						$copyprobe =~ s/\[a-zA-Z\]/^/g;
						$subspos = index($copyprobe,"^") + 1;
						$type = "substitution";
						$interruption  = substr($search, $subspos,1);
					}
					my $addinfo = join("\t",$end, $postend, $search, $type, $interruption, $subspos);
					#print "adding information: $addinfo \n";
					push(@endadds, $addinfo);
					$postend = $postend + $substitution_distance;
					$end = $end+$substitution_distance;
					push(@endadds, $search);
					$endflag = 'down';
					last;
				}
				else{
					$endflag = 'up';
				}
			}
		}
		#print "startadds = @startadds, endadds  = @endadds \n";
	
	}
}
sub microsat_packer{
	my $microsat = $_[0];
	my $addition = $_[1];



}
sub multiSpecies_interruptedMicrosatHunter_merge{
		$prinkter = 0;
#	print "~~~~~~~~|||~~~~~~~~|||~~~~~~~~|||~~~~~~~~|||~~~~~~~~|||~~~~~~~~|||~~~~~~~~\n";
	my $line = $_[0];
#	print "sent for mering: $line \n" if $prinkter ==1;
	my @mields = split(/\t/,$line);
	my @fields = @mields;
	my $microsat = allCaps($fields[$microsatcord]);
	my $motifline = allCaps($fields[$motifcord]);
	my $microsatcopy = $microsat;
#	print "microsat = $microsat|\n" if $prinkter ==1;
	$microsatcopy =~ s/^\[|\]$//sg;
	chomp $microsatcopy;
	my @microields = split(/\][a-zA-Z|-]*\[/,$microsatcopy);
	my @inields = split(/\[[a-zA-Z|-]*\]/,$microsat);
	shift @inields;
#	print "inields =",join("|",@inields)," microields = ",join("|",@microields)," and count of microields = ", $#microields,"\n" if $prinkter ==1;
	$motifline =~ s/^\[|\]$//sg;
	my @motields = split(/\]\[/,$motifline);
	my @firstmotifs = ();
	my @lastmotifs = ();
	for my $i  (0 ... $#microields){
		$firstmotifs[$i] =  substr($microields[$i],0,length($motields[$i]));
		$lastmotifs[$i] = substr($microields[$i],-length($motields[$i]));
	}
#	print "firstmotif = @firstmotifs... lastmotif = @lastmotifs\n" if $prinkter ==1;
	my @mergelist = ();
	my @inter_poses = split(/,/,$fields[$interr_poscord]);
	my $no_of_interruptions = $fields[$no_of_interruptionscord];
	my @interruptions = split(/,/,$fields[$interrcord]);
	my @interrtypes = split(/,/,$fields[$interrtypecord]);
	my $stopper = 0;
	for my $i (0 ... $#motields-1){
#		print "studying connection of $motields[$i] and $motields[$i+1], i = $i in $microsat\n:$lastmotifs[$i] eq $firstmotifs[$i+1]?\n" if $prinkter ==1;
		if ((allCaps($lastmotifs[$i]) eq allCaps($firstmotifs[$i+1])) && (!exists $inields[$i] || $inields[$i] !~ /[a-zA-Z]/)){
			$stopper = 1;
			push(@mergelist, ($i)."_".($i+1)); #<STDIN> if $prinkter ==1;
		}
	}
	
#	print "mergelist = @mergelist\n" if $prinkter ==1;
	return $line if scalar(@mergelist) == 0;
#	print "merging @mergelist\n" if $prinkter ==1;
#	<STDIN> if $prinkter ==1;
	
	foreach my $merging (@mergelist){
		my @sets = split(/_/, $merging);
#		print "sets = @sets\n" if $prinkter ==1;
		my @tempmicro = ();
		my @tempmot = ();
#		print "for loop going from 0 ... ", $sets[0]-1, "\n" if $prinkter ==1;
		for my $i (0 ... $sets[0]-1){
#			print " adding pre- i = $i adding: microields= $microields[$i]. motields = $motields[$i], inields = |$inields[$i]|\n" if $prinkter ==1;
			push(@tempmicro, "[".$microields[$i]."]");
			push(@tempmicro, $inields[$i]);
			push(@tempmot, "[".$motields[$i]."]");
#			print "adding pre-motifs number $i\n" if $prinkter ==1;
#			print "tempmot = @tempmot, tempmicro = @tempmicro \n" if $prinkter ==1;
		}
#		print "tempmot = @tempmot, tempmicro = @tempmicro \n" if $prinkter ==1;
#		print "now pushing ", "[",$microields[$sets[0]]," and ",$microields[$sets[1]],"]\n" if $prinkter ==1;
		my $pusher = "[".$microields[$sets[0]].$microields[$sets[1]]."]";
#		print "middle is, from @motields -   @sets, number 0 which is  is\n";
#		print ": $motields[$sets[0]]\n";
		push (@tempmicro, $pusher);
		push(@tempmot, "[".$motields[$sets[0]]."]");
		push (@tempmicro, $inields[$sets[1]]) if $sets[1] != $#microields && exists $sets[1] && exists $inields[$sets[1]];
		my $outcoming = -2;
#		print "tempmot = @tempmot, tempmicro = @tempmicro \n" if $prinkter ==1;
#		print "for loop going from ",$sets[1]+1, " ... ", $#microields, "\n" if $prinkter ==1;
		for my $i ($sets[1]+1 ... $#microields){
#			print " adding post- i = $i adding: microields= $microields[$i]. motields = $motields[$i]\n" if $prinkter ==1;
			push(@tempmicro, "[".$microields[$i]."]") if exists $microields[$i];
			push(@tempmicro, $inields[$i]) unless $i == $#microields || !exists $inields[$i];
			push(@tempmot, "[".$motields[$i]."]");
#			print "adding post-motifs number $i\n" if $prinkter ==1;
			$outcoming  = $i;
		}
#		print "____________________________________________________________________________\n";
		$prinkter = 0;
		$fields[$microsatcord] = join("",@tempmicro);
		$fields[$motifcord] = join("",@tempmot);
#		print "tempmot = @tempmot, tempmicro = @tempmicro . microsat = $fields[$microsatcord] and motif = $fields[$motifcord] \n" if $prinkter ==1;
		
		splice(@interrtypes, $sets[0], 1);
		$fields[$interrtypecord] = join(",",@interrtypes);
		splice(@interruptions, $sets[0], 1);
		$fields[$interrcord] = join(",",@interruptions);
		splice(@inter_poses, $sets[0], 1);
		$fields[$interr_poscord] = join(",",@inter_poses);
		$no_of_interruptions = $no_of_interruptions - 1;
	}	

	if ($no_of_interruptions == 0 && $line !~ /compound/){
		$fields[$microsatcord] =~ s/^\[|\]$//sg;
		$fields[$motifcord] =~ s/^\[|\]$//sg;
		$line = join("\t", @fields[0 ... $motifcord]);		
	}
	else{
		$line = join("\t", @fields);
	}
#	print "post merging, the line is $line\n" if $prinkter ==1;
	#<STDIN> if $stopper ==1;
	return $line;
}
sub interval_asseser{
	my $pre_phase = $_[0]; my $post_phase = $_[1]; my $inter = $_[3];
}
#---------------------------------------------------------------------------------------------------
sub allCaps{
	my $motif = $_[0];
	$motif =~ s/a/A/g;
	$motif =~ s/c/C/g;
	$motif =~ s/t/T/g;
	$motif =~ s/g/G/g;
	return $motif;
}


#xxxxxxxxxxxxxx multiSpecies_interruptedMicrosatHunter xxxxxxxxxxxxxx  chromosome_unrand_breamultiSpecies_interruptedMicrosatHunterker xxxxxxxxxxxxxx  multiSpecies_interruptedMicrosatHunter xxxxxxxxxxxxxx 


#xxxxxxxxxxxxxx merge_interruptedMicrosats xxxxxxxxxxxxxx  merge_interruptedMicrosats xxxxxxxxxxxxxx  merge_interruptedMicrosats xxxxxxxxxxxxxx 
sub merge_interruptedMicrosats{
#	print "IN merge_interruptedMicrosats: @_\n";
	my $input0 = $_[0];  ######looks like this: my $t8humanoutput = $pipedir.$ptag."_nogap_op_unrand2"
	my $input1 = $_[1];  ###### the *_sput_op4_ii file
	my $input2 = $_[2];  ###### the *_sput_op4_ii file
	$no_of_species = $_[3];
	
	my $output1 = $_[1]."_separate";    #$_[3]; ###### plain microsatellite file forward
	my $output2 = $_[2]."_separate";    ##$_[4]; ###### plain microsatellite file reverse
	my $output3 = $_[1]."_merged";    ##$_[5]; ###### plain microsatellite file forward
	#my $output4 = $_[2]."_merged";    ##$_[6]; ###### plain microsatellite file reverse
	#my $info = $_[4];
	#my @tags = split(/\t/,$info);
	
	open(SEQ,"<$input0") or die "Cannot open file $input0 $!";
	open(INF,"<$input1") or die "Cannot open file $input1 $!";
	open(INR,"<$input2") or die "Cannot open file $input2 $!";
	open(OUTF,">$output1") or die "Cannot open file $output1 $!";
	open(OUTR,">$output2") or die "Cannot open file $output2 $!";
	open(MER,">$output3") or die "Cannot open file $output3 $!";
	#open(MERR,">$output4") or die "Cannot open file $output4 $!";
		
	
		
	 $printer = 0;
	
#	print "files opened \n";
	$infocord = 2 + (4*$no_of_species) - 1;
	$startcord = 2 + (4*$no_of_species) + 2 - 1;
	$strandcord = 2 + (4*$no_of_species) + 3 - 1;
	$endcord = 2 + (4*$no_of_species) + 4 - 1;
	$microsatcord = 2 + (4*$no_of_species) + 5 - 1;
	$motifcord = 2 + (4*$no_of_species) + 6 - 1;
	$typecord = $infocord + 1;
	my $sequencepos = 2 + (5*$no_of_species) + 1 -1 ; 
	
	$interrtypecord = $motifcord + 1;
	$interrcord = $motifcord + 2;
	$interr_poscord = $motifcord + 3;
	$no_of_interruptionscord = $motifcord + 4;
	$mergestarts  = $no_of_interruptionscord+ 1;
	$mergeends = $no_of_interruptionscord+ 2;
	$mergemicros = $no_of_interruptionscord+ 3;
	
	# NOW ADDING FORWARD MICROSATELLITES TO HASH
	my %fmicros = ();
	my $microcounter=0;
	my $linecounter = 0;
	while (my $line = <INF>){
	#	print "$org\t(chr[0-9a-zA-Z]+)\t([0-9]+)\t([0-9])+\t \n";
		$linecounter++;
		if ($line =~ /^>[A-Za-z0-9]+\s+([0-9]+)\s+([0-9a-zA-Z]+)\s([0-9a-zA-Z_]+)\s([0-9]+)\s([0-9]+)\s/ ) {
			my $key = join("\t",$1, $2, $4, $5);
		#	print $key, "#-#-#-#-#-#-#-#\n";
			push (@{$fmicros{$key}},$line);	
			$microcounter++;
		}
		else {
			#print $line;
		}
	}
#	print "number of microsatellites added to hash = $microcounter\nnumber of lines scanned = $linecounter\n";
	close INF;
	my @deletedlines = ();
#	print "done forward hash \n";
	$linecounter = 0;
	#---------------------------------------------------------------------------------------------------
	# NOW ADDING REVERSE MICROSATELLITES TO HASH
	my %rmicros = ();
	$microcounter=0;
	while (my $line = <INR>){
	#	print "$org\t(chr[0-9a-zA-Z]+)\t([0-9]+)\t([0-9])+\t \n";
		$linecounter++;
		if ($line =~ /^>[A-Za-z0-9]+\s+([0-9]+)\s+([0-9a-zA-Z]+)\s([0-9a-zA-Z_]+)\s([0-9]+)\s([0-9]+)\s/ ) {
			my $key = join("\t",$1, $2, $4, $5);
	#		print $key, "#-#-#-#-#-#-#-#\n";
			push (@{$rmicros{$key}},$line);	
			$microcounter++;
		}
		else {
			#print "cant make key\n";
		}
	}
#	print "number of reverse microsatellites added to hash = $microcounter\nnumber of lines scanned = $linecounter\n";
	close INR;
#	print "done reverse hash \n";
	$linecounter = 0;
	
	#------------------------------------------------------------------------------------------------
	
	while(my $sine = <SEQ>){
		#<STDIN> if $sine =~ /16349128/;
		next if $sine !~ /[a-zA-Z0-9]/;
#		print "-" x 150, "\n"  if $printer == 1;
		my @sields = split(/\t/,$sine);
		my @merged = ();
	
		my $key = ();
	
		if ($sine =~ /^>[A-Za-z0-9]+\s+([0-9]+)\s+([0-9a-zA-Z]+)\s([0-9a-zA-Z_]+)\s([0-9]+)\s([0-9]+)\s/ ) {
			$key = join("\t",$1, $2, $4, $5);
		#	print $key, "<-<-<-<-<-<-<-<\n";		
		}
	#	print "key = $key\n";
		
		my @sets1;
		my @sets2;
		chomp $sields[$sequencepos];
		my $rev_sequence = reverse($sields[$sequencepos]); 
		$rev_sequence =~ s/ //g;
		$rev_sequence = " ".$rev_sequence;
		next if (!exists $fmicros{$key} && !exists $rmicros{$key});
		
		if (exists $fmicros{$key}){
		#	print "line no : $linecount\n";
			my @raw_microstring = @{$fmicros{$key}};
			my %starts = (); my %ends = ();
#			print colored ['yellow'],"unsorted, unfiltered microats = \n" if $printer == 1; foreach (@raw_microstring) {print colored ['blue'],$_,"\n" if $printer == 1;}
			my @microstring=();
			for my $u (0 ... $#raw_microstring){
				my @tields = split(/\t/,$raw_microstring[$u]);
				next if exists $starts{$tields[$startcord]} && exists $ends{$tields[$endcord]};
				push(@microstring, $raw_microstring[$u]);
				$starts{$tields[$startcord]} = $tields[$startcord];
				$ends{$tields[$endcord]} = $tields[$endcord];
			}
			
	#		print "founf microstring in forward\n: @microstring\n"; 
			chomp @microstring;
			my $clusterresult = (find_clusters(@microstring, $sields[$sequencepos])); 	
			@sets1 = split("\=", $clusterresult);
			my @temp = split(/_X0X_/,$sets1[0]) ; $microscanned+= scalar(@temp);
		#	print "sets = ", join("<all\nmerged>", @sets1), "\n<<-sets1\n"; <STDIN>;
		}	#if (exists $micros{$key}){
	
		if (exists $rmicros{$key}){
		#	print "line no : $linecount\n";
			my @raw_microstring = @{$rmicros{$key}};
			my %starts = (); my %ends = ();
#			print colored ['yellow'],"unsorted, unfiltered microats = \n" if $printer == 1; foreach (@raw_microstring) {print colored ['blue'],$_,"\n" if $printer == 1;}
			my @microstring=();
			for my $u (0 ... $#raw_microstring){
				my @tields = split(/\t/,$raw_microstring[$u]);
				next if exists $starts{$tields[$startcord]} && exists $ends{$tields[$endcord]};
				push(@microstring, $raw_microstring[$u]);
				$starts{$tields[$startcord]} = $tields[$startcord];
				$ends{$tields[$endcord]} = $tields[$endcord];
			}
	#		print "founf microstring in reverse\n: @microstring\n"; <STDIN>;
			chomp @microstring;
	#		print "sending reversed sequence\n";
			my $clusterresult = (find_clusters(@microstring, $rev_sequence ) ); 	
			@sets2 = split("\=", $clusterresult);
			my @temp = split(/_X0X_/,$sets2[0]) ; $microscanned+= scalar(@temp);
		}	#if (exists $micros{$key}){
	
		my @popout1 = ();
		my @popout2 = ();
		my @forwardset = ();
		if (exists $sets2[1] ){
			if(exists $sets1[0]) {
				push (@popout1, $sets1[0],$sets2[1]);
				my @forwardset = split("=", popOuter(@popout1, $rev_sequence ));#		
				print OUTF join("\n",split("_X0X_", $forwardset[0])), "\n";
				my @localmerged = split("_X0X_", $forwardset[1]);
				my $sequence = $sields[$sequencepos];
				$sequence =~ s/ //g;
#				print "\nforwardset = @forwardset\n";
				for my $j (0 ... $#localmerged){
					$localmerged[$j] = 	invert_justCoordinates ($localmerged[$j], length($sequence));
				}
				
				push (@merged, @localmerged);
				
			}
			else{
				my @localmerged = split("_X0X_", $sets2[1]);
				my $sequence = $sields[$sequencepos];
				$sequence =~ s/ //g;
				for my $j (0 ... $#localmerged){
#					print "\nlocalmerged = @localmerged\n";
					$localmerged[$j] = 	invert_justCoordinates ($localmerged[$j], length($sequence));
				}
				
				push (@merged, @localmerged);
			}
		}
		elsif (exists $sets1[0]){
			print OUTF join("\n",split("_X0X_", $sets1[0])), "\n";
		}
		
		my @reverseset= ();
		if (exists $sets1[1]){
			if (exists $sets2[0]){
				push (@popout2, $sets2[0],$sets1[1]);
			#	print "popout2 = @popout2\n";
				my @reverseset = split("=", popOuter(@popout2, $sields[$sequencepos]));
				#print "reverseset = $reverseset[1] < --- reverseset1\n"; 
				print OUTR join("\n",split("_X0X_", $reverseset[0])), "\n";
				push(@merged,  (split("_X0X_", $reverseset[1])));
			}
			else{
				push(@merged,  (split("_X0X_", $sets1[1])));
			}
		}
		elsif (exists $sets2[0]){
			print OUTR join("\n",split("_X0X_", $sets2[0])), "\n";
		
		}
		
		if (scalar @merged > 0){
			my @filtered_merged = split("__",(filterDuplicates_merged(@merged)));
			print MER join("\n", @filtered_merged),"\n"; 
		}	
	#		<STDIN> if $sine =~ /16349128/;
	
	}
	close(SEQ);
	close(INF);
	close(INR);
	close(OUTF);
	close(OUTR);
	close(MER);

}
sub find_clusters{
	my @input = @_;
	my $sequence = pop(@input);
	$sequence =~ s/ //g;
	my @microstring0 = @input;
#	print "IN: find_clusters:\n";
	my %microstart=();
	my %microend=();
	my @nonmerged = ();
	my @mergedSet = ();
#		print "set of microsats = @microstring \n";
	my @microstring = map { $_->[0] } sort custom map { [$_, split /\t/ ] } @microstring0; 
#	print "microstring = ", join("\n",@microstring0) ," \n---->\n", join("\n", @microstring),"\n ,,+." if $printer == 1; 
	#<STDIN> if $printer == 1; 
	my @tempmicrostring = @microstring;
	foreach my $line (@tempmicrostring){
		my @fields = split(/\t/,$line);
		my $start = $fields[$startcord];
		my $end = $fields[$endcord];
		next if $start !~ /[0-9]+/ || $end !~ /[0-9]+/;
	#		print " starts >>> start: $start = $fields[11] - $fields[10] || $end = $fields[13] - $fields[10]\n";
		push (@{$microstart{$start}},$line);
		push (@{$microend{$end}},$line);	
	}
	my $firstflag = 'down';
	while( my $line =shift(@microstring)){
#		print "-----------\nline = $line \n" if $printer == 1;
		chomp $line;
		my @fields = split(/\t/,$line);
		my $start = $fields[$startcord];
		my $end = $fields[$endcord];
		next if $start !~ /[0-9]+/ || $end !~ /[0-9]+/ || $distance !~ /[0-9]+/ ;
		my $startmicro = $line;
		my $endmicro = $line;
#		print "start: $start = $fields[11] - $fields[10] || $end = $fields[13] - $fields[10]\n";

		delete ($microstart{$start});
		delete ($microend{$end});
		my $flag = 'down';	
		my $startflag = 'down';
		my $endflag = 'down';
		my $prestart = $start - $distance;
		my $postend = $end + $distance;
		my @compoundlines = ();
		my %compoundhash = ();
		push (@compoundlines, $line);
		push (@{$compoundhash{$line}},$line);
		my $startrank = 1;
		my $endrank = 1;

		while( ($startflag eq "down") || ($endflag eq "down") ){
#			print "prestart=$prestart, post end =$postend.. seqlen =", length($sequence)," firstflag = $firstflag \n" if $printer == 1;
			if ( (($prestart < 0) && $firstflag eq "up") || (($postend > length($sequence) && $firstflag eq "up")) ){
#				print "coming to the end of sequence,post end = $postend and sequence length =", length($sequence)," so exiting\n" if $printer == 1;
				last;
			}
			
			$firstflag = "up";
			if ($startflag eq "down"){		
				for my $i ($prestart ... $end){
					if(exists $microend{$i}){	
						chomp $microend{$i}[0];
						if(exists $compoundhash{$microend{$i}[0]}) {next;}
							chomp $microend{$i}[0];
							push(@compoundlines, $microend{$i}[0]);
							my @tields = split(/\t/,$microend{$i}[0]);
							$startmicro = $microend{$i}[0];
							chomp $startmicro;
							$flag = 'down';
							$startrank++;
#							print "deleting $microend{$i}[0] and $microstart{$tields[$startcord]}[0]\n" if $printer == 1;
							delete $microend{$i};
							delete $microstart{$tields[$startcord]};
							$end = $tields[$endcord];
							$startflag = 'down';
							$prestart = $tields[$startcord] - $distance;
							last;
					}
					else{
						$flag = 'up';
						$startflag = 'up';
					}
				}
			}
	
			if ($endflag eq "down"){	

				for my $i ($start ... $postend){
#					print "$start ----> $i -----> $postend\n" if $printer == 1;
					if(exists $microstart{$i} ){
						chomp $microstart{$i}[0];
						if(exists $compoundhash{$microstart{$i}[0]}) {next;}	
							chomp $microstart{$i}[0];
							push(@compoundlines, $microstart{$i}[0]);
							my @tields = split(/\t/,$microstart{$i}[0]);
							$endmicro = $microstart{$i}[0];
							$endrank++;
							chomp $endmicro;
							$flag = 'down';
#							print "deleting $microend{$tields[$endcord]}[0]\n" if $printer == 1;
							
							delete $microstart{$i} if exists $microstart{$i} ;
							delete $microend{$tields[$endcord]} if exists $microend{$tields[$endcord]};
#							print "done\n" if $printer == 1;
							
							shift @microstring;
							$end = $tields[$endcord];
							$postend = $tields[$endcord] + $distance;
							$endflag = 'down';
							last;								
					}
					else{
						$flag = 'up';
						$endflag = 'up';
					}
#					print "out of the if\n" if $printer == 1;
				}
#				print "out of the for\n" if $printer == 1;

			}
#			print "for next turn, flag status: startflag = $startflag and endflag = $endflag \n";
		} 														#end while( $flag eq "down")
#			print "compoundlines = @compoundlines \n" if $printer == 1;

		if (scalar (@compoundlines) == 1){
			push(@nonmerged, $line);		

		}
		if (scalar (@compoundlines) > 1){
#			print "FROM CLUSTERER\n"  if $printer == 1;
			push(@mergedSet,merge_microsats(@compoundlines, $sequence) );
		}
	} #end foreach my $line (@microstring){
#	print join("\n",@mergedSet),"<-----mergedSet\n"  if $printer == 1;
#<STDIN> if scalar(@mergedSet) > 0;
#	print "EXIT: find_clusters\n";
return (join("_X0X_",@nonmerged). "=".join("_X0X_",@mergedSet));
}

sub custom {
	$a->[$startcord+1] <=> $b->[$startcord+1];
}

sub popOuter {
#	print "\nIN: popOuter @_\n"; <STDIN>;
	my @all = split ("_X0X_",$_[0]);
#	<STDIN> if !defined $_[0];
	my @merged = split ("_X0X_",$_[1]);
	my $sequence = $_[2];
	my $seqlen = length($sequence);
	my %microstart=();
	my %microend=();
	my @mergedSet = ();
	my @nonmerged = ();
	
	foreach my $line (@all){
		my @fields = split(/\t/,$line);
		my $start = $seqlen - $fields[$startcord]+ 1;
		my $end = $seqlen - $fields[$endcord] + 1;
		push (@{$microstart{$start}},$line);
		push (@{$microend{$end}},$line);	
	}
	my $firstflag = 'down';
	my %forPopouting = ();

	while( my $line =shift(@merged)){
	#	print "\n MErgedline: $line .. startcord = $startcord  ... endcord = $endcord\n" ;
		chomp $line;
		my @fields = split(/\t/,$line);
		my $start = $fields[$startcord];
		my $end = $fields[$endcord];
		my $startmicro = $line;
		my $endmicro = $line;
		
		
		delete ($microstart{$start});
		delete ($microend{$end});
		my $flag = 'down';	
		my $startflag = 'down';
		my $endflag = 'down';
		my $prestart = $start - $distance;
		my $postend = $end + $distance;
		my @compoundlines = ();
		my %compoundhash = ();
		push (@compoundlines, $line);
		my $startrank = 1;
		my $endrank = 1;
		
	#	print "\nstart = $start, end = $end\n";
	#	<STDIN>;
		for my $i ($start ... $end){
			if(exists $microend{$i}){	
		#		print "\nmicrosat exists: $microend{$i}[0] microsat exists\n"; 
				chomp $microend{$i}[0];
				my @fields = split(/\t/,$microend{$i}[0]);
				delete $microstart{$seqlen - $fields[$startcord] + 1};
				my $invertseq = $sequence;
				$invertseq =~ s/ //g;
				push(@compoundlines, invert_microsat($microend{$i}[0] , $invertseq ));
				delete $microend{$i};
				
			}

			if(exists $microstart{$i} ){
		#		print "\nmicrosat exists: $microstart{$i}[0] microsat exists\n"; 

				chomp $microstart{$i}[0];
				my @fields = split(/\t/,$microstart{$i}[0]);
				delete $microend{$seqlen - $fields[$endcord] + 1};
				my $invertseq = $sequence;
				$invertseq =~ s/ //g;
				push(@compoundlines, invert_microsat($microstart{$i}[0], $invertseq) );						
				delete $microstart{$i};
			}
		}			
	
		if (scalar (@compoundlines) == 1){
			push(@mergedSet,join("\t",@compoundlines) );
		}
		else {
#			print "FROM POPOUTER\n" if $printer == 1;
			push(@mergedSet, merge_microsats(@compoundlines, $sequence) );
		}
	} 
	
	foreach my $key (sort keys %microstart) {
    	push(@nonmerged,$microstart{$key}[0]);
	}
	
	return (join("_X0X_",@nonmerged). "=".join("_X0X_",@mergedSet) );
}



sub invert_justCoordinates{
	my $microsat = $_[0];
#	print "IN invert_justCoordinates ... @_\n" ; <STDIN>;
	chomp $microsat;
	my $seqLength = $_[1];
	my @fields = split(/\t/,$microsat);
	my $start = $seqLength - $fields[$endcord] + 1;
	my $end = $seqLength - $fields[$startcord] + 1;
	$fields[$startcord] = $start;
	$fields[$endcord] = $end;
	$fields[$microsatcord] = reverse_micro($fields[$microsatcord]);
#	print "RETURNIG: ", join("\t",@fields), "\n" if $printer == 1;
	return join("\t",@fields); 	
}

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


sub filterDuplicates_merged{
	my @merged = @_;
	my %revmerged = ();
	my @fmerged = ();
	foreach my $micro (@merged) {
		my @fields = split(/\t/,$micro);
		if ($fields[3] =~ /chr[A-Z0-9a-z]+r/){
			my $key = join("_K0K_",$fields[1], $fields[$startcord], $fields[$endcord]);
	#		print "adding  ... \n$key\n$micro\n";
			push(@{$revmerged{$key}}, $micro);
		}
		else{
		#	print "pushing.. $micro\n";
			push(@fmerged, $micro);
		}
	}
#	print "\n";
	foreach my $micro (@fmerged) {
			my @fields = split(/\t/,$micro);
			my $key = join("_K0K_",$fields[1], $fields[$startcord], $fields[$endcord]);
	#		print "searching for key $key\n";
			if (exists $revmerged{$key}){
		#		print "deleting $revmerged{$key}[0]\n";
				delete $revmerged{$key};
			}
	}
	foreach my $key (sort keys %revmerged) {
    	push(@fmerged,$revmerged{$key}[0]);
	}
#	print "returning ", join("\n", @fmerged),"\n" ;
	return join("__", @fmerged);
}

sub invert_microsat{
	my $micro = $_[0];
	chomp $micro;
	if ($micro =~ /chr[A-Z0-9a-z]+r/) { $micro =~  s/chr([0-9a-b]+)r/chr$1/g ;}
	else {  $micro =~  s/chr([0-9a-b]+)/chr$1r/g ; }
	my $sequence = $_[1];
	$sequence =~ s/ //g;
	my $seqlen = length($sequence);
	my @fields = split(/\t/,$micro);
	my $start = $seqlen - $fields[$endcord] +1;
	my $end = $seqlen - $fields[$startcord] +1;
	$fields[$startcord]  = $start;
	$fields[$endcord] = $end;
	$fields[$motifcord] = reverse_micro($fields[$motifcord]);
	$fields[$microsatcord] = reverse_micro($fields[$microsatcord]);
	if ($fields[$typecord] ne "compound" && exists $fields[$no_of_interruptionscord] ){
		my @intertypes = split(/,/,$fields[$interrtypecord]);
		my @inters = split(/,/,$fields[$interrcord]);
		my @interposes = split(/,/,$fields[$interr_poscord]);
		$fields[$interrtypecord] = join(",",reverse(@intertypes));
		$fields[$no_of_interruptionscord] = scalar(@interposes);
		for my $i (0 ... $fields[$no_of_interruptionscord]-1){
			if (exists $inters[$i] && $inters[$i] =~ /[a-zA-Z]/){
				$inters[$i] = reverse($inters[$i]);
				$interposes[$i] = $interposes[$i] + length($inters[$i]) - 1;
			}	
			else{
				$inters[$i] = "";
				$interposes[$i] = $interposes[$i] - 1;
			}
			$interposes[$i] = ($end - $start + 1) - $interposes[$i] + 1;
		}
		
		$fields[$interrcord] = join(",",reverse(@inters));
		$fields[$interr_poscord] = join(",",reverse(@interposes));
	}
	
	my $finalmicrosat = join("\t", @fields);
	return $finalmicrosat;			

}
sub reverse_micro{
	my $micro = reverse($_[0]);
	my @strand = split(/\s*/,$micro);
	for my $i (0 ... $#strand){
		if ($strand[$i] =~ /\[/i) {$strand[$i] = "]";next;}
		if ($strand[$i] =~ /\]/i) {$strand[$i] = "[";next;}
	}
	return join("",@strand);
}

#xxxxxxxxxxxxxx merge_interruptedMicrosats xxxxxxxxxxxxxx  merge_interruptedMicrosats xxxxxxxxxxxxxx  merge_interruptedMicrosats xxxxxxxxxxxxxx 


#xxxxxxxxxxxxxx forward_reverse_sputoutput_comparer xxxxxxxxxxxxxx  forward_reverse_sputoutput_comparer xxxxxxxxxxxxxx  forward_reverse_sputoutput_comparer xxxxxxxxxxxxxx 

sub forward_reverse_sputoutput_comparer	{
#	print "IN forward_reverse_sputoutput_comparer: @_\n";
	my $input0 = $_[0];  ###### the *nogap_unrand_match file
	my $input1 = $_[1];  ###### the real file, *sput* data
	my $input2 = $_[2];  ###### the reverse file, *sput* data
	my $output1 = $_[3]; ###### microsats different in real file
	my $output2 = $_[4]; ###### microsats missing in real file
	my $output3 = $_[5]; ###### microsats common among real and reverse file
	my $no_of_species = $_[6];
	
	$infocord = 2 + (4*$no_of_species) - 1;
	$typecord = 2 + (4*$no_of_species) + 1 - 1;
	$startcord = 2 + (4*$no_of_species) + 2 - 1;
	$strandcord = 2 + (4*$no_of_species) + 3 - 1;
	$endcord = 2 + (4*$no_of_species) + 4 - 1;
	$microsatcord = 2 + (4*$no_of_species) + 5 - 1;
	$motifcord = 2 + (4*$no_of_species) + 6 - 1;
	$sequencepos = 2 + (5*$no_of_species) + 1 -1 ; 
	$interrtypecord = $motifcord + 1;
	$interrcord = $motifcord + 2;
	$interr_poscord = $motifcord + 3;
	$no_of_interruptionscord = $motifcord + 4;
	$mergestarts  = $no_of_interruptionscord+ 1;
	$mergeends = $no_of_interruptionscord+ 2;
	$mergemicros = $no_of_interruptionscord+ 3;
	
	
	open(SEQ,"<$input0") or die "Cannot open file $input0 $!";
	open(INF,"<$input1") or die "Cannot open file $input1 $!";
	open(INR,"<$input2") or die "Cannot open file $input2 $!";
	
	open(DIFF,">$output1") or die "Cannot open file $output1 $!";
	#open(MISS,">$output2") or die "Cannot open file $output2 $!";
	open(SAME,">$output3") or die "Cannot open file $output3 $!";
		
		
#	print "opened files \n";
	my $linecounter = 0;
	my $fcounter = 0;
	my $rcounter = 0;
	
	$printer = 0;
	#---------------------------------------------------------------------------------------------------
	# NOW ADDING FORWARD MICROSATELLITES TO HASH
	my %fmicros = ();
	my $microcounter=0;
	while (my $line = <INF>){
		$linecounter++;
		if ($line =~ /([0-9a-zA-Z]+)\s([0-9a-zA-Z_]+)\s([0-9]+)\s([0-9]+)\s([0-9a-zA-Z]+)\s([0-9a-zA-Z_]+)\s([0-9]+)\s([0-9]+)\s([0-9a-zA-Z]+)\s([0-9a-zA-Z_]+)\s([0-9]+)\s([0-9]+)\s/ ) {
			my $key = join("\t",$1, $3, $4, $5, $7, $8, $9, $11, $12);
		#	print $key, "#-#-#-#-#-#-#-#\n";
			push (@{$fmicros{$key}},$line);	
			$microcounter++;
		}
		else {
		#print $line;
		}
	}
#	print "number of microsatellites added to hash = $microcounter\nnumber of lines scanned = $linecounter\n";
	close INF;
	my @deletedlines = ();
#	print "done forward hash \n";
	$linecounter = 0;
	#---------------------------------------------------------------------------------------------------
	# NOW ADDING REVERSE MICROSATELLITES TO HASH
	my %rmicros = ();
	$microcounter=0;
	while (my $line = <INR>){
		$linecounter++;
		if ($line =~ /([0-9a-zA-Z]+)\s([0-9a-zA-Z_]+)\s([0-9]+)\s([0-9]+)\s([0-9a-zA-Z]+)\s([0-9a-zA-Z_]+)\s([0-9]+)\s([0-9]+)\s([0-9a-zA-Z]+)\s([0-9a-zA-Z_]+)\s([0-9]+)\s([0-9]+)\s/ ) {
			my $key = join("\t",$1, $3, $4, $5, $7, $8, $9, $11, $12);
		#	print $key, "#-#-#-#-#-#-#-#\n";
			push (@{$rmicros{$key}},$line);	
			$microcounter++;
		}
		else {}
	}
#	print "number of microsatellites added to hash = $microcounter\nnumber of lines scanned = $linecounter\n";
	close INR;
#	print "done reverse hash \n";
	$linecounter = 0;
	#---------------------------------------------------------------------------------------------------
	#---------------------------------------------------------------------------------------------------
	# NOW READING THE SEQUENCE FILE
	while(my $sine = <SEQ>){
		my %microstart=();
		my %microend=();
		my @sields = split(/\t/,$sine);
		my $key = ();
		if ($sine =~ /([0-9a-zA-Z]+)\s([0-9a-zA-Z_]+)\s([0-9]+)\s([0-9]+)\s[\+|\-]\s([0-9a-zA-Z]+)\s([0-9a-zA-Z_]+)\s([0-9]+)\s([0-9]+)\s[\+|\-]\s([0-9a-zA-Z]+)\s([0-9a-zA-Z_]+)\s([0-9]+)\s([0-9]+)\s/ ) {
			$key = join("\t",$1, $3, $4, $5, $7, $8, $9, $11, $12);
		}
		else {
			next;
		}
		$printer = 0;
		my $sequence = $sields[$sequencepos];
		chomp $sequence;
		$sequence =~ s/ //g;
		my @localfs = ();
		my @localrs = ();
		
		if (exists $fmicros{$key}){
			@localfs = @{$fmicros{$key}};
			delete $fmicros{$key};		
		}
	
		my %forwardstarts = ();
		my %forwardends = ();
	
		foreach my $f (@localfs){
			my @fields = split(/\t/,$f);
			push (@{$forwardstarts{$fields[$startcord]}},$f);
			push (@{$forwardends{$fields[$endcord]}},$fields[$startcord]);
		}
	
		if (exists $rmicros{$key}){
			@localrs = @{$rmicros{$key}};
			delete $rmicros{$key};		
		}
		else{
		}
	
		foreach my $r (@localrs){
			chomp $r;
			my @rields = split(/\t/,$r);
#			print "rields = @rields\n" if $printer == 1;
			my $reciprocalstart = length($sequence) - $rields[$endcord] + 1;
			my $reciprocalend = length($sequence) - $rields[$startcord] + 1;
#			print "reciprocal start = $reciprocalstart = ",length($sequence)," - $rields[$endcord] + 1\n" if $printer == 1;
			my $microsat = reverse_micro(all_caps($rields[$microsatcord]));
			my @localcollection=();
			for my $i ($reciprocalstart+1 ... $reciprocalend-1){
				if (exists $forwardstarts{$i}){
					push(@localcollection, $forwardstarts{$i}[0] );
					delete $forwardstarts{$i}; 
				}
				if (exists $forwardends{$i}){
					next if !exists $forwardstarts{$forwardends{$i}[0]};
					push(@localcollection, $forwardstarts{$forwardends{$i}[0]}[0] );
				}
			}
			if (exists $forwardstarts{$reciprocalstart} && exists $forwardends{$reciprocalend}) {push(@localcollection,$forwardstarts{$reciprocalstart}[0]);}
			
			if (scalar(@localcollection) == 0){
				print SAME invert_microsat($r,($sequence) ), "\n";
			}
	
			elsif (scalar(@localcollection) == 1){
#				print "f microsat = $localcollection[0]\n"  if $printer == 1;
				my @lields = split(/\t/,$localcollection[0]);
				$lields[$microsatcord]=all_caps($lields[$microsatcord]);
#				print "comparing: $microsat and $lields[$microsatcord]\n" if $printer == 1;
#				print "coordinates are: $lields[$startcord]-$lields[$endcord] and $reciprocalstart-$reciprocalend\n" if $printer == 1;
				if ($microsat eq $lields[$microsatcord]){
					chomp $localcollection[0];
					print SAME $localcollection[0], "\n";
				}
				if ($microsat ne $lields[$microsatcord]){
					chomp $localcollection[0];
					my $newmicro = microsatChooser(join("\t",@lields), join("\t",@rields), $sequence);
#					print "newmicro = $newmicro\n"  if $printer == 1;
					if ($newmicro =~ /[a-zA-Z]/){
						print SAME $newmicro,"\n";
					}
					else{
					print DIFF join("\t",$localcollection[0],"-->",$rields[$typecord],$reciprocalstart,$reciprocalend, $rields[$microsatcord], reverse_micro($rields[$motifcord]), @rields[$motifcord+1 ... $#rields] ),"\n";
#					print join("\t",$localcollection[0],"-->",$rields[$typecord],$reciprocalstart,$reciprocalend, $rields[$microsatcord], reverse_micro($rields[$motifcord]), @rields[$motifcord+1 ... $#rields] ),"\n" if $printer == 1;
#					print "@rields\n@lields\n" if $printer == 1;
					}
				}			
			}
			else{
#				print "multiple found for $r --> ", join("\t",@localcollection),"\n" if $printer == 1;
			}
		}
	}	
		
	close(SEQ);
	close(INF);
	close(INR);
	close(DIFF);
	close(SAME);
	
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
sub microsatChooser{
	my $forward = $_[0];
	my $reverse = $_[1];
	my $sequence = $_[2];
	my $seqLength = length($sequence);
	$sequence =~ s/ //g;
	my @fields = split(/\t/,$forward);
	my @rields = split(/\t/,$reverse);	
	my $r_start = $seqLength - $rields[$endcord] + 1;
	my $r_end = $seqLength - $rields[$startcord] + 1;
	
	
	my $f_microsat = $fields[$microsatcord];
	my $r_microsat = $rields[$microsatcord];
	
	if ($fields[$typecord] =~ /\./ && $rields[$typecord] =~ /\./) {
		return $forward if length($f_microsat) >= length($r_microsat);
		return invert_microsat($reverse, $sequence) if length($f_microsat) < length($r_microsat);
	}
	return $forward if all_caps($fields[$motifcord]) eq all_caps($rields[$motifcord]) && $fields[$startcord] == $rields[$startcord] && $fields[$endcord] == $rields[$endcord];	

	my $f_microsat_copy = $f_microsat;
	my $r_microsat_copy = $r_microsat;
	$f_microsat_copy =~ s/^\[|\]$//g;
	$r_microsat_copy =~ s/^\[|\]$//g;

	my @f_microields = split(/\][a-zA-Z]*\[/,$f_microsat_copy);
	my @r_microields = split(/\][a-zA-Z]*\[/,$r_microsat_copy);
	my @f_intields = split(/\][a-zA-Z]*\[/,$f_microsat_copy);
	my @r_intields = split(/\][a-zA-Z]*\[/,$r_microsat_copy);
	
	my $f_motif = $fields[$motifcord];
	my $r_motif = $rields[$motifcord];
	my $f_motif_copy = $f_motif;
	my $r_motif_copy = $r_motif;
	$f_motif_copy =~ s/^\[|\]$//g;
	$r_motif_copy =~ s/^\[|\]$//g;

	my @f_motields = split(/\]\[/,$f_motif_copy);
	my @r_motields = split(/\]\[/,$r_motif_copy);

	my $f_purestretch = join("",@f_microields);
	my $r_purestretch = join("",@r_microields);

	if ($fields[$typecord]=~/nucleotide/ && $rields[$typecord]=~/nucleotide/){
#		print "now.. studying $forward\n$reverse\n" if $printer == 1;
		if ($fields[$typecord] eq $rields[$typecord]){
#			print "comparing motifs::", all_caps($fields[$motifcord]) ," and ", all_caps(reverse_micro($rields[$motifcord])), "\n" if $printer == 1;

			if(motifBYmotif_match(all_caps($fields[$motifcord]), all_caps(reverse_micro($rields[$motifcord]))) == 1){
				my $subset_answer = isSubset($forward, $reverse, $seqLength);
#				print "subset answer = $subset_answer\n" if $printer == 1;
				return $forward if $subset_answer == 1; 
				return invert_microsat($reverse, $sequence) if $subset_answer == 2; 
				return $forward if $subset_answer == 0 && length($f_purestretch) >= length($r_purestretch);
				return invert_microsat($reverse, $sequence) if $subset_answer == 0 && length($f_purestretch) < length($r_purestretch);
				return $forward if $subset_answer == 3 && slided_microsat($forward, $reverse, $seqLength) == 0 && length($f_purestretch) >= length($r_purestretch);
				return invert_microsat($reverse, $sequence) if $subset_answer == 3 && slided_microsat($forward, $reverse, $seqLength) == 0 && length($f_purestretch) < length($r_purestretch);
				return merge_microsats($forward, invert_microsat($reverse, $sequence), $sequence) if $subset_answer == 3 ;			
			}
			elsif(motifBYmotif_match(all_caps($fields[$motifcord]), all_caps(reverse_micro($rields[$motifcord]))) == 0){
				return merge_microsats($forward, invert_microsat($reverse, $sequence), $sequence);
			}
			elsif(motifBYmotif_match(all_caps($fields[$motifcord]), all_caps(reverse_micro($rields[$motifcord]))) == 2){
				return $forward;
			}
			elsif(motifBYmotif_match(all_caps($fields[$motifcord]), all_caps(reverse_micro($rields[$motifcord]))) == 3){
				return invert_microsat($reverse, $sequence);
			}
		}
		else{
			my $fmotlen = ();
			my $rmotlen = ();
	 		$fmotlen =1 if $fields[$typecord] eq "mononucleotide";
	 		$fmotlen =2 if $fields[$typecord] eq "dinucleotide";
	 		$fmotlen =3 if $fields[$typecord] eq "trinucleotide";
	 		$fmotlen =4 if $fields[$typecord] eq "tetranucleotide";
	 		$rmotlen =1 if $rields[$typecord] eq "mononucleotide";
	 		$rmotlen =2 if $rields[$typecord] eq "dinucleotide";
	 		$rmotlen =3 if $rields[$typecord] eq "trinucleotide";
	 		$rmotlen =4 if $rields[$typecord] eq "tetranucleotide";
			
			if ($fmotlen < $rmotlen){
				if (abs($fields[$startcord] -  $r_start) <= $fmotlen || abs($fields[$endcord] -  $r_end) <= $fmotlen ){
					return $forward;
				}
				else{
					return merge_microsats($forward, invert_microsat($reverse, $sequence), $sequence);
				}
			}
			if ($fmotlen > $rmotlen){
				if (abs($fields[$startcord] -  $r_start) <= $rmotlen || abs($fields[$endcord] -  $r_end) <= $rmotlen){
					return invert_microsat($reverse, $sequence);
				}
				else{
					return merge_microsats($forward, invert_microsat($reverse, $sequence), $sequence);
				}
			}
		}
	}
	if ($fields[$typecord] eq "compound" && $rields[$typecord] eq "compound"){
#			print "comparing compound motifs::", all_caps($fields[$motifcord]) ," and ", all_caps(reverse_micro($rields[$motifcord])), "\n" if $printer == 1;
			if(motifBYmotif_match(all_caps($fields[$motifcord]), all_caps(reverse_micro($rields[$motifcord]))) == 1){
				my $subset_answer = isSubset($forward, $reverse, $seqLength);
#				print "subset answer = $subset_answer\n" if $printer == 1;
				return $forward if $subset_answer == 1; 
				return invert_microsat($reverse, $sequence) if $subset_answer == 2; 
#				print length($f_purestretch) ,">", length($r_purestretch)," \n" if $printer == 1;
				return $forward if $subset_answer == 0 && length($f_purestretch) >= length($r_purestretch);
				return invert_microsat($reverse, $sequence) if $subset_answer == 0 && length($f_purestretch) < length($r_purestretch);
				if ($subset_answer == 3){
					if ($fields[$startcord] < $r_start || $fields[$endcord] > $r_end){
						if (abs($fields[$startcord] -  $r_start) < length($f_motields[0]) || abs($fields[$endcord] -  $r_end)  < length($f_motields[$#f_motields]) ){
							return $forward;
						}
						else{
							return merge_microsats($forward, invert_microsat($reverse, $sequence), $sequence);
						}
					}
					if ($fields[$startcord] > $r_start || $fields[$endcord] < $r_end){
						if (abs($fields[$startcord] -  $r_start) < length($r_motields[0]) || abs($fields[$endcord] -  $r_end) < length($r_motields[$#r_motields]) ){
							return invert_microsat($reverse, $sequence);
						}
						else{
							return merge_microsats($forward, invert_microsat($reverse, $sequence), $sequence);
						}
					}
				}
			}
			elsif(motifBYmotif_match(all_caps($fields[$motifcord]), all_caps(reverse_micro($rields[$motifcord]))) == 0){
				return merge_microsats($forward, invert_microsat($reverse, $sequence), $sequence);
			}
			elsif(motifBYmotif_match(all_caps($fields[$motifcord]), all_caps(reverse_micro($rields[$motifcord]))) == 2){
				return $forward;
			}
			elsif(motifBYmotif_match(all_caps($fields[$motifcord]), all_caps(reverse_micro($rields[$motifcord]))) == 3){
				return invert_microsat($reverse, $sequence);
			}
		
	}
	
	if ($fields[$typecord] eq "compound" && $rields[$typecord] =~ /nucleotide/){
#		print "one compound, one nucleotide\n" if $printer == 1; 
		return merge_microsats($forward, invert_microsat($reverse, $sequence), $sequence);
	}
	if ($fields[$typecord] =~ /nucleotide/ && $rields[$typecord]eq "compound"){
#		print "one compound, one nucleotide\n" if $printer == 1; 
		return merge_microsats($forward, invert_microsat($reverse, $sequence), $sequence);
	}
}

sub isSubset{
	my $forward = $_[0]; 	my @fields = split(/\t/,$forward);
	my $reverse = $_[1];	my @rields = split(/\t/,$reverse);
	my $seqLength = $_[2];
	my $r_start = $seqLength - $rields[$endcord] + 1;
	my $r_end = $seqLength - $rields[$startcord] + 1;
#	print "we have $fields[$startcord] -> $fields[$endcord] && $r_start -> $r_end\n" if $printer == 1;
	return "0" if $fields[$startcord] == $r_start && $fields[$endcord] == $r_end;
	return "1" if $fields[$startcord] <= $r_start && $fields[$endcord] >= $r_end;
	return "2" if $r_start <= $fields[$startcord] && $r_end >= $fields[$endcord];
	return "3";
}

sub motifBYmotif_match{
	my $forward = $_[0];
	my $reverse = $_[1];
	$forward =~ s/^\[|\]$//g;
	$reverse =~ s/^\[|\]$//g;
	my @f_motields=split(/\]\[/, $forward);
	my @r_motields=split(/\]\[/, $reverse);
	my $finalresult = 0;

	if (scalar(@f_motields) != scalar(@r_motields)){
		my $subresult = 0;
		my @mega = (); my @sub = ();
		@mega = @f_motields if scalar(@f_motields) > scalar(@r_motields);
		@sub = @f_motields if scalar(@f_motields) > scalar(@r_motields);
		@mega = @r_motields if scalar(@f_motields) < scalar(@r_motields);
		@sub = @r_motields if scalar(@f_motields) < scalar(@r_motields);
		
		for my $i (0 ... $#sub){
			my $probe = $sub[$i].$sub[$i];
#			print "probing $probe and $mega[$i]\n" if $printer == 1;
			if ($probe =~ /$mega[$i]/) {$subresult = 1; }
			else {$subresult = 0; last; }
		}
		
		return 0 if $subresult == 0;
		return 2 if $subresult == 1 && scalar(@f_motields) > scalar(@r_motields); # r is subset of f
		return 3 if $subresult == 1 && scalar(@f_motields) < scalar(@r_motields);  # ^reverse
		
	}
	else{
		for my $i (0 ... $#f_motields){
			my $probe = $f_motields[$i].$f_motields[$i];
			if ($probe =~ /$r_motields[$i]/) {$finalresult = 1 ;}
			else {$finalresult = 0 ;last;}
		}
	}
#	print "finalresult = $finalresult\n" if $printer == 1;
	return $finalresult;
}

sub merge_microsats{
	my @input = @_;
	my $sequence = pop(@input);
	$sequence =~ s/ //g;
	my @seq_string = @input;
#	print "IN: merge_microsats\n";
#	print "recieved for merging: ", join("\n", @seq_string), "\nsequence = $sequence\n"; 
	my $start;
	my $end;
	my @micros = map { $_->[0] } sort custom map { [$_, split /\t/ ] } @seq_string; 
#	print "\nrearranged into @micros \n";
	my (@motifs, @microsats, @interruptiontypes, @interruptions, @interrposes, @no_of_interruptions, @types, @starts, @ends, @mergestart, @mergeend, @mergemicro) = ();
	my @fields = ();
	for my $i (0 ... $#micros){
		chomp $micros[$i];
		@fields = split(/\t/,$micros[$i]);
		push(@types, $fields[$typecord]);
		push(@motifs, $fields[$motifcord]);		

		if (exists $fields[$interrtypecord]){ push(@interruptiontypes, $fields[$interrtypecord]);}
			else { push(@interruptiontypes, "NA"); }
		if (exists $fields[$interrcord]) {push(@interruptions, $fields[$interrcord]);}
			else { push(@interruptions, "NA"); }
		if (exists $fields[$interr_poscord]) { push(@interrposes, $fields[$interr_poscord]);}	
			else { push(@interrposes, "NA"); }
		if (exists $fields[$no_of_interruptionscord]) {push(@no_of_interruptions, $fields[$no_of_interruptionscord]);}
			else { push(@no_of_interruptions, "NA"); }
		if(exists $fields[$mergestarts]) { @mergestart = (@mergestart, split(/\./,$fields[$mergestarts]));}
			else { push(@mergestart, $fields[$startcord]); }
		if(exists $fields[$mergeends]) { @mergeend = (@mergeend, split(/\./,$fields[$mergeends]));}
			else { push(@mergeend, $fields[$endcord]); }
		if(exists $fields[$mergemicros]) { push(@mergemicro, $fields[$mergemicros]);}
			else { push(@mergemicro, $fields[$microsatcord]); }
			

	}
	$start = smallest_number(@mergestart);
	$end = largest_number(@mergeend);
	my $microsat_entry = "[".substr( $sequence, $start-1, ($end - $start + 1) )."]";
	my $microsat = join("\t", @fields[0 ... $infocord], join(".", @types), $start, $fields[$strandcord], $end, $microsat_entry , join(".", @motifs), join(".", @interruptiontypes),join(".", @interruptions),join(".", @interrposes),join(".", @no_of_interruptions), join(".", @mergestart), join(".", @mergeend) , join(".", @mergemicro));
	return $microsat;
}

sub slided_microsat{
	my $forward = $_[0]; 	my @fields = split(/\t/,$forward);
	my $reverse = $_[1];	my @rields = split(/\t/,$reverse);
	my $seqLength = $_[2];
	my $r_start = $seqLength - $rields[$endcord] + 1;
	my $r_end = $seqLength - $rields[$startcord] + 1;
	my $motlen =();
	 $motlen =1 if $fields[$typecord] eq "mononucleotide";
	 $motlen =2 if $fields[$typecord] eq "dinucleotide";
	 $motlen =3 if $fields[$typecord] eq "trinucleotide";
	 $motlen =4 if $fields[$typecord] eq "tetranucleotide";
	
	if (abs($fields[$startcord] - $r_start) < $motlen || abs($fields[$endcord] - $r_end) < $motlen ) {
		return 0;
	}
	else{
		return 1;
	}
	
}

#xxxxxxxxxxxxxx forward_reverse_sputoutput_comparer xxxxxxxxxxxxxx  forward_reverse_sputoutput_comparer xxxxxxxxxxxxxx  forward_reverse_sputoutput_comparer xxxxxxxxxxxxxx 



#xxxxxxxxxxxxxx new_multispecies_t10 xxxxxxxxxxxxxx  new_multispecies_t10 xxxxxxxxxxxxxx  new_multispecies_t10 xxxxxxxxxxxxxx 
sub new_multispecies_t10{
	my $input1 = $_[0];  #gap_op_unrand_match
	my $input2 = $_[1];  #sput
	my $output = $_[2];  #output
	my $bin = $output."_bin";
	my $orgs = join("|",split(/\./,$_[3]));
	my @organisms = split(/\./,$_[3]);
	my $no_of_species = scalar(@organisms); #3
	my $t10info = $output."_info";
	$prinkter = 0;
	
	open (MATCH, "<$input1");
	open (SPUT, "<$input2");
	open (OUT, ">$output");
	open (INFO, ">$t10info");


	sub microsat_bracketer;
	sub custom;
	my %seen = ();
	$infocord = 2 + (4*$no_of_species) - 1;
	$typecord = 2 + (4*$no_of_species) + 1 - 1;
	$startcord = 2 + (4*$no_of_species) + 2 - 1;
	$strandcord = 2 + (4*$no_of_species) + 3 - 1;
	$endcord = 2 + (4*$no_of_species) + 4 - 1;
	$microsatcord = 2 + (4*$no_of_species) + 5 - 1;
	$motifcord = 2 + (4*$no_of_species) + 6 - 1;
	$sequencepos = 2 + (5*$no_of_species) + 1 -1 ; 
	#---------------------------------------------------------------------------------------------------------------#
	#	MAKING A HASH FROM SPUT, WITH HASH KEYS GENERATED BELOW AND SEQUENCES STORED AS VALUES	#
	#---------------------------------------------------------------------------------------------------------------#
	my $linecounter = 0;
	my $microcounter = 0;
	while (my $line = <SPUT>){
		chomp $line;
	#	print "$org\t(chr[0-9]+)\t([0-9]+)\t([0-9])+\t \n";
		next if $line !~ /[0-9a-z]+/;
		$linecounter++;
	#		my $key = join("\t",$1 , $2, $4, $5, $6, $8, $9, $10, $12, $13);
	#		print $key, "#-#-#-#-#-#-#-#\n";
		if ($line =~ /([0-9]+)\s+([0-9a-zA-Z]+)\s(chr[0-9a-zA-Z]+)\s([0-9]+)\s([0-9]+)\s/ ) {
			my $key = join("\t",$1, $2, $3, $4, $5);
#			print "key = $key\n" if $prinkter == 1;
			push (@{$seen{$key}},$line);	
			$microcounter++;
		}
		else {		
			#print "could not make ker in SPUT : \n$line \n"; 
		}
	}
#	print "done hash.. linecounter = $linecounter, microcounter = $microcounter and total keys entered = ",scalar(keys %seen),"\n";
#	print INFO  "done hash.. linecounter = $linecounter, microcounter = $microcounter and total keys entered = ",scalar(keys %seen),"\n";
	close SPUT;
	
	#----------------------------------------------------------------------------------------------------------------
	
	#-------------------------------------------------------------------------------------------------------#
	#	THE ENTIRE CODE BELOW IS DEVOTED TO GENERATING HASH KEYS FROM MATCH FOLLOWED BY			#
	#	USING THESE HASH KEYS TO CORRESPOND EACH SEQUENCE IN FIRST FILE TO ITS MICROSAT REPEATS IN			#
	#   SECOND FILE FOLLOWED BY																				#
	#	FINDING THE EXACT LOCATION OF EACH MICROSAT REPEAT WITHIN EACH SEQUENCE USING THE 'index' FUNCTION	#
	#-------------------------------------------------------------------------------------------------------#		
	my $ref = 0;
	my $ref2 = 0;
	my $ref3 = 0;
	my $ref4 = 0;
	my $deletes= 0;
	my $duplicates = 0;
	my $neighbors = 0;
	my $tooshort = 0;
	my $prevmicrol=();
	my $startnotfound = 0;
	my $matchkeysformed = 0;
	my $keysused = 0;
	
	while (my $line = <MATCH>)	{
#		print    colored ['magenta'], $line  if $prinkter == 1;
		next if $line !~ /[a-zA-Z0-9]/;
		chomp $line;	
		my @fields2 = split(/\t/,$line);
		my $key2 = ();
	#		$key2 = join("\t",$1 , $2, $4, $5, $6, $8, $9, $10, $12, $13);
		if ($line =~ /([0-9]+)\s+([0-9a-zA-Z]+)\s(chr[0-9a-zA-Z]+)\s([0-9]+)\s([0-9]+)\s/ ) {
			$matchkeysformed++;
			$key2 = join("\t",$1, $2, $3, $4, $5);
#			print "key = $key2 \n" if $prinkter == 1; 
		}
		else{
#			print "could not make ker in SEQ : $line\n";
			next;
		}
		my $sequence = $fields2[$sequencepos];
		$sequence =~ s/\*/-/g;
		my $count = 0;
		if (exists $seen{$key2}){
			$keysused++;
			my @unsorted_raw = @{$seen{$key2}};
			delete $seen{$key2};
			my @sequencearr = split(/\s*/, $sequence);
			
#			print "sequencearr = @sequencearr\n" if $prinkter == 1;
			
			my $counter;
	
			my %start_database = ();
			my %end_database = ();
			foreach my $uns (@unsorted_raw){
				my @uields = split(/\t/,$uns);
				$start_database{$uields[$startcord]} = $uns;
				$end_database{$uields[$endcord]} = $uns;
			}
			
			my @unsorted = ();
			my %starts = (); my %ends = ();
#			print colored ['yellow'],"unsorted, unfiltered microats = \n" if $prinkter == 1; foreach (@unsorted_raw) {print colored ['blue'],$_,"\n" if $prinkter == 1;}
			for my $u (0 ... $#unsorted_raw){
				my @tields = split(/\t/,$unsorted_raw[$u]);
				next if exists $starts{$tields[$startcord]} && exists $ends{$tields[$endcord]};
				push(@unsorted, $unsorted_raw[$u]);
				$starts{$tields[$startcord]} = $unsorted_raw[$u];
#				print "in starts : $tields[$startcord] -> $unsorted_raw[$u]\n" if $prinkter == 1;
			}
			
			my $basecounter= 0;
			my $gapcounter = 0;
			my $poscounter = 0;
			
			for my $s (@sequencearr){
				
				$poscounter++;
				if ($s eq "-"){
					$gapcounter++; next;
				}
				else{
					$basecounter++;
				}
				
				
				#print "s = $s, poscounter = $poscounter, basecounter = $basecounter, gapcpunter = $gapcounter\n" if $prinkter == 1;
				#print "s = $s, basecounter = $basecounter, gapcpunter = $gapcounter\n" if $prinkter == 1;
				#print "s = $s, gapcpunter = $gapcounter\n" if $prinkter == 1;
				
				if (exists $starts{$basecounter}){
					my $locus = $starts{$basecounter};
#					print "locus identified = $locus\n" if $prinkter == 1;
					my @fields3 = split(/\t/,$locus);
					my $start = $fields3[$startcord];
					my $end = $fields3[$endcord];
					my $motif = $fields3[$motifcord];
					my $microsat = $fields3[$microsatcord];				
					my @leftbracketpos = ();			
					my @rightbracketpos = (); 
					my $bracket_picker = 'no';
					my $leftbrackets=();
					my $rightbrackets = ();
					my $micro_cpy = $microsat;
#					print "microsat = $microsat\n" if $prinkter == 1;
					while($microsat =~ m/\[/g) {push(@leftbracketpos, (pos($microsat)));  $leftbrackets = join("__",@leftbracketpos);$bracket_picker='yes';}
					while($microsat =~ m/\]/g) {push(@rightbracketpos, (pos($microsat))); $rightbrackets = join("__",@rightbracketpos);}
					$microsat =~ s/[\[\]\-\*]//g;
#					print "microsat = $microsat\n" if $prinkter == 1;
					my $human_search = join '-*', split //, $microsat;
					my $temp = substr($sequence, $poscounter-1);
#					print "with poscounter = $poscounter\n" if $prinkter == 1;
					my $search_result = ();
					my $posnow  = ();
					
#					print "for $line, temp $temp or human_search $human_search not defined\n" if !defined $temp || !defined $human_search;
#					<STDIN> if !defined $temp || !defined $human_search;
					
					while ($temp =~ /($human_search)/gi){
						$search_result = $1;
					#	$posnow  = pos($temp);
						last;
					}
					
					my @gapspos = ();
					next if !defined $search_result;
					
					while($search_result =~ m/-/g) {push(@gapspos, (pos($search_result))); }
					my $gaps  = join("__",@gapspos);
	
					my $final_microsat = $search_result;
					if ($bracket_picker eq "yes"){
						$final_microsat = microsat_bracketer($search_result, $gaps,$leftbrackets,$rightbrackets);
					}
					
					my $outsentence = join("\t",join ("\t",@fields3[0 ... $infocord]),$fields3[$typecord],$fields3[$motifcord],$gapcounter,$poscounter,$fields3[$strandcord],$poscounter + length($search_result) -1 ,$final_microsat);
					
					if ($bracket_picker eq "yes") {
						$outsentence = $outsentence."\t".join("\t",@fields3[($motifcord+1) ... $#fields3]);
					}
					print OUT $outsentence,"\n";	
				}			
			}
		}
	}
	my $unusedkeys = scalar(keys %seen);
#	print INFO "in hash = $ref, looped = $ref4, captured = $ref3\n REMOVED: \nmicrosats with too long gaps = $deletes\n";
#	print INFO "exact duplicated removed = $duplicates \nmicrosats removed due to multiple microsats defined  in +-10 bp neighboring region: $neighbors \n";
#	print INFO "microsatellites too short = $tooshort\n";
#	print INFO "keysused = $keysused...starts not found = $startnotfound ... matchkeysformed=$matchkeysformed ... unusedkeys=$unusedkeys\n";
	
	#print  "in hash = $ref, looped = $ref4, captured = $ref3\n REMOVED: \nmicrosats with too long gaps = $deletes\n";
	#print  "exact duplicated removed = $duplicates \nmicrosats removed due to multiple microsats defined  in +-10 bp neighboring region: $neighbors \n";
	#print  "microsatellites too short = $tooshort\n";
	#print  "keysused = $keysused...starts not found = $startnotfound ... matchkeysformed=$matchkeysformed ... unusedkeys=$unusedkeys\n";
	#print "unused keys = \n",join("\n", (keys %seen)),"\n";
	close (MATCH);
	close (SPUT);
	close (OUT);
	close (INFO);
}	

sub microsat_bracketer{
#	print "in bracketer: @_\n";
	my ($microsat, $gapspos, $leftbracketpos, $rightbracketpos) = @_;
	my @gaps = split(/__/,$gapspos);
	my @lefts = split(/__/,$leftbracketpos);
	my @rights = split(/__/,$rightbracketpos);
	my @new=();
	my $pure = $microsat;
	$pure =~ s/-//g;
	my $off = 0;
	my $finallength  = length($microsat) + scalar(@lefts)+scalar(@rights);
	push(@gaps, 0);
	push(@lefts,0);
	push(@rights,0);
	
	for my $i (1 ... $finallength){
#		print "1 current i = >$i<>, right = >$rights[0]<  gap = $gaps[0] left = >$lefts[0]< and $rights[0] == $i\n";
		if($rights[0] == $i){
	#		print "pushed a ]\n";
			push(@new, "]");
			shift(@rights);
			push(@rights,0);
			for my $j (0 ... scalar(@gaps)-1) {$gaps[$j]++;}	
			next;
		}
		if($gaps[0] == $i){
	#		print "pushed a -\n";
			push(@new, "-");
			shift(@gaps);
			push(@gaps, 0);
			for my $j (0 ... scalar(@rights)-1) {$rights[$j]++;}	
			for my $j (0 ... scalar(@lefts)-1) {$lefts[$j]++;}	

			next;
		}
		if($lefts[0] == $i){
#			print "pushed a [\n";
			push(@new, "[");
			shift(@lefts);
			push(@lefts,0);
			for my $j (0 ... scalar(@gaps)-1) {$gaps[$j]++;}	
			next;
		}
		else{
			my $pushed = substr($pure,$off,1);
			$off++;
			push(@new,$pushed );
#			print "pushed an alphabet, now new = @new, pushed = $pushed\n";
			next;
		}
	}
	my $returnmicrosat = join("",@new);
#	print "final microsat = $returnmicrosat \n";
	return($returnmicrosat);
}

#xxxxxxxxxxxxxx new_multispecies_t10 xxxxxxxxxxxxxx  new_multispecies_t10 xxxxxxxxxxxxxx  new_multispecies_t10 xxxxxxxxxxxxxx 


#xxxxxxxxxxxxxx multiSpecies_orthFinder4 xxxxxxxxxxxxxx  multiSpecies_orthFinder4 xxxxxxxxxxxxxx  multiSpecies_orthFinder4 xxxxxxxxxxxxxx 
sub multiSpecies_orthFinder4{
	#print "IN multiSpecies_orthFinder4: @_\n";
	my @handles = ();
	#1 SEPT 30TH 2008
	#2 THIS CODE (multiSpecies_orthFinder4.pl)  IS BEING MADE SO THAT IN THE REMOVAL OF MICROSATELLITES THAT ARE CLOSER TO EACH OTHER
	#3 THAN 50 BP (HE 50BP RADIUS OF EXCLUSION), WE ARE LOOKING ACCROSS ALIGNMENT BLOCKS.. AND NOT JUST LOOKING WITHIN THE ALIGNMENT BLOCKS. THIS WILL
	#4 POTENTIALLY REMOVE EVEN MORE MICROSATELLITES THAN BEFORE, BUT THIS WILL RESCUE THOSE MICROSATELLITES THAT WERE LOST
	#5 DUE TO OUR PREVIOUS REQUIREMENT FROM VERSION 3, THAT MICROSATELLITES THAT ARE CLOSER TO THE BOUNDARY THAN 25 BP NEED TO BE REMOVED
	#6 SUCH A REQUIREMENT WAS A CRUDE WAY TO IMPOSE THE ABOVE 50 BP RADIUS OF EXCLUSION ACCROSS THE ALIGNMENT BLOCKS WITHOUT ACTUALLY
	#7 CHECKING COORDINATES OF THE EXCLUDED MICROSATELLITES.
	#8 IN ORDER TO TAKE CARE OF THE CASES WHERE MICROSATELLITES ARE PRELIOUSLY CLOSE TO ENDS OF THE ALIGNMENT BLOCKS, WE IMPOSE HERE
	#9 A NEW REQUIREMENT THAT FOR A MICROSATELLITE TO BE CONSIDERED, ALL THE SPECIES NEED TO HAVE AT LEAST 10 BP OF NON-MICROSATELLITE SEQUENCE
	#10 ON EITHER SIDE OF IT.. GAPLESS. THIS INFORMATION IS STORED IN THE VARIABLE: $FLANK_SUPPORT. THIS PART, INSTEAD OF BEING INCLUDED IN
	#11 THIS CODE, WILL BE INCLUDED IN A NEW CODE THAT WE WILL BE WRITING AS PART OF THE PIPELINE: multiSpecies_microsatSetSelector.pl
	
	#1 trial run:
	#2 perl ../../../codes/multiSpecies_orthFinder4.pl /gpfs/home/ydk104/work/rhesus_microsat/axtNet/hg18.panTro2.ponAbe2.rheMac2.calJac1/chr22.hg18.panTro2.ponAbe2.rheMac2.calJac1.net.axt H.hg18-chr22.panTro2.ponAbe2.rheMac2.calJac1_allmicrosats_symmetrical_fin_hit_all_2:C.hg18-chr22.panTro2.ponAbe2.rheMac2.calJac1_allmicrosats_symmetrical_fin_hit_all_2:O.hg18-chr22.panTro2.ponAbe2.rheMac2.calJac1_allmicrosats_symmetrical_fin_hit_all_2:R.hg18-chr22.panTro2.ponAbe2.rheMac2.calJac1_allmicrosats_symmetrical_fin_hit_all_2:M.hg18-chr22.panTro2.ponAbe2.rheMac2.calJac1_allmicrosats_symmetrical_fin_hit_all_2 orth22 hg18:panTro2:ponAbe2:rheMac2:calJac1 50
	
	$prinkter=0;
	
	#############
	my $CLUSTER_DIST = $_[4];
	#############
	
	
	my $aligns = $_[0];
	my @micros = split(/:/, $_[1]);
	my $orth = $_[2];
	#my $not_orth = "notorth";
	@tags = split(/:/, $_[3]);
	
	$no_of_species=scalar(@tags);
	my $junkfile = $orth."_junk";
	#open(JUNK,">$junkfile");
	
	#my $info = $output1."_info";
	#print "inputs are : \n"; foreach(@micros){print $_,"\n";} 
	#print "info = @_\n";
	
	
	open (BO, "<$aligns") or die "Cannot open alignment file: $aligns: $!";
	open (ORTH, ">$orth");
	my $output=$orth."_out";
	open (OUTP, ">$output");
	
	
	#open (NORTH, ">$not_orth");
	#open (INF, ">$info");
	my $i = 0;
	foreach my $path (@micros){
		$handles[$i] = IO::Handle->new();
		open ($handles[$i], "<$path") or die "Can't open microsat file $path : $!";
		$i++;
	}
	
	#print "Opened files\n";
	
	
	$infocord = 2 + (4*$no_of_species) - 1;
	$typecord = 2 + (4*$no_of_species) + 1 - 1;
	$motifcord = $typecord + 1;
	$gapcord = $motifcord+1;
	$startcord = $gapcord + 1;
	$strandcord = $startcord + 1;
	$endcord = $strandcord + 1;
	$microsatcord = $endcord + 1;
	$sequencepos = 2 + (4*$no_of_species) + 1 -1 ; 
	#$sequencepos = 17;
	#	GENERATING HASHES CONTAINING CHIMP AND HUMAN DATA FROM ABOVE FILES
	#----------------------------------------------------------------------------------------------------------------
	my @hasharr = ();
	foreach my $path (@micros){
		open(READ, "<$path") or die "Cannot open file $path :$!";
		my %single_hash = ();
		my $key = ();
		my $counter = 0;
		while (my $line = <READ>){
			$counter++;
		#	print $line;
			chomp $line;
			my @fields1 = split(/\t/,$line);
			if ($line =~ /([0-9]+)\s+($focalspec)\s(chr[0-9a-zA-Z]+)\s([0-9]+)\s([0-9]+)/ ) {
				$key = join("\t",$1, $2,  $4, $5);
	
#					print "key =  : $key\n" if $prinkter == 1;
				
#				print $line if $prinkter == 1;
				push (@{$single_hash{$key}},$line);
			}
			else{
			#	print "microsat line incompatible\n";
			}
		}
		push @hasharr, {%single_hash};
	#	print "@{$single_hash{$key}} \n";
#		print "done $path: counter = $counter\n" if $prinkter == 1;
		close READ;
	}	
#	print "Done hashes\n";
	#----------------------------------------------------------------------------------------------------------------
	my $question=();
	#----------------------------------------------------------------------------------------------------------------
	my @contigstarts = ();
	my @contigends = ();
	
	my %contigclusters = ();
	my %contigclustersFirstStartOnly=();
	my %contigclustersLastEndOnly=();
	my %contigclustersLastEndLengthOnly=();
	my %contigclustersFirstStartLengthOnly=();
	my %contigpath=();
	my $dotcounter = 0;
	while (my $line = <BO>){
#		print "x" x 60, "\n" if $prinkter == 1;
		$dotcounter++;
#		print "." if $dotcounter % 100 ==0;
#		print "\n" if $dotcounter % 5000 ==0;
		next if $line !~ /^[0-9]+/;
#		print $line if $prinkter == 1;
		chomp $line;	
		my @fields2 = split(/\t/,$line);
		my $key2 = ();
		if ($line =~ /([0-9]+)\s+($focalspec)\s(chr[0-9a-zA-Z]+)\s([0-9]+)\s([0-9]+)/ ) {
			$key2 = join("\t",$1, $2,  $4, $5);
		}
		else {
#			print "seq line $line incompatible\n" if $prinkter == 1; 
			next;}
		
		
		
		
		
		
		my @sequences = ();
		for (0 ... $#tags){
			my $seq = <BO>;
	#		print $seq;
			chomp $seq;
			push(@sequences , " ".$seq);
		}
		my @origsequences = @sequences;
		my $seqcopy = $sequences[0];
		my @strings = ();
		$seqcopy =~ s/[a-zA-Z]|-/x/g;
		my @string = split(/\s*/,$seqcopy);
	
		for my $s (0 ... $#tags){
			$sequences[$s] =~ s/-//g;
			$sequences[$s] =~ s/[a-zA-Z]/x/g;		
	#		print "length  of sequence = ",length($sequences[$s]),"\n";
			my @tempstring = split(/\s*/,$sequences[$s]);
			push(@strings, [@tempstring])
			
		}
	
		my @species_list = ();
		my @micro_count = 0;
		my @starthash = ();
		my $stopper = 1;
		my @endhash = ();
		
		my @currentcontigstarts=();
		my @currentcontigends=();
		my @currentcontigchrs=();
		
		for my $i (0 ... $#tags){
#			print "searching for : if exists  hasharr: $i : $tags[$i] : $key2 \n" if $prinkter == 1;
			my @temparr = (); 
	
			if (exists $hasharr[$i]{$key2}){
				@temparr =  @{$hasharr[$i]{$key2}};
				
				$line =~ /$tags[$i]\s([a-zA-Z0-9_]+)\s([0-9]+)\s([0-9]+)/;
##				print "in line $line, trying to hunt for: $tags[$i]\\s([a-zA-Z0-9_])+\\s([0-9]+)\\s([0-9]+) \n" if $prinkter == 1;
#				print "org = $tags[$i], and chr = $1, start = $2, end =$3 \n" if $prinkter == 1; 
				my $startkey = $1."_SK0SK_".$2; #print "adding start key for this alignmebt block: $startkey to species $tags[$i]\n" if $prinkter == 1;
				my $endkey = $1."_EK0EK_".$3; #print "adding end key for this alignmebt block: $endkey to species $tags[$i]\n" if $prinkter == 1;
				$contigstarts[$i]{$startkey}= $key2;
				$contigends[$i]{$endkey}= $key2;
#				print "confirming existance: \n" if $prinkter == 1;
#				print "present \n" if exists $contigends[$i]{$endkey} && $prinkter == 1;
#				print "absent \n" if !exists $contigends[$i]{$endkey} && $prinkter == 1;			
				$currentcontigchrs[$i]=$1;
				$currentcontigstarts[$i]=$2;
				$currentcontigends[$i]=$3;
				
			} # print "exists: @{$hasharr[$i]{$key2}}[0]\n"}
			else {
				push (@starthash, {0 => "0"});
				push (@endhash, {0 => "0"});
				$currentcontigchrs[$i] = 0;
				next;
			}
			$stopper = 0;
	#		print "exists: @temparr\n" if $prinkter == 1;
			push(@micro_count, scalar(@temparr));
			push(@species_list, [@temparr]);	
			my @tempstart = (); my @tempend = ();
			my %localends = ();
			my %localhash = ();
	#		print "---------------------------\n";
	
			foreach my $templine (@temparr){
#				print "templine = $templine\n" if $prinkter == 1;
				my @tields = split(/\t/,$templine);
				my $start = $tields[$startcord]; # - $tields[$gapcord];
				my $end = $tields[$endcord]; #- $tields[$gapcord];
				my $realstart = $tields[$startcord]- $tields[$gapcord];
				my $gapsinmicrosat = ($tields[$microsatcord] =~ s/-/-/g);
				$gapsinmicrosat = 0 if $gapsinmicrosat !~ /[0-9]+/;
	#			print "infocord = $infocord  typecord = $typecord  motifcord = $motifcord  gapcord = $gapcord  startcord = $startcord strandcord = $strandcord endcord = $endcord   microsatcord = $microsatcord  sequencepos = $sequencepos\n";
				my $realend = $tields[$endcord]- $tields[$gapcord]- $gapsinmicrosat;
		#		print "real start = $realstart, realend = $realend \n";
				for my $pos ($realstart ... $realend){  $strings[$i][$pos] = $strings[$i][$pos].",".$i.":".$start."-".$end;}
				push(@tempstart, $start);
				push(@tempend, $end);
				$localhash{$start."-".$end} = $templine;
				}
			push @starthash, {%localhash};
			my $foundclusters  =findClusters(join("!",@{$strings[$i]}), $CLUSTER_DIST);
	
#			print "foundclusters = $foundclusters\n";
	
			my @clusters = split(/_/,$foundclusters);
			
			my $clustno = 0;
			
			foreach my $cluster (@clusters) {
				my @constituenst = split(/,/,$cluster);
#				print "clusters returned: @constituenst\n" if $prinkter == 1;
			}
	
			@string = split("_S0S_",stringPainter(join("_C0C_",@string),$foundclusters));
			
			
		}
		next if $stopper == 1;
	
#		print colored ['blue'],"FINAL:\n" if $prinkter == 1;
		my $finalclusters  =findClusters(join("!",@string), 1);
#		print "finalclusters = $finalclusters\n";
#		print colored ['blue'],"----------------------\n" if $prinkter == 1;
		my @clusters = split(/,/,$finalclusters);
#			print "@string\n" if $prinkter == 1;
#			print "@clusters\n" if $prinkter == 1;
#			print "------------------------------------------------------------------\n" if $prinkter == 1;
		
		my $clustno = 0;
		
	#	foreach my $cluster (@clusters) {
	#		my @constituenst = split(/,/,$cluster);
	#		print "clusters returned: @constituenst\n";
	#	}
	
		next if (scalar @clusters == 0);
	
		my @contigcluster=();
		my $clusterno=0;
		my @contigClusterstarts=();
		my @contigClusterends = ();
		
		foreach my $clust (@clusters){
	 #		print "cluster: $clust\n";   		
			$clusterno++;
			my @localclust = split(/\./, $clust);
			my @result = ();
			my @starts = ();
			my @ends = ();
	 
			for my $i (0 ... $#localclust){
	 #			print "localclust[$i]: $localclust[$i]\n";   		
				my @pattern = split(/:/, $localclust[$i]);
				my @cords = split(/-/, $pattern[1]);
				push (@starts, $cords[0]);
				push (@ends, $cords[1]);
			}
	
			my $extremestart = smallest_number(@starts);
			my $extremeend = largest_number(@ends);
			push(@contigClusterstarts, $extremestart);
			push(@contigClusterends, $extremeend);
#			print "cluster starts from $extremestart and ends at $extremeend \n" if $prinkter == 1 ;
					
			foreach my $clustparts (@localclust){
				my @pattern = split(/:/, $clustparts);
	# 			print "printing from pattern: $pattern[1]: $starthash[$pattern[0]]{$pattern[1]}\n";
				push (@result, $starthash[$pattern[0]]{$pattern[1]});
			}
			push(@contigcluster, join("\t", @result));
#			print join("\t", @result),"<-result \n" if $prinkter == 1 ;
		}	
		
	
		my $firstclusterstart = smallest_number(@contigClusterstarts);
		my $lastclusterend = largest_number(@contigClusterends);
		
		
		$contigclustersFirstStartOnly{$key2}=$firstclusterstart;	
		$contigclustersLastEndOnly{$key2} = $lastclusterend;
		$contigclusters{$key2}=[ @contigcluster ];
#		print "currentcontigchr are @currentcontigchrs , firstclusterstart = $firstclusterstart, lastclusterend = $lastclusterend\n " if $prinkter == 1;
		for my $i (0 ... $#tags){
			#1 check if there exists adjacent alignment block wrt coordinates of this species.
			next if $currentcontigchrs[$i] eq "0"; #1 this means that there are no microsats in this species in this alignment block.. 
												 #2	no need to worry about proximity of anything in adjacent block!
			
			#1 BELOW, the following is really to calclate the distance between the end coordinate of the 
			#2 cluster and the end of the gap-free sequence of each species. this is so that if an
			#3 adjacent alignment block is found lateron, the exact distance between the potentially
			#4 adjacent microsat clusters can be found here. the exact start coordinate will be used
			#5 immediately below.
	#		print "full sequence = $origsequences[$i] and its length = ",length($origsequences[$i])," \n" if $prinkter == 1;		
			
			my $species_startsubstring = substr($origsequences[$i], 0, $firstclusterstart);
			my $species_endsubstring = ();
			
			if (length ($origsequences[$i]) <= $lastclusterend+1){ $species_endsubstring = "";}
			else{  $species_endsubstring = substr($origsequences[$i], $lastclusterend+1);}
			
#			print "\nnot defined species_endsubstring...\n"  if !defined $species_endsubstring && $prinkter == 1;
#			print "for species: $tags[$i]: \n" if $prinkter == 1;
			
			$species_startsubstring =~ s/-| //g;
			$species_endsubstring =~ s/-| //g;
			$contigclustersLastEndLengthOnly{$key2}[$i]=length($species_endsubstring);
			$contigclustersFirstStartLengthOnly{$key2}[$i]=length($species_startsubstring);
	
	
	
#			print "species_startsubstring = $species_startsubstring, and its length =",length($species_startsubstring)," \n" if $prinkter == 1;
#			print "species_endsubstring = $species_endsubstring, and its length =",length($species_endsubstring)," \n" if $prinkter == 1;
#			print "attaching to contigclustersLastEndOnly: $key2: $i\n" if $prinkter == 1;	
			
#			print "just confirming: $contigclustersLastEndLengthOnly{$key2}[$i] \n" if $prinkter == 1;
	
		}
	
	
	}
#	print "\ndone the job of filling... \n";
	#///////////////////////////////////////////////////////////////////////////////////////
	#///////////////////////////////////////////////////////////////////////////////////////
	#///////////////////////////////////////////////////////////////////////////////////////
	#///////////////////////////////////////////////////////////////////////////////////////
	$prinkter=0;
	open (BO, "<$aligns") or die "Cannot open alignment file: $aligns: $!";
	
	my %clusteringpaths=();
	my %clustersholder=();
	my %foundkeys=();
	my %clusteringpathsRev=();
	
	
	my $totalcount=();
	my $founkeys_enteredcount=();
	my $transfered=0;
	my $complete_transfered=0;
	my $plain_transfered=0;
	my $existing_removed=0;
	
	while (my $line = <BO>){
#		print "x" x 60, "\n" if $prinkter == 1;
		next if $line !~ /^[0-9]+/;
		#print $line;
		chomp $line;	
		my @fields2 = split(/\t/,$line);
		my $key2 = ();
		if ($line =~ /([0-9]+)\s+($focalspec)\s(chr[0-9a-zA-Z_]+)\s([0-9]+)\s([0-9]+)/ ) {
			$key2 = join("\t",$1, $2,  $4, $5);
		}
		
		else {
		#	print "seq line $line incompatible\n";
			next;
		}
#		print "KEY =  : $key2\n" if $prinkter == 1;
	
	
		my @currentcontigstarts=();
		my @currentcontigends=();
		my @currentcontigchrs=();
		my @clusters = ();
		my @clusterscopy=();
		if (exists $contigclusters{$key2}){
			@clusters =  @{$contigclusters{$key2}};
			@clusterscopy=@clusters;
			for my $i (0 ... $#tags){
	#			print "in line $line, trying to hunt for: $tags[$i]\\s([a-zA-Z0-9])+\\s([0-9]+)\\s([0-9]+) \n" if $prinkter == 1;
				if ($line =~ /$tags[$i]\s([a-zA-Z0-9_]+)\s([0-9]+)\s([0-9]+)/){
	#				print "org = $tags[$i], and chr = $1, start = $2, end =$3 \n" if $prinkter == 1; 
					my $startkey = $1."_S0E_".$2; #print "adding start key for this alignmebt block: $startkey to species $tags[$i]\n" if $prinkter == 1;
					my $endkey = $1."_S0E_".$3; #print "adding end key for this alignmebt block: $endkey to species $tags[$i]\n" if $prinkter == 1;
					$currentcontigchrs[$i]=$1;
					$currentcontigstarts[$i]=$2;
					$currentcontigends[$i]=$3;			
				}
				else {
					$currentcontigchrs[$i] = 0;
	#				print "no microsat clusters for $key2\n" if $prinkter == 1; next;	
				}
			}
		} # print "exists: @{$hasharr[$i]{$key2}}[0]\n"}
		
		my @sequences = ();
		for (0 ... $#tags){
			my $seq = <BO>;
	#		print $seq;
			chomp $seq;
			push(@sequences , " ".$seq);
		}
		
		next if scalar @currentcontigchrs == 0;
		
	#	print "contigchrs= @currentcontigchrs \n" if $prinkter == 1;
		my %visitedcontigs=();
	
		for my $i (0 ... $#tags){
			#1 check if there exists adjacent alignment block wrt coordinates of this species.
			next if $currentcontigchrs[$i] eq "0"; #1 this means that there are no microsats in this species in this alignment block.. 
													#2	no need to worry about proximity of anything in adjacent block!
			@clusters=@clusterscopy;
			#1 BELOW, the following is really to calclate the distance between the end coordinate of the 
			#2 cluster and the end of the gap-free sequence of each species. this is so that if an
			#3 adjacent alignment block is found lateron, the exact distance between the potentially
			#4 adjacent microsat clusters can be found here. the exact start coordinate will be used
			#5 immediately below.
			my $firstclusterstart = $contigclustersFirstStartOnly{$key2};
			my $lastclusterend = $contigclustersLastEndOnly{$key2};
					
			my $key3 = $currentcontigchrs[$i]."_S0E_".($currentcontigstarts[$i]);
#			print  "check if exists $key3 in  contigends for $i\n" if $prinkter == 1; 
			
			if (exists($contigends[$i]{$key3}) && !exists $visitedcontigs{$contigends[$i]{$key3}}){
				$visitedcontigs{$contigends[$i]{$key3}} = $contigends[$i]{$key3}; #1 this array keeps track of adjacent contigs that we have already visited, thus saving computational time and potential redundancies#
	#			print "just checking the hash visitedcontigs: ",$visitedcontigs{$contigends[$i]{$key3}} ,"\n" if $prinkter == 1;
	
				#1 extract coordinates of the last cluster of this found alignment block
#				print "key of the found alignment block = ", $contigends[$i]{$key3},"\n" if $prinkter == 1;
	#			print "we are trying to mine: contigclustersAllLastEndLengthOnly_raw: $contigends[$i]{$key3}: $i \n" if $prinkter == 1;
	#			print "EXISTS\n" if exists $contigclusters{$contigends[$i]{$key3}} && $prinkter == 1;
	#			print "does NOT EXIST\n" if !exists $contigclusters{$contigends[$i]{$key3}} && $prinkter == 1;
				my @contigclustersAllFirstStartLengthOnly_raw=@{$contigclustersFirstStartLengthOnly{$key2}};
				my @contigclustersAllLastEndLengthOnly_raw=@{$contigclustersLastEndLengthOnly{$contigends[$i]{$key3}}};
				my @contigclustersAllFirstStartLengthOnly=(); my @contigclustersAllLastEndLengthOnly=();
				
				for my $val (0 ... $#contigclustersAllFirstStartLengthOnly_raw){
	#				print "val = $val\n" if $prinkter == 1;
					if (defined $contigclustersAllFirstStartLengthOnly_raw[$val]){
						push(@contigclustersAllFirstStartLengthOnly, $contigclustersAllFirstStartLengthOnly_raw[$val]) if $contigclustersAllFirstStartLengthOnly_raw[$val] =~ /[0-9]+/;
					}
				}
	#			print "-----\n" if $prinkter == 1;
				for my $val (0 ... $#contigclustersAllLastEndLengthOnly_raw){
	#				print "val = $val\n" if $prinkter == 1;
					if (defined $contigclustersAllLastEndLengthOnly_raw[$val]){
						push(@contigclustersAllLastEndLengthOnly, $contigclustersAllLastEndLengthOnly_raw[$val]) if  $contigclustersAllLastEndLengthOnly_raw[$val] =~ /[0-9]+/;
					}
				}
				
				
	#			print "our two arrays are: starts = <@contigclustersAllFirstStartLengthOnly> ......... and ends = <@contigclustersAllLastEndLengthOnly>\n" if $prinkter == 1;
	#			print "the last cluster's end in that one is: ",smallest_number(@contigclustersAllFirstStartLengthOnly) + smallest_number(@contigclustersAllLastEndLengthOnly)," = ", smallest_number(@contigclustersAllFirstStartLengthOnly)," + ",smallest_number(@contigclustersAllLastEndLengthOnly),"\n" if $prinkter == 1; 
				
	#			if ($contigclustersFirstStartLengthOnly{$key2}[$i] + $contigclustersLastEndLengthOnly{$contigends[$i]{$key3}}[$i] < 50){
				if (smallest_number(@contigclustersAllFirstStartLengthOnly) + smallest_number(@contigclustersAllLastEndLengthOnly) < $CLUSTER_DIST){
					my @regurgitate = @{$contigclusters{$contigends[$i]{$key3}}}; 
					$regurgitate[$#regurgitate]=~s/\n//g;
					$regurgitate[$#regurgitate] = $regurgitate[$#regurgitate]."\t".shift(@clusters);
					delete $contigclusters{$contigends[$i]{$key3}};
					$contigclusters{$contigends[$i]{$key3}}=[ @regurgitate ];
					delete $contigclusters{$key2};
					$contigclusters{$key2}= [ @clusters ] if scalar(@clusters) >0;
					$contigclusters{$key2}= [ "" ] if scalar(@clusters) ==0;
					
					if (scalar(@clusters) < 1){
				#		print "$key2-> $clusteringpaths{$key2} in the loners\n" if exists $foundkeys{$key2};
						$clusteringpaths{$key2}=$contigends[$i]{$key3};	
						$clusteringpathsRev{$contigends[$i]{$key3}}=$key2;				
						print OUTP "$contigends[$i]{$key3} -> $clusteringpathsRev{$contigends[$i]{$key3}}\n";
	#					print " clusteringpaths $key2 -> $contigends[$i]{$key3}\n";
						$founkeys_enteredcount-- if exists $foundkeys{$key2};
						$existing_removed++  if exists $foundkeys{$key2};
#						print "$key2->",@{$contigclusters{$key2}},"->>$foundkeys{$key2}\n" if exists $foundkeys{$key2} && $prinkter == 1;
						delete $foundkeys{$key2} if exists $foundkeys{$key2};
						$complete_transfered++;
					}
					else{
						print OUTP "$key2-> 0 not so lonely\n"  if !exists $clusteringpathsRev{$key2};
						$clusteringpaths{$key2}=$key2  if !exists $clusteringpaths{$key2};
						$clusteringpathsRev{$key2}=0 if !exists $clusteringpathsRev{$key2};
						
						$founkeys_enteredcount++ if !exists $foundkeys{$key2};
						$foundkeys{$key2} = $key2 if !exists $foundkeys{$key2};
	#					print "adding foundkeys entry $foundkeys{$key2}\n";
						$transfered++;				
					}
					#$contigclusters{$key2}=[ @contigcluster ];
				}
			}
			else{
	#					print "adjacent block with species $tags[$i] does not exist\n" if $prinkter == 1; 
						$plain_transfered++;
						print OUTP "$key2-> 0 , going straight\n"  if exists $contigclusters{$key2} && !exists $clusteringpathsRev{$key2};
						$clusteringpaths{$key2}=$key2 if exists $contigclusters{$key2} && !exists $clusteringpaths{$key2};
						$clusteringpathsRev{$key2}=0  if exists $contigclusters{$key2} && !exists $clusteringpathsRev{$key2};
						$founkeys_enteredcount++ if !exists $foundkeys{$key2} && exists $contigclusters{$key2};
						$foundkeys{$key2} = $key2 if !exists $foundkeys{$key2} && exists $contigclusters{$key2};
	#					print "adding foundkeys entry $foundkeys{$key2}\n";
				
			}
			$totalcount++;
	
		}
		
		
	}
	close BO;
	#close (NORTH);
	#///////////////////////////////////////////////////////////////////////////////////////
	#///////////////////////////////////////////////////////////////////////////////////////
	#///////////////////////////////////////////////////////////////////////////////////////
	#///////////////////////////////////////////////////////////////////////////////////////
	
	my $founkeys_count=();
	my $nopath_count=();
	my $pathed_count=0; 
	foreach my $key2 (keys %foundkeys){
		#print "x" x 60, "\n";
#		print "x" if $dotcounter % 100 ==0;
#		print "\n" if $dotcounter % 5000 ==0;
		$founkeys_count++;
		my $key = $key2;
#		print "$key2 -> $clusteringpaths{$key2}\n" if $prinkter == 1;
		if ($clusteringpaths{$key} eq $key){
#			print "printing hit the alignment block immediately... no path needed\n" if $prinkter == 1;
			$nopath_count++;
			delete $foundkeys{$key2};
			print ORTH join ("\n",@{$contigclusters{$key2}}),"\n";
		}
		else{
			my @pool=();
			my $key3=();
			$pathed_count++;
#			print "going reverse... clusteringpathsRev, $key = $clusteringpathsRev{$key}\n" if exists $clusteringpathsRev{$key} && $prinkter == 1;
#			print "going reverse... clusteringpathsRev  $key does not exist\n" if !exists $clusteringpathsRev{$key} && $prinkter == 1;
			if ($clusteringpathsRev{$key} eq "0") {
 				next;
			}
			else{
				my $yek3 = $clusteringpathsRev{$key};
				my $yek = $key;
#				print "caught in the middle of a path, now goin down from $yek to $yek3, which is $clusteringpathsRev{$key} \n" if $prinkter == 1;
				while ($yek3 ne "0"){
#					print "$yek->$yek3," if $prinkter == 1;
					$yek = $yek3;
					$yek3 = $clusteringpathsRev{$yek};
				}
#				print "\nfinally reached the end of path: $yek3, and the next in line is $yek, and its up-route is  $clusteringpaths{$yek}\n" if $prinkter == 1; 
				$key3 = $clusteringpaths{$yek};
				$key = $yek;
			}
		
#			print "now that we are at bottom of the path, lets start climbing up again\n" if $prinkter == 1;
			
			while($key ne $key3){
#				print "KEEY $key->$key3\n" if $prinkter == 1;
#				print "our contigcluster = @{$contigclusters{$key}}\n----------\n" if $prinkter == 1;
				
				if (scalar(@{$contigclusters{$key}}) > 0) {push @pool, @{$contigclusters{$key}}; 
				#	print "now pool = @pool\n" if $prinkter == 1;
				}
				delete $foundkeys{$key3};
				$key=$key3;
				$key3=$clusteringpaths{$key};
			}
#			print "\nfinally, adding the first element of path: @{$contigclusters{$key}}\n AND printing the contents:\n" if $prinkter == 1;
			my @firstcontig= @{$contigclusters{$key}};
			delete $foundkeys{$key2} if exists $foundkeys{$key2} ;
			delete $foundkeys{$key} if exists $foundkeys{$key};
	
			unshift @pool, pop @firstcontig;
#			print join("\t",@pool),"\n" if $prinkter == 1;
			print ORTH join ("\n",@firstcontig),"\n" if scalar(@firstcontig) > 0;
			print ORTH join ("\t",@pool),"\n";		
		#	join();
		}
	
	}
	#close (NORTH);
#	print "founkeys_entered =$founkeys_enteredcount, plain_transfered=$plain_transfered,existing_removed=$existing_removed,founkeys_count =$founkeys_count, nopath_count =$nopath_count, transfered = $transfered, complete_transfered = $complete_transfered, totalcount = $totalcount, pathed=$pathed_count\n" if $prinkter == 1;
	close (BO);
	close (ORTH);
	close (OUTP);
	return 1;
	
}
sub stringPainter{
	my @string  = split(/_C0C_/,$_[0]);
#	print $_[0], " <- in stringPainter\n";
#	print $_[1], " <- in clusters\n";
	
	my @clusters = split(/,/, $_[1]);
	for my $i (0 ... $#clusters){
		my $cluster = $clusters[$i];
#		print "cluster = $cluster\n";
		my @parts = split(/\./,$cluster);
		my @cord = split(/:|-/,shift(@parts));
		my $minstart = $cord[1];
		my $maxend = $cord[2];
#		print "minstart = $minstart , maxend = $maxend\n";
		
		for my $j (0 ... $#parts){
#			print "oing thri $parts[$j]\n";
			my @cord = split(/:|-/,$parts[$j]);
			$minstart = $cord[1] if $cord[1] < $minstart;
			$maxend = $cord[2] if $cord[2] > $maxend;
		}
#		print "minstart = $minstart , maxend = $maxend\n";
		for my $pos ($minstart ... $maxend){ $string[$pos] = $string[$pos].",".$cluster;}
				
		
	}
#	print "@string <-done from function stringPainter\n";
	return join("_S0S_",@string);
}

sub findClusters{
	my $continue = 0;
	my @mapped_clusters = ();	
	my $clusterdist = $_[1];
	my $previous = 'x';
	my @localcluster = ();
	my $cluster_starts = ();
	my $cluster_ends = ();
	my $localcluster_start = ();
	my $localcluster_end = ();
	my @record_cluster = ();
	my @string = split(/\!/, $_[0]);
	my $zerolength=0;
	
	for my $pos_pos (1 ... $#string){
			my $pos = $string[$pos_pos];
#			print $pos, "\n";
			if ($continue == 0 && $pos eq "x") {next;}
			
			if ($continue == 1 && $pos eq "x" && $zerolength <= $clusterdist){ 
				if ($zerolength == 0) {$localcluster_end = $pos_pos-1};
				$zerolength++; 
				$continue = 1; 
			}

			if ($continue == 1 && $pos eq "x" && $zerolength > $clusterdist) { 
				$zerolength = 0; 
				$continue = 0; 
				my %seen;
				my @uniqed = grep !$seen{$_}++, @localcluster;
#				print "caught cluster : @uniqed \n";
				push(@mapped_clusters, [@uniqed]);
#				print "clustered:\n@uniqed\n";
				@localcluster = ();
				@record_cluster = ();
				
			}
			
			if ($pos ne "x"){
				$zerolength = 0;
				$continue = 1;
				$pos =~ s/x,//g;
				my @entries = split(/,/,$pos);
				$localcluster_end = 0;
				$localcluster_start = 0;
				push(@record_cluster,$pos);
			
				if ($continue == 0){
					@localcluster = ();
					@localcluster = (@localcluster, @entries);
					$localcluster_start = $pos_pos;
				}
			
				if ($continue == 1 ) {
					@localcluster = (@localcluster, @entries);
				}
			}
	}
	
	if (scalar(@localcluster) > 0){
		my %seen;
		my @uniqed = grep !$seen{$_}++, @localcluster;
	#	print "caught cluster : @uniqed \n";
		push(@mapped_clusters, [@uniqed]);
	#	print "clustered:\n@uniqed\n";
		@localcluster = ();
		@record_cluster = ();
	}

	my @returner = ();
	
	foreach my $clust (@mapped_clusters){
		my @localclust = @$clust;
		my @result = ();
		foreach my $clustparts (@localclust){
			push(@result,$clustparts);
		}
		push(@returner , join(".",@result));
	}	
#	print "returnig: ", join(",",@returner), "\n";
	return join(",",@returner);
}
#xxxxxxxxxxxxxx multiSpecies_orthFinder4 xxxxxxxxxxxxxx  multiSpecies_orthFinder4 xxxxxxxxxxxxxx  multiSpecies_orthFinder4 xxxxxxxxxxxxxx 

#xxxxxxxxxxxxxx MakeTrees xxxxxxxxxxxxxxxxxxxxxxxxxxxx  MakeTrees xxxxxxxxxxxxxxxxxxxxxxxxxxxx  MakeTrees xxxxxxxxxxxxxxxxxxxxxxxxxxxx 

sub MakeTrees{
	my $tree = $_[0];
	my @parts=($tree);
#	my @parts=();
	
	while (1){
		$tree =~ s/^\(//g;
		$tree =~ s/\)$//g;
		my @arr = ();
	
		if ($tree =~ /^([a-zA-Z0-9_]+),([a-zA-Z0-9_\(\),]+)\)$/){
			@arr = $tree =~ /^([a-zA-Z0-9_]+),([a-zA-Z0-9_\(\),]+)$/;
			$tree = $2;
			push @parts, $tree;
		}
		elsif ($tree =~ /^\(([a-zA-Z0-9_\(\),]+),([a-zA-Z0-9_]+)$/){
			@arr = $tree =~ /^([a-zA-Z0-9_\(\),]+),([a-zA-Z0-9_]+)$/;
			$tree = $1;
			push @parts, $tree;
		}
		elsif ($tree =~ /^([a-zA-Z0-9_]+),([a-zA-Z0-9_]+)$/){
			last;
		}
	}	
	return @parts;
}

#xxxxxxxxxxxxxx qualityFilter xxxxxxxxxxxxxxxxxxxxxxxxxxxx  qualityFilter xxxxxxxxxxxxxxxxxxxxxxxxxxxx  qualityFilter xxxxxxxxxxxxxxxxxxxxxxxxxxxx 

sub qualityFilter{
	my $unmaskedorthfile = $_[0];
	my $seqfile = $_[1];
	my $maskedorthfile = $_[2];
	my $filteredout = $maskedorthfile."_residue";
	open (PMORTH, "<$unmaskedorthfile") or die "Cannot open unmaskedorthfile file: $unmaskedorthfile: $!";

	my %keyhash = ();
	
	while (my $line = <PMORTH>){
		my $key = join("\t", $1,$2,$3,$4) if $line =~ /($focalspec)\s+([a-zA-Z0-9\-_]+)\s+([0-9]+)\s+([0-9]+)/;
		push @{$keyhash{$key}}, $line;
	}
	
	open (SEQ, "<$seqfile") or die "Cannot open seqfile file: $seqfile: $!";
	open (MORTH, ">$maskedorthfile") or die "Cannot open maskedorthfile file: $maskedorthfile: $!";
        open (RES, ">$filteredout") or die "Cannot open filteredout file: $filteredout: $!";


	
	while (my $line = <SEQ>){
		chomp $line;
		if ($line =~ /($focalspec)\s+([a-zA-Z0-9\-_]+)\s+([0-9]+)\s+([0-9]+)/){
			my $key = join("\t", $1,$2,$3,$4);
			next if !exists $keyhash{$key};
			my @orths = @{$keyhash{$key}} if exists $keyhash{$key};
			delete $keyhash{$key};
			
			my $sine = <SEQ>;
			
			foreach my $orth (@orths){
				#print "-----------------------------------------------------------------\n";
				#print $orth;
				my $orthcopy = $orth;
				$orth =~ s/^>//;
				my @parts = split(/>/,$orth);
				
				my @starts = ();
				my @ends = ();
				
				foreach my $part (@parts){
					my $no_of_species = adjustCoordinates($part);
					my @pields = split(/\t/,$part);
					
				#	print "pields = @pields .. no_of_species = $no_of_species .. startcord = $pields[$startcord]\n";
					
					push @starts, $pields[$startcord];
					push @ends, $pields[$endcord];
				}
				
				#print "starts = @starts ... ends = @ends\n";
				
				my $leftend = smallest_number(@starts)-10;
				my $rightend = largest_number(@ends)+10;

				my $maskarea = substr($sine, $leftend, $rightend-$leftend+1);
				print RES $orth if $maskarea =~ /#/;		
				
				
				next if $maskarea =~ /#/;
				
				print MORTH $orthcopy;
			}
		}
		else{
			next;
		}
		
		
	}
	
#	print "UNDONE: ", scalar(keys %keyhash),"\n";
#	print MORTH "UNDONE: ", scalar(keys %keyhash),"\n";
	
}

sub adjustCoordinates{
	my $line = $_[0];
	my $no_of_species = $line =~ s/(chr[0-9a-zA-Z]+)|(Contig[0-9a-zA-Z\._\-]+)|(scaffold[0-9a-zA-Z\._\-]+)|(supercontig[0-9a-zA-Z\._\-]+)/x/ig;
	my @got = ($line =~ s/(chr[0-9a-zA-Z]+)|(Contig[0-9a-zA-Z\._\-]+)/x/g);
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




