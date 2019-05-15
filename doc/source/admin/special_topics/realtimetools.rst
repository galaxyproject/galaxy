Galaxy RealTimeTools
=====================================

A Galaxy RealTimeTool allows launching a container-backed Galaxy Tool 
and enabling a Galaxy User to gain access to content inside in real-time.


How Galaxy RealTimeTools work
-----------------------------

A RealTimeTool is defined in the same familiar way as standard Galaxy Tools,
but are specified with **tool_type="realtime"**, and providing additional entry point
information:

.. code-block:: xml

        <realtime>
            <entry_point name="Display name">
                <port>80</port>
                <url><![CDATA[optional/path/can/be/${templated}]]></url>
            </entry_point>
        </realtime>

**Note** that name, port, and url are each able to be templated from the RealTimeTool's parameter dictionary.



Some important benefits of using Galaxy RealTimeTools
-----------------------------------------------------

- You can have and access **any number of RealTimeTools at a time** (admin configurable)
- If you accidentally close the **RealTimeTool browser window**, you can **regain access** by selecting from a **list of active RealTimeTools**
- A single **RealTimeTool** can **grant access** to **multiple running applications, servers, and interfaces**
- **RealTimeTools** can be **added to** Galaxy **Workflows**
- **Native, out-of-the box support for RealTimeTools** in Galaxy via uWSGI proxying
- **RealTimeTools** are **bonafide Galaxy Tools**; just specify tool_type as "realtime" and list the ports you want to expose
- **RealTimeTools** can be **added** to and **installed from the ToolShed**.
- **R Shiny apps**, **Javascript-based VNC** access to desktop environments, **genome-browsers-in-a-box**, **interactive notebook environments**, etc, are all possible with **RealTimeTools**



Server-side configuration of Galaxy RealTimeTools
-------------------------------------------------

The **galaxy.yml** file will need to be populated as seen in **config/galaxy.yml.realtime**.

In the **uwsgi:** section:

.. code-block:: yaml

  http-raw-body: true
  # master: true

  realtime_map: database/realtime_map.sqlite
  python-raw: scripts/realtime/key_type_token_mapping.py
  route-host: ^([A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)\.([A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)\.([A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)\.(realtime\.localhost:8080)$ goto:realtime
  route-run: goto:endendend
  route-label: realtime
  route-host: ^([A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)\.([A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)\.([A-Za-z0-9]+(?:-[A-Za-z0-9]+)*)\.(realtime\.localhost:8080)$ rpcvar:TARGET_HOST rtt_key_type_token_mapper_cached $2 $1 $3 $4 $0 5
  route-if-not: empty:${TARGET_HOST} httpdumb:${TARGET_HOST}
  route-label: endendend

In the **galaxy:** section:

.. code-block:: yaml

  realtime_prefix: realtime


The admin should modify the **route-host**s and **realtime_prefix** to match their preferred configuration.


An example **job_conf.xml** file as seen in **config/galaxy.yml.realtime**:

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


Alternatively to the local job runner, RealTimeTools have been enabled for the condor job runner, e.g.:

.. code-block:: xml

        <destination id="condor" runner="condor">
            <param id="docker_enabled">true</param>
            <param id="docker_sudo">false</param>
        </destination>


**Note on resource consumption:** Keep in mind that Distributed Resource Management (DRM) / cluster systems may have a maximum runtime configured for jobs. From the Galaxy point of view, such a container could run as long as the user desires, this may not be advisable and an admin may want to restrict the runtime of RealTimeTools *(and jobs in general)*. However, if the job is killed by the DRM, the user is not informed beforehand and data in the container could be discarded.

Two **example test RealTimeTools** have been defined, and can be added to the **config/tool_conf.xml**:

.. code-block:: xml

        <tool file="../test/functional/tools/realtimetool_juypter_notebook.xml" />
        <tool file="../test/functional/tools/realtimetool_cellxgene.xml" />


A few words on the condor integration
-------------------------------------

Galaxy needs to be able to stop a container gracefully. This is not a problem with the local job runner, where we assume that Docker is either running on the same host. However, if you are using production scale DRM, like condor, then your job is running
somewhere on your cluster and you can not easily **docker stop** your container. For the condor integration we are using a great
condor feature and commandline utility called **condor_ssh_to_job**. This tool (assuming your condor setup is configured correctly) will bring us directly to the host in question and we can execute the **docker stop** command. Galaxy will simply run **condor_ssh_to_job <condor_job_id> docker stop <container_name>** to stop the container gracefully.
