"""
The following tools have been eliminated from the distribution:

1:  Bowtie2
2:  Control-based ChIP-seq Analysis Tool
3:  ClustalW multiple sequence alignment program for DNA or proteins
4:  Compute P-values and Correlation Coefficients for Feature Occurrences
5:  Compute P-values and Correlation Coefficients for Occurrences of Two Set of Features
6:  Compute P-values and Second Moments for Feature Occurrences
7:  Compute P-values and Max Variances for Feature Occurrences
8:  Wavelet variance using Discrete Wavelet Transfoms
9:  Quantify the abundances of a set of target sequences from sampled subsequences
10: Read QC reports using FastQC
11: Combine FASTA and QUAL into FASTQ.
12: Filter FASTQ reads by quality score and length
13: Convert between various FASTQ quality formats.
14: Manipulate FASTQ reads on various attributes.
15: FASTQ Masker by quality score
16: FASTQ de-interlacer on paired end reads.
17: FASTQ interlacer on paired end reads
18: FASTQ joiner on paired end reads
19: FASTQ splitter on joined paired end reads
20: FASTQ Summary Statistics by column
21: FASTQ to FASTA converter
22: FASTQ to Tabular converter
23: FASTQ Trimmer by quality
24: FASTQ Quality Trimmer by sliding window
25: Filter Combined Transcripts
26: find_diag_hits
27: Call SNPS with Freebayes
28: Fetch taxonomic representation
29: GMAJ Multiple Alignment Viewer
30: Find lowest diagnostic rank
31: Model-based Analysis of ChIP-Seq
32: Poisson two-sample test
33: Statistical approach for the Identification of ChIP-Enriched Regions
34: Draw phylogeny
35: Summarize taxonomy
36: Tabular to FASTQ converter
37: Find splice junctions using RNA-seq data
38: Gapped-read mapper for RNA-seq data
39: Annotate a VCF file (dbSNP, hapmap)
40: Extract reads from a specified region
41: Filter a VCF file
42: Generate the intersection of two VCF files
43: Sequence Logo generator for fasta (eg Clustal alignments)

The tools are now available in the repositories respectively:

1:  bowtie2
2:  ccat
3:  clustalw
4:  dwt_cor_ava_perclass
5:  dwt_cor_avb_all
6:  dwt_ivc_all
7:  dwt_var_perclass
8:  dwt_var_perfeature
9:  express
10: fastqc
11: fastq_combiner
12: fastq_filter
13: fastq_groomer
14: fastq_manipulation
15: fastq_masker_by_quality
16: fastq_paired_end_deinterlacer
17: fastq_paired_end_interlacer
18: fastq_paired_end_joiner
19: fastq_paired_end_splitter
20: fastq_stats
21: fastqtofasta
22: fastq_to_tabular
23: fastq_trimmer
24: fastq_trimmer_by_quality
25: filter_transcripts_via_tracking
26: find_diag_hits
27: freebayes_wrapper
28: gi2taxonomy
29: gmaj
30: lca_wrapper
31: macs
32: poisson2test
33: sicer
34: t2ps
35: t2t_report
36: tabular_to_fastq
37: tophat
38: tophat2
39: vcf_annotate
40: vcf_extract
41: vcf_filter
42: vcf_intersect
43: weblogo3

from the main Galaxy tool shed at http://toolshed.g2.bx.psu.edu
and will be installed into your local Galaxy instance at the 
location discussed above by running the following command.
"""

def upgrade( migrate_engine ):
    print __doc__
    
def downgrade( migrate_engine ):
    pass
