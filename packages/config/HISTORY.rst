History
-------

.. to_doc

-------------------
23.1.2 (2023-11-29)
-------------------


=========
Bug fixes
=========

* Prevent Singular external auth users from disconnecting identity by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#16961 <https://github.com/galaxyproject/galaxy/pull/16961>`_
* Set correct tool_path for packaged galaxy by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17102 <https://github.com/galaxyproject/galaxy/pull/17102>`_

============
Enhancements
============

* Add support for larch datatypes by `@patrick-austin <https://github.com/patrick-austin>`_ in `#17080 <https://github.com/galaxyproject/galaxy/pull/17080>`_

-------------------
23.1.1 (2023-10-23)
-------------------


=========
Bug fixes
=========

* Fix some drs handling issues by `@nuwang <https://github.com/nuwang>`_ in `#15777 <https://github.com/galaxyproject/galaxy/pull/15777>`_
* Improve container resolver documentation by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16280 <https://github.com/galaxyproject/galaxy/pull/16280>`_
* Limit tool document cache to tool configs with explicit cache path by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16537 <https://github.com/galaxyproject/galaxy/pull/16537>`_
* Backport tool mem fixes by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16601 <https://github.com/galaxyproject/galaxy/pull/16601>`_
* Fix allowlist deserialization in file sources by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16729 <https://github.com/galaxyproject/galaxy/pull/16729>`_

============
Enhancements
============

* External Login Flow: Redirect users if account already exists by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#15019 <https://github.com/galaxyproject/galaxy/pull/15019>`_
* Add slack error reporting plugin by `@hexylena <https://github.com/hexylena>`_ in `#15025 <https://github.com/galaxyproject/galaxy/pull/15025>`_
* Documents use of k8s_extra_job_envs in job_conf sample advanced by `@pcm32 <https://github.com/pcm32>`_ in `#15110 <https://github.com/galaxyproject/galaxy/pull/15110>`_
* Expose additional beaker caching backends  by `@claudiofr <https://github.com/claudiofr>`_ in `#15349 <https://github.com/galaxyproject/galaxy/pull/15349>`_
* Unify url handling with filesources by `@nuwang <https://github.com/nuwang>`_ in `#15497 <https://github.com/galaxyproject/galaxy/pull/15497>`_
* Handle "email_from" config option consistently, as per schema description by `@jdavcs <https://github.com/jdavcs>`_ in `#15557 <https://github.com/galaxyproject/galaxy/pull/15557>`_
* Drop workflow exports to myexperiment.org by `@dannon <https://github.com/dannon>`_ in `#15576 <https://github.com/galaxyproject/galaxy/pull/15576>`_
* Container resolvers: add docs, typing and tests by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#15614 <https://github.com/galaxyproject/galaxy/pull/15614>`_
* Add suggested Training material to Tool Form by `@ElectronicBlueberry <https://github.com/ElectronicBlueberry>`_ in `#15628 <https://github.com/galaxyproject/galaxy/pull/15628>`_
* Deprecate tools/evolution by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#15656 <https://github.com/galaxyproject/galaxy/pull/15656>`_
* Add Galaxy Notification System by `@davelopez <https://github.com/davelopez>`_ in `#15663 <https://github.com/galaxyproject/galaxy/pull/15663>`_
* More object store documentation. by `@jmchilton <https://github.com/jmchilton>`_ in `#15707 <https://github.com/galaxyproject/galaxy/pull/15707>`_
* Drop use_legacy_history from config  by `@dannon <https://github.com/dannon>`_ in `#15861 <https://github.com/galaxyproject/galaxy/pull/15861>`_
* FITS data format by `@volodymyrss <https://github.com/volodymyrss>`_ in `#15905 <https://github.com/galaxyproject/galaxy/pull/15905>`_
* Export tool citations configurable message by `@minh-biocommons <https://github.com/minh-biocommons>`_ in `#15998 <https://github.com/galaxyproject/galaxy/pull/15998>`_
* Rename object stores in config. by `@jmchilton <https://github.com/jmchilton>`_ in `#16029 <https://github.com/galaxyproject/galaxy/pull/16029>`_
* Add hdf4 datatype by `@TheoMathurin <https://github.com/TheoMathurin>`_ in `#16105 <https://github.com/galaxyproject/galaxy/pull/16105>`_
* Improved Cache Monitoring for Object Stores by `@jmchilton <https://github.com/jmchilton>`_ in `#16110 <https://github.com/galaxyproject/galaxy/pull/16110>`_
* Refactor caching object stores ahead of adding task-based store. by `@jmchilton <https://github.com/jmchilton>`_ in `#16144 <https://github.com/galaxyproject/galaxy/pull/16144>`_
* Add zipped mongodb and genenotebook datatypes by `@abretaud <https://github.com/abretaud>`_ in `#16173 <https://github.com/galaxyproject/galaxy/pull/16173>`_
* Add Visium datatype for squidpy and spatialomics tools by `@astrovsky01 <https://github.com/astrovsky01>`_ in `#16255 <https://github.com/galaxyproject/galaxy/pull/16255>`_

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


=========
Bug fixes
=========

* 
* Minor bug fix for default mail templates by `@neoformit <https://github.com/neoformit>`_ in `#16362 <https://github.com/galaxyproject/galaxy/pull/16362>`_

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

* 
* 
* 
* Change default watchdog inotify_buffer log level to info by `@mvdbeek <https://github.com/mvdbeek>`_ in `#15967 <https://github.com/galaxyproject/galaxy/pull/15967>`_

============
Enhancements
============

* 
* Add ``ca_certs`` option for sentry client by `@mvdbeek <https://github.com/mvdbeek>`_ in `#15943 <https://github.com/galaxyproject/galaxy/pull/15943>`_

-------------------
22.1.1 (2022-08-22)
-------------------

* Initial release
