
HELP
====

**What to do if I have a problem?**

E-mail us at `galaxy@bx.psu.edu`__

.. __: mailto:galaxy@bx.psu.edu

-----

**What do I do first?**

To start your Galaxy session you first need to initialize history by adding some data. You can do this by using *Data* tool on the laft pane of the Galaxy window.

Once you have at least one item in the history, you will be able to run appropriate tools.

-----

**Datatypes**

Galaxy supports the following datatypes:

 * text - any text file
 * tabular - tab delimited text
 * interval - tab delimited file containing information about genome features
 * BED - a special case of the interval type
 * FASTA - nucleotide or protein sequences
 * AXT - blastZ-style pairwise alignments
 * MAF - TBA and multiZ multiple alignments

-----

**What is the difference between Interval and BED?**

`BED format`__ always contains *chromosome*, *start*, and *end* as the first three fields. Interval is more generic and does not require these fields to be in any strict order.  Here is the formal description of interval format used in Galaxy:

.. __: http://genome.ucsc.edu/goldenPath/help/customTrack.html#BED

- Tab delimited format
- File must start with definition line in the following format (columns may be in any order).::

    #CHROM START END STRAND

- CHROM - The name of the chromosome (e.g. chr3, chrY, chr2_random) or contig (e.g. ctgY1).
- START - The starting position of the feature in the chromosome or contig. The first base in a chromosome is numbered 0.
- END - The ending position of the feature in the chromosome or contig. The chromEnd base is not included in the display of the feature. For example, the first 100 bases of a chromosome are defined as chromStart=0, chromEnd=100, and span the bases numbered 0-99.
- STRAND - Defines the strand - either '+' or '-'.
- Example.::
    
    #CHROM START END   STRAND NAME COMMENT
    chr1   10    100   +      exon myExon
    chrX   1000  10050 -      gene myGene     
 
 