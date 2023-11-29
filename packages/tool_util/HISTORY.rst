History
-------

.. to_doc

-------------------
23.1.2 (2023-11-29)
-------------------


=========
Bug fixes
=========

* Change log level for duplicate data table entries to warning by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16988 <https://github.com/galaxyproject/galaxy/pull/16988>`_
* Upgrade minimum conda to be compatible with latest conda-build by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#17013 <https://github.com/galaxyproject/galaxy/pull/17013>`_
* Fix duplicated tools in tool panel view section copying by `@jmchilton <https://github.com/jmchilton>`_ in `#17036 <https://github.com/galaxyproject/galaxy/pull/17036>`_

============
Enhancements
============

* Adds `biii` as supported xref reference type by `@kostrykin <https://github.com/kostrykin>`_ in `#16952 <https://github.com/galaxyproject/galaxy/pull/16952>`_

-------------------
23.1.1 (2023-10-23)
-------------------


=========
Bug fixes
=========

* Fixes for two framework test tools by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#15483 <https://github.com/galaxyproject/galaxy/pull/15483>`_
* add missing f for f-string by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#15584 <https://github.com/galaxyproject/galaxy/pull/15584>`_
* Fix call to `docker_cached_container_description` by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#15598 <https://github.com/galaxyproject/galaxy/pull/15598>`_
* Fix log message by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#15838 <https://github.com/galaxyproject/galaxy/pull/15838>`_
* add required_files to the tag list for linting by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#16129 <https://github.com/galaxyproject/galaxy/pull/16129>`_
* Handle appending to a results file that does not exists. by `@ksuderman <https://github.com/ksuderman>`_ in `#16233 <https://github.com/galaxyproject/galaxy/pull/16233>`_
* Improve container resolver documentation by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16280 <https://github.com/galaxyproject/galaxy/pull/16280>`_
* Add missing singularity_no_mount prop parsing by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16367 <https://github.com/galaxyproject/galaxy/pull/16367>`_
* Restore resolution of Conda environments generated from non-lowercase package names by `@nsoranzo <https://github.com/nsoranzo>`_ in `#16474 <https://github.com/galaxyproject/galaxy/pull/16474>`_
* Fix up unit tests for local use by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16483 <https://github.com/galaxyproject/galaxy/pull/16483>`_
* Fix `multiple` remote test data by `@davelopez <https://github.com/davelopez>`_ in `#16542 <https://github.com/galaxyproject/galaxy/pull/16542>`_
* Don't use ``docker run`` --user flag on OSX by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16573 <https://github.com/galaxyproject/galaxy/pull/16573>`_
* Backport tool mem fixes by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16601 <https://github.com/galaxyproject/galaxy/pull/16601>`_
* xsd: allow name attribute of test collections by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#16663 <https://github.com/galaxyproject/galaxy/pull/16663>`_
* Fix short ids in tool panel views.  by `@jmchilton <https://github.com/jmchilton>`_ in `#16800 <https://github.com/galaxyproject/galaxy/pull/16800>`_
* Fix tool panel views for versionless tool ids by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16809 <https://github.com/galaxyproject/galaxy/pull/16809>`_

============
Enhancements
============

* Decompress history data for testing assertions by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#15085 <https://github.com/galaxyproject/galaxy/pull/15085>`_
* OIDC tokens by `@SergeyYakubov <https://github.com/SergeyYakubov>`_ in `#15300 <https://github.com/galaxyproject/galaxy/pull/15300>`_
* Fix for new style conda packages by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#15446 <https://github.com/galaxyproject/galaxy/pull/15446>`_
* Move database access code out of tool_util by `@jdavcs <https://github.com/jdavcs>`_ in `#15467 <https://github.com/galaxyproject/galaxy/pull/15467>`_
* Protection against problematic boolean parameters. by `@jmchilton <https://github.com/jmchilton>`_ in `#15493 <https://github.com/galaxyproject/galaxy/pull/15493>`_
* Implement initial tool/wf test assertions module for JSON data. by `@jmchilton <https://github.com/jmchilton>`_ in `#15494 <https://github.com/galaxyproject/galaxy/pull/15494>`_
* Explore tool remote test data by `@davelopez <https://github.com/davelopez>`_ in `#15510 <https://github.com/galaxyproject/galaxy/pull/15510>`_
* xsd: add multiple to the list of attributes for all parameter types deriving from select by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#15534 <https://github.com/galaxyproject/galaxy/pull/15534>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#15564 <https://github.com/galaxyproject/galaxy/pull/15564>`_
* Container resolvers: add docs, typing and tests by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#15614 <https://github.com/galaxyproject/galaxy/pull/15614>`_
* Migrate to MyST-Parser for Markdown docs by `@nsoranzo <https://github.com/nsoranzo>`_ in `#15844 <https://github.com/galaxyproject/galaxy/pull/15844>`_
* Enable per-destination ``container_resolver_config_file`` by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#15884 <https://github.com/galaxyproject/galaxy/pull/15884>`_
* Updated doc and tests for attribute value filter by `@tuncK <https://github.com/tuncK>`_ in `#15929 <https://github.com/galaxyproject/galaxy/pull/15929>`_
* Make container builders use mamba by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#15953 <https://github.com/galaxyproject/galaxy/pull/15953>`_
* Code cleanups from ruff and pyupgrade by `@nsoranzo <https://github.com/nsoranzo>`_ in `#16035 <https://github.com/galaxyproject/galaxy/pull/16035>`_
* Vendorise ``packaging.versions.LegacyVersion`` by `@nsoranzo <https://github.com/nsoranzo>`_ in `#16058 <https://github.com/galaxyproject/galaxy/pull/16058>`_
* Merge ``Target`` class with ``CondaTarget`` by `@nsoranzo <https://github.com/nsoranzo>`_ in `#16181 <https://github.com/galaxyproject/galaxy/pull/16181>`_
* Small test decorator improvements. by `@jmchilton <https://github.com/jmchilton>`_ in `#16220 <https://github.com/galaxyproject/galaxy/pull/16220>`_
* tool_util: switch to mambaforge on non-32bit; add arm64 support by `@mr-c <https://github.com/mr-c>`_ in `#16223 <https://github.com/galaxyproject/galaxy/pull/16223>`_
* Fix tool remote test data by `@davelopez <https://github.com/davelopez>`_ in `#16311 <https://github.com/galaxyproject/galaxy/pull/16311>`_

=============
Other changes
=============

* Restore tmp mounting by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16533 <https://github.com/galaxyproject/galaxy/pull/16533>`_

-------------------
23.0.6 (2023-10-23)
-------------------


=========
Bug fixes
=========

* 
* Fixes for extra files handling and cached object stores  by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16595 <https://github.com/galaxyproject/galaxy/pull/16595>`_
* Fix create/install commands for conda 23.9.0 by `@nsoranzo <https://github.com/nsoranzo>`_ in `#16831 <https://github.com/galaxyproject/galaxy/pull/16831>`_

-------------------
23.0.5 (2023-07-29)
-------------------


=========
Bug fixes
=========

* 
* 
* Allow duplicate labels in linter if outputs contain filters  by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#15933 <https://github.com/galaxyproject/galaxy/pull/15933>`_
* Fix parsing tool metadata from bio.tools by `@kysrpex <https://github.com/kysrpex>`_ in `#16449 <https://github.com/galaxyproject/galaxy/pull/16449>`_
* Linter: fix regex for profile version by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#16480 <https://github.com/galaxyproject/galaxy/pull/16480>`_
* Adjust test_data_download method in GalaxyInteractorApi so an admin user is not required by `@simonbray <https://github.com/simonbray>`_ in `#16482 <https://github.com/galaxyproject/galaxy/pull/16482>`_

-------------------
23.0.4 (2023-06-30)
-------------------

No recorded changes since last release

-------------------
23.0.3 (2023-06-26)
-------------------


=========
Bug fixes
=========

* 
* 
* 
* xsd: add missing `sep` attribute for `has_n_columns` by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#16262 <https://github.com/galaxyproject/galaxy/pull/16262>`_
* Missing init prevents models.py being bundled into tool_util by `@nuwang <https://github.com/nuwang>`_ in `#16308 <https://github.com/galaxyproject/galaxy/pull/16308>`_

============
Enhancements
============

* 
* When importing tool data bundles, use the first loc file for the matching table by `@natefoo <https://github.com/natefoo>`_ in `#16247 <https://github.com/galaxyproject/galaxy/pull/16247>`_

-------------------
23.0.2 (2023-06-13)
-------------------


=========
Bug fixes
=========

* 
* 
* 
* 
* 
* Don't fail CWL tool parsing when Cheetah not installed by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16219 <https://github.com/galaxyproject/galaxy/pull/16219>`_
* Allow skipping ``expect_num_outputs`` when ``expect_failure`` is set in tool test by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#16237 <https://github.com/galaxyproject/galaxy/pull/16237>`_

-------------------
23.0.1 (2023-06-08)
-------------------


=========
Bug fixes
=========

* 
* 
* 
* 
* 
* 
* Fix assertion linting to not fail on byte suffixes by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#15873 <https://github.com/galaxyproject/galaxy/pull/15873>`_
* Fix ``get_test_from_anaconda()`` and ``base_image_for_targets()`` functions by `@nsoranzo <https://github.com/nsoranzo>`_ in `#16125 <https://github.com/galaxyproject/galaxy/pull/16125>`_
* Fix test search for mulled container hashes by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16170 <https://github.com/galaxyproject/galaxy/pull/16170>`_

============
Enhancements
============

* 
* 
* 
* 
* 
* Allow setting auto_decompress property in staging interface by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16014 <https://github.com/galaxyproject/galaxy/pull/16014>`_

-------------------
22.1.5 (2022-11-14)
-------------------

* Set test status to success on expected failure

-------------------
22.1.4 (2022-10-28)
-------------------

* Add missing unittest_utils package to galaxy-tool-util

-------------------
22.1.3 (2022-10-27)
-------------------

* Pin minimum pyopenssl version when installing Conda
* Add ``--strict-channel-priority`` to conda create/install commands if using conda >=4.7.5

-------------------
22.1.2 (2022-08-29)
-------------------

* Fix lint context error level
* Pin galaxy-util to >= 22.1
* Fix biocontainer resolution without beaker cache

-------------------
22.1.1 (2022-08-22)
-------------------

* First release from the 22.01 branch of Galaxy

-------------------
21.9.2 (2021-11-23)
-------------------

* Fix linting of ``multiple="true"`` select inputs.

-------------------
21.9.1 (2021-11-03)
-------------------

* Fix tool linting.

-------------------
21.9.0 (2021-11-03)
-------------------

* First release from the 21.09 branch of Galaxy.

-------------------
21.1.2 (2021-06-23)
-------------------



-------------------
21.1.1 (2021-05-21)
-------------------



-------------------
21.1.0 (2021-03-19)
-------------------

* First release from the 21.01 branch of Galaxy.

-------------------
20.9.1 (2020-10-28)
-------------------

* Bugfixes to work around & annotate expected tool test failures.

-------------------
20.9.0 (2020-10-28)
-------------------

* First release from the 20.09 branch of Galaxy.

------------------------
20.9.0.dev2 (2020-08-02)
------------------------

* First release from the 20.09 branch of Galaxy.

-------------------
20.5.0 (2020-07-04)
-------------------

* First release from the 20.05 branch of Galaxy.

-------------------
20.1.0 (2020-07-04)
-------------------

* First release from the 20.01 branch of Galaxy.

-------------------
19.9.1 (2019-12-28)
-------------------

* Fix declared dependency problem with package.

-------------------
19.9.0 (2019-12-16)
-------------------

* Initial import from dev branch of Galaxy during 19.09 development cycle.
