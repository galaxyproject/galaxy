#!/usr/bin/env bash

# Runs performance tests - compares Edlib with other aligners (Parasail, Seqan, Myers).

EDLIB=~/git/edlib/build/bin/edlib-aligner

PARASAIL=~/git/parasail/apps/parasail_aligner
PARASAIL_FLAGS="-t 1 -d -e 1 -o 1 -M 0 -X 1"

# Here I am using Seqan through modified edlib aligner. It can be found in seqan-test branch of edlib repo.
SEQAN=~/git/edlib-seqan/src/aligner

MYERS=~/Dropbox/Mile/SIMD_alignment/Myers/myers_98_martin/myers

TEST_DATA=.

########################## TEST RUNNERS ########################

function edlib {
    mode=$1
    query=$2
    target=$3
    num_tests=$4
    k=$5

    time_sum=0
    for i in $(seq $num_tests); do
        sleep 1
        output=$($EDLIB -m $mode -k $k $query $target)
        time=$(echo "$output" | grep "Cpu time of searching" | cut -d " " -f5)
        score=$(echo "$output" | grep "#0:" | cut -d " " -f2)
        time_sum=$(python -c "print($time_sum + $time)")
        echo ">" "#"$i $score $time
    done
    avg_time=$(python -c "print($time_sum / $num_tests)")
    echo "Edlib:" $avg_time $score
}

function edlib_path {
    mode=$1
    query=$2
    target=$3
    num_tests=$4

    time_sum=0
    for i in $(seq $num_tests); do
        sleep 1
        output=$($EDLIB -m $mode -p -s $query $target)
        time=$(echo "$output" | grep "Cpu time of searching" | cut -d " " -f5)
        time_sum=$(python -c "print($time_sum + $time)")
        echo ">" "#"$i $time
    done
    avg_time=$(python -c "print($time_sum / $num_tests)")
    echo "Edlib (path):" $avg_time
}

function seqan {
    mode=$1
    query=$2
    target=$3
    num_tests=$4

    time_sum=0
    for i in $(seq $num_tests); do
        sleep 1
        output=$($SEQAN -m $mode -t $query $target)
        time=$(echo "$output" | grep "Cpu time of searching" | cut -d " " -f5)
        score=$(($(echo "$output" | grep "Seqan Score:" | cut -d " " -f4) * -1))
        time_sum=$(python -c "print($time_sum + $time)")
        echo ">" "#"$i $score $time
    done
    avg_time=$(python -c "print($time_sum / $num_tests)")
    echo "Seqan:" $avg_time $score
}

function seqan_path {
    mode=$1
    query=$2
    target=$3
    num_tests=$4

    time_sum=0
    for i in $(seq $num_tests); do
        sleep 1
        output=$($SEQAN -m $mode -t -p -s $query $target)
        time=$(echo "$output" | grep "Cpu time of searching" | cut -d " " -f5)
        score=$(($(echo "$output" | grep "Seqan Score:" | cut -d " " -f4) * -1))
        time_sum=$(python -c "print($time_sum + $time)")
        echo ">" "#"$i $score $time
    done
    avg_time=$(python -c "print($time_sum / $num_tests)")
    echo "Seqan (path):" $score $avg_time
}

function parasail {
    query=$1
    target=$2
    num_tests=$3

    time_sum=0
    for i in $(seq $num_tests); do
        sleep 1
        output=$($PARASAIL $PARASAIL_FLAGS -a nw_striped_32 -f $target -q $query)
        time=$(echo "$output" | grep "alignment time" | cut -d ":" -f2 | cut -d " " -f2)
        score=$(($(head -n 1 parasail.csv | cut -d "," -f5) * -1))
        rm parasail.csv
        time_sum=$(python -c "print($time_sum + $time)")
        echo ">" "#"$i $score $time
    done
    avg_time=$(python -c "print($time_sum / $num_tests)")
    echo "Parasail:" $avg_time $score
}

function myers {
    query=$1
    target=$2
    num_tests=$3
    k=$4

    time_sum=0
    for i in $(seq $num_tests); do
        sleep 1
        tail -n +2 $query | tr -d '\n' > queryMyers.fasta
        tail -n +2 $target | tr -d '\n' > targetMyers.fasta
        output=$({ time -p $MYERS $(cat queryMyers.fasta) $k targetMyers.fasta; } 2>&1)
        rm queryMyers.fasta targetMyers.fasta
        time=$(echo "$output" | grep "real" | cut -d " " -f2)
        time_sum=$(python -c "print($time_sum + $time)")
        echo ">" "#"$i $time
    done
    avg_time=$(python -c "print($time_sum / $num_tests)")
    echo "Myers:" $avg_time

}


############################ TESTS #############################


#Enterobacteria
echo -e "\nEnterobacteria, NW"
target=$TEST_DATA/Enterobacteria_Phage_1/Enterobacteria_phage_1.fasta
for query in $(ls $TEST_DATA/Enterobacteria_Phage_1/mutated_*_perc.fasta); do
    echo $query

    edlib NW $query $target 3 -1
    edlib_path NW $query $target 3
    seqan NW $query $target 3
    seqan_path NW $query $target 3
    parasail $query $target 3
done


#E coli and its illumina read, HW
echo -e "\nE coli and its illumina read, HW"
target=$TEST_DATA/E_coli_DH1/e_coli_DH1.fasta
for query in $(ls $TEST_DATA/E_coli_DH1/mason_illumina_read_10kbp/*.fasta); do
    echo $query

    edlib HW $query $target 3 -1
    edlib_path HW $query $target 3
    seqan HW $query $target 3
#    seqan_path HW $query $target 3   # Fails because it allocates too much memory.
done


#E coli and its prefix, SHW
echo -e "\nE coli and its prefix, SHW"
target=$TEST_DATA/E_coli_DH1/e_coli_DH1.fasta
for query in $(ls $TEST_DATA/E_coli_DH1/prefix_10kbp/mutated_*_perc.fasta); do
    echo $query

    edlib SHW $query $target 3 -1
    edlib_path SHW $query $target 3
    seqan SHW $query $target 3
#    seqan_path SHW $query $target 3   # Fails because it allocates too much memory.
done


#Chromosome
echo -e "\nChromosome, NW"
target=$TEST_DATA/Chromosome_2890043_3890042_0/Chromosome_2890043_3890042_0.fasta
for query in $(ls $TEST_DATA/Chromosome_2890043_3890042_0/mutated_*_perc.fasta); do
    echo $query

    edlib NW $query $target 3 -1
    edlib_path NW $query $target 3
    seqan NW $query $target 3
    seqan_path NW $query $target 3
    parasail $query $target 3
done


################### Myers #####################
echo -e "\nMyers"
target=$TEST_DATA/E_coli_DH1/e_coli_DH1.fasta

k=100
for query_file in e_coli_DH1_illumina_1x10000.fasta; do
    query=$TEST_DATA/E_coli_DH1/mason_illumina_read_10kbp/$query_file
    echo $query $k
    edlib HW $query $target 3 $k
    myers $query $target 3 $k
done

k=1000
for query_file in e_coli_DH1_illumina_1x10000.fasta mutated_97_perc.fasta mutated_94_perc.fasta mutated_90_perc.fasta; do
    query=$TEST_DATA/E_coli_DH1/mason_illumina_read_10kbp/$query_file
    echo $query $k
    edlib HW $query $target 3 $k
    myers $query $target 3 $k
done

k=10000
for query in $(ls $TEST_DATA/E_coli_DH1/mason_illumina_read_10kbp/*); do
    echo $query $k
    edlib HW $query $target 3 $k
    myers $query $target 3 $k
done
