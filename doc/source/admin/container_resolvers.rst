.. _container_resolvers:

Containers in Galaxy
====================

TODO Advantages / disadvantages (docker vs singularity).

bioconda, quay.org, namespaces

mulled 

Container Resolvers in Galaxy
=============================

A container resolver tries to get a container description, i.e. the information
(URI/path to the container image, ...) that is needed to execute a tool, given the
requirements specified in this tool. Galaxy implements various container resolvers
that are suitable for different needs. 

Galaxy tries to execute jobs using containers if they are send
to execution environments (previously called destinations) with either 

- `docker_enabled <https://github.com/galaxyproject/galaxy/blob/0742d6e27702c60d1b8fe358ae03a267e3f252c3/lib/galaxy/config/sample/job_conf.sample.yml#L419>`_ or
- `singularity_enabled <https://github.com/galaxyproject/galaxy/blob/0742d6e27702c60d1b8fe358ae03a267e3f252c3/lib/galaxy/config/sample/job_conf.sample.yml#L556>`_

enabled. Note the while the links above examplify this for local execution
environments this works for any environment as long as ``docker`` or ``singularity``
are available.

For jobs that are sent to such an execution environment Galaxy tries
to obtain a container description by sequentially executing the container
resolvers that are configured for the Galaxy instance (see below).
The job is then executed using the description returned by the first successful
container resolver.
If all configured container resolvers failed, i.e. no container description
could be obtained, the tool is by default excuted using 
:doc:`standard dependency resolvers <dependency_resolvers>`, e.g. ``conda``.
Alternatively, if the excution environment specifies
`require_container <https://github.com/galaxyproject/galaxy/blob/0742d6e27702c60d1b8fe358ae03a267e3f252c3/lib/galaxy/config/sample/job_conf.sample.yml#L528>`_
the job fails in this case (TODO to be tested? or is it already).

Configuration:
--------------

TODO: per destination container resolvers

The list of container resolvers is defined using YAML that can be
specified in an extra file (``container_resolvers_config_file``) or
inline the Galaxy configuration (``container_resolvers``). 
During the container resolution the resolvers specified in this
list are sequentially applied stopping at the first resolver that
yields a container description. 

The YAML defines a list of container resolvers and their properties.
This might look as follows:

.. code-block:: yaml

   - type: "cached_explicit_singularity"
   - type: "cached_mulled_singularity"
   - type: "mulled_singularity"
     auto_install: False

would define a list of three container resolvers, and the last setting an option
of this resolver.

By default (if neither ``container_resolvers_config_file`` nor
``container_resolvers`` is specified) the following resolvers are loaded:

.. code-block:: yaml

   - type: "explicit"
   - type: "explicit_singularity"

In addition if ``enable_mulled_containers`` is set in ``galaxy.yml``

.. code-block:: yaml

   - type: "cached_mulled"
     namespace: "biocontainers"
   - type: "cached_mulled"
     namespace: "local"
   - type: "cached_mulled_singularity"
     namespace: "biocontainers"
   - type: "cached_mulled_singularity"
     namespace: "local"
   - type: "mulled"
     namespace: "biocontainers"
   - type: "mulled_singularity"
     namespace: "local"

And if ``docker`` is available also the following resolvers are added to the defaults.

   - type: "build_mulled"
   - type: "build_mulled_singularity"



The available container resolver types are described below.
The properties depend on the resolver type (see documentation
of the resolvers). Properties that do not apply to the resolver
are ignored.

.. note::

   Its's important to note that similarities in the names not necessarily
   imply any similarity in the function of the container resolvers.

Main resolver types:
--------------------

The main types of container resolvers follow this naming scheme: 
``[cached_][explicit,mulled][_singularity]``. That is

- a container resolver is either ``explicit`` or ``mulled``
- cached if it is prefixed with ``cached_`` and non-cached otherwise. 
- yield a container discription suitable for singularity if
  suffixed by ``_singularity`` and docker otherwise.

1. docker vs singularity

Galaxy can execute tools in containers using  ``docker`` or ``singularity``.
The corresponding container resolvers yield container descriptions suitable
for the corresponding "executor" (i.e. that is, docker (singularity, resp.)
container resolvers will resolve a container only in compute environments
with enabled docker (singularity, resp.). Thus, if only compute environments
with docker (resp. singularity) are present then only docker (resp. singularity)
container resolvers need to be listed. If compute environments for both
container types are in use both types of container resolvers are needed.

Note that for the execution with ``singularity`` Galaxy relies mostly on
docker containers that are either executed directly or are converted
to singularity images (except for explicit container requirements of
``type="singularity"``).

There are important differences between Galaxy's cached docker and singularity
container resolvers. The caching mechanism essentially executes a
``docker pull`` or ``singularity pull``, respectively. For docker this creates
an entry in the docker image cache (on the local node) whereas for
singularity an image file is created in the specified ``cache_directory``.
On distributed systems ``cache_directory`` needs to be accessible on all
compute nodes.

.. note::

   Using a cached docker resolver has no additional value on distributed compute
   systems since the cache is only available locally. 
   Therefore an additional ``docker inspect ... ; [ $? -ne 0 ] && docker pull ...``
   command is used in each job script.
   For distributed compute systems built in techniques of docker may be useful:
   https://docs.docker.com/registry/recipes/mirror/.


2. mulled vs explict

Mulled container resolvers apply for requirements defined by tools that are
a set of packages:

.. code-block:: xml

  <requirements>
      <requirement type="package" version="0.5">foo</requirement>
      <requirement type="package" version="1.0">bar</requirement>
  </requirements>

Explicit containers apply for requirements defined by tools in the form of a
container requirement:

.. code-block:: xml

  <requirements>
      <container type="docker">quay.io/qiime2/core:2022.8</container>
  </requirements>

3. cached vs non-cached

While non-cached resolvers will yield a container description pointing to an online
available docker container cached resolvers will store container images on disk and
use those.

There are the following mulled container resolvers:

- ``mulled``
- ``mulled_singularity``
- ``cached_mulled``
- ``cached_mulled_singularity``

Furthermore there are the following excplit container resolvers:

- ``explicit``
- ``explicit_singularity``
- ``cached_explicit_singularity``

Note that there is no ``cached_explicit`` resolver.

Function of the ``resolve`` function of the main resolver types:
----------------------------------------------------------------

The resolve function is called when 

- opening the container tab in the dependency admin UI (with ``install=False``)
- triggering a build from the admin UI (``with install=True``)
- when a job is prepared (with ``install=True``)

If the ``resolve`` function implements the caching of images then this only
happens if ``install=True``.

1. Explicit resolvers

The uncached explicit resolvers (``explicit`` and ``explicit_singularity``) only
compute a container description using an URI that suites the ``docker`` or
``singularity``, resp.

The cached explicit resolver, i.e. ``cached_explicit_singularity`` (no docker
analogon available), will download the image to the ``cache_directory`` and
return a container description that points to the image file in the
``cache_directory``.

2. Mulled resolvers

All mulled resolvers compute a mulled hash that desribes the reuirements and
corresponds (TODO corresponds not really clear) to the image name.

For the cached mulled resolvers (``cached_mulled`` and ``cached_mulled_singularity``)
the ``resolve`` function only queries if the required image is already cached
and returns a container description pointing to the cached image. For docker this is
done by executing ``docker images`` and for ``singularity`` the content of the
cache directory is queried.

.. note::

    In contrast to the cached explicit resolver the cached mulled resolvers do not
    cache images, but they only query the available cached images.

The "uncached" mulled resolvers (``mulled`` and ``mulled_singularity``) by default just return a container description containing
the URI of the container and download the image to the cache if ``install=True``.
The caching is done by a call to ``docker pull`` and ``singularity pull``, resp.
Note that the URI is returned even if the image is in the cache. 
Only if the resolvers are initialized with ``auto_install=True`` the ``resolve``
function returns a container description pointing to the image (TODO which makes a difference only for singularity?)

.. note::

    In contrast to the uncached explict resolver the uncached mulled resolvers do
    cache images, but the returned container description points to the uncached URI
    (if the default of ``auto_install=True`` is used; otherwise the cached image
    is used).

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

Note that at the moment ``build_mulled_singularity`` requires docker for building.

Instead of using these, it might be better to create multi package containers
that are deployed to biocontainers using the infrastructure provided by the
`multi-package-containers <https://github.com/BioContainers/multi-package-containers>`_
repository.

This allready happens automatically for the tools in many tool repositories, see
`planemo monitor <https://github.com/galaxyproject/planemo-monitor>`_


Parameters:
-----------

- namespace
- hash_func
- shell

- auto_install TODO no idea what this is doing / what it is good for

- ``cache_directory``: defaults to ``container_image_cache_path`` set in galaxy.yml,
  i.e. ``"database/container_cache/"``. Applies to all singularity resolvers and sets
  the directory where to save images.
- ``cache_directory_cacher_type``: ``"uncached"`` (default) or ``"dir_mtime"``.
  The singularity resolvers iterate over the contents of the cache directory. The contents
  of the directory can be accessed uncached (thn the file listing is computed for each access)
  or cached (then the listing is computed only if the mtime of the cache dir changes and on first access).
  (applies to all singularity resolvers, except explicit_singularity TODO)

Note on the built in caching of singularity and docker
------------------------------------------------------

It is important to note that docker as well as singularity have their own builtin
caching mechanism.

In case of docker Galaxy's container resolvers relies on this mechanism, i.e.
``docker pull`` commands executed on the node running Galaxy (when using the
``cached_mulled`` resolver) of the compute nodes will create entries in docker's
container cache. Admins might want to control these caches, e.g. prune them
regularly.

.. note::

   For the the execution of jobs Galaxy already implement the `support for using
   tarballs of container images
   <https://github.com/galaxyproject/galaxy/blob/c517e805771cc16807dfe675075a13fe6343f01f/lib/galaxy/tool_util/deps/container_classes.py#L319>`_.
   from ``container_image_cache_path`` (set in galaxy.yml) or the destination
   property docker_container_image_cache_path. But at the moment non of the
   docker container resolvers creates these image tarballs.

Also singularity has its own caching mechanism and caches by default to ``$HOME/.singularity``.
It may be cleaned regularly using ``singularity cache`` of be disabled by using the
``SINGULARITY_DISABLE_CACHE``. Environment variable.

Setting up Galaxy using docker / singularity on distributed compute resources
(in particular in real user setups) requires careful planning.
