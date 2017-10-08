The Mulled Toolkit
========================

The mulled toolkit distributed as part of `galaxy-lib` allows for the automatic 
generation and testing of containers from Conda_ packages. These containers can
be used stand alone on the command-line or automatically as part of properly
annotated Galaxy_ or CWL_ tools.

This documentation describes the low-level mulled toolkit, but for information
on using these containers automatically with tools check out these other documents:

- `Galaxy tool development with containers <http://planemo.readthedocs.io/en/latest/writing_advanced.html#dependencies-and-docker>`__
- `Using cwltool with Biocontainers <https://github.com/common-workflow-language/cwltool#leveraging-softwarerequirements-beta>`__

The mulled toolkit utilizes mulled_ with involucro_ in an automatic way to build
and test containers. This for example has been used to convert all packages in
bioconda_ into Linux Containers (Docker and rkt at the moment) and made available
via the `BioContainers Quay.io account`_.

Once you have `installed galaxy-lib
<http://galaxy-lib.readthedocs.io/en/latest/installation.html>`__,
several mulled utilities should be configured on your ``PATH`` including 
``mulled-search``, ``mulled-build``, ``mulled-build-channel``, and
``mulled-build-tool``.

Some examples of using these tools are described below.

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


.. _Galaxy: https://galaxyproject.org/
.. _CWL: http://www.commonwl.org/
.. _mulled: https://github.com/mulled/mulled
.. _involucro: https://github.com/involucro/involucro
.. _Conda: https://conda.io/
.. _BioContainers: https://github.com/biocontainers
.. _bioconda: https://github.com/bioconda/bioconda-recipes
.. _galaxy-lib: https://github.com/galaxyproject/galaxy-lib
.. _BioContainers Quay.io account: https://quay.io/organization/biocontainers
