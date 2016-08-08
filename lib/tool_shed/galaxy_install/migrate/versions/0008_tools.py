"""
The following tools have been eliminated from the distribution:

1:  BAM-to-SAM converts BAM format to SAM format
2:  Categorize Elements satisfying criteria
3:  Compute Motif Frequencies For All Motifs motif by motif
4:  Compute Motif Frequencies in indel flanking regions
5:  CTD analysis of chemicals, diseases, or genes
6:  Cuffcompare
7:  Cuffdiff
8:  Cufflinks
9:  Cuffmerge
10: Delete Overlapping Indels from a chromosome indels file
11: Separate pgSnp alleles into columns
12: Draw Stacked Bar Plots for different categories and different criteria
13: Length Distribution chart
14: FASTA Width formatter
15: RNA/DNA converter
16: Draw quality score boxplot
17: Quality format converter (ASCII-Numeric)
18: Filter by quality
19: FASTQ to FASTA converter
20: Remove sequencing artifacts
21: Barcode Splitter
22: Clip adapter sequences
23: Collapse sequences
24: Draw nucleotides distribution chart
25: Compute quality statistics
26: Rename sequences
27: Reverse- Complement
28: Trim sequences
29: FunDO human genes associated with disease terms
30: HVIS visualization of genomic data with the Hilbert curve
31: Fetch Indels from 3-way alignments
32: Identify microsatellite births and deaths
33: Extract orthologous microsatellites for multiple (>2) species alignments
34: Mutate Codons with SNPs
35: Pileup-to-Interval condenses pileup format into ranges of bases
36: Filter pileup on coverage and SNPs
37: Filter SAM on bitwise flag values
38: Merge BAM Files merges BAM files together
39: Generate pileup from BAM dataset
40: SAM-to-BAM converts SAM format to BAM format
41: Convert SAM to interval
42: flagstat provides simple stats on BAM files
43: MPileup SNP and indel caller
44: rmdup remove PCR duplicates
45: Slice BAM by provided regions
46: Split paired end reads
47: T Test for Two Samples
48: Plotting tool for multiple series and graph types.

The tools are now available in the repositories respectively:

1:  bam_to_sam
2:  categorize_elements_satisfying_criteria
3:  compute_motif_frequencies_for_all_motifs
4:  compute_motifs_frequency
5:  ctd_batch
6:  cuffcompare
7:  cuffdiff
8:  cufflinks
9:  cuffmerge
10: delete_overlapping_indels
11: divide_pg_snp
12: draw_stacked_barplots
13: fasta_clipping_histogram
14: fasta_formatter
15: fasta_nucleotide_changer
16: fastq_quality_boxplot
17: fastq_quality_converter
18: fastq_quality_filter
19: fastq_to_fasta
20: fastx_artifacts_filter
21: fastx_barcode_splitter
22: fastx_clipper
23: fastx_collapser
24: fastx_nucleotides_distribution
25: fastx_quality_statistics
26: fastx_renamer
27: fastx_reverse_complement
28: fastx_trimmer
29: hgv_fundo
30: hgv_hilbertvis
31: indels_3way
32: microsatellite_birthdeath
33: multispecies_orthologous_microsats
34: mutate_snp_codon
35: pileup_interval
36: pileup_parser
37: sam_bitwise_flag_filter
38: sam_merge
39: sam_pileup
40: sam_to_bam
41: sam2interval
42: samtools_flagstat
43: samtools_mpileup
44: samtools_rmdup
45: samtools_slice_bam
46: split_paired_reads
47: t_test_two_samples
48: xy_plot

from the main Galaxy tool shed at http://toolshed.g2.bx.psu.edu
and will be installed into your local Galaxy instance at the
location discussed above by running the following command.
"""
from __future__ import print_function


def upgrade( migrate_engine ):
    print(__doc__)


def downgrade( migrate_engine ):
    pass
