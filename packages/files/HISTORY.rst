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


=========
Bug fixes
=========

* Invenio plugin fixes by `@davelopez <https://github.com/davelopez>`_ in `#17997 <https://github.com/galaxyproject/galaxy/pull/17997>`_

============
Enhancements
============

* Fix remote files sources error handling by `@davelopez <https://github.com/davelopez>`_ in `#18027 <https://github.com/galaxyproject/galaxy/pull/18027>`_

-------------------
24.0.0 (2024-04-02)
-------------------


============
Enhancements
============

* Add support for Python 3.12 by `@tuncK <https://github.com/tuncK>`_ in `#16796 <https://github.com/galaxyproject/galaxy/pull/16796>`_
* Python 3.8 as minimum by `@mr-c <https://github.com/mr-c>`_ in `#16954 <https://github.com/galaxyproject/galaxy/pull/16954>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#17235 <https://github.com/galaxyproject/galaxy/pull/17235>`_
* fix s3fs templating by `@bgruening <https://github.com/bgruening>`_ in `#17311 <https://github.com/galaxyproject/galaxy/pull/17311>`_
* Update to black 2024 stable style by `@nsoranzo <https://github.com/nsoranzo>`_ in `#17391 <https://github.com/galaxyproject/galaxy/pull/17391>`_

-------------------
23.2.1 (2024-02-21)
-------------------


=========
Bug fixes
=========

* pin fs.dropboxfs to >=1 by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#16451 <https://github.com/galaxyproject/galaxy/pull/16451>`_
* Write to a temp filename in posix file source plugin by `@natefoo <https://github.com/natefoo>`_ in `#17350 <https://github.com/galaxyproject/galaxy/pull/17350>`_
* Set webdav file source to use temp files by default by `@davelopez <https://github.com/davelopez>`_ in `#17388 <https://github.com/galaxyproject/galaxy/pull/17388>`_
* More defensive access of extra props in filesources by `@nuwang <https://github.com/nuwang>`_ in `#17445 <https://github.com/galaxyproject/galaxy/pull/17445>`_

============
Enhancements
============

* Add Invenio RDM repository integration by `@davelopez <https://github.com/davelopez>`_ in `#16381 <https://github.com/galaxyproject/galaxy/pull/16381>`_
* Refactor FilesDialog + Remote Files API schema improvements by `@davelopez <https://github.com/davelopez>`_ in `#16420 <https://github.com/galaxyproject/galaxy/pull/16420>`_
* Use fs.onedatarestfs for Onedata files source plugin implementation by `@lopiola <https://github.com/lopiola>`_ in `#16690 <https://github.com/galaxyproject/galaxy/pull/16690>`_
* Remove record access handling for Invenio RDM plugin by `@davelopez <https://github.com/davelopez>`_ in `#16900 <https://github.com/galaxyproject/galaxy/pull/16900>`_
* Enhance Invenio RDM integration by `@davelopez <https://github.com/davelopez>`_ in `#16964 <https://github.com/galaxyproject/galaxy/pull/16964>`_

-------------------
23.1.4 (2024-01-04)
-------------------


=========
Bug fixes
=========

* Separate collection and non-collection data element by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17236 <https://github.com/galaxyproject/galaxy/pull/17236>`_

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

* Implement missing upload for S3 file sources by `@davelopez <https://github.com/davelopez>`_ in `#17100 <https://github.com/galaxyproject/galaxy/pull/17100>`_

-------------------
23.1.1 (2023-10-23)
-------------------


=========
Bug fixes
=========

* Fix some drs handling issues by `@nuwang <https://github.com/nuwang>`_ in `#15777 <https://github.com/galaxyproject/galaxy/pull/15777>`_
* Fix filesource file url support by `@nuwang <https://github.com/nuwang>`_ in `#15794 <https://github.com/galaxyproject/galaxy/pull/15794>`_
* Fix unittest mocks to support us checking geturl()  by `@dannon <https://github.com/dannon>`_ in `#16726 <https://github.com/galaxyproject/galaxy/pull/16726>`_
* Fix allowlist deserialization in file sources by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16729 <https://github.com/galaxyproject/galaxy/pull/16729>`_

============
Enhancements
============

* Unify url handling with filesources by `@nuwang <https://github.com/nuwang>`_ in `#15497 <https://github.com/galaxyproject/galaxy/pull/15497>`_

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


=========
Bug fixes
=========

* Fix dropbox import to support newer versions by `@nuwang <https://github.com/nuwang>`_ in `#16239 <https://github.com/galaxyproject/galaxy/pull/16239>`_

-------------------
23.0.1 (2023-06-08)
-------------------

No recorded changes since last release

-------------------
22.1.1 (2022-08-22)
-------------------

* Initial standalone release of this package.
