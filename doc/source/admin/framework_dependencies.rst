.. _framework-dependencies:

Framework Dependencies
======================

Galaxy is a large Python application with a long list of `Python module dependencies`_. As a result, the Galaxy
developers have made significant effort to provide these dependencies in as simple a method as possible while remaining
compatible with the `Python packaging best practices`_. Thus, Galaxy's runtime setup procedure makes use of virtualenv_
for package environment isolation, pip_ for installation, and wheel_ to provide pre-built versions of dependencies.

In addition to framework dependencies, since Galaxy 18.09, the client (UI) is no longer provided in its built format
when downloading Galaxy. For more information, see https://github.com/galaxyproject/galaxy/blob/dev/client/README.md .

.. _Python module dependencies: https://github.com/galaxyproject/galaxy/blob/dev/lib/galaxy/dependencies/pipfiles/default/pinned-requirements.txt
.. _Python packaging best practices: https://packaging.python.org
.. _virtualenv: https://packaging.python.org/tutorials/installing-packages/#creating-virtual-environments
.. _pip: https://packaging.python.org/tutorials/installing-packages/#use-pip-for-installing
.. _wheel: https://packaging.python.org/tutorials/installing-packages/#source-distributions-vs-wheels

How it works
------------

Upon startup (with ``run.sh``), the startup scripts will:

1. Create a Python virtualenv_ in the directory ``.venv``.

2. Unset the ``$PYTHONPATH`` environment variable (if set) as this can interfere with installing dependencies.

3. Download and install packages from the `Galaxy project wheel server`_, as well as the `Python
   Package Index`_ (aka PyPI) , using pip_.

4. Start Galaxy using ``.venv/bin/python``.

.. _Galaxy project wheel server: https://wheels.galaxyproject.org/
.. _Python Package Index: https://pypi.org

Options
-------

A variety of options to ``run.sh`` are available to control the above behavior:

- ``--skip-venv``: Do not create or use a virtualenv.
- ``--skip-wheels``: Do not install wheels.
- ``--no-create-venv``: Do not create a virtualenv, but use one if it exists at ``.venv`` or if ``$VIRTUAL_ENV`` is set
  (this variable is set by virtualenv's ``activate``).
- ``--replace-pip/--no-replace-pip``: Do/do not upgrade pip if necessary.

Managing dependencies manually
------------------------------

Create a virtualenv
^^^^^^^^^^^^^^^^^^^

Using a `virtualenv`_ in ``.venv`` under the Galaxy source tree is not required. More complicated Galaxy setups may
choose to use a virtualenv external to the Galaxy source tree, which can be done either by not using ``run.sh`` directly
(an example of this can be found under the :doc:`Scaling and Load Balancing <scaling>` documentation) or using the ``--no-create-venv``
option, explained in the `Options`_ section. It is also possible to force Galaxy to start without a virtualenv at all,
but you should not do this unless you know what you're doing.

To manually create a virtualenv, you will first need to obtain virtualenv.  There are a variety of ways to do this:

- ``pip install virtualenv``
- ``brew install virtualenv``
- Install your Linux distribution's virtualenv package from the system package manager (e.g. ``apt-get install
  python-virtualenv``).
- Download the `virtualenv source from PyPI <https://pypi.python.org/pypi/virtualenv>`_, untar, and run the
  ``virtualenv.py`` script contained within as ``python virtualenv.py /path/to/galaxy/virtualenv``

Once this is done, create a virtualenv. In our example, the virtualenv will live in ``/srv/galaxy/venv`` and the Galaxy
source code has been cloned to ``/srv/galaxy/server``.

.. code-block:: console

    $ virtualenv /srv/galaxy/venv
    New python executable in /srv/galaxy/venv/bin/python
    Installing setuptools, pip, wheel...done.
    $ . /srv/galaxy/venv/bin/activate
    (venv)$

Next, in ``galaxy.yml``, set the ``virtualenv`` option in the ``uwsgi`` section to point to your new virtualenv:

.. code-block:: yaml

    ---
    uwsgi:
        #...
        virtualenv: /srv/galaxy/venv

Install dependencies
^^^^^^^^^^^^^^^^^^^^

Normally, ``run.sh`` calls `common_startup.sh`_, which creates the virtualenv and installs dependencies. You can call
this script yourself to set up Galaxy pip and the dependencies without creating a virtualenv using the
``--no-create-venv`` option:

.. code-block:: console

    (venv)$ PYTHONPATH= sh /srv/galaxy/server/scripts/common_startup.sh --no-create-venv
    Requirement already satisfied: pip>=8.1 in /home/nate/.virtualenvs/test/lib/python2.7/site-packages
    Collecting numpy==1.9.2 (from -r requirements.txt (line 4))
      Downloading https://wheels.galaxyproject.org/packages/numpy-1.9.2-cp27-cp27mu-manylinux1_x86_64.whl (10.2MB)
        100% |████████████████████████████████| 10.2MB 21.7MB/s 
    Collecting bx-python==0.7.3 (from -r requirements.txt (line 5))
      Downloading https://wheels.galaxyproject.org/packages/bx_python-0.7.3-cp27-cp27mu-manylinux1_x86_64.whl (2.1MB)
        100% |████████████████████████████████| 2.2MB 97.2MB/s 

        ...

    Installing collected packages: numpy, bx-python, ...
    Successfully installed numpy-1.9.2 bx-python-0.7.3 ...

.. warning::

    If your ``$PYTHONPATH`` is set, it may interfere with the dependency installation process. Without
    ``--no-create-venv`` the ``$PYTHONPATH`` variable will be automatically unset, but we assume you know what you're
    doing and may want it left intact if you are using ``--no-create-venv``. If you encounter problems, try unsetting
    ``$PYTHONPATH`` as shown in the example above.

.. _common_startup.sh: https://github.com/galaxyproject/galaxy/blob/dev/scripts/common_startup.sh

Dependency management complications
-----------------------------------

Certain deployment scenarios or other software may complicate Galaxy dependency management. If you use any of these,
relevant information can be found in the corresponding subsection below.

Galaxy job handlers
^^^^^^^^^^^^^^^^^^^

All Galaxy jobs run a metadata detection step on the job outputs upon completion of the tool. The metadata detection
step requires many of Galaxy's dependencies. Because of this, it's necessary to make sure the metadata detection step
runs in Galaxy's virtualenv. If you run a relatively simple Galaxy deployment (e.g. ``run.sh``) then this is assured for
you automatically. In more complicated setups (running under supervisor and/or the virtualenv used to start Galaxy is
not on a shared filesystem) it may be necessary to make sure the handlers know where the virtualenv (or a virtualenv
containing Galaxy's dependencies) can be found.

If the virtualenv cannot be located, you will see job failures due to Python ``ImportError`` exceptions, like so:

.. code-block:: pytb

	Traceback (most recent call last):
	  File "/srv/galaxy/tmp/job_working_directory/001/set_metadata_RK41sy.py", line 1, in <module>
		from galaxy_ext.metadata.set_metadata import set_metadata; set_metadata()
	  File "/srv/galaxy/server/lib/galaxy_ext/metadata/set_metadata.py", line 23, in <module>
		from sqlalchemy.orm import clear_mappers
	ImportError: No module named sqlalchemy.orm

If this is the case, you can instruct jobs to activate the virtualenv with an ``env`` tag in ``job_conf.xml``:

.. code-block:: xml

    <destination id="cluster" runner="drmaa">
        <!-- ... other destination params -->
        <env file="/cluster/galaxy/venv/bin/activate" />
    </destination>

If your Galaxy server's virtualenv isn't available on the cluster you can create one manually using the instructions
under `Managing dependencies manually`_.

Pulsar
^^^^^^

If using `Pulsar`_'s option to set metadata on the remote server, the same conditions as with `Galaxy job handlers`_
apply. You should create a virtualenv on the remote resource, install Galaxy's dependencies in to it, and set an
``<env>`` tag pointing to the virtualenv's ``activate`` as in the `Galaxy job handlers`_ section. Instructions on how to
create a virtualenv can be found under the `Managing dependencies manually`_ section.

.. _Pulsar: https://pulsar.readthedocs.io/

Conda
^^^^^

.. caution::
    These instruction apply to Galaxy release 19.01 or newer. Please consult the documentation for your version of Galaxy.


`Conda`_ and `virtualenv`_ are incompatible, unless an adapted ``virtualenv`` package from the `conda-forge`_ channel is used.
Galaxy can create a virtualenv using the adapted virtualenv package. Once a valid ``.venv`` environment exists it will be used.

.. tip::

    If you would like to use a virtualenv created by Conda, the simplest method is:

        1. Ensure ``.venv`` does not exist.
        2. Place ``conda`` on your PATH if it isn't.
        3. Start galaxy using ``sh run.sh`` or execute ``sh scripts/common_startup.sh``.


    A Conda environment named ``_galaxy_`` will be created using python 2 and the appropriate virtualenv package will be installed into this environment.
    Using this environment a ``.venv`` is initialized. This is a one-time setup, and all other activation and dependency
    management happens exactly as if a system python was used for creating ``.venv``.

.. _Conda: https://conda.io/
.. _Conda environments: https://conda.io/docs/user-guide/tasks/manage-environments.html
.. _conda-forge: https://conda-forge.org/
.. _Bioconda: https://bioconda.github.io/

uWSGI
^^^^^

``run.sh`` should automatically set ``--virtualenv`` on uWSGI's command line. However, you can override this using the
``virtualenv`` option in the ``uwsgi`` section of ``galaxy.yml`` as described in the `Managing dependencies manually`_
section.

Unpinned dependencies
^^^^^^^^^^^^^^^^^^^^^

.. danger::

    Unpinned dependencies may be useful for development but should not be used in production. Please do not install
    unpinned dependencies unless you know what you're doing. While the :doc:`Galaxy Committers </project/organization>`
    will do their best to keep dependencies updated, they cannot provide support for problems arising from unpinned
    dependencies.

Galaxy's dependencies can be installed either "pinned" (they will be installed at exact versions specified for your
Galaxy release) or "unpinned" (the latest versions of all dependencies will be installed unless there are known
incompatibilities with new versions). By default, the release branches of Galaxy use pinned versions for three reasons:

1. Using pinned versions insures that the prebuilt wheels will be installed, and no
   compilation will be necessary.

2. Galaxy releases are tested with the pinned versions and this allows us to give as much assurance as possible that the
   pinned versions will work with the given Galaxy release (especially as time progresses and newer dependency versions
   are released while the Galaxy release receives fewer updates.

3. Pinning furthers Galaxy's goal of reproducibility as differing dependency versions could result in non-reproducible
   behavior.

If you would like to install unpinned versions of Galaxy's dependencies, install dependencies using the `unpinned
requirements file`_, and then instruct Galaxy to start without attempting to fetch wheels:

.. code-block:: console

    (venv)$ pip install -r lib/galaxy/dependencies/requirements.txt
    (venv)$ deactivate
    $ sh run.sh --no-create-venv --skip-wheels

You may be able to save yourself some compiling by adding the argument ``--index-url
https://wheels.galaxyproject.org/simple/`` to ``pip install``, but it is possible to install all of Galaxy's
dependencies directly from PyPI_.

.. _unpinned requirements file: https://github.com/galaxyproject/galaxy/blob/dev/lib/galaxy/dependencies/requirements.txt
.. _PyPI: https://pypi.org


Adding additional Galaxy dependencies
-------------------------------------

New packages can be added to Galaxy, or the versions of existing packages can be updated, using `pipenv`_ and `Starforge`_, Galaxy's Docker-based build system.

.. note::

    Dependency pinning management is being migrated to pipenv_. As of this release, pinning for packages used for Galaxy
    development are managed by pipenv_, but pinning for regular runtime packages are still managed with manual changes
    to ``pinned-requirements.txt``. See `Pull Request #4891`_ for details.

The process is still under development and will be streamlined and automated over time. For the time being, please use
the following process to add new packages and have their wheels built:

1. Install `Starforge`_ (e.g. with ``pip install starforge`` or ``python setup.py install`` from the source). You will
   also need to have Docker installed on your system.

2. Obtain `wheels.yml`_ (this file will most likely be moved in to Galaxy in the future) and add/modify the wheel
   definition.

3. Use ``starforge wheel --wheels-config=wheels.yml <wheel-name>`` to build the wheel. If the wheel includes C
   extensions, you will probably want to also use the ``--no-qemu`` flag to prevent Starforge from attempting to build
   on Mac OS X using QEMU/KVM.

4. If the wheel build is successful, submit a pull request to `Starforge`_ with your changes to `wheels.yml`_.

5. A :doc:`Galaxy Committers group </project/organization>` member will need to trigger an automated build of the wheel
   changes in your pull request. Galaxy's Jenkins_ service will build these changes using Starforge.

6. If the pull request is merged, submit a pull request to Galaxy modifying the files in `lib/galaxy/dependencies`_ as
   appropriate.

You may attempt to skip directly to step 4 and let the Starforge wheel PR builder build your wheels for you. This is
especially useful if you are simply updating an existing wheel's version. However, if you are adding a new C extension
wheel that is not simple to build, you may need to go through many iterations of updating the PR and having a
:doc:`Galaxy Committers group </project/organization>` member triggering builds
before wheels are successfully built. You can avoid this cycle by performing
steps 1-3 locally.

.. _pipenv: https://pipenv.readthedocs.io/
.. _Starforge: https://github.com/galaxyproject/starforge/
.. _Pull Request #4891: https://github.com/galaxyproject/galaxy/pull/4891
.. _wheels.yml: https://github.com/galaxyproject/starforge/blob/master/wheels/build/wheels.yml
.. _Jenkins: https://jenkins.galaxyproject.org/
.. _lib/galaxy/dependencies: https://github.com/galaxyproject/galaxy/tree/dev/lib/galaxy/dependencies
