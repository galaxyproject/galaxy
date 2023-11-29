History
-------

.. to_doc

-------------------
23.1.2 (2023-11-29)
-------------------


=========
Bug fixes
=========

* Provide error message instead of internal server error by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16905 <https://github.com/galaxyproject/galaxy/pull/16905>`_
* Fix input dates in notifications: consider timezone offset by `@davelopez <https://github.com/davelopez>`_ in `#17088 <https://github.com/galaxyproject/galaxy/pull/17088>`_

============
Enhancements
============

* Add HEAD route to job_files endpoint by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17072 <https://github.com/galaxyproject/galaxy/pull/17072>`_

-------------------
23.1.1 (2023-10-23)
-------------------


=========
Bug fixes
=========

* Create ToolSuccess route and refactor component by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#15484 <https://github.com/galaxyproject/galaxy/pull/15484>`_
* fix premature return in user API by `@martenson <https://github.com/martenson>`_ in `#15781 <https://github.com/galaxyproject/galaxy/pull/15781>`_
* Ensure session is request-scoped for legacy endpoints by `@jdavcs <https://github.com/jdavcs>`_ in `#16207 <https://github.com/galaxyproject/galaxy/pull/16207>`_
* allow anon access for api/datasets/get_content_as_text by `@martenson <https://github.com/martenson>`_ in `#16226 <https://github.com/galaxyproject/galaxy/pull/16226>`_
* Fix form builder value handling by `@guerler <https://github.com/guerler>`_ in `#16304 <https://github.com/galaxyproject/galaxy/pull/16304>`_
* Fix tags ownership by `@davelopez <https://github.com/davelopez>`_ in `#16339 <https://github.com/galaxyproject/galaxy/pull/16339>`_
* Fix histories count by `@davelopez <https://github.com/davelopez>`_ in `#16400 <https://github.com/galaxyproject/galaxy/pull/16400>`_
* Make datatype edit default value a string instead of list of strings by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16591 <https://github.com/galaxyproject/galaxy/pull/16591>`_
* Backport tool mem fixes by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16601 <https://github.com/galaxyproject/galaxy/pull/16601>`_
* Optimize getting current user session by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16604 <https://github.com/galaxyproject/galaxy/pull/16604>`_
* Drop RecursiveMiddleware by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16605 <https://github.com/galaxyproject/galaxy/pull/16605>`_
* List extra files only for terminal datasets by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16705 <https://github.com/galaxyproject/galaxy/pull/16705>`_
* Copy the collection contents by default when copying a collection by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16717 <https://github.com/galaxyproject/galaxy/pull/16717>`_
* Fix up local tool version handling by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16836 <https://github.com/galaxyproject/galaxy/pull/16836>`_
* Fix delete collection + elements by `@davelopez <https://github.com/davelopez>`_ in `#16879 <https://github.com/galaxyproject/galaxy/pull/16879>`_

============
Enhancements
============

* Empower Users to Select Storage Destination by `@jmchilton <https://github.com/jmchilton>`_ in `#14073 <https://github.com/galaxyproject/galaxy/pull/14073>`_
* Add Storage Dashboard visualizations for histories by `@davelopez <https://github.com/davelopez>`_ in `#14820 <https://github.com/galaxyproject/galaxy/pull/14820>`_
* External Login Flow: Redirect users if account already exists by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#15019 <https://github.com/galaxyproject/galaxy/pull/15019>`_
* Various Tool Shed Cleanup by `@jmchilton <https://github.com/jmchilton>`_ in `#15247 <https://github.com/galaxyproject/galaxy/pull/15247>`_
* Add Storage Management API by `@davelopez <https://github.com/davelopez>`_ in `#15295 <https://github.com/galaxyproject/galaxy/pull/15295>`_
* OIDC tokens by `@SergeyYakubov <https://github.com/SergeyYakubov>`_ in `#15300 <https://github.com/galaxyproject/galaxy/pull/15300>`_
* Add support for visualizing HDF5 datasets. by `@jarrah42 <https://github.com/jarrah42>`_ in `#15394 <https://github.com/galaxyproject/galaxy/pull/15394>`_
* Towards SQLAlchemy 2.0: drop session autocommit setting by `@jdavcs <https://github.com/jdavcs>`_ in `#15421 <https://github.com/galaxyproject/galaxy/pull/15421>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#15435 <https://github.com/galaxyproject/galaxy/pull/15435>`_
* Unify url handling with filesources by `@nuwang <https://github.com/nuwang>`_ in `#15497 <https://github.com/galaxyproject/galaxy/pull/15497>`_
* Explore tool remote test data by `@davelopez <https://github.com/davelopez>`_ in `#15510 <https://github.com/galaxyproject/galaxy/pull/15510>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#15564 <https://github.com/galaxyproject/galaxy/pull/15564>`_
* Drop workflow exports to myexperiment.org by `@dannon <https://github.com/dannon>`_ in `#15576 <https://github.com/galaxyproject/galaxy/pull/15576>`_
* Add Galaxy Notification System by `@davelopez <https://github.com/davelopez>`_ in `#15663 <https://github.com/galaxyproject/galaxy/pull/15663>`_
* Mention OpenAPI docs in Galaxy API Documentation by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#15713 <https://github.com/galaxyproject/galaxy/pull/15713>`_
* Fix/Enhance recalculate disk usage API endpoint by `@davelopez <https://github.com/davelopez>`_ in `#15739 <https://github.com/galaxyproject/galaxy/pull/15739>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#15890 <https://github.com/galaxyproject/galaxy/pull/15890>`_
* Add History Archival feature by `@davelopez <https://github.com/davelopez>`_ in `#16003 <https://github.com/galaxyproject/galaxy/pull/16003>`_
* Code cleanups from ruff and pyupgrade by `@nsoranzo <https://github.com/nsoranzo>`_ in `#16035 <https://github.com/galaxyproject/galaxy/pull/16035>`_
* Dataset chunking tests (and small fixes) by `@jmchilton <https://github.com/jmchilton>`_ in `#16069 <https://github.com/galaxyproject/galaxy/pull/16069>`_
* Paginate History Store by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#16084 <https://github.com/galaxyproject/galaxy/pull/16084>`_
* Allow HEAD request for requesting metadata files by `@martenson <https://github.com/martenson>`_ in `#16113 <https://github.com/galaxyproject/galaxy/pull/16113>`_
* Add option to see invocations related to a history by `@martenson <https://github.com/martenson>`_ in `#16136 <https://github.com/galaxyproject/galaxy/pull/16136>`_
* Improve histories and datasets immutability checks by `@davelopez <https://github.com/davelopez>`_ in `#16143 <https://github.com/galaxyproject/galaxy/pull/16143>`_
* Migrate display applications API to Fast API by `@heisner-tillman <https://github.com/heisner-tillman>`_ in `#16156 <https://github.com/galaxyproject/galaxy/pull/16156>`_
* adjust grid sharing indicators by `@martenson <https://github.com/martenson>`_ in `#16163 <https://github.com/galaxyproject/galaxy/pull/16163>`_
* Remove various fallback behaviors by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16199 <https://github.com/galaxyproject/galaxy/pull/16199>`_
* bring grids for (published) pages on par with workflows by `@martenson <https://github.com/martenson>`_ in `#16209 <https://github.com/galaxyproject/galaxy/pull/16209>`_
* Small test decorator improvements. by `@jmchilton <https://github.com/jmchilton>`_ in `#16220 <https://github.com/galaxyproject/galaxy/pull/16220>`_
* Don't error on missing parameters or unused parameters in UI controllers by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16246 <https://github.com/galaxyproject/galaxy/pull/16246>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#16267 <https://github.com/galaxyproject/galaxy/pull/16267>`_
* Fix Storage Dashboard missing archived histories by `@davelopez <https://github.com/davelopez>`_ in `#16473 <https://github.com/galaxyproject/galaxy/pull/16473>`_
* Add missing archived filter in saved histories by `@davelopez <https://github.com/davelopez>`_ in `#16475 <https://github.com/galaxyproject/galaxy/pull/16475>`_
* Drop expunge_all() call in WebTransactionRequest by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16606 <https://github.com/galaxyproject/galaxy/pull/16606>`_

=============
Other changes
=============

* Follow up on object store selection PR. by `@jmchilton <https://github.com/jmchilton>`_ in `#15654 <https://github.com/galaxyproject/galaxy/pull/15654>`_
* Tweaks to new object store and quota APIs by `@jmchilton <https://github.com/jmchilton>`_ in `#15709 <https://github.com/galaxyproject/galaxy/pull/15709>`_
* Fix Enums in API docs by `@davelopez <https://github.com/davelopez>`_ in `#15740 <https://github.com/galaxyproject/galaxy/pull/15740>`_
* Quota source labelling bug fixes and improvements  by `@jmchilton <https://github.com/jmchilton>`_ in `#15795 <https://github.com/galaxyproject/galaxy/pull/15795>`_
* merge release_23.0 into dev by `@martenson <https://github.com/martenson>`_ in `#15830 <https://github.com/galaxyproject/galaxy/pull/15830>`_
* merge release_23.0 into dev by `@martenson <https://github.com/martenson>`_ in `#15854 <https://github.com/galaxyproject/galaxy/pull/15854>`_
* Merge 23.0 into dev by `@nsoranzo <https://github.com/nsoranzo>`_ in `#15902 <https://github.com/galaxyproject/galaxy/pull/15902>`_
* Fix recalculate_quota throug kombu message by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16299 <https://github.com/galaxyproject/galaxy/pull/16299>`_

-------------------
23.0.6 (2023-10-23)
-------------------


=========
Bug fixes
=========

* 
* Fix incorrect ASGI request host by `@davelopez <https://github.com/davelopez>`_ in `#16574 <https://github.com/galaxyproject/galaxy/pull/16574>`_
* Allow the legacy DELETE dataset endpoint to accept any string for the history_id by `@assuntad23 <https://github.com/assuntad23>`_ in `#16593 <https://github.com/galaxyproject/galaxy/pull/16593>`_

-------------------
23.0.5 (2023-07-29)
-------------------


=========
Bug fixes
=========

* 
* 
* Fix active step display in workflow editor side panel by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16364 <https://github.com/galaxyproject/galaxy/pull/16364>`_

-------------------
23.0.4 (2023-06-30)
-------------------


=========
Bug fixes
=========

* 
* 
* 
* Fix folder access for anonymous user by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16330 <https://github.com/galaxyproject/galaxy/pull/16330>`_

-------------------
23.0.3 (2023-06-26)
-------------------


=========
Bug fixes
=========

* 
* 
* 
* 
* Fix converting Enum value to str for Python 3.11 by `@nsoranzo <https://github.com/nsoranzo>`_ in `#16284 <https://github.com/galaxyproject/galaxy/pull/16284>`_

============
Enhancements
============

* 
* When importing tool data bundles, use the first loc file for the matching table by `@natefoo <https://github.com/natefoo>`_ in `#16247 <https://github.com/galaxyproject/galaxy/pull/16247>`_

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
* 
* 
* Display DCE in job parameter component, allow rerunning with DCE input by `@mvdbeek <https://github.com/mvdbeek>`_ in `#15744 <https://github.com/galaxyproject/galaxy/pull/15744>`_
* Various fixes to path prefix handling by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16033 <https://github.com/galaxyproject/galaxy/pull/16033>`_
* Fix dataype_change not updating HDCA update_time by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16099 <https://github.com/galaxyproject/galaxy/pull/16099>`_
* Ignore invalid query params in display_by_username_and_slug by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16117 <https://github.com/galaxyproject/galaxy/pull/16117>`_

-------------------
20.5.0 (2020-07-04)
-------------------

* First release from the 20.05 branch of Galaxy.
