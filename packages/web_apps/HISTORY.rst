History
-------

.. to_doc

-----------
24.2.2.dev0
-----------



-------------------
24.2.1 (2025-02-28)
-------------------


=========
Bug fixes
=========

* Fix user preferences secret (without vault) lost on save by `@davelopez <https://github.com/davelopez>`_ in `#19610 <https://github.com/galaxyproject/galaxy/pull/19610>`_
* Disable chatgxy wizard for anon users by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19628 <https://github.com/galaxyproject/galaxy/pull/19628>`_

-------------------
24.2.0 (2025-02-11)
-------------------


=========
Bug fixes
=========

* Drop "Send to cloud" tool and associated cloudauthz code by `@jdavcs <https://github.com/jdavcs>`_ in `#18196 <https://github.com/galaxyproject/galaxy/pull/18196>`_
* Fix some deprecations by `@nsoranzo <https://github.com/nsoranzo>`_ in `#18433 <https://github.com/galaxyproject/galaxy/pull/18433>`_
* Fix MessageException handling in get_edit by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18529 <https://github.com/galaxyproject/galaxy/pull/18529>`_
* Fixes for errors reported by mypy 1.11.0 by `@nsoranzo <https://github.com/nsoranzo>`_ in `#18608 <https://github.com/galaxyproject/galaxy/pull/18608>`_
* Fix new flake8-bugbear B039 and mypy type-var errors by `@nsoranzo <https://github.com/nsoranzo>`_ in `#18755 <https://github.com/galaxyproject/galaxy/pull/18755>`_
* Fix response if dataset requested by display application is deleted by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18803 <https://github.com/galaxyproject/galaxy/pull/18803>`_
* Ignore preflight options in API schema by `@jmchilton <https://github.com/jmchilton>`_ in `#18983 <https://github.com/galaxyproject/galaxy/pull/18983>`_
* Fix issue with generating slug for sharing by `@arash77 <https://github.com/arash77>`_ in `#18986 <https://github.com/galaxyproject/galaxy/pull/18986>`_
* Fix auto-detect metadata from Edit Dataset Attributes panel by `@davelopez <https://github.com/davelopez>`_ in `#19025 <https://github.com/galaxyproject/galaxy/pull/19025>`_
* Prevent purged users from logging in by `@jdavcs <https://github.com/jdavcs>`_ in `#19094 <https://github.com/galaxyproject/galaxy/pull/19094>`_
* Restore access to saved visualizations by `@guerler <https://github.com/guerler>`_ in `#19136 <https://github.com/galaxyproject/galaxy/pull/19136>`_
* Fix PSA Redirect by `@dannon <https://github.com/dannon>`_ in `#19247 <https://github.com/galaxyproject/galaxy/pull/19247>`_
* Login redirect followup by `@dannon <https://github.com/dannon>`_ in `#19251 <https://github.com/galaxyproject/galaxy/pull/19251>`_
* Fix invocation metrics usability by providing job context. by `@jmchilton <https://github.com/jmchilton>`_ in `#19279 <https://github.com/galaxyproject/galaxy/pull/19279>`_
* Fix importing shared workflows with deeply nested subworkflows by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19335 <https://github.com/galaxyproject/galaxy/pull/19335>`_
* Show Keycloak provider label in UI by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#19447 <https://github.com/galaxyproject/galaxy/pull/19447>`_
* Serialize message exceptions on execution error by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19483 <https://github.com/galaxyproject/galaxy/pull/19483>`_
* Use visualizations api in trackster by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19495 <https://github.com/galaxyproject/galaxy/pull/19495>`_
* Set a hard limit of 100 invocations per request in api/invocations by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19497 <https://github.com/galaxyproject/galaxy/pull/19497>`_
* Fix deleting lddas in batch by `@davelopez <https://github.com/davelopez>`_ in `#19506 <https://github.com/galaxyproject/galaxy/pull/19506>`_
* Fix WSGI response status handling in controller methods by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19520 <https://github.com/galaxyproject/galaxy/pull/19520>`_
* Fix saved visualization (non-trackster ones) not displaying by `@davelopez <https://github.com/davelopez>`_ in `#19561 <https://github.com/galaxyproject/galaxy/pull/19561>`_
* Allow unused query params in ``workflows/export_to_file`` by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19574 <https://github.com/galaxyproject/galaxy/pull/19574>`_

============
Enhancements
============

* Experimental galactic wizard by `@dannon <https://github.com/dannon>`_ in `#15860 <https://github.com/galaxyproject/galaxy/pull/15860>`_
* Feature - stdout live reporting by `@gecage952 <https://github.com/gecage952>`_ in `#16975 <https://github.com/galaxyproject/galaxy/pull/16975>`_
* Add errors fast api by `@arash77 <https://github.com/arash77>`_ in `#18093 <https://github.com/galaxyproject/galaxy/pull/18093>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#18226 <https://github.com/galaxyproject/galaxy/pull/18226>`_
* Allow OAuth 2.0 user defined file sources (w/Dropbox integration) by `@jmchilton <https://github.com/jmchilton>`_ in `#18272 <https://github.com/galaxyproject/galaxy/pull/18272>`_
* More data access tests, some refactoring and cleanup by `@jdavcs <https://github.com/jdavcs>`_ in `#18312 <https://github.com/galaxyproject/galaxy/pull/18312>`_
* Replace History Dataset Picker in Library Folder by `@itisAliRH <https://github.com/itisAliRH>`_ in `#18518 <https://github.com/galaxyproject/galaxy/pull/18518>`_
* Update openapi-typescript dependency to version 6.7.6 by `@davelopez <https://github.com/davelopez>`_ in `#18519 <https://github.com/galaxyproject/galaxy/pull/18519>`_
* Improve datasets permissions API schema typing by `@davelopez <https://github.com/davelopez>`_ in `#18563 <https://github.com/galaxyproject/galaxy/pull/18563>`_
* Drop unused datasets controller methods by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18568 <https://github.com/galaxyproject/galaxy/pull/18568>`_
* Improve typing for archived histories API schema by `@davelopez <https://github.com/davelopez>`_ in `#18586 <https://github.com/galaxyproject/galaxy/pull/18586>`_
* More tool test typing. by `@jmchilton <https://github.com/jmchilton>`_ in `#18590 <https://github.com/galaxyproject/galaxy/pull/18590>`_
* Improve update user API payload schema by `@davelopez <https://github.com/davelopez>`_ in `#18602 <https://github.com/galaxyproject/galaxy/pull/18602>`_
* Improve update history payload schema by `@davelopez <https://github.com/davelopez>`_ in `#18618 <https://github.com/galaxyproject/galaxy/pull/18618>`_
* Parameter Model Improvements by `@jmchilton <https://github.com/jmchilton>`_ in `#18641 <https://github.com/galaxyproject/galaxy/pull/18641>`_
* Improve accept header API schema by `@davelopez <https://github.com/davelopez>`_ in `#18668 <https://github.com/galaxyproject/galaxy/pull/18668>`_
* Allow access to invocation via shared or published history by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18707 <https://github.com/galaxyproject/galaxy/pull/18707>`_
* Migrate Visualizations API to FastAPI by `@arash77 <https://github.com/arash77>`_ in `#18721 <https://github.com/galaxyproject/galaxy/pull/18721>`_
* Improvements to help terms & tool help. by `@jmchilton <https://github.com/jmchilton>`_ in `#18722 <https://github.com/galaxyproject/galaxy/pull/18722>`_
* More typing, docs, and decomposition around tool execution by `@jmchilton <https://github.com/jmchilton>`_ in `#18758 <https://github.com/galaxyproject/galaxy/pull/18758>`_
* Refactor ``LibraryDatasetsManager`` and fix type annotation issue by `@nsoranzo <https://github.com/nsoranzo>`_ in `#18773 <https://github.com/galaxyproject/galaxy/pull/18773>`_
* Backend handling of setting user-role, user-group, and group-role associations by `@jdavcs <https://github.com/jdavcs>`_ in `#18777 <https://github.com/galaxyproject/galaxy/pull/18777>`_
* Update Visualization FastAPI by `@arash77 <https://github.com/arash77>`_ in `#18792 <https://github.com/galaxyproject/galaxy/pull/18792>`_
* Workflow Landing Requests by `@jmchilton <https://github.com/jmchilton>`_ in `#18807 <https://github.com/galaxyproject/galaxy/pull/18807>`_
* Migrate Library Contents API to FastAPI by `@arash77 <https://github.com/arash77>`_ in `#18838 <https://github.com/galaxyproject/galaxy/pull/18838>`_
* Enable extra user preferences for remotely authorized users by `@maartenschermer <https://github.com/maartenschermer>`_ in `#18887 <https://github.com/galaxyproject/galaxy/pull/18887>`_
* Enable ``ignore-without-code`` mypy error code by `@nsoranzo <https://github.com/nsoranzo>`_ in `#18898 <https://github.com/galaxyproject/galaxy/pull/18898>`_
* Type annotations and fixes by `@nsoranzo <https://github.com/nsoranzo>`_ in `#18911 <https://github.com/galaxyproject/galaxy/pull/18911>`_
* Allow CORS requests to /api/workflow_landings by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18963 <https://github.com/galaxyproject/galaxy/pull/18963>`_
* Decouple user email from role name by `@jdavcs <https://github.com/jdavcs>`_ in `#18966 <https://github.com/galaxyproject/galaxy/pull/18966>`_
* Optimize to_history_dataset_association in create_datasets_from_library_folder by `@arash77 <https://github.com/arash77>`_ in `#18970 <https://github.com/galaxyproject/galaxy/pull/18970>`_
* Workflow landing improvements by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18979 <https://github.com/galaxyproject/galaxy/pull/18979>`_
* Allow recovering a normalized version of workflow request state from API by `@jmchilton <https://github.com/jmchilton>`_ in `#18985 <https://github.com/galaxyproject/galaxy/pull/18985>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#19031 <https://github.com/galaxyproject/galaxy/pull/19031>`_
* Silence the quota manager for updates by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#19046 <https://github.com/galaxyproject/galaxy/pull/19046>`_
* Add job metrics per invocation by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19048 <https://github.com/galaxyproject/galaxy/pull/19048>`_
* Run installed Galaxy with no config and a simplified entry point by `@natefoo <https://github.com/natefoo>`_ in `#19050 <https://github.com/galaxyproject/galaxy/pull/19050>`_
* Move TRS import into WorkflowContentManager by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19070 <https://github.com/galaxyproject/galaxy/pull/19070>`_
* Better cleanup of sharing roles on user purge by `@jdavcs <https://github.com/jdavcs>`_ in `#19096 <https://github.com/galaxyproject/galaxy/pull/19096>`_
* Always validate hashes when provided by `@nsoranzo <https://github.com/nsoranzo>`_ in `#19110 <https://github.com/galaxyproject/galaxy/pull/19110>`_
* Backport of Workflow Editor Activity Bar by `@dannon <https://github.com/dannon>`_ in `#19212 <https://github.com/galaxyproject/galaxy/pull/19212>`_
* Workflow Inputs Activity by `@ElectronicBlueberry <https://github.com/ElectronicBlueberry>`_ in `#19252 <https://github.com/galaxyproject/galaxy/pull/19252>`_

=============
Other changes
=============

* Format dev to fix linting. by `@jmchilton <https://github.com/jmchilton>`_ in `#18860 <https://github.com/galaxyproject/galaxy/pull/18860>`_

-------------------
24.1.4 (2024-12-11)
-------------------


=========
Bug fixes
=========

* Return generic message for password reset email by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#18479 <https://github.com/galaxyproject/galaxy/pull/18479>`_
* Fix view parameter type in Job index API by `@davelopez <https://github.com/davelopez>`_ in `#18521 <https://github.com/galaxyproject/galaxy/pull/18521>`_
* Check if dataset has any data before running provider checks by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18526 <https://github.com/galaxyproject/galaxy/pull/18526>`_
* Raise appropriate exception if ldda not found by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18569 <https://github.com/galaxyproject/galaxy/pull/18569>`_
* Close install model session when request ends by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18629 <https://github.com/galaxyproject/galaxy/pull/18629>`_
* Fix resume_paused_jobs if no session provided by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18640 <https://github.com/galaxyproject/galaxy/pull/18640>`_
* Fix extract workflow from history when implicit collection has no jobs by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18661 <https://github.com/galaxyproject/galaxy/pull/18661>`_
* Return error when following a link to a non-ready display application by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18672 <https://github.com/galaxyproject/galaxy/pull/18672>`_
* Only load authnz routes when oidc enabled by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18683 <https://github.com/galaxyproject/galaxy/pull/18683>`_
* File source and object store instance api fixes by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18685 <https://github.com/galaxyproject/galaxy/pull/18685>`_
* Fix sorting users in admin by last login by `@jdavcs <https://github.com/jdavcs>`_ in `#18694 <https://github.com/galaxyproject/galaxy/pull/18694>`_
* Fix resume paused jobs response handling by `@dannon <https://github.com/dannon>`_ in `#18733 <https://github.com/galaxyproject/galaxy/pull/18733>`_
* Fix wrong extension on pick data output by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18798 <https://github.com/galaxyproject/galaxy/pull/18798>`_
* Tighten TRS url check by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18841 <https://github.com/galaxyproject/galaxy/pull/18841>`_
* Fix Workflow index bookmark filter by `@itisAliRH <https://github.com/itisAliRH>`_ in `#18842 <https://github.com/galaxyproject/galaxy/pull/18842>`_
* Extend on disk checks to running, queued and error states by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18846 <https://github.com/galaxyproject/galaxy/pull/18846>`_
* Limit max number of items in dataproviders by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18881 <https://github.com/galaxyproject/galaxy/pull/18881>`_
* Access tool data table filters in workflow building mode by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18900 <https://github.com/galaxyproject/galaxy/pull/18900>`_
* Don't use ``async def`` where not appropriate by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18944 <https://github.com/galaxyproject/galaxy/pull/18944>`_
* Fix very slow workflow editor loading by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19068 <https://github.com/galaxyproject/galaxy/pull/19068>`_

============
Enhancements
============

* Make `default_panel_view` a `_by_host` option by `@natefoo <https://github.com/natefoo>`_ in `#18471 <https://github.com/galaxyproject/galaxy/pull/18471>`_

=============
Other changes
=============

* Fix check dataset check by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18856 <https://github.com/galaxyproject/galaxy/pull/18856>`_

-------------------
24.1.3 (2024-10-25)
-------------------


=========
Bug fixes
=========

* Return generic message for password reset email by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#18479 <https://github.com/galaxyproject/galaxy/pull/18479>`_
* Fix view parameter type in Job index API by `@davelopez <https://github.com/davelopez>`_ in `#18521 <https://github.com/galaxyproject/galaxy/pull/18521>`_
* Check if dataset has any data before running provider checks by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18526 <https://github.com/galaxyproject/galaxy/pull/18526>`_
* Raise appropriate exception if ldda not found by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18569 <https://github.com/galaxyproject/galaxy/pull/18569>`_
* Close install model session when request ends by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18629 <https://github.com/galaxyproject/galaxy/pull/18629>`_
* Fix resume_paused_jobs if no session provided by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18640 <https://github.com/galaxyproject/galaxy/pull/18640>`_
* Fix extract workflow from history when implicit collection has no jobs by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18661 <https://github.com/galaxyproject/galaxy/pull/18661>`_
* Return error when following a link to a non-ready display application by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18672 <https://github.com/galaxyproject/galaxy/pull/18672>`_
* Only load authnz routes when oidc enabled by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18683 <https://github.com/galaxyproject/galaxy/pull/18683>`_
* File source and object store instance api fixes by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18685 <https://github.com/galaxyproject/galaxy/pull/18685>`_
* Fix sorting users in admin by last login by `@jdavcs <https://github.com/jdavcs>`_ in `#18694 <https://github.com/galaxyproject/galaxy/pull/18694>`_
* Fix resume paused jobs response handling by `@dannon <https://github.com/dannon>`_ in `#18733 <https://github.com/galaxyproject/galaxy/pull/18733>`_
* Fix wrong extension on pick data output by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18798 <https://github.com/galaxyproject/galaxy/pull/18798>`_
* Tighten TRS url check by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18841 <https://github.com/galaxyproject/galaxy/pull/18841>`_
* Fix Workflow index bookmark filter by `@itisAliRH <https://github.com/itisAliRH>`_ in `#18842 <https://github.com/galaxyproject/galaxy/pull/18842>`_
* Extend on disk checks to running, queued and error states by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18846 <https://github.com/galaxyproject/galaxy/pull/18846>`_
* Limit max number of items in dataproviders by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18881 <https://github.com/galaxyproject/galaxy/pull/18881>`_
* Access tool data table filters in workflow building mode by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18900 <https://github.com/galaxyproject/galaxy/pull/18900>`_
* Don't use ``async def`` where not appropriate by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18944 <https://github.com/galaxyproject/galaxy/pull/18944>`_

============
Enhancements
============

* Make `default_panel_view` a `_by_host` option by `@natefoo <https://github.com/natefoo>`_ in `#18471 <https://github.com/galaxyproject/galaxy/pull/18471>`_

=============
Other changes
=============

* Fix check dataset check by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18856 <https://github.com/galaxyproject/galaxy/pull/18856>`_

-------------------
24.1.2 (2024-09-25)
-------------------


=========
Bug fixes
=========

* Return generic message for password reset email by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#18479 <https://github.com/galaxyproject/galaxy/pull/18479>`_
* Fix view parameter type in Job index API by `@davelopez <https://github.com/davelopez>`_ in `#18521 <https://github.com/galaxyproject/galaxy/pull/18521>`_
* Check if dataset has any data before running provider checks by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18526 <https://github.com/galaxyproject/galaxy/pull/18526>`_
* Raise appropriate exception if ldda not found by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18569 <https://github.com/galaxyproject/galaxy/pull/18569>`_
* Close install model session when request ends by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18629 <https://github.com/galaxyproject/galaxy/pull/18629>`_
* Fix resume_paused_jobs if no session provided by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18640 <https://github.com/galaxyproject/galaxy/pull/18640>`_
* Fix extract workflow from history when implicit collection has no jobs by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18661 <https://github.com/galaxyproject/galaxy/pull/18661>`_
* Return error when following a link to a non-ready display application by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18672 <https://github.com/galaxyproject/galaxy/pull/18672>`_
* Only load authnz routes when oidc enabled by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18683 <https://github.com/galaxyproject/galaxy/pull/18683>`_
* File source and object store instance api fixes by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18685 <https://github.com/galaxyproject/galaxy/pull/18685>`_
* Fix sorting users in admin by last login by `@jdavcs <https://github.com/jdavcs>`_ in `#18694 <https://github.com/galaxyproject/galaxy/pull/18694>`_
* Fix resume paused jobs response handling by `@dannon <https://github.com/dannon>`_ in `#18733 <https://github.com/galaxyproject/galaxy/pull/18733>`_
* Fix wrong extension on pick data output by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18798 <https://github.com/galaxyproject/galaxy/pull/18798>`_
* Tighten TRS url check by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18841 <https://github.com/galaxyproject/galaxy/pull/18841>`_
* Fix Workflow index bookmark filter by `@itisAliRH <https://github.com/itisAliRH>`_ in `#18842 <https://github.com/galaxyproject/galaxy/pull/18842>`_
* Extend on disk checks to running, queued and error states by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18846 <https://github.com/galaxyproject/galaxy/pull/18846>`_

============
Enhancements
============

* Make `default_panel_view` a `_by_host` option by `@natefoo <https://github.com/natefoo>`_ in `#18471 <https://github.com/galaxyproject/galaxy/pull/18471>`_

=============
Other changes
=============

* Fix check dataset check by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18856 <https://github.com/galaxyproject/galaxy/pull/18856>`_

-------------------
24.1.1 (2024-07-02)
-------------------


=========
Bug fixes
=========

* Fix permissions for temporary upload file for API uploads by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#17850 <https://github.com/galaxyproject/galaxy/pull/17850>`_
* Dynamic tool fixes by `@dcore94 <https://github.com/dcore94>`_ in `#18085 <https://github.com/galaxyproject/galaxy/pull/18085>`_
* Revert some requests import changes by `@nsoranzo <https://github.com/nsoranzo>`_ in `#18199 <https://github.com/galaxyproject/galaxy/pull/18199>`_
* Small bug fixes for user data plugins by `@jmchilton <https://github.com/jmchilton>`_ in `#18246 <https://github.com/galaxyproject/galaxy/pull/18246>`_
* Fix various packages' issues by `@nsoranzo <https://github.com/nsoranzo>`_ in `#18301 <https://github.com/galaxyproject/galaxy/pull/18301>`_

============
Enhancements
============

* Remove deprecated BCO export endpoint by `@martenson <https://github.com/martenson>`_ in `#16645 <https://github.com/galaxyproject/galaxy/pull/16645>`_
* Implement a page object accessibility dialog by `@jmchilton <https://github.com/jmchilton>`_ in `#17225 <https://github.com/galaxyproject/galaxy/pull/17225>`_
* Enable storage management by object store by `@jmchilton <https://github.com/jmchilton>`_ in `#17500 <https://github.com/galaxyproject/galaxy/pull/17500>`_
* Type annotation and CWL-related improvements by `@nsoranzo <https://github.com/nsoranzo>`_ in `#17630 <https://github.com/galaxyproject/galaxy/pull/17630>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#17653 <https://github.com/galaxyproject/galaxy/pull/17653>`_
* Code cleanups from ruff and pyupgrade by `@nsoranzo <https://github.com/nsoranzo>`_ in `#17654 <https://github.com/galaxyproject/galaxy/pull/17654>`_
* SQLAlchemy 2.0 by `@jdavcs <https://github.com/jdavcs>`_ in `#17778 <https://github.com/galaxyproject/galaxy/pull/17778>`_
* Add `email` notifications channel by `@davelopez <https://github.com/davelopez>`_ in `#17914 <https://github.com/galaxyproject/galaxy/pull/17914>`_
* Model typing and SA2.0 follow-up by `@jdavcs <https://github.com/jdavcs>`_ in `#17958 <https://github.com/galaxyproject/galaxy/pull/17958>`_
* Drop unused workflow controller methods by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17974 <https://github.com/galaxyproject/galaxy/pull/17974>`_
* Enable ``warn_unused_ignores`` mypy option by `@nsoranzo <https://github.com/nsoranzo>`_ in `#17991 <https://github.com/galaxyproject/galaxy/pull/17991>`_
* Add galaxy to user agent by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18003 <https://github.com/galaxyproject/galaxy/pull/18003>`_
* Consolidate Visualization container, avoid using default iframe by `@guerler <https://github.com/guerler>`_ in `#18016 <https://github.com/galaxyproject/galaxy/pull/18016>`_
* Add pagination support to Files Source plugins by `@davelopez <https://github.com/davelopez>`_ in `#18059 <https://github.com/galaxyproject/galaxy/pull/18059>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#18063 <https://github.com/galaxyproject/galaxy/pull/18063>`_
* Enable flake8-implicit-str-concat ruff rules by `@nsoranzo <https://github.com/nsoranzo>`_ in `#18067 <https://github.com/galaxyproject/galaxy/pull/18067>`_
* Change `InvocationsList` into a grid using `GridList` by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#18088 <https://github.com/galaxyproject/galaxy/pull/18088>`_
* Empower users to bring their own storage and file sources by `@jmchilton <https://github.com/jmchilton>`_ in `#18127 <https://github.com/galaxyproject/galaxy/pull/18127>`_
* Harden User Object Store and File Source Creation by `@jmchilton <https://github.com/jmchilton>`_ in `#18172 <https://github.com/galaxyproject/galaxy/pull/18172>`_
* Drop restriction to switch to immutable histories by `@davelopez <https://github.com/davelopez>`_ in `#18234 <https://github.com/galaxyproject/galaxy/pull/18234>`_
* More structured indexing for user data objects. by `@jmchilton <https://github.com/jmchilton>`_ in `#18291 <https://github.com/galaxyproject/galaxy/pull/18291>`_
* Allow running and editing workflows for specific versions by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#18378 <https://github.com/galaxyproject/galaxy/pull/18378>`_

=============
Other changes
=============

* Fix typing issue in reused variable by `@davelopez <https://github.com/davelopez>`_ in `#18344 <https://github.com/galaxyproject/galaxy/pull/18344>`_

-------------------
24.0.3 (2024-06-28)
-------------------


=========
Bug fixes
=========

* do not expand datasets that are known to be inaccessible by `@martenson <https://github.com/martenson>`_ in `#17818 <https://github.com/galaxyproject/galaxy/pull/17818>`_
* Raise exception if collection elements missing during download by `@jdavcs <https://github.com/jdavcs>`_ in `#18094 <https://github.com/galaxyproject/galaxy/pull/18094>`_
* Allow purge query param, deprecate purge body param by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18105 <https://github.com/galaxyproject/galaxy/pull/18105>`_
* Prevent anonymous and inactive users from running workflows by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#18192 <https://github.com/galaxyproject/galaxy/pull/18192>`_
* Fix `make all histories private` with immutable histories by `@davelopez <https://github.com/davelopez>`_ in `#18200 <https://github.com/galaxyproject/galaxy/pull/18200>`_
* Fix pca 3d rendering of tabular files and visualization error handling in general by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18211 <https://github.com/galaxyproject/galaxy/pull/18211>`_
* Check dataset state when attempting to acces dataset contents by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18214 <https://github.com/galaxyproject/galaxy/pull/18214>`_
* Restrict job_files access to jobs that are not terminal by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18217 <https://github.com/galaxyproject/galaxy/pull/18217>`_
* Raise appropriate exception if accessing deleted input file by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18223 <https://github.com/galaxyproject/galaxy/pull/18223>`_
* Fix element serialization for collections that aren't populated yet by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18235 <https://github.com/galaxyproject/galaxy/pull/18235>`_
* Skip new history creation if user is anonymous and login is required by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18319 <https://github.com/galaxyproject/galaxy/pull/18319>`_
* Fix users API serialization when listing users by `@davelopez <https://github.com/davelopez>`_ in `#18329 <https://github.com/galaxyproject/galaxy/pull/18329>`_
* Fix authentication error for anonymous users querying jobs by `@davelopez <https://github.com/davelopez>`_ in `#18333 <https://github.com/galaxyproject/galaxy/pull/18333>`_
* Do not copy purged outputs to object store by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18342 <https://github.com/galaxyproject/galaxy/pull/18342>`_
* Fix anonymous user job retrieval logic by `@davelopez <https://github.com/davelopez>`_ in `#18358 <https://github.com/galaxyproject/galaxy/pull/18358>`_
* Fix update group API payload model by `@davelopez <https://github.com/davelopez>`_ in `#18374 <https://github.com/galaxyproject/galaxy/pull/18374>`_
* Drop unnecessary escaping for workflow name and annotation by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18376 <https://github.com/galaxyproject/galaxy/pull/18376>`_

=============
Other changes
=============

* Decrease log level for expected visualization errors by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18229 <https://github.com/galaxyproject/galaxy/pull/18229>`_

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

* Fix tool version switch in editor by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17858 <https://github.com/galaxyproject/galaxy/pull/17858>`_
* Fix workflow run form failing on certain histories by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17869 <https://github.com/galaxyproject/galaxy/pull/17869>`_
* Ensure that offset and limit are never negative by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18044 <https://github.com/galaxyproject/galaxy/pull/18044>`_
* Fix history update time after bulk operation by `@davelopez <https://github.com/davelopez>`_ in `#18068 <https://github.com/galaxyproject/galaxy/pull/18068>`_

============
Enhancements
============

* Add middleware for logging start and end of request by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18046 <https://github.com/galaxyproject/galaxy/pull/18046>`_

-------------------
24.0.0 (2024-04-02)
-------------------


=========
Bug fixes
=========

* tus wants a json response from v2.0.0 by `@mira-miracoli <https://github.com/mira-miracoli>`_ in `#17246 <https://github.com/galaxyproject/galaxy/pull/17246>`_
* Fix quotas ID encoding by `@davelopez <https://github.com/davelopez>`_ in `#17335 <https://github.com/galaxyproject/galaxy/pull/17335>`_
* Fixes for flake8-bugbear 24.1.17 by `@nsoranzo <https://github.com/nsoranzo>`_ in `#17340 <https://github.com/galaxyproject/galaxy/pull/17340>`_
* Fix data_source and data_source_async bugs by `@wm75 <https://github.com/wm75>`_ in `#17422 <https://github.com/galaxyproject/galaxy/pull/17422>`_
* Only check access permissions in ``/api/{history_dataset_collection_id}/contents/{dataset_collection_id}`` by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#17444 <https://github.com/galaxyproject/galaxy/pull/17444>`_
* Associate default history with session when creating a new session by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17557 <https://github.com/galaxyproject/galaxy/pull/17557>`_
* Fix tool shed webapp by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17597 <https://github.com/galaxyproject/galaxy/pull/17597>`_
* Don't call ``get_or_create_default_history()`` twice for invalidated sessions by `@nsoranzo <https://github.com/nsoranzo>`_ in `#17613 <https://github.com/galaxyproject/galaxy/pull/17613>`_
* Fix tool panel workflow and favorites button bugs by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#17634 <https://github.com/galaxyproject/galaxy/pull/17634>`_
* Fix DataResult type by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17639 <https://github.com/galaxyproject/galaxy/pull/17639>`_
* Prevent 500 for anon /api/invocations by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17640 <https://github.com/galaxyproject/galaxy/pull/17640>`_
* Don't fail for anon /api/users request by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17645 <https://github.com/galaxyproject/galaxy/pull/17645>`_
* Limit new anon histories by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17657 <https://github.com/galaxyproject/galaxy/pull/17657>`_
* Fix histories API index_query serialization by `@davelopez <https://github.com/davelopez>`_ in `#17726 <https://github.com/galaxyproject/galaxy/pull/17726>`_
* Handle missing indexer for a dataset by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#17736 <https://github.com/galaxyproject/galaxy/pull/17736>`_
* Don't require history to calculate anon disk usage by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17765 <https://github.com/galaxyproject/galaxy/pull/17765>`_
* Fix anon user values again by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17772 <https://github.com/galaxyproject/galaxy/pull/17772>`_
* Fix new default history creation when in remote or single user mode by `@dannon <https://github.com/dannon>`_ in `#17796 <https://github.com/galaxyproject/galaxy/pull/17796>`_
* Return published histories first in display_by_username_and_slug by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17808 <https://github.com/galaxyproject/galaxy/pull/17808>`_
* Fix archived histories mixing with active in histories list by `@davelopez <https://github.com/davelopez>`_ in `#17856 <https://github.com/galaxyproject/galaxy/pull/17856>`_

============
Enhancements
============

* New Workflow List and Card View by `@itisAliRH <https://github.com/itisAliRH>`_ in `#16607 <https://github.com/galaxyproject/galaxy/pull/16607>`_
* port invocation API to fastapi by `@martenson <https://github.com/martenson>`_ in `#16707 <https://github.com/galaxyproject/galaxy/pull/16707>`_
* Python 3.8 as minimum by `@mr-c <https://github.com/mr-c>`_ in `#16954 <https://github.com/galaxyproject/galaxy/pull/16954>`_
* Support for OIDC API Auth and OIDC integration tests by `@nuwang <https://github.com/nuwang>`_ in `#16977 <https://github.com/galaxyproject/galaxy/pull/16977>`_
* Toward declarative help for Galaxy markdown directives. by `@jmchilton <https://github.com/jmchilton>`_ in `#16979 <https://github.com/galaxyproject/galaxy/pull/16979>`_
* Vueify Admin User Grid by `@guerler <https://github.com/guerler>`_ in `#17030 <https://github.com/galaxyproject/galaxy/pull/17030>`_
* Remove web framework dependency from tools by `@davelopez <https://github.com/davelopez>`_ in `#17058 <https://github.com/galaxyproject/galaxy/pull/17058>`_
* Vueify Admin Roles Grid by `@guerler <https://github.com/guerler>`_ in `#17118 <https://github.com/galaxyproject/galaxy/pull/17118>`_
* SA2.0 updates: handling "object is being merged into a Session along the backref cascade path" by `@jdavcs <https://github.com/jdavcs>`_ in `#17122 <https://github.com/galaxyproject/galaxy/pull/17122>`_
* Vueify Admin Groups Grid by `@guerler <https://github.com/guerler>`_ in `#17126 <https://github.com/galaxyproject/galaxy/pull/17126>`_
* Towards SQLAlchemy 2.0: fix last cases of RemovedIn20Warning by `@jdavcs <https://github.com/jdavcs>`_ in `#17132 <https://github.com/galaxyproject/galaxy/pull/17132>`_
* Vueify Admin Forms and Quota grids by `@guerler <https://github.com/guerler>`_ in `#17141 <https://github.com/galaxyproject/galaxy/pull/17141>`_
* Migrate dataset extra files store to Pinia by `@davelopez <https://github.com/davelopez>`_ in `#17145 <https://github.com/galaxyproject/galaxy/pull/17145>`_
* Create pydantic model for the return of show operation -  get: `/api/jobs/{job_id}`  by `@heisner-tillman <https://github.com/heisner-tillman>`_ in `#17153 <https://github.com/galaxyproject/galaxy/pull/17153>`_
* Remove legacy tool versions list from admin panel by `@guerler <https://github.com/guerler>`_ in `#17155 <https://github.com/galaxyproject/galaxy/pull/17155>`_
* Don't require admin user to list ``/api/tool_data`` by `@jozh2008 <https://github.com/jozh2008>`_ in `#17161 <https://github.com/galaxyproject/galaxy/pull/17161>`_
* Drop fastapi-utils.InferringRouter in favor of fastapi.APIRouter  by `@jdavcs <https://github.com/jdavcs>`_ in `#17184 <https://github.com/galaxyproject/galaxy/pull/17184>`_
* Vendorize fastapi-utls.cbv by `@jdavcs <https://github.com/jdavcs>`_ in `#17205 <https://github.com/galaxyproject/galaxy/pull/17205>`_
* Vueifiy History Grids by `@guerler <https://github.com/guerler>`_ in `#17219 <https://github.com/galaxyproject/galaxy/pull/17219>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#17235 <https://github.com/galaxyproject/galaxy/pull/17235>`_
* Refactor two of the missing invocation routes to FastAPI by `@heisner-tillman <https://github.com/heisner-tillman>`_ in `#17237 <https://github.com/galaxyproject/galaxy/pull/17237>`_
* Allow job files to consume TUS uploads by `@jmchilton <https://github.com/jmchilton>`_ in `#17242 <https://github.com/galaxyproject/galaxy/pull/17242>`_
* Migrate models to pydantic 2 by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17262 <https://github.com/galaxyproject/galaxy/pull/17262>`_
* Adds delete, purge and undelete batch operations to History Grid by `@guerler <https://github.com/guerler>`_ in `#17282 <https://github.com/galaxyproject/galaxy/pull/17282>`_
* Fix any type for tool_data_file_path by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17293 <https://github.com/galaxyproject/galaxy/pull/17293>`_
* API endpoint that allows "changing" the objectstore for "safe" scenarios.  by `@jmchilton <https://github.com/jmchilton>`_ in `#17329 <https://github.com/galaxyproject/galaxy/pull/17329>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#17333 <https://github.com/galaxyproject/galaxy/pull/17333>`_
* Combines legacy qv-pattern and advanced filter pattern in history index endpoint by `@guerler <https://github.com/guerler>`_ in `#17368 <https://github.com/galaxyproject/galaxy/pull/17368>`_
* Update to black 2024 stable style by `@nsoranzo <https://github.com/nsoranzo>`_ in `#17391 <https://github.com/galaxyproject/galaxy/pull/17391>`_
* Replaces Trackster Grids with Data Dialog, Removes Phyloviz, Circster and Sweepster by `@guerler <https://github.com/guerler>`_ in `#17415 <https://github.com/galaxyproject/galaxy/pull/17415>`_
* Removes outdated Grid controller and backbone modules by `@guerler <https://github.com/guerler>`_ in `#17434 <https://github.com/galaxyproject/galaxy/pull/17434>`_
* Allow using tool data bundles as inputs to reference data select parameters by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17435 <https://github.com/galaxyproject/galaxy/pull/17435>`_
* Modernize bits and pieces of storage display by `@jmchilton <https://github.com/jmchilton>`_ in `#17436 <https://github.com/galaxyproject/galaxy/pull/17436>`_
* UI for "relocating" a dataset to a new object store (when safe) by `@jmchilton <https://github.com/jmchilton>`_ in `#17437 <https://github.com/galaxyproject/galaxy/pull/17437>`_
* Refactor Workflow API routes - Part 1 by `@heisner-tillman <https://github.com/heisner-tillman>`_ in `#17463 <https://github.com/galaxyproject/galaxy/pull/17463>`_
* Consolidate resource grids into tab views by `@guerler <https://github.com/guerler>`_ in `#17487 <https://github.com/galaxyproject/galaxy/pull/17487>`_
* Display workflow invocation counts. by `@jmchilton <https://github.com/jmchilton>`_ in `#17488 <https://github.com/galaxyproject/galaxy/pull/17488>`_
* Removes legacy history xml makos by `@guerler <https://github.com/guerler>`_ in `#17505 <https://github.com/galaxyproject/galaxy/pull/17505>`_
* add encode ID API endpoint by `@mira-miracoli <https://github.com/mira-miracoli>`_ in `#17510 <https://github.com/galaxyproject/galaxy/pull/17510>`_
* Fixing data_source tools and incrementing tool profile by `@wm75 <https://github.com/wm75>`_ in `#17515 <https://github.com/galaxyproject/galaxy/pull/17515>`_
* Filter out subworkflow invocations by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17558 <https://github.com/galaxyproject/galaxy/pull/17558>`_
* Links to individual invocations. by `@jmchilton <https://github.com/jmchilton>`_ in `#17566 <https://github.com/galaxyproject/galaxy/pull/17566>`_
* Restore histories API behavior for `keys` query parameter by `@davelopez <https://github.com/davelopez>`_ in `#17779 <https://github.com/galaxyproject/galaxy/pull/17779>`_
* Fix datasets API custom keys encoding by `@davelopez <https://github.com/davelopez>`_ in `#17793 <https://github.com/galaxyproject/galaxy/pull/17793>`_

-------------------
23.2.1 (2024-02-21)
-------------------


=========
Bug fixes
=========

* Rename to_dict to populate in FormDefintion to fix bug by `@jdavcs <https://github.com/jdavcs>`_ in `#16553 <https://github.com/galaxyproject/galaxy/pull/16553>`_
* Fix: serialize `tool_shed_urls` directly from the API by `@davelopez <https://github.com/davelopez>`_ in `#16561 <https://github.com/galaxyproject/galaxy/pull/16561>`_
* chore: fix typos by `@afuetterer <https://github.com/afuetterer>`_ in `#16851 <https://github.com/galaxyproject/galaxy/pull/16851>`_
* Restore ToolsApi and create new api route for new panel structure by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#16872 <https://github.com/galaxyproject/galaxy/pull/16872>`_
* Ruff and flake8 fixes by `@nsoranzo <https://github.com/nsoranzo>`_ in `#16884 <https://github.com/galaxyproject/galaxy/pull/16884>`_
* Make payload optional again for create tag API by `@nsoranzo <https://github.com/nsoranzo>`_ in `#17144 <https://github.com/galaxyproject/galaxy/pull/17144>`_
* Fix Display Application link generation by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17227 <https://github.com/galaxyproject/galaxy/pull/17227>`_
* Display application fixes and tests by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17233 <https://github.com/galaxyproject/galaxy/pull/17233>`_
* Respect ``upstream_gzip`` setting  when streaming dataset collection archive by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17400 <https://github.com/galaxyproject/galaxy/pull/17400>`_
* Fix history bulk operations menu conditions by `@davelopez <https://github.com/davelopez>`_ in `#17433 <https://github.com/galaxyproject/galaxy/pull/17433>`_
* Only check access permissions in `/api/{history_dataset_collection_id}/contents/{dataset_collection_id}` by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17459 <https://github.com/galaxyproject/galaxy/pull/17459>`_
* Set metadata states on dataset association, not dataset by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17474 <https://github.com/galaxyproject/galaxy/pull/17474>`_
* Provide working routes.url_for every ASGI request by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17497 <https://github.com/galaxyproject/galaxy/pull/17497>`_

============
Enhancements
============

* Tool Shed 2.0 by `@jmchilton <https://github.com/jmchilton>`_ in `#15639 <https://github.com/galaxyproject/galaxy/pull/15639>`_
* Limit number of celery task executions per second per user by `@claudiofr <https://github.com/claudiofr>`_ in `#16232 <https://github.com/galaxyproject/galaxy/pull/16232>`_
* Delete non-terminal jobs and subworkflow invocations when cancelling invocation by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16252 <https://github.com/galaxyproject/galaxy/pull/16252>`_
* Towards SQLAlchemy 2.0 (upgrades to SA Core usage) by `@jdavcs <https://github.com/jdavcs>`_ in `#16264 <https://github.com/galaxyproject/galaxy/pull/16264>`_
* Notifications admin panel by `@itisAliRH <https://github.com/itisAliRH>`_ in `#16278 <https://github.com/galaxyproject/galaxy/pull/16278>`_
* Migrate cloud API to Fast API by `@heisner-tillman <https://github.com/heisner-tillman>`_ in `#16296 <https://github.com/galaxyproject/galaxy/pull/16296>`_
* Drop (admin only) userskeys controller by `@dannon <https://github.com/dannon>`_ in `#16318 <https://github.com/galaxyproject/galaxy/pull/16318>`_
* Migrate a part of the users API to Fast API by `@heisner-tillman <https://github.com/heisner-tillman>`_ in `#16341 <https://github.com/galaxyproject/galaxy/pull/16341>`_
* Add Invenio RDM repository integration by `@davelopez <https://github.com/davelopez>`_ in `#16381 <https://github.com/galaxyproject/galaxy/pull/16381>`_
* Refactor FilesDialog + Remote Files API schema improvements by `@davelopez <https://github.com/davelopez>`_ in `#16420 <https://github.com/galaxyproject/galaxy/pull/16420>`_
* SQLAlchemy 2.0 upgrades to ORM usage in /lib by `@jdavcs <https://github.com/jdavcs>`_ in `#16434 <https://github.com/galaxyproject/galaxy/pull/16434>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#16436 <https://github.com/galaxyproject/galaxy/pull/16436>`_
* Published Workflow Sharing Page Overhaul by `@ElectronicBlueberry <https://github.com/ElectronicBlueberry>`_ in `#16510 <https://github.com/galaxyproject/galaxy/pull/16510>`_
* Tweak tool memory use and optimize shared memory when using preload by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16536 <https://github.com/galaxyproject/galaxy/pull/16536>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#16577 <https://github.com/galaxyproject/galaxy/pull/16577>`_
* Workflow Comments 💬 by `@ElectronicBlueberry <https://github.com/ElectronicBlueberry>`_ in `#16612 <https://github.com/galaxyproject/galaxy/pull/16612>`_
* Galaxy Markdown - add workflow image and license to Galaxy markdown. by `@jmchilton <https://github.com/jmchilton>`_ in `#16672 <https://github.com/galaxyproject/galaxy/pull/16672>`_
* Implement instance URLs in Galaxy markdown. by `@jmchilton <https://github.com/jmchilton>`_ in `#16675 <https://github.com/galaxyproject/galaxy/pull/16675>`_
* Enhance task monitor composable by `@davelopez <https://github.com/davelopez>`_ in `#16695 <https://github.com/galaxyproject/galaxy/pull/16695>`_
* SQLAlchemy 2.0 upgrades (part 2) by `@jdavcs <https://github.com/jdavcs>`_ in `#16724 <https://github.com/galaxyproject/galaxy/pull/16724>`_
* Migrate `collection elements` store to Pinia by `@davelopez <https://github.com/davelopez>`_ in `#16725 <https://github.com/galaxyproject/galaxy/pull/16725>`_
* Refactor Tool Panel views structures and combine ToolBox and ToolBoxWorkflow into one component by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#16739 <https://github.com/galaxyproject/galaxy/pull/16739>`_
* Don't copy collection elements in ``test_dataset_collection_hide_originals`` by `@nsoranzo <https://github.com/nsoranzo>`_ in `#16747 <https://github.com/galaxyproject/galaxy/pull/16747>`_
* Drop legacy server-side search by `@jdavcs <https://github.com/jdavcs>`_ in `#16755 <https://github.com/galaxyproject/galaxy/pull/16755>`_
* Migrate a part of the jobs API to Fast API by `@heisner-tillman <https://github.com/heisner-tillman>`_ in `#16778 <https://github.com/galaxyproject/galaxy/pull/16778>`_
* Replace file_name property with get_file_name function by `@SergeyYakubov <https://github.com/SergeyYakubov>`_ in `#16783 <https://github.com/galaxyproject/galaxy/pull/16783>`_
* Updated path-based interactive tools with entry point path injection, support for ITs with relative links, shortened URLs, doc and config updates including Podman job_conf by `@sveinugu <https://github.com/sveinugu>`_ in `#16795 <https://github.com/galaxyproject/galaxy/pull/16795>`_
* Galaxy help forum integration by `@ElectronicBlueberry <https://github.com/ElectronicBlueberry>`_ in `#16798 <https://github.com/galaxyproject/galaxy/pull/16798>`_
* SQLAlchemy 2.0 upgrades (part 4) by `@jdavcs <https://github.com/jdavcs>`_ in `#16852 <https://github.com/galaxyproject/galaxy/pull/16852>`_
* Vueify Visualizations Grid by `@guerler <https://github.com/guerler>`_ in `#16892 <https://github.com/galaxyproject/galaxy/pull/16892>`_
* Change `api/tool_panel` to `api/tool_panels/...` by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#16928 <https://github.com/galaxyproject/galaxy/pull/16928>`_
* Remove "Create Workflow" form and allow workflow creation in editor by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#16938 <https://github.com/galaxyproject/galaxy/pull/16938>`_
* Update API tool_panels route conditions by `@dannon <https://github.com/dannon>`_ in `#16991 <https://github.com/galaxyproject/galaxy/pull/16991>`_
* Fix invocation report to target correct workflow version. by `@jmchilton <https://github.com/jmchilton>`_ in `#17008 <https://github.com/galaxyproject/galaxy/pull/17008>`_
* Upgrade job manager's index_query method to SA2.0 by `@jdavcs <https://github.com/jdavcs>`_ in `#17020 <https://github.com/galaxyproject/galaxy/pull/17020>`_
* Require name for workflows on save, set default to Unnamed Workflow by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#17038 <https://github.com/galaxyproject/galaxy/pull/17038>`_
* Migrate groups API to fastAPI by `@arash77 <https://github.com/arash77>`_ in `#17051 <https://github.com/galaxyproject/galaxy/pull/17051>`_
* Migrate ItemTags API to FastAPI by `@arash77 <https://github.com/arash77>`_ in `#17064 <https://github.com/galaxyproject/galaxy/pull/17064>`_

=============
Other changes
=============

* Merge 23.1 into dev by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16534 <https://github.com/galaxyproject/galaxy/pull/16534>`_
* Fix succces typo by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17481 <https://github.com/galaxyproject/galaxy/pull/17481>`_

-------------------
23.1.4 (2024-01-04)
-------------------


=========
Bug fixes
=========

* Properly clear session on OIDC logout by `@guerler <https://github.com/guerler>`_ in `#17120 <https://github.com/galaxyproject/galaxy/pull/17120>`_

-------------------
23.1.3 (2023-12-01)
-------------------


=========
Bug fixes
=========

* Add missing optional description field, fixes ephemeris data library example by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17116 <https://github.com/galaxyproject/galaxy/pull/17116>`_

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

* Fix incorrect ASGI request host by `@davelopez <https://github.com/davelopez>`_ in `#16574 <https://github.com/galaxyproject/galaxy/pull/16574>`_
* Allow the legacy DELETE dataset endpoint to accept any string for the history_id by `@assuntad23 <https://github.com/assuntad23>`_ in `#16593 <https://github.com/galaxyproject/galaxy/pull/16593>`_

-------------------
23.0.5 (2023-07-29)
-------------------


=========
Bug fixes
=========

* Fix active step display in workflow editor side panel by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16364 <https://github.com/galaxyproject/galaxy/pull/16364>`_

-------------------
23.0.4 (2023-06-30)
-------------------


=========
Bug fixes
=========

* Fix folder access for anonymous user by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16330 <https://github.com/galaxyproject/galaxy/pull/16330>`_

-------------------
23.0.3 (2023-06-26)
-------------------


=========
Bug fixes
=========

* Fix converting Enum value to str for Python 3.11 by `@nsoranzo <https://github.com/nsoranzo>`_ in `#16284 <https://github.com/galaxyproject/galaxy/pull/16284>`_

============
Enhancements
============

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

* Display DCE in job parameter component, allow rerunning with DCE input by `@mvdbeek <https://github.com/mvdbeek>`_ in `#15744 <https://github.com/galaxyproject/galaxy/pull/15744>`_
* Various fixes to path prefix handling by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16033 <https://github.com/galaxyproject/galaxy/pull/16033>`_
* Fix dataype_change not updating HDCA update_time by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16099 <https://github.com/galaxyproject/galaxy/pull/16099>`_
* Ignore invalid query params in display_by_username_and_slug by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16117 <https://github.com/galaxyproject/galaxy/pull/16117>`_

-------------------
20.5.0 (2020-07-04)
-------------------

* First release from the 20.05 branch of Galaxy.
