#!/usr/bin/env bash

# Mutate given sequence using Mutatrix and compare it with original sequence using Edlib,
# to see how different it is.

MUTATRIX=~/git/mutatrix/mutatrix
EDLIB=~/git/edlib/build/bin/edlib-aligner

INPUT_SEQUENCE=$1
MUTATION_PERC=$2

OUTPUT_SEQUENCE="mutated_"$MUTATION_PERC"_"$INPUT_SEQUENCE

$MUTATRIX -s $MUTATION_PERC -i $MUTATION_PERC -n 1 -m 0 -M 0 -P mutatrix_output $INPUT_SEQUENCE > mutation.vcf
mv mutatrix_output* $OUTPUT_SEQUENCE

$EDLIB $INPUT_SEQUENCE $OUTPUT_SEQUENCE
