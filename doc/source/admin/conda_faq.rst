.. _conda_faq:

===========================
Conda for Tool Dependencies
===========================

.. note:: This document describes configuring Galaxy using YAML based configuraiton
  options. For Galaxy instances before version 18.01, `this variant
  <https://docs.galaxyproject.org/en/release_17.09/admin/conda_faq.html>`__ of this
  document will be more directly relatable.

Galaxy tools (also called wrappers) have traditionally used Tool Shed package
recipes to install their dependencies. These were too tightly tied to Galaxy
and to the Tool Shed and so have been replaced with Conda as the package
management solution of choice for newer best practice tools. The
Galaxy community has taken steps to improve the tool dependency system
in order to enable new features and expand its reach. Not only do Conda packages
make tool dependencies more reliable and stable, they are also easier to test
and faster to develop than the traditional Tool Shed package recipes. This
document aims to describe these and answer frequently asked questions.

Conda is a package manager like ``apt-get``, ``yum``, ``pip``, ``brew`` or
``guix``. We don't want to argue about the relative merits of various package
managers here, in fact Galaxy supports multiple package managers and we welcome
community contributions (such as implementing a Guix package manager or
enhancing the existing brew support to bring it on par with Conda).

As a community, we have decided that Conda is the one that best fulfills
the community's current needs. The following are some of the crucial Conda
features that led to this decision:

-  Installation of packages does not require *root* privileges
   (installation at any location the Galaxy user has write access to)
-  Multiple versions of software can be installed on the system
-  HPC-ready
-  Faster and more robust package installations through pre-compiled
   packages (no build environment complications)
-  Independent of programming language (R, Perl, Python, Julia, Java,
   pre-compiled binaries, and more)
-  Easy to write recipes (1 YAML description file + 1 Bash install
   script)
-  An active, large and growing community (with more and more software
   authors managing their own recipes)
-  Extensive documentation: `Conda documentation`_ and `Conda quick-start`_

Below we answer some common questions (collected by Lance Parsons):


1. How do I enable Conda dependency resolution for Galaxy tools?
****************************************************************

The short answer is that as of 17.01, Galaxy should install Conda the first
time it starts up and be configured to use it by default.

The long answer is that Galaxy's tool dependency resolution is managed via
``dependency_resolvers`` option in the Galaxy configuration file (``galaxy.yml``). This
option is discussed in detail in the :doc:`Dependency Resolvers <dependency_resolvers>`
documentation. Most Galaxy administrators will be using Galaxy's default dependency
resolvers configuration. With release 16.04, Galaxy has enabled Conda dependency
resolution by default when Conda was already installed on the system. As of 17.01, Galaxy
will also install Conda as needed when starting up. Having Conda enabled in
``dependency_resolvers`` means that Galaxy can look for tool dependencies using the Conda
system when it attempts to run a job.

Note that the order of resolvers in the configuration option matters and that when
upgrading older Galaxy servers with existing Tool Shed tools installed, the
``tool_shed_packages`` entry should remain first. This means that tools that have
specified Tool Shed packages as their dependencies will work without a change.

The most common configuration settings related to Conda are listed in Table 1.
See :doc:`Configuration Options <options>` for the complete list. Note that these options
(without the ``conda_`` prefix) can also be set on a per-resolver basis under the
``dependency_resolvers`` option.

+-------------------------+------------------------------------+---------------------------+
| Setting                 | Default setting                    | Meaning                   |
+-------------------------+------------------------------------+---------------------------+
| ``conda_auto_init``     | ``true``                           | If ``true``, Galaxy will  |
|                         |                                    | try to install Conda      |
|                         |                                    | (the package manager)     |
|                         |                                    | automatically if it       |
|                         |                                    | cannot find a local copy  |
|                         |                                    | already on the system     |
+-------------------------+------------------------------------+---------------------------+
| ``conda_auto_install``  | ``false``                          | If ``true``, Galaxy will  |
|                         |                                    | look for and install      |
|                         |                                    | Conda packages for        |
|                         |                                    | missing tool dependencies |
|                         |                                    | before running a job      |
+-------------------------+------------------------------------+---------------------------+
| ``conda_prefix``        | ``<tool_dependency_dir>/_conda``   | The location on the       |
|                         |                                    | filesystem where Conda    |
|                         |                                    | packages and environments |
|                         |                                    | are installed             |
+-------------------------+------------------------------------+---------------------------+

*Table 1: Commonly used configuration options for Conda in Galaxy.*


2. How do Conda dependencies work? Where do things get installed?
*****************************************************************

In contrast to the Tool Shed dependency system, which was used exclusively by Galaxy,
Conda is a pre-existing, independent project. With Conda, it is possible for an
admin to install and manage packages without touching Galaxy at all. Galaxy can
handle these dependencies for you, but admins are not required to use Galaxy for
dependency management.

There are a few config options in the ``galaxy.yml`` file (see Table 1 or
:doc:`Configuration Options <options>` for more information), but by default Galaxy will install
Conda (the package manager) and the required packages in the
``<tool_dependency_dir>/_conda/`` directory. In this directory, Galaxy will
create an ``envs`` folder with all of the environments managed by Galaxy. Each
environment contains a ``lib``, ``bin``, ``share``, and ``include``
subdirectories, depending on the tool, which are sufficient to get a Galaxy tool
running. Galaxy simply sources this folder via Conda and makes everything
available before the tool is executed on your system.

To summarize, there are four ways to manage Conda dependencies for use
with Galaxy. For all of these options, Conda dependency management must
be configured in the ``dependency_resolvers`` option in the ``galaxy.yml`` file.

#. Galaxy Admin Interface - Galaxy will install Conda tool dependencies when
   tools are installed from the Tool Shed if the option **Install resolvable
   dependencies** under **Show advanced settings** on the tool install dialog is
   checked. Admins may also view and manage Conda dependencies via the **Manage
   Dependencies** section of the  Admin interface.
#. Manual Install - Conda dependencies may be installed by
   administrators from the command line. Conda (and thus the Conda
   environments) should be installed in the location specified by the
   ``conda_prefix`` path (defined in ``galaxy.yml`` and by default
   ``<tool_dependency_dir>/_conda/`` directory). Galaxy will search
   these environments for required packages when tools are run. Conda
   environment names have to follow a specific naming pattern. As an
   example, to install samtools in version 0.1.19, the administrator can
   run the command:

   .. code-block:: bash

      $ conda create --name __samtools@0.1.19 samtools==0.1.19 --channel bioconda

   Tools that require samtools version 0.1.19 will then be able to find
   and use the installed Conda package.
#. Automatically at tool run time - When a tool is run and a dependency
   is not found, Galaxy will attempt to install the dependency using
   Conda if ``conda_auto_install`` is activated in the configuration.
#. Via the API (>= 16.07) - The Galaxy community maintains an `ansible role`_
   that uses BioBlend_ and the Galaxy API to install tools. Additionally, the
   Ephemeris_ command shed-tools_ can be used to install tools via the API from
   the command line.


3. What is required to make use of this? Any specific packages, Galaxy revision, OS version, etc.?
**************************************************************************************************

The minimum required version of Galaxy to use Conda is 16.01, however
version 17.01 or greater is recommended. The 16.07 release of Galaxy has
a graphical user interface to manage packages, but this is not
required to have Conda dependencies managed and used by Galaxy.

Conda packages should work on all compatible operating systems with
*glibc* version 2.12 or newer (this includes Centos 6). So all packages
will run on all major \*nix operating systems newer than 2007.


4. If I have Conda enabled, what do I need to do to install tools using it? For example, how can I install the latest Trinity? And how will I know the dependencies are installed?
**********************************************************************************************************************************************************************************

This depends on your ``galaxy.yml`` settings. Starting with release 16.07, Galaxy
can automatically install the Conda package manager for you if you have enabled
``conda_auto_init``. Galaxy can then install Trinity along with its dependencies
using one of the methods listed in question 2 above. In particular, if
``conda_auto_install`` is ``true`` and Trinity is not installed yet, Galaxy will
try to install it via Conda when a Trinity job is launched.

With release 16.07 you can see which dependencies are being used
in the “Manage installed tools” section of the Admin panel and you can select
whether or not to install Conda packages or Tool Shed package recipes when you
install new tools there, even if ``conda_auto_install`` is disabled.

During a tool installation, the Galaxy admin has control over which systems will be used to
install the tool requirements. The default settings will trigger installation
of both Tool Shed and Conda packages (if Conda is present), thus depending on the
dependency resolvers configuration with regards to what will actually be used during
the tool execution.

To check if Galaxy has created a Trinity environment, have a look at folders under
``<tool_dependency_dir>/_conda/envs/`` (or ``<conda_prefix>/envs`` if you have changed ``conda_prefix`` in your ``galaxy.yml`` file).

We recommend to use Conda on a tool-per-tool basis, by unchecking the checkbox
for Tool Shed dependencies during the tool installation, and for tools where there
are no available Tool Shed dependencies.


5. Can I mix traditional Galaxy packages and Conda packages?
************************************************************

Yes, the way this works is that Galaxy goes through the list of
requirements for a tool, and then determines for each requirement if it
can be satisfied by any of the active resolver systems.

The order in which resolvers are tried is listed in the
``dependency_resolvers`` configuration option. The default order is

-  Tool Shed packages
-  Packages manually installed by administrators
-  Conda packages

The first system that satisfies a requirement will be used. See
:doc:`Dependency Resolvers <dependency_resolvers>` for detailed documentation.

This however is not recommended, ideally tools will target and test
against Conda for all dependencies. Also resolving all requirements
with Conda gives Conda a chance to select compatible versions of
dependencies. Read more about selecting compatible versions on
`Issue #3299`_ and `Pull Request #3391`_.

6. How do I know what system is being used by a given tool?
***********************************************************

The Galaxy log will show which dependency resolution system is used
to satisfy each tool dependency and you can specify priorities using the
``dependency_resolvers`` configuration option (see question 5 above). Starting from Galaxy
release 16.07, you can see which dependency will be used (“resolved”) in the
Admin panel (under Tool Management → Manage dependencies).


7. How do I go about specifying Conda dependencies for a tool? All the docs still seem to recommend (or exclusively discuss) the ``tool_dependencies.xml`` method.
******************************************************************************************************************************************************************

The simple answer is: you don't need to do much to make Conda work for a tool.

The ``<requirement>`` tag in the tool XML file is enough. The name and the
version should correspond to a Conda package in one of the enabled channels
(which are specified by the ``conda_ensure_channels`` directive in
``galaxy.yml`` ). If this is the case you are ready to go. Read
more about `Conda channels`_  and browse their packages on https://anaconda.org/ url followed by the channel name (e.g.
`https://anaconda.org/bioconda <https://anaconda.org/bioconda>`__
).

We will gradually adjust the documentation about ``tool_dependencies.xml`` and
deprecate it everywhere.


8. During tool installation what if there is no Conda package available for a given requirement? What if the requirement is resolved in a different software than the original wrapper author meant to use?
***********************************************************************************************************************************************************************************************************

If there is no Conda package available during tool installation the tool
will install automatically, and can be used if its dependencies are
satisfied by another dependency system such as Tool Shed package
recipes, Docker containers or modules.

If there is a package of correct name and version it will be used. There
is no equivalent of the “owner” concept used in Galaxy packages
installed from the Tool Shed.


9. Where can I find a list of existing Conda packages that I can point to, so I don't have to reinvent the wheel for common dependencies?
*****************************************************************************************************************************************

With Conda package manager installed on your system, run:

.. code-block:: bash

   $ conda search <package_name> -c iuc -c conda-forge -c bioconda

This will search in all channels that are activated by default in
Galaxy. If you find your package, you are ready to go. If not please
`create a Conda package`_ and submit_ it to BioConda_ or get in `contact with the IUC`_.


10. How can I create a new Conda package for a dependency?
**********************************************************

Adding a package to the BioConda or IUC Conda channels will make it
available for Galaxy tools to use as a dependency. To learn how, get in
touch with the awesome BioConda community. They have great documentation
and assist with all development. You will also see a few of us at this
project to get you started :)

Don't be scared! Conda recipes are really simple to write. Conda also
offers so called \`skeleton\` generators that generate recipes from
pypi, cran, or cpan for you (mostly) automatically.


11. Is there a way to convert traditional Tool Shed package recipes that are not yet in a Conda channel?
********************************************************************************************************

First, you do not need to do anything to your wrapper as long as the
package name in the requirement tag matches the name of correct
Conda package. (You may want to mention in the README or a comment the
Conda channel that contains the package).

If you want to migrate some recipes from XML to Conda, IUC is happy to
give you a hand. We are trying to get all new versions under Conda and
leave the old versions as they are – simply because of time.


12. What is the recommendation for existing installations? Will I continue to maintain both systems or migrate to the new Conda system eventually?
**************************************************************************************************************************************************

Old tools will use the traditional installation system; this system will
stay and will be supported for installing old tools to guarantee sustainability
and reproducibility. New tools from the IUC and other best practices sources
are Conda only.


13. What can I do about this placehold error?
*********************************************

If you see a warning similar to the following in your galaxy log files:

.. code-block:: bash

   ERROR: placeholder '/home/ray/r_3_3_1-x64-3.5/envs/_build_placehold_placehold_placehold_placehold_pl' too short

This means you are very likely using an older version of Conda. This
bug has been fixed with the Conda release that is targeted by Galaxy
17.01 or newer.

In the past, the work around for this limitation, was to make sure that the total length
of the ``conda_prefix`` and ``job_working_directory`` path was less than 50
characters long.


14. What can I do about this LOCKERROR error?
***********************************************

This question addresses workaround for Conda if something like the following
message appears in your logs:

.. code-block:: bash

   Error:     LOCKERROR: It looks like conda is already doing something.
       The lock ['/galaxy/galaxy-app/tool-dependencies/_conda/pkgs/.conda_lock-119903'] was found. Wait for it to finish before continuing.
       If you are sure that conda is not running, remove it and try again.
       You can also use: $ conda clean --lock

First, you may wish to enable cached dependencies. This can be done by setting
``use_cached_dependency_manager`` to ``true`` in ``galaxy.yml``. Without this
option, many jobs will create a per-job Conda environment with just the
dependencies needed for that job installed.
This will be placed on the filesystem containing the job working directory. This
is an expensive operation and Conda doesn't always link environments correctly
across filesystems. Enabling this dependency caching will create a cache
directory for each required combination of requirements inside the directory
specified by ``tool_dependency_cache_dir`` in ``galaxy.yml`` (defaulting to
``<tool_dependency_dir>/_cache``).

The cached dependency manager was added to the 16.10 release of Galaxy (see
`Pull Request #3106`_). In 17.01 Galaxy was updated to build the cached dependencies
as needed if the caching is in fact enabled (see `Pull Request #3348`_) and reduced
the number of jobs that would require such caching (see `Pull Request #3391`_).


15. What can I do about linking errors?
***************************************

If Galaxy jobs run on filesystems that cannot hardlink Conda packages managed
by Galaxy, linking errors may occur when building environment to execute jobs.
There are a few ways to potentially work around this.

The most straight forward and efficient work around is probably just to enable the cached
dependency manager as described in the previous question. Notice the default location
of the cache is right next to the default Conda directory - so hardlinks should
lie on the same file system as the default Conda installation.

If this still doesn't work, perhaps the underlying file system does not support hard
linking at all. In this case it is best to add ``always_softlink: True`` to Galaxy's
YAML ``condarc`` file, this should be created by Galaxy and placed in
``<tool_dependency_dir/_condarc``. This requires Conda 4.3 or newer. Note this is a
newer version of Conda than shipped with Galaxy as of 17.01. See the question below
on upgrading Conda if you must use this trick.

Alternatively, copying can be used when creating environments instead of links (either
symbolic or hard). To enable this set ``conda_copy_dependencies`` to ``true`` in
``galaxy.yml``. This requires at least version 16.07 of Galaxy.

More reading on this can be found at `Conda Pull Request #3870`_, `Conda Issue #3308`,
and Galaxy `Issue #3193`_.

16. What can I do if Conda doesn't work for me?
***********************************************

Please review the common problems covered in the previous few questions, if your
problem is different more investigation will be needed.

In rare cases Conda may not have been properly installed by Galaxy.
A symptom for this is if there is no activate script in
``<conda_prefix>/bin`` folder. In that case you can delete the ``conda_prefix`` folder
and restart Galaxy, which will again attempt to install Conda.

If this does not solve your problem or you have any trouble following
the instructions, please ask on the Galaxy developing mailing list or the Galaxy
Gitter or IRC channel.

17. How can I upgrade Conda?
****************************

Many potential issues with Conda have been resolved with fixes in Conda itself.
The Conda installed by Galaxy can be updated to e.g. version 4.6.14 with the
following command:

.. code-block:: bash

   $ <tool_dependency_dir>/_conda/bin/conda install -c conda-forge conda==4.6.14

The command can obviously be adapted to install any version of Conda. If the
above command fails with an error like:

.. code-block:: bash

   UnsatisfiableError: The following specifications were found to be in conflict:
     - conda ==4.6.14 -> python >=3.6,<3.7.0a0
     - python 3.5*
   Use "conda info <package>" to see the dependencies for each package.

Then you need to also update the ``python`` package installed in the base
environment by appending to the ``conda install`` command above an appropriate
specification, which for the example error above would be ``python==3.6``:

.. code-block:: bash

   $ <tool_dependency_dir>/_conda/bin/conda install -c conda-forge conda==4.6.14 python==3.6


.. _Conda documentation: https://conda.io/docs/
.. _Conda quick-start: https://conda.io/docs/user-guide/getting-started.html
.. _ansible role: https://github.com/galaxyproject/ansible-galaxy-tools
.. _BioBlend: https://github.com/galaxyproject/bioblend
.. _Ephemeris: https://ephemeris.readthedocs.io/
.. _shed-tools: https://ephemeris.readthedocs.io/en/latest/commands/shed-tools.html
.. _Conda channels: https://conda.io/docs/user-guide/tasks/manage-channels.html
.. _create a Conda package: https://conda.io/docs/user-guide/tasks/build-packages/recipe.html
.. _submit: https://bioconda.github.io/#step-4-join-the-team
.. _BioConda: https://bioconda.github.io
.. _contact with the IUC: https://gitter.im/galaxy-iuc/iuc
.. _Pull Request #3106: https://github.com/galaxyproject/galaxy/pull/3106
.. _Pull Request #3348: https://github.com/galaxyproject/galaxy/pull/3348
.. _Pull Request #3391: https://github.com/galaxyproject/galaxy/pull/3391
.. _Issue #3193: https://github.com/galaxyproject/galaxy/issues/3193
.. _Conda Pull Request #3870: https://github.com/conda/conda/pull/3870
.. _Conda Issue #3308: https://github.com/conda/conda/issues/3308
.. _Issue #3299: https://github.com/galaxyproject/galaxy/issues/3299
