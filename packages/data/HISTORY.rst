History
-------

.. to_doc

-------------------
23.1.2 (2023-11-29)
-------------------


=========
Bug fixes
=========

* Skip change_datatype things if we're not actually changing the extension by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16931 <https://github.com/galaxyproject/galaxy/pull/16931>`_
* Fix copying metadata to copied job outputs by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17007 <https://github.com/galaxyproject/galaxy/pull/17007>`_
* Update tar_to_directory dependency by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17009 <https://github.com/galaxyproject/galaxy/pull/17009>`_
* Assert that ``DatasetCollectioElement`` has an associated object by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17071 <https://github.com/galaxyproject/galaxy/pull/17071>`_
* Fix input dates in notifications: consider timezone offset by `@davelopez <https://github.com/davelopez>`_ in `#17088 <https://github.com/galaxyproject/galaxy/pull/17088>`_
* Allow relative URLs in broadcasts action links by `@davelopez <https://github.com/davelopez>`_ in `#17093 <https://github.com/galaxyproject/galaxy/pull/17093>`_

============
Enhancements
============

* Improve invocation error reporting by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16917 <https://github.com/galaxyproject/galaxy/pull/16917>`_
* Add support for larch datatypes by `@patrick-austin <https://github.com/patrick-austin>`_ in `#17080 <https://github.com/galaxyproject/galaxy/pull/17080>`_

-------------------
23.1.1 (2023-10-23)
-------------------


=========
Bug fixes
=========

* Fix bad auto-merge of dev. by `@jmchilton <https://github.com/jmchilton>`_ in `#15386 <https://github.com/galaxyproject/galaxy/pull/15386>`_
* Merge conflicting db migration branches into one by `@jdavcs <https://github.com/jdavcs>`_ in `#15771 <https://github.com/galaxyproject/galaxy/pull/15771>`_
* Enable ``strict_equality`` mypy option by `@nsoranzo <https://github.com/nsoranzo>`_ in `#15808 <https://github.com/galaxyproject/galaxy/pull/15808>`_
* Fix revision scripts, run migrations in CI, add repair option, improve migrations utils by `@jdavcs <https://github.com/jdavcs>`_ in `#15811 <https://github.com/galaxyproject/galaxy/pull/15811>`_
* Fix anonymous user uploads when vault is configured by `@tchaussepiedifb <https://github.com/tchaussepiedifb>`_ in `#15858 <https://github.com/galaxyproject/galaxy/pull/15858>`_
* Fix nullable deleted column in API Keys table by `@davelopez <https://github.com/davelopez>`_ in `#15956 <https://github.com/galaxyproject/galaxy/pull/15956>`_
* Attempt to fix mypy check by `@davelopez <https://github.com/davelopez>`_ in `#16103 <https://github.com/galaxyproject/galaxy/pull/16103>`_
* Ensure session is request-scoped for legacy endpoints by `@jdavcs <https://github.com/jdavcs>`_ in `#16207 <https://github.com/galaxyproject/galaxy/pull/16207>`_
* Reset autocommit to True (temporarily) by `@jdavcs <https://github.com/jdavcs>`_ in `#16283 <https://github.com/galaxyproject/galaxy/pull/16283>`_
* Update 23.1 release tags for migration scripts by `@jdavcs <https://github.com/jdavcs>`_ in `#16294 <https://github.com/galaxyproject/galaxy/pull/16294>`_
* Fix form builder value handling by `@guerler <https://github.com/guerler>`_ in `#16304 <https://github.com/galaxyproject/galaxy/pull/16304>`_
* Fix tags ownership by `@davelopez <https://github.com/davelopez>`_ in `#16339 <https://github.com/galaxyproject/galaxy/pull/16339>`_
* Fix disk usage recalculation for distributed object stores by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16380 <https://github.com/galaxyproject/galaxy/pull/16380>`_
* Job cache fixes for DCEs by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16384 <https://github.com/galaxyproject/galaxy/pull/16384>`_
* Fix histories count by `@davelopez <https://github.com/davelopez>`_ in `#16400 <https://github.com/galaxyproject/galaxy/pull/16400>`_
* Fix double-encoding notification content by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16530 <https://github.com/galaxyproject/galaxy/pull/16530>`_
* Optimize getting current user session by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16604 <https://github.com/galaxyproject/galaxy/pull/16604>`_
* Fixes for conditional subworkflow steps by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16632 <https://github.com/galaxyproject/galaxy/pull/16632>`_
* Copy the collection contents by default when copying a collection by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16717 <https://github.com/galaxyproject/galaxy/pull/16717>`_
* Fix allowlist deserialization in file sources by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16729 <https://github.com/galaxyproject/galaxy/pull/16729>`_
* Fix workflow output display without label by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16749 <https://github.com/galaxyproject/galaxy/pull/16749>`_
* Fix and prevent persisting null file_size by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16855 <https://github.com/galaxyproject/galaxy/pull/16855>`_
* Fix workflow import losing tool_version by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16869 <https://github.com/galaxyproject/galaxy/pull/16869>`_
* Remove more flushes in database operation tools by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16875 <https://github.com/galaxyproject/galaxy/pull/16875>`_
* Fix join condition for nested collection query by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16880 <https://github.com/galaxyproject/galaxy/pull/16880>`_

============
Enhancements
============

* Empower Users to Select Storage Destination by `@jmchilton <https://github.com/jmchilton>`_ in `#14073 <https://github.com/galaxyproject/galaxy/pull/14073>`_
* Add Storage Dashboard visualizations for histories by `@davelopez <https://github.com/davelopez>`_ in `#14820 <https://github.com/galaxyproject/galaxy/pull/14820>`_
* Towards decoupling datatypes and model by `@jdavcs <https://github.com/jdavcs>`_ in `#15186 <https://github.com/galaxyproject/galaxy/pull/15186>`_
* Add Storage Management API by `@davelopez <https://github.com/davelopez>`_ in `#15295 <https://github.com/galaxyproject/galaxy/pull/15295>`_
* OIDC tokens by `@SergeyYakubov <https://github.com/SergeyYakubov>`_ in `#15300 <https://github.com/galaxyproject/galaxy/pull/15300>`_
* Expose additional beaker caching backends  by `@claudiofr <https://github.com/claudiofr>`_ in `#15349 <https://github.com/galaxyproject/galaxy/pull/15349>`_
* Follow up to #15186 by `@jdavcs <https://github.com/jdavcs>`_ in `#15388 <https://github.com/galaxyproject/galaxy/pull/15388>`_
* Add support for visualizing HDF5 datasets. by `@jarrah42 <https://github.com/jarrah42>`_ in `#15394 <https://github.com/galaxyproject/galaxy/pull/15394>`_
* Towards SQLAlchemy 2.0: drop session autocommit setting by `@jdavcs <https://github.com/jdavcs>`_ in `#15421 <https://github.com/galaxyproject/galaxy/pull/15421>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#15435 <https://github.com/galaxyproject/galaxy/pull/15435>`_
* Unify url handling with filesources by `@nuwang <https://github.com/nuwang>`_ in `#15497 <https://github.com/galaxyproject/galaxy/pull/15497>`_
* Move TS to Alembic by `@jdavcs <https://github.com/jdavcs>`_ in `#15509 <https://github.com/galaxyproject/galaxy/pull/15509>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#15564 <https://github.com/galaxyproject/galaxy/pull/15564>`_
* Update database_heartbeat for SA 2.0 compatibility by `@jdavcs <https://github.com/jdavcs>`_ in `#15611 <https://github.com/galaxyproject/galaxy/pull/15611>`_
* Update supports_skip_locked, supports_returning for SA 2.0 compatibility by `@jdavcs <https://github.com/jdavcs>`_ in `#15633 <https://github.com/galaxyproject/galaxy/pull/15633>`_
* Add Galaxy Notification System by `@davelopez <https://github.com/davelopez>`_ in `#15663 <https://github.com/galaxyproject/galaxy/pull/15663>`_
* Drop model mapping unit tests by `@jdavcs <https://github.com/jdavcs>`_ in `#15669 <https://github.com/galaxyproject/galaxy/pull/15669>`_
* Add transactional state to workflow scheduling manager by `@jdavcs <https://github.com/jdavcs>`_ in `#15683 <https://github.com/galaxyproject/galaxy/pull/15683>`_
* Remove DELETED_NEW job state from code base by `@jdavcs <https://github.com/jdavcs>`_ in `#15690 <https://github.com/galaxyproject/galaxy/pull/15690>`_
* Fix/Enhance recalculate disk usage API endpoint by `@davelopez <https://github.com/davelopez>`_ in `#15739 <https://github.com/galaxyproject/galaxy/pull/15739>`_
* Drop database views by `@jdavcs <https://github.com/jdavcs>`_ in `#15876 <https://github.com/galaxyproject/galaxy/pull/15876>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#15890 <https://github.com/galaxyproject/galaxy/pull/15890>`_
* FITS data format by `@volodymyrss <https://github.com/volodymyrss>`_ in `#15905 <https://github.com/galaxyproject/galaxy/pull/15905>`_
* Improve display chunk generation for BAMs by `@wm75 <https://github.com/wm75>`_ in `#15972 <https://github.com/galaxyproject/galaxy/pull/15972>`_
* Add History Archival feature by `@davelopez <https://github.com/davelopez>`_ in `#16003 <https://github.com/galaxyproject/galaxy/pull/16003>`_
* Add alter_column migration utility by `@jdavcs <https://github.com/jdavcs>`_ in `#16009 <https://github.com/galaxyproject/galaxy/pull/16009>`_
* Code cleanups from ruff and pyupgrade by `@nsoranzo <https://github.com/nsoranzo>`_ in `#16035 <https://github.com/galaxyproject/galaxy/pull/16035>`_
* Add missing fields to HistorySummary schema model by `@davelopez <https://github.com/davelopez>`_ in `#16041 <https://github.com/galaxyproject/galaxy/pull/16041>`_
* Dataset chunking tests (and small fixes) by `@jmchilton <https://github.com/jmchilton>`_ in `#16069 <https://github.com/galaxyproject/galaxy/pull/16069>`_
* Add create_foreign_key migration utility by `@jdavcs <https://github.com/jdavcs>`_ in `#16077 <https://github.com/galaxyproject/galaxy/pull/16077>`_
* Refactor models enums to eliminate schema dependency on model layer. by `@jmchilton <https://github.com/jmchilton>`_ in `#16080 <https://github.com/galaxyproject/galaxy/pull/16080>`_
* Use automated naming convention to generate indexes and constraints in database by `@jdavcs <https://github.com/jdavcs>`_ in `#16089 <https://github.com/galaxyproject/galaxy/pull/16089>`_
* Add zipped mongodb and genenotebook datatypes by `@abretaud <https://github.com/abretaud>`_ in `#16173 <https://github.com/galaxyproject/galaxy/pull/16173>`_
* Drop workarounds for old ro-crate-py and docutils versions by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16198 <https://github.com/galaxyproject/galaxy/pull/16198>`_
* bring grids for (published) pages on par with workflows by `@martenson <https://github.com/martenson>`_ in `#16209 <https://github.com/galaxyproject/galaxy/pull/16209>`_
* Add Visium datatype for squidpy and spatialomics tools by `@astrovsky01 <https://github.com/astrovsky01>`_ in `#16255 <https://github.com/galaxyproject/galaxy/pull/16255>`_
* Filter deleted keys from api_keys relationship by `@dannon <https://github.com/dannon>`_ in `#16321 <https://github.com/galaxyproject/galaxy/pull/16321>`_
* Increase `CustosAuthnzToken.external_user_id` column size by `@davelopez <https://github.com/davelopez>`_ in `#16818 <https://github.com/galaxyproject/galaxy/pull/16818>`_

=============
Other changes
=============

* Follow up on object store selection PR. by `@jmchilton <https://github.com/jmchilton>`_ in `#15654 <https://github.com/galaxyproject/galaxy/pull/15654>`_
* Fix Enums in API docs by `@davelopez <https://github.com/davelopez>`_ in `#15740 <https://github.com/galaxyproject/galaxy/pull/15740>`_
* merge release_23.0 into dev by `@martenson <https://github.com/martenson>`_ in `#15830 <https://github.com/galaxyproject/galaxy/pull/15830>`_
* Fix linting of FITS datatype code by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16169 <https://github.com/galaxyproject/galaxy/pull/16169>`_
* backport of pysam tostring by `@martenson <https://github.com/martenson>`_ in `#16822 <https://github.com/galaxyproject/galaxy/pull/16822>`_

-------------------
23.0.6 (2023-10-23)
-------------------


=========
Bug fixes
=========

* 
* Fix extra files path handling by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16541 <https://github.com/galaxyproject/galaxy/pull/16541>`_
* Don't fail invocation message without dependent_workflow_step_id by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16628 <https://github.com/galaxyproject/galaxy/pull/16628>`_

-------------------
23.0.5 (2023-07-29)
-------------------


=========
Bug fixes
=========

* 
* 
* Copy when_expression when copying workflow step by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16377 <https://github.com/galaxyproject/galaxy/pull/16377>`_

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
* Display DCE in job parameter component, allow rerunning with DCE input by `@mvdbeek <https://github.com/mvdbeek>`_ in `#15744 <https://github.com/galaxyproject/galaxy/pull/15744>`_
* Fix folder listing via file browser by `@mvdbeek <https://github.com/mvdbeek>`_ in `#15950 <https://github.com/galaxyproject/galaxy/pull/15950>`_
* Fix RO-crate invocation export with complex collections by `@davelopez <https://github.com/davelopez>`_ in `#15971 <https://github.com/galaxyproject/galaxy/pull/15971>`_
* Backport Improve display chunk generation for BAMs by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16007 <https://github.com/galaxyproject/galaxy/pull/16007>`_
* Ensure history export contains all expected datasets by `@davelopez <https://github.com/davelopez>`_ in `#16013 <https://github.com/galaxyproject/galaxy/pull/16013>`_
* Various fixes to path prefix handling by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16033 <https://github.com/galaxyproject/galaxy/pull/16033>`_
* Fix dataype_change not updating HDCA update_time by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16099 <https://github.com/galaxyproject/galaxy/pull/16099>`_
* Fix mypy error due to alembic 1.11.0 by `@nsoranzo <https://github.com/nsoranzo>`_ in `#16104 <https://github.com/galaxyproject/galaxy/pull/16104>`_
* Fix extended metadata file size handling by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16109 <https://github.com/galaxyproject/galaxy/pull/16109>`_
* Fix implicit converters with optional parameters by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16133 <https://github.com/galaxyproject/galaxy/pull/16133>`_
* Make ``ctx_rev`` optional in InstalledToolShedRepository response model by `@dannon <https://github.com/dannon>`_ in `#16139 <https://github.com/galaxyproject/galaxy/pull/16139>`_
* Fix optional fields being validated as missing in ts api by `@jmchilton <https://github.com/jmchilton>`_ in `#16141 <https://github.com/galaxyproject/galaxy/pull/16141>`_
* Support ro crate 0.8.0 and 0.7.0 by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16193 <https://github.com/galaxyproject/galaxy/pull/16193>`_
* Verify existence of default value attribute for user forms fields by `@guerler <https://github.com/guerler>`_ in `#16205 <https://github.com/galaxyproject/galaxy/pull/16205>`_

-------------------
20.9.0 (2020-10-15)
-------------------

* First release from the 20.09 branch of Galaxy.

-------------------
20.5.0 (2020-07-04)
-------------------

* First release from the 20.05 branch of Galaxy.
