"""
The following tools have been eliminated from the distribution:

1:  BAM-to-SAM converts BAM format to SAM format
2:  Categorize Elements satisfying criteria
3:  Compute Motif Frequencies For All Motifs motif by motif
4:  Compute Motif Frequencies in indel flanking regions
5:  CTD analysis of chemicals, diseases, or genes
6:  Delete Overlapping Indels from a chromosome indels file
7:  Separate pgSnp alleles into columns
8:  Draw Stacked Bar Plots for different categories and different criteria
9:  Length Distribution chart
10: FASTA Width formatter
11: RNA/DNA converter
12: Draw quality score boxplot
13: Quality format converter (ASCII-Numeric)
14: Filter by quality
15: FASTQ to FASTA converter
16: Remove sequencing artifacts
17: Barcode Splitter
18: Clip adapter sequences
19: Collapse sequences
20: Draw nucleotides distribution chart
21: Compute quality statistics
22: Rename sequences
23: Reverse- Complement
24: Trim sequences
25: FunDO human genes associated with disease terms
26: HVIS visualization of genomic data with the Hilbert curve
27: Fetch Indels from 3-way alignments
28: Identify microsatellite births and deaths
29: Extract orthologous microsatellites for multiple (>2) species alignments
30: Mutate Codons with SNPs
31: Pileup-to-Interval condenses pileup format into ranges of bases
32: Filter pileup on coverage and SNPs
33: Filter SAM on bitwise flag values
34: Merge BAM Files merges BAM files together
35: Generate pileup from BAM dataset
36: SAM-to-BAM converts SAM format to BAM format
37: Convert SAM to interval
38: flagstat provides simple stats on BAM files
39: MPileup SNP and indel caller
40: rmdup remove PCR duplicates
41: Slice BAM by provided regions
42: Split paired end reads
43: T Test for Two Samples
44: Plotting tool for multiple series and graph types.

The tools are now available in the repositories respectively:

1:  bam_to_sam
2:  categorize_elements_satisfying_criteria
3:  compute_motif_frequencies_for_all_motifs
4:  compute_motifs_frequency
5:  ctd_batch
6:  delete_overlapping_indels
7:  divide_pg_snp
8:  draw_stacked_barplots
9:  fasta_clipping_histogram
10: fasta_formatter
11: fasta_nucleotide_changer
12: fastq_quality_boxplot
13: fastq_quality_converter
14: fastq_quality_filter
15: fastq_to_fasta
16: fastx_artifacts_filter
17: fastx_barcode_splitter
18: fastx_clipper
19: fastx_collapser
20: fastx_nucleotides_distribution
21: fastx_quality_statistics
22: fastx_renamer
23: fastx_reverse_complement
24: fastx_trimmer
25: hgv_fundo
26: hgv_hilbertvis
27: indels_3way
28: microsatellite_birthdeath
29: multispecies_orthologous_microsats
30: mutate_snp_codon
31: pileup_interval
32: pileup_parser
33: sam_bitwise_flag_filter
34: sam_merge
35: sam_pileup
36: sam_to_bam
37: sam2interval
38: samtools_flagstat
39: samtools_mpileup
40: samtools_rmdup
41: samtools_slice_bam
42: split_paired_reads
43: t_test_two_samples
44: xy_plot

from the main Galaxy tool shed at http://toolshed.g2.bx.psu.edu
and will be installed into your local Galaxy instance at the 
location discussed above by running the following command.

"""

def upgrade( migrate_engine ):
    print __doc__
    
def downgrade( migrate_engine ):
    pass
