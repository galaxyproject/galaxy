Galaxy Performance Tracking
===========================

Tracking performance over time and identifying slow queries in your Galaxy can be an extremely important thing to do, especially for larger Galaxies.

Most performance tracking requires sending metrics to a metrics collection server such as `Graphite <http://graphiteapp.org/>`__ or `StatsD <https://github.com/etsy/statsd/>`__. This document assumes you have already deployed a metrics server.

Gunicorn
-----

There is some built-in Gunicorn support for performance logging. You can send Gunicorn's internal metrics to a StatsD server by setting the `--statsd-host` and `--statsd-prefix` command line options for Gunicorn in the `gravity` section of `galaxy.yml`:

.. code-block:: yaml

   gravity:
      ...
      gunicorn:
        gunicorn_extra_args: `--statsd-host 127.0.0.1:8125 --statsd-prefix=galaxy`
      ...


Alternatively, you can use `gxadmin <https://github.com/usegalaxy-eu/gxadmin#uwsgi-stats_influx>`__ to generate data ready to load in an InfluxDB database. In this case, you will need to add the stats option to your galaxy.yml:

.. code-block:: yaml

   gravity:
      ...
      gunicorn:
        gunicorn_extra_args: `--statsd-host 127.0.0.1:9191 --statsd-prefix=galaxy`
      ...

And then run gxadmin like this:


.. code-block:: bash

   gxadmin uwsgi stats_influx 127.0.0.1:9191

API / Route Timing Statistics
-----------------------------

Galaxy provides middleware to automatically log the amount of time controllers take to execute and to send that data to a stats server. Using the stats server of your choice, you can calculate the relevant statistics to ensure that your Galaxy server is performing as expected.

The statsD configuration requires setting the following options in the ``galaxy`` section of ``config/galaxy.yml``:

.. code-block:: yaml

    galaxy:
      #...
      statsd_host: 127.0.0.1
      statsd_port: 8125
      statsd_prefix: galaxy

Most people visualize the statistics using something like `Grafana <https://grafana.com/>`__:

.. image:: grafana.png
