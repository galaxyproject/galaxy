History
-------

.. to_doc

-----------
24.2.1.dev0
-----------



-------------------
24.2.0 (2025-02-11)
-------------------


============
Enhancements
============

* Allow OAuth 2.0 user defined file sources (w/Dropbox integration) by `@jmchilton <https://github.com/jmchilton>`_ in `#18272 <https://github.com/galaxyproject/galaxy/pull/18272>`_
* Add onedata templates by `@bwalkowi <https://github.com/bwalkowi>`_ in `#18457 <https://github.com/galaxyproject/galaxy/pull/18457>`_
* Add missing version in the file sources and object store templates by `@sanjaysrikakulam <https://github.com/sanjaysrikakulam>`_ in `#18497 <https://github.com/galaxyproject/galaxy/pull/18497>`_
* Add a new version of the production s3fs file source template with the writable configuration variable added by `@sanjaysrikakulam <https://github.com/sanjaysrikakulam>`_ in `#18575 <https://github.com/galaxyproject/galaxy/pull/18575>`_
* Bring your own file sources: Add the WebDAV template and configuration by `@sanjaysrikakulam <https://github.com/sanjaysrikakulam>`_ in `#18598 <https://github.com/galaxyproject/galaxy/pull/18598>`_
* Allow setting a few global defaults for file source plugin types. by `@jmchilton <https://github.com/jmchilton>`_ in `#18909 <https://github.com/galaxyproject/galaxy/pull/18909>`_
* Type annotations and fixes by `@nsoranzo <https://github.com/nsoranzo>`_ in `#18911 <https://github.com/galaxyproject/galaxy/pull/18911>`_
* Allow a posix file source to prefer linking. by `@jmchilton <https://github.com/jmchilton>`_ in `#19132 <https://github.com/galaxyproject/galaxy/pull/19132>`_

-------------------
24.1.4 (2024-12-11)
-------------------


=========
Bug fixes
=========

* Fix production_aws_private_bucket.yml by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19155 <https://github.com/galaxyproject/galaxy/pull/19155>`_

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


=========
Bug fixes
=========

* Fix file source search query with empty string value by `@davelopez <https://github.com/davelopez>`_ in `#18191 <https://github.com/galaxyproject/galaxy/pull/18191>`_
* Small bug fixes for user data plugins by `@jmchilton <https://github.com/jmchilton>`_ in `#18246 <https://github.com/galaxyproject/galaxy/pull/18246>`_
* Fix check for anonymous by `@jdavcs <https://github.com/jdavcs>`_ in `#18364 <https://github.com/galaxyproject/galaxy/pull/18364>`_

============
Enhancements
============

* Add onedata objectstore by `@bwalkowi <https://github.com/bwalkowi>`_ in `#17540 <https://github.com/galaxyproject/galaxy/pull/17540>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#17653 <https://github.com/galaxyproject/galaxy/pull/17653>`_
* Code cleanups from ruff and pyupgrade by `@nsoranzo <https://github.com/nsoranzo>`_ in `#17654 <https://github.com/galaxyproject/galaxy/pull/17654>`_
* Enable ``warn_unused_ignores`` mypy option by `@nsoranzo <https://github.com/nsoranzo>`_ in `#17991 <https://github.com/galaxyproject/galaxy/pull/17991>`_
* Add galaxy to user agent by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18003 <https://github.com/galaxyproject/galaxy/pull/18003>`_
* Add Zenodo integration by `@davelopez <https://github.com/davelopez>`_ in `#18022 <https://github.com/galaxyproject/galaxy/pull/18022>`_
* More typing in galaxy.files. by `@jmchilton <https://github.com/jmchilton>`_ in `#18037 <https://github.com/galaxyproject/galaxy/pull/18037>`_
* Refactor galaxy.files plugin loading + config handling. by `@jmchilton <https://github.com/jmchilton>`_ in `#18049 <https://github.com/galaxyproject/galaxy/pull/18049>`_
* Add stronger type annotations in file sources + refactoring by `@davelopez <https://github.com/davelopez>`_ in `#18050 <https://github.com/galaxyproject/galaxy/pull/18050>`_
* Add pagination support to Files Source plugins by `@davelopez <https://github.com/davelopez>`_ in `#18059 <https://github.com/galaxyproject/galaxy/pull/18059>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#18063 <https://github.com/galaxyproject/galaxy/pull/18063>`_
* Overhaul Azure storage infrastructure. by `@jmchilton <https://github.com/jmchilton>`_ in `#18087 <https://github.com/galaxyproject/galaxy/pull/18087>`_
* Empower users to bring their own storage and file sources by `@jmchilton <https://github.com/jmchilton>`_ in `#18127 <https://github.com/galaxyproject/galaxy/pull/18127>`_
* Display DOIs in Archived Histories by `@davelopez <https://github.com/davelopez>`_ in `#18134 <https://github.com/galaxyproject/galaxy/pull/18134>`_
* Update s3fs dependency. by `@jmchilton <https://github.com/jmchilton>`_ in `#18135 <https://github.com/galaxyproject/galaxy/pull/18135>`_
* Onedada object store and files source stability fixes by `@bwalkowi <https://github.com/bwalkowi>`_ in `#18372 <https://github.com/galaxyproject/galaxy/pull/18372>`_

=============
Other changes
=============

* Fix #18316 (anonymous file sources) by `@jmchilton <https://github.com/jmchilton>`_ in `#18352 <https://github.com/galaxyproject/galaxy/pull/18352>`_

-------------------
24.0.3 (2024-06-28)
-------------------


=========
Bug fixes
=========

* Fix listing possibly untitled records in Invenio Plugin by `@davelopez <https://github.com/davelopez>`_ in `#18130 <https://github.com/galaxyproject/galaxy/pull/18130>`_
* Raise ``RequestParameterInvalidException`` when url is invalid by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18155 <https://github.com/galaxyproject/galaxy/pull/18155>`_
* Fix error message when accessing restricted Zenodo records by `@davelopez <https://github.com/davelopez>`_ in `#18169 <https://github.com/galaxyproject/galaxy/pull/18169>`_
* Raise ``RequestParameterInvalidException`` if url can't be verified by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18230 <https://github.com/galaxyproject/galaxy/pull/18230>`_
* Fix Invenio credentials handling by `@davelopez <https://github.com/davelopez>`_ in `#18255 <https://github.com/galaxyproject/galaxy/pull/18255>`_

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
