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
- **Native, out-of-the box support for InteractiveTools** in Galaxy via uWSGI proxying
- **InteractiveTools** are **bonafide Galaxy Tools**; just specify **tool_type as "interactive"** and list the ports you want to expose
- **InteractiveTools** can be **added** to and **installed from the ToolShed**.
- **R Shiny apps**, **Javascript-based VNC** access to desktop environments, **genome-browsers-in-a-box**, **interactive notebook environments**, etc, are all possible with **InteractiveTools**



Server-side configuration of Galaxy InteractiveTools
----------------------------------------------------

The ``galaxy.yml`` file will need to be populated as seen in
``config/galaxy.yml.interactivetools``.

Galaxy InteractiveTool routing relies on wildcard subdomain routes. For users
who manage their own DNS, you can set the appropriate A records to redirect
``*.interactivetool.yourdomain``, following format seen below.

It's not recommended for production, but for a quick local deployment
``localhost.blankenberglab.org`` is a domain record provided by Dan Blankenberg
(a Galaxy contributor and the architect of ITs) configured with the appropriate
wildcard redirect to 127.0.0.1, which you can use that in place of
``<server address>`` to resolve to your local machine.

In the ``uwsgi:`` section:

.. code-block:: yaml

  http-raw-body: true
  # master: true

  interactivetools_map: database/interactivetools_map.sqlite
  python-raw: scripts/interactivetools/key_type_token_mapping.py
  route-host: ^([A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)-([A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)\.([A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)\.(interactivetool\.<server address>:8080)$ goto:interactivetool
  route-run: goto:endendend
  route-label: interactivetool
  route-host: ^([A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)-([A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)\.([A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)\.(interactivetool\.<server address>:8080)$ rpcvar:TARGET_HOST rtt_key_type_token_mapper_cached $1 $3 $2 $4 $0 5
  route-if-not: empty:${TARGET_HOST} httpdumb:${TARGET_HOST}
  route: .* break:404 Not Found
  route-label: endendend


In the ``galaxy:`` section:

.. code-block:: yaml

  interactivetools_enable: true
  interactivetools_map: database/interactivetools_map.sqlite
  galaxy_infrastructure_url: http://<server address>.org:8080


The admin should modify the ``route-host`` and ``interactivetools_prefix`` to match their preferred configuration.

An example ``job_conf.xml`` file as seen in ``config/job_conf.xml.interactivetools``:

.. code-block:: xml

        <job_conf>
            <plugins>
                <plugin id="local" type="runner" load="galaxy.jobs.runners.local:LocalJobRunner" workers="4"/>
            </plugins>
            <destinations default="docker_dispatch">
                <destination id="local" runner="local"/>
                <destination id="docker_local" runner="local">
                  <param id="docker_enabled">true</param>
                  <param id="docker_volumes">$galaxy_root:ro,$tool_directory:ro,$job_directory:rw,$working_directory:rw,$default_file_path:ro</param>
                  <param id="docker_sudo">false</param>
                  <param id="docker_net">bridge</param>
                  <param id="docker_auto_rm">true</param>
                  <param id="require_container">true</param>
                </destination>
                <destination id="docker_dispatch" runner="dynamic">
                    <param id="type">docker_dispatch</param>
                    <param id="docker_destination_id">docker_local</param>
                    <param id="default_destination_id">local</param>
                </destination>
            </destinations>
        </job_conf> 


Alternatively to the local job runner, InteractiveTools have been enabled for the condor job runner, e.g.:

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
