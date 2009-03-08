#!/usr/bin/perl -w
# a program to get indels 
# input is a MAF format 3-way alignment file
# from 3-way blocks only at this time
# translate seq2, seq3, etc coordinates to + if align orient is reverse complement
 
use strict;
use warnings;

# declare and initialize variables
my $fh; # variable to store filehandle
my $record;
my $offset;
my $library = $ARGV[0]; 
my $count = 0;
my $count2 = 0;
my $count3 = 0;
my $count4 = 0;
my $start1 = my $start2 = my $start3 = my $start4 = my $start5 = my $start6 = 0;
my $orient = "";
my $outgroup = $ARGV[2];
my $ingroup1 = my $ingroup2 = "";
my $count_seq1insert = my $count_seq1delete = 0;
my $count_seq2insert = my $count_seq2delete = 0;
my $count_seq3insert = my $count_seq3delete = 0;
my @seq1_insert_lengths = my @seq1_delete_lengths = ();
my @seq2_insert_lengths = my @seq2_delete_lengths = ();
my @seq3_insert_lengths = my @seq3_delete_lengths = ();
my @seq1_insert =  my @seq1_delete =  my @seq2_insert =  my @seq2_delete =  my @seq3_insert =  my @seq3_delete = ();
my @seq1_insert_startOnly = my @seq1_delete_startOnly = my @seq2_insert_startOnly = my @seq2_delete_startOnly = ();
my @seq3_insert_startOnly = my @seq3_delete_startOnly = ();
my @indels = (); 

# check to make sure correct files
my $usage = "usage: parseMAF_smallIndels.pl [MAF.in] [small_Indels_summary.out] [outgroup]\n";
die $usage unless @ARGV == 3;

# perform some standard subroutines 
$fh = open_file($library);

$offset = tell($fh);

#my $ofile = $ARGV[2];
#unless (open(OFILE, ">$ofile")){
#	 print "Cannot open output file \"$ofile\"\n\n";
#	 exit;
#}

my $ofile2 = $ARGV[1];
unless (open(OFILE2, ">$ofile2")){
         print "Cannot open output file \"$ofile2\"\n\n";
         exit;
}


# header line for output files
#print OFILE "# small indel events, parsed from MAF 3-way alignment file, coords are translated from (-) to (+) if necessary\n";
#print OFILE "#align\tingroup1\tingroup1_coord\tingroup1_orient\tingroup2\tingroup2_coord\tingroup2_orient\toutgroup\toutgroup_coord\toutgroup_orient\tindel_type\n";

#print OFILE2 "# small indels summary, parsed from MAF 3-way alignment file, coords are translated from (-) to (+) if necessary\n";
print OFILE2 "#block\tindel_type\tindel_length\tingroup1\tingroup1_start\tingroup1_end\tingroup1_alignSize\tingroup1_orient\tingroup2\tingroup2_start\tingroup2_end\tingroup2_alignSize\tingroup2_orient\toutgroup\toutgroup_start\toutgroup_end\toutgroup_alignSize\toutgroup_orient\n";

# main body of program
while ($record = get_next_record($fh) ){
	if ($record=~ m/\s*##maf(.*)\s*# maf/s){
		next;
	}

	my @sequences = get_sequences_within_block($record);
	my @seq_info = get_indels_within_block(@sequences);
	get_indels_lengths(@seq_info);
	
	$offset = tell($fh);
        $count++;
        
}

get_starts_only(@seq1_insert);
get_starts_only(@seq1_delete);
get_starts_only(@seq2_insert);
get_starts_only(@seq2_delete);
get_starts_only(@seq3_insert);
get_starts_only(@seq3_delete);

# print some things to keep track of progress
#print "# $library\n";
#print "# number of records = $count\n";
#print "# number of sequence \"s\" lines = $count2\n";
if ($count3 != 0){
	print "Skipped $count3 blocks with only 2 seqs;\n";
}
#print "# number of records with only h-m = $count4\n\n";

print "Ingroup1 = $ingroup1; Ingroup2 = $ingroup2; Outgroup = $outgroup;\n";
print "# of ingroup1 inserts = $count_seq1insert;\n";
print "# of ingroup1 deletes = $count_seq1delete;\n";
print "# of ingroup2 inserts = $count_seq2insert;\n";
print "# of ingroup2 deletes = $count_seq2delete;\n";
print "# of outgroup3 inserts = $count_seq3insert;\n";
print "# of outgroup3 deletes = $count_seq3delete\n";


#close OFILE;

if ($count == $count3){
	print STDERR "Skipped all blocks since none of them contain 3-way alignments.\n";
  	exit -1;
}

###################SUBROUTINES#####################################

# subroutine to open file
sub open_file {
        my($filename) = @_;
        my $fh;

        unless (open($fh, $filename)){
                print "Cannot open file $filename\n";
                exit;
        }
        return $fh;
}

# get next record
sub get_next_record {
        my ($fh) = @_;
        my ($offset);
        my ($record) = "";
        my ($save_input_separator) = $/;
	
	$/ = "a score";

        $record = <$fh>;

        $/ = $save_input_separator;
        return $record;
}

# get header info
sub get_sequences_within_block{
	my (@alignment) = @_;
	my @lines = ();
	
	my @sequences = ();
		
	@lines = split ("\n", $record);
	foreach (@lines){
		chomp($_);
		if (m/^\s*$/){
			next;
		}
		elsif (m/^\s*=(\d+\.*\d*)/){

		}elsif (m/^\s*s(.*)$/){
			$count2++;
			
			push (@sequences,$_);
		}
	}
	return @sequences;
}
	
sub get_indels_within_block{
	my (@sequences) = @_;	
	my $line1 = my $line2 = my $line3 = "";
    my @line1 = my @line2 = my @line3 = ();
	my $score = 0;
        my $start1 = my $align_length1 = my $end1 = my $seq_length1 = 0;
        my $start2 = my $align_length2 = my $end2 = my $seq_length2 = 0;
        my $start3 = my $align_length3 = my $end3 = my $seq_length3 = 0;
        my $seq1 = my $orient1 = "";
        my $seq2 = my $orient2 = "";
        my $seq3 = my $orient3 = "";
        my $start1_plus = my $end1_plus = 0;
        my $start2_plus = my $end2_plus = 0;
        my $start3_plus = my $end3_plus = 0;
   	my @test = ();
        my $test = "";
        my $header = "";
        my @header = ();
        my $sequence1 = my $sequence2 = my $sequence3 ="";
	my @array_return = ();	
	my $test1 = 0;
	my $line1_stat = my $line2_stat = my $line3_stat = "";
    
	# process 3-way blocks only
	if (scalar(@sequences) == 3){
		$line1 = $sequences[0]; 
		chomp ($line1);
		$line2 = $sequences[1]; 
		chomp ($line2);
		$line3 = $sequences[2];	
		chomp ($line3);
		# check order of sequences and assign uniformly seq1= human, seq2 = chimp, seq3 = macaque
		if ($line1 =~ m/$outgroup/){
			$line1_stat = "out";
			$line2=~ s/^\s*//;
            $line2 =~ s/\s+/\t/g;
            @line2 = split(/\t/, $line2);
			if (($ingroup1 eq "") || ($line2[1] =~ m/$ingroup1/)){
			 $line2_stat = "in1";
			 $line3_stat = "in2";
			 }
			 else{
             $line3_stat = "in1";
             $line2_stat = "in2";              }
			}
		elsif ($line2 =~ m/$outgroup/){
			$line2_stat = "out";
			$line1=~ s/^\s*//;
            $line1 =~ s/\s+/\t/g;
            @line1 = split(/\t/, $line1);
            if (($ingroup1 eq "") || ($line1[1] =~ m/$ingroup1/)){
             $line1_stat = "in1";
             $line3_stat = "in2";
             }
             else{
             $line3_stat = "in1";
             $line1_stat = "in2";              }
            }
		elsif ($line3 =~ m/$outgroup/){
			$line3_stat = "out";
			$line1=~ s/^\s*//;
            $line1 =~ s/\s+/\t/g;
            @line1 = split(/\t/, $line1);
            if (($ingroup1 eq "") || ($line1[1] =~ m/$ingroup1/)){
             $line1_stat = "in1";
             $line2_stat = "in2";
             }
             else{
             $line2_stat = "in1";
             $line1_stat = "in2";              }
			}

		#print "# l1 = $line1_stat\n";
		#print "# l2 = $line2_stat\n";
		#print "# l3 = $line3_stat\n";
		my $linei1 = my $linei2 = my $lineo = "";
		my @linei1 = my @linei2 = my @lineo = ();
		
        if ($line1_stat eq "out"){
            $lineo = $line1;
        }
        elsif ($line1_stat eq "in1"){
            $linei1 = $line1;
        }
        else{
            $linei2 = $line1;
        }
        
        if ($line2_stat eq "out"){
            $lineo = $line2;
        }
        elsif ($line2_stat eq "in1"){
            $linei1 = $line2;
        }
        else{
            $linei2 = $line2;
        }
        
        if ($line3_stat eq "out"){
            $lineo = $line3;
        }
        elsif ($line3_stat eq "in1"){
            $linei1 = $line3;
        }
        else{
            $linei2 = $line3;
        }
        
        $linei1=~ s/^\s*//;
        $linei1 =~ s/\s+/\t/g;
        @linei1 = split(/\t/, $linei1);
        $end1 =($linei1[2]+$linei1[3]-1);
        $seq1 = $linei1[1].":".$linei1[3];
        $ingroup1 = (split(/\./, $seq1))[0];
        $start1 = $linei1[2];
        $align_length1 = $linei1[3];
        $orient1 = $linei1[4];
        $seq_length1 = $linei1[5];
        $sequence1 = $linei1[6];
        $test1 = length($sequence1);
        my $total_length1 = $test1+$start1;
        my @array1 = ($start1,$end1,$orient1,$seq_length1);
        ($start1_plus, $end1_plus) =  convert_coords(@array1);
           
        $linei2=~ s/^\s*//;
        $linei2 =~ s/\s+/\t/g;
        @linei2 = split(/\t/, $linei2);
        $end2 =($linei2[2]+$linei2[3]-1);               
        $seq2 = $linei2[1].":".$linei2[3];
        $ingroup2 = (split(/\./, $seq2))[0];
        $start2 = $linei2[2];
        $align_length2 = $linei2[3];
        $orient2 = $linei2[4];
        $seq_length2 = $linei2[5];
        $sequence2 = $linei2[6];
        my $test2 = length($sequence2);
        my $total_length2 = $test2+$start2;
        my @array2 = ($start2,$end2,$orient2,$seq_length2);
        ($start2_plus, $end2_plus) = convert_coords(@array2); 
            
        $lineo=~ s/^\s*//;
        $lineo =~ s/\s+/\t/g;
        @lineo = split(/\t/, $lineo);
        $end3 =($lineo[2]+$lineo[3]-1);
        $seq3 = $lineo[1].":".$lineo[3];
        $start3 = $lineo[2];
        $align_length3 = $lineo[3];
        $orient3 = $lineo[4];
        $seq_length3 = $lineo[5];
        $sequence3 = $lineo[6];
        my $test3 = length($sequence3);
        my $total_length3 = $test3+$start3;
        my @array3 = ($start3,$end3,$orient3,$seq_length3);
        ($start3_plus, $end3_plus) = convert_coords(@array3);
        
        #print "# l1 = $ingroup1\n";
		#print "# l2 = $ingroup2\n";
		#print "# l3 = $outgroup\n";
	
		my $ABC = "";
		my $coord1 = my $coord2 = my $coord3 = 0;
                $coord1 = $start1_plus;
                $coord2 = $start2_plus;
                $coord3 = $start3_plus;
		
		for (my $position = 0; $position < $test1; $position++) {
			my $indelType = "";
			my $indel_line = "";	
			# seq1 deletes
			 if ((substr($sequence1,$position,1) eq "-") 
		    		&& (substr($sequence2,$position,1) !~ m/[-*\#$?^@]/)
	       			&& (substr($sequence3,$position,1) !~ m/[-*\#$?^@]/)){
					$ABC = join("",($ABC,"X"));
					my @s = split(/:/, $seq1);
					$indelType = $s[0]."_delete";

					#print OFILE "$count\t$seq1\t$coord1\t$orient1\t$seq2\t$coord2\t$orient2\t$seq3\t$coord3\t$orient3\t$indelType\n";	
					$indel_line = join("\t",($count,$seq1,$coord1,$orient1,$seq2,$coord2,$orient2,$seq3,$coord3,$orient3,$indelType));
					push (@indels,$indel_line);
					push (@seq1_delete,$indel_line);
		 			$coord2++; $coord3++;
	       		}	
			# seq2 deletes
			elsif ((substr($sequence1,$position,1) !~ m/[-*\#$?^@]/)
				&& (substr($sequence2,$position,1) eq "-")
				&& (substr($sequence3,$position,1) !~ m/[-*\$?^]/)){
					$ABC = join("",($ABC,"Y"));
					my @s = split(/:/, $seq2);
					$indelType = $s[0]."_delete";
					#print OFILE "$count\t$seq1\t$coord1\t$orient1\t$seq2\t$coord2\t$orient2\t$seq3\t$coord3\t$orient3\t$indelType\n";
					$indel_line = join("\t",($count,$seq1,$coord1,$orient1,$seq2,$coord2,$orient2,$seq3,$coord3,$orient3,$indelType));
                                        push (@indels,$indel_line);
					push (@seq2_delete,$indel_line);
					$coord1++;
					$coord3++;

			}
			# seq1 inserts
			elsif ((substr($sequence1,$position,1) !~ m/[-*\#$?^@]/)
				&& (substr($sequence2,$position,1) eq "-")
				&& (substr($sequence3,$position,1) eq "-")){
					$ABC = join("",($ABC,"Z"));
					my @s = split(/:/, $seq1);
					$indelType = $s[0]."_insert";
					#print OFILE "$count\t$seq1\t$coord1\t$orient1\t$seq2\t$coord2\t$orient2\t$seq3\t$coord3\t$orient3\t$indelType\n";
					$indel_line = join("\t",($count,$seq1,$coord1,$orient1,$seq2,$coord2,$orient2,$seq3,$coord3,$orient3,$indelType));
					push (@indels,$indel_line);
					push (@seq1_insert,$indel_line);
					$coord1++;
			}
			# seq2 inserts	
			elsif ((substr($sequence1,$position,1) eq "-")
				&& (substr($sequence2,$position,1) !~ m/[-*\#$?^@]/)
				&& (substr($sequence3,$position,1) eq "-")){
					$ABC = join("",($ABC,"W"));
					my @s = split(/:/, $seq2);
					$indelType = $s[0]."_insert";
					#print OFILE "$count\t$seq1\t$coord1\t$orient1\t$seq2\t$coord2\t$orient2\t$seq3\t$coord3\t$orient3\t$indelType\n";
					$indel_line = join("\t",($count,$seq1,$coord1,$orient1,$seq2,$coord2,$orient2,$seq3,$coord3,$orient3,$indelType));
					push (@indels,$indel_line);
					push (@seq2_insert,$indel_line);
					$coord2++;
			}
			# seq3 deletes
			elsif ((substr($sequence1,$position,1) !~ m/[-*\#$?^@]/)
				&& (substr($sequence2,$position,1) !~ m/[-*\#$?^@]/)
				&& (substr($sequence3,$position,1) eq "-")){
					$ABC = join("",($ABC,"S"));
					my @s = split(/:/, $seq3);
					$indelType = $s[0]."_delete";
					#print OFILE "$count\t$seq1\t$coord1\t$orient1\t$seq2\t$coord2\t$orient2\t$seq3\t$coord3\t$orient3\t$indelType\n";
					$indel_line = join("\t",($count,$seq1,$coord1,$orient1,$seq2,$coord2,$orient2,$seq3,$coord3,$orient3,$indelType));
					push (@indels,$indel_line);
					push (@seq3_delete,$indel_line);
					$coord1++; $coord2++;
			}
			# seq3 inserts
			elsif ((substr($sequence1,$position,1) eq "-")
				&& (substr($sequence2,$position,1) eq "-")
				&& (substr($sequence3,$position,1) !~ m/[-*\#$?^@]/)){
					$ABC = join("",($ABC,"T"));
					my @s = split(/:/, $seq3);
					$indelType = $s[0]."_insert";
					#print OFILE "$count\t$seq1\t$coord1\t$orient1\t$seq2\t$coord2\t$orient2\t$seq3\t$coord3\t$orient3\t$indelType\n";
					$indel_line = join("\t",($count,$seq1,$coord1,$orient1,$seq2,$coord2,$orient2,$seq3,$coord3,$orient3,$indelType));
					push (@indels,$indel_line);
					push (@seq3_insert,$indel_line);
					$coord3++;
			}else{
				$ABC = join("",($ABC,"N"));
				$coord1++; $coord2++; $coord3++;
			}

		}
		@array_return=($seq1,$seq2,$seq3,$ABC);
		return (@array_return); 

	}
	# ignore pairwise cases for now, just count the number of blocks
	elsif (scalar(@sequences) == 2){
		my $ABC = "";
		my $coord1 = my $coord2 = my $coord3 = 0;
		$count3++;

		$line1 = $sequences[0];
		$line2 = $sequences[1];
		chomp ($line1);
		chomp ($line2);

		if ($line2 !~ m/$ingroup2/){
		       $count4++;
		}
	}
}

		
sub get_indels_lengths{
	my (@array) = @_;
	if (scalar(@array) == 4){
		my $seq1 = $array[0]; my $seq2 = $array[1]; my $seq3 = $array[2]; my $ABC = $array[3];

		while ($ABC =~ m/(X+)/g) {
			push (@seq1_delete_lengths,length($1));
			$count_seq1delete++;
		}
		
		while ($ABC =~ m/(Y+)/g) {
			push (@seq2_delete_lengths,length($1));
			$count_seq2delete++;
		}
		while ($ABC =~ m/(S+)/g) {
			push (@seq3_delete_lengths,length($1));
			$count_seq3delete++;
		}
		while ($ABC =~ m/(Z+)/g) {	
			push (@seq1_insert_lengths,length($1));
			$count_seq1insert++;
		}
		while ($ABC =~ m/(W+)/g) {
			push(@seq2_insert_lengths,length($1));
			$count_seq2insert++;
		}
		while ($ABC =~ m/(T+)/g) {
			push (@seq3_insert_lengths,length($1));
			$count_seq3insert++;
		}
	}
	elsif (scalar(@array) == 0){
		next;
	}
		
}
# convert to coordinates to + strand if align orient = -
sub convert_coords{
	my (@array) = @_;
	my $s = $array[0];
	my $e = $array[1];
	my $o = $array[2];
	my $l = $array[3];
	my $start_plus = my $end_plus = 0;

	if ($o eq "-"){
		$start_plus = ($l - $e);
		$end_plus = ($l - $s);
	}elsif ($o eq "+"){
		$start_plus = $s;
		$end_plus = $e;
	}

	return ($start_plus, $end_plus);
}

# get first line only for each event
sub get_starts_only{
	my (@test) = @_;
        my $seq1 = my $seq2 = my $seq3 = my $indelType = my $old_seq1 = my $old_seq2 = my $old_seq3 = my $old_indelType = my $old_line = "";
        my $coord1 = my $coord2 = my $coord3 = my $old_coord1 = my $old_coord2 = my $old_coord3 = 0;

        my @matches = ();
        my @seq1_insert = my @seq1_delete = my @seq2_insert = my @seq2_delete = my @seq3_insert = my @seq3_delete = ();
				
	
       	foreach my $line (@test){
                chomp($line);
                $line =~ s/^\s*//;
                $line =~ s/\s+/\t/g;
				my @line1 = split(/\t/, $line);
                 $seq1 = $line1[1];
                 $coord1 = $line1[2];
                $seq2 = $line1[4];
                 $coord2 = $line1[5];
                 $seq3 = $line1[7];
                 $coord3 = $line1[8];
                 $indelType = $line1[10];
                if ($indelType =~ m/$ingroup1/ && $indelType =~ m/insert/){
           		if ($coord1 != $old_coord1+1 || ($coord2 != $old_coord2 || $coord3 != $old_coord3)){
	       			$start1++;
                              	push (@seq1_insert_startOnly,$line);
                     	}
	     	}
                elsif ($indelType =~ m/$ingroup1/ && $indelType =~ m/delete/){
		        if ($coord1 != $old_coord1 || ($coord2 != $old_coord2+1 || $coord3 != $old_coord3+1)){
		                $start2++;
		                push(@seq1_delete_startOnly,$line);
		        }
		}
                elsif ($indelType =~ m/$ingroup2/ && $indelType =~ m/insert/){
	                if ($coord2 != $old_coord2+1 || ($coord1 != $old_coord1 || $coord3 != $old_coord3)){
		                $start3++;
		                push(@seq2_insert_startOnly,$line);
		        }
		}
                elsif ($indelType =~ m/$ingroup2/ && $indelType =~ m/delete/){
                        if ($coord2 != $old_coord2 || ($coord1 != $old_coord1+1 || $coord3 != $old_coord3+1)){
                                $start4++;
                                push(@seq2_delete_startOnly,$line);
                        }
                }
                elsif ($indelType =~ m/$outgroup/ && $indelType =~ m/insert/){
                        if ($coord3 != $old_coord3+1 || ($coord1 != $old_coord1 || $coord2 != $old_coord2)){
                                $start5++;
                                push(@seq3_insert_startOnly,$line);
                        }
                }
                elsif ($indelType =~ m/$outgroup/ && $indelType =~ m/delete/){
                        if ($coord3 != $old_coord3 || ($coord1 != $old_coord1+1 ||$coord2 != $old_coord2+1)){
                                $start6++;
                                push(@seq3_delete_startOnly,$line);
                        }
                }
                 $old_indelType = $indelType;
                 $old_seq1 = $seq1;
                 $old_coord1 = $coord1;
                 $old_seq2 = $seq2;
                 $old_coord2 = $coord2;
                 $old_seq3 = $seq3;
                 $old_coord3 = $coord3;
                 $old_line = $line;
        }
}
# append lengths to each event start line
my $counter1; my $counter2; my $counter3; my $counter4; my $counter5; my $counter6; 
my @final1 = my @final2 = my @final3 = my @final4 = my @final5 = my @final6 = ();
my $final_line1 = my $final_line2 = my $final_line3 = my $final_line4 = my $final_line5 = my $final_line6 = "";


for ($counter1 = 0; $counter1 < @seq3_insert_startOnly; $counter1++){
	$final_line1 = join("\t",($seq3_insert_startOnly[$counter1],$seq3_insert_lengths[$counter1]));
	push (@final1,$final_line1);
}

for ($counter2 = 0; $counter2 < @seq3_delete_startOnly; $counter2++){
        $final_line2 =  join("\t",($seq3_delete_startOnly[$counter2],$seq3_delete_lengths[$counter2]));
        push(@final2,$final_line2);
}

for ($counter3 = 0; $counter3 < @seq2_insert_startOnly; $counter3++){
    $final_line3 =  join("\t",($seq2_insert_startOnly[$counter3],$seq2_insert_lengths[$counter3]));
	push(@final3,$final_line3);
}

for ($counter4 = 0; $counter4 < @seq2_delete_startOnly; $counter4++){
        $final_line4 =  join("\t",($seq2_delete_startOnly[$counter4],$seq2_delete_lengths[$counter4]));
        push(@final4,$final_line4);
}
		
for ($counter5 = 0; $counter5 < @seq1_insert_startOnly; $counter5++){
        $final_line5 =  join("\t",($seq1_insert_startOnly[$counter5],$seq1_insert_lengths[$counter5]));
        push(@final5,$final_line5);
}

for ($counter6 = 0; $counter6 < @seq1_delete_startOnly; $counter6++){
        $final_line6 =  join("\t",($seq1_delete_startOnly[$counter6],$seq1_delete_lengths[$counter6]));
        push(@final6,$final_line6);
}       

# format final output
# # if inserts, increase coords for the sequence inserted, other sequences give coords for 5' and 3' bases flanking the gap
# # for deletes, increase coords for other 2 sequences and the one deleted give coords for 5' and 3' bases flanking the gap

get_final_format(@final5);
get_final_format(@final6);
get_final_format(@final3);
get_final_format(@final4);
get_final_format(@final1);
get_final_format(@final2);

sub get_final_format{
	my (@final) = @_;
	foreach (@final){
		my $event_line = $_;
		my @events = split(/\t/, $event_line);
		my $event_type = $events[10];
		my @name_align1 = split(/:/, $events[1]);
		my @name_align2 = split(/:/, $events[4]);
		my @name_align3 = split(/:/, $events[7]);
		my $seq1_event_start = my $seq1_event_end = my $seq2_event_start = my $seq2_event_end = my $seq3_event_start = my $seq3_event_end = 0;
		my $final_event_line = "";	
		# seq1_insert
		if ($event_type =~ m/$ingroup1/ && $event_type =~ m/insert/){
			# only increase coord for human
			# remember that other two sequnences, the gap spans (coord - 1) --> coord
			$seq1_event_start = ($events[2]);
			$seq1_event_end = ($events[2]+$events[11]-1);
			$seq2_event_start = ($events[5]-1);
			$seq2_event_end = ($events[5]);
			$seq3_event_start = ($events[8]-1);
			$seq3_event_end = ($events[8]);
			$final_event_line = join("\t",($events[0],$event_type,$events[11],$name_align1[0],$seq1_event_start,$seq1_event_end,$name_align1[1],$events[3],$name_align2[0],$seq2_event_start,$seq2_event_end,$name_align2[1],$events[6],$name_align3[0],$seq3_event_start,$seq3_event_end,$name_align3[1],$events[9]));
		}
		# seq1_delete
		elsif ($event_type =~ m/$ingroup1/ && $event_type =~ m/delete/){
			# only increase coords for seq2 and seq3
			# remember for seq1, the gap spans (coord - 1) --> coord
			$seq1_event_start = ($events[2]-1);
			$seq1_event_end = ($events[2]);
                        $seq2_event_start = ($events[5]);
                        $seq2_event_end = ($events[5]+$events[11]-1);
                        $seq3_event_start = ($events[8]);
                        $seq3_event_end = ($events[8]+$events[11]-1);
			$final_event_line = join("\t",($events[0],$event_type,$events[11],$name_align1[0],$seq1_event_start,$seq1_event_end,$name_align1[1],$events[3],$name_align2[0],$seq2_event_start,$seq2_event_end,$name_align2[1],$events[6],$name_align3[0],$seq3_event_start,$seq3_event_end,$name_align3[1],$events[9]));
		}
		# seq2_insert
		elsif ($event_type =~ m/$ingroup2/ && $event_type =~ m/insert/){	
			# only increase coords for seq2 
			# remember that other two sequnences, the gap spans (coord - 1) --> coord
                        $seq1_event_start = ($events[2]-1);
                        $seq1_event_end = ($events[2]);
			$seq2_event_start = ($events[5]);
                        $seq2_event_end = ($events[5]+$events[11]-1);
                        $seq3_event_start = ($events[8]-1);
			$seq3_event_end = ($events[8]);			
			$final_event_line = join("\t",($events[0],$event_type,$events[11],$name_align1[0],$seq1_event_start,$seq1_event_end,$name_align1[1],$events[3],$name_align2[0],$seq2_event_start,$seq2_event_end,$name_align2[1],$events[6],$name_align3[0],$seq3_event_start,$seq3_event_end,$name_align3[1],$events[9]));
		}
		# seq2_delete
		elsif ($event_type =~ m/$ingroup2/ && $event_type =~ m/delete/){
			# only increase coords for seq1 and seq3
			# remember for seq2, the gap spans (coord - 1) --> coord
                        $seq1_event_start = ($events[2]);
			$seq1_event_end = ($events[2]+$events[11]-1);	
                        $seq2_event_start = ($events[5]-1);
	                $seq2_event_end = ($events[5]);
                        $seq3_event_start = ($events[8]);
                        $seq3_event_end = ($events[8]+$events[11]-1);
			$final_event_line = join("\t",($events[0],$event_type,$events[11],$name_align1[0],$seq1_event_start,$seq1_event_end,$name_align1[1],$events[3],$name_align2[0],$seq2_event_start,$seq2_event_end,$name_align2[1],$events[6],$name_align3[0],$seq3_event_start,$seq3_event_end,$name_align3[1],$events[9]));
		}	
		# start testing w/seq3_insert
		elsif ($event_type =~ m/$outgroup/ && $event_type =~ m/insert/){
			# only increase coord for rheMac
			# remember that other two sequnences, the gap spans (coord - 1) --> coord
			$seq1_event_start = ($events[2]-1);
			$seq1_event_end = ($events[2]);
			$seq2_event_start = ($events[5]-1);
			$seq2_event_end = ($events[5]);
			$seq3_event_start = ($events[8]);
			$seq3_event_end = ($events[8]+$events[11]-1);
			$final_event_line = join("\t",($events[0],$event_type,$events[11],$name_align1[0],$seq1_event_start,$seq1_event_end,$name_align1[1],$events[3],$name_align2[0],$seq2_event_start,$seq2_event_end,$name_align2[1],$events[6],$name_align3[0],$seq3_event_start,$seq3_event_end,$name_align3[1],$events[9]));
		}
		# seq3_delete
		elsif ($event_type =~ m/$outgroup/ && $event_type =~ m/delete/){
			# only increase coords for seq1 and seq2
			# remember for seq3, the gap spans (coord - 1) --> coord
			$seq1_event_start = ($events[2]);
			$seq1_event_end = ($events[2]+$events[11]-1);
			$seq2_event_start = ($events[5]);
			$seq2_event_end = ($events[5]+$events[11]-1);
			$seq3_event_start = ($events[8]-1);
			$seq3_event_end = ($events[8]);
			$final_event_line = join("\t",($events[0],$event_type,$events[11],$name_align1[0],$seq1_event_start,$seq1_event_end,$name_align1[1],$events[3],$name_align2[0],$seq2_event_start,$seq2_event_end,$name_align2[1],$events[6],$name_align3[0],$seq3_event_start,$seq3_event_end,$name_align3[1],$events[9]));

		}
		
		print OFILE2 "$final_event_line\n";
	}
}
close OFILE2;
