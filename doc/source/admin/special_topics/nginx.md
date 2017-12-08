# Proxying Galaxy with NGINX

[NGINX](http://nginx.org/en/) is a lightweight http server designed with high performance proxying in mind. The public Galaxy sites ([Main](https://galaxyproject.org/main/) and [Test](https://galaxyproject.org/test/)) as well as the [Docker Galaxy project](https://github.com/bgruening/docker-galaxy-stable) use nginx to proxy rather than Apache for its simple, fast load balancing and other features.

Galaxy should _never_ be located on disk inside nginx's `root`. By default, this would expose all of Galaxy (including datasets) to anyone on the web.

## Prerequisites

Make sure that inbound (and outbound) traffic to the TCP protocol HTTP on port 80 (and HTTPS on port 443 if using SSL) is permitted by your server's firewall/security.

```eval_rst
.. warning:: Please note that Galaxy should *never* be located on disk inside Nginx's document root. By default, this would expose all of Galaxy (including datasets) to anyone on the web.
```

## Basic configuration

### Serving Galaxy at the web server root (/)

For a default Galaxy configuration running on [http://localhost:8080/](http://localhost:8080/) (see [SSL](https://github.com/VJalili/galaxy-site/blob/patch-1/src/admin/config/nginxProxy/index.md#ssl) section for HTTPS), the following lines in the nginx configuration will proxy requests to the Galaxy application:

```nginx
http {
    ...

    upstream galaxy_app {
        server localhost:8080;
    }

    proxy_next_upstream off;
    server {
        client_max_body_size 10G;
        # ... other server stuff ...
        location / {
            proxy_pass http://galaxy_app;
            proxy_set_header X-Forwarded-Host $host;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        }

        # serve static content for visualization and interactive environment plugins
        location ~ ^/plugins/(?<plug_type>.+?)/(?<vis_name>.+?)/static/(?<static_file>.*?)$ {
            alias $GALAXY_ROOT/config/plugins/$plug_type/$vis_name/static/$static_file;
        }
    }
}
```


**Notes:**

Make sure that you either comment out or modify line containing default configuration for enabled sites.

```
include /etc/nginx/sites-enabled/*;
```

- The `proxy_next_upstream off;` disables nginx's round-robin scheme to prevent it from submitting POST requests more than once. This is unsafe, and is useful when using more than one upstream.
- Replace `$GALAXY_ROOT` with the path to your copy of Galaxy.
- The parameter `client_max_body_size` specifies the maximum upload size that can be handled by POST requests through nginx. You should set this to the largest file size that could be reasonable handled by your network. It defaults to 1M files, so will probably need to be increased if you are dealing with genome sized datasets.

Since nginx is more efficient at serving static content, it is best to serve it directly, reducing the load on the Galaxy process and allowing for more effective compression (if enabled), caching, and pipelining. To do so, add the following to your existing `server { }` block, replacing `$GALAXY_ROOT` with the correct path.:

```nginx
http {
    server {
        location /static {
            alias $GALAXY_ROOT/static;
        }
        location /static/style {
            alias $GALAXY_ROOT/static/style/blue;
        }
        location /static/scripts {
            alias $GALAXY_ROOT/static/scripts;
        }
        location /favicon.ico {
            alias $GALAXY_ROOT/static/favicon.ico;
        }
        location /robots.txt {
            alias $GALAXY_ROOT/static/robots.txt;
        }
    }
}
```

You'll need to ensure that filesystem permissions are set such that the user running your nginx server has access to the Galaxy static/ directory.


### Serving Galaxy at a sub directory (such as /galaxy)

It may be necessary to house Galaxy at an address other than the web server root (`http://www.example.org/galaxy`), instead of `http://www.example.org`). To do this, you need to make the following changes:

1. In the nginx config, prefix all of the location directives with your prefix, like so:

```nginx
http {
    server {
        ...

        location /galaxy {
            proxy_pass http://galaxy_app;
            proxy_set_header X-Forwarded-Host $host;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        }
        location /galaxy/static {
            alias $GALAXY_ROOT/static;
        }

        ...
    }
}
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

```nginx
location / {
    ...
    proxy_set_header X-URL-SCHEME https;
    ...
}
```

Setting `X-URL-SCHEME` makes Galaxy aware of what type of URL it should generate for external sites like Biomart. This should be added to the existing `location / { } ` block if you already have one, and adjusted accordingly if you're serving Galaxy from a subdirectory.

## Advanced Configuration Topics

### Compression and caching

All of Galaxy's static content can be cached on the client side, and everything (including dynamic content) can be compressed on the fly. This will decrease download and page load times for your clients, as well as decrease server load and bandwidth usage. To enable, you'll need nginx gzip support (which is standard unless compiled with `--without-http_gzip_module`), and the following in your `nginx.conf`:

```nginx
http {
    ...
    gzip on;
    gzip_http_version 1.1;
    gzip_vary on;
    gzip_comp_level 4;
    gzip_proxied any;
    gzip_types text/plain text/css application/x-javascript text/xml application/xml text/javascript application/json application/javascript;
    gzip_buffers 16 8k;
    gzip_disable "MSIE [1-6].(?!.*SV1)";
    ...
}
```

For caching, you'll need to add an `expires` directive to the `location /static { }` blocks:

```nginx
http {
    server {
        location /static {
            alias $GALAXY_ROOT/static;
            expires 24h;
        }
        location /static/style {
            alias $GALAXY_ROOT/static/style/blue;
            expires 24h;
        }
    }
}
```

The contents of `location /static { }` should be adjusted accordingly if you're serving Galaxy from a subdirectory.

### Sending files using Nginx

Galaxy sends files (e.g. dataset downloads) by opening the file and streaming it in chunks through the proxy server. However, this ties up the Galaxy process, which can impact the performance of other operations (see [Production Server Configuration](/src/admin/config/performance/production-server/index.md) for a more in-depth explanation).

Nginx can assume this task instead and as an added benefit, speed up downloads. This is accomplished through the use of the special `X-Accel-Redirect` header. Dataset security is maintained in this configuration because nginx will still check with Galaxy to ensure that the requesting user has permission to access the dataset before sending it.

To enable it, add the following to your `nginx.conf`:

```nginx
http {
    server {
        location /_x_accel_redirect/ {
            internal;
            alias /;
        }
    }
}
```

Finally edit your `$GALAXY_ROOT/config/galaxy.ini` and make the following change before restarting Galaxy:

```ini
[app:main]
nginx_x_accel_redirect_base = /_x_accel_redirect
```

For this to work, the user under which your nginx server runs will need read access to Galaxy's `$GALAXY_ROOT/database/files/` directory and its contents.

### Receiving files using nginx

Galaxy receives files (e.g. dataset uploads) by streaming them in chunks through the proxy server and writing the files to disk. However, this again ties up the Galaxy process. nginx can assume this task instead and as an added benefit, speed up uploads. This is accomplished through the use of `nginx_upload_module`, a 3rd-party nginx module.

To enable it, you must first [download](http://www.grid.net.ru/nginx/upload.en.html), compile and install `nginx_upload_module`. This means recompiling nginx. Once done, add the necessary directives to `nginx.conf`:

```nginx
user galaxy;
http {
    server {
        ...

        location /_upload {
            upload_store $GALAXY_ROOT/database/tmp/upload_store;
            upload_pass_form_field "";
            upload_set_form_field " __${upload_field_name}__ is_composite" "true";
            upload_set_form_field " __${upload_field_name}__ keys" "name path";
            upload_set_form_field "${upload_field_name}_name" "$upload_file_name";
            upload_set_form_field "${upload_field_name}_path" "$upload_tmp_path";
            upload_pass_args on;
            upload_pass /_upload_done;
        }

        location /_upload_done {
            set $dst /api/tools;
            if ($args ~ nginx_redir=([^&]+)) {
                set $dst $1;
            }
            rewrite "" $dst;
        }

        ...
    }
}
```

Note the `user` directive. To ensure that Galaxy has write permission on the uploaded files, nginx's workers will need to run as the same user as Galaxy.

Finally edit your `$GALAXY_ROOT/config/galaxy.ini` and make the following change before restarting Galaxy:

```ini
[app:main]
nginx_upload_store = database/tmp/upload_store
nginx_upload_path = /_upload
```

When serving Galaxy with a prefix, as described in the serving Galaxy in a sub-directory section above, you will need to change one line in the `\_upload\_done` section. If your galaxy instance is available from `/galaxy`, then the first line should include this prefix:

```nginx
set $dst /galaxy/api/tools;
```

### Protect Galaxy Reports

Galaxy can run a separate reports app which gives useful information about your Galaxy instance.
To setup this reports app, have a look here https://docs.galaxyproject.org/en/master/admin/reports.html and here http://galacticengineer.blogspot.de/2015/06/exposing-galaxy-reports-via-nginx-in.html

After succesfully following the blogpost you will have your galaxy reports available at e.g. http://yourgalaxy/reports
To secure this page to only galaxy administrators, adjust your nginx config with the following snippets:

```nginx
# Add these snippets to your galaxy nginx configuration to make the reports
# daemon running on the default port 9001 available under the same address
# as your galaxy instance. In addition, the reports app will only be available
# to admins logged in to the galaxy instance.

upstream reports {
    server localhost:9001;
}

server {          # This you should already have.
    listen   80;
    (..)          # The rest of your nginx configuration for galaxy

    location /reports {             # the section to make reports available
        proxy_pass  http://reports; # on the same host as your galaxy at e.g. http://galaxy/reports 
        proxy_set_header   X-Forwarded-Host $host;
        proxy_set_header   X-Forwarded-For  $proxy_add_x_forwarded_for;
        satisfy any;                # Restrict access
        deny all;
        auth_request /auth;
    }
    location /auth {
        # The used galaxy api endpoint is only available to galaxy admins and thus limits the access
        # to only logged in admins.
        proxy_pass http://localhost/api/configuration/dynamic_tool_confs;
        proxy_pass_request_body off;
        proxy_set_header Content-Length "";
        proxy_set_header X-Original-URI $request_uri;
    }
    (..)
}
```

### External User Authentication

- [Nginx for External Authentication](https://galaxyproject.org/admin/config/nginx-external-user-auth/)
- [Built-in Galaxy External Authentication](../authentication.html)
