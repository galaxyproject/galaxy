Galaxy Performance Tracking
===========================

Tracking performance over time and identifying slow queries in your Galaxy can be an extremely important thing to do, especially for larger Galaxies.

Most performance tracking requires sending metrics to a metrics collection server such as `Graphite <http://graphiteapp.org/>`__ or `StatsD <https://github.com/etsy/statsd/>`__. This document assumes you have already deployed a metrics server.

uWSGI
-----

As you have certainly switched to uWSGI from the default paste server, there is some built-in uWSGI support for performance logging. You can send uWSGI's internal metrics to a carbon (Graphite) server by setting the carbon option in your galaxy.yml:

.. code-block:: yaml

   uwsgi:
      socket: ...
      carbon: 127.0.0.1:2003

Or a StatsD server via:

.. code-block:: yaml

   wsgi:
      socket: ...
      statsd-push: 127.0.0.1:8125

The `official documentation <https://uwsgi-docs.readthedocs.io/en/latest/Metrics.html#stats-pushers>`__ contains further information on uWSGI and stats servers. In the `uWSGI Stats Server <https://uwsgi-docs.readthedocs.io/en/latest/StatsServer.html>` documentation, you can see an example of the sort of information that you will be able to collect.

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
