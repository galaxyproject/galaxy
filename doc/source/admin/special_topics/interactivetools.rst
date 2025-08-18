.. _interactivetools:

Galaxy InteractiveTools
=======================

Galaxy Interactive Tools allows launching a container-backed Galaxy Tool
and enabling a Galaxy User to gain access to content inside in real-time.


How Galaxy InteractiveTools work
--------------------------------

A InteractiveTool is defined in the same familiar way as standard Galaxy Tools,
but are specified with ``tool_type="interactive"``, and providing additional
entry point information:

.. code-block:: xml

        <entry_points>
            <entry_point name="Display name">
                <port>80</port>
                <url><![CDATA[optional/path/can/be/${templated}]]></url>
            </entry_point>
        </entry_points>

**Note** that name, port, and url are each able to be templated from the InteractiveTool's parameter dictionary.


Some important benefits of using Galaxy InteractiveTools
--------------------------------------------------------

- You can have and access **any number of InteractiveTools at a time** (admin configurable)
- If you accidentally close the **InteractiveTool browser window**, you can **regain access** by selecting from a **list of active InteractiveTools**
- A single **InteractiveTool** can **grant access** to **multiple running applications, servers, and interfaces**
- **InteractiveTools** can be **added to** Galaxy **Workflows**
- **InteractiveTools** are **bonafide Galaxy Tools**; just specify **tool_type as "interactive"** and list the ports you want to expose
- **InteractiveTools** can be **added** to and **installed from the ToolShed**.
- **R Shiny apps**, **Javascript-based VNC** access to desktop environments, **genome-browsers-in-a-box**, **interactive notebook environments**, etc, are all possible with **InteractiveTools**
- **InteractiveTools** typically run as software (e.g. Docker) containers in an isolated environment



Server-side configuration of Galaxy InteractiveTools
----------------------------------------------------


Basic configuration
^^^^^^^^^^^^^^^^^^^

For production deployments and additional considerations please see the `Galaxy Interactive Tools Tutorial <https://training.galaxyproject.org/training-material/topics/admin/tutorials/interactive-tools/tutorial.html>`__.

The ``galaxy.yml`` file will need to be populated as seen in
``config/galaxy.yml.interactivetools``.

Galaxy InteractiveTool routing by default relies on wildcard subdomain routes and a proxy server that forwards requests to a running container.
For users who manage their own DNS, you can set the appropriate A records to redirect
``*.interactivetool.yourdomain``.

``gravity`` will automatically start the needed proxy server.

The following configuration is only recommended for local testing, as users will directly connect to the InteractiveTool Proxy.
In a production setup an upstream proxy should route requests to the proxy via the ``*.interactivetool.yourdomain`` subdomain,
or use path-based proxying for interactive tools that support it (``requires_domain=False``, see below for more details).

Set these values in ``galaxy.yml``:

.. code-block:: yaml

    gravity:
      gx_it_proxy:
        enable: true
        port: 4002

      #handlers:
      #  handler:
      #    processes: 3
      #    pools:
      #      - job-handlers
      #      - workflow-schedulers

    galaxy:
      interactivetools_enable: true
      interactivetools_map: database/interactivetools_map.sqlite

      # outputs_to_working_directory will provide you with a better level of isolation. It is highly recommended to set
      # this parameter with InteractiveTools.
      outputs_to_working_directory: true

      # `galaxy_infrastructure_url` needs to be reachable from IT containers.
      # For local development you can map arbitrary hostnames. See `job_conf.yml.interactivetools`
      # for an example.
      # In the local development case you should use the `http` protocol (e.g http://localhost:8080) to access
      # your Galaxy, so saving notebooks doesn't fail due to invalid certificates.
      galaxy_infrastructure_url: http://localhost:8080

      # Do not set the following 2 options if you are using an upstream proxy server like nginx
      interactivetools_upstream_proxy: false
      interactivetools_proxy_host: localhost:4002


The ``gx-it-proxy`` config relates to an important service in the InteractiveTool infrastructure: the InteractiveTool
proxy. ``gx-it-proxy`` runs as a separate process listening at port 4002 (by default). HTTP requests are decoded based on
the URL and headers, then somewhat massaged, and finally forwarded to the correct entry point port of the target InteractiveTool.

.. note::

    Entry point mappings used by the proxy are stored on a SQLite database file located at ``interactivetools_map``. In
    `some situations <https://www.sqlite.org/whentouse.html#situations_where_a_client_server_rdbms_may_work_better>`_,
    SQLite may not be the best choice. A common case is a high-availability production setup, meaning that multiple
    copies of Galaxy are running on different servers behind a load balancer.

    For these situations, there exists an optional |configuration option interactivetoolsproxy_map|_ that allows using
    any database supported by SQLAlchemy (it overrides ``interactivetools_map``).

.. |configuration option interactivetoolsproxy_map| replace:: configuration option ``interactivetoolsproxy_map``
.. _configuration option interactivetoolsproxy_map: ../config.html#interactivetoolsproxy-map

.. note::

    A previous config option ``interactivetools_shorten_url`` was removed in commit `#73100de <https://github.com/galaxyproject/galaxy/pull/16795/commits/73100de17149ca3486c83b8c6ded74987c68a836>`_
    since similar functionality is now default behavior. Setting ``interactivetools_shorten_url`` to ``true`` shortened
    long interactive tool URLs (then default) from e.g.

        ``8c24e5aaae1db3a3-d0fc9f05229e40259142c4d8b5829797.interactivetoolentrypoint.interactivetool.mygalaxy.org``

    down to

        ``8c24e5aaae1db3a3-d0fc9f0522.interactivetool.mygalaxy.org``

    Now, all interactive tool URLs are similarly short, e.g.

        ``24q1dbzrknq1v-1a1p13jnahscj.ep.interactivetool.mygalaxy.org``

    Note that the previous ``.interactivetoolentrypoint`` part has been shortened down to ``.ep``, but this is now always included.
    For this reason, URLs are now up to ``3`` character longer than was previously the case when ``interactivetools_shorten_url``
    was set to ``true``. For deployments that require URLs to be shorter than a specific limit (for example ``63`` characters for some kubernetes
    setups), this slight ``3`` character increase could cause the URLs to break the limit. If so, please adjust the
    ``interactivetools_prefix`` config (default value: ``interactivetool``) to counter this.

You will also need to enable a docker destination in the job_conf.xml file.
An example ``job_conf.yml`` file as seen in ``config/job_conf.yml.interactivetools``:

.. code-block:: yaml

    ## A sample job config for InteractiveTools using local runner. ##

    runners:
      local:
        load: galaxy.jobs.runners.local:LocalJobRunner
        workers: 4

    # Uncomment if dynamic handlers are defined in "gravity:handlers" section in galaxy.yml
    #
    #handling:
    #  assign:
    #    - db-skip-locked

    execution:
      default: docker_dispatch
      environments:
        local:
          runner: local

        docker_local:
          runner: local
          docker_enabled: true
          #docker_volumes: $defaults,/mnt/galaxyData/libraries:ro,/mnt/galaxyData/indices:ro
          #docker_volumes_from: parent_container_name
          #docker_memory: 24G
          #docker_sudo: false
          #docker_sudo_cmd: /usr/bin/sudo -extra_param
          #docker_net: bridge
          #docker_auto_rm: true
          #docker_set_user: $UID
          docker_set_user:

          # InteractiveTools do need real hostnames or URLs to work - simply specifying IPs will not work.
          # If you develop interactive tools on your 'localhost' and don't have a proper domain name
          # you need to tell all Docker containers a hostname where Galaxy is running.
          # This can be done via the add-host parameter during the `docker run` command.
          # 'localhost' here is an arbitrary hostname that matches the IP address of your
          # Galaxy host. Make sure this hostname ('localhost') is also set in your galaxy.yml file, e.g.
          # `galaxy_infrastructure_url: http://localhost:8080`.
          #docker_run_extra_arguments: --add-host localhost:host-gateway

          #docker_cmd: /usr/local/custom_docker/docker
          #docker_host:
          #docker_container_id_override: busybox:1.36.1-glibc
          #docker_default_container_id: busybox:1.36.1-glibc
          #require_container: true
          #container_monitor: true
          #container_monitor_result: file
          #container_monitor_command: python /path/to/galaxy/lib/galaxy_ext/container_monitor/monitor.py
          #container_monitor_get_ip_method: null
          #container_resolvers_config_file: null
          #container_resolvers:

        docker_dispatch:
          runner: dynamic
          type: docker_dispatch
          docker_destination_id: docker_local
          default_destination_id: local


The Galaxy currently contains a sizable collection of **InteractiveTools** directly in the
code base. To be enabled, they need to be commented in or added to the ``config/tool_conf.xml``:

.. code-block:: xml

    <toolbox monitor="true">
        <tool file="interactive/interactivetool_jupyter_notebook.xml" />
        <tool file="interactive/interactivetool_cellxgene.xml" />
    </toolbox>


A InteractiveTool is defined in the same familiar way as standard Galaxy Tools,
but are specified with ``tool_type="interactive"``, and providing additional
entry point information:

.. code-block:: xml

        <entry_points>
            <entry_point name="Display name">
                <port>80</port>
                <url><![CDATA[optional/path/can/be/${templated}]]></url>
            </entry_point>
        </entry_points>


**Note** that name, port, and url are each able to be templated from the InteractiveTool's parameter dictionary.


Path-based InteractiveTools
^^^^^^^^^^^^^^^^^^^^^^^^^^^

As will become clear in the NGINX tutorial below, the default configuration of InteractiveTools in a production setting gives rise
to some complications - in particular the need to set up a wildcard DNS entry and procuring a wildcard SSL certificate.
This is necessary to support unique URLs for InteractiveTool instances using only the domain part of the URL,
e.g. ``https://24q1dbzrknq1v-1a1p13jnahscj.ep.interactivetool.myserver.net/``. Wildcard SSL certificates are less convenient
than regular certificates and are inherently less safe and thus prohibited at many institutions. Hence,
path-based interactive tools was implemented as an alternative way to configure InteractiveTools. Path-based URLs to
InteractiveTools look something like this: ``https://myserver.net/interactivetool/ep/24q1dbzrknq1v/1a1p13jnahscj/``.
To enable path-based InteractiveTools, set ``requires_domain="False"`` in the relevant ``entry_point`` tag in the tool XML:

.. code-block:: xml

        <entry_points>
            <entry_point name="Display name" requires_domain="False">
                <port>80</port>
            </entry_point>
        </entry_points>


Path-based InteractiveTools are somewhat more difficult to configure than domain-based ITs. This is due to the fact that the web
server within an InteractiveTool container now must serve the contents under a path prefix. There are two main ways this can be solved:

1.  Relative links. If the web server embedded in the InteractiveTool only serves HTML pages with relative links then the
    contents can be served at any level in the path hierarchy. The InteractiveTool proxy then strips away the "path prefix"
    or "entry point path" part of the URL (e.g. ``interactivetool/ep/24q1dbzrknq1v/1a1p13jnahscj/``) from forwarded HTTP requests
    so that the InteractiveTool web server operates like if it was served at the top level (directly under ``/``). Since all
    links are relative, the web browser will automatically handle merging of the path prefix with the relative path appended
    by the InteractiveTool.

    This setup is the default setup provided by the tool XML example above, but to be more explicit one can also set
    ``requires_path_in_url="False"`` in the ``entry_point`` tag. As the web service operates with relative links it does
    not need to know the entry point path under which it is served.

2.  Absolute links. Unfortunately many relevant services are implemented with absolute links, i.e. starting
    at the top-level ``/``. For such InteractiveTools to work with path-based URLs the contained web server
    needs to be configured with the path prefix/entry point path under which the content should be served. Two issues then
    needs to be considered:

    a.  How to inject the path prefix into the InteractiveTool at run-time?

        Two injection mechanisms are provided, injecting the path prefix as an environment variable or as an HTTP header.

        i.  Injecting the path prefix as an environment variable:

            .. code-block:: xml

                <entry_points>
                    <entry_point name="Display name" label="mytool" requires_domain="False" requires_path_in_url="True">
                        <port>80</port>
                    </entry_point>
                </entry_points>

                <environment_variables>
                    <environment_variable name="EP_PATH" inject="entry_point_path_for_label">mytool</environment_variable>
                </environment_variables>


            Here, the entry point is attached a ``label="mytool"`` attribute. This label is then used by the ``entry_point_path_for_label``
            injection mechanism to identify the entry point whose path shall be injected into the environment variable, here ``EP_PATH``.
            This environment variable must then be mobilized in the InteractiveTool tool XML to properly configure the contained web server,
            such as in the ``command`` tag of the JupyTool InteractiveTool:

            .. code-block:: xml

                <command><![CDATA[
                    [...]
                    export PROXY_PREFIX=\${EP_PATH%/ipython*} &&
                    [...]
                ]]>
                </command>


            If we follow the same entry point path example as above, the ``PROXY_PREFIX`` variable will in this case be set to the value
            ``interactivetool/ep/24q1dbzrknq1v/1a1p13jnahscj/ipython``. This variable is further parsed by the Jupyter Notebook software
            as a configuration of the path prefix under which the contents will be served.

        ii. Injecting the path prefix as an HTTP header:

            .. code-block:: xml

                <entry_points>
                    <entry_point name="Display name" label="mytool" requires_domain="False" requires_path_in_header_named="X-My-Header">
                        <port>80</port>
                    </entry_point>


            Here, the InteractiveTool proxy service is informed to inject the path prefix as a HTTP header, e.g.
            ``X-My-Header="interactivetool/ep/24q1dbzrknq1v/1a1p13jnahscj/`` in the proxied requests to the InteractiveTool server.

    b.  Does the InteractiveTool service require that the full path is provided in the URL?

        When ``requires_path_in_url="True"`` in the ``entry_point`` tag, the InteractiveTool proxy service forwards the HTTP requests
        with the full path intact.

    Both values of ``requires_path_in_url`` can be combined with both injection mechanisms, leading two four configuration variants
    for path-based InteractiveTools. Choosing the correct one depends on the implementation of the web server contained in the
    InteractiveTool and can be a bit tricky to get correct. In some cases, none of these options will work. One solution can then
    be to configure another highly customized proxy web server within the InteractiveTool, e.g. using NGINX.


NGINX proxy server configuration (in production)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you want to use nginx as an proxy server upstream of a Galaxy installation (in a production setting), you can use the following
server section to route domain-based requests to the InteractiveTool proxy:

.. code-block:: nginx

    server {
        # Listen on port 443
        listen       *:443 ssl;
        # Match all requests for the interactive tools subdomain
        server_name  *.interactivetool.localhost;

        # Route all domain-based interactive tool requests to the InteractiveTool proxy application
        location / {
            proxy_redirect off;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_pass http://localhost:4002;
        }
    }


Note that this nginx example uses https, so you need to have a wildcard certificate for your domain,
and you need to adjust ``galaxy_infrastructure_url`` as appropriate.

You should also set up nginx to route path-based InteractiveTool URLs to the InteractiveTool proxy.
Path-based InteractiveTool URLs will only be created for tools that have defined ``requires_domain=False`` in the tool
XML file (which signals that the web server running on the container are configured to operate at a subpath under the main
Galaxy installation). Hence, no wildcard DNS configuration or wildcard SSL certificates are needed for path-based
interactive tools.

To support path-based interactive tools through nginx proxy, add the following to the main Galaxy "server"
section (serving port 443):

.. code-block:: nginx

        # Route all path-based interactive tool requests to the InteractiveTool proxy application
        location ~* ^/(interactivetool/.+)$ {
            proxy_redirect off;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_pass http://localhost:4002;
        }


This example config works for default values of ``interactivetools_base_path`` and ``interactivetools_prefix`` as defined in
``galaxy.yml``. For other values, you will need to adjust the location patterns accordingly.

In both nginx config examples, you might want to replace localhost with your server domain (or possibly
``127.0.0.1``), depending on your server setup.


Job runner configuration in production
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

InteractiveTools have been enabled for the Condor, Slurm, Pulsar and Kuberneters job runner.
A destination configuration for Condor may look like this:

.. code-block:: xml

    condor:
      runner: condor
      docker_enabled: true
      docker_sudo: false


**Note on resource consumption:** Keep in mind that Distributed Resource
Management (DRM) / cluster systems may have a maximum runtime configured for
jobs. From the Galaxy point of view, such a container could run as long as the
user desires, this may not be advisable and an admin may want to restrict the
runtime of InteractiveTools *(and jobs in general)*. However, if the job is
killed by the DRM, the user is not informed beforehand and data in the container
could be discarded.
