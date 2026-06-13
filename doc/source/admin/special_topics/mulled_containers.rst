================================
Containers for Tool Dependencies
================================

Galaxy tools (also called wrappers) are able to use Conda packages
(see more information in our :doc:`Galaxy Conda documentation <../conda_faq>`) and Docker containers as dependency resolvers.
The IUC_ recommends to use Conda packages as the primary dependency resolver, mainly because Docker is not
available on every (HPC-) system. Conda on the other hand can be installed by Galaxy and maintained
entirely in user-space. Nevertheless, Docker and containers in general have some unique features and
there are many use-cases in the Galaxy community that make containerized tools very appealing.

Since 2014 Galaxy supports running tools in Docker containers via a special `container annotation`_ inside of the 
requirement field.

.. code-block:: xml

    <requirements>
        <!-- Container based dependency handling -->
        <container type="docker">busybox:1.36.1-glibc</container>
        <!-- Conda based dependency handling -->
        <requirement type="package" version="8.22">gnu_coreutils</requirement>
    </requirements>


This approach has shown two limitations that slowed down the adoption by tool developers.
First, every tool needs to be annotated with a container name (as shown above) and this container needs
to be created beforehand, usually manually. The second reason is that Galaxy tools should be deployable everywhere,
regardless of the underlying system, meaning that if Docker is not available, Galaxy should use Conda packages instead. 
This puts an additional burden on tool developers who need to take care of two dependency resolvers. This setup can cause
different tool results depending on the resolver, because both the Conda package and the Docker container are
usually not created out of the same recipe and maybe were compiled in a different way, use different sources etc.

Not an ideal solution and something we wanted to solve.

Here we demonstrate a solution that can create Containers out of Conda packages automatically.
This can be either used to support communities like BioContainers_ to create Containers
before deploying a Galaxy tool, or this can be used by Galaxy to create Containers on-demand and on-the-fly if one
is not available already.


Automatic build of Linux containers
-----------------------------------

We utilize mulled_ (with involucro_) to automatically convert all packages in Bioconda_ into Linux container images
and make them available at the `BioContainers Quay.io account`_.

We have developed small utilities around this technology stack, which is currently included in the ``galaxy-tool-util``
package, which can be installed simply using ``pip install galaxy-tool-util``. Here is a short introduction:

Search for containers
^^^^^^^^^^^^^^^^^^^^^

This will search for Docker containers (in the biocontainers organisation on quay.io), Singularity containers (located at https://depot.galaxyproject.org/singularity/), Conda packages (in the bioconda channel), and GitHub files (on the bioconda-recipes repository).

.. code-block:: bash

   $ mulled-search --destination quay conda --search vsearch

The user can specify the location(s) for a search using the ``--destination`` option. The search term is specified using ``--search``. Multiple search terms can be specified simultaneously; in this case, the search will also encompass multi-package containers. For example, ``--search samtools bamtools``, will return ``mulled-v2-0560a8046fc82aa4338588eca29ff18edab2c5aa:c17ce694dd57ab0ac1a2b86bb214e65fedef760e-0``, in addition to all individual samtools and bamtools results.

If the user wishes to specify a quay.io organization or Conda channel for the search, this may be done using the ``--organization`` and ``--channel`` options respectively, e.g. ``--channel conda-forge``. Enabling ``--json`` causes results to be returned in JSON format.


Calculate a mulled hash
^^^^^^^^^^^^^^^^^^^^^^^

Each mulled container is identified with a hash such as ``mulled-v2-8186960447c5cb2faa697666dc1e6d919ad23f3e``. You can calculate this hash using the ``mulled-hash`` command, submitting a comma-separated list of package names:

.. code-block:: bash

   $ mulled-hash samtools=1.3.1,bedtools=2.22
   mulled-v2-8186960447c5cb2faa697666dc1e6d919ad23f3e:d52e471b5bfa168ac813d54fc5dfe7f96ade56e6

The user can specify whether to generate hashes for either version 1 or version 2 containers with ``--hash``; version 2 is the default.


Build all packages from bioconda from the last 25h
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The BioConda community is building a container for every package they create with a command similar to this.

.. code-block:: bash

   $ mulled-build-channel --channel bioconda --namespace biocontainers \
      --involucro-path ./involucro --recipes-dir ./bioconda-recipes \
      --diff-hours 24 --repo-data bioconda build


Building Docker containers for local Conda packages
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Conda packages can be tested by creating a *busybox* based container for this particular package in the following way.
This also demonstrates how you can build a container locally and on-the-fly.

  > we modified the ``samtools`` package to version 3.0 to make it clear we are using a local version

1) Build your recipe

.. code-block:: bash

   $ conda build recipes/samtools

2) Index your local builds

.. code-block:: bash

   $ conda index /home/bag/miniconda3/conda-bld/linux-64/

3) Build a container for your local package

.. code-block:: bash

   $ mulled-build build-and-test 'samtools=3.0--0' \
      --channels conda-forge,bioconda,file:///home/user/conda-bld/ --test 'samtools --help'

The ``--0`` indicates the build version of the conda package. It is recommended to specify this number, otherwise
you will override already existing images. For Python Conda packages this extension might look like this ``--py35_1``.

Build, test, and push a conda-forge package to biocontainers
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

 > You need to have write access to the biocontainers repository

You can build packages from other Conda channels as well, not only from BioConda. ``pandoc`` tool is available from the
conda-forge channel and conda-forge is also enabled by default in Galaxy. To build ``pandoc`` and push it to biocontainers
you could do something along these lines.

.. code-block:: bash

   $ mulled-build build-and-test 'pandoc=1.17.2--0' --test 'pandoc --help' -n biocontainers

.. code-block:: bash

   $ mulled-build push 'pandoc=1.17.2--0' --test 'pandoc --help' -n biocontainers

Build Singularity containers from Docker containers
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Singularity containers can be built from Docker containers using the ``mulled-update-singularity-containers`` command.

To generate a single container:

.. code-block:: bash

   $ mulled-update-singularity-containers --containers samtools:1.6--0 --filepath /tmp/sing/ --installation /usr/local/bin/singularity

``--containers`` indicates the container name (here ``samtools:1.6--0``), ``--filepath`` the location where the containers should be placed, and ``--installation`` the location of the Singularity installation. (This can be found using ``whereis singularity``.)

Multiple containers can be installed simultaneously by giving ``--containers`` more than one argument:

.. code-block:: bash

   $ mulled-update-singularity-containers --containers samtools:1.6--0 bamtools:2.4.1--0 --filepath /tmp/sing/ --installation /usr/local/bin/singularity

For a large number of containers, it may be more convenient to employ the ``--container-list`` option:

.. code-block:: bash

   $ mulled-update-singularity-containers --container-list list.txt --filepath /tmp/sing/ --installation /usr/local/bin/singularity

Here ``list.txt`` should contain a list of containers, each on a new line.

In order to generate the list file the ``mulled-list`` command may be useful. The following command returns a list of all Docker containers available on the quay.io biocontainers organization, excluding those already available as Singularity containers on https://depot.galaxyproject.org/singularity/ .

.. code-block:: bash

   $ mulled-list --source docker --not-singularity --blacklist blacklist.txt --file output.txt

The list of containers will be saved as ``output.txt``. The (optional) ``--blacklist`` option may be used to exclude containers which should not be included in the output; ``blacklist.txt`` should contain a list of the 'blacklisted' containers, each on a new line.

The generated containers should also be tested. This can be achieved by affixing ``--testing test-output.log`` to the ``mulled-update-singularity-containers`` command:

.. code-block:: bash

   $ mulled-update-singularity-containers --container-list list.txt --filepath /tmp/sing/ --installation /usr/local/bin/singularity --testing test-output.log


Command Reference
=================

The sections below provide a detailed reference for each command.

mulled-search
-------------

.. code-block:: bash

   $ mulled-search --destination quay conda --search vsearch

Multi-package search::

   $ mulled-search --search samtools bamtools --destination quay

Options:

``-d, --destination``
  Where to search. Choices: ``quay``, ``singularity``, ``github``, ``conda``.
  Defaults: all of the above (``conda`` only if the ``conda`` binary is on ``PATH``).
  Multiple values can be given.

``-s, --search`` (required)
  Search term(s). Multiple terms trigger a multi-package container hash lookup.

``-o, --organization``
  Quay.io organization to search. Default: ``biocontainers``.

``-c, --channel``
  Conda channel to search. Default: ``bioconda``.

``--non-strict``
  Enable autocorrection of typos. Lists more results but can be confusing.
  Quay.io may block requests with too many queries.

``--cache-time``
  Number of seconds to reuse cached results. Default: ``900``.

``-j, --json``
  Return results in JSON format.


mulled-hash
-----------

Compute the mulled hash for a set of packages.

.. code-block:: bash

   $ mulled-hash samtools=1.3.1,bedtools=2.22
   mulled-v2-8186960447c5cb2faa697666dc1e6d919ad23f3e:d52e471b5bfa168ac813d54fc5dfe7f96ade56e6

Options:

``TARGETS`` (positional)
  Comma-separated packages for calculating the mulled hash,
  e.g. ``samtools=1.3.1,bedtools=2.22``.

``--hash``
  Hash version. Choices: ``v1``, ``v2`` (default).


mulled-build-channel
--------------------

Build mulled images for all recent conda recipe updates that do not
already have published containers on quay.io.

.. code-block:: bash

   $ mulled-build-channel --channel bioconda --namespace biocontainers \
      --involucro-path ./involucro --recipes-dir ./bioconda-recipes \
      --diff-hours 25 --repo-data bioconda build

Commands:

``list``
  Print package names that would be affected.

``build``
  Build containers for new packages.

``build-and-test``
  Build and test containers.

``all``
  Build, test, and push containers.

Options:

``--channel``
  Conda channel to fetch repodata from. Default: ``bioconda``.

``--repo-data`` (required)
  Path to published repodata. If the file does not exist, it will be
  auto-downloaded from the channel specified by ``--channel``.

``--diff-hours``
  Look back this many hours for changed recipes. Default: ``25``.

``--recipes-dir``
  Directory containing bioconda recipes. Default: ``./bioconda-recipes``.

``--force-rebuild``
  Rebuild packages even if they already exist on quay.io.

``--targets``
  Build a single container with specific package(s) instead of scanning the channel.

``--repository-name``
  Name of a single container. Leave blank to auto-generate based on packages.

Inherits all shared build options from mulled-build (``--namespace``,
``--channels``, ``--dry-run``, ``--verbose``, ``--singularity``,
``--target-platform``, etc.).


mulled-build
------------

Build a mulled container for specific conda packages.

.. code-block:: bash

   $ mulled-build build-and-test 'samtools=3.0--0' \
      --channels conda-forge,bioconda,file:///home/user/conda-bld/ \
      --test 'samtools --help'

Commands:

``build``
  Build the container image.

``build-and-test``
  Build and run a test command inside the container.

``push``
  Push the built image to the repository.

``all``
  Build, test, and push.

Target specification::

   # Single package
   mulled-build build 'samtools=1.3.1--4'

   # Multiple packages (comma-separated)
   mulled-build build 'samtools=1.3.1--4,bedtools=2.22'

   # Version-less (will use latest)
   mulled-build build 'samtools'

Options:

``TARGETS`` (positional)
  Package target(s) as ``name=version--build``. Multiple targets comma-separated.

``COMMAND`` (positional)
  ``build``, ``build-and-test``, ``push``, or ``all``.

Build options:

``-c, --channels``
  Comma-separated list of conda channels. Default: ``conda-forge,bioconda``.

``-n, --namespace``
  Quay.io namespace. Default: ``biocontainers``.

``-r, --repository-template``
  Docker repository template. Default: ``quay.io/${namespace}/${image}``.

``--target-platform``
  Target platform for cross-architecture builds.
  Choices: ``linux/amd64``, ``linux/arm64``, ``linux/arm/v7``, ``linux/ppc64le``.
  Requires binfmt/QEMU support on the Docker daemon host.
  Cannot be combined with ``--singularity``.

``--hash``
  Hash version for multi-package containers. Choices: ``v1``, ``v2`` (default).

``--name-override``
  Override mulled image name. Not recommended — metadata will not be
  detectable from the name of resulting images.

``--image-build``
  Build a versioned variant of this image.

``--repository-name``
  Name of the container. Leave blank to auto-generate based on packages.

``--involucro-path``
  Path to involucro binary. If not set, searches working directory and PATH.

``--involucro-lua-file``
  Path to invfile.lua. Default: uses bundled file.

Testing:

``--test``
  Test command to run inside the container.

``--test-files``
  Test files to mount inside the container. Comma-separated, supports
  ``source:dest`` Docker syntax. Relative paths are mounted under ``/source/``.

Output control:

``--dry-run``
  Print commands instead of executing them.

``--verbose``
  Verbose output.

Execution:

``--singularity``
  Additionally build a Singularity image. Cannot be combined with
  ``--target-platform``.

``--singularity-image-dir``
  Directory to write Singularity images to.

``--disable-strict-channel-priority``
  Disable strict channel priority. Slows resolver; use only in exceptional cases.

``--conda-version``
  Use a specific version of Conda inside the build container.

``--mamba-version``
  Use a specific version of Mamba inside the build container.

``--use-mamba``
  Use Mamba instead of Conda for package installation.

``--oauth-token``
  Token for communicating with the quay.io API.

``--check-published``
  If set, check whether the image already exists on quay.io before building.
  By default images are always rebuilt.


mulled-build-files
------------------

Build composite mulled containers from recipe combinations defined in TSV files.
Unlike ``mulled-build-channel`` (which builds single-package images for a whole
channel), this tool builds multi-package images from explicit combinations.

.. code-block:: bash

   $ mulled-build-files build
   $ mulled-build-files build /path/to/recipes.tsv

Each TSV line describes one container. Columns (tab-separated):

``targets``
  Package specification, e.g. ``samtools=1.3.1,bedtools=2.26.0``.

``image_build``
  Build number to append to the image tag (optional).

``name_override``
  Custom image name instead of auto-generated hash (optional).

``base_image``
  Base Docker image to use instead of the default busybox (optional).

Header lines (starting with ``#``) can redefine the column order.

Options:

``COMMAND`` (positional)
  ``build``, ``build-and-test``, or ``all``.

``FILES`` (positional)
  Path to a TSV file or a directory of TSV files. Default: current directory.

Inherits all shared build options from mulled-build (``--channels``,
``--namespace``, ``--target-platform``, ``--dry-run``, ``--verbose``,
``--singularity``, etc.).


mulled-build-tool
-----------------

Build a mulled container directly from a Galaxy or CWL tool definition.

.. code-block:: bash

   $ mulled-build-tool build path/to/tool.xml

The tool's ``<requirement type="package">`` tags are extracted and used
to build a matching container.

Options:

``COMMAND`` (positional)
  ``build``, ``build-and-test``, or ``all``.

``TOOL`` (positional)
  Path to a Galaxy tool XML file or CWL descriptor.

Inherits all shared build options and single-image options from mulled-build
(``--channels``, ``--namespace``, ``--target-platform``, ``--name-override``,
``--image-build``, etc.).


mulled-list
-----------

List containers from quay.io, filtered by whether they already exist as
Singularity images or Conda environments.

.. code-block:: bash

   $ mulled-list --source docker --not-singularity --blacklist blocklist.txt --file output.txt

Options:

``--source, -s``
  Source to list from. Choices: ``docker``, ``singularity``, ``conda``.

``--not-singularity``
  Exclude Docker containers that already have a Singularity build on
  https://depot.galaxyproject.org/singularity/.

``--not-conda``
  Exclude Docker containers that already have a Conda environment extracted.

``--conda-filepath``
  Path to directory of Conda environments. Required if ``--not-conda`` is used.

``-b, --blocklist, --blacklist``
  Path to a file listing containers to exclude (one per line).

``-f, --file``
  Output file. If not given, results are printed to stdout.


mulled-update-singularity-containers
------------------------------------

Convert Docker containers to Singularity images.

.. code-block:: bash

   $ mulled-update-singularity-containers --containers samtools:1.6--0 \
      --filepath /tmp/sing/ --installation /usr/local/bin/singularity

Options:

``-c, --containers``
  Container names to convert (one or more).

``-l, --container-list``
  Path to a file listing containers to convert (one per line).
  Alternative to ``--containers``.

``-f, --filepath``
  Output directory for the Singularity images.

``-i, --installation``
  Path to the Singularity installation (find with ``which singularity``).

``--no-sudo``
  Build containers without sudo.

``--testing, -t``
  Enable automatic testing. Value is the output file for test results.
  Uses a shallow search on Anaconda for test commands/imports from the
  package's ``meta.yaml`` or ``run_test.sh``.


.. _IUC: https://galaxyproject.org/iuc/
.. _container annotation:  https://github.com/galaxyproject/galaxy/blob/dev/test/functional/tools/catDocker.xml#L4
.. _BioContainers: https://github.com/biocontainers
.. _involucro: https://github.com/involucro/involucro
.. _Bioconda: https://bioconda.github.io/
.. _BioContainers Quay.io account: https://quay.io/organization/biocontainers
