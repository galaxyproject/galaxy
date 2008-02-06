How to prepare NCBI taxonomy for Galaxy Metagenomic Toolkit
-----------------------------------------------------------

1. run runTest.sh
   If this script produces NO messages -> everything is OK
   
2. run processRaxonomy.sh
   This script does several things:
   - downloads taxonomy dump tarball from NCBI ftp site
   - downloads very large gi2taxId files for nucleotide and protein entries of GenBank
   - runs a series of 3 python scripts on these files
   - creates a sqlite database called taxonomy.db (you can use sqlite to explore this database)
   - this database is used by /tools/metag/tax.py tool to convert gi's into full taxonomic representation
   
3. move taxonomy.db into /static/taxonomy/

Taxonomy ranks
--------------

These scripts consider the following taxonomic ranks:

 1      root
 2      superkingdom
 3      kingdom
 4      subkingdom
 5      superphylum
 6      phylum
 7      subphylum
 8      superclass
 9      class
10      subclass
11      superorder
12      order
13      suborder
14      superfamily
15      family
16      subfamily
17      tribe
18      subtribe
19      genus
20      subgenus
21      species
22      subspecies

Problems?
---------
   E-mail to anton@bx.psu.edu
   

