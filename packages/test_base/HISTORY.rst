History
-------

.. to_doc

-----------
24.2.2.dev0
-----------



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

* Fix some deprecations by `@nsoranzo <https://github.com/nsoranzo>`_ in `#18433 <https://github.com/galaxyproject/galaxy/pull/18433>`_
* Fix tag processing in library upload by `@davelopez <https://github.com/davelopez>`_ in `#18714 <https://github.com/galaxyproject/galaxy/pull/18714>`_

============
Enhancements
============

* Mixed enhancements from CWL branch by `@nsoranzo <https://github.com/nsoranzo>`_ in `#18539 <https://github.com/galaxyproject/galaxy/pull/18539>`_
* Workflow Landing Requests by `@jmchilton <https://github.com/jmchilton>`_ in `#18807 <https://github.com/galaxyproject/galaxy/pull/18807>`_
* Migrate Library Contents API to FastAPI by `@arash77 <https://github.com/arash77>`_ in `#18838 <https://github.com/galaxyproject/galaxy/pull/18838>`_
* Implement Pydantic model for workflow test format.  by `@jmchilton <https://github.com/jmchilton>`_ in `#18884 <https://github.com/galaxyproject/galaxy/pull/18884>`_
* Type annotations and fixes by `@nsoranzo <https://github.com/nsoranzo>`_ in `#18911 <https://github.com/galaxyproject/galaxy/pull/18911>`_
* Allow CORS requests to /api/workflow_landings by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18963 <https://github.com/galaxyproject/galaxy/pull/18963>`_
* Decouple user email from role name by `@jdavcs <https://github.com/jdavcs>`_ in `#18966 <https://github.com/galaxyproject/galaxy/pull/18966>`_
* More concise, readable tool execution testing. by `@jmchilton <https://github.com/jmchilton>`_ in `#18977 <https://github.com/galaxyproject/galaxy/pull/18977>`_
* Workflow landing improvements by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18979 <https://github.com/galaxyproject/galaxy/pull/18979>`_
* Allow recovering a normalized version of workflow request state from API by `@jmchilton <https://github.com/jmchilton>`_ in `#18985 <https://github.com/galaxyproject/galaxy/pull/18985>`_
* A variety of improvements around tool parameter modeling (second try) by `@jmchilton <https://github.com/jmchilton>`_ in `#19027 <https://github.com/galaxyproject/galaxy/pull/19027>`_
* Access public history in job cache / job search by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19108 <https://github.com/galaxyproject/galaxy/pull/19108>`_
* Always validate hashes when provided by `@nsoranzo <https://github.com/nsoranzo>`_ in `#19110 <https://github.com/galaxyproject/galaxy/pull/19110>`_
* Fix default value handling for parameters connected to required parameters by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19219 <https://github.com/galaxyproject/galaxy/pull/19219>`_
* Release testing - selenium tests for workflow invocation export. by `@jmchilton <https://github.com/jmchilton>`_ in `#19262 <https://github.com/galaxyproject/galaxy/pull/19262>`_

=============
Other changes
=============

* Fix workflow invocation accessibility check by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18746 <https://github.com/galaxyproject/galaxy/pull/18746>`_

-------------------
24.1.4 (2024-12-11)
-------------------


=========
Bug fixes
=========

* Fix subwofklow tags serialization type by `@arash77 <https://github.com/arash77>`_ in `#18456 <https://github.com/galaxyproject/galaxy/pull/18456>`_
* Fix infinitely delayed workflow scheduling if skipped step creates HDCA by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18751 <https://github.com/galaxyproject/galaxy/pull/18751>`_
* Fix wrong extension on pick data output by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18798 <https://github.com/galaxyproject/galaxy/pull/18798>`_
* Fix data_column ref to nested collection by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18875 <https://github.com/galaxyproject/galaxy/pull/18875>`_
* Access tool data table filters in workflow building mode by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18900 <https://github.com/galaxyproject/galaxy/pull/18900>`_

-------------------
24.1.3 (2024-10-25)
-------------------


=========
Bug fixes
=========

* Fix subwofklow tags serialization type by `@arash77 <https://github.com/arash77>`_ in `#18456 <https://github.com/galaxyproject/galaxy/pull/18456>`_
* Fix infinitely delayed workflow scheduling if skipped step creates HDCA by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18751 <https://github.com/galaxyproject/galaxy/pull/18751>`_
* Fix wrong extension on pick data output by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18798 <https://github.com/galaxyproject/galaxy/pull/18798>`_
* Fix data_column ref to nested collection by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18875 <https://github.com/galaxyproject/galaxy/pull/18875>`_
* Access tool data table filters in workflow building mode by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18900 <https://github.com/galaxyproject/galaxy/pull/18900>`_

-------------------
24.1.2 (2024-09-25)
-------------------


=========
Bug fixes
=========

* Fix infinitely delayed workflow scheduling if skipped step creates HDCA by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18751 <https://github.com/galaxyproject/galaxy/pull/18751>`_
* Fix wrong extension on pick data output by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18798 <https://github.com/galaxyproject/galaxy/pull/18798>`_
* Fix data_column ref to nested collection by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18875 <https://github.com/galaxyproject/galaxy/pull/18875>`_

-------------------
24.1.1 (2024-07-02)
-------------------


=========
Bug fixes
=========

* Revert some requests import changes by `@nsoranzo <https://github.com/nsoranzo>`_ in `#18199 <https://github.com/galaxyproject/galaxy/pull/18199>`_
* Fix subwofklow tags serialization type by `@arash77 <https://github.com/arash77>`_ in `#18456 <https://github.com/galaxyproject/galaxy/pull/18456>`_

============
Enhancements
============

* Remove deprecated BCO export endpoint by `@martenson <https://github.com/martenson>`_ in `#16645 <https://github.com/galaxyproject/galaxy/pull/16645>`_
* Enable all-vs-all collection analysis patterns. by `@jmchilton <https://github.com/jmchilton>`_ in `#17366 <https://github.com/galaxyproject/galaxy/pull/17366>`_
* Code cleanups from ruff and pyupgrade by `@nsoranzo <https://github.com/nsoranzo>`_ in `#17654 <https://github.com/galaxyproject/galaxy/pull/17654>`_
* Error reporting unit tests by `@jmchilton <https://github.com/jmchilton>`_ in `#17968 <https://github.com/galaxyproject/galaxy/pull/17968>`_
* Add galaxy to user agent by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18003 <https://github.com/galaxyproject/galaxy/pull/18003>`_
* Empower users to bring their own storage and file sources by `@jmchilton <https://github.com/jmchilton>`_ in `#18127 <https://github.com/galaxyproject/galaxy/pull/18127>`_
* More structured indexing for user data objects. by `@jmchilton <https://github.com/jmchilton>`_ in `#18291 <https://github.com/galaxyproject/galaxy/pull/18291>`_

-------------------
24.0.3 (2024-06-28)
-------------------


=========
Bug fixes
=========

* Fix submitted value in workflow run form if data is constrained by tag filter by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18193 <https://github.com/galaxyproject/galaxy/pull/18193>`_

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

* Make `wait_for_history_jobs` look at jobs, not datasets by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17892 <https://github.com/galaxyproject/galaxy/pull/17892>`_
* Fix missing implicit conversion for mapped over jobs by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17952 <https://github.com/galaxyproject/galaxy/pull/17952>`_

-------------------
24.0.0 (2024-04-02)
-------------------


============
Enhancements
============

* port invocation API to fastapi by `@martenson <https://github.com/martenson>`_ in `#16707 <https://github.com/galaxyproject/galaxy/pull/16707>`_
* Python 3.8 as minimum by `@mr-c <https://github.com/mr-c>`_ in `#16954 <https://github.com/galaxyproject/galaxy/pull/16954>`_
* Support for OIDC API Auth and OIDC integration tests by `@nuwang <https://github.com/nuwang>`_ in `#16977 <https://github.com/galaxyproject/galaxy/pull/16977>`_
* Reuse test instance during non-integration tests by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17234 <https://github.com/galaxyproject/galaxy/pull/17234>`_
* API endpoint that allows "changing" the objectstore for "safe" scenarios.  by `@jmchilton <https://github.com/jmchilton>`_ in `#17329 <https://github.com/galaxyproject/galaxy/pull/17329>`_
* Update to black 2024 stable style by `@nsoranzo <https://github.com/nsoranzo>`_ in `#17391 <https://github.com/galaxyproject/galaxy/pull/17391>`_
* Allow filtering history datasets by object store ID and quota source. by `@jmchilton <https://github.com/jmchilton>`_ in `#17460 <https://github.com/galaxyproject/galaxy/pull/17460>`_
* Refactor Workflow API routes - Part 1 by `@heisner-tillman <https://github.com/heisner-tillman>`_ in `#17463 <https://github.com/galaxyproject/galaxy/pull/17463>`_
* Filter out subworkflow invocations by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17558 <https://github.com/galaxyproject/galaxy/pull/17558>`_

-------------------
23.2.1 (2024-02-21)
-------------------


=========
Bug fixes
=========

* Restore ToolsApi and create new api route for new panel structure by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#16872 <https://github.com/galaxyproject/galaxy/pull/16872>`_

============
Enhancements
============

* Implement default locations for data and collection parameters. by `@jmchilton <https://github.com/jmchilton>`_ in `#14955 <https://github.com/galaxyproject/galaxy/pull/14955>`_
* Delete non-terminal jobs and subworkflow invocations when cancelling invocation by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16252 <https://github.com/galaxyproject/galaxy/pull/16252>`_
* Augment pgcleanup to allow periodically deleting old datasets. by `@jmchilton <https://github.com/jmchilton>`_ in `#16340 <https://github.com/galaxyproject/galaxy/pull/16340>`_
* Refactor Tool Panel views structures and combine ToolBox and ToolBoxWorkflow into one component by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#16739 <https://github.com/galaxyproject/galaxy/pull/16739>`_
* Change `api/tool_panel` to `api/tool_panels/...` by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#16928 <https://github.com/galaxyproject/galaxy/pull/16928>`_

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

* Fix duplicated tools in tool panel view section copying by `@jmchilton <https://github.com/jmchilton>`_ in `#17036 <https://github.com/galaxyproject/galaxy/pull/17036>`_

-------------------
23.1.1 (2023-10-23)
-------------------


=========
Bug fixes
=========

* Ensure session is request-scoped for legacy endpoints by `@jdavcs <https://github.com/jdavcs>`_ in `#16207 <https://github.com/galaxyproject/galaxy/pull/16207>`_

============
Enhancements
============

* Empower Users to Select Storage Destination by `@jmchilton <https://github.com/jmchilton>`_ in `#14073 <https://github.com/galaxyproject/galaxy/pull/14073>`_
* Outline Deployment Tests by `@jmchilton <https://github.com/jmchilton>`_ in `#15420 <https://github.com/galaxyproject/galaxy/pull/15420>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#15890 <https://github.com/galaxyproject/galaxy/pull/15890>`_
* Add History Archival feature by `@davelopez <https://github.com/davelopez>`_ in `#16003 <https://github.com/galaxyproject/galaxy/pull/16003>`_
* Dataset chunking tests (and small fixes) by `@jmchilton <https://github.com/jmchilton>`_ in `#16069 <https://github.com/galaxyproject/galaxy/pull/16069>`_
* Improve histories and datasets immutability checks by `@davelopez <https://github.com/davelopez>`_ in `#16143 <https://github.com/galaxyproject/galaxy/pull/16143>`_
* bring grids for (published) pages on par with workflows by `@martenson <https://github.com/martenson>`_ in `#16209 <https://github.com/galaxyproject/galaxy/pull/16209>`_
* Small test decorator improvements. by `@jmchilton <https://github.com/jmchilton>`_ in `#16220 <https://github.com/galaxyproject/galaxy/pull/16220>`_

=============
Other changes
=============

* Tweaks to new object store and quota APIs by `@jmchilton <https://github.com/jmchilton>`_ in `#15709 <https://github.com/galaxyproject/galaxy/pull/15709>`_

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

* Ensure history export contains all expected datasets by `@davelopez <https://github.com/davelopez>`_ in `#16013 <https://github.com/galaxyproject/galaxy/pull/16013>`_
* Fix extended metadata file size handling by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16109 <https://github.com/galaxyproject/galaxy/pull/16109>`_

-------------------
20.9.0 (2020-10-15)
-------------------

* Initial release from the 20.09 branch of Galaxy.

-------------------
20.5.0 (2020-07-04)
-------------------

* Initial import from the 20.05 branch of Galaxy.
