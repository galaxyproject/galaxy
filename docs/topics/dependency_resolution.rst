Dependency Resolution
=============================================

`galaxy-lib` includes a pluggable dependency resolution system that can be used to map software descriptions
(such a Galaxy ``requirement`` tags or CWL tool ``SoftwareRequirement`` annotations) to shell command that
inject these software requirements into a shell job.

This module for dependency resolution has been integrated with:

- `Galaxy <https://galaxyproject.org/>`__
- `cwltool <https://github.com/common-workflow-language/cwltool#leveraging-softwarerequirements-beta>`__
- `Plaemo <https://github.com/galaxyproject/planemo>`__
- `Pulsar <https://github.com/galaxyproject/pulsar>`__
- A fork of `Toil <https://github.com/BD2KGenomics/toil/pull/1757>`__

Dependency resolvers are configured from within a dependency resolvers configuration file (e.g.
``dependency_resolvers_conf.yml``). This file can be either XML or YAML and must contain an ordered
list of dependency resolvers to configure.

The dependency resolution system will attempt to walk through each requirement and find the first
resolver that matches that requirement. The configuration corresponding to the default Galaxy
resolution is discussed `here <https://docs.galaxyproject.org/en/latest/admin/dependency_resolvers.html>`__
and various CWL examples are worked through in the `cwltool` README `here <https://github.com/common-workflow-language/cwltool#leveraging-softwarerequirements-beta>`__.

Below some of the command resolvers are discussed in detail and some of their options are described as well but
no promise of completeness is made. Please consult the code for the latest options.

=============================================
The Resolvers
=============================================

Conda Dependency Resolver - ``conda``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``conda`` directive can be used to configure a conda dependency resolver.
This resolver can be configured with the following options.

For a very detailed discussion of Conda dependency resolution, check out the
`Galaxy Conda FAQ <https://docs.galaxyproject.org/en/latest/admin/conda_faq.html>`__.

prefix
    The conda_prefix used to locate dependencies in (default: ``<tool_dependency_dir>/_conda``).

exec
    The conda executable to use, it will default to the one on the
    PATH (if available) and then to ``<conda_prefix>/bin/conda``.

versionless
    whether to resolve tools using a version string or not (default: ``False``).

debug
    Pass debug flag to conda commands (default: ``False``).

ensure_channels
    conda channels to enable by default. See
    http://conda.pydata.org/docs/custom-channels.html for more
    information about channels. This defaults to ``iuc,conda-forge,bioconda,defaults``.
    This order should be consistent with the `Bioconda prescribed order <https://github.com/bioconda/bioconda-recipes/blob/master/config.yml>`__
    if it includes ``bioconda``.

auto_install
    If ``True``, Galaxy will look for and install missing tool
    dependencies before running a job (default: ``False``).

auto_init
    If ``True``, Galaxy will try to install Conda from the web
    automatically if it cannot find a local copy and ``conda_exec`` is not
    configured. This defaults to ``True`` as of Galaxy 17.01.

copy_dependencies
    If ``True``, Galaxy will copy dependencies over instead of symbolically
    linking them when creating per job environments. This should be considered somewhat
    deprecated because Conda will do this as needed for newer versions of Conda - such
    as the version targeted with Galaxy 17.01+.

mapping_files
    See a discussion of mapping files below.


Galaxy Packages Dependency Resolver - ``galaxy_packages``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``galaxy_packages`` dependency resolver allows Galaxy admins to specify how Galaxy should load manually
installed packages. This resolver can be configured either to use the version string or in *versionless* mode.

The Galaxy Packages dependency resolver takes a ``base_path`` argument that specifies the path under which
it starts looking for the files it requires. The default value for this ``base_path`` is the
``tool_dependency_dir`` configured in Galaxy's ``config/galaxy.ini``. Below the base path, the Galaxy Packages
resolver looks for directories named after tools, e.g. ``bedtools``. As mentioned before, this resolver
works in versioned and versionless mode. The default mode is versioned, where the dependency resolver looks for a
directory named after the dependency's version string. For example, if the Galaxy tool specifies that it
needs ``bedtools`` version 2.20.1, the dependency resolver will look for a directory ``bedtools/2.20.1``.

If the Galaxy Package dependency resolver finds a ``bin`` directory in this directory, it adds it to the ``PATH``
used by the scripts Galaxy uses to run tools. If, however, it finds an ``env.sh`` script, it sources this
script before running the tool that requires this dependency. This can be used to set up the environment
needed for the tool to run.

A simple example might be to assume that a collection of bioinformatics software is manually installed in various
directories under ``/opt/biosoftware``. In this case a ``<tool_dependency_dir>/bedtools/2.20.1/env.sh`` could be
setup to add the corresponding bedtools installation to the Galaxy tool execution's ``PATH``.

.. code-block:: bash

    #!/bin/sh

    export PATH=$PATH:/opt/biosoftware/bedtools/2.20.1/bin


As another example, this ``env.sh`` uses `Environment Modules <http://modules.sourceforge.net/>`_
to setup the environment for ``bedtools``

.. code-block:: bash

    #!/bin/sh

    if [ -z "$MODULEPATH" ] ; then
      . /etc/profile.d/module.sh
    fi

    module add bedtools/bedtools-2.20.1

The Galaxy Package dependency resolver operates quite similarly when used in versionless module. Instead of looking
for a directory named after a version, it looks for a directory symbolic link named ``default`` that links to a
concrete version such as the ``2.20.1`` example above. For example if ``bedtools/default`` links to ``bedtools/2.20.1``.
It then looks for a `bin` subdirectory or ``env.sh`` and incorporates these in the tool script that finally gets run.
This versionless (i.e. default) lookup is also used if the package requirement does not specify a version string.

The ``mapping_file`` parameter on can be set on the dependency resolution directive for the ``galaxy_packages`` 
dependency resolver. See a discussion of mapping files below for more information.

Environment Modules Dependency Resolver - ``modules``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The example above used Environment Modules to set the ``PATH`` (and other settings) for ``bedtools``. With
the ``modules`` dependency resolver it is possible to use Environment Modules directory. This resolver
takes these parameters:

modulecmd
    path to Environment Modules' ``modulecmd`` tool

modulepath
    value used for MODULEPATH environment variable, used to locate modules

versionless
    whether to resolve tools using a version string or not (default: ``false``)

find_by
    whether to use the ``DirectoryModuleChecker`` or ``AvailModuleChecker`` (permissable values are ``directory`` or ``avail``,
    default is ``avail``)

prefetch
    in the AvailModuleChecker prefetch module info with ``module avail`` (default: ``true``)

default_indicator
    what indicate to the AvailModuleChecker that a module is the default version (default: ``(default)``). Note
    that the first module found is considered the default when no version is used by the resolver, so
    the sort order of modules matters.

mapping_files
    See a discussion of mapping files below.

The Environment Modules dependency resolver can work in two modes. The ``AvailModuleChecker`` searches the results
of the ``module avail`` command for the name of the dependency. If it is configured in versionless mode,
or is looking for a package with no version specified, it accepts any module whose name matches and is a bare word
or the first module whose name matched. For this reason, the default version of the module should be the first one
listed, something that can be achieved by tagging it with a word that appears first in sort order, for example the
string ``(default)`` (yielding a module name like ``bedtools/(default)``). So when looking for ``bedtools`` in
versionless mode the search would match the first module called ``bedtools``, and in versioned mode the search would
only match if a module named ``bedtools/2.20.1`` was present (assuming you're looking for ``bedtools/2.20.1``).

The``DirectoryModuleChecker`` looks for files or directories in the path specified by ``MODULEPATH`` or
``MODULESHOME`` that match the dependency being resolved. In versionless mode a match on simply
the dependency name is needed, and in versioned mode a match on the dependency name and
version string is needed.

If a module matches the dependency is found, code to executed ``modulecmd sh load`` with the name of the dependency
is added to the script that is run to run the tool. E.g. ``modulecmd sh load bedtools``. If version strings are being
used, they'll be used in the ``load`` command e.g. ``modulecmd sh load bwa/0.7.10.039ea20639``.

LMOD Dependency Resolver - ``lmod``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The LMOD dependency resolver closely mirrors the environment module dependency resolver but is 
optimized to target the `LMOD <https://www.tacc.utexas.edu/research-development/tacc-projects/lmod>`__ module
system.

The options available to this dependency resolver include:

versionless
    whether to resolve tools using a version string or not (default is ``false``).

lmodexec
    Path to the lmod executable on your system (default the value of the ``LMOD_CMD`` environment variable).

settargexec
    Path to the settarg executable on your system (default is the value of the ``LMOD_SETTARG_CMD`` environment variable)

modulepath
    Path to the folder that contains the LMOD module files on your system (default is the value of the ``MODULEPATH`` environment variable)

mapping_files
    See a discussion of mapping files below.

The LMOD dependency was implemented in Galaxy `Pull Request #4489 <https://github.com/galaxyproject/galaxy/pull/4489>`__ by @arbernard.


Tool Shed Dependency Resolver - ``tool_shed_packages``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Unlike the other dependency resolvers described here - this one is likely only useful from within Galaxy.

The ``tool_shed_packages`` dependency resolver works with explicit software packages installed from the Galaxy Tool
Shed as described by legacy ``tool_dependencies.xml`` files. When such a package is installed from the Tool Shed it
creates a directory structure under the directory that is specified as the ``tool_dependency_dir`` in Galaxy's
configuration. This directory structure contains references to the tool's ID, owner (in the Tool Shed) and version
string (amongst other things) and ultimately contains a file named ``env.sh`` that contains commands to make the
dependency runnable. This is installed, along with the packaged tool, by the tool package and doesn't require any
configuration by the Galaxy administrator.

Tools installed from the Tool Shed may also install Conda recipes and most new best practice tools do this
by default now.

The Tool Shed dependency resolver is not able to resolve package requirements that do not have a version string,
like the `bedtools` example above.

Homebrew Dependency Resolver - ``homebrew``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This dependency resolver uses homebrew packages to resolve requirements. It is highly experimental
and undocumented.


Brew Tool Shed Package Resolver - ``shed_tap``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This dependency resolver would resolve tool shed packages that had been
auto converted to the tool shed. It is highly experimental, undocumented,
and will almost certainy be removed from the code base.


======================================================
Mapping Files
======================================================

A few different dependency resolvers allow specification of a ``mapping_files`` parameter. If specified,
these files describe rules to rewrite the abstract requirements from tools to locally available values on either
the system or in a known package source such as Bioconda. Check out Galaxy `Pull Request #3444
<https://github.com/galaxyproject/galaxy/pull/3444>`__ and `Pull Request #3509
<https://github.com/galaxyproject/galaxy/pull/3509>`__ for implementation details.

The format of the mapping files is simple a YAML file with a flat list of "rules". Each rule should specify a
``from`` condition describing the abstract requirements to map and a ``to`` value that describes how the requirement
should be rewritten.

Consider the following CWL ``SoftwareRequirement`` and Galaxy ``requirement``:

.. code-block:: yaml

    hints:
      SoftwareRequirement:
        packages:
        - package: 'random-lines'
          version:
          - '1.0'


.. code-block:: xml

    <requirement type="package" version="1.0">random-lines</requirement>


Now imaging some ``galaxy_package`` or environment Module named ``randomLines`` fullfills this requirement and
is configured with a version of ``1.0.0-rc1``. The following mapping rule would allow redirecting the corresponding
resolver to target that package:

.. code-block:: yaml

    - from:
        name: randomLines
        version: 1.0.0-rc1
      to:
        name: random-lines
        version: '1.0'

If no ``version`` is specified, all versions will be targetted and the ``from`` value can simply the requirement name 
instead of a dictionary. To just target requirements without specified versions set ``unversioned: true`` in the requirement rule. For instance:

.. code-block:: yaml

    - from:
        name: package
        unversioned: true
      to:
        name: package
        version: 1.3.1


By default, Galaxy (not `galaxy-lib`) configures some mappings from Conda in the file 
`default_conda_mapping.yml
<https://github.com/galaxyproject/galaxy/blob/dev/lib/galaxy/tools/deps/resolvers/default_conda_mapping.yml>`__

Here are some examples from that file:

.. code-block:: yaml

    - from: R
      to: r-base
    - from: blast+
      to: blast
    - from:
        name: samtools
        unversioned: true
      to:
        name: samtools
        version: 1.3.1
    - from:
        name: ucsc_tools
        unversioned: true
      to:
        name: ucsc_tools
        version: 332
    - from:
        name: bedtools
        unversioned: true
      to:
        name: bedtools
        version: 2.26.0gx

Galaxy also sets up some default mapping files for both the ``conda`` and ``lmod`` dependency resolvers if the
files ``config/local_conda_mapping.yml`` or ``config/lmod_modules_mapping.yml`` respectively are present in Galaxy.
