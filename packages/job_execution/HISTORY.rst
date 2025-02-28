History
-------

.. to_doc

---------
25.0.dev0
---------



-------------------
24.2.1 (2025-02-28)
-------------------

No recorded changes since last release

-------------------
24.2.0 (2025-02-11)
-------------------


=========
Bug fixes
=========

* Fixes for errors reported by mypy 1.11.0 by `@nsoranzo <https://github.com/nsoranzo>`_ in `#18608 <https://github.com/galaxyproject/galaxy/pull/18608>`_

-------------------
24.1.4 (2024-12-11)
-------------------


=========
Bug fixes
=========

* Add input extra files to `get_input_fnames` by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18462 <https://github.com/galaxyproject/galaxy/pull/18462>`_
* Retry container monitor POST if it fails (don't assume it succeeded) by `@natefoo <https://github.com/natefoo>`_ in `#18863 <https://github.com/galaxyproject/galaxy/pull/18863>`_

-------------------
24.1.3 (2024-10-25)
-------------------


=========
Bug fixes
=========

* Add input extra files to `get_input_fnames` by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18462 <https://github.com/galaxyproject/galaxy/pull/18462>`_
* Retry container monitor POST if it fails (don't assume it succeeded) by `@natefoo <https://github.com/natefoo>`_ in `#18863 <https://github.com/galaxyproject/galaxy/pull/18863>`_

-------------------
24.1.2 (2024-09-25)
-------------------


=========
Bug fixes
=========

* Retry container monitor POST if it fails (don't assume it succeeded) by `@natefoo <https://github.com/natefoo>`_ in `#18863 <https://github.com/galaxyproject/galaxy/pull/18863>`_

-------------------
24.1.1 (2024-07-02)
-------------------


=========
Bug fixes
=========

* Add input extra files to `get_input_fnames` by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18462 <https://github.com/galaxyproject/galaxy/pull/18462>`_

============
Enhancements
============

* Enable ``warn_unused_ignores`` mypy option by `@nsoranzo <https://github.com/nsoranzo>`_ in `#17991 <https://github.com/galaxyproject/galaxy/pull/17991>`_
* Add galaxy to user agent by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18003 <https://github.com/galaxyproject/galaxy/pull/18003>`_
* Refactor galaxy.files plugin loading + config handling. by `@jmchilton <https://github.com/jmchilton>`_ in `#18049 <https://github.com/galaxyproject/galaxy/pull/18049>`_
* Add stronger type annotations in file sources + refactoring by `@davelopez <https://github.com/davelopez>`_ in `#18050 <https://github.com/galaxyproject/galaxy/pull/18050>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#18063 <https://github.com/galaxyproject/galaxy/pull/18063>`_

-------------------
24.0.3 (2024-06-28)
-------------------


=========
Bug fixes
=========

* Include traceback when logging email PJA exception by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18122 <https://github.com/galaxyproject/galaxy/pull/18122>`_
* Don't commit in ``DeleteIntermediatesAction`` by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18131 <https://github.com/galaxyproject/galaxy/pull/18131>`_
* Don't fail metadata if we only have an extra output files dir by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18179 <https://github.com/galaxyproject/galaxy/pull/18179>`_
* Don't set dataset peek for errored jobs by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18231 <https://github.com/galaxyproject/galaxy/pull/18231>`_
* Do not copy purged outputs to object store by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18342 <https://github.com/galaxyproject/galaxy/pull/18342>`_

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


=========
Bug fixes
=========

* Fixes for output discovery by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#17266 <https://github.com/galaxyproject/galaxy/pull/17266>`_
* Fix change_datatype PJA for dynamic collections  by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17803 <https://github.com/galaxyproject/galaxy/pull/17803>`_

============
Enhancements
============

* Python 3.8 as minimum by `@mr-c <https://github.com/mr-c>`_ in `#16954 <https://github.com/galaxyproject/galaxy/pull/16954>`_
* Extend regex groups in stdio regex matches by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#17016 <https://github.com/galaxyproject/galaxy/pull/17016>`_
* Update to black 2024 stable style by `@nsoranzo <https://github.com/nsoranzo>`_ in `#17391 <https://github.com/galaxyproject/galaxy/pull/17391>`_

-------------------
23.2.1 (2024-02-21)
-------------------


============
Enhancements
============

* Replace file_name property with get_file_name function by `@SergeyYakubov <https://github.com/SergeyYakubov>`_ in `#16783 <https://github.com/galaxyproject/galaxy/pull/16783>`_
* Enable some flake8-logging-format rules in ruff by `@nsoranzo <https://github.com/nsoranzo>`_ in `#16915 <https://github.com/galaxyproject/galaxy/pull/16915>`_
* Move and re-use persist_extra_files by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16955 <https://github.com/galaxyproject/galaxy/pull/16955>`_
* optimize object store cache operations by `@SergeyYakubov <https://github.com/SergeyYakubov>`_ in `#17025 <https://github.com/galaxyproject/galaxy/pull/17025>`_

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

* Fix library import from path linking files by `@davelopez <https://github.com/davelopez>`_ in `#16919 <https://github.com/galaxyproject/galaxy/pull/16919>`_
* Don't store job in JobIO instance attributes by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16965 <https://github.com/galaxyproject/galaxy/pull/16965>`_
* Fix extra files collection if using ``store_by="id"`` and `outputs_to_working_directory` by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17067 <https://github.com/galaxyproject/galaxy/pull/17067>`_

-------------------
23.1.1 (2023-10-23)
-------------------


=========
Bug fixes
=========

* Fix tags ownership by `@davelopez <https://github.com/davelopez>`_ in `#16339 <https://github.com/galaxyproject/galaxy/pull/16339>`_
* Push to object store even if ``set_meta`` fails by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16667 <https://github.com/galaxyproject/galaxy/pull/16667>`_
* Fix metadata setting in extended metadata + outputs_to_working_directory mode by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16678 <https://github.com/galaxyproject/galaxy/pull/16678>`_
* Fix ItemOwnerShipException in tag removal by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16773 <https://github.com/galaxyproject/galaxy/pull/16773>`_
* Fix and prevent persisting null file_size by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16855 <https://github.com/galaxyproject/galaxy/pull/16855>`_

============
Enhancements
============

* Empower Users to Select Storage Destination by `@jmchilton <https://github.com/jmchilton>`_ in `#14073 <https://github.com/galaxyproject/galaxy/pull/14073>`_
* Towards SQLAlchemy 2.0: drop session autocommit setting by `@jdavcs <https://github.com/jdavcs>`_ in `#15421 <https://github.com/galaxyproject/galaxy/pull/15421>`_
* Unify url handling with filesources by `@nuwang <https://github.com/nuwang>`_ in `#15497 <https://github.com/galaxyproject/galaxy/pull/15497>`_
* Handle "email_from" config option consistently, as per schema description by `@jdavcs <https://github.com/jdavcs>`_ in `#15557 <https://github.com/galaxyproject/galaxy/pull/15557>`_
* Record input datasets and collections at full parameter path by `@mvdbeek <https://github.com/mvdbeek>`_ in `#15978 <https://github.com/galaxyproject/galaxy/pull/15978>`_
* Code cleanups from ruff and pyupgrade by `@nsoranzo <https://github.com/nsoranzo>`_ in `#16035 <https://github.com/galaxyproject/galaxy/pull/16035>`_
* Improved Cache Monitoring for Object Stores by `@jmchilton <https://github.com/jmchilton>`_ in `#16110 <https://github.com/galaxyproject/galaxy/pull/16110>`_
* Remove various fallback behaviors by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16199 <https://github.com/galaxyproject/galaxy/pull/16199>`_

-------------------
23.0.6 (2023-10-23)
-------------------


=========
Bug fixes
=========

* Fix extra files path handling by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16541 <https://github.com/galaxyproject/galaxy/pull/16541>`_
* Make sure job_wrapper uses a consistent metadata strategy by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16569 <https://github.com/galaxyproject/galaxy/pull/16569>`_
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
20.9.0 (2020-10-15)
-------------------

* First release from the 20.09 branch of Galaxy.

-------------------
20.5.0 (2020-07-04)
-------------------

* First release from the 20.05 branch of Galaxy.
