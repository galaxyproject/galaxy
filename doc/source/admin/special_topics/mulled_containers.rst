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
to be created beforehand, usually manually. The second reason is that a Galaxy tool aims to be deployed everywhere,
independet of the underlying system, meaning if Docker is not available Galaxy should use Conda packages. 
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

We utilize mulled_ with involucro_ to automatically convert all packages in Bioconda_ into Linux containers images 
(Docker and rkt at the moment) and make them available at the `BioContainers Quay.io account`_.

We have developed small utilities around this technology stack, which is currently included in the ``galaxy-tool-util``
package, which can be installed simply using ``pip install galaxy-tool-util``. Here is a short introduction:

Search for containers
^^^^^^^^^^^^^^^^^^^^^

This will search for Docker containers (in the biocontainers organisation on quay.io), Singularity containers (located at https://depot.galaxyproject.org/singularity/), Conda packages (in the bioconda channel), and GitHub files (on the bioconda-recipes repository. 

.. code-block:: bash

   $ mulled-search --destination docker conda --search vsearch

The user can specify the location(s) for a search using the ``--destination`` option. The search term is specified using ``--search``. Multiple search terms can be specified simultaneously; in this case, the search will also encompass multi-package containers. For example, ``--search samtools bamtools``, will return ``mulled-v2-0560a8046fc82aa4338588eca29ff18edab2c5aa:c17ce694dd57ab0ac1a2b86bb214e65fedef760e-0``, in addition to all individual samtools and bamtools results.

If the user wishes to specify a quay.io organization or Conda channel for the search, this may be done using the ``--organization`` and ``--channel`` options respectively, e.g. ``--channel conda-forge``. Enabling ``--json`` causes results to be returned in JSON format.


Calculate a mulled hash
^^^^^^^^^^^^^^^^^^^^^^^

Each mulled container is identified with a hash such as ``mulled-v2-8186960447c5cb2faa697666dc1e6d919ad23f3e``. You can calculate this hash using the ``mulled-hash`` command, submitting a comma-separated list of package names:

.. code-block:: bash

   $ mulled-hash samtools=1.3.1,bedtools=2.22
   mulled-v2-8186960447c5cb2faa697666dc1e6d919ad23f3e:d52e471b5bfa168ac813d54fc5dfe7f96ade56e6

The user can specify whether to generate hashes for either version 1 or version 2 containers with ``--hash``; version 2 is the default.


Build all packages from bioconda from the last 24h
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The BioConda community is building a container for every package they create with a command similar to this.

.. code-block:: bash

   $ mulled-build-channel --channel bioconda --namespace biocontainers \
      --involucro-path ./involucro --recipes-dir ./bioconda-recipes --diff-hours 25 build


Building Docker containers for local Conda packages
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Conda packages can be tested with creating a *busybox* based container for this particular package in the following way.
This also demonstrates how you can build a container locally and on-the-fly.

  > we modified the ``samtools`` package to version 3.0 to make it clear we are using a local version

1) Build your recipe

.. code-block:: bash
   
   $ conda build recipes/samtools

2) Index your local builds

.. code-block:: bash
   
   $ conda index /home/bag/miniconda2/conda-bld/linux-64/


3) Build a container for your local package

.. code-block:: bash
   
   $ mulled-build build-and-test 'samtools=3.0--0' \
      --extra-channel file://home/bag/miniconda2/conda-bld/ --test 'samtools --help'

The ``--0`` indicates the build version of the conda package. It is recommended to specify this number, otherwise
you will override already existing images. For Python Conda packages this extension might look like this ``--py35_1``.

Build, test, and push a conda-forge package to biocontainers
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

 > You need to have write access to the biocontainers repository

You can build packages from other Conda channels as well, not only from BioConda. ``pandoc`` tool is available from the
conda-forge channel and conda-forge is also enabled by default in Galaxy. To build ``pandoc`` and push it to biocontainrs
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

   $ mulled-update-singularity-containers --containers samtools:1.6--0 --logfile /tmp/sing/test.log --filepath /tmp/sing/ --installation /usr/local/bin/singularity

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

The list of containers will be saved as ``output.txt``. The (optional) ``--blacklist`` option may be used to exclude containers which should not included in the output; ``blacklist.txt`` should contain a list of the 'blacklisted' containers, each on a new line.

The generated containers should also be tested. This can be achieved by affixing ``--testing test-output.log`` to the ``mulled-update-singularity-containers`` command:

.. code-block:: bash

   $ mulled-update-singularity-containers --container-list list.txt --filepath /tmp/sing/ --installation /usr/local/bin/singularity --testing test-output.log

.. _IUC: https://galaxyproject.org/iuc/
.. _container annotation:  https://github.com/galaxyproject/galaxy/blob/dev/test/functional/tools/catDocker.xml#L4
.. _BioContainers: https://github.com/biocontainers
.. _mulled: https://github.com/mulled/mulled
.. _involucro: https://github.com/involucro/involucro
.. _Bioconda: https://bioconda.github.io/
.. _BioContainers Quay.io account: https://quay.io/organization/biocontainers
