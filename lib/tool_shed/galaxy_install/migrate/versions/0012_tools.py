"""
The following tools have been eliminated from the distribution:

1:  Compute an expression on every row
2:  Correlation for numeric columns
3:  Count GFF Features
4:  Filter on ambiguities in polymorphism datasets
5:  Generate A Matrix for using PC and LDA
6:  Histogram of a numeric column
7:  Perform Linear Discriminant Analysis
8:  Maximal Information-based Nonparametric Exploration
9:  Pearson and apos Correlation between any two numeric columns
10: Convert from pgSnp to gd_snp
11: Draw ROC plot on &#34;Perform LDA&#34; output
12: Scatterplot of two numeric columns
13: snpFreq significant SNPs in case-control data
14: Build custom track for UCSC genome browser
15: VCF to pgSnp

The tools are now available in the repositories respectively:

1:  column_maker
2:  correlation
3:  count_gff_features
4:  dna_filtering
5:  generate_pc_lda_matrix
6:  histogram
7:  lda_analysis
8:  mine
9:  pearson_correlation
10: pgsnp2gd_snp
11: plot_from_lda
12: scatterplot
13: snpfreq
14: ucsc_custom_track
15: vcf2pgsnp

from the main Galaxy tool shed at http://toolshed.g2.bx.psu.edu
and will be installed into your local Galaxy instance at the
location discussed above by running the following command.
"""
from __future__ import print_function


def upgrade( migrate_engine ):
    print(__doc__)


def downgrade( migrate_engine ):
    pass
