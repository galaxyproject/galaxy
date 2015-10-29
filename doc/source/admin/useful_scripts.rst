Useful Scripts and Administration Tricks
========================================

This page aims to help ease the burden of administration with some easy to use scripts and documentation on what is available for admins to use.

Uploading a directory into a Data Library
-----------------------------------------

Data libraries can really ease the use of Galaxy for your administrators and end users. They provide a form of shared folders that users can copy datasets from into their history.

This script was developed to be as general as possible, allowing you to pipe the output of a much more complex find command to this script, uploading all of the files into a data library:

.. code-block:: console

    $ find /path/to/sequencing-data/ -name '*.fastq' -or -name '*.fa' | python $GALAXY_ROOT/scripts/api/library_upload_dir.py

Find has an extremely expressive command line for selecting specific files that are of interest to you. These will then be recursively uploaded into Galaxy, maintaining the folder hierarchy, a useful feature when moving legacy data into Galaxy. For a complete description of the options of this script, you can run ``python $GALAXY_ROOT/scripts/api/library_upload_dir.py --help``

This tool will not overwrite or re-upload already uploaded datasets. As a result, one can imagine running this on a cron job to keep an "incoming sequencing data" directory synced with a data library.
