# Proxying Galaxy with Apache

For various reasons (performance, authentication, etc.) in a production environment, it's recommended to run Galaxy behind a web server proxy. Although any proxy could work, Apache is a common choice. Alternatively, we use [nginx](http://nginx.net/) for our public sites and open source infrastructure, and [details are available](./nginx.html) for it, too.

Currently the only recommended way to run Galaxy with Apache is using `mod_rewrite` and `mod_proxy`. Either `mod_proxy_uwsgi` or `mod_proxy_http` may be used from there.

To support proxying, the `mod_proxy`, `mod_http_proxy` and `mod_rewrite` modules must be enabled in the Apache config. The main proxy directives, `ProxyRequests` and `ProxyVia` do **not** need to be enabled.

## Prerequisites

Make sure that inbound (and outbound) traffic to the TCP protocol HTTP on port 80 (and HTTPS on port 443 if using SSL) is permitted by your server's firewall/security.

```eval_rst
.. warning:: Please note that Galaxy should *never* be located on disk inside Apache's `DocumentRoot`. By default, this would expose all of Galaxy (including datasets) to anyone on the web.
```

## Basic configuration

### Allow Encoded Slashes in URLs

Some Galaxy URLs contain encoded slashes (%2F) in the path and Apache will not serve these URLs by default. To configure Apache to serve URLs with encoded slashes in the path, add the following line to your Apache configuration file:

```apache
AllowEncodedSlashes NoDecode
```

**Note**: The `NoDecode` setting was added in httpd 2.2.18, and CentOS 6 (as RHEL 6 does) only has 2.2.15. The [CentOS SCLo SIG Repo](https://wiki.centos.org/SpecialInterestGroup/SCLo/CollectionsList) has an httpd24 package.

### Serving Galaxy at the web server root (/)

For a default Galaxy configuration running on [http://localhost:8080/](http://localhost:8080/), the following lines in the Apache configuration will proxy requests to the Galaxy application:

```apache
# Rewrite
RewriteEngine on
RewriteRule ^(.*) http://localhost:8080$1 [P]
```

Or, if using `mod_proxy` with HTTP transport

```apache
ProxyPass / http://127.0.0.1:8080/
```

Or, if using `mod_proxy` with uWSGI transport

```apache
ProxyPass / uwsgi://127.0.0.1:4001/
```

Thus, all requests on your server are now redirected to Galaxy. Because this example uses the "root" of your web server, you may want to use a [VirtualHost](http://httpd.apache.org/docs/2.2/vhosts/) to be able to run other sites from this same server.

If your Apache server is set up to use `mod_security`, you may need to modify the value of the `SecRequestBodyLimit`. The default value on some systems will limit uploads to only a few kilobytes.

Since Apache is more efficient at serving static content, it is best to serve it directly, reducing the load on the Galaxy process and allowing for more effective compression (if enabled), caching, and pipelining. To do so, your configuration will now include the following, where `$GALAXY_ROOT` should be replaced with the filesystem path to your Galaxy installation

```apache
RewriteEngine on
RewriteRule ^/static/style/(.*) $GALAXY_ROOT/static/june_2007_style/blue/$1 [L]
RewriteRule ^/static/scripts/(.*) $GALAXY_ROOT/static/scripts/packed/$1 [L]
RewriteRule ^/static/(.*) $GALAXY_ROOT/static/$1 [L]
RewriteRule ^/favicon.ico $GALAXY_ROOT/static/favicon.ico [L]
RewriteRule ^/robots.txt $GALAXY_ROOT/static/robots.txt [L]
```

You will need to ensure that filesystem permissions are set such that the user running your Apache server has access to the Galaxy static/ directory.

### Serving Galaxy at a sub directory (such as /galaxy)

It may be necessary to house Galaxy at an address other than the web server root (`http://www.example.org/galaxy`), instead of `http://www.example.org`). To do this, you need to make the following changes:

Two changes are necessary:

1. In the apache config, prefix all of the location directives with your prefix, like so:

```apache
RewriteEngine on
RewriteRule ^/galaxy/static/style/(.*) $GALAXY_ROOT/static/june_2007_style/blue/$1 [L]
RewriteRule ^/galaxy/static/scripts/(.*) $GALAXY_ROOT/static/scripts/packed/$1 [L]
RewriteRule ^/galaxy/static/(.*) $GALAXY_ROOT/static/$1 [L]
RewriteRule ^/galaxy/favicon.ico $GALAXY_ROOT/static/favicon.ico [L]
RewriteRule ^/galaxy/robots.txt $GALAXY_ROOT/static/robots.txt [L]
```

Note the first rewrite rule deals with the missing trailing slash problem. If left out, [http://www.example.org/galaxy](http://www.example.org/galaxy) will result in a 404 error.

If you are using `mod_rewrite` for serving:

```
RewriteRule ^/galaxy$ /galaxy/ [R]
RewriteRule ^/galaxy(.*) http://localhost:8080$1 [P]
```

Or for `proxy_http`/`proxy_uwsgi`:

```
ProxyPass /galaxy http://127.0.0.1:8080/galaxy
# or
ProxyPass /galaxy uwsgi://127.0.0.1:4001/
```

2. The Galaxy application needs to be aware that it is running with a prefix (for generating URLs in dynamic pages). This is accomplished by configuring a Paste proxy-prefix filter in the `[app:main]` section of `config/galaxy.ini` and restarting Galaxy:


```ini
[filter:proxy-prefix]
use = egg:PasteDeploy#prefix
prefix = /galaxy

[app:main]
filter-with = proxy-prefix
cookie_path = /galaxy
```

`cookie_prefix` should be set to prevent Galaxy's session cookies from clobbering each other if running more than one instance of Galaxy in different subdirectories on the same hostname.

### SSL

If you place Galaxy behind a proxy address that uses SSL (i.e., `https://` URLs), edit your galaxy location block (e.g. `location /` when served at the root, or something else like `location /galaxy` when served under a prefix)

```apache
<Location "/">
    ...
    RequestHeader set X-URL-SCHEME https
    ...
</Location>
```

Setting `X-URL-SCHEME` makes Galaxy aware of what type of URL it should generate for external sites like Biomart. This should be added to the existing `<Location />` block if you already have one, and adjusted accordingly if you're serving Galaxy from a subdirectory.

## Advanced Configuration Topics

### Compression and caching

All of Galaxy's static content can be cached on the client side, and everything (including dynamic content) can be compressed on the fly. This will decrease download and page load times for your clients, as well as decrease server load and bandwidth usage. To enable, you'll need to load `mod_deflate` and `mod_expires` in your Apache configuration, and then set:

```apache
<Location "/">
    ...
    # Compress all uncompressed content.
    SetOutputFilter DEFLATE
    SetEnvIfNoCase Request_URI \.(?:gif|jpe?g|png)$ no-gzip dont-vary
    SetEnvIfNoCase Request_URI \.(?:t?gz|zip|bz2)$ no-gzip dont-vary
    SetEnvIfNoCase Request_URI /history/export_archive no-gzip dont-vary
</Location>
<Location "/static">
    # Allow browsers to cache everything from /static for 6 hours
    ExpiresActive On
    ExpiresDefault "access plus 6 hours"
    ...
</Location>
```

The contents above should be added to the existing `<Location "/">` block if you already have one, and adjusted accordingly if you're serving Galaxy from a subdirectory.

### Sending files using Apache

Galaxy sends files (e.g. dataset downloads) by opening the file and streaming it in chunks through the proxy server. However, this ties up the Galaxy process, which can impact the performance of other operations (see [production configuration](../production.html) for a more in-depth explanation).

Apache can assume this task instead and as an added benefit, speed up downloads. This is accomplished through the use of `mod_xsendfile`, a 3rd-party Apache module. Dataset security is maintained in this configuration because Apache will still check with Galaxy to ensure that the requesting user has permission to access the dataset before sending it.

To enable it, you must first install `mod_xsendfile`, this is usually available via your OS's repositories. Once done, add the appropriate `LoadModule` directive to your Apache configuration to load the xsendfile module and the `XSendFile` directives to your proxy configuration:

```apache
<Location "/">
     XSendFile on
     XSendFilePath /
</Location>
```

Finally edit your `$GALAXY_ROOT/config/galaxy.ini` and make the following change before restarting Galaxy:

```ini
[app:main]
apache_xsendfile = True
```

For this to work, the user under which your nginx server runs will need read access to Galaxy's `$GALAXY_ROOT/database/files/` directory and its contents.

### External user authentication

- [Apache for External Authentication](https://galaxyproject.org/admin/config/apache-external-user-auth/)
- [Built-in Galaxy External Authentication](../authentication.html)

### Display Sites

Display sites such as UCSC work not by sending data directly from Galaxy to UCSC via the client's browser, but by sending UCSC a URL to the data in Galaxy that the UCSC server will retrieve data from. Since enabling authentication will place **all** of Galaxy behind authentication, such display sites will no longer be able to access data via that URL. If `display_servers` is set to a non-empty value in `$GALAXY_ROOT/config/galaxy.ini`, this tells Galaxy it should allow the named servers access to data in Galaxy. However, you still need to configure Apache to allow access to the datasets. An example config is provided here that allows the UCSC Main/Test backends:

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

**PLEASE NOTE that this introduces a security hole** , the impact of which depends on whether you have restricted access to the dataset via Galaxy's [internal dataset permissions](https://galaxyproject.org/learn/security-features/).

- By default, data in Galaxy is public. Normally with a Galaxy server behind authentication in a proxy server this is of little concern since only clients who've authenticated can access Galaxy. However, if display site exceptions are made as shown above, anyone could use those public sites to bypass authentication and view any **public** dataset on your Galaxy server. If you have not changed from the default and most of your datasets are public, you should consider running your own display sites that are also behind authentication rather than using the public ones.

- For datasets for which access has been restricted to one or more roles (i.e. it is no longer "public"), access for reading via external browsers is only allowed for a brief period, when someone with access permission clicks the "display at..." link. During this period, anyone who has the dataset ID would then be able to use the browser to view this dataset. Although such a scenario is unlikely, it is technically possible.


### Proxying multiple galaxy worker threads

If you've configured multiple threads for galaxy in the `config/galaxy.ini` file, you will need a `ProxyBalancer` to manage sending requests to each of the threads. You can do that with apache configuration as follows:

```apache
<Proxy balancer://galaxy>
 BalancerMember http://localhost:8400
 BalancerMember http://localhost:8401
</Proxy>


# Replace the following line from the regular proxy configuration:
# RewriteRule ^(.*) http://localhost:8080$1 [P]
# With:
RewriteRule ^(.*) balancer://galaxy$1 [P]
```
