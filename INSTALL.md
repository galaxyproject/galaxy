# Installation

We've developed the templates and containers such that they can be run through an Apache proxy using
SSL. This requires some trivial apache configuration to support.

## Requirements

 * [mod_proxy](http://httpd.apache.org/docs/2.4/mod/mod_proxy.html)
 * [mod_proxy_http](http://httpd.apache.org/docs/2.4/mod/mod_proxy_http.html)
 * [mod_rewrite](http://httpd.apache.org/docs/2.4/mod/mod_rewrite.html)

## Apache Configuration

Here is the relevant configuration

```apache
RewriteEngine On
RewriteRule  ^/rstudio/([0-9]+)/(.*)$  http://localhost:$1/rstudio/$1/$2 [P,L]
```

## Nginx Configuration

Please submit it if you write it!

## Template Configuration

Normally containers are accessed via URLs that look like:

```
http://fqdn:11235/rstudio/11235/
```

In order to secure them we want to access them via URLs that look like:

```
http://fqdn/rstudio/11235/
```
