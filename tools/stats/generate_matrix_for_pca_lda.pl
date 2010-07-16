#!/usr/bin/perl -w

use strict;
use warnings;

my $Input_Matrix = $ARGV[0];
my $Input_Label = $ARGV[1];

my %Hash_X = ();
my %Hash_Y = ();
my $My_Num_X = 0;
my $My_Num_Y = 0;

open (OUT, "> $ARGV[2]");

open (LABEL, "< $Input_Label")     ||
	die "Sorry, I couldn't open the escape.txt for clone: $!\n";

my $Label_Index = 0;
my $X_Label;
my $input_Label;
while (defined($input_Label = <LABEL>)){
	chomp($input_Label);
	my @cArray_Label = $input_Label =~ /(\S+)\s*/g;
	if ($input_Label =~ /\w/){
		if ($Label_Index == 0){
			$Hash_X{$cArray_Label[0]} = $cArray_Label[1];
			$X_Label = $cArray_Label[1];
			$Label_Index = 1;
		}else{
			if ($cArray_Label[1] eq $X_Label){
				$Hash_X{$cArray_Label[0]} = $cArray_Label[1];
			}else{
				$Hash_Y{$cArray_Label[0]} = $cArray_Label[1];
			}
		}
	}
}
close(LABEL);

open (MATRIX, "< $Input_Matrix")     ||
	die "Sorry, I couldn't open the escape.txt for clone: $!\n";

my %Hash_Matrix = ();
my %Hash_Features = ();
my @cArray_Features = ();

my %Hash_Sum = ();
my $Matrix_Index = 0;
my $input_Matrix;
while (defined($input_Matrix = <MATRIX>)){
	chomp($input_Matrix);
	my @cArray_Matrix = $input_Matrix =~ /(\S+)\s*/g;
	if ($input_Matrix =~ /\w/){
		if ($Matrix_Index == 0){
			@cArray_Features = @cArray_Matrix;
			my $Temp_Num_Array = scalar(@cArray_Matrix);
			my $Temp_Index = 0;
			for(;$Temp_Index < $Temp_Num_Array; $Temp_Index++){
				$Hash_Features{$cArray_Matrix[$Temp_Index]} = "BOL";	
				$Hash_Sum{$cArray_Matrix[$Temp_Index]} = 0;	
			}
			$Matrix_Index = 1;
		}else{
			$Hash_Matrix{$cArray_Matrix[0]} = $input_Matrix;
		}
	}
}
close(MATRIX);	

my $Trace_Key;

foreach $Trace_Key (sort {$a cmp $b} keys %Hash_X){
	my @cArray_Trace_X = $Hash_Matrix{$Trace_Key} =~ /(\S+)\s*/g;
	my $Num_Array_Feature_X = scalar(@cArray_Features);
	my $Index_Feature_X = 0;
	for(;$Index_Feature_X < $Num_Array_Feature_X; $Index_Feature_X++){
		if ($Hash_Features{$cArray_Features[$Index_Feature_X]} eq "BOL"){
			$Hash_Features{$cArray_Features[$Index_Feature_X]} = $cArray_Trace_X[$Index_Feature_X + 1];
		}else{
			$Hash_Features{$cArray_Features[$Index_Feature_X]} = $Hash_Features{$cArray_Features[$Index_Feature_X]} . "\t" . $cArray_Trace_X[$Index_Feature_X + 1];
		}

		$Hash_Sum{$cArray_Features[$Index_Feature_X]} += $cArray_Trace_X[$Index_Feature_X + 1];
	} 		
	$My_Num_X ++;
}

my $Append_Key;
foreach $Append_Key (keys %Hash_Features){
	$Hash_Features{$Append_Key} = $Hash_Features{$Append_Key} . "\t" . $Hash_Sum{$Append_Key};
	$Hash_Sum{$Append_Key} = 0;
}

foreach $Trace_Key (sort {$a cmp $b} keys %Hash_Y){
	my @cArray_Trace_Y = $Hash_Matrix{$Trace_Key} =~ /(\S+)\s*/g;
	my $Num_Array_Feature_Y = scalar(@cArray_Features);
	my $Index_Feature_Y = 0;
	for(;$Index_Feature_Y < $Num_Array_Feature_Y; $Index_Feature_Y++){
		if ($Hash_Features{$cArray_Features[$Index_Feature_Y]} eq "BOL"){
			$Hash_Features{$cArray_Features[$Index_Feature_Y]} = $cArray_Trace_Y[$Index_Feature_Y + 1];
		}else{
			$Hash_Features{$cArray_Features[$Index_Feature_Y]} = $Hash_Features{$cArray_Features[$Index_Feature_Y]} . "\t" . $cArray_Trace_Y[$Index_Feature_Y + 1];
		}

		$Hash_Sum{$cArray_Features[$Index_Feature_Y]} += $cArray_Trace_Y[$Index_Feature_Y + 1];
	} 		
	$My_Num_Y ++;
}

foreach $Append_Key (keys %Hash_Features){
	$Hash_Features{$Append_Key} = $Hash_Features{$Append_Key} . "\t" . $Hash_Sum{$Append_Key} . "\t" . "EOL";
}

my $Prt_Key;
print OUT " \t";
foreach $Prt_Key (sort {$a cmp $b} keys %Hash_X){
	print OUT "$Prt_Key \t";
}
print OUT "X(SUM) \t";

foreach $Prt_Key (sort {$a cmp $b} keys %Hash_Y){
	print OUT "$Prt_Key \t";
}
print OUT "Y(SUM) \t";
print OUT "\n";

my $Prt_Index = 0;
my $Prt_Array_Num = scalar (@cArray_Features);
for(;$Prt_Index < $Prt_Array_Num; $Prt_Index++){
	print OUT "$cArray_Features[$Prt_Index] \t$Hash_Features{$cArray_Features[$Prt_Index]}\n";
}

print OUT " \t";
my $My_Label_Index = 0;
for(;$My_Label_Index < $My_Num_X; $My_Label_Index++){
	print OUT "X \t";
}
print OUT " \t";

$My_Label_Index = 0;
for(;$My_Label_Index < $My_Num_Y; $My_Label_Index++){
	print OUT "Y \t";
}
print OUT " \t\n";

close(OUT);
