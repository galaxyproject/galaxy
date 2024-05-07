History
-------

.. to_doc

-------------------
24.0.2 (2024-05-07)
-------------------

No recorded changes since last release

-------------------
24.0.1 (2024-05-02)
-------------------

No recorded changes since last release

-------------------
24.0.0 (2024-04-02)
-------------------


============
Enhancements
============

* Convert sample object store configuration to YAML and support configuring inline by `@natefoo <https://github.com/natefoo>`_ in `#17222 <https://github.com/galaxyproject/galaxy/pull/17222>`_
* Migrate models to pydantic 2 by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17262 <https://github.com/galaxyproject/galaxy/pull/17262>`_
* API endpoint that allows "changing" the objectstore for "safe" scenarios.  by `@jmchilton <https://github.com/jmchilton>`_ in `#17329 <https://github.com/galaxyproject/galaxy/pull/17329>`_
* Update to black 2024 stable style by `@nsoranzo <https://github.com/nsoranzo>`_ in `#17391 <https://github.com/galaxyproject/galaxy/pull/17391>`_
* Allow filtering history datasets by object store ID and quota source. by `@jmchilton <https://github.com/jmchilton>`_ in `#17460 <https://github.com/galaxyproject/galaxy/pull/17460>`_
* Improved error messages for runtime sharing problems. by `@jmchilton <https://github.com/jmchilton>`_ in `#17794 <https://github.com/galaxyproject/galaxy/pull/17794>`_

-------------------
23.2.1 (2024-02-21)
-------------------


============
Enhancements
============

* Move and re-use persist_extra_files by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16955 <https://github.com/galaxyproject/galaxy/pull/16955>`_
* optimize object store cache operations by `@SergeyYakubov <https://github.com/SergeyYakubov>`_ in `#17025 <https://github.com/galaxyproject/galaxy/pull/17025>`_

=============
Other changes
=============

* Merge 23.1 into dev by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16534 <https://github.com/galaxyproject/galaxy/pull/16534>`_

-------------------
23.1.4 (2024-01-04)
-------------------

No recorded changes since last release

-------------------
23.1.3 (2023-12-01)
-------------------

No recorded changes since last release

-------------------
23.1.2 (2023-11-29)
-------------------

No recorded changes since last release

-------------------
23.1.1 (2023-10-23)
-------------------


=========
Bug fixes
=========

* Enable ``strict_equality`` mypy option by `@nsoranzo <https://github.com/nsoranzo>`_ in `#15808 <https://github.com/galaxyproject/galaxy/pull/15808>`_

============
Enhancements
============

* Empower Users to Select Storage Destination by `@jmchilton <https://github.com/jmchilton>`_ in `#14073 <https://github.com/galaxyproject/galaxy/pull/14073>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#15435 <https://github.com/galaxyproject/galaxy/pull/15435>`_
* Refactor badge parsing/serialization/typing for reuse. by `@jmchilton <https://github.com/jmchilton>`_ in `#15987 <https://github.com/galaxyproject/galaxy/pull/15987>`_
* Rename object stores in config. by `@jmchilton <https://github.com/jmchilton>`_ in `#16029 <https://github.com/galaxyproject/galaxy/pull/16029>`_
* Code cleanups from ruff and pyupgrade by `@nsoranzo <https://github.com/nsoranzo>`_ in `#16035 <https://github.com/galaxyproject/galaxy/pull/16035>`_
* De-duplicate code around object store caches.  by `@jmchilton <https://github.com/jmchilton>`_ in `#16108 <https://github.com/galaxyproject/galaxy/pull/16108>`_
* Improved Cache Monitoring for Object Stores by `@jmchilton <https://github.com/jmchilton>`_ in `#16110 <https://github.com/galaxyproject/galaxy/pull/16110>`_
* De-duplication and improvements to the in-process object store cache monitor by `@jmchilton <https://github.com/jmchilton>`_ in `#16111 <https://github.com/galaxyproject/galaxy/pull/16111>`_
* Refactor caching object stores ahead of adding task-based store. by `@jmchilton <https://github.com/jmchilton>`_ in `#16144 <https://github.com/galaxyproject/galaxy/pull/16144>`_

=============
Other changes
=============

* Follow up on object store selection PR. by `@jmchilton <https://github.com/jmchilton>`_ in `#15654 <https://github.com/galaxyproject/galaxy/pull/15654>`_

-------------------
23.0.6 (2023-10-23)
-------------------


=========
Bug fixes
=========

* Fix extra files path handling by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16541 <https://github.com/galaxyproject/galaxy/pull/16541>`_
* Fixes for extra files handling and cached object stores  by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16595 <https://github.com/galaxyproject/galaxy/pull/16595>`_

-------------------
23.0.5 (2023-07-29)
-------------------

No recorded changes since last release

-------------------
23.0.4 (2023-06-30)
-------------------

No recorded changes since last release

-------------------
23.0.3 (2023-06-26)
-------------------

No recorded changes since last release

-------------------
23.0.2 (2023-06-13)
-------------------

No recorded changes since last release

-------------------
23.0.1 (2023-06-08)
-------------------

No recorded changes since last release

-------------------
20.9.1 (2021-03-01)
-------------------

* Second release from the 20.09 branch of Galaxy.

-------------------
20.9.0 (2020-10-15)
-------------------

* First release from the 20.09 branch of Galaxy.

-------------------
20.5.0 (2020-07-04)
-------------------

* First release from the 20.05 branch of Galaxy.

-------------------
19.9.0 (2019-12-16)
-------------------

* Initial import from dev branch of Galaxy during 19.09 development cycle.
