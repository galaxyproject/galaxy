"""
The following tools have been eliminated from the distribution:

1:  Profile Annotations for a set of genomic intervals
2:  Polymorphism of the Reads
3:  Coverage of the Reads in wiggle format
4:  Canonical Correlation Analysis
5:  Convert Color Space to Nucleotides
6:  Compute sequence length
7:  Concatenate FASTA alignment by species
8:  Filter sequences by length
9:  FASTA-to-Tabular converter
10: FASTQSOLEXA-to-FASTA-QUAL extracts sequences and quality scores from FASTQSOLEXA data
11: Kernel Canonical Correlation Analysis
12: Kernel Principal Component Analysis
13: Format mapping data as UCSC custom track
14: Megablast compare short reads against htgs, nt, and wgs databases
15: Parse blast XML output
16: Principal Component Analysis
17: RMAP for Solexa Short Reads Alignment
18: RMAPQ for Solexa Short Reads Alignment with Quality Scores
19: Histogram of high quality score reads
20: Build base quality distribution
21: Select high quality segments
22: Tabular-to-FASTA

The tools are now available in the repositories respectively:

1:  annotation_profiler
2:  blat_coverage_report
3:  blat_mapping
4:  canonical_correlation_analysis
5:  convert_solid_color2nuc
6:  fasta_compute_length
7:  fasta_concatenate_by_species
8:  fasta_filter_by_length
9:  fasta_to_tabular
10: fastqsolexa_to_fasta_qual
11: kernel_canonical_correlation_analysis
12: kernel_principal_component_analysis
13: mapping_to_ucsc
14: megablast_wrapper
15: megablast_xml_parser
16: principal_component_analysis
17: rmap
18: rmapq
19: short_reads_figure_high_quality_length
20: short_reads_figure_score
21: short_reads_trim_seq
22: tabular_to_fasta

from the main Galaxy tool shed at http://toolshed.g2.bx.psu.edu
and will be installed into your local Galaxy instance at the 
location discussed above by running the following command.

"""

def upgrade( migrate_engine ):
    print __doc__
    
def downgrade( migrate_engine ):
    pass
