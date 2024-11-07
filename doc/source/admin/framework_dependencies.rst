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

Install dependencies
^^^^^^^^^^^^^^^^^^^^

Normally, ``run.sh`` calls `common_startup.sh`_, which creates the virtualenv and installs dependencies. You can call
this script yourself to set up Galaxy pip and the dependencies without creating a virtualenv using the
``--no-create-venv`` option:

.. code-block:: console

    (venv)$ PYTHONPATH= sh /srv/galaxy/server/scripts/common_startup.sh --no-create-venv

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

If your Galaxy server has a different Python version installed than the one on the cluster worker nodes, you might encounter an error containing this message:

.. code-block:: pytb

	File "/usr/lib/python2.7/weakref.py", line 14, in <module>
	    from _weakref import (
	ImportError: cannot import name _remove_dead_weakref
	
If you encounter this error or your Galaxy server's virtualenv isn't available on the cluster you can create one manually using the instructions under `Managing dependencies manually`_ and activate it using the above-mentioned ``env`` tag in ``job_conf.xml``.

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


    A Conda environment named ``_galaxy_`` will be created and the appropriate virtualenv package will be installed into this environment.
    Using this environment a ``.venv`` is initialized. This is a one-time setup, and all other activation and dependency
    management happens exactly as if a system Python was used for creating ``.venv``.

.. _Conda: https://conda.io/
.. _Conda environments: https://conda.io/docs/user-guide/tasks/manage-environments.html
.. _conda-forge: https://conda-forge.org/
.. _Bioconda: https://bioconda.github.io/


Adding additional Galaxy dependencies
-------------------------------------

New packages can be added to Galaxy, or the versions of existing packages can be
updated, using `uv`_ and `Wheelforge`_.

If wheels already exist on PyPI for all platforms and Python versions supported
by Galaxy, you can skip to step 3 in the process below.

1. Clone https://github.com/galaxyproject/wheelforge/ and add or edit the
   `meta.yaml` file for the package you would like to build.

2. Submit a pull request to `Wheelforge`_.

3. Add the new dependency to the ``dependencies`` list in the ``[project]``
   section (or to ``dev`` list in the ``[dependency-groups]`` section if only
   needed for Galaxy development) of `pyproject.toml`_ .
4. Run ``make update-dependencies`` to update the requirements files in `lib/galaxy/dependencies`_.
5. Submit a pull request to Galaxy with your changes.

.. _uv: https://docs.astral.sh/uv/
.. _Wheelforge: https://github.com/galaxyproject/wheelforge/
.. _pyproject.toml: https://github.com/galaxyproject/galaxy/blob/dev/pyproject.toml
.. _lib/galaxy/dependencies: https://github.com/galaxyproject/galaxy/tree/dev/lib/galaxy/dependencies
