:orphan:

Proxy Package Layouts
========================================

Every software package has a suggested filesystem layout, and proxy servers like Apache and NGINX are no exception.
However, Linux distribution package maintainers often have their own opinions about layout, especially with respect to
following a layout standard or scheme employed by their particular distribution.

Thus, although you can configure the proxy server entirely within its primary configuration file, if you have installed
the proxy via your system package manager, this may not be the best idea. The primary config file in the cases of both Apache
and nginx under both Debian-based distributions and Enterprise Linux-based distributions contains various *include*
directives designed to allow you to place your configuration in files that are entirely controlled by you. This helps to
avoid conflicts in the primary config file when the package is upgraded.

.. hint::

    Primary configuration files can be found at:

    - nginx (both EL and Debian): ``/etc/nginx/nginx.conf``
    - Apache:

      - EL: ``/etc/httpd/conf/httpd.conf``
      - Debian: ``/etc/apache2/apache2.conf``

Package Layout Overviews
---------------------------

Debian
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Debian uses a very similar directory scheme for both nginx and Apache, where ``<server>`` is ``apache2`` or ``nginx``
and ``<component>`` is some configuration subcomponent:

- ``/etc/<server>/<component>-available`` for files containing configuration snippets for various instances of the given
  component
- ``/etc/<server>/<component>-enabled`` for symbolic links to files in ``/etc/<server>/<component>-available`` for each
  snippet that the administrator wishes to enable

``<component>-available`` is effectively a "repository" for configurations which are enabled by symbolic links in
``<component>-enabled``.

Both nginx and Apache use the component ``sites``, intended for individual website configurations. Apache additionally
uses the components ``mods`` and ``conf`` for module loading/configuration and general global configuration statements,
respectively. Nginx, lacking the ``mods`` and ``conf`` components, provides ``/etc/nginx/conf.d``

.. tip::

    On Debian, the paths most relevant to our purposes are:

    - nginx:

      - ``/etc/nginx/conf.d/*.conf`` for general directives that belong in the ``http {}`` block
      - ``/etc/nginx/sites-available/*`` for individual site configs
      - ``/etc/nginx/sites-enabled/*`` to enable sites

    - Apache:

      - ``/etc/apache2/conf-available/*`` for general directives that belong in the ``http {}`` block
      - ``/etc/apache2/conf-enabled/*`` to enable configs
      - ``/etc/apache2/sites-available/*`` for individual site configs
      - ``/etc/apache2/sites-enabled/*`` to enable sites

Enterprise Linux
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

EL's layout is simpler: both nginx and Apache provide a single configuration inclusion directory, where ``<server>`` is
``httpd`` or ``nginx``:

- ``/etc/<server>/conf.d/``

Apache additionally has a module configuration directory at ``/etc/httpd/conf.modules.d``

.. tip::

    On EL, the paths most relevant to our purposes are:

    - nginx: ``/etc/nginx/conf.d/*.conf``
    - Apache: ``/etc/httpd/conf.d/*.conf``

NGINX
---------------------------

**Global option configuration:**

On both Debian and EL, you could create ``/etc/nginx/conf.d/galaxy_options.conf`` for global options intended for the
``http {}`` block.  Because this file is included from within the ``http {}`` block, you would simply define directives
without enclosing them in any sort of block:

.. code-block:: nginx

    proxy_read_timeout 180;
    client_max_body_size 10g;
    ssl_certificate /etc/nginx/ssl/server.crt;
    ssl_certificate_key /etc/nginx/ssl/server.key;
    #...

**Site configuration:**

For the site configurations, you could create:

- ``/etc/nginx/sites-available/galaxy`` on Debian
- ``/etc/nginx/conf.d/galaxy_site.conf`` on EL

These files contain ``server {}`` blocks (again, not enclosed in an ``http {}``):

.. code-block:: nginx

    server {
        listen 80 default_server;
        listen [::]:80 default_server;
        server_name _;
        #...
    }

    server {
        listen 443 default_server;
        listen [::]:443 default_server;
        server_name _;
        #...
    }

On Debian, you'd then need to symlink the config with:

.. code-block:: shell-session

    # ln -s /etc/nginx/sites-available/galaxy /etc/nginx/sites-enabled/galaxy

Apache
---------------------------

**Global option configuration:**

For the global options, you could create:

- ``/etc/apache2/confs-available/galaxy.conf`` on Debian
- ``/etc/httpd/conf.d/galaxy_options.conf`` on EL

With the global configuration directives:

.. code-block:: apache

    SSLProtocol             all -SSLv3
    SSLCipherSuite          ...
    #...

**Site configuration:**

For the site configurations, you could create:

- ``/etc/apache2/sites-available/galaxy.conf`` on Debian
- ``/etc/httpd/conf.d/galaxy_site.conf`` on EL

With the ``<VirtualHost>`` blocks:

.. code-block:: apache

    <VirtualHost _default_:80>
        Redirect permanent / https://galaxy.example.org
    </VirtualHost>

    <VirtualHost _default_:443>
        SSLEngine on
        SSLCertificateFile      /etc/apache2/ssl/server.crt
        SSLCertificateKeyFile   /etc/apache2/ssl/server.key
        #...
    </VirtualHost>

On Debian you'd then need to symlink the configs with (or do it by hand with `ln -s`):

.. code-block:: shell-session

    # a2enconf galaxy
    # a2ensite galaxy
