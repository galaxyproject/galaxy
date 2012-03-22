#!/usr/bin/env bash

input_file="$1"
output_file="$2"
chromInfo_file="$3"
chrom="$4"
score_col="$5"
hilbert_curve_level="$6"
summarization_mode="$7"
chrom_col="$8"
start_col="$9"
end_col="${10}"
strand_col="${11}"

## use first sequence if chrom filed is empty
if [ -z "$chrom" ]; then
    chrom=$( head -n 1 "$input_file" | cut -f$chrom_col )
fi

## get sequence length 
if [ ! -r "$chromInfo_file" ]; then
    echo "Unable to read chromInfo_file $chromInfo_file" 1>&2
    exit 1
fi

chrom_len=$( awk '$1 == chrom {print $2}' chrom=$chrom $chromInfo_file )

## error if we can't find the chrom_len
if [ -z "$chrom_len" ]; then
    echo "Can't find length for sequence \"$chrom\" in chromInfo_file $chromInfo_file" 1>&2
    exit 1
fi

## make sure chrom_len is positive
if [ $chrom_len -le 0 ]; then
    echo "sequence \"$chrom\" length $chrom_len <= 0" 1>&2
    exit 1
fi

## modify R script depending on the inclusion of a score column, strand information
input_cols="\$${start_col}, \$${end_col}"
col_types='beg=0, end=0, strand=""'

# if strand_col == 0 (strandCol metadata is not set), assume everything's on the plus strand
if [ $strand_col -ne 0 ]; then
    input_cols="${input_cols}, \$${strand_col}"
else
    input_cols="${input_cols}, \\\"+\\\""
fi

# set plot value (either from data or use a constant value)
if [ $score_col -eq -1 ]; then
    value=1
else
    input_cols="${input_cols}, \$${score_col}"
    col_types="${col_types}, score=0"
    value='chunk$score[i]'
fi

R --vanilla &> /dev/null <<endOfCode
library(HilbertVis);

chrom_len <- ${chrom_len};
chunk_size <- 1000;
interval_count <- 0;
invalid_strand <- 0;

awk_cmd <- paste(
  "awk 'BEGIN{FS=\"\t\";OFS=\"\t\"}",
    "\$${chrom_col} == \"${chrom}\"",
      "{print ${input_cols}}' ${input_file}"
);

col_types <- list(${col_types});
vec <- vector(mode="numeric", length=chrom_len);
conn <- pipe(description=awk_cmd, open="r");

repeat {
  chunk <- scan(file=conn, what=col_types, sep="\t", nlines=chunk_size, quiet=TRUE);

  if ((rows <- length(chunk\$beg)) == 0)
        break;

  interval_count <- interval_count + rows;

  for (i in 1:rows) {
    if (chunk\$strand[i] == '+') {
      start <- chunk\$beg[i] + 1;
      stop <- chunk\$end[i];
    } else if (chunk\$strand[i] == '-') {
      start <- chrom_len - chunk\$end[i] - 1;
      stop <- chrom_len - chunk\$beg[i];
    } else {
      invalid_strand <- invalid_strand + 1;
      interval_count <- interval_count - 1;
      next;
    }
    vec[start:stop] <- ${value};
  }
}

close(conn);

hMat <- hilbertImage(vec, level=$hilbert_curve_level, mode="$summarization_mode");
pdf(file="$output_file", onefile=TRUE, width=8, height=10.5, paper="letter");
showHilbertImage(hMat);
dev.off();
endOfCode

