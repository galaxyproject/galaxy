"""
The following tools have been eliminated from the distribution:

1. Analyze Covariates
2. Base Coverage of all intervals
3. Perform Best-subsets Regression
4. Cluster
5. Complement intervals of a dataset
6. Compute q-values based on multiple simultaneous tests p-values
7. Concatenate two datasets into one dataset
8. Count Covariates on BAM files
9. Coverage of a set of intervals on second set of intervals
10. Depth of Coverage on BAM files
11. Feature coverage
12. Fetch closest non-overlapping feature for every interval
13. Get flanks - returns flanking region/s for every gene
14. Estimate Indel Rates for 3-way alignments
15. Fetch Indels from pairwise alignments
16. Indel Realigner - perform local realignment
17. Intersect the intervals of two datasets
18. Join the intervals of two datasets side-by-side
19. Perform Linear Regression
20. Perform Logistic Regression with vif
21. Mask CpG/non-CpG sites from MAF file
22. Merge the overlapping intervals of a dataset
23. Extract Orthologous Microsatellites from pair-wise alignments
24. Estimate microsatellite mutability by specified attributes
25. Compute partial R square
26. Print Reads from BAM files
27. Filter nucleotides based on quality scores
28. Compute RCVE
29. Realigner Target Creator for use in local realignment
30. Estimate substitution rates for non-coding regions
31. Fetch substitutions from pairwise alignments
32. Subtract the intervals of two datasets
33. Subtract Whole Dataset from another dataset
34. Table Recalibration on BAM files
35. Arithmetic Operations on tables
36. Unified Genotyper SNP and indel caller
37. Variant Annotator
38. Apply Variant Recalibration
39. Combine Variants
40. Eval Variants
41. Variant Filtration on VCF files
42. Variant Recalibrator
43. Select Variants from VCF files
44. Validate Variants
45. Assign weighted-average of the values of features overlapping an interval
46. Make windows

The tools are now available in the repositories respectively:

1. analyze_covariates
2. basecoverage
3. best_regression_subsets
4. cluster
5. complement
6. compute_q_values
7. concat
8. count_covariates
9. coverage
10. depth_of_coverage
11. featurecounter
12. flanking_features
13. get_flanks
14. getindelrates_3way
15. getindels_2way
16. indel_realigner
17. intersect
18. join
19. linear_regression
20. logistic_regression_vif
21. maf_cpg_filter
22. merge
23. microsats_alignment_level
24. microsats_mutability
25. partialr_square
26. print_reads
27. quality_filter
28. rcve
29. realigner_target_creator
30. substitution_rates
31. substitutions
32. subtract
33. subtract_query
34. table_recalibration
35. tables_arithmetic_operations
36. unified_genotyper
37. variant_annotator
38. variant_apply_recalibration
39. variant_combine
40. variant_eval
41. variant_filtration
42. variant_recalibrator
43. variant_select
44. variants_validate
45. weightedaverage
46. windowsplitter

from the main Galaxy tool shed at http://toolshed.g2.bx.psu.edu
and will be installed into your local Galaxy instance at the
location discussed above by running the following command.
"""
from __future__ import print_function


def upgrade( migrate_engine ):
    print(__doc__)


def downgrade( migrate_engine ):
    pass
