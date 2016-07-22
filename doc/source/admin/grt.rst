Galactic Radio Telescope
========================

This is an opt-in service which Galaxy admins can configure to contribute their
job run data back to the community. We hope that by collecting this information
we can build accurate models of tool CPU/memory/time requirements. In turn,
admins will be able to use this analyzed data to optimize their job
distribution across highly heterogenous clusters.

Registration
------------

You will need to register your Galaxy instance with the Galactic Radio
Telescope (GRT). This can be done `https://radio-telescope.galaxyproject.org
<https://radio-telescope.galaxyproject.org>`__.

Submitting Data
---------------

Once you've registered your Galaxy instance, you'll receive an instance ID and
an API key which are used to run ``scripts/grt.py``. The tool itself is very simple
to run. It collects the last 7 days (by default) of data from your Galaxy
server, and sends them to the GRT for processing and display. Additionally
it collects the total number of users, and the number of users who ran
jobs in the last N days.

Running the tool is simple:

.. code-block:: shell

    python scripts/grt.py \
        <INSTANCE_UUID> \
        <API_KEY> \
        -c config/galaxy.ini \
        --grt-url https://radio-telescope.galaxyproject.org/api/v1/upload/
        --days 7

The only required parameters are the instance ID and API key. As you can see in
the example command, the GRT URL is configurable. If you do not wish to
participate in the public version of this experiment you can host your own
radio telescope to collect Galactic information.
