.. _framework-dependencies:

Galaxy Framework Dependencies
=============================

Galaxy is a large Python application with a long list of `Python module
dependencies`_. As a result, the Galaxy developers have made significant effort
to provide these dependencies in as simple a method as possible. Prior to the
16.01 release, this was done by distributing dependencies in Python's old
standard packaging format (Egg) in a non-standard way. As of the 16.01 release,
Galaxy now distributes dependencies in Python's new standard packaging format
(Wheel), albeit still in a non-standard way. Thankfully, the new distribution
method is far more compatible with the standard package distribution tooling
(i.e. `pip`_) than the old method.

.. _Python module dependencies: https://github.com/galaxyproject/galaxy/blob/dev/lib/galaxy/dependencies/requirements.txt
.. _pip: https://pip.pypa.io/
.. _wheel: https://wheel.readthedocs.org/

How it works
------------

Upon startup (with ``run.sh``), the startup scripts will:

1. Create a Python `virtualenv`_ in the directory ``.venv``.

2. Unset the ``$PYTHONPATH`` environment variable (if set) as this can
   interfere with installing `Galaxy pip`_ and dependencies.

3. Replace that virtualenv's pip with `Galaxy pip`_.

4. If applicable, create a ``binary-compatibility.cfg`` (see the `Galaxy pip
   and wheel`_ section for an explanation of this file).

5. Download and install wheels from the Galaxy project wheel server,
   `wheels.galaxyproject.org`_, using pip.

6. Start Galaxy using ``.venv/bin/python``.

.. _virtualenv: https://virtualenv.readthedocs.org/
.. _wheels.galaxyproject.org: https://wheels.galaxyproject.org/

Options
-------

A variety of options to ``run.sh`` are available to control the above behavior:

- ``--skip-venv``: Do not create or use a virtualenv, and do not replace pip
  with Galaxy pip.
- ``--skip-wheels``: Do not install wheels.
- ``--no-create-venv``: Do not create a virtualenv, but use one if it exists at
  ``.venv`` or if ``$VIRTUAL_ENV`` is set (this variable is set by virtualenv's
  ``activate``)
- ``--replace-pip/--no-replace-pip``: Do/do not replace pip with Galaxy pip.

Managing dependencies manually
------------------------------

Create a virtualenv
^^^^^^^^^^^^^^^^^^^

Using a `virtualenv`_ in ``.venv`` under the Galaxy source tree is not
required. More complicated Galaxy setups may choose to use a virtualenv
external to the Galaxy source tree, which can be done either by not using
``run.sh`` directly (an example of this can be found under the `Supervisor`_
section) or using the ``--no-create-venv`` option, explained in the `Options`_
section. It is also possible to force Galaxy to start without a virtualenv at
all, but you should not do this unless you know what you're doing.

To manually create a virtualenv, you will first need to obtain virtualenv.
There are a variety of ways to do this:

- ``pip install virtualenv``
- ``brew install virtualenv``
- Install your Linux distribution's virtualenv package from the system package
  manager (e.g. ``apt-get install python-virtualenv``).
- Download the `virtualenv source from PyPI
  <https://pypi.python.org/pypi/virtualenv>`_, untar, and run the
  ``virtualenv.py`` script contained within as ``python virtualenv.py
  /path/to/galaxy/virtualenv``

Once this is done, create a virtualenv. In our example, the virtualenv will
live in ``/srv/galaxy/venv`` and the Galaxy source code has been cloned to
``/srv/galaxy/server``.

.. code-block:: console
    
    $ virtualenv /srv/galaxy/venv
    New python executable in /srv/galaxy/venv/bin/python
    Installing setuptools, pip, wheel...done.
    $ . /srv/galaxy/venv/bin/activate
    (venv)$

Install dependencies
^^^^^^^^^^^^^^^^^^^^

Normally, ``run.sh`` calls `common_startup.sh`_, which creates the virtualenv,
installs Galaxy pip, and installs dependencies. You can call this script
yourself to set up Galaxy pip and the dependencies without creating a
virtualenv using the ``--no-create-venv`` option:

.. code-block:: console
    
    (venv)$ PYTHONPATH= sh /srv/galaxy/server/scripts/common_startup.sh --no-create-venv
    Ignoring indexes: https://pypi.python.org/simple
    Collecting pip
      Downloading https://wheels.galaxyproject.org/packages/pip-8.0.0+gx1-py2.py3-none-any.whl (1.2MB)
        100% |████████████████████████████████| 1.2MB 37.8MB/s 
    Installing collected packages: pip
      Found existing installation: pip 7.1.2
        Uninstalling pip-7.1.2:
          Successfully uninstalled pip-7.1.2
    Successfully installed pip-8.0.0+gx1
    Collecting bx-python==0.7.3 (from -r requirements.txt (line 2))
      Downloading https://wheels.galaxyproject.org/packages/bx_python-0.7.3-cp27-cp27mu-linux_x86_64.whl (1.7MB)
        100% |████████████████████████████████| 1.7MB 25.4MB/s 

    ...

    Collecting pysam==0.8.3+gx1 (from -r requirements.txt (line 69))
      Downloading https://wheels.galaxyproject.org/packages/pysam-0.8.3+gx1-cp27-cp27mu-linux_x86_64.whl (7.4MB)
        100% |████████████████████████████████| 7.4MB 15.1MB/s 
    Installing collected packages: bx-python, MarkupSafe, PyYAML, SQLAlchemy,
      mercurial, numpy, pycrypto, six, Paste, PasteDeploy, docutils, wchartype,
      repoze.lru, Routes, WebOb, WebHelpers, Mako, pytz, Babel, Beaker,
      Markdown, Cheetah, requests, requests-toolbelt, boto, bioblend, amqp,
      anyjson, kombu, pbr, sqlparse, decorator, Tempita, sqlalchemy-migrate,
      Parsley, nose, svgwrite, ecdsa, paramiko, Fabric, Whoosh, pysam
    Successfully installed Babel-2.0 Beaker-1.7.0 Cheetah-2.4.4 Fabric-1.10.2
      Mako-1.0.2 Markdown-2.6.3 MarkupSafe-0.23 Parsley-1.3 Paste-2.0.2
      PasteDeploy-1.5.2 PyYAML-3.11 Routes-2.2 SQLAlchemy-1.0.8 svgwrite-1.1.6
      Tempita-0.5.3.dev0 WebHelpers-1.3 WebOb-1.4.1 Whoosh-2.4.1+gx1 amqp-1.4.8
      anyjson-0.3.3 bioblend-0.6.1 boto-2.38.0 bx-python-0.7.3 decorator-4.0.2
      docutils-0.12 ecdsa-0.13 kombu-3.0.30 mercurial-3.4.2 nose-1.3.7
      numpy-1.9.2 paramiko-1.15.2 pbr-1.8.0 pycrypto-2.6.1 pysam-0.8.3+gx1
      pytz-2015.4 repoze.lru-0.6 requests-2.8.1 requests-toolbelt-0.4.0
      six-1.9.0 sqlalchemy-migrate-0.10.0 sqlparse-0.1.16 wchartype-0.1

**Warning:** If your ``$PYTHONPATH`` is set, it may interfere with the
dependency installation process (this will almost certainly be the case if you
use `virtualenv-burrito`_). Without ``--no-create-venv`` the ``$PYTHONPATH``
variable will be automatically unset, but we assume you know what you're doing
and may want it left intact if you are using ``--no-create-venv``. If you
encounter problems, try unsetting ``$PYTHONPATH`` as shown in the example
above.

.. _common_startup.sh: https://github.com/galaxyproject/galaxy/blob/dev/scripts/common_startup.sh
.. _virtualenv-burrito: https://github.com/brainsik/virtualenv-burrito

Installing unpinned dependencies
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Galaxy's dependencies can be installed either "pinned" (they will be installed
at exact versions specified for your Galaxy release) or "unpinned" (the latest
versions of all dependencies will be installed unless there are known
incompatibilities with new versions). By default, the release branch(es) of
Galaxy use pinned versions for three reasons:

1. Using pinned versions insures that the prebuilt wheels on
   `wheels.galaxyproject.org`_ will be installed, and no compilation will be
   necesseary.

2. Galaxy releases are tested with the pinned versions and this allows us to
   give as much assurance as possible that the pinned versions will work with
   the given Galaxy release (especially as time progresses and newer dependency
   versions are released while the Galaxy release receives fewer updates.

3. Pinning furthers Galaxy's goal of reproducibility as differing dependency
   versions could result in non-reproducible behavior.

Install dependencies using the `unpinned requirements file`_, and then instruct
Galaxy to start without attempting to fetch wheels:

.. code-block:: console

    (venv)$ pip install --index-url=https://wheels.galaxyproject.org/simple/ -r lib/galaxy/dependencies/requirements.txt
    (venv)$ deactivate
    $ sh run.sh --no-create-venv --skip-wheels

Including ``--index-url=https://wheels.galaxyproject.org/simple/`` is important
as two dependencies (pysam, Whoosh) include modifications specific to Galaxy
which are only available on `wheels.galaxyproject.org`_.

.. _unpinned requirements file: https://github.com/galaxyproject/galaxy/blob/dev/lib/galaxy/dependencies/requirements.txt

Wheel interaction with other software
-------------------------------------

Galaxy job handlers
^^^^^^^^^^^^^^^^^^^

All Galaxy jobs run a metadata detection step on the job outputs upon
completion of the tool. The metadata detection step requires many of Galaxy's
dependencies. Because of this, it's necessary to make sure the metadata
detection step runs in Galaxy's virtualenv. If you run a relatively simple
Galaxy setup (e.g. single process, or multiple Python Paste processes started
using ``run.sh``) then this is assured for you automatically. In more
complicated setups (supervisor, the "headless" Galaxy handler, and/or the
virtualenv used to start Galaxy is not a shared filesystem) it may be necessary
to make sure the handlers know where the virtualenv (or a virtualenv containing
Galaxy's dependencies) can be found.

If your jobs are failing due to Python ``ImportError`` exceptions, this is most
likely the problem. If so, you can use the ``<env>`` tag in ``job_conf.xml`` to
source the virtualenv. For example:

.. code-block:: xml

    <job_conf>
        <plugins>
            ...
        </plugins>
        <destinations default="cluster">
            <destination id="cluster" runner="drmaa">
                <param id="nativeSpecification"> ...cluster options... </param>

                <env file="/galaxy/server/.venv/bin/activate" />

            </destination>
        </destinations>
    </job_conf>

If your Galaxy server's virtualenv isn't available on the cluster you can
create one manually using the instructions under `Managing dependencies
manually`_.

Pulsar
^^^^^^

If using `Pulsar`_'s option to set metadata on the remote server, the same
conditions as with `Galaxy job handlers`_ apply. You should create a virtualenv
on the remote resource, install Galaxy's dependencies in to it, and set an
``<env>`` tag pointing to the virtualenv's ``activate`` as in the `Galaxy job
handlers`_ section. Instructions on how to create a virtualenv can be found
under the `Managing dependencies manually`_ section.

.. _Pulsar: http://pulsar.readthedocs.org/

Conda
^^^^^

`Conda`_ and `virtualenv`_ are incompatible. However, Conda provides its own
environment separation functionality in the form of `Conda environments`_.
Starting Galaxy with Conda Python will cause ``--skip-venv`` to be implicitly
set, and the currently active Conda environment will be used to install Galaxy
framework dependencies instaead.  Be sure to create and activate a Conda
environment for Galaxy prior to installing packages and/or starting Galaxy.

You may choose to install Galaxy's dependencies either at their `pinned`_
versions using pip or `unpinned`_ using a combination of conda and pip. When
running under Conda, pip is not replaced with Galaxy pip, so installing pinned
dependencies will require compilation, will be slower and requires having those
dependencies' build-time dependencies installed, but has benefits as explained
under the `Installing unpinned dependencies`_ section.  Installing unpinned
dependencies allows you to use Conda's binary packages for quick and easy
installation.

Pinned dependencies will be installed by default when running ``run.sh``. To
install unpinned dependencies, the process is similar as to installing unpinned
versions without Conda, with the extra step of installing as much as possible
from Conda/Bioconda before installing from pip. Begin by adding the `Bioconda`_
channel as explained in the `Bioconda instructions`_ and then creating a new
Conda environment using the provided Conda environment file. Then, install
remaining dependencies using pip and start Galaxy, instructing it to skip the
automatic fetching of pinned dependencies.

.. code-block:: console

    $ conda config --add channels r
    $ conda config --add channels bioconda
    $ conda create --name galaxy --file lib/galaxy/dependencies/conda-environment.txt
    Fetching package metadata: ........
    Solving package specifications: ............................................
    Package plan for installation in environment /home/nate/conda/envs/galaxy:

    The following packages will be downloaded:

        package                    |            build
        ---------------------------|-----------------
        boto-2.38.0                |           py27_0         1.3 MB
        cheetah-2.4.4              |           py27_0         267 KB
        decorator-4.0.6            |           py27_0          11 KB
        docutils-0.12              |           py27_0         636 KB
        ecdsa-0.11                 |           py27_0          73 KB
        markupsafe-0.23            |           py27_0          30 KB
        mercurial-3.4.2            |           py27_0         2.9 MB
        nose-1.3.7                 |           py27_0         194 KB
        paste-1.7.5.1              |           py27_0         490 KB
        pytz-2015.7                |           py27_0         174 KB
        repoze.lru-0.6             |           py27_0          15 KB
        requests-2.9.1             |           py27_0         605 KB
        six-1.10.0                 |           py27_0          16 KB
        sqlalchemy-1.0.11          |           py27_0         1.3 MB
        sqlparse-0.1.18            |           py27_0          51 KB
        webob-1.4.1                |           py27_0         108 KB
        babel-2.1.1                |           py27_0         2.3 MB
        bx-python-0.7.3            |      np110py27_1         2.1 MB
        mako-1.0.3                 |           py27_0         105 KB
        paramiko-1.15.2            |           py27_0         197 KB
        pastedeploy-1.5.2          |           py27_1          23 KB
        requests-toolbelt-0.5.0    |           py27_0          83 KB
        routes-2.2                 |           py27_0          48 KB
        bioblend-0.7.0             |           py27_0         181 KB
        fabric-1.10.2              |           py27_0         108 KB
        ------------------------------------------------------------
                                               Total:        13.2 MB

    The following NEW packages will be INSTALLED:

        babel:             2.1.1-py27_0     
        bioblend:          0.7.0-py27_0     
        boto:              2.38.0-py27_0    
        bx-python:         0.7.3-np110py27_1
        cheetah:           2.4.4-py27_0     
        decorator:         4.0.6-py27_0     
        docutils:          0.12-py27_0      
        ecdsa:             0.11-py27_0      
        fabric:            1.10.2-py27_0    
        libgfortran:       1.0-0            
        mako:              1.0.3-py27_0     
        markupsafe:        0.23-py27_0      
        mercurial:         3.4.2-py27_0     
        nose:              1.3.7-py27_0     
        numpy:             1.10.2-py27_0    
        openblas:          0.2.14-3         
        openssl:           1.0.2e-0         
        paramiko:          1.15.2-py27_0    
        paste:             1.7.5.1-py27_0   
        pastedeploy:       1.5.2-py27_1     
        pip:               7.1.2-py27_0     
        pycrypto:          2.6.1-py27_0     
        python:            2.7.11-0         
        pytz:              2015.7-py27_0    
        pyyaml:            3.11-py27_1      
        readline:          6.2-2            
        repoze.lru:        0.6-py27_0       
        requests:          2.9.1-py27_0     
        requests-toolbelt: 0.5.0-py27_0     
        routes:            2.2-py27_0       
        setuptools:        19.2-py27_0      
        six:               1.10.0-py27_0    
        sqlalchemy:        1.0.11-py27_0    
        sqlite:            3.9.2-0          
        sqlparse:          0.1.18-py27_0    
        tk:                8.5.18-0         
        webob:             1.4.1-py27_0     
        wheel:             0.26.0-py27_1    
        yaml:              0.1.6-0          
        zlib:              1.2.8-0          

    Proceed ([y]/n)? 

    Fetching packages ...
    boto-2.38.0-py 100% |############################################| Time: 0:00:00   3.27 MB/s
    cheetah-2.4.4- 100% |############################################| Time: 0:00:00   1.65 MB/s
    decorator-4.0. 100% |############################################| Time: 0:00:00  20.38 MB/s
    docutils-0.12- 100% |############################################| Time: 0:00:00   2.21 MB/s
    ecdsa-0.11-py2 100% |############################################| Time: 0:00:00 762.58 kB/s
    markupsafe-0.2 100% |############################################| Time: 0:00:00 931.23 kB/s
    mercurial-3.4. 100% |############################################| Time: 0:00:00   5.36 MB/s
    nose-1.3.7-py2 100% |############################################| Time: 0:00:00   1.12 MB/s
    paste-1.7.5.1- 100% |############################################| Time: 0:00:00   1.91 MB/s
    pytz-2015.7-py 100% |############################################| Time: 0:00:00   1.08 MB/s
    repoze.lru-0.6 100% |############################################| Time: 0:00:00 465.26 kB/s
    requests-2.9.1 100% |############################################| Time: 0:00:00   2.28 MB/s
    six-1.10.0-py2 100% |############################################| Time: 0:00:00 477.04 kB/s
    sqlalchemy-1.0 100% |############################################| Time: 0:00:00   4.25 MB/s
    sqlparse-0.1.1 100% |############################################| Time: 0:00:00 774.57 kB/s
    webob-1.4.1-py 100% |############################################| Time: 0:00:00 819.13 kB/s
    babel-2.1.1-py 100% |############################################| Time: 0:00:00   5.53 MB/s
    bx-python-0.7. 100% |############################################| Time: 0:00:00   5.11 MB/s
    mako-1.0.3-py2 100% |############################################| Time: 0:00:00 813.04 kB/s
    paramiko-1.15. 100% |############################################| Time: 0:00:00   1.23 MB/s
    pastedeploy-1. 100% |############################################| Time: 0:00:00 721.20 kB/s
    requests-toolb 100% |############################################| Time: 0:00:00 856.06 kB/s
    routes-2.2-py2 100% |############################################| Time: 0:00:00 666.70 kB/s
    bioblend-0.7.0 100% |############################################| Time: 0:00:00   1.15 MB/s
    fabric-1.10.2- 100% |############################################| Time: 0:00:00 843.81 kB/s
    Extracting packages ...
    [      COMPLETE      ]|###############################################################| 100%
    Linking packages ...
    [      COMPLETE      ]|###############################################################| 100%
    #
    # To activate this environment, use:
    # $ source activate galaxy
    #
    # To deactivate this environment, use:
    # $ source deactivate
    #
    $ source activate galaxy
    discarding /home/nate/conda/bin from PATH
    prepending /home/nate/conda/envs/galaxy/bin to PATH
    $ pip install --index-url=https://wheels.galaxyproject.org/simple/ -r lib/galaxy/dependencies/requirements.txt
    Requirement already satisfied (use --upgrade to upgrade): numpy in /home/nate/conda/envs/galaxy/lib/python2.7/site-packages (from -r lib/galaxy/dependencies/requirements.txt (line 1))

      ...

    Collecting WebHelpers (from -r lib/galaxy/dependencies/requirements.txt (line 15))
      Downloading https://wheels.galaxyproject.org/packages/WebHelpers-1.3-py2-none-any.whl (149kB)
        100% |████████████████████████████████| 151kB 55.7MB/s 

      ...

    Building wheels for collected packages: pysam
      Running setup.py bdist_wheel for pysam

    $ sh run.sh --skip-wheels

.. _Conda: http://conda.pydata.org/
.. _Conda environments: http://conda.pydata.org/docs/using/envs.html
.. _Bioconda: https://bioconda.github.io/
.. _Bioconda instructions: Bioconda_
.. _pinned: `Installing unpinned dependencies`_
.. _unpinned: pinned_

uWSGI
^^^^^

The simplest scenario to using uWSGI with the wheel-based dependencies is to
install uWSGI into Galaxy virtualenv (by default, ``.venv``) using pip, e.g.:

.. code-block:: console

    $ . ./.venv/bin/activate
    (.venv)$ pip install uwsgi
    Collecting uwsgi
      Downloading uwsgi-2.0.12.tar.gz (784kB)
        100% |████████████████████████████████| 786kB 981kB/s 
    Building wheels for collected packages: uwsgi
      Running setup.py bdist_wheel for uwsgi
      Stored in directory: /home/nate/.cache/pip/wheels/a4/7b/7c/8cbe2fe2c2b963173361cc18aa726f165dc4803effbb8195fc
    Successfully built uwsgi
    Installing collected packages: uwsgi
    Successfully installed uwsgi-2.0.12

Because uWSGI is installed in the virtualenv, Galaxy's dependencies will be
found upon startup.

If uWSGI is installed outside of the virtualenv (e.g. from apt) you will need
to pass the ``-H`` option (or one of `its many aliases
<http://uwsgi-docs.readthedocs.org/en/latest/Options.html#home>`_) on the uWSGI
command line:

.. code-block:: console

    $ uwsgi --ini /srv/galaxy/config/uwsgi.ini -H /srv/galaxy/venv

Or in the uWSGI config file:

.. code-block:: ini

    [uwsgi]
    processes = 8
    threads = 4
    socket = /srv/galaxy/var/uwgi.sock
    logto = /srv/galaxy/var/uwsgi.log
    master = True
    pythonpath = /srv/galaxy/server/lib
    pythonhome = /srv/galaxy/venv
    module = galaxy.webapps.galaxy.buildapp:uwsgi_app_factory()
    set = galaxy_config_file=/srv/galaxy/config/galaxy.ini
    set = galaxy_root=/srv/galaxy/server

Supervisor
^^^^^^^^^^

Many production sites use `supervisord`_ to manage their Galaxy processes
rather than relying on ``run.sh`` or other means. There's no simple way to
activate a virtualenv when using supervisor, but you can simulate the effects
by setting ``$PATH`` and ``$VIRTUAL_ENV`` in your supervisor config:

.. code-block:: ini

    [program:galaxy_uwsgi]
    command         = /srv/galaxy/venv/bin/uwsgi --ini /srv/galaxy/config/uwsgi.ini
    directory       = /srv/galaxy/server
    environment     = VIRTUAL_ENV="/srv/galaxy/venv",PATH="/srv/galaxy/venv/bin:%(ENV_PATH)s"
    numprocs        = 1

    [program:galaxy_handler]
    command         = /srv/galaxy/venv/bin/python ./scripts/galaxy-main -c /srv/galaxy/config/galaxy.ini --server-name=handler%(process_num)s
    directory       = /srv/galaxy/server
    process_name    = handler%(process_num)s
    numprocs        = 4
    environment     = VIRTUAL_ENV="/srv/galaxy/venv",PATH="/srv/galaxy/venv/bin:%(ENV_PATH)s"

With supervisor < 3.0 you cannot use the ``%(ENV_PATH)s`` template variable and
must instead specify the full desired ``$PATH``.

.. _supervisord: http://supervisord.org/

Custom pip/wheel rationale
--------------------------

We chose to use a modified version of the `pip`_ and `wheel`_ packages in order
to make Galaxy easy to use. People wishing to run Galaxy (especially only for
tool development) may not be systems or command line experts. Unfortunately,
Python modules with C extensions may not always compile out of the box
(typically due to missing compilers, headers, or other system packages) and the
failure messages generated are typically only decipherable to people
experienced with software compilation and almost never indicate how to fix the
problem. In addition, the process of compiling all of Galaxy's C extension
dependencies can be very long if it does succeed. As a result, we want to
precompile Galaxy's dependencies. However, the egg format was never prepared
for doing this on any platform and wheels could not do it on Linux because
there is no ABI compatibility between Linux distributions or versions.

As a benefit of using the standard tooling (pip), if you choose not to use
Galaxy pip, all of Galaxy's dependencies should still be installable using
standard pip. You will still need to point pip at `wheels.galaxyproject.org`_
in order to fetch some modified packages and ones that aren't available on
PyPI, but this can be done with the unmodified version of pip.

A good early discussion of these problems can be found in Armin Ronacher's
`blog post on wheels <http://lucumr.pocoo.org/2014/1/27/python-on-wheels/>`_.
One of the problems Armin discusses, Python interpreter ABI incompatibilites
depending on build-time options (UCS2 vs. UCS4), has been fixed by us and
accepted into pip >= 8.0 in `pip pull request #3075`_. The other major problem
(the non-portability of wheels between Linux distributions) remains. `Galaxy
pip`_ provides one solution to this problem.

More recently, the proposed `PEP 513`_ proposes a different solution to the
cross-distro problem.  PEP 513 also contains a very detailed technical
explanation of the problem.

.. _PEP 513: https://www.python.org/dev/peps/pep-0513/
.. _pip pull request #3075: https://github.com/pypa/pip/pull/3075

Galaxy pip and wheel
--------------------
.. _Galaxy pip:
.. _Galaxy wheel: `Galaxy pip and wheel`_

`Galaxy pip is a fork <https://github.com/natefoo/pip/tree/linux-wheels>`_ of
`pip`_ in which we have added support for installing wheels containing C
extensions (wheels that have compiled binary code) on Linux.  `Galaxy wheel is
a fork <https://bitbucket.org/natefoo/wheel>`_ of `wheel`_ in which we have
added support for building wheels installable with Galaxy pip.

Two different types of wheels can be created:

1. "Simple" wheels with very few dependencies outside of libc and libm built on
   a "suitably old" platform (currently Debian Squeeze) such that they should
   work on all newer systems (e.g. RHEL 6+, Ubuntu 12.04+). These wheels carry
   the unmodified ``linux_{arch}`` platform tag (e.g. ``linux_x86_64``) as
   specified in `PEP 425`_ and that you will find on wheels built with an
   unmodified `wheel`_.

2. Wheels with specific external dependencies (for example, ``libpq.so``, the
   PostgreSQL library, used by `psycopg2`_) can be built on each supported
   Linux distribution and tagged more specifically for each distribution. These
   wheels carry a ``linux_{arch}_{distro}_{version}`` platform tag (e.g.
   ``linux_x86_ubuntu_14_04``) and can be created using `Galaxy wheel`_.

The `manylinux`_ project implements the "Simple" wheels in a more clearly
defined way and allows for the inclusion of "non-standard" external
dependencies directly into the wheel. Galaxy will officially support any
standard which allows for Linux wheels in PyPI once such a standard is
complete.

.. _PEP 425: https://www.python.org/dev/peps/pep-0425/
.. _manylinux: https://github.com/manylinux/manylinux/
.. _psycopg2: http://initd.org/psycopg/

Wheel platform compatibility
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Galaxy pip and Galaxy wheel also include support for the proposed
`binary-compatibility.cfg`_ file. This file allows distributions that are
binary compatibile (e.g. Red Hat Enterprise Linux 6 and CentOS 6) to use the
same wheels.

This is a JSON format file which can be installed in ``/etc/python`` or the
root of a virtualenv (`common_startup.sh`_ creates it here) and provides a
mapping between `PEP 425`_ platform tags. For example, the following
``binary-compatibility.cfg`` indicates that wheels built on the platform
``linux_x86_centos_6_7`` will have their platform tag overridden to
``linux_x86_rhel_6``. In addition, wheels tagged with ``linux_x86_64_rhel_6_7``
and ``linux_x86_64_rhel_6`` will be installable on a ``linux_x86_centos_6_7``
system:

.. code-block:: json

    {
        "linux_x86_64_centos_6_7": {
            "build": "linux_x86_64_rhel_6",
            "install": ["linux_x86_64_rhel_6_7", "linux_x86_64_rhel_6"]
        }
    }

Currently, Scientific Linux, CentOS, and Red Hat Enterprise Linux will be set
as binary compatible by `common_startup.sh`_.

.. _binary-compatibility.cfg: https://mail.python.org/pipermail/distutils-sig/2015-July/026617.html

Adding additional wheels as Galaxy dependencies
-----------------------------------------------

New wheels can be added to Galaxy, or the versions of existing wheels can be
updated, using `Galaxy Starforge`_, Galaxy's Docker-based build system.

The process is still under development and will be streamlined and automated
over time. For the time being, please use the following process to add new
wheels:

1. Install `Starforge`_ (e.g. with ``pip install starforge`` or ``python
   setup.py install`` from the source). You will also need to have Docker
   installed on your system.

2. Obtain `wheels.yml`_ (this file will most likely be moved in to Galaxy in
   the future) and add/modify the wheel definition.

3. Use ``starforge wheel --wheels-config=wheels.yml <wheel-name>`` to build the
   wheel. If the wheel includes C extensions, you will probably want to also
   use the ``--no-qemu`` flag to prevent Starforge from attempting to build on
   Mac OS X using QEMU/KVM.

4. If the wheel build is successful, submit a pull request to `Starforge`_ with
   your changes to `wheels.yml`_.

5. A `Galaxy Committers group`_ member will need to trigger an automated build
   of the wheel changes in your pull request. Galaxy's Jenkins_ service will
   build these changes using Starforge.

6. If the pull request is merged, submit a pull request to Galaxy modifying the
   files in `lib/galaxy/dependencies`_ as appropriate.

You may attempt to skip directly to step 4 and let the Starforge wheel PR
builder build your wheels for you. This is especially useful if you are simply
updating an existing wheel's version. However, if you are adding a new C
extension wheel that is not simple to build, you may need to go through many
iterations of updating the PR and having a `Galaxy Committers group`_ member
triggering builds before wheels are successfully built. You can avoid this
cycle by performing steps 1-3 locally.

.. _Starforge:
.. _Galaxy Starforge: https://github.com/galaxyproject/starforge/
.. _wheels.yml: https://github.com/galaxyproject/starforge/blob/master/wheels/build/wheels.yml
.. _Galaxy Committers group: https://github.com/galaxyproject/galaxy/blob/dev/doc/source/project/organization.rst#committers
.. _Jenkins: https://jenkins.galaxyproject.org/
.. _lib/galaxy/dependencies: https://github.com/galaxyproject/galaxy/tree/dev/lib/galaxy/dependencies
