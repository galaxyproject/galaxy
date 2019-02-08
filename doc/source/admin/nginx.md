```eval_rst
.. |PROXY| replace:: nginx
```

# Proxying Galaxy with NGINX

In a production environment, it is recommended to run Galaxy behind a proxy web server for performance and security
reasons. The proxy server sits between clients and your Galaxy server, relaying requests between them and offloading
some of the more menial and resource-intensive tasks.

[NGINX][nginx] is a lightweight HTTP server designed with high performance proxying in mind. The Galaxy Project's public
servers, [usegalaxy.org][main] ("Main") and [Test][test], as well as the [Docker Galaxy project][docker-galaxy] use
NGINX, rather than Apache, to proxy Galaxy. NGINX was chosen for its simple, fast load balancing and other
proxy-oriented features.

Instructions for [proxying with Apache](apache.md) are also available.

[nginx]: http://nginx.org/en/
[main]: https://galaxyproject.org/main/
[test]: https://galaxyproject.org/test/
[docker-galaxy]: https://github.com/bgruening/docker-galaxy-stable

## Prerequisites

```eval_rst
.. include:: _inc_proxy_prereq.rst
```

### NGINX Proxy Prerequisities

If you plan to use nginx to handle your file uploads, you will (most likely) not be able to use your package manager's
version of nginx. The [Receiving Files With NGINX](#receiving-files-with-nginx) section explains this in detail and
provides some options for installing *nginx + upload module* packages maintained by the Galaxy Committers Team.

Otherwise, your system package manager's version of nginx should be suitable. Under Debian, the
[nginx-light][nginx-light] package contains all the necessary modules used in this guide. On EL, the [EPEL][epel]
version of nginx is suitable.

[nginx-light]: https://packages.debian.org/search?keywords=nginx-light
[epel]: https://fedoraproject.org/wiki/EPEL

## Basic Configuration

```eval_rst
.. include:: _inc_proxy_ssl.rst
```

### Serving Galaxy at the Web Server Root

```eval_rst
.. include:: _inc_proxy_serving_root.rst
.. _Galaxy Release 17.09 Proxy Documentation: https://docs.galaxyproject.org/en/release_17.09/admin/special_topics/nginx.html
```

uWSGI protocol support is built in to nginx, so (unlike Apache) no extra modules or recompiling should be required.

The following configuration is not exhaustive, only the portions most relevant to serving Galaxy are shown, these should
be incorporated with your existing/default nginx config as is appropriate for your server. Notably, the nginx package
you installed most likely has a multi-file config layout. If you are not already familiar with that layout and where
best to place your configuration, you can learn more in the [Proxy Package Layouts](proxy_package_layout)
documentation.

```nginx
http {

    #...

    # compress responses whenever possible
    gzip on;
    gzip_http_version 1.1;
    gzip_vary on;
    gzip_comp_level 6;
    gzip_proxied any;
    gzip_types text/plain text/css application/json application/x-javascript text/xml application/xml application/xml+rss text/javascript;
    gzip_buffers 16 8k;

    # allow up to 3 minutes for Galaxy to respond to slow requests before timing out
    uwsgi_read_timeout 180;

    # maximum file upload size
    client_max_body_size 10g;

    # allowable SSL protocols
    ssl_protocols TLSv1 TLSv1.1 TLSv1.2;

    # use secure ciphers
    ssl_ciphers
    ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-ECDSA-AES128-SHA:ECDHE-ECDSA-AES256-SHA:ECDHE-ECDSA-AES128-SHA256:ECDHE-ECDSA-AES256-SHA384:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES128-SHA:ECDHE-RSA-AES256-SHA:ECDHE-RSA-AES128-SHA256:ECDHE-RSA-AES256-SHA384:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES128-SHA:DHE-RSA-AES256-SHA:DHE-RSA-AES128-SHA256:DHE-RSA-AES256-SHA256;
    ssl_dhparam /etc/nginx/ssl/dhparams.pem;
    ssl_prefer_server_ciphers on;

    # enable session reuse
    ssl_session_cache shared:SSL:8m;
    ssl_session_timeout 5m;

    # cert/key
    ssl_certificate /etc/nginx/ssl/server.crt;
    ssl_certificate_key /etc/nginx/ssl/server.key;

    # OCSP stapling
    ssl_stapling on;
    ssl_stapling_verify on;
    ssl_trusted_certificate /etc/nginx/ssl/ca.crt;


    server {
        listen 80 default_server;
        listen [::]:80 default_server;
        server_name _;

        return 301 https://$host$request_uri;
    }

    server {
        listen 443 default_server;
        listen [::]:443 default_server;
        server_name _;

        # use a variable for convenience
		set $galaxy_root /srv/galaxy/server;

        # Enable HSTS
        add_header Strict-Transport-Security "max-age=15552000; includeSubdomains";

        # proxy all requests not matching other locations to uWSGI
        location / {
            uwsgi_pass unix:///srv/galaxy/var/uwsgi.sock
            uwsgi_param UWSGI_SCHEME $scheme;
            include uwsgi_params;
        }

		# serve framework static content
		location /static/style {
			alias $galaxy_root/static/style/blue;
			expires 24h;
		}
		location /static {
			alias $galaxy_root/static;
			expires 24h;
		}
		location /robots.txt {
			alias $galaxy_root/static/robots.txt;
			expires 24h;
		}
		location /favicon.ico {
			alias $galaxy_root/static/favicon.ico;
			expires 24h;
		}

        # serve visualization and interactive environment plugin static content
		location ~ ^/plugins/(?<plug_type>.+?)/(?<vis_name>.+?)/static/(?<static_file>.*?)$ {
            alias $galaxy_root/config/plugins/$plug_type/$vis_name/static/$static_file;
			expires 24;
        }
    }
}
```

Be sure to set `$galaxy_root` to the path to your copy of Galaxy and modify the value of `uwsgi_pass` to match your
uWSGI socket path. With the default configuration, uWSGI will bind to a random TCP socket, so you will need to set it to
a fixed value as described in the [Scaling and Load Balancing](scaling.md) documentation. If using a UNIX domain
socket, be sure to pay particular attention to the discussion of users and permissions.

### Additional Notes

- **Do not** simply copy the SSL configuration directives and expect them to work on your server or to be secure! These
  are provided as examples of some of the best practices as of the time of writing, but will not always be up to date.
  Use the guides referenced in [basic configuration](#basic-configuration) section to configure SSL properly.
- If your existing nginx configuration contains a line or included config file defining a default server, be sure to
  disable it by commenting its `server {}` or preventing its inclusion (under Debian this is done by removing its
  symlink from `/etc/nginx/sites-enabled`).
- `uwsgi_read_timeout` can be adjusted as appropriate for your site. This is the amount of time allowed for
  communication between nginx and uWSGI to block while waiting for a response from Galaxy, and is useful for holding
  client (browser) connections while uWSGI is restarting Galaxy subprocesses or Galaxy is performing a slow operation.
- The parameter `client_max_body_size` specifies the maximum upload size that can be handled by POST requests through
  nginx. You should set this to the largest file size that you wish to allow for upload and that could be reasonably
  handled by your site. It defaults to 1MB, so it will need to be increased if you are dealing with genome sized
  datasets.
- If you must serve Galaxy without SSL, you would simply replace the `listen` directives in the SSL `server {}` block
  with the `listen` directives from the non-SSL `server {}` block and remove the non-SSL block and SSL directives from
  the `http {}` block.
- If the proxy works but you are getting 404 errors for Galaxy's static content, be sure that the user that nginx runs
  as has access to Galaxy's `static/` directory (and all its parent directories) on the filesystem. You can test this on
  the command line with e.g. `sudo -u www-data ls /srv/galaxy/server/static`.

### Serving Galaxy at a URL Prefix

It may be necessary to serve Galaxy from an address other than the web server root (`https://www.example.org/galaxy`),
instead of `https://galaxy.example.org`). To do this, you need to make the following changes to the configuration in the
previous section:

1. In the nginx config, prefix all of the location directives with your prefix and redirect requests from `/prefix` to
   `/prefix/` like so:

    ```nginx
            #...

            # proxy all requests not matching other locations to uWSGI
            location /galaxy {
                uwsgi_pass unix:///srv/galaxy/var/uwsgi.sock
                uwsgi_param UWSGI_SCHEME $scheme;
                include uwsgi_params;
            }

            # serve framework static content
            location /galaxy/static/style {
                alias $galaxy_root/static/style/blue;
                expires 24h;
            }

            # additional static locations...

            # redirect /prefix -> /prefix/
            rewrite ^/galaxy$ /galaxy/ last;
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

### Sending Files With Nginx

Galaxy sends files (e.g. dataset downloads) by opening the file and streaming it in chunks through the proxy server.
However, this ties up the Galaxy process, which can impact the performance of other operations (see [Production Server
Configuration](production.md) for a more in-depth explanation). 

Nginx can assume this task instead and, as an added benefit, speed up downloads. In addition, both the IGV genome browser and JBrowse tool (run within Galaxy) require support for the HTTP *Range* header, and this is only available if the proxy serves datasets.
This is accomplished through the use of the special `X-Accel-Redirect` header. Dataset security is maintained in this configuration because nginx will still check with Galaxy to ensure that the requesting user has permission to access the dataset before sending it.

To enable it, add the following to your Galaxy's `server {}` block:

```nginx
        location /_x_accel_redirect/ {
            internal;
            alias /;
        }
```

Next, edit `galaxy.yml` and make the following change before restarting Galaxy:

```yaml
galaxy:
    #...
    nginx_x_accel_redirect_base: '/_x_accel_redirect'
```

For this to work, the user under which your nginx server runs will need read access to Galaxy's `files_path` directory
(by default, `database/files/`) and its contents. This is most easily done by adding the nginx user to the Galaxy user's
primary group and setting the `umask(2)` to create files with the group read permission set. If you start Galaxy from
the command line, you can do this like so:

```shell-session
admin@server$ sudo usermod -a -G galaxy www-data    # add `www-data` user to `galaxy` group
admin@server$ sudo -iu galaxy
galaxy@server$ umask 027
galaxy@server$ sh run.sh
```

If you start Galaxy from supervisord, you can set the `umask` option in the [program
section](http://supervisord.org/configuration.html#program-x-section-settings) after adding the nginx user to the Galaxy
group as shown above.

### Receiving Files With Nginx

Galaxy receives files (e.g. dataset uploads) by streaming them in chunks through the proxy server and writing the files
to disk. However, this again ties up the Galaxy process. nginx can assume this task instead and as an added benefit,
speed up uploads. This is accomplished through the use of
[nginx_upload_module](http://www.grid.net.ru/nginx/upload.en.html), a 3rd-party nginx module.

To enable it, you must first download, compile and install nginx with the upload module, since prior to NGINX 1.11.5,
nginx did not support shared modules, and the upload module is not yet shared-compatible. Because this is a tedious
and complicated process, the Galaxy Committers team maintains (for some platforms) versions of nginx modified from their
upstream package sources (APT, EPEL, etc.) to include the upload module:

- [Ubuntu (PPA)](https://launchpad.net/~galaxyproject/+archive/ubuntu/nginx) (Be sure to install `nginx-extras`, not `nginx`)
- [Enterprise Linux](https://depot.galaxyproject.org/yum/)

To contribute support for additional platforms, please see the [Galaxy
Starforge](https://github.com/galaxyproject/starforge) project, which is used to do the repackaging.


Once nginx with the upload module is installed, create a directory in which to store uploads (ideally, for performance
reasons, on the same filesystem as Galaxy's datasets) and add the necessary directives to `nginx.conf`:

```nginx
user galaxy;

http {

	#...

    server {

		#...

        # handle file uploads via the upload module
		location /_upload {
			upload_store /srv/galaxy/upload_store;
			upload_store_access user:rw group:rw;
			upload_pass_form_field "";
			upload_set_form_field "__${upload_field_name}__is_composite" "true";
			upload_set_form_field "__${upload_field_name}__keys" "name path";
			upload_set_form_field "${upload_field_name}_name" "$upload_file_name";
			upload_set_form_field "${upload_field_name}_path" "$upload_tmp_path";
			upload_pass_args on;
			upload_pass /_upload_done;
		}

        # once upload is complete, redirect to the proper galaxy path
        location /_upload_done {
            set $dst /api/tools;
            if ($args ~ nginx_redir=([^&]+)) {
                set $dst $1;
            }
            rewrite "" $dst;
        }
}
```

Note the `user` directive at the top, outside of the `http {}` block. To ensure that Galaxy has write permission on the
uploaded files, nginx's workers will need to run as the same user as Galaxy.

When serving Galaxy at a URL prefix as described in the [Serving Galaxy at a URL
prefix](#serving-galaxy-at-a-url-prefix) section, you will need to change `set $dst /api/tools;` to `set $dst
/prefix/api/tools;` (e.g. `set $dst /galaxy/api/tools;`).

Finally, edit `galaxy.yml` and make the following change before restarting Galaxy:

```yaml
galaxy:
    #...
    nginx_upload_store: /srv/galaxy/upload_store
    nginx_upload_path: '/_upload'
```

### Use Galaxy Authentication to Protect Custom Paths

You may find it useful to require authentication for access to certain paths on your server.  For example, Galaxy can
run a separate reports app which gives useful information about your Galaxy instance. See the [Reports Configuration
documentation](reports.md) and [Peter Briggs' blog post on the
subject](http://galacticengineer.blogspot.com/2015/06/exposing-galaxy-reports-via-nginx-in.html) for more.

After successfully following the blog post, Galaxy reports should be available at e.g. `https://galaxy.example.org/reports`.
To secure this page to only Galaxy administrators, adjust your nginx config accordingly:

**TODO:** This is not valid for the uWSGI proxy method and needs to be updated. -nate 2018-01-11

```nginx
        location /reports {
            #...
            satisfy any;            # only one auth method needs to succeed
            deny all;               # host-based auth is not allowed
            auth_request /_auth;    # forward authentication
        }

        location /_auth {
            #internal; probably?
            # The used galaxy api endpoint is only available to galaxy admins and thus limits the access
            # to only logged in admins.
            proxy_pass http://localhost/api/configuration/dynamic_tool_confs;
            proxy_pass_request_body off;
            proxy_set_header Content-Length "";
            proxy_set_header X-Original-URI $request_uri;
        }
```

### External User Authentication

- [Nginx for External Authentication](https://galaxyproject.org/admin/config/nginx-external-user-auth/)
- [Built-in Galaxy External Authentication](authentication.md)
