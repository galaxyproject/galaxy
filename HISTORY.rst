.. :changelog:

History
-------

.. to_doc

---------------------
18.5.13 (2018-05-23)
---------------------

* Small updates to test parsing to support Galaxy workflow testing.

---------------------
18.5.12 (2018-05-22)
---------------------

* Update test data processing to allow URIs in Galaxy workflow tests.

---------------------
18.5.11 (2018-05-16)
---------------------

* Parse CWL SoftwareRequirements to Galaxy requirements (required to fix various Planemo functionality
  for CWL tools).

---------------------
18.5.10 (2018-05-10)
---------------------

* Docker logging API fix for Planemo.

---------------------
18.5.9 (2018-05-07)
---------------------

* Update CWL linting to target CWL 1.0.

---------------------
18.5.8 (2018-05-06)
---------------------

* Better error handling for Conda searching (thanks to @bgruening).
* Update against the latest Galaxy codebase.
* Add Galaxy tool linting to ensure versions are PEP 440 compliant (thanks to @davebx).

---------------------
18.5.7 (2018-03-12)
---------------------

* More tool testing client fixes, this time for ephemeris.

---------------------
18.5.6 (2018-03-12)
---------------------

* Bring in the latest Galaxy dev branch - includes code cleanup and many Python 3 fixes from
  @nsoranzo as well as client code for executing tool tests against external Galaxy instances.
* Extend tool testing client from Galaxy's dev branch with even more data collection for compatiblity
  with Planemo.

---------------------
18.5.5 (2018-03-06)
---------------------

* Fix mulled to use shlex.quote to escape single quotes in test command
  (thanks to @mbargull).
* Make markupsafe a dependency since it is import unconditionally in galaxy.tools.toolbox
  (thanks to @mbargull).
* Python 3 fix for assertion testing.

---------------------
18.5.4 (2018-03-01)
---------------------

* Make conda image for mulled builds configurable via an environment variable
  (thanks to @mbargull).

---------------------
18.5.3 (2018-02-28)
---------------------

* Fix path module for import on Windows for Pulsar.

---------------------
18.5.2 (2018-02-28)
---------------------

* Various fixes for library usage mostly related to Conda (with help from @nsoranzo).

---------------------
18.5.1 (2018-02-26)
---------------------

* Redo last release - pushed to PyPI without actually including the desired fix.

---------------------
18.5.0 (2018-02-26)
---------------------

* Another Python 3 fix for Planemo.
* Fix galaxy-lib version - this has actually been tracking the 18.05 release of Galaxy for the last two releases.

---------------------
18.1.0 (2018-02-26)
---------------------

* More Python 3 fixes for Planemo thanks to @nsoranzo.
* Bring in the latest Galaxy development branch.

---------------------
17.9.12 (2018-02-22)
---------------------

* Python 3 fix for Planemo thanks to @nsoranzo.
* Fix bad merge of miniconda update for mulled work.

---------------------
17.9.11 (2018-02-22)
---------------------

* Update to the latest Galaxy dev just prior to the branch of 18.01.
* Python 3 fixes.

---------------------
17.9.10 (2017-11-23)
---------------------

* Added docs for using mulled-build with your own quay.io account
  (thanks to @jerowe).
* Catch errors in Conda search if nothing is found (preventing planemo-monitor
  from functioning properly) (thanks to @bgruening).
* Make multi-requirement container building via mulled more stable
  (thanks to @bgruening).

---------------------
17.9.9 (2017-09-27)
---------------------

* Bring in latest updates from the 17.09 branch of Galaxy - including updating the default target Conda version and fixes for module resolution.

---------------------
17.9.8 (2017-09-26)
---------------------

* Bring in updated CWL utilities from the upstream work on CWL integration.

---------------------
17.9.7 (2017-09-19)
---------------------

* Bring in updated CWL utilities from the upstream work on CWL integration.

---------------------
17.9.6 (2017-09-15)
---------------------

* Remove ``command`` lint check that is no longer valid.

---------------------
17.9.5 (2017-09-06)
---------------------

* Bring in updated CWL utilities from the upstream work on CWL integration.

---------------------
17.9.4 (2017-09-06)
---------------------

* Bring in various Galaxy updates including numerous Conda fixes and changes (thanks to @nsoranzo).
* Improved error handling when parsing tool reStructuredText (thanks to @erasche).
* Updated CWL utilities.

---------------------
17.9.3 (2017-06-27)
---------------------

* Bug fix in from_dict parsing of tool dependency specs.

---------------------
17.9.2 (2017-06-22)
---------------------

* Sync with mulled enhancements and fixes from Galaxy's development branch.

---------------------
17.9.1 (2017-06-17)
---------------------

* Various small Singularity fixes and enhancements.

---------------------
17.9.0 (2017-06-11)
---------------------

* Bring in latest Galaxy dev changes.
* Implement support for building Singularity mulled containers.
* Implement mulled version 2 package hashing.
* Fix default namespace for mulled operations from mulled to biocontainers.

---------------------
17.5.11 (2017-05-31)
---------------------

* Fix HISTORY.rst formatting to properly render release on PyPI.
* Fix bug in new offline Conda search function introduced in 17.5.10.

---------------------
17.5.10 (2017-05-30)
---------------------

* Always clean up build directory in mulled commands (thanks to @johanneskoester).
* Expose offline mode in Conda search utility (for repeated fast searches).
* When publishing mulled containers - use quay.io API to publish them as public.
* Add explicit option ``--check-published`` to ``mulled-build-*``.
* Fix auto-installation of Involucro on first attempt.
* Handle explicit tags in ``mulled-build-files`` and add an implicit tag of ``0`` if none found.
* Fix tab parsing in ``mulled-build-files``.

---------------------
17.5.9 (2017-05-16)
---------------------

* Make mulled-search to search biocontainers instead of mulled repository by default
  (thanks to @tom-tan).
* Allow setting a new base image with mulled-build.

---------------------
17.5.8 (2017-04-23)
---------------------

* Fix mulled image cleanup. #55.

---------------------
17.5.7 (2017-03-15)
---------------------

* Updates to CWL library functionality for several months worth of CWL tool updates.
* Allow finding tools by a URI-like strings (e.g. ``file://``, ``http://``, ``dockstore://``).
* Bring in latest Galaxy updates.

---------------------
17.5.6 (2017-03-01)
---------------------

* Expanded options for mulled CLI tools and library functionality.
  Fixes #49.

---------------------
17.5.5 (2017-02-26)
---------------------

* Fix bug in 17.5.4 where under certain conditions conda-build would attempt to be setup
  with the conda --use-local flag - which is not allowed.

---------------------
17.5.4 (2017-02-26)
---------------------

* Fix local builds Conda support to reflect conda-build is required.
* Fix default target path for miniconda installs.

---------------------
17.5.3 (2017-02-24)
---------------------

* Update against the latest Galaxy dev branch changes.
* Update Conda utilities to allow using locally built packages.

---------------------
17.5.2 (2017-02-21)
---------------------

* Conda utility enhancements to fix a Planemo bug.

---------------------
17.5.1 (2017-02-21)
---------------------

* Various improvements to Galaxy tool linting.

---------------------
17.5.0 (2017-02-16)
---------------------

* Bring in the last of the Galaxy dev changes.
* Allow Conda installs to target global Conda config (for Planemo)

---------------------
17.1.2 (2017-01-23)
---------------------

* Bring in the last of the Galaxy dev changes before branch of release_17.01.
* Improvements to mulled testing thanks to @mvdbeek.

---------------------
17.1.1 (2016-12-14)
---------------------

* Revert changes to shell command execution in Galaxy that had unintended consequences for Planemo.    

---------------------
17.1.0 (2016-12-12)
---------------------

* Improved mulled logging thanks to @bgruening.
* Bring in the latest Galaxy dev changes.

---------------------
16.10.10 (2016-10-24)
---------------------

* Fix mulled package data fetching for Mac OS X (thanks to @dannon).

---------------------
16.10.9 (2016-10-21)
---------------------

* Small fixes including to reflect mulled name on quay.io changed to biocontainers.

---------------------
16.10.8 (2016-10-10)
---------------------

* More mulled enhancements and bug fixes thanks to @bgruening and @daler.

---------------------
16.10.7 (2016-10-08)
---------------------

* More mulled enhancements and bug fixes thanks to @bgruening.
* Fix bioconda support by adding conda-forge to list of default channels.

---------------------
16.10.6 (2016-10-07)
---------------------

* More mulled enhancements thanks to @bgruening.

---------------------
16.10.5 (2016-10-04)
---------------------

* Some docstring cleanup and minor tweaks to Conda support for downstream planemo mulled work.

---------------------
16.10.4 (2016-10-03)
---------------------

* More mulled fixes and enhancements.

---------------------
16.10.3 (2016-10-02)
---------------------

* Small mulled and Conda related fix and enhancements.

---------------------
16.10.2 (2016-09-30)
---------------------

* Fix setup.py for features in 16.10.1.

---------------------
16.10.1 (2016-09-29)
---------------------

* Updates for recents changes to Galaxy and initial mulled scripts and container resolver.

---------------------
16.10.0 (2016-08-31)
---------------------

* Updates for recent changes to Galaxy.

---------------------
16.7.10 (2016-08-04)
---------------------

* Updates for recent change to Galaxy.    

---------------------
16.7.9 (2016-06-13)
---------------------

* Updates for recent changes to Galaxy and cwltool.

---------------------
16.7.8 (2016-06-05)
---------------------

* Updates to include Galaxy library for verifying test outputs
  and the latest dev changes to Galaxy.

---------------------
16.7.7 (2016-05-23)
---------------------

* Fixes to CWL and Docker libraries for Planemo.

---------------------
16.7.6 (2016-05-11)
---------------------

* Fixes to cwl processing for Planemo.
    
---------------------
16.7.5 (2016-05-11)
---------------------

* Updates to cwl processing for Planemo.

---------------------
16.7.4 (2016-05-10)
---------------------

* Updates to cwl processing for Planemo.

---------------------
16.7.3 (2016-05-07)
---------------------

* Updates to cwltool_deps for Planemo.

---------------------
16.7.2 (2016-05-06)
---------------------

* Updates to tool parsing and linting for Planemo.

---------------------
16.7.1 (2016-05-02)
---------------------

* Update against the latest development branch of Galaxy.

---------------------
16.7.0 (2016-04-21)
---------------------

* Update against the latest development branch of Galaxy.

---------------------
16.4.1 (2016-04-08)
---------------------

* Update against the latest development branch of Galaxy.

---------------------
16.4.0 (2016-02-15)
---------------------

* Update against the latest development branch of Galaxy.

---------------------
16.1.9 (2016-01-14)
---------------------

* Fix a bug in the source distribution of galaxy-lib.

---------------------
16.1.8 (2016-01-12)
---------------------

* Update against Galaxy's release_16.01 branch.

---------------------
16.1.7 (2016-01-03)
---------------------

* Update against Galaxy's dev branch - including conda updates,
  dependency resolution changes, and toolbox updates.

---------------------
16.1.6 (2015-12-28)
---------------------

* Additional fixes to setup.py and updates for recent changes to
  Galaxy's dev branch.

---------------------
16.1.5 (2015-12-22)
---------------------

* Fix another bug that was preventing dependency resolution from
  working in Pulsar.

---------------------
16.1.4 (2015-12-22)
---------------------

* Another setup.py fix for job metrics module.

---------------------
16.1.3 (2015-12-22)
---------------------

* Python 3 fixes and updates for recent Galaxy dev commits.

---------------------
16.1.2 (2015-12-21)
---------------------

* Fix for missing galaxy.tools.parser package in setup.py.
* Fix LICENSE in repository.

---------------------
16.1.1 (2015-12-20)
---------------------

* Fix small issues with dependencies, naming, and versioning with first release.

---------------------
16.1.0 (2015-12-20)
---------------------

* Setup project.

.. _bioblend: https://github.com/galaxyproject/bioblend/
.. _XSD: http://www.w3schools.com/schema/
.. _lxml: http://lxml.de/
.. _xmllint: http://xmlsoft.org/xmllint.html
.. _nose: https://nose.readthedocs.org/en/latest/
