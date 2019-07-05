This documentation should be used in conjunction with the `Scaling and Load Balancing` documentation, which you should
familiarize yourself with prior to setting up your proxy.

You will need to ensure that inbound (and outbound) traffic on the HTTP (TCP port 80) and HTTPS (TCP port 443) ports is
permitted by your server's firewall/security.

**Documentation Conventions:**

For the purposes of this example, we assume that:

- **Debian** refers to any *Debian*-based Linux distribution (including Ubuntu)
- **EL** refers to any *RedHat Enterprise Linux*-based Linux distribution (including CentOS)
- the Galaxy server is installed at ``/srv/galaxy/server``
- |PROXY| runs as the user ``www-data`` (this is the default under Debian)
- Galaxy runs as the user ``galaxy`` with primary group ``galaxy``
- Galaxy is served from the hostname ``galaxy.example.org``

Throughout the configuration examples in this document, in order to avoid repetition, ``#...`` is used to denote a
location where existing or previously given configuration statements would appear.

.. danger:: Please note that Galaxy's files - code, datasets, and so forth - should *never* be located on disk inside
   |PROXY|'s document root. By default, this would expose all of Galaxy (including datasets) to anyone on the web.
