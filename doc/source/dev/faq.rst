How Do I ...
===========

This section contains a number of smaller topics with links and examples meant
to provide relatively concrete answers for specific Galaxy development scenarios.

... interact with the Galaxy database interactively?
----------------------------------------------------

This can be done with either IPython or a plain Python console, depending on your preferences:

.. code-block:: python

    python -i scripts/db_shell.py

... build Galaxy Javascript frontend client?
--------------------------------------------

We have added a Makefile which will let you do this. You can simply run:

.. code-block:: bash

    make client

Please see the ``Makefile`` itself for details and other options. There is also a readme at
``client/README.md``.

... rebuild the Galaxy configuration schema?
-------------------------------------------

Galaxy and the Tool Shed each have a schema that is used to validate their
configuration files. These schemas are defined in
``packages/config/src/galaxy/config/schemas/config_schema.yml`` (for ``galaxy.yml``) and
``packages/config/src/galaxy/config/schemas/tool_shed_config_schema.yml`` (for ``tool_shed.yml``).
If you need to add or modify a configuration option, edit the relevant schema
file directly instead of the corresponding
``packages/config/src/galaxy/config/sample/*.yml.sample`` file, then run the following
command from Galaxy's root directory to regenerate the sample YAML files
(and, for Galaxy, the RST documentation and type stubs):

.. code-block:: bash

    make config-rebuild

Then add the regenerated files to your commit.

... add or update a Galaxy Python dependency?
----------------------------------------------

Galaxy's Python dependencies are declared in the root ``pyproject.toml``
file. Each subdirectory of ``packages/`` also corresponds to a package
published on PyPI (e.g. ``packages/util/`` is ``galaxy-util``) and has its
own ``pyproject.toml``. If a dependency is needed by the code of one or more
of these packages, also add it to the ``dependencies`` list of the relevant
``packages/<package>/pyproject.toml`` file(s).

After editing the root ``pyproject.toml``, run the following command from
Galaxy's root directory to update the pinned requirements files (the runtime
export ``pinned-requirements.txt`` stays under
``packages/app/src/galaxy/dependencies/`` where it ships with the wheel; the
tooling requirement files are regenerated under the repository-level
``requirements/`` directory). This also regenerates the root ``uv.lock``,
which is tracked in the repository and is never hand-edited; regenerate
it with the uv version pinned in the root ``.uv-version`` file:

.. code-block:: bash

    make update-dependencies

Then add the updated ``pyproject.toml`` and pinned requirements files to
your commit. ``uv lock --check`` verifies that ``uv.lock`` is up to date
without modifying it, and
``UV_CHECK=1 bash packages/app/src/galaxy/dependencies/update.sh``
additionally verifies the exported requirements files without upgrading
anything. If a merge conflicts on ``uv.lock``, resolve the conflicts in the
``pyproject.toml`` manifests and dependency groups first, regenerate the lock
with the pinned uv version, and review the resulting dependency diff; never
concatenate lock files or run broad upgrades (e.g. ``uv lock --upgrade``) in
source-move changes.
