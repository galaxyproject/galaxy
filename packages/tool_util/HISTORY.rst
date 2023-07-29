History
-------

.. to_doc

-------------------
23.0.5 (2023-07-29)
-------------------


=========
Bug fixes
=========

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

* xsd: add missing `sep` attribute for `has_n_columns` by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#16262 <https://github.com/galaxyproject/galaxy/pull/16262>`_
* Missing init prevents models.py being bundled into tool_util by `@nuwang <https://github.com/nuwang>`_ in `#16308 <https://github.com/galaxyproject/galaxy/pull/16308>`_

============
Enhancements
============

* When importing tool data bundles, use the first loc file for the matching table by `@natefoo <https://github.com/natefoo>`_ in `#16247 <https://github.com/galaxyproject/galaxy/pull/16247>`_

-------------------
23.0.2 (2023-06-13)
-------------------


=========
Bug fixes
=========

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
* Fix assertion linting to not fail on byte suffixes by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#15873 <https://github.com/galaxyproject/galaxy/pull/15873>`_
* Fix ``get_test_from_anaconda()`` and ``base_image_for_targets()`` functions by `@nsoranzo <https://github.com/nsoranzo>`_ in `#16125 <https://github.com/galaxyproject/galaxy/pull/16125>`_
* Fix test search for mulled container hashes by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16170 <https://github.com/galaxyproject/galaxy/pull/16170>`_

============
Enhancements
============

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
