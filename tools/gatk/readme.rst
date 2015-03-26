Galaxy wrapper for GATK2
========================

This wrapper is copyright 2013 by Björn Grüning, Jim Johnson & the Galaxy Team.

The Genome Analysis Toolkit or GATK is a software package developed at the 
Broad Institute to analyse next-generation resequencing data. The toolkit offers
a wide variety of tools, with a primary focus on variant discovery and 
genotyping as well as strong emphasis on data quality assurance. Its robust 
architecture, powerful processing engine and high-performance computing features
make it capable of taking on projects of any size.

http://www.broadinstitute.org/gatk
http://www.broadinstitute.org/gatk/about/citing-gatk

GATK is Free for academics, and fee for commercial use. Please study the GATK licensing website:
http://www.broadinstitute.org/gatk/about/#licensing


Installation
============

The recommended installation is by means of the toolshed_.

.. _toolshed: http://toolshed.g2.bx.psu.edu/view/iuc/gatk2

Galaxy should be able to install samtools dependencies automatically
for you. GATK2, and its new licence model, does not allow us to distribute the GATK binaries.
As a consequence you need to install GATK2 by your own, please see the GATK website for more information:

http://www.broadinstitute.org/gatk/download

Once you have installed GATK2, you need to edit the env.sh files that are installed together with the wrappers.
You must edit the GATK2_PATH environment variable in the file:

<tool_dependency_dir>/environment_settings/GATK2_PATH/iuc/gatk2/<hash_string>/env.sh

to point to the folder where you have installed GATK2.

Optionally, you may also want to edit the GATK2_SITE_OPTIONS environment variable in the file:

<tool_dependency_dir>/environment_settings/GATK2_SITE_OPTIONS/iuc/gatk2/<hash_string>/env.sh

to deactivate the 'call home feature' of GATK with something like:

GATK2_SITE_OPTIONS='-et NO_ET -K /data/gatk2_key_file'

GATK2_SITE_OPTIONS can be also used to insert other specific options into every GATK2 wrapper
at runtime, without changing the actual wrapper.

Read more about the "Phone Home" problem at:
http://www.broadinstitute.org/gatk/guide/article?id=1250

Optionally, you may also want to add some commands to be executed before GATK (e.g. to load modules) to the file:

<tool_dependency_dir>/gatk2/default/env.sh

Finally, you should fill in additional information about your genomes and 
annotations in the gatk2_picard_index.loc and gatk2_annotations.txt. 
You can find them in the tool-data/ Galaxy directory.


History
=======

v0.1 - Initial public release


Licence (MIT)
=============

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
