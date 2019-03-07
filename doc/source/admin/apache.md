```eval_rst
.. |PROXY| replace:: Apache
```
# Proxying Galaxy with Apache

In a production environment, it is recommended to run Galaxy behind a proxy web server for performance and security 
reasons. The proxy server sits between clients and your Galaxy server, relaying requests between them and offloading 
some of the more menial and resource-intensive tasks.

[The Apache HTTP Server][apache] is a widely deployed and very featureful general purpose web server with mature
proxying capabilities.

Instructions for [proxying with NGINX](nginx.md), which is the proxy server used by The Galaxy Project's public
servers, [usegalaxy.org][main] ("Main") and [Test][test], as well as the [Docker Galaxy project][docker-galaxy], are
also available.

[apache]: https://httpd.apache.org/
[main]: https://galaxyproject.org/main/
[test]: https://galaxyproject.org/test/
[docker-galaxy]: https://github.com/bgruening/docker-galaxy-stable

## Prerequisites

```eval_rst
.. include:: _inc_proxy_prereq.rst
```

### Apache Proxy Prerequisites

Currently, the only recommended way to proxy Galaxy with Apache is using `mod_rewrite`, `mod_proxy`, and
`mod_proxy_uwsgi`. These modules must be enabled in the Apache config. The main proxy directives, `ProxyRequests` and
`ProxyVia` do **not** need to be enabled.

Additionally, these directions are written for Apache 2.4+. Apache 2.4 for EL 6 can be obtained from the [CentOS SCLo
SIG Repo][sclo-sig-repo]. Otherwise, your system package manager's version of Apache should be suitable. On EL, you will
need to enable the [EPEL][epel] repository to obtain the `mod_proxy_uwsgi` package.

```eval_rst
.. caution:: ``mod_uwsgi`` is not the same module as ``mod_proxy_uwsgi``. The former is the old and unsupported module.
   Be sure that you have installed ``mod_proxy_uwsgi``.
```

Ensure that the `mod_headers`, `mod_rewrite`, `mod_proxy`, and `mod_proxy_uwsgi` modules are loaded. Although not
required, the configuration examples also use `mod_deflate` and `mod_expires` for increased client/server performance,
so these should also be enabled.

On Debian you can install the necessary packages and enable the modules this with the following:

```shell-session
# apt-get install apache2 libapache2-mod-proxy-uwsgi
# a2enmod headers deflate expires rewrite proxy proxy_uwsgi
Enabling module headers.
Considering dependency filter for deflate:
Module filter already enabled
Module deflate already enabled
Enabling module expires.
Enabling module rewrite.
Enabling module proxy.
Considering dependency proxy for proxy_uwsgi:
Module proxy already enabled
Enabling module proxy_uwsgi.
To activate the new configuration, you need to run:
  service apache2 restart
```

And on EL:

```shell-session
# yum install httpd mod_proxy_uwsgi
# echo "LoadModule proxy_uwsgi_module modules/mod_proxy_uwsgi.so" > /etc/httpd/conf.modules.d/10-proxy-uwsgi.conf
```

[sclo-sig-repo]: https://wiki.centos.org/SpecialInterestGroup/SCLo/CollectionsList
[epel]: https://fedoraproject.org/wiki/EPEL

## Basic configuration

```eval_rst
.. include:: _inc_proxy_ssl.rst
```

### Serving Galaxy at the Web Server Root

```eval_rst
.. include:: _inc_proxy_serving_root.rst
.. _Galaxy Release 17.09 Proxy Documentation: https://docs.galaxyproject.org/en/release_17.09/admin/special_topics/apache.html
```

The following configuration is not exhaustive, only the portions most relevant to serving Galaxy are shown, these should
be incorporated with your existing/default Apache config as is appropriate for your server.  Notably, the Apache package
you installed most likely has a multi-file config layout. If you are not already familiar with that layout and where
best to place your configuration, you can learn more in the [Proxy Package Layouts](proxy_package_layout)
documentation.

```apache
SSLProtocol             all -SSLv3
SSLCipherSuite          ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-ECDSA-AES128-SHA:ECDHE-ECDSA-AES256-SHA:ECDHE-ECDSA-AES128-SHA256:ECDHE-ECDSA-AES256-SHA384:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES128-SHA:ECDHE-RSA-AES256-SHA:ECDHE-RSA-AES128-SHA256:ECDHE-RSA-AES256-SHA384:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES128-SHA:DHE-RSA-AES256-SHA:DHE-RSA-AES128-SHA256:DHE-RSA-AES256-SHA256
SSLHonorCipherOrder     on
SSLCompression          off
SSLSessionTickets       off

# OCSP stapling
SSLUseStapling          on
SSLStaplingResponderTimeout 5
SSLStaplingReturnResponderErrors off
SSLStaplingCache        shmcb:/var/run/ocsp(128000)

<VirtualHost _default_:80> 
    Redirect permanent / https://galaxy.example.org
</VirtualHost>

<VirtualHost _default_:443>
    SSLEngine on
    SSLCertificateFile      /etc/apache2/ssl/server.crt
    SSLCertificateKeyFile   /etc/apache2/ssl/server.key

    # Enable HSTS
    Header always set Strict-Transport-Security "max-age=15552000; includeSubdomains"

    # use a variable for convenience
    Define galaxy_root /srv/galaxy/server

    # don't decode encoded slashes in path info
    AllowEncodedSlashes NoDecode

    # enable compression on all relevant types
    AddOutputFilterByType DEFLATE text/html text/plain text/xml
    AddOutputFilterByType DEFLATE text/css
    AddOutputFilterByType DEFLATE application/x-javascript application/javascript application/ecmascript
    AddOutputFilterByType DEFLATE application/rss+xml
    AddOutputFilterByType DEFLATE application/xml
    AddOutputFilterByType DEFLATE application/json

    # allow access to static content
    <Directory "${galaxy_root}/static">
        AllowOverride None
        Require all granted
    </Directory>

	# Galaxy needs to know that this is https for generating URLs
	RequestHeader set X-URL-SCHEME "%{REQUEST_SCHEME}e"

    # allow up to 3 minutes for Galaxy to respond to slow requests before timing out
    ProxyTimeout 180

    # proxy all requests not matching other locations to uWSGI
    ProxyPass / unix:///srv/galaxy/var/uwsgi.sock|uwsgi://
    # or uWSGI on a TCP socket
    #ProxyPass / uwsgi://127.0.0.1:4001/

    # serve framework static content
    RewriteEngine On
    RewriteRule ^/static/style/(.*) ${galaxy_root}/static/style/blue/$1 [L]
    RewriteRule ^/static/(.*) ${galaxy_root}/static/$1 [L]
    RewriteRule ^/favicon.ico ${galaxy_root}/static/favicon.ico [L]
    RewriteRule ^/robots.txt ${galaxy_root}/static/robots.txt [L]

    # enable caching on static content
    <Location "/static">
        ExpiresActive On
        ExpiresDefault "access plus 24 hours"
    </Location>

    # serve visualization and interactive environment plugin static content
    <Directory "${galaxy_root}/config/plugins/(.+)/(.+)/static">
        AllowOverride None
        Require all granted
    </Directory>
    RewriteRule ^/plugins/(.+)/(.+)/static/(.*)$ ${galaxy_root}/config/plugins/$1/$2/static/$3 [L]
</VirtualHost>
```

Be sure to set `galaxy_root` to the path to your copy of Galaxy and modify the value of `ProxyPass /`  to match your
uWSGI socket path. With the default configuration, uWSGI will bind to a random TCP socket, so you will need to set it to
a fixed value as described in the [Scaling and Load Balancing](scaling.md) documentation. If using a UNIX domain
socket, be sure to pay particular attention to the discussion of users and permissions.

### Additional Notes

- **Do not** simply copy the SSL configuration directives and expect them to work on your server or to be secure! These
  are provided as examples of some of the best practices as of the time of writing, but will not always be up to date.
  Use the guides referenced in [basic configuration](#basic-configuration) section to configure SSL properly.
- If your existing Apache configuration contains a line or included config file defining a default server, be sure to
  disable it by commenting its `<VirtualHost>` or preventing its inclusion (under Debian this is done by removing its
  symlink from `/etc/apache2/sites-enabled`).
- `ProxyTimeout` can be adjusted as appropriate for your site. This is the amount of time allowed for communication
  between Apache and uWSGI to block while waiting for a response from Galaxy, and is useful for holding client (browser)
  connections while uWSGI is restarting Galaxy subprocesses or Galaxy is performing a slow operation.
- If your Apache server is set up to use `mod_security`, you may need to modify the value of the `SecRequestBodyLimit`.
  The default value on some systems will limit uploads to only a few kilobytes.
- Some Galaxy URLs contain encoded slashes (%2F) in the path and Apache will not serve these URLs by default, which is
  the reason for inclusion of the `AllowEncodedSlashes` directive. Note: The `NoDecode` value was added in Apache2
  2.2.18, which is newer than EL 6's provided 2.2.15.
- If you must serve Galaxy without SSL, you would simply replace the `443` with `80` in the SSL `VirtualHost` block
  and remove the non-SSL block and all SSL directives.
- If the proxy works but you are getting 404 errors for Galaxy's static content, be sure that the user that Apache runs
  as has access to Galaxy's `static/` directory (and all its parent directories) on the filesystem. You can test this on
  the command line with e.g. `sudo -u www-data ls /srv/galaxy/server/static`.

### Serving Galaxy at a URL Prefix

It may be necessary to serve Galaxy from an address other than the web server root (`https://www.example.org/galaxy`),
instead of `https://galaxy.example.org`). To do this, you need to make the following changes to the configuration in the
previous section:

1. In the Apache config, prefix all of the location directives with your prefix, like so:

	```apache
		#...

		# proxy all requests not matching other locations to uWSGI
		ProxyPass /galaxy unix:///srv/galaxy/var/uwsgi.sock|uwsgi://
		# or uWSGI on a TCP socket
		#ProxyPass /galaxy uwsgi://127.0.0.1:4001/

		# serve framework static content
		RewriteEngine On
		RewriteRule ^/galaxy/$ /galaxy [R,L]
		RewriteRule ^/galaxy/static/style/(.*) ${galaxy_root}/static/style/blue/$1 [L]
		RewriteRule ^/galaxy/static/(.*) ${galaxy_root}/static/$1 [L]
		RewriteRule ^/galaxy/favicon.ico ${galaxy_root}/static/favicon.ico [L]
		RewriteRule ^/galaxy/robots.txt ${galaxy_root}/static/robots.txt [L]
	```

2. The Galaxy application needs to be aware that it is running with a prefix (for generating URLs in dynamic pages).
   This is accomplished by configuring uWSGI and Galaxy (the `uwsgi` and `galaxy` sections in `config/galaxy.yml`
   respectively) like so and restarting Galaxy:

    ```yaml
    uwsgi:
        #...
        socket: unix:///srv/galaxy/var/uwsgi.sock
        mount: /galaxy=galaxy.webapps.galaxy.buildapp:uwsgi_app()
        manage-script-name: true
        # `module` MUST NOT be set when `mount` is in use
        #module: galaxy.webapps.galaxy.buildapp:uwsgi_app()

    galaxy:
        #...
        cookie_path: /galaxy
    ```

   `cookie_path` should be set to prevent Galaxy's session cookies from clobbering each other if you are running more
   than one instance of Galaxy under different URL prefixes on the same hostname.

   Be sure to consult the [Scaling and Load Balancing](scaling.md) documentation, other options unrelated to proxying
   should also be set in the `uwsgi` section of the config.

## Advanced Configuration Topics

### Sending Files With Apache

Galaxy sends files (e.g. dataset downloads) by opening the file and streaming it in chunks through the proxy server.
However, this ties up the Galaxy process, which can impact the performance of other operations (see [Production Server
Configuration](production.md) for a more in-depth explanation).

Apache can assume this task instead and, as an added benefit, speed up downloads. In addition, both the IGV genome browser and JBrowse tool (run within Galaxy) require support for the HTTP *Range* header, and this is only available if the proxy serves datasets.
This is accomplished through the use of `mod_xsendfile`, a 3rd-party Apache module. Dataset security is maintained in this configuration because Apache will
still check with Galaxy to ensure that the requesting user has permission to access the dataset before sending it.

To enable it, you must first install `mod_xsendfile`. This is usually available via your package manager
(`libapache2-mod-xsendfile` on Debian and `mod_xsendfile` from EPEL on EL). Once installed, add the appropriate
`LoadModule` directive to your Apache configuration (`LoadModule xsendfile_module /path/to/mod_xsendfile.so`, but both
the Debian and EPEL packages do this for you upon installation).

The, add `XSendFile` directives to your proxy configuration:

```apache
<Location "/">
     XSendFile on
     XSendFilePath /
</Location>
```

Next, edit `galaxy.yml` and make the following change before restarting Galaxy:

```yaml
galaxy:
    # ...
    apache_xsendfile: true
```

For this to work, the user under which your Apache server runs will need read access to Galaxy's `files_path` directory
(by default, `database/files/`) and its contents. This is most easily done by adding the Apache user to the Galaxy user's
primary group and setting the `umask(2)` to create files with the group read permission set. If you start Galaxy from
the command line, you can do this like so:

```shell-session
admin@server$ sudo usermod -a -G galaxy www-data    # add `www-data` user to `galaxy` group
admin@server$ sudo -iu galaxy
galaxy@server$ umask 027
galaxy@server$ sh run.sh
```

If you start Galaxy from supervisord, you can set the `umask` option in the [program
section](http://supervisord.org/configuration.html#program-x-section-settings) after adding the Apache user to the Galaxy
group as shown above.

### External user authentication

- [Apache for External Authentication](https://galaxyproject.org/admin/config/apache-external-user-auth/)
- [Built-in Galaxy External Authentication](authentication.md)

#### Display Sites

Display sites such as UCSC work not by sending data directly from Galaxy to UCSC via the client's browser, but by
sending UCSC a URL to the data in Galaxy that the UCSC server will retrieve data from. Since enabling authentication
will place **all** of Galaxy behind authentication, such display sites will no longer be able to access data via that
URL. If `display_servers` is set to a non-empty value in `$galaxy_root/config/galaxy.yml`, this tells Galaxy it should
allow the named servers access to data in Galaxy. However, you still need to configure Apache to allow access to the
datasets. An example config is provided here that allows the UCSC Main/Test backends:

```apache
<Location "/root/display_as">
    Satisfy Any
    Order deny,allow
    Deny from all
    Allow from hgw1.cse.ucsc.edu
    Allow from hgw2.cse.ucsc.edu
    Allow from hgw3.cse.ucsc.edu
    Allow from hgw4.cse.ucsc.edu
    Allow from hgw5.cse.ucsc.edu
    Allow from hgw6.cse.ucsc.edu
    Allow from hgw7.cse.ucsc.edu
    Allow from hgw8.cse.ucsc.edu
</Location>
```

**PLEASE NOTE that this introduces a security hole** , the impact of which depends on whether you have restricted access
to the dataset via Galaxy's [internal dataset permissions](https://galaxyproject.org/learn/security-features/).

- By default, data in Galaxy is public. Normally with a Galaxy server behind authentication in a proxy server this is of
  little concern since only clients who've authenticated can access Galaxy. However, if display site exceptions are made
  as shown above, anyone could use those public sites to bypass authentication and view any **public** dataset on your
  Galaxy server. If you have not changed from the default and most of your datasets are public, you should consider
  running your own display sites that are also behind authentication rather than using the public ones.

- For datasets for which access has been restricted to one or more roles (i.e. it is no longer "public"), access for
  reading via external browsers is only allowed for a brief period, when someone with access permission clicks the
  "display at..." link. During this period, anyone who has the dataset ID would then be able to use the browser to view
  this dataset. Although such a scenario is unlikely, it is technically possible.
