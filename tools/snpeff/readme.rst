SnpEff wrappers
===============

These are galaxy tools for SnpEff_, a variant annotation and effect prediction tool by Pablo Cingolani.
It annotates and predicts the effects of variants on genes (such as amino acid changes).

.. _SnpEff: http://snpeff.sourceforge.net/


This repository let you automatically install SnpEff and SnpSift.
This will use the default location for genome reference downloads from the ``snpEff.config`` file:

  data_dir = ~/snpEff/data/

You can manually edit the installed ``snpEff.config`` file and change the location, or you can create a symbolic link to the desired data location from ``~/snpEff``.

The genome reference options used by the tools "SnpEff" (snpEff.xml) and "SnpEff Download" (snpEff_download.xml) are taken from the ``tool-data/snpeffect_genomedb.loc`` file.
You can fill this file by running the following command:

  java -jar snpEff.jar databases | tail -n +3 | cut -f 1,2 | awk '{ gsub(/_/, " ", $2); printf "%s\\t%s : %s\\n", $1, $2, $1 }' | sort -k 2 > snpeffect_genomedb.loc

There are 2 datamanagers to download and install prebuilt SnpEff genome databases:

* data_manager_snpeff_databases: generates a list of available SnpEff genome databases into the ``tool-data/snpeff_databases.loc`` file
* data_manager_snpeff_download: downloads a SnpEff genome database selected from ``tool-data/snpeff_databases.loc`` and adds entries to ``snpeff_genomedb.loc``, ``snpeff_regulationdb.loc`` and ``snpeff_annotations.loc``

SnpEff citation: |Cingolani2012program|_.

.. |Cingolani2012program| replace:: Cingolani, P., Platts, A., Wang, L. L., Coon, M., Nguyen, T., Wang, L., Land, S. J., Lu, X., Ruden, D. M. (2012) A program for annotating and predicting the effects of single nucleotide polymorphisms, SnpEff: SNPs in the genome of *Drosophila melanogaster* strain w1118; iso-2; iso-3. *Fly* 6(2):80-92
.. _Cingolani2012program: https://www.landesbioscience.com/journals/fly/article/19695/

SnpSift citation: |Cingolani2012using|_.

.. |Cingolani2012using| replace:: Cingolani, P., Patel, V. M., Coon, M., Nguyen, T., Land, S. J., Ruden, D. M., Lu, X. (2012) Using *Drosophila melanogaster* as a model for genotoxic chemical mutational studies with a new program, SnpSift. *Front. Genet.* 3:35
.. _Cingolani2012using: http://journal.frontiersin.org/Journal/10.3389/fgene.2012.00035/

Wrapper authors: Jim Johnson

