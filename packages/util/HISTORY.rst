History
-------

.. to_doc

---------
24.2.dev0
---------



-------------------
24.1.2 (2024-09-25)
-------------------


=========
Bug fixes
=========

* Fix Archive header encoding by `@arash77 <https://github.com/arash77>`_ in `#18583 <https://github.com/galaxyproject/galaxy/pull/18583>`_
* File source and object store instance api fixes by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18685 <https://github.com/galaxyproject/galaxy/pull/18685>`_

============
Enhancements
============

* Use smtplib send_message to support utf-8 chars in to and from by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18805 <https://github.com/galaxyproject/galaxy/pull/18805>`_

-------------------
24.1.1 (2024-07-02)
-------------------


=========
Bug fixes
=========

* Fix bug in image_util.py by `@kostrykin <https://github.com/kostrykin>`_ in `#17749 <https://github.com/galaxyproject/galaxy/pull/17749>`_
* Revert some requests import changes by `@nsoranzo <https://github.com/nsoranzo>`_ in `#18199 <https://github.com/galaxyproject/galaxy/pull/18199>`_

============
Enhancements
============

* Better display of estimated line numbers and add number of columns for tabular by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#17492 <https://github.com/galaxyproject/galaxy/pull/17492>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#17653 <https://github.com/galaxyproject/galaxy/pull/17653>`_
* Code cleanups from ruff and pyupgrade by `@nsoranzo <https://github.com/nsoranzo>`_ in `#17654 <https://github.com/galaxyproject/galaxy/pull/17654>`_
* SQLAlchemy 2.0 by `@jdavcs <https://github.com/jdavcs>`_ in `#17778 <https://github.com/galaxyproject/galaxy/pull/17778>`_
* Error reporting unit tests by `@jmchilton <https://github.com/jmchilton>`_ in `#17968 <https://github.com/galaxyproject/galaxy/pull/17968>`_
* Enable ``warn_unused_ignores`` mypy option by `@nsoranzo <https://github.com/nsoranzo>`_ in `#17991 <https://github.com/galaxyproject/galaxy/pull/17991>`_
* Add galaxy to user agent by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18003 <https://github.com/galaxyproject/galaxy/pull/18003>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#18063 <https://github.com/galaxyproject/galaxy/pull/18063>`_
* Enable flake8-implicit-str-concat ruff rules by `@nsoranzo <https://github.com/nsoranzo>`_ in `#18067 <https://github.com/galaxyproject/galaxy/pull/18067>`_
* Overhaul Azure storage infrastructure. by `@jmchilton <https://github.com/jmchilton>`_ in `#18087 <https://github.com/galaxyproject/galaxy/pull/18087>`_
* Empower users to bring their own storage and file sources by `@jmchilton <https://github.com/jmchilton>`_ in `#18127 <https://github.com/galaxyproject/galaxy/pull/18127>`_
* Harden User Object Store and File Source Creation by `@jmchilton <https://github.com/jmchilton>`_ in `#18172 <https://github.com/galaxyproject/galaxy/pull/18172>`_

-------------------
24.0.3 (2024-06-28)
-------------------


=========
Bug fixes
=========

* Use config_section to distinguish between galaxy and ts or other apps by `@jdavcs <https://github.com/jdavcs>`_ in `#18215 <https://github.com/galaxyproject/galaxy/pull/18215>`_

-------------------
24.0.2 (2024-05-07)
-------------------


=========
Bug fixes
=========

* Adds logging of messageExceptions in the fastapi exception handler. by `@dannon <https://github.com/dannon>`_ in `#18041 <https://github.com/galaxyproject/galaxy/pull/18041>`_

-------------------
24.0.1 (2024-05-02)
-------------------


=========
Bug fixes
=========

* Fix conditional Image imports by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17899 <https://github.com/galaxyproject/galaxy/pull/17899>`_

-------------------
24.0.0 (2024-04-02)
-------------------


=========
Bug fixes
=========

* Optional Reply-to SMTP header in tool error reports by `@neoformit <https://github.com/neoformit>`_ in `#17243 <https://github.com/galaxyproject/galaxy/pull/17243>`_
* Follow-up on #17274 and #17262 by `@nsoranzo <https://github.com/nsoranzo>`_ in `#17302 <https://github.com/galaxyproject/galaxy/pull/17302>`_
* Fixes for flake8-bugbear 24.1.17 by `@nsoranzo <https://github.com/nsoranzo>`_ in `#17340 <https://github.com/galaxyproject/galaxy/pull/17340>`_

============
Enhancements
============

* Add support for Python 3.12 by `@tuncK <https://github.com/tuncK>`_ in `#16796 <https://github.com/galaxyproject/galaxy/pull/16796>`_
* Python 3.8 as minimum by `@mr-c <https://github.com/mr-c>`_ in `#16954 <https://github.com/galaxyproject/galaxy/pull/16954>`_
* Remove web framework dependency from tools by `@davelopez <https://github.com/davelopez>`_ in `#17058 <https://github.com/galaxyproject/galaxy/pull/17058>`_
* Add support for (fast5.tar).xz binary compressed files by `@tuncK <https://github.com/tuncK>`_ in `#17106 <https://github.com/galaxyproject/galaxy/pull/17106>`_
* Reuse test instance during non-integration tests by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17234 <https://github.com/galaxyproject/galaxy/pull/17234>`_
* Add OIDC backend configuration schema and validation by `@uwwint <https://github.com/uwwint>`_ in `#17274 <https://github.com/galaxyproject/galaxy/pull/17274>`_
* Enable ``warn_unreachable`` mypy option by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17365 <https://github.com/galaxyproject/galaxy/pull/17365>`_
* Fix type annotation of code using XML etree by `@nsoranzo <https://github.com/nsoranzo>`_ in `#17367 <https://github.com/galaxyproject/galaxy/pull/17367>`_
* Update to black 2024 stable style by `@nsoranzo <https://github.com/nsoranzo>`_ in `#17391 <https://github.com/galaxyproject/galaxy/pull/17391>`_
* Add `image_diff` comparison method for test output verification using images by `@kostrykin <https://github.com/kostrykin>`_ in `#17556 <https://github.com/galaxyproject/galaxy/pull/17556>`_

-------------------
23.2.1 (2024-02-21)
-------------------


=========
Bug fixes
=========

* Ruff and flake8 fixes by `@nsoranzo <https://github.com/nsoranzo>`_ in `#16884 <https://github.com/galaxyproject/galaxy/pull/16884>`_

============
Enhancements
============

* Tool Shed 2.0 by `@jmchilton <https://github.com/jmchilton>`_ in `#15639 <https://github.com/galaxyproject/galaxy/pull/15639>`_
* Move database access code out of ``galaxy.util`` by `@jdavcs <https://github.com/jdavcs>`_ in `#16526 <https://github.com/galaxyproject/galaxy/pull/16526>`_
* Tweak tool memory use and optimize shared memory when using preload by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16536 <https://github.com/galaxyproject/galaxy/pull/16536>`_
* Updated path-based interactive tools with entry point path injection, support for ITs with relative links, shortened URLs, doc and config updates including Podman job_conf by `@sveinugu <https://github.com/sveinugu>`_ in `#16795 <https://github.com/galaxyproject/galaxy/pull/16795>`_
* Allow partial matches in workflow name tag search and search all tags for unquoted query by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#16860 <https://github.com/galaxyproject/galaxy/pull/16860>`_
* Use python-isal for fast zip deflate compression in rocrate export by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17342 <https://github.com/galaxyproject/galaxy/pull/17342>`_

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


============
Enhancements
============

* Improve invocation error reporting by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16917 <https://github.com/galaxyproject/galaxy/pull/16917>`_

-------------------
23.1.1 (2023-10-23)
-------------------


=========
Bug fixes
=========

* Fix bad auto-merge of dev. by `@jmchilton <https://github.com/jmchilton>`_ in `#15386 <https://github.com/galaxyproject/galaxy/pull/15386>`_
* Fix some drs handling issues by `@nuwang <https://github.com/nuwang>`_ in `#15777 <https://github.com/galaxyproject/galaxy/pull/15777>`_
* Enable ``strict_equality`` mypy option by `@nsoranzo <https://github.com/nsoranzo>`_ in `#15808 <https://github.com/galaxyproject/galaxy/pull/15808>`_
* Ensure session is request-scoped for legacy endpoints by `@jdavcs <https://github.com/jdavcs>`_ in `#16207 <https://github.com/galaxyproject/galaxy/pull/16207>`_
* Fix form builder value handling by `@guerler <https://github.com/guerler>`_ in `#16304 <https://github.com/galaxyproject/galaxy/pull/16304>`_
* Backport tool mem fixes by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16601 <https://github.com/galaxyproject/galaxy/pull/16601>`_
* Workaround for XML nodes of job resource parameters losing their children by `@kysrpex <https://github.com/kysrpex>`_ in `#16728 <https://github.com/galaxyproject/galaxy/pull/16728>`_
* Fix allowlist deserialization in file sources by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16729 <https://github.com/galaxyproject/galaxy/pull/16729>`_
* Exclude on_opened and on_closed from watcher events by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16850 <https://github.com/galaxyproject/galaxy/pull/16850>`_

============
Enhancements
============

* Various Tool Shed Cleanup by `@jmchilton <https://github.com/jmchilton>`_ in `#15247 <https://github.com/galaxyproject/galaxy/pull/15247>`_
* Protection against problematic boolean parameters. by `@jmchilton <https://github.com/jmchilton>`_ in `#15493 <https://github.com/galaxyproject/galaxy/pull/15493>`_
* Unify url handling with filesources by `@nuwang <https://github.com/nuwang>`_ in `#15497 <https://github.com/galaxyproject/galaxy/pull/15497>`_
* Explore tool remote test data by `@davelopez <https://github.com/davelopez>`_ in `#15510 <https://github.com/galaxyproject/galaxy/pull/15510>`_
* Drop database views by `@jdavcs <https://github.com/jdavcs>`_ in `#15876 <https://github.com/galaxyproject/galaxy/pull/15876>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#15890 <https://github.com/galaxyproject/galaxy/pull/15890>`_
* Record input datasets and collections at full parameter path by `@mvdbeek <https://github.com/mvdbeek>`_ in `#15978 <https://github.com/galaxyproject/galaxy/pull/15978>`_
* Code cleanups from ruff and pyupgrade by `@nsoranzo <https://github.com/nsoranzo>`_ in `#16035 <https://github.com/galaxyproject/galaxy/pull/16035>`_
* Vendorise ``packaging.versions.LegacyVersion`` by `@nsoranzo <https://github.com/nsoranzo>`_ in `#16058 <https://github.com/galaxyproject/galaxy/pull/16058>`_
* Improve histories and datasets immutability checks by `@davelopez <https://github.com/davelopez>`_ in `#16143 <https://github.com/galaxyproject/galaxy/pull/16143>`_
* Merge ``Target`` class with ``CondaTarget`` by `@nsoranzo <https://github.com/nsoranzo>`_ in `#16181 <https://github.com/galaxyproject/galaxy/pull/16181>`_

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


=========
Bug fixes
=========

* Replace httpbin service with pytest-httpserver by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16042 <https://github.com/galaxyproject/galaxy/pull/16042>`_

-------------------
22.1.2 (2022-12-08)
-------------------

* Pin packaging dependency to < 22, fixes ``LegacyVersion`` import errors
* Add missing pyparsing dependency

-------------------
22.1.1 (2022-08-22)
-------------------

* First release from the 22.01 branch of Galaxy

-------------------
21.1.0 (2021-03-19)
-------------------

* First release from the 21.01 branch of Galaxy.

-------------------
20.9.1 (2020-10-28)
-------------------



-------------------
20.9.0 (2020-10-15)
-------------------

* First release from the 20.09 branch of Galaxy.

-------------------
20.5.0 (2020-07-03)
-------------------

* First release from 20.05 branch of Galaxy.

-------------------
19.9.0 (2019-11-21)
-------------------

* Initial import from dev branch of Galaxy during 19.09 development cycle.
