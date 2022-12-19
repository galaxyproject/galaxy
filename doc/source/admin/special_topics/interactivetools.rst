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



Server-side configuration of Galaxy InteractiveTools
----------------------------------------------------

For production deployments and additional considerations please see the `Galaxy Interactive Tools Tutorial <https://training.galaxyproject.org/training-material/topics/admin/tutorials/interactive-tools/tutorial.html>`__.

The ``galaxy.yml`` file will need to be populated as seen in
``config/galaxy.yml.interactivetools``.

Galaxy InteractiveTool routing relies on wildcard subdomain routes and a proxy server that forwards requests to a running container.
For users who manage their own DNS, you can set the appropriate A records to redirect
``*.interactivetool.yourdomain``.

`gravity` will automatically start the needed proxy server.

The following configuration is only recommended for local testing, as users will directly connect to the InteractiveTool Proxy.
In a production setup an upstream proxy should route requests to the proxy via the ``*.interactivetool.yourdomain`` subdomain,
or use path-based proxying for interactive tools that support it (``requires_domain=False``, see below for more details).

Set these values in `galaxy.yml`:

.. code-block:: yaml

        gravity:
          # ...
          gx_it_proxy:
            enable: true
            port: 4002
        galaxy:
          # ...
          interactivetools_enable: true
          interactivetools_map: database/interactivetools_map.sqlite
          galaxy_infrastructure_url: http://localhost:8080
          # Do not set the following 2 options if you are using an upstream proxy server like nginx
          interactivetools_upstream_proxy: false
          interactivetools_proxy_host: localhost:4002
          # ...


If you do want to use nginx as an upstream proxy server you can use the following server section to route requests to
the InteractiveTool proxy:

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

It is also possible to set up nginx to route path-based interactive tool URLs to the InteractiveTool proxy.
Path-based interactive tool URLs will only be created for tools that have defined ``requires_domain=False`` in the tool
XML file (which signals that the web server running on the container makes use of relative links and can serve
content starting from any path). A tool config variable will be added in the next version to simplify this for
tools that need to know the path to where it is served.

To support path-based interactive tools through nginx proxy, add the following to the main Galaxy "server"
section (serving port 443):

.. code-block:: nginx

        # Route all path-based interactive tool requests to the InteractiveTool proxy application
        location ~* ^/(interactivetool/access/.+)$ {
            proxy_redirect off;
            proxy_http_version 1.1;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_pass http://localhost:4002;
        }

This example config works for default values of ``interactivetools_base_path`` and ``interactivetools_prefix`` as defined in
``galaxy.yml``. For other values, you will need to adjust the location patterns accordingly. This solution also
requires ``interactivetools_shorten_url`` to be set to ``false`` (default).

In both nginx config examples, you might want to replace localhost with your server domain (or possibly
``127.0.0.1``), depending on your server setup.

You will also need to enable a docker destination in the job_conf.xml file.
An example ``job_conf.xml`` file as seen in ``config/job_conf.xml.interactivetools``:

.. code-block:: xml

        <?xml version="1.0"?>
        <!-- A sample job config for InteractiveTools using local runner. -->
        <job_conf>
            <plugins>
                <plugin id="local" type="runner" load="galaxy.jobs.runners.local:LocalJobRunner" workers="4"/>
            </plugins>
            <destinations default="docker_dispatch">
                <destination id="local" runner="local"/>
                <destination id="docker_local" runner="local">
                  <param id="docker_enabled">true</param>
                  <!-- If you have not set 'outputs_to_working_directory: true' in galaxy.yml you can remove the docker_volumes setting. -->
                  <param id="docker_volumes">$galaxy_root:ro,$tool_directory:ro,$job_directory:rw,$working_directory:rw,$default_file_path:ro</param>
                  <param id="docker_sudo">false</param>
                  <param id="docker_net">bridge</param>
                  <param id="docker_auto_rm">true</param>
                  <param id="require_container">true</param>
                  <param id="container_monitor">true</param>
                  <param id="docker_set_user"></param>
                  <!-- InteractiveTools need real hostnames or URLs to work - simply specifying IPs will not work.
                       If you develop interactive tools on your 'localhost' and don't have a proper domain name
                       you need to tell all Docker containers a hostname where Galaxy is running.
                       This can be done via the add-host parameter during the `docker run` command.
                       'localhost' here is an arbitrary hostname that matches the IP address of your
                       Galaxy host. Make sure this hostname ('localhost') is also set in your galaxy.yml file, e.g.
                       `galaxy_infrastructure_url: http://localhost:8080`.
                  -->
                  <param id="docker_run_extra_arguments">--add-host localhost:host-gateway</param>
                </destination>
                <destination id="docker_dispatch" runner="dynamic">
                    <param id="type">docker_dispatch</param>
                    <param id="docker_destination_id">docker_local</param>
                    <param id="default_destination_id">local</param>
                </destination>
            </destinations>
        </job_conf>


InteractiveTools have been enabled for the Condor, Slurm, Pulsar and Kuberneters job runner.
A destination configuration for Condor may look like this:

.. code-block:: xml

        <destination id="condor" runner="condor">
            <param id="docker_enabled">true</param>
            <param id="docker_sudo">false</param>
        </destination>


**Note on resource consumption:** Keep in mind that Distributed Resource
Management (DRM) / cluster systems may have a maximum runtime configured for
jobs. From the Galaxy point of view, such a container could run as long as the
user desires, this may not be advisable and an admin may want to restrict the
runtime of InteractiveTools *(and jobs in general)*. However, if the job is
killed by the DRM, the user is not informed beforehand and data in the container
could be discarded.

Some **example test InteractiveTools** have been defined, and can be added to
the ``config/tool_conf.xml``:

.. code-block:: xml

    <toolbox monitor="true">
        <tool file="interactive/interactivetool_jupyter_notebook.xml" />
        <tool file="interactive/interactivetool_cellxgene.xml" />
    </toolbox>
