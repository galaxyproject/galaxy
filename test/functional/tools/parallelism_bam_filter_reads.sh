#!/bin/bash
ln -s $1 input.bam
samtools index input.bam
#ln -s $2 input.bam.bai
regions_arg=""
if [ -f regions.bed ]; then
    regions_arg="-L regions.bed"
fi
samtools view -hbq 40 input.bam $regions_arg -o $3

