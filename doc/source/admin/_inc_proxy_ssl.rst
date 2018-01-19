The use of SSL is **strongly encouraged** to avoid exposure of confidential information such as datasets and user
credentials to eavesdroppers. The instructions in this document are for setting up an SSL-enabled Galaxy server.

When setting up an SSL server, simply enabling SSL with the default options is not enough to have a secure server. In
most cases, the configuration is weak and vulnerable to one or more of the multitude of SSL attacks that have been
recently prevalent.  The `Qualys SSL/TLS Deployment Best Practices`_ is an excellent and up-to-date guide covering
everything necessary for securing an SSL server. In addition, the `Mozilla SSL Configuration Generator`_ can provide you
with a best practices config tailored to your desired security level and software versions.

Finally, Google's `PageSpeed Insights`_ tool is helpful for determining how you can improve responsiveness as related to
proxying, such as verifying that caching and compression are configured properly.

If you need to run more than one site on your Galaxy server, there are two options:

- Run them on the same server but serve them on different hostnames
- Serve them from different URL prefixes on a single hostname

The former option is typically cleaner, but if serving more than one SSL site, you will need an SSL certificate with
subjectAltNames_ for each hostname served by the server.

.. _Qualys SSL/TLS Deployment Best Practices: https://www.ssllabs.com/projects/best-practices/
.. _Mozilla SSL Configuration Generator: https://mozilla.github.io/server-side-tls/ssl-config-generator/
.. _PageSpeed Insights: https://developers.google.com/speed/pagespeed/insights/
.. _subjectAltNames: http://wiki.cacert.org/FAQ/subjectAltName

