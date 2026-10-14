# Caching Tool Shed install info with NGINX

`/api/repositories/get_repository_revision_install_info` is the most requested route on a
busy Tool Shed. Every Galaxy server installing or reinstalling a repository calls it, once
per repository, and the answer for a given `name` / `owner` / `changeset_revision` only
changes when that revision's metadata is rebuilt. That makes it a good candidate for
proxy caching.

The Tool Shed helps by sending validators on both install info routes:

- `/api/repositories/get_repository_revision_install_info` (the legacy route Galaxy uses)
- `/api/repositories/install_info`

Each `200` carries:

```
ETag: "aa5cf0…"
Cache-Control: public, max-age=86400
```

The `ETag` is a hash of the response body, so it changes whenever the payload changes for
any reason -- a metadata reset, an edited repository description, or a change in one of the
repository's dependencies. A client that sends `If-None-Match` with a matching tag gets a
`304 Not Modified` with an empty body.

Note that Galaxy's own install client issues a plain `GET` with no conditional headers and
keeps no local cache, so it will not produce `304`s by itself. The benefit comes from the
proxy in front of the Tool Shed, which absorbs the repeated requests, and from clients such
as ephemeris or browsers that do revalidate.

## NGINX configuration

Declare a cache zone in the `http` block:

```nginx
proxy_cache_path /var/cache/nginx/toolshed
                 levels=1:2
                 keys_zone=toolshed_install_info:10m
                 max_size=1g
                 inactive=24h
                 use_temp_path=off;
```

Then add a `location` for the install info routes inside the Tool Shed `server` block,
*before* the general `location /` that proxies everything else:

```nginx
location ~ ^/api/repositories/(get_repository_revision_install_info|install_info)$ {
    proxy_pass http://tool_shed;

    proxy_cache toolshed_install_info;

    # Key on the parameters that actually determine the response. Anything else in the
    # query string -- notably an API key -- is deliberately left out, so one cached entry
    # serves every caller and no secret ends up in the cache key.
    proxy_cache_key "$uri|$arg_name|$arg_owner|$arg_changeset_revision";

    # The 24h lifetime comes from the Cache-Control header the Tool Shed sends; this is
    # only a fallback for responses that arrive without one. Shorten it here if you want
    # metadata resets to become visible sooner.
    proxy_cache_valid 200 24h;
    proxy_cache_valid 404 1m;

    # On expiry, revalidate with If-None-Match instead of refetching the body. The Tool
    # Shed answers 304 and NGINX refreshes the entry in place.
    proxy_cache_revalidate on;

    # One request populates a cold entry; the rest wait for it rather than stampeding
    # the Tool Shed.
    proxy_cache_lock on;
    proxy_cache_lock_timeout 10s;

    # Keep serving the stale copy while the refresh happens in the background, and if
    # the Tool Shed is down or slow.
    proxy_cache_background_update on;
    proxy_cache_use_stale updating error timeout http_500 http_502 http_503 http_504;

    # These responses are identical for every caller, so a session cookie must neither be
    # stored in the cache nor prevent caching in the first place.
    proxy_ignore_headers Set-Cookie;
    proxy_hide_header Set-Cookie;

    add_header X-Cache-Status $upstream_cache_status always;
}
```

`upstream tool_shed` here is whatever upstream block already proxies your Tool Shed.

## Verifying

`X-Cache-Status` reports what NGINX did with each request:

```console
$ curl -sI 'https://toolshed.example.org/api/repositories/get_repository_revision_install_info?name=column_maker&owner=devteam&changeset_revision=0b4e36026794' | grep -i -E 'x-cache-status|etag|cache-control'
X-Cache-Status: MISS
ETag: "aa5cf0…"
Cache-Control: public, max-age=86400

$ curl -sI '…same url…' | grep -i x-cache-status
X-Cache-Status: HIT
```

To confirm the Tool Shed's own conditional handling, replay the `ETag`:

```console
$ curl -s -o /dev/null -w '%{http_code}\n' \
    -H 'If-None-Match: "aa5cf0…"' \
    'http://localhost:9009/api/repositories/get_repository_revision_install_info?name=…'
304
```

## Invalidating after a metadata reset

Resetting metadata on a repository changes the install info for its revisions, but a cached
entry is served until it expires. With the configuration above that is up to 24 hours.

Open source NGINX has no `proxy_cache_purge` directive (it is a commercial feature), so the
options are:

- Lower `proxy_cache_valid` and the `max-age` the Tool Shed sends if you reset metadata
  often and need changes to propagate faster.
- Delete the cache directory and reload NGINX after a bulk metadata reset:

  ```console
  $ rm -rf /var/cache/nginx/toolshed/*
  $ nginx -s reload
  ```

- Add a bypass so administrators can force a refresh of a single entry:

  ```nginx
  proxy_cache_bypass $http_x_refresh_cache;
  ```

  and then `curl -H 'X-Refresh-Cache: 1' …`. Restrict this to trusted networks -- it lets a
  caller push load straight through to the Tool Shed.
