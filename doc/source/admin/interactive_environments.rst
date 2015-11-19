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

.. image:: interactive_environments.png

Deploying GIEs
--------------

Deploying GIEs is not a trivial operation. They have complex interactions with
numerous services, you'll need to be a fairly competent SysAdmin to debug all
of the possible problems that can occur during deployment. After the initial
hurdle, most find that GIEs require little to no maintenance.

An `Ansible <http://www.ansible.com/>`__ role for installing and managing GIEs
can be found on
`Github <https://github.com/galaxyproject/ansible-interactive-environments>`__
and `Ansible Galaxy <https://galaxy.ansible.com/detail#/role/6056>`__.

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

Once Node and npm are ready to go, you'll need to install the dependencies

.. code-block:: console

    $ cd $GALAXY_ROOT/lib/galaxy/web/proxy/js
    $ npm install

Running ``node lib/main.js --help`` should produce some useful help text

.. code-block::

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
(or via supervisord) is

.. code-block::  console

    $ node $GALAXY_ROOT/lib/galaxy/web/proxy/js/lib/main.js --ip 0.0.0.0 \
        --port 8800 --sessions $GALAXY_ROOT/database/session_map.sqlite \
        --cookie galaxysession --verbose

Configuring the Proxy
^^^^^^^^^^^^^^^^^^^^^

Configuration is all managed in ``galaxy.ini``

.. code-block::  ini

    dynamic_proxy_manage=True
    dynamic_proxy_session_map=database/session_map.sqlite
    dynamic_proxy_bind_port=8800
    dynamic_proxy_bind_ip=0.0.0.0
    dynamic_proxy_debug=True

As you can see most of these variables map directly to the command line
arguments to the NodeJS script. There are a few extra parameters which merit
individual discussion

.. code-block:: ini

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

**Apache**

.. code-block:: apache

    # IPython specific. Other IEs may require their own routes.
    ProxyPass        /galaxy/gie_proxy/ipython/api/kernels ws://localhost:8800/galaxy/gie_proxy/ipython/api/kernels

    # Global GIE configuration
    ProxyPass        /galaxy/gie_proxy http://localhost:8800/galaxy/gie_proxy
    ProxyPassReverse /galaxy/gie_proxy http://localhost:8800/galaxy/gie_proxy

    # Normal Galaxy configuration
    ProxyPass        /galaxy http://localhost:8000/galaxy
    ProxyPassReverse /galaxy http://localhost:8000/galaxy

Please note you will need to be using apache2.4 with ``mod_proxy_wstunnel``.

**Nginx**

.. code-block:: nginx

    # Global GIE configuration
    location /galaxy/gie_proxy {
        proxy_pass http://localhost:8800/galaxy/gie_proxy;
        proxy_redirect off;
    }

    # IPython specific. Other IEs may require their own routes.
    location /galaxy/gie_proxy/ipython/api/kernels {
        proxy_pass http://localhost:8800/galaxy/gie_proxy/ipython/api/kernels;
        proxy_redirect off;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

If you proxy static content, you may find the following rule useful for
proxying to GIE and other visualization plugin static content.

.. code-block:: nginx

    location ~ ^/plugins/(?<plug_type>.+?)/(?<vis_name>.+?)/static/(?<static_file>.*?)$ {
        alias /path/to/galaxy-dist/config/plugins/$plug_type/$vis_name/static/$static_file;
    }

Docker on Another Host
^^^^^^^^^^^^^^^^^^^^^^

There are many reasons to run Interactive Environments on a separate host and
not on your webserver, serving Galaxy. This feature has been available since
15.07 and is used in production at the University of Freiburg.

First you need to configure a second host to be Docker enabled. In the
following we call this host ``gx-docker`` You need to start the Docker daemon
and bind it to a TCP port, not to a socket as is the default. For example
you can start the daemon with

.. code-block:: console

    $ docker -H 0.0.0.0:4243 -d

On your client, the Galaxy webserver, you can now install a Docker client. This
can also be done on older Systems like Scientific-Linux, CentOS 6, which does
not have Docker support by default. The client just talks to the Docker daemon
on host ``gx-docker``, and does not run anything itself, locally. You can test
your configuration for example by starting busybox from your client on the
Docker host with

.. code-block:: console

    $ docker -H tcp://gx-docker:4243 run -it busybox sh

So far so good! Now we need to configure Galaxy to use our new Docker host
to start the Interactive Environments. For that we need to edit the IPython GIE
configuration, ``ipython.ini`` to use our custom docker host

.. code-block:: ini

    [main]

    [docker]
    command = docker -H tcp://gx-docker:4243 {docker_args}
    image = bgruening/docker-ipython-notebook:dev
    docker_hostname = gx-docker

Please adapt your ``command`` and the ``image`` as needed.

As next step we need to configure a share mount point between the Docker host
and Galaxy. Unfortunately, this can not be a NFS mount. Docker does not like
NFS yet. You could for example use a sshfs mount with the following script

.. code-block:: bash

    if mount | grep ^gx-docker:/var/tmp/gx-docker; then
        echo "/var/tmp/gx-docker already mounted."
    else
        sshfs gx-docker:/var/tmp/gx-docker /var/tmp/gx-docker
        echo 'Mounting ...'
    fi

This will let Galaxy and the Docker host share temporary files.

Interactive Environments in Detail (and How to Build Your Own)
--------------------------------------------------------------

Unfortunately building a GIE isn't completely straightforward, and it's
certainly not as simple as picking out an existing container and plugging it
in. Here we'll go through build a "Hello, World" GIE which just displays a file
from a user's history.

Directory Layout
^^^^^^^^^^^^^^^^

The GIE directory layout looks identical to that of normal visualization
plugins, for those familiar with developing those

.. code-block:: console

    $ tree $GALAXY_ROOT/config/plugins/interactive_environments/ipython/
    config/plugins/interactive_environments/ipython/
    ├── config
    │   ├── ipython.ini
    │   ├── ipython.ini.sample
    │   └── ipython.xml
    ├── static
    │   └── js
    │       └── ipython.js
    └── templates
        ├── ipython.mako
        └── notebook.ipynb

We'll use the variable ``{gie}`` to stand in for the name of your GIE. It
should match ``[a-z]+``, like ``ipython`` or ``rstudio``. Here you can see the
``config/`` directory with a ``{gie}.ini.sample`` providing docker and image
configuration, and then ``{gie}.xml`` which outlines that it is a GIE.

The static directory can hold resources such as javascript and css files. If
you are actively developing a GIE, you'll need to restart Galaxy after adding
any resources to that file, before they can be accessed in the browser.

Lastly, and most importantly, there's the templates folder. This normally just
contains ``{gie}.mako``, however the IPython file needs an extra template file.

First Steps, Configuration
^^^^^^^^^^^^^^^^^^^^^^^^^^

We will name our GIE "helloworld", but you are free to name your's differently.
We'll first need to create the directory structure and set up our
configuration

.. code-block:: console

    $ mkdir -p $GALAXY_ROOT/config/plugins/interactive_environments/helloworld/{config,static,templates}
    $ cd $GALAXY_ROOT/config/plugins/interactive_environments/helloworld/

Next, you'll need to create the GIE plugin XML file ``config/helloworld.xml``

.. code-block:: xml

    <?xml version="1.0" encoding="UTF-8"?>
    <!DOCTYPE interactive_environment SYSTEM "../../interactive_environments.dtd">
    <!-- This is the name which will show up in the User's Browser -->
    <interactive_environment name="HelloWorld">
        <data_sources>
            <data_source>
                <model_class>HistoryDatasetAssociation</model_class>

                <!-- here you filter out which types of datasets are
                     appropriate for this GIE -->
                <test type="isinstance" test_attr="datatype" result_type="datatype">tabular.Tabular</test>
                <test type="isinstance" test_attr="datatype" result_type="datatype">data.Text</test>
                <to_param param_attr="id">dataset_id</to_param>
            </data_source>
        </data_sources>
        <params>
            <param type="dataset" var_name_in_template="hda" required="true">dataset_id</param>
        </params>
        <!-- Be sure that your entrypoint name is correct! -->
        <entry_point entry_point_type="mako">helloworld.mako</entry_point>
    </interactive_environment>

Once this is done, we can set up our INI file, ``config/helloworld.ini.sample`` which controlls docker interaction

.. code-block:: ini

    [main]
    # Unused

    [docker]
    # Command to execute docker. For example `sudo docker` or `docker-lxc`.
    #command = docker {docker_args}

    # The docker image name that should be started.
    image = hello-ie

    # Additional arguments that are passed to the `docker run` command.
    #command_inject = --sig-proxy=true -e DEBUG=false

    # URL to access the Galaxy API with from the spawn Docker container, if empty
    # this falls back to galaxy.ini's galaxy_infrastructure_url and finally to the
    # Docker host of the spawned container if that is also not set.
    #galaxy_url =

    # The Docker hostname. It can be useful to run the Docker daemon on a different
    # host than Galaxy.
    #docker_hostname = localhost

We've named our image ``hello-ie``, we'll get to creating that in a minute.

Mako Templates
^^^^^^^^^^^^^^

Mako templates are very easy to use, and they allow significantly more
flexibility than many other templating languages. It's because of this
flexibility (and ability to write plain python code in them) that GIEs were
possible to develop easily.

In our ``templates/helloworld.mako``, we'll add the following

.. code-block:: html+mako

    <%namespace name="ie" file="ie.mako" />

This line says to inherit from the ``ie.mako`` file that's available in
``$GALAXY_ROOT/config/plugins/interactive_environments/common/templates/ie.mako``.
Next we'll add the following

.. code-block:: html+mako

    <%
    # Sets ID and sets up a lot of other variables
    ie_request.load_deploy_config()

    # Define a volume that will be mounted into the container.
    # This is a useful way to provide access to large files in the container,
    # if the user knows ahead of time that they will need it.
    user_file = ie_request.volume(
        hda.file_name, '/import/file.dat', how='ro')

    # Launch the IE. This builds and runs the docker command in the background.
    ie_request.launch(
        volumes=[user_file],
        env_override={
            'custom': '42'
        }
    )

    # Only once the container is launched can we template our URLs. The ie_request
    # doesn't have all of the information needed until the container is running.
    url = ie_request.url_template('${PROXY_URL}/helloworld/')
    %>

That mako snippet loaded the configuration from the INI files, launched the
docker container, and then built a URL to the correct endpoint, through the
Galaxy NodeJS proxy. Additionally we've set an environment variable named ``CUSTOM`` with the value ``42`` to be passed to the container, and we've attached the dataset the user selected (available in ``hda``) to the container as a read-only volume.

We'll continue appending to our ``helloworld.mako`` the HTML code that's actually displayed to the user, when this template is rendered

.. code-block:: html+mako

    <html>
    <head>
    <!-- Loads some necessary javascript libraries. Specifically jquery,
         toastr, and requirejs -->
    ${ ie.load_default_js() }
    </head>
    <body>

    <script type="text/javascript">
    // see $GALAXY_ROOT/config/plugins/interactive_environments/common/templates/ie.mako to learn what this does
    ${ ie.default_javascript_variables() }
    var notebook_login_url = 'unused';
    var notebook_access_url = '${ notebook_access_url }';

    // Load code with require.js
    ${ ie.plugin_require_config() }

    // Load notebook
    // This will load code from static/helloworld.js, often used to handle
    // things like Login. The load_notebook function will eventually append
    // an IFrame to the <div id="main" /> below.
    requirejs(['interactive_environments', 'plugin/helloworld'], function(){
        load_notebook(notebook_access_url);
    });
    </script>
    <div id="main" width="100%" height="100%">
    </div>
    </body>
    </html>

We've glossed over some of the features of this file, but most IEs do a significant amount of "magic" in the top half of the mako template. For instance, the IPython notebook:

- If the user is trying to run the IPython GIE Visualization on an existing notebook in their history, then that gets loaded into the docker container via the temp directory and set as the default notebook
- Otherwise a default notebook is built for the user.

The RStudio notebook:

- generates a random password and configures the image to use this password
- Copies in an RData file if the user has loaded one
- sets some custom environment variables.


Connecting the User to the Container via Javascript
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

With the mako template above finished, if you were to load this in your
browser, not a lot would happen because we haven't built the hello-ie image,
and we haven't used Javascript to connect the user with the container. In the
tail end of the template, we set a variable ``notebook_access_url``. These are
partially a legacy of how things used to be done and you're welcome to clean up
your code according to your desires. Galaxy's NodeJS proxy handles the
authentication of users, so you don't have to worry about it, and can just
assume that only the correct user will have access to a given notebook.

In the ``static/`` directory, we generally create a ``js/`` directory below that, and create a ``{gie}.js`` (so, ``static/js/helloworld.js``) file in there. That file will have a function, ``load_notebook`` which will check if the GIE is available, and when it is, display it to the user.

We start by writing the load notebook function, which is pretty generic

.. code-block:: javascript

    // Load an interactive environment (IE) from a remote URL
    // @param {String} notebook_access_url: the URL embeded in the page and loaded 
    function load_notebook(notebook_access_url){
        // When the page has completely loaded...
        $( document ).ready(function() {
            // Test if we can access the GIE, and if so, execute the function
            // to load the GIE for the user.
            test_ie_availability(notebook_access_url, function(){
                _handle_notebook_loading(notebook_access_url);
            });
        });
    }

This function will display a spinner to the user to indicate process, and then make multiple requests to ``notebook_access_url``. That MUST return a 200 OK for the ``_handle_notebook_loading`` function to ever be called. 302s do not count!

With that, we've almost completed the Javascript portion, just need to implement the function to display the GIE to the user in an iframe

.. code-block:: javascript

    function _handle_notebook_loading(notebook_access_url){
        append_notebook(notebook_access_url);
    }


This function is very short. Historically, the GIE process involved a complex dance of:

- generating a random password in the mako template
- setting it as a javascript variable
- passing it to the docker container
- once the container was available, have the javascript automatically log a
  user in (something browsers try to prevent since that's otherwise an XSS
  vulnerability.)
- hope everything worked

Since the NodeJS proxy takes care of authentication/authorization, we can
reduce the helloworld ``_handle_notebook_loading`` function to a simple
``append_notebook`` call. You may wish to look at the IPython and RStudio GIEs
for examples of the complex things that can be done at every step.

The GIE Container
^^^^^^^^^^^^^^^^^

We'll build a simple container that just displays the dataset a user has
selected to them. Remember when we attached a volume to the container? We'll
make use of that now.

GIE Containers (often) consist of:

- Dockerfile
- NGINX Proxy configuration
- A custom startup script/entrypoint
- A script to monitor traffic and kill unused containers

We have to monitor the container's traffic and kill off unused containers,
bceause no one is watching them. The user launches the container in Galaxy, and
Galaxy immediately forgets the container exists. Thus, we say that if a
container has no connections to TCP connections to itself, then it should
commit suicide by killing the root process.

Here's an example Dockerfile for our helloworld container

.. code-block:: dockerfile

    FROM ubuntu:14.04
    # These environment variables are passed from Galaxy to the container
    # and help you enable connectivity to Galaxy from within the container.
    # This means your user can import/export data from/to Galaxy.
    ENV DEBIAN_FRONTEND=noninteractive \
        API_KEY=none \
        DEBUG=false \
        PROXY_PREFIX=none \
        GALAXY_URL=none \
        GALAXY_WEB_PORT=10000 \
        HISTORY_ID=none \
        REMOTE_HOST=none

    RUN apt-get -qq update && \
        apt-get install --no-install-recommends -y \
        wget procps nginx python python-pip net-tools nginx

    # Our very important scripts. Make sure you've run `chmod +x startup.sh
    # monitor_traffic.sh` outside of the container!
    ADD ./startup.sh /startup.sh
    ADD ./monitor_traffic.sh /monitor_traffic.sh

    # /import will be the universal mount-point for IPython
    # The Galaxy instance can copy in data that needs to be present to the
    # container
    RUN mkdir /import

    # Nginx configuration
    COPY ./proxy.conf /proxy.conf

    VOLUME ["/import"]
    WORKDIR /import/

    # EXTREMELY IMPORTANT! You must expose a SINGLE port on your container.
    EXPOSE 80
    CMD /startup.sh

If you have questions on this, please feel free to contact us on IRC
(`irc.freenode.net#galaxyproject <https://webchat.freenode.net/?channels=galaxyproject>`__).

The proxy configuration is interesting, here we'll point NGINX to reverse proxy
a service running on ``:8000`` inside the container. That port will be hosting
a python process which serves up the directory contents of ``/import``, i.e.
the file the user selected which was mounted as a volume into
``/import/file.dat``

.. code-block:: nginx

    server {
        listen 80;
        server_name localhost;
        access_log /var/log/nginx/localhost.access.log;

        # Note the trailing slash used everywhere!
        location PROXY_PREFIX/helloworld/ {
            proxy_buffering off;
            proxy_pass         http://127.0.0.1:8000/;
            proxy_redirect     http://127.0.0.1:8000/ PROXY_PREFIX/helloworld/;
        }
    }


And here we'll run that service in our ``startup.sh`` file

.. code-block:: bash

    #!/bin/bash
    # First, replace the PROXY_PREFIX value in /proxy.conf with the value from
    # the environment variable.
    sed -i "s|PROXY_PREFIX|${PROXY_PREFIX}|" /proxy.conf;
    # Then copy into the default location for ubuntu+nginx
    cp /proxy.conf /etc/nginx/sites-enabled/default;

    # Here you would normally start whatever service you want to start. In our
    # example we start a simple directory listing service on port 8000
    cd /import/ && python -mSimpleHTTPServer &

    # Launch traffic monitor which will automatically kill the container if
    # traffic stops
    /monitor_traffic.sh &
    # And finally launch nginx in foreground mode. This will make debugging
    # easier as logs will be available from `docker logs ...`
    nginx -g 'daemon off;'

Lastly, our ``monitor_traffic.sh`` file is often re-used between containers, the only adjustment being the port that is looked at

.. code-block:: bash

    #!/bin/bash
    while true; do
        sleep 60
        if [ `netstat -t | grep -v CLOSE_WAIT | grep ':80' | wc -l` -lt 3 ]
        then
            pkill nginx
        fi
    done

With those files, ``monitor_traffic.sh``, ``Dockerfile``, ``startup.sh``, and ``proxy.conf``, you should be able to build your ``hello-ie`` container

.. code-block:: bash

    $ cd hello-ie
    $ docker build -t hello-ie .

Now, if everything went smoothly, you should be able to restart Galaxy and try out your new GIE on a tabular or text file!

Debugging
^^^^^^^^^

When you launch your new GIE in Galaxy, your Galaxy logs should show something like the following:

.. code-block:: console

    Starting docker container for IE helloworld with command [docker run --sig-proxy=true -e DEBUG=false -e "GALAXY_URL=http://localhost/galaxy/" -e "CORS_ORIGIN=http://localhost" -e "GALAXY_WEB_PORT=8000" -e "HISTORY_ID=f2db41e1fa331b3e" -e "CUSTOM=42" -e "GALAXY_PASTER_PORT=8000" -e "PROXY_PREFIX=/galaxy/gie_proxy" -e "API_KEY=1712364174a0ff79b34e9a78fee3ca1c" -e "REMOTE_HOST=127.0.0.1" -e "USER_EMAIL=hxr@local.host" -d -P -v "/home/hxr/work/galaxy/database/tmp/tmp5HaqZy:/import/" -v "/home/hxr/work/galaxy/database/files/000/dataset_68.dat:/import/file.dat:ro" hello-ie]

Here's the docker command written out in a more readable manner:

.. code-block:: console

    $ docker run --sig-proxy=true \
        -d -P \
        -e "API_KEY=1712364174a0ff79b34e9a78fee3ca1c" \
        -e "CORS_ORIGIN=http://localhost" \
        -e "CUSTOM=42" \
        -e "DEBUG=false" \
        -e "GALAXY_PASTER_PORT=8000" \
        -e "GALAXY_URL=http://localhost/galaxy/" \
        -e "GALAXY_WEB_PORT=8000" \
        -e "HISTORY_ID=f2db41e1fa331b3e" \
        -e "PROXY_PREFIX=/galaxy/gie_proxy" \
        -e "REMOTE_HOST=127.0.0.1" \
        -e "USER_EMAIL=hxr@local.host" \
        -v "/home/hxr/work/galaxy/database/tmp/tmp5HaqZy:/import/" \
        -v "/home/hxr/work/galaxy/database/files/000/dataset_68.dat:/import/file.dat:ro" \
      hello-ie

As you can see, a LOT is going on! We'll break it down further:

- ``-d`` runs the container in daemon mode, it launches and the client
  submitting the container finished
- ``-P`` randomly assigns an unused port to the container for each ``EXPOSE``d
  port from our ``Dockerfile``. This is why you must expose a port, and only
  one port.
- A large number of environment variables are set:

    - The user's API key is provided, allowing you to access datasets and
      submit jobs on their behalf. If you have an environment like
      IPython/RStudio, it is **highly recommended** that you provide some magic
      by which the user can use their API key without embedding it in the
      ntoebook. If you do embed it somehow in a document that gets saved to
      their history, anyone can impersonate that user if they get a hold of it.
      In the IPython GIE we have a variable that just runs
      ``os.environ.get('API_KEY')`` to avoid embedding it in their notebook.
    - A CORS Origin is provided for very strict servers, but it may be easier
      to simply void CORS requirements within the nginx proxy in your
      container.
    - Custom variables specified in your ``launch()`` command are available
    - A ``DEBUG`` environment variable should be used to help admins debug
      existing containers. You should use it to increase logging, not cleanup
      temporary files, and so on.
    - ``GALAXY_PASTER_PORT`` (deprecated) and ``GALAXY_WEB_PORT`` are the raw
      port that Galaxy is listening on. You can use this to help decide how to
      takl to Galaxy.
    - ``GALAXY_URL`` is the URL that Galaxy should be accessible at. For
      various reasons this may not be true. We recommend looking at our
      implementation of `galaxy.py
      <https://github.com/bgruening/docker-ipython-notebook/blob/15.07/galaxy.py>`__
      which is a small utility script to provide API access to Galaxy to get
      and fetch data, based on those environment variables.
    - The ``HISTORY_ID`` of the current history the user is on is provided. In
      the IPython/RStudio containers, we provide a dead simple method for users
      to download datasets from their current history which will be visible to
      them on the right hand side of their screen.
    - A ``PROXY_PREFIX`` is provided which should be used in the nginx conf.
    - ``REMOTE_HOST`` is another component used to test for a possible Galaxy
      access path
    - The user's email is made available, very convenient for webservices like
      Entrez which require the user's email address. You can pre-fill it out
      for them, making their life easier.
    - Two volumes are mounted, one a temporary directory from Galaxy (rw), and one
      the dataset the user selected (ro).

- and finally the image is specified.

Most of this information is usually required to build friendly, easy-to-use
GIEs. One of the strong points of GIEs is their magic interaction with Galaxy.
Here we've mounted a volume read-only, but in real life you may wish to provide
connectivity like IPython and RStudio provide, allowing the user to load
datasets on demand for interactive analysis, and then to store analysis
artefacts (and a log of what was done inside the container, à la IPython's
"notebooks") back to their current history.

If everything went well, at this point you should see a directory listing show up:

.. image:: interactive_environments_success.png

If you find yourself encountering difficulties, the "Hello, World" IE is
available in a `GitHub repo <https://github.com/erasche/hello-world-interactive-environment/releases/tag/v15.10>`__, and there are people on the IRC channel who can help debug.
