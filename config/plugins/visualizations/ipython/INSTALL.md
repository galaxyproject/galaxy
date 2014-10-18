# Installation

We've developed the templates and containers such that they can be run through an Apache proxy using
SSL. This requires some non-trivial apache configuration to support.

## Requirements

 * `mod_proxy`
 * `mod_proxy_http`
 * `mod_proxy_wstunnel`
 * `mod_headers`

IPython makes use of WebSockets which we need to proxy in apache. Support was added to `apache2.4`
for this, which is available in `Ubuntu 14.04`. There are tutorials on the internet for backporting
the websockets module, and installing `apache2.4` PPAs.

## Apache Configuration

Here is the relevant configuration

```apache
RewriteEngine On
SetEnvIf Request_URI "/ipython/([0-9]+)/api/kernels/" DOCKER_PORT=$1
RewriteRule     ^/ipython/([0-9]+)/api/kernels/(.*)$   ws://127.0.0.1:$1/ipython/$1/api/kernels/$2 [P,L]
RewriteRule     ^/ipython/([0-9]+)/(.*)$             http://localhost:$1/ipython/$1/$2 [P,L]
<Location /ipython/>
        # spoof headers to make notepad accept the request as coming from the same origin
        Header set Origin "http://127.0.0.1:%{DOCKER_PORT}e"
        RequestHeader set Origin "http://127.0.0.1:%{DOCKER_PORT}e"
</Location>
</VirtualHost>
```

We'll step through line-by-line for clarity.

```apache
SetEnvIf Request_URI "/ipython/([0-9]+)/api/kernels/" DOCKER_PORT=$1
```

Here we check the `Request_URI` for the presence for the kernel request. We do this only for the `api/kernel` subcall, as the only configuration which needs access to `DOCKER_PORT` is kernel calls.

```apache
RewriteRule ^/ipython/([0-9]+)/api/kernels/(.*)$   ws://127.0.0.1:$1/ipython/$1/api/kernels/$2 [P,L]
RewriteRule ^/ipython/([0-9]+)/(.*)$             http://localhost:$1/ipython/$1/$2 [P,L]
```

These two rules proxy `^/ipython/` requests to their correct locations. API requests for the IPython kernel are routed through the wstunnel (WebSocket) proxy, while all other requests go through HTTP. There are modified listed after both, `[P,L]`. `P` specifies a proxy, and `L` specifies this is the last rule, to prevent the second rewrite statement from matching all kernel calls.

```apache
<Location /ipython/>
        # spoof headers to make notepad accept the request as coming from the same origin
        Header set Origin "http://127.0.0.1:%{DOCKER_PORT}e"
        RequestHeader set Origin "http://127.0.0.1:%{DOCKER_PORT}e"
</Location>
```

The WebSocket server in IPython pays attention to Cross-Origin-Requests and will through up a 500 Internal Server Error (in docker) if you attempt to send it bad data. Thus, we use the extracted port number from the earlier `SetEnvIf` request in order to obtain the port that IPython will actually receive connections from.

## Template Configuration

Normally containers are accessed via URLs that look like:

```
http://fqdn:11235/ipython/11235/ipython_notebook.ipynb
```

In order to secure them we want to access them via URLs that look like:

```
http://fqdn/ipython/11235/ipython_notebook.ipynb
```

This change needs to be realised in the template file. At the very end of the template there is a section of HTML code which looks like the following:

```html
<object data="http://${HOST}:${PORT}/ipython/${PORT}/notebooks/ipython_galaxy_notebook.ipynb" height="100%" width="100%">
    <embed src="http://${HOST}:${PORT}/ipython/${PORT}/notebooks/ipython_galaxy_notebook.ipynb" height="100%" width="100%">
    </embed>
</object>
```

Just remove the `:${PORT}` and you're ready to go! It should look like this:

```html
<object data="http://${HOST}/ipython/${PORT}/notebooks/ipython_galaxy_notebook.ipynb" height="100%" width="100%">
    <embed src="http://${HOST}/ipython/${PORT}/notebooks/ipython_galaxy_notebook.ipynb" height="100%" width="100%">
    </embed>
</object>
```
