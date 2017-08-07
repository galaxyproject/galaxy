Galactic Radio Telescope
========================

This is an opt-in service which Galaxy admins can configure to contribute their
job run data back to the community. We hope that by collecting this information
we can build accurate models of tool CPU/memory/time requirements. In turn,
admins will be able to use this analyzed data to optimize their job
distribution across highly heterogeneous clusters.

Registration
------------

You will need to register your Galaxy instance with the Galactic Radio
Telescope (GRT). This can be done `https://telescope.galaxyproject.org
<https://telescope.galaxyproject.org>`__.

About the Script
----------------

Once you've registered your Galaxy instance, you'll receive an instance ID and
an API key which are used to run ``scripts/grt/export.py``. The tool itself is very
simple to run. GRT will run and produce a directory of reports that can be
synced with the GRT server. Every time it is run, GRT only processes the list
of jobs that were run since the last time it was run. On first run, GRT will
attempt to export all job data for your instance which may be very slow
depending on your instance size. We have attempted to optimize this as much as
is feasible.

Data Privacy
------------

All data submitted to the GRT will be released into the public domain. If there
are certain tools you do not want included, or certain parameters you wish to
hide (e.g. because they contain API keys), then you can take advantage of the
built-in sanitization. ``scripts/grt/grt.yml.sample`` file allows you to build up
sanitization for the job logs.

.. code-block:: yaml

    sanitization:
        # Blacklist the entire tool from appearing
        tools:
            - __SET_METADATA__
            - upload1
        # Or you can blacklist individual parameters from being submitted, e.g. if
        # you have API keys as a tool parameter.
        tool_params:
            # Or to blacklist under a specific tool, just specify the ID
            some_tool_id:
                - dbkey
                # If you need to specify a parameter multiple levels deep, you can
                # do that as well. Currently we only support blacklisting via the
                # full path, rather than just a path component. So everything under
                # `path.to.parameter` will be blacklisted.
                - path.to.parameter
                # However you could not do "parameter" and have everything under
                # `path.to.parameter` be removed.
                # Repeats are rendered as an *, e.g.: repeat_name.*.values

To blacklist the results from specific tools appearing in results, just add the
tool ID under the ``tools`` list.

Blacklisting tool parameters is more complex. In a key under the ``tool_params`` key,
supply a list of parameters you wish to blacklist. *NB: This will slow down
processing of records associated with that tool.* Selecting keys is done
identically to writing test cases, except if you have a repeat element, just
replace the location of the numeric identifier with ``*``, e.g.
``repeat_name.*.some_subkey``

Data Collection Process
-----------------------

.. code-block:: console

    cd $GALAXY; python scripts/grt/export.py -l debug


``export.py`` connects to your galaxy database and makes queries against the
database for three primary tables:

- job
- job_parameter
- job_metric_numeric

these are exported with very little processing, as tabular files to the GRT
reports directory, ``$GALAXY/reports/``. We only collect new job data that we
have not seen since the previous run. The last-seen job ID is stored in
``$GALAXY/reports/.checkpoint``. Once the files have been exported, they are
put in a compressed archive, and some metadata about the export process is
written to a json file with the same name as the report archive.

You may wish to inspect these files to be sure that you're comfortable with the
information being sent.

Once you're happy with the data, you can submit it with the GRT submission tool...

Data Submission
---------------

.. code-block:: console

    cd $GALAXY; python scripts/grt/upload.py

``scripts/grt/upload.py`` is a script which will submit your data to the
configured GRT server. You must first be registered with the server which will
also walk you through the setup process.

With your reports, submitting them is very simple. The script will login to the
server and determine which reports the server does not have yet. Then it will
begin uploading those.

For administrators with firewalled galaxies and no internet access, if you are
able to exfiltrate your files to somewhere with internet, then you can still
take advantage of GRT. Alternatively you can deploy GRT on your own
infrastructure if you don't want to share your job logs.
