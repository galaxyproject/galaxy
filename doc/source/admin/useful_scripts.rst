Scripts & Tricks
================

This page aims to help ease the burden of administration with some easy to use scripts and documentation on what is available for admins to use.

Uploading a directory into a Data Library
-----------------------------------------

Data libraries can really ease the use of Galaxy for your administrators and end users. They provide a form of shared folders that users can copy datasets from into their history.

This script was developed to be as general as possible, allowing you to pipe the output of a much more complex find command to this script, uploading all of the files into a data library:

.. code-block:: console

    $ find /path/to/sequencing-data/ -name '*.fastq' -or -name '*.fa' | python $GALAXY_ROOT/scripts/api/library_upload_dir.py

Find has an extremely expressive command line for selecting specific files that are of interest to you. These will then be recursively uploaded into Galaxy, maintaining the folder hierarchy, a useful feature when moving legacy data into Galaxy. For a complete description of the options of this script, you can run ``python $GALAXY_ROOT/scripts/api/library_upload_dir.py --help``

This tool will not overwrite or re-upload already uploaded datasets. As a result, one can imagine running this on a cron job to keep an "incoming sequencing data" directory synced with a data library.

Deleting unused histories
-------------------------

Galaxy accommodates anonymous usage by creating a default history. Often, such histories will remain unused, as a result of which the database may contain a considerable number of anonymous histories along with associated records, which serve no purpose. Deleting such records will declutter the database and free up space. However, given that a row in the history table may be referenced from multiple other tables, manually deleting such data may leave the database in an inconsistent state. Furthermore, whereas some types of data associated with such histories are clearly obsolete and can be safely deleted, others may require preservation for a variety of reasons. 

To safely delete unused histories and their associated records, please use the `prune_history_table` script. Due to the potentially very large size of some of the tables in the database, the script deletes records in batches. The default size is 1000, which means the script will delete up to 1000 histories, plus any associated records in a single batch. The size of the batch is configurable. By default, an anonymous history should be at least a month old to be considered unused. This value is configurable as well.

.. code-block:: console

    $ python  $GALAXY_ROOT/lib/galaxy/model/scripts/prune_history_table.py
    usage: prune_history_table.py [-h] [--batch BATCH] [--created CREATED]
    
    Remove unused histories from database. A history is considered unused if it doesn't have a user and its hid counter has not been incremented.
    
    optional arguments:
      -h, --help         show this help message and exit
      --batch BATCH      batch size
      --created CREATED  most recent created date/time in ISO format (for example, March 11, 1952 is represented as '1952-03-11')
