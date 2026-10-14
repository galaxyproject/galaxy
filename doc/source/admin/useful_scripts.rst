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

Deleting old galaxy_session records
-----------------------------------

Each time Galaxy is accessed, a galaxy_session record is created, even when the user is anonymous. Over time, Galaxy accumulates such records. Deleting such records will declutter the database and free up space. 

To safely delete such records, please use the galaxy-delete-sessions script. By default, a galaxy_session record should be at least a month old to be considered safe to delete (which is determined by the value of its ``update_time`` field). Each user's most recent galaxy_session record is never deleted, however old: it keeps that user's browser logged in, determines which history is opened on their next login, and is the source of the last-login time in the admin users list.

.. code-block:: console

    $ python  $GALAXY_ROOT/lib/galaxy/model/scripts/delete_galaxy_sessions.py
    usage: delete_galaxy_sessions.py [-h] [--updated UPDATED]
    
    Remove old galaxy_session records from database.
    
    options:
      -h, --help         show this help message and exit
      --updated UPDATED  most recent `updated` date/time in ISO format (for example, March 11, 1952 is represented as '1952-03-11'

Deleting old job metrics
-------------------------

Galaxy stores job metrics in two tables: `job_metrics_text` and `job_metrics_numeric`.  To free up space and delete old job metrics records, please use the galaxy-delete-job-metrics script.

Warning: these tables store useful data; you should only use this script if you need to reclaim space. 

To view disk usage by table you can use gxadmin, a command line utility for Galaxy admins: `gxadmin query pg-table-size` (Ref: https://github.com/galaxyproject/gxadmin).

.. code-block:: console

    $ python  $GALAXY_ROOT/lib/galaxy/model/scripts/delete_job_metrics.py
    usage: delete_job_metrics.py [-h] --updated UPDATED
    
    Remove old job metrics records from database.
    
    options:
      -h, --help         show this help message and exit
      --updated UPDATED  most recent `updated` date/time in ISO format (for example, March 11, 1952 is represented as '1952-03-11')

Making existing users' data private
-----------------------------------

The ``new_user_dataset_access_role_default_private`` option only applies to users created after it is set. To make data private for existing users as well, use the galaxy-make-data-private script. It restricts access to each user's private role for:

- the user's default permissions, which apply to their new histories;
- the default permissions of their histories that are not shared, which apply to new datasets in those histories;
- datasets that only the owner can reach through histories that are not shared.

A history counts as shared if it is published, accessible via link, shared with other users, or referenced by a page that is. Datasets that already have access restrictions, are in a data library, or are also in another user's or an anonymous history are left unchanged. Datasets that Galaxy converted from another dataset, for example for visualizations, are only made private if every dataset they were converted from is private to the same user.

Things to consider before running it:

- The script cannot tell whether a user chose public defaults in their preferences or kept the old server default, so it makes both private.
- Links to datasets that users handed out themselves, for example display or download URLs, stop working for anyone else.
- Saved visualizations are not checked: a shared visualization of a dataset that becomes private no longer displays for other users.
- Pages are only checked when the script starts. Histories shared while it runs are left unchanged, but a page published while it runs may lose access to the datasets it shows.
- Pages saved before Galaxy 18.09 refer to histories and datasets by encoded ids. The script decodes these with the ``id_secret`` from the Galaxy configuration file, so run it with the same configuration as Galaxy.

By default the script only reports what it would change. Run it with ``--commit`` to apply the changes. Running it again is safe; it only adds permissions that are missing.

.. code-block:: console

    $ python  $GALAXY_ROOT/lib/galaxy/model/scripts/make_data_private.py
    usage: make_data_private.py [-h] [--commit] [--batch BATCH] [-c CONFIG_FILE]

    Make existing users' data private by default.

    Restricts access to each user's private role for:

    - users' default permissions, used for new histories;
    - default permissions of histories that are not shared, used for new datasets in those histories;
    - datasets that only that user can reach through histories that are not shared.

    Datasets are left unchanged if they already have access restrictions, are in a data library, are
    reachable through histories of other users or of anonymous users, or are reachable through a
    history that is published, accessible via link, shared with other users, or referenced by a page
    that is. Datasets converted from another dataset (e.g. for visualizations) are only restricted
    if every dataset they were converted from is private to the same user.

    Without --commit, only reports what would be changed.

    options:
      -h, --help            show this help message and exit
      --commit              apply the changes (default: only report them)
      --batch BATCH         number of ids processed per batch
      -c, --config-file, --config CONFIG_FILE
                            Galaxy config file (defaults to $GALAXY_ROOT/config/galaxy.yml if that
                            file exists or else to ./config/galaxy.ini if that exists). If this isn't
                            set on the command line it can be set with the environment variable
                            GALAXY_CONFIG_FILE.
