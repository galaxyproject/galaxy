.. _container_resolvers:


Containers in Galaxy
====================

Galaxy can run tools inside containers using ``docker`` or ``singularity``.
The containers can be either explicit or mulled (also called multi package containers).
The former are given by ``<container>`` requirements pointing to a specific container.
The latter are containers built for a set of requirements of type ``package``.
Mulled containers are described by a hash that is unique for a set of
packages and versions (for mulled v2), e.g.
``mulled-v2-0d814cbcd5aa81b280ecadbee9e4aba8d9ab33f7:0fb38379c04f2a8a345a2c8f74b190ea9a51b6f3-0``
(mulled-v2-PACKAGEHASH:VERSIONHASH-BUILDNUMBER). For mulled containers
of single packages simply the package name and version are used instead of the hashes,
e.g. ``ucsc-liftover:357--h446ed27_4``.

Bioconda and the Galaxy project provide infrastructure to create mulled
containers and to make them globally available on the ``quay.io/biocontainers``
container registry.

1. For each bioconda package a container is deployed
2. Mulled containers are created and deployed by the infrastructure provided by the
   `multi-package-containers <https://github.com/BioContainers/multi-package-containers>`_
   repository. Mulled containers are added automatically to this repository for all tools
   in tool repositories that are crawled by the
   `planemo monitor <https://github.com/galaxyproject/planemo-monitor>`_ repository
   (which includes for instance tools-iuc and several other tool repositories).

Container Resolvers in Galaxy
-----------------------------

A container resolver tries to get a container description, i.e. the information
(URI/path to the container image, ...) that is needed to execute a tool in a
container (in the execution environment), given the requirements specified in
this tool. Galaxy implements various container resolvers that are suitable for
different needs.

Galaxy tries to execute jobs using containers if they are sent
to execution environments (previously called destinations) with either
`docker_enabled <https://github.com/galaxyproject/galaxy/blob/0742d6e27702c60d1b8fe358ae03a267e3f252c3/lib/galaxy/config/sample/job_conf.sample.yml#L419>`_ or
`singularity_enabled <https://github.com/galaxyproject/galaxy/blob/0742d6e27702c60d1b8fe358ae03a267e3f252c3/lib/galaxy/config/sample/job_conf.sample.yml#L556>`_
enabled. Note, the links to the sample configurations exemplify this for local execution environments,
but this works for any environment as long as ``docker`` or ``singularity`` are
available.

For jobs that are sent to such an execution environment Galaxy tries to obtain a
container description by sequentially executing the configured container
resolvers (see below). The job is then executed using the description returned
by the first successful container resolver.
If all configured container resolvers failed, i.e. no container description
could be obtained, the tool is by default executed using
:doc:`standard dependency resolvers <dependency_resolvers>`, e.g. ``conda``.
Alternatively, if the execution environment specifies
`require_container <https://github.com/galaxyproject/galaxy/blob/0742d6e27702c60d1b8fe358ae03a267e3f252c3/lib/galaxy/config/sample/job_conf.sample.yml#L528>`_
the job fails in this case.

Besides determining a container description, some container resolvers
also cache and/or build containers.

Configuration:
--------------

The list of container resolvers is defined using YAML. This can be
either

- globally in an extra file (``container_resolvers_config_file``) or inline the Galaxy configuration (``container_resolvers``) or
- per execution environment using ``container_resolvers_config_file`` or ``container_resolvers``

Container resolvers defined for the execution environment
take precedence over globally defined container resolvers.
A sample YAML file showing the default configuration which is active
if neither a global or local configuration is given in
`container_resolvers.yml.sample <https://github.com/galaxyproject/galaxy/tree/dev/lib/galaxy/config/sample/container_resolvers.yml.sample>`_.

During the container resolution the configured container resolvers
are sequentially applied, stopping at the first resolver that
yields a container description.

Main resolver types:
--------------------

The main types of container resolvers follow this naming scheme:
``[cached_][explicit,mulled][_singularity]``. That is

- a container resolver is either ``explicit`` or ``mulled``
- cached if it is prefixed with ``cached_`` and non-cached otherwise.
- yield a container description suitable for singularity if
  suffixed by ``_singularity`` and docker otherwise.

.. note::

   It's important to note that similarities in the names not necessarily
   imply any similarity in the function of the container resolvers.

There are the following mulled container resolvers:

- ``mulled``
- ``mulled_singularity``
- ``cached_mulled``
- ``cached_mulled_singularity``

Furthermore there are the following explicit container resolvers:

- ``explicit``
- ``explicit_singularity``
- ``cached_explicit_singularity``

Note that there is no ``cached_explicit`` resolver.

1. docker vs singularity
""""""""""""""""""""""""

Galaxy can execute tools in containers using ``docker`` or ``singularity``.
The corresponding container resolvers yield container descriptions suitable
for the corresponding "executor", i.e., docker (singularity, resp.)
container resolvers will resolve a container only in execution environments
with enabled docker (singularity, resp.). Thus, if only execution environments
with docker (resp. singularity) are present then singularity (resp. docker)
container resolvers are ignored (and may be omitted).

Note that, for the execution with ``singularity`` Galaxy relies mostly on
docker containers that are either executed directly or are converted
to singularity images. An exception is for instance explicit container
requirements of ``type="singularity"``.

2. mulled vs explicit
"""""""""""""""""""""

Mulled container resolvers apply for requirements defined by tools that are
a set of packages:

.. code-block:: xml

  <requirements>
      <requirement type="package" version="0.5">foo</requirement>
      <requirement type="package" version="1.0">bar</requirement>
  </requirements>

Explicit container resolvers apply for requirements defined by tools in the form
of a container requirement:

.. code-block:: xml

  <requirements>
      <container type="docker">quay.io/qiime2/core:2022.8</container>
  </requirements>

See also :ref:`additional_resolver_types`.

3. cached vs non-cached
"""""""""""""""""""""""

While non-cached resolvers will yield a container description pointing to an online
available docker container, cached resolvers will store container images on disk and
use those.

This distinction is the weakest: some (by name) non-cached container resolvers
can also resolve cached containers and are even responsible for the caching itself,
i.e. they execute a ``pull``.

There are important differences between Galaxy's cached docker and singularity
container resolvers. The caching mechanism essentially executes a
``docker pull`` or ``singularity pull``, respectively. For docker this creates
an entry in the docker image cache (on the local node) whereas for
singularity an image file is created in the specified ``cache_directory``.
On distributed systems ``cache_directory`` needs to be accessible on all
compute nodes.
For singularity, admins should also take care of the ``APPTAINER_CACHEDIR``
directory.

.. note::

   An additional ``docker inspect ... ; [ $? -ne 0 ] && docker pull ...``
   command is used in each job script to ensure that images are available on a compute node.
   Thereby a container will be cached after the tool run even if no cached container resolver was used.
   Admins need to take care of docker caches of the main and compute nodes.
   For distributed compute systems, built-in techniques of docker may be useful:
   https://docs.docker.com/registry/recipes/mirror/.

.. _function_of_the_resolve_function_of_the_main_resolver_types:

Function and use of the ``resolve`` function of the main resolver types:
------------------------------------------------------------------------

The resolve function is called when

1. listing the container tab in the dependency admin UI (using ``api/container_resolvers/toolbox``)
2. triggering a build from the admin UI (using ``api/container_resolvers/toolbox/install``)
3. when a job is prepared

If the ``resolve`` function implements the caching of images then this only
happens if its ``install`` parameter is set to ``True``. This is the case
in case 2 and case 3 (but see https://github.com/galaxyproject/tools-iuc/pull/5221#discussion_r1152025883).

.. note::

   It's important to understand that 1 and 2 rely on the global
   container resolver config and do not set a resolver type!

   This becomes relevant (e.g.) for setups specifying either:

   a.  container resolver config(s) only per execution environment (i.e. no global
       container resolver config) or
   b.  different global and execution environment container resolver config(s)

   In case a) the default container config will be used which contains docker
   and singularity container resolvers (see `container_resolvers.yml.sample <https://github.com/galaxyproject/galaxy/tree/dev/lib/galaxy/config/sample/container_resolvers.yml.sample>`_).
   If both container backends (i.e. the ``docker`` and ``singularity`` executables)
   are available then only the docker container resolvers will be used.

   In case b) using the Admin UI for building/caching containers might
   be impossible, but one needs to use the API directly which allows
   to specify the container type and the resolver(s) that should be used.

1. Explicit resolvers
"""""""""""""""""""""

The uncached explicit resolvers (``explicit`` and ``explicit_singularity``) only
compute a container description using an URI that suites the ``docker`` or
``singularity``, respectively.

.. note::

   Note that ``explicit`` will still cache the docker container on tool run, since
   the job script contains ``docker pull ...``

The cached explicit resolver, i.e. ``cached_explicit_singularity`` (no docker
analog available), downloads the image to the ``cache_directory`` if needed and
return a container description that points to the image file in the
``cache_directory``.

.. note::

   The ``cached_explicit_singularity`` will automatically cache the container
   on first tool run (and when the build/installation is triggered via the Admin
   UI or the API). When listing the container the container resolver will always
   yield the path (even if non existent, i.e. before the 1st tool run or the
   caching was triggered).

2. Mulled resolvers
"""""""""""""""""""

All mulled resolvers compute a mulled hash that describes the requirements and
is included in the container name (see above).

For the cached mulled resolvers (``cached_mulled`` and ``cached_mulled_singularity``)
the ``resolve`` function only queries if the required image is already cached
and returns a container description pointing to the cached image. For docker this is
done by executing ``docker images`` and for ``singularity`` the content of the
cache directory (``cache_directory``) is queried.

.. note::

    In contrast to the cached explicit resolver the cached mulled resolvers do not
    cache images, but they only query the available cached images.

The "uncached" mulled resolvers (``mulled`` and ``mulled_singularity``) by
default just return a container description containing the URI of the container
and download the image to the cache if ``install=True`` (see also
:ref:`function_of_the_resolve_function_of_the_main_resolver_types`). The caching
is done by a call to ``docker pull`` and ``singularity pull``, respectively.
Note that, by default the URI is returned in any case, i.e. even if the image
just has been downloaded or if the image is already in the cache. Only if the
resolvers are initialized with ``auto_install=True`` the ``resolve`` function
returns a container description pointing to the cached image. Note that this
makes a difference only for singularity (since for docker the URI is identical
to the name of the cached image).

.. note::

    In contrast to the uncached explicit resolver, the uncached mulled resolvers
    do cache images, but the returned container description by default points to
    the uncached URI (if the default of ``auto_install=True`` is used; otherwise
    the cached image is used).


.. _additional_resolver_types:

Additional resolver types
-------------------------

In addition there are several resolvers that allow to hardcode container identifiers
for certain conditions:

- The ``mapping`` resolver allows to map pairs of tool IDs and tool versions to
  container identifiers and container types. This allows to hardcode or overwrite
  container definitions for specific tools.
- ``fallback_no_requirements`` for tools specifying no requirements
- ``requires_galaxy_environment`` for (internal) tools that need Galaxy's (python) environment
- ``fallback`` a fallback container for tools that don't match any resolver

Building resolver types:
------------------------

There are two container resolvers that locally create a mulled container.

- ``build_mulled``
- ``build_mulled_singularity``

Note that at the moment ``build_mulled_singularity`` also requires docker for
building.

.. note::

    Instead of using these locally, it might be better to create multi package containers
    that are deployed to biocontainers using the infrastructure provided by the
    `multi-package-containers <https://github.com/BioContainers/multi-package-containers>`_
    repository, e.g. by adding more tool repositories to the
    `planemo monitor <https://github.com/galaxyproject/planemo-monitor>`_

Parameters:
-----------

- ``namespace`` defaults to ``"biocontainers"`` for the non-building and
  ``"local"`` for the building mulled resolvers. Available for all mulled
  container resolvers **except** ``cached_mulled_singularity``.
  Used to set the namespace that is used to query quay.io. Note that there
  is no `"local"` namespace at quay.io, but Galaxy uses it to refer
  to locally built images (that's why it is the default for the building
  resolvers).
- ``hash_func``: ``"v1"`` or ``"v2"`` (default: "v2"):
  Applies to all mulled container resolvers. Sets the version of the mulled
  hash that is used in the image name.
- ``shell`` Defaults to ``/bin/bash`` and sets the shell to be used in the container.
  Applies only to the resolvers listed in `Additional resolver types`_.
- ``auto_install``: defaults to ``True``.
  Applies to ``mulled``, ``mulled_singularity``, ``build_mulled``, and ``build_mulled_singularity``.
  For the non-building resolvers this controls if a container description pointing to the
  cached image shall be returned (``auto_install==False``). For the building
  resolvers the parameter controls if the container should be built
  also if the resolve function is called with ``install=False`` (e.g. when listing
  the container in the Admin UI and no other container resolver worked for a tool).

.. note::

    Admins certainly should think carefully about ``auto_install``, since there are
    many scenarios where the default is not desirable.


- ``cache_directory``: applies to singularity container resolvers that allow to
  cache images and sets the directory where to save images.
  If not set, containers are saved in ``"database/container_cache/singularity/[explicit|mulled]"``.
- ``cache_directory_cacher_type``: ``"uncached"`` (default) or ``"dir_mtime"``.
  The singularity resolvers iterate over the contents of the cache directory. The contents
  of the directory can be accessed uncached (in which case the file listing is computed for each access)
  or cached (then the listing is computed only if the mtime of the cache dir changes and on first access).
  (applies to all singularity resolvers that can cache images, except explicit_singularity)

Note on the built-in caching capabilities of singularity and docker
-------------------------------------------------------------------

It is important to note that docker as well as singularity have their own built-in
caching mechanism.

In case of docker, a ``docker pull`` (e.g. executed from a container resolver) or
``docker run`` (e.g. executed on the compute node running the job) will add the
image to the **local** image cache.
Galaxy's docker container resolvers rely on docker's built-in image cache,
i.e. they query the image cache on the node that is executing Galaxy.
If the nodes that execute jobs are different from the node executing Galaxy
it's important to note that these nodes will have independent caches that
admins might want to control.

.. note::

   For the execution of jobs Galaxy already implement the `support for using
   tarballs of container images
   <https://github.com/galaxyproject/galaxy/blob/c517e805771cc16807dfe675075a13fe6343f01f/lib/galaxy/tool_util/deps/container_classes.py#L319>`_.
   from ``container_image_cache_path`` (set in galaxy.yml) or the destination
   property ``docker_container_image_cache_path``. But at the moment none of the
   docker container resolvers creates these image tarballs.

Also singularity has its own caching mechanism and caches by default to ``$HOME/.singularity``.
It can be cleaned regularly using the ``singularity cache`` command, or disabled by using the
``SINGULARITY_DISABLE_CACHE`` environment variable.

Setting up Galaxy using docker / singularity on distributed compute resources
(in particular in real user setups) requires careful planning.

Other considerations
--------------------

Tools frequently use ``$TMP``, ``$TEMP``, or ``$TMPDIR`` (or simply use hardcoded
``/tmp``) for storing temporary data. In containerized environments ``/tmp``
is by default bound to a directory in the job working dir (``$_GALAXY_JOB_TMP_DIR``),
i.e. ``$_GALAXY_JOB_TMP_DIR:/tmp:rw`` is in the bind strings (in addition to
``$_GALAXY_JOB_TMP_DIR:$_GALAXY_JOB_TMP_DIR:rw``).
Galaxy automatically passes the environment variables ``$TMP``, ``$TEMP``, and
``$TMPDIR`` to the container and bind-mounts these.

The default bind for `/tmp` can be overwritten by setting the
`docker_volumes <https://github.com/galaxyproject/galaxy/blob/85f16381694224598dff139bcfe307d9fd4f22bc/lib/galaxy/config/sample/job_conf.sample.yml#L455>`_ and
`singularity_volumes <https://github.com/galaxyproject/galaxy/blob/85f16381694224598dff139bcfe307d9fd4f22bc/lib/galaxy/config/sample/job_conf.sample.yml#L567>`_, resp.,
configuration properties in the :doc:`job configuration <jobs>`.
