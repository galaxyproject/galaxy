History
-------

.. to_doc

---------
25.0.dev0
---------



-------------------
24.2.0 (2025-02-11)
-------------------


=========
Bug fixes
=========

* Fixes for errors reported by mypy 1.11.0 by `@nsoranzo <https://github.com/nsoranzo>`_ in `#18608 <https://github.com/galaxyproject/galaxy/pull/18608>`_

============
Enhancements
============

* Implement Declarative Testing for Workflow Behaviors by `@jmchilton <https://github.com/jmchilton>`_ in `#18542 <https://github.com/galaxyproject/galaxy/pull/18542>`_
* Allow a posix file source to prefer linking. by `@jmchilton <https://github.com/jmchilton>`_ in `#19132 <https://github.com/galaxyproject/galaxy/pull/19132>`_

-------------------
24.1.4 (2024-12-11)
-------------------

No recorded changes since last release

-------------------
24.1.3 (2024-10-25)
-------------------

No recorded changes since last release

-------------------
24.1.2 (2024-09-25)
-------------------

No recorded changes since last release

-------------------
24.1.1 (2024-07-02)
-------------------


============
Enhancements
============

* Adding object store plugin for Rucio by `@SergeyYakubov <https://github.com/SergeyYakubov>`_ in `#17156 <https://github.com/galaxyproject/galaxy/pull/17156>`_
* Code cleanups from ruff and pyupgrade by `@nsoranzo <https://github.com/nsoranzo>`_ in `#17654 <https://github.com/galaxyproject/galaxy/pull/17654>`_
* Overhaul Azure storage infrastructure. by `@jmchilton <https://github.com/jmchilton>`_ in `#18087 <https://github.com/galaxyproject/galaxy/pull/18087>`_
* Empower users to bring their own storage and file sources by `@jmchilton <https://github.com/jmchilton>`_ in `#18127 <https://github.com/galaxyproject/galaxy/pull/18127>`_

-------------------
24.0.3 (2024-06-28)
-------------------


=========
Bug fixes
=========

* Skip tests if toolshed, dx.doi not responding by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18250 <https://github.com/galaxyproject/galaxy/pull/18250>`_
* Move tool shed specific driver function to tool_shed.test by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18296 <https://github.com/galaxyproject/galaxy/pull/18296>`_

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

* Python 3.8 as minimum by `@mr-c <https://github.com/mr-c>`_ in `#16954 <https://github.com/galaxyproject/galaxy/pull/16954>`_
* Update to black 2024 stable style by `@nsoranzo <https://github.com/nsoranzo>`_ in `#17391 <https://github.com/galaxyproject/galaxy/pull/17391>`_
* Type annotation and refactoring of tests by `@nsoranzo <https://github.com/nsoranzo>`_ in `#17484 <https://github.com/galaxyproject/galaxy/pull/17484>`_

-------------------
23.2.1 (2024-02-21)
-------------------


=========
Bug fixes
=========

* Tool Shed 2.0 fixes by `@nsoranzo <https://github.com/nsoranzo>`_ in `#16825 <https://github.com/galaxyproject/galaxy/pull/16825>`_

============
Enhancements
============

* Limit number of celery task executions per second per user by `@claudiofr <https://github.com/claudiofr>`_ in `#16232 <https://github.com/galaxyproject/galaxy/pull/16232>`_
* Tweak tool memory use and optimize shared memory when using preload by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16536 <https://github.com/galaxyproject/galaxy/pull/16536>`_

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


=========
Bug fixes
=========

* Assert that ``DatasetCollectioElement`` has an associated object by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17071 <https://github.com/galaxyproject/galaxy/pull/17071>`_

-------------------
23.1.1 (2023-10-23)
-------------------


=========
Bug fixes
=========

* Backport tool mem fixes by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16601 <https://github.com/galaxyproject/galaxy/pull/16601>`_
* Fix allowlist deserialization in file sources by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16729 <https://github.com/galaxyproject/galaxy/pull/16729>`_

============
Enhancements
============

* Towards SQLAlchemy 2.0: drop session autocommit setting by `@jdavcs <https://github.com/jdavcs>`_ in `#15421 <https://github.com/galaxyproject/galaxy/pull/15421>`_
* Explore tool remote test data by `@davelopez <https://github.com/davelopez>`_ in `#15510 <https://github.com/galaxyproject/galaxy/pull/15510>`_
* Refactor integration tests to create utility for setting up a database vault. by `@jmchilton <https://github.com/jmchilton>`_ in `#16027 <https://github.com/galaxyproject/galaxy/pull/16027>`_
* Merge ``Target`` class with ``CondaTarget`` by `@nsoranzo <https://github.com/nsoranzo>`_ in `#16181 <https://github.com/galaxyproject/galaxy/pull/16181>`_
* Fix tool remote test data by `@davelopez <https://github.com/davelopez>`_ in `#16311 <https://github.com/galaxyproject/galaxy/pull/16311>`_

=============
Other changes
=============

* Implement some initial object store selection end-to-end tests. by `@jmchilton <https://github.com/jmchilton>`_ in `#15785 <https://github.com/galaxyproject/galaxy/pull/15785>`_

-------------------
23.0.6 (2023-10-23)
-------------------

No recorded changes since last release

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
20.9.0 (2020-10-15)
-------------------

* First release from the 20.09 branch of Galaxy.

-------------------
20.5.0 (2020-07-04)
-------------------

* First release from the 20.05 branch of Galaxy.
