Galaxy Interactive Environments (GIEs)
======================================

GIEs were a new feature back in Galaxy 15.05, leading with the release of the
IPython IE. They were presented at GCC2015, and the RStudio IE was released as
part of 15.07.

A GIE is a docker container, launched by Galaxy, proxied by Galaxy, with some
extra sugar inside the container to allow users to interact easily with their
Galaxy histories.

How GIEs Work
-------------

A GIE is primarily composed of a Docker container, and the Galaxy visualization
component. GIE's are essentially visualization plugins which abuse the fact
that they're rendered with mako templates. The mako templating language used in
Viz plugins allows running python code, which in turn allows for us to launch
docker containers. Once this container is launched, we notify a proxy built
into Galaxy which helps coordinate a 1:1 mapping of users and their docker containers.

Here's a simple diagram recapping the above:

.. image:: interactive_environments.*

Deploying GIEs
--------------

Deploying GIEs is not a trivial operation. They have complex interactions with
numerous services, you'll need to be a fairly competent SysAdmin to debug all
of the possible problems that can occur during deployment. After the initial
hurdle, most find that GIEs require little to no maintenance.

Setting up the Proxy
^^^^^^^^^^^^^^^^^^^^

Currently the Galaxy proxy is a NodeJS+Sqlite3 proxy. 

- Node has recently upgraded, and our proxy is pinned to an old version of
  sqlite3. As such you'll currently need to have an older version of Node
  available (0.10.X - 0.11.X vintage).
- We're working on solutions in this space to provide a better deployment
  mechanism here and fewer dependencies.
- Please note that if you have NodeJS installed under Ubuntu, it often
  installs to ``/usr/bin/nodejs``, whereas ``npm`` expects it to be
  ``/usr/bin/node``. You will need to create that symlink yourself.

Once Node and npm are ready to go, you'll need to install the dependencies::

    $ cd $GALAXY_ROOT/lib/galaxy/web/proxy/js
    $ npm install

Running ``node lib/main.js --help`` should produce some useful help text::

    Usage: main [options]

    Options:

    -h, --help             output usage information
    -V, --version          output the version number
    --ip <n>               Public-facing IP of the proxy
    --port <n>             Public-facing port of the proxy
    --cookie <cookiename>  Cookie proving authentication
    --sessions <file>      Routes file to monitor
    --verbose

There are two ways to handle actually running the proxy. The first is to have
Galaxy automatically launch the proxy as needed, the second is to manage it
with something like Supervisord. The command for launching the proxy manually
(or via supervisord) is::

    $ node $GALAXY_ROOT/lib/galaxy/web/proxy/js/main.js --ip 0.0.0.0 \
        --port 8800 --sessions $GALAXY_ROOT/database/session_map.sqlite \
        --cookie galaxysession --verbose

Configuring the Proxy
^^^^^^^^^^^^^^^^^^^^^

Configuration is all managed in ``galaxy.ini``::

    dynamic_proxy_manage=True
    dynamic_proxy_session_map=database/session_map.sqlite
    dynamic_proxy_bind_port=8800
    dynamic_proxy_bind_ip=0.0.0.0
    dynamic_proxy_debug=True

As you can see most of these variables map directly to the command line
arguments to the NodeJS script. There are a few extra parameters which merit
individual discussion::

    dynamic_proxy_external_proxy=True
    dynamic_proxy_prefix=gie_proxy

The first option says that you have Galaxy and the Galaxy NodeJS proxy wrapped
in an upstream proxy like Apache or NGINX. If you're using an upstream proxy, then
you'll need to set this to true. This will cause Galaxy to connect users to the
same port as Galaxy is being served on (so 80/443), rather than directing them
to ``:8800``.

The second option is closely entertwined with the first option. When Galaxy is
accessed, it sets a cookie. This cookie generally cannot be sent with requests
to different domains and different ports, so Galaxy and the dynamic proxy must
be accessible on the same port and protocol. A further restriction is the
cookie path; if you're running Galaxy under a URL like
``https://f.q.d.n/galaxy/``, the cookie is only accessible to URLs that look
like ``https://f.q.d.n/galaxy/*``. Galaxy and the Galaxy NodeJS proxy will take
care of most of this for you, but you should be aware of how it functions. If
your ``galaxysession`` cookie is not available in your request to the proxy
URL, it will through up an error and you won't be able to connect. Back on
topic, specifically, the second option sets the URL path that's used to
differentiate requests that should go through the proxy to those that should go
to Galaxy. You will need to add special upstream proxy configuration to handle
this, and you'll need to use the same ``dynamic_proxy_prefix`` in your
``galaxy.ini`` that you use in your URL routes.

Apache::

    # IPython specific. Other IEs may require their own routes.
    ProxyPass        /galaxy/gie_proxy/ipython/api/kernels ws://localhost:8800/galaxy/gie_proxy/ipython/api/kernels

    # Global GIE configuration
    ProxyPass        /galaxy/gie_proxy http://localhost:8800/galaxy/gie_proxy
    ProxyPassReverse /galaxy/gie_proxy http://localhost:8800/galaxy/gie_proxy

    # Normal Galaxy configuration
    ProxyPass        /galaxy http://localhost:8000/galaxy
    ProxyPassReverse /galaxy http://localhost:8000/galaxy

Please note you will need to be using apache2.4 with ``mod_proxy_wstunnel``.

Nginx::

    # TODO, please PR / ping erasche on IRC if you have samples


Docker on Another Host
^^^^^^^^^^^^^^^^^^^^^^










