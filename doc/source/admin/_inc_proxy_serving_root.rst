This configuration assumes that Galaxy will be the only site on your server using the given hostname (e.g.
``https://galaxy.example.org``).

Beginning with Galaxy Release 18.01, the default application server that Galaxy runs under is uWSGI. Because of this,
the native high performance uWSGI protocol should be used for communication between |PROXY| and Galaxy, rather
than HTTP. Legacy instructions for proxying via HTTP can be found in the `Galaxy Release 17.09 proxy documentation`_.

Since |PROXY| is more efficient than uWSGI at serving static content, it is best to serve it directly, reducing the load
on the Galaxy process and allowing for more effective compression (if enabled), caching, and pipelining. Directives to
do so are included in the example below.
