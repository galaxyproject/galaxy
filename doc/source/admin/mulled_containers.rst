================================
Containers for Tool Dependencies
================================

Galaxy tools (also called wrappers) are able to use Conda packages
(see more information in our `Galaxy Conda documentation`_) and Docker containers as dependency resolvers.
The IUC_ recommends to use Conda packages as primary dependency resolver, mainly because Docker is not
available on every (HPC-) system. Conda on the other hand can be installed by Galaxy and maintained
entirely in user-space. Nevertheless, Docker (Containers in general) has some unique features and
there are many use-cases in the Galaxy community which makes containerized systems very appealing.

Since 2014 Galaxy supports running tools in Docker containers via a special `container annotation`_ inside of the 
requirement field.

.. code-block:: xml

    <requirements>
        <!-- Container based dependency handling -->
        <container type="docker">busybox:ubuntu-14.04</container>
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

We utilize [mulled](https://github.com/mulled/mulled) with [involucro](https://github.com/involucro/involucro)
in an automatic way. This is for example used to convert all packages in bioconda_ into Linux Containers
(Docker and rkt at the moment) and made available at the `BioContainers Quay.io account`_.

We have developed small utilities around this technology stack which is currently included in galaxy-lib_.
Here is a short introduction:

Search for containers
^^^^^^^^^^^^^^^^^^^^^

This will search for containers in the biocontainers organisation.

.. code-block:: bash

   $ mulled-search -s vsearch -o biocontainers


Build all packages from bioconda from the last 24h
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The BioConda community is building a container for every package they create with a command similar to this.

.. code-block:: bash

   $ mulled-build-channel --channel bioconda --namespace biocontainers \
      --involucro-path ./involucro --recipes-dir ./bioconda-recipes --diff-hours 25 build


Building Docker containers for local Conda packages
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Conda packages can be tested with creating a busybox based container for this particular package in the following way.
This also demonstrates how you can build a container locally and on-the-fly.

  > we modified the samtools package to version 3.0 to make clear we are using a local version

1) build your recipe

.. code-block:: bash
   
   $ conda build recipes/samtools

2) index your local builds

.. code-block:: bash
   
   $ conda index /home/bag/miniconda2/conda-bld/linux-64/


3) build a container for your local package

.. code-block:: bash
   
   $ mulled-build build-and-test 'samtools=3.0--0' \
      --extra-channel file://home/bag/miniconda2/conda-bld/ --test 'samtools --help'

The ``--0`` indicates the build version of the conda package. It is recommended to specify this number otherwise
you will override already existing images. For Python Conda packages this extension might look like this ``--py35_1``.

Build, test and push a conda-forge package to biocontainers
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

 > You need to have write access to the biocontainers repository

You can build packages from other Conda channels as well, not only from BioConda. ``pandoc`` is available from the
conda-forge channel and conda-forge is also enabled by default in Galaxy. To build ``pandoc`` and push it to biocontainrs
you could do something along these lines.


.. code-block:: bash

   $ mulled-build build-and-test 'pandoc=1.17.2--0' --test 'pandoc --help' -n biocontainers

.. code-block:: bash
  
   $ mulled-build push 'pandoc=1.17.2--0' --test 'pandoc --help' -n biocontainers


.. _Galaxy Conda documentation: ./conda_faq.rst
.. _IUC: https://wiki.galaxyproject.org/IUC
.. _container annotation:  https://github.com/galaxyproject/galaxy/blob/dev/test/functional/tools/catDocker.xml#L4
.. _BioContainers: https://github.com/biocontainers
.. _bioconda: https://github.com/bioconda/bioconda-recipes
.. _BioContainers Quay.io account: https://quay.io/organization/biocontainers
.. _galaxy-lib: https://github.com/galaxyproject/galaxy-lib
