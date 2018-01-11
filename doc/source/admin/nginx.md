# Proxying Galaxy with NGINX

[NGINX](http://nginx.org/en/) is a lightweight http server designed with high performance proxying in mind. The public
Galaxy sites ([Main](https://galaxyproject.org/main/) and [Test](https://galaxyproject.org/test/)) as well as the
[Docker Galaxy project](https://github.com/bgruening/docker-galaxy-stable) use nginx to proxy rather than Apache for its
simple, fast load balancing and other features.


## Prerequisites

Make sure that inbound (and outbound) traffic to the TCP protocol HTTP on port 80 (and HTTPS on port 443 if using SSL)
is permitted by your server's firewall/security.

For the purposes of this example, we assume that:

- the Galaxy server is installed at `/srv/galaxy/server`
- nginx runs as the user `www-data` (this is the default under Debian-based Linux distributions)
- Galaxy runs as the user `galaxy` with primary group `galaxy`
- Galaxy is served from the hostname `galaxy.example.org`

Throughout the configuration examples in this document, in order to avoid reptition, `#...` is used to denote a location
where existing or previously given configuration statements would appear.

```eval_rst
.. warning:: Please note that Galaxy should *never* be located on disk inside nginx's document root. By default, this
   would expose all of Galaxy (including datasets) to anyone on the web.
```

## Basic Configuration

The use of SSL is **strongly encouraged** to avoid exposure of confidential information such as datasets and user
credentials to eavesdroppers. The instructions in this document are for setting an SSL-enabled Galaxy server.

When setting up an SSL server, simply enabling SSL with the default options is not enough. In most cases, the
configuration is weak and vulnerable to one or more of the multitude of SSL attacks that have been recently prevalent.
The [Qualys SSL/TLS Deployment Best Practices](https://www.ssllabs.com/projects/best-practices/) is an excellent and
up-to-date guide covering everything necessary for securing an SSL server. In addition, the [Mozilla SSL Configuration
Generator](https://mozilla.github.io/server-side-tls/ssl-config-generator/) can provide you with a best practices config
tailored to your desired security level and software versions.

Finally, Google's [PageSpeed Insights](https://developers.google.com/speed/pagespeed/insights/) tool is helpful for
determining how you can improve responsiveness as related to proxying, such as verifying that caching and compression
are configured properly.

If you need to run more than one site on your Galaxy server, there are two options:

- Run them on the same server but serve them on different hostnames
- Serve them from different URL prefixes on a single hostname

The former option is typically cleaner, but if serving more than one SSL site, you will need an SSL certificate with
[subjectAltName](http://wiki.cacert.org/FAQ/subjectAltName)s for each hostname served by the server.

### Serving Galaxy at the Web Server Root

This configuration assumes that Galaxy will be the only site on your server using the given hostname (e.g.
`https://galaxy.example.org`).

Beginning with Galaxy Release 18.01, the default application server that Galaxy runs under is uWSGI. Because of this,
the native high performance uWSGI protocol should be used for communication between the proxy server and Galaxy, rather
than HTTP. Legacy instructions for proxying via HTTP can be found in the [Galaxy Release 17.09 nginx
documentation](https://docs.galaxyproject.org/en/release_17.09/admin/special_topics/nginx.html).

uWSGI protocol support is built in to nginx, so (unlike Apache) no extra modules or recompiling should be required.

Since nginx is more efficient than uWSGI at serving static content, it is best to serve it directly, reducing the load
on the Galaxy process and allowing for more effective compression (if enabled), caching, and pipelining. Directives to
do so are included in the example below.

The following configuration is not exhaustive, only the portions most relevant to serving Galaxy are shown, these should
be incorporated with your existing/default nginx config as is appropriate for your server:

```nginx
http {

    #...

    # compress responses whenever possible
    gzip on;
    gzip_http_version 1.1;
    gzip_vary on;
    gzip_comp_level 4;
    gzip_proxied any;
    gzip_types text/plain text/css application/json application/x-javascript text/xml application/xml application/xml+rss text/javascript;
    gzip_comp_level 6;
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
a fixed value as described in the [Scaling and Load Balancing](scaling.html) documentation. If using a UNIX domain
socket, be sure to pay particular attention to the discussion of users and permissions.

### Implementation-specific Notes

It is possible to perform the entire configuration in the main nginx configuration file (typically
`/etc/nginx/nginx.conf`), however, nginx packages as provided by Linux distribution package managers typically provide a
slightly more complex layout that is designed to prevent conflicts in `nginx.conf` when updating the package.

On Debian-based Linux distributions (Debian, Ubuntu, etc.), the nginx package's default configuration contains two
include directives in the `http {}` block:

- One which includes any configuration files with the `.conf` extension in the `/etc/nginx/conf.d` directory, where you
  would place directives that belong in the `http {}` block.
- One which includes all files in the `/etc/nginx/sites-enabled` directory, which contains symlinks to
  `/etc/nginx/sites-available`, where you would place the `server {}` configurations for websites hosted by this nginx
  server.

On EL-based Linux distributions (RedHat Enterprise Linux, CentOS, etc.), the EPEL nginx package's default configuration
contains a directive in the `http {}` block that includes any configuration files with the `.conf` extension in the
`/etc/nginx/conf.d` directory.

Thus, on both Debian- and EL-based distributions, you might put the `http` directives in
`/etc/nginx/conf.d/galaxy_http_options.conf`. Note that these are **not** enclosed in an `http {}` block themselves, as
they are already enclosed by the `http {}` block in `/etc/nginx/nginx.conf`:

```nginx
uwsgi_read_timeout 180;
client_max_body_size 10g;
ssl_certificate /etc/nginx/ssl/server.crt;
ssl_certificate_key /etc/nginx/ssl/server.key;
#...
```

Then for the site configurations, you might create:

- `/etc/nginx/conf.d/galaxy_site.conf` on EL-based distributions
- `/etc/nginx/sites-available/galaxy` on Debian-based distributions

With the `server {}` blocks (again, not enclosed in an `http {}`):

```nginx
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
```

On Debian-based distribution, you'd then need to symlink the config with:

```shell-session
# ln -s /etc/nginx/sites-available/galaxy /etc/nginx/sites-enabled/galaxy
```

### Additional Notes

- **Do not** simply copy the SSL configuration directives and expect them to work on your server or to be secure! These
  are provided as examples of some of the best practices as of the time of writing, but will not always be up to date.
  Use the guides referenced in [basic configuration](#basic-configuration) section to configure SSL properly.
- If your existing nginx configuration contains a line or included config file defining a default server, be sure to
  disable it by commenting its `server {}` or preventing its inclusion (under Debian-based operating systems, this
  is done by removing its symlink from `/etc/nginx/sites-enabled`.
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

   Be sure to consult the [Scaling and Load Balancing](scaling.html) documentation, other options unrelated to proxying
   should also be set in the `uwsgi` section of the config.

## Advanced Configuration Topics

### Sending Files With Nginx

Galaxy sends files (e.g. dataset downloads) by opening the file and streaming it in chunks through the proxy server.
However, this ties up the Galaxy process, which can impact the performance of other operations (see [Production Server
Configuration](production.html) for a more in-depth explanation).

Nginx can assume this task instead and as an added benefit, speed up downloads. This is accomplished through the use of
the special `X-Accel-Redirect` header. Dataset security is maintained in this configuration because nginx will still
check with Galaxy to ensure that the requesting user has permission to access the dataset before sending it.

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

- [Ubuntu (PPA)](https://launchpad.net/~galaxyproject/+archive/ubuntu/nginx)
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
documentation](reports.html) and [Peter Briggs' blog post on the
subject](http://galacticengineer.blogspot.com/2015/06/exposing-galaxy-reports-via-nginx-in.html) for more.

After succesfully following the blog post, Galaxy reports should be available at e.g. `https://galaxy.example.org/reports`.
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
- [Built-in Galaxy External Authentication](authentication.html)
