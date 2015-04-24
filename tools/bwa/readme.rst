BWA-MEM wrapper
===============

This is a wrapper for BWA_, a software package for mapping low-divergent sequences against a large reference genome. This wrapper supports only the latest algorithm, BWA-MEM, which is generally recommended for high-quality queries as it is faster and more accurate. BWA-MEM also has better performance than BWA-backtrack for 70-100bp Illumina reads. 

.. _BWA: http://bio-bwa.sourceforge.net/

If you need a wrapper for the old BWA-backtrack algorithm, you may install http://toolshed.g2.bx.psu.edu/view/devteam/bwa_wrappers repository.

Configuration
-------------

bwa_mem tool may be configured to use more than one CPU core by selecting an appropriate destination for this tool in Galaxy job_conf.xml file (see https://wiki.galaxyproject.org/Admin/Config/Jobs and https://wiki.galaxyproject.org/Admin/Config/Performance/Cluster ).

If you are using Galaxy release_2013.11.04 or later, this tool will automatically use the number of CPU cores allocated by the job runner according to the configuration of the destination selected for this tool.

If instead you are using an older Galaxy release, you should also add a line

  GALAXY_SLOTS=N; export GALAXY_SLOTS

(where N is the number of CPU cores allocated by the job runner for this tool) to the file

  <tool_dependencies_dir>/bwa/0.7.7/crs4/bwa_mem/<hash_string>/env.sh

Version history
---------------

- Release 1 (bwa_mem 0.8.0): Rewrite of param handling. interPairEnd param moved to "paired" section. Add param for '-a' option. Remove basic parallelism tag, which does not work with multiple inputs (thanks Björn Grüning for the notice). Simplify Python code.
- Release 0 (bwa_mem 0.7.7): Initial release in the Tool Shed. This is a fork of http://toolshed.g2.bx.psu.edu/view/yufei-luo/bwa_0_7_5 repository with the following changes: Remove .loc file, only .loc.sample should be included. Fix bwa_index.loc.sample file to contain only comments. Add suppressHeader param as in bwa_wrappers. Use $GALAXY_SLOTS environment variable when available. Add <version_command> and <help>. Remove unused import. Fix spacing and typos. Use new recommended citation. Add tool_dependencies.xml . Rename to bwa_mem. Remove definitively colorspace support. Use optparse instead of argparse since Galaxy still supports Python 2.6 . Add COPYING and readme.rst files.

Development
-----------

Development is hosted at https://bitbucket.org/crs4/orione-tools . Contributions and bug reports are very welcome!
