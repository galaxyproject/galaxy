History
-------

.. to_doc

---------
25.1.dev0
---------



-------------------
25.0.1 (2025-06-20)
-------------------


=========
Bug fixes
=========

* Do not expose user info to non authenticated users by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#20524 <https://github.com/galaxyproject/galaxy/pull/20524>`_

-------------------
25.0.0 (2025-06-18)
-------------------


=========
Bug fixes
=========

* Alternative `format_source` fix by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19395 <https://github.com/galaxyproject/galaxy/pull/19395>`_
* Fix wrong id in test_combined_mapping_and_subcollection_mapping by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19481 <https://github.com/galaxyproject/galaxy/pull/19481>`_
* More fixes to `FormData` drag and drop and typing by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#19900 <https://github.com/galaxyproject/galaxy/pull/19900>`_
* Fix ownership check in history contents update route by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19969 <https://github.com/galaxyproject/galaxy/pull/19969>`_
* Fix certain cases of collection parameter handling during workflow execution. by `@jmchilton <https://github.com/jmchilton>`_ in `#20152 <https://github.com/galaxyproject/galaxy/pull/20152>`_
* Increase proxy API robustness by validating URL before use by `@davelopez <https://github.com/davelopez>`_ in `#20311 <https://github.com/galaxyproject/galaxy/pull/20311>`_
* Add test for workflow instance download fix by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#20326 <https://github.com/galaxyproject/galaxy/pull/20326>`_
* Fix toolshed-installed tool icons by `@dannon <https://github.com/dannon>`_ in `#20399 <https://github.com/galaxyproject/galaxy/pull/20399>`_
* Fix job rerun with tool version change by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20417 <https://github.com/galaxyproject/galaxy/pull/20417>`_
* Fix copying of job metrics for cached jobs by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20436 <https://github.com/galaxyproject/galaxy/pull/20436>`_

============
Enhancements
============

* Calculate hash for new non-deferred datasets when finishing a job by `@nsoranzo <https://github.com/nsoranzo>`_ in `#19181 <https://github.com/galaxyproject/galaxy/pull/19181>`_
* Fix UP031 errors - Part 1 by `@nsoranzo <https://github.com/nsoranzo>`_ in `#19194 <https://github.com/galaxyproject/galaxy/pull/19194>`_
* Empower Users to Build More Kinds of Collections, More Intelligently by `@jmchilton <https://github.com/jmchilton>`_ in `#19377 <https://github.com/galaxyproject/galaxy/pull/19377>`_
* Add User-Defined Tools by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19434 <https://github.com/galaxyproject/galaxy/pull/19434>`_
* Add test that verifies workflow source_metadata is preserved on landing claim by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19454 <https://github.com/galaxyproject/galaxy/pull/19454>`_
* Expand workflow metadata for readme.  by `@jmchilton <https://github.com/jmchilton>`_ in `#19591 <https://github.com/galaxyproject/galaxy/pull/19591>`_
* Update test_create_dataset_in_subfolder to check for the dataset presence by `@davelopez <https://github.com/davelopez>`_ in `#19660 <https://github.com/galaxyproject/galaxy/pull/19660>`_
* Relax job status check in test_delete_user_cancel_all_jobs by `@davelopez <https://github.com/davelopez>`_ in `#19661 <https://github.com/galaxyproject/galaxy/pull/19661>`_
* Drop support for Python 3.8 by `@nsoranzo <https://github.com/nsoranzo>`_ in `#19685 <https://github.com/galaxyproject/galaxy/pull/19685>`_
* Improved simplicity and isolation in transiently failing test. by `@jmchilton <https://github.com/jmchilton>`_ in `#19709 <https://github.com/galaxyproject/galaxy/pull/19709>`_
* Preserve workflow labels in final invocation reports by `@guerler <https://github.com/guerler>`_ in `#19721 <https://github.com/galaxyproject/galaxy/pull/19721>`_
* Migrate Page editing controller endpoint to API by `@guerler <https://github.com/guerler>`_ in `#19923 <https://github.com/galaxyproject/galaxy/pull/19923>`_
* Job cache allow different names when possible by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19962 <https://github.com/galaxyproject/galaxy/pull/19962>`_
* Implement dataset collection support in workflow landing requests by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20004 <https://github.com/galaxyproject/galaxy/pull/20004>`_
* Add DOI to workflow metadata by `@jdavcs <https://github.com/jdavcs>`_ in `#20033 <https://github.com/galaxyproject/galaxy/pull/20033>`_
* Add ZIP explorer to import individual files from local or remote ZIP archives by `@davelopez <https://github.com/davelopez>`_ in `#20054 <https://github.com/galaxyproject/galaxy/pull/20054>`_
* Add specific datatypes for Cytoscape and Kepler.gl by `@guerler <https://github.com/guerler>`_ in `#20117 <https://github.com/galaxyproject/galaxy/pull/20117>`_
* Yaml parser fixes and improvements (part 1) by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20158 <https://github.com/galaxyproject/galaxy/pull/20158>`_
* Improve performance of job cache query by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20319 <https://github.com/galaxyproject/galaxy/pull/20319>`_
* Enable retrieving contents from extra file paths when request contains leading `/` by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20336 <https://github.com/galaxyproject/galaxy/pull/20336>`_
* Add ``/api/datasets/{dataset_id}/extra_files/raw/{filename:path}`` by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20468 <https://github.com/galaxyproject/galaxy/pull/20468>`_

=============
Other changes
=============

* Fix copying job output from discovered outputs by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19999 <https://github.com/galaxyproject/galaxy/pull/19999>`_

-------------------
24.2.4 (2025-06-17)
-------------------


=========
Bug fixes
=========

* Skip ``data_meta`` filter in run form by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19895 <https://github.com/galaxyproject/galaxy/pull/19895>`_
* Restrict job cache to terminal jobs (and other fixes) by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19978 <https://github.com/galaxyproject/galaxy/pull/19978>`_
* Job cache backports by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20078 <https://github.com/galaxyproject/galaxy/pull/20078>`_
* Skip ``param_value`` filter if ref value is runtime value by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20144 <https://github.com/galaxyproject/galaxy/pull/20144>`_

-------------------
24.2.3 (2025-03-16)
-------------------

No recorded changes since last release

-------------------
24.2.2 (2025-03-08)
-------------------


=========
Bug fixes
=========

* Allow tool state changes in refactor actions by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19730 <https://github.com/galaxyproject/galaxy/pull/19730>`_

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

* Fix tag processing in library upload by `@davelopez <https://github.com/davelopez>`_ in `#18714 <https://github.com/galaxyproject/galaxy/pull/18714>`_
* Fix issue with generating slug for sharing by `@arash77 <https://github.com/arash77>`_ in `#18986 <https://github.com/galaxyproject/galaxy/pull/18986>`_
* Fix numerous issues with tool input format "21.01" by `@jmchilton <https://github.com/jmchilton>`_ in `#19030 <https://github.com/galaxyproject/galaxy/pull/19030>`_
* Record implicitly converted dataset as input dataset by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19301 <https://github.com/galaxyproject/galaxy/pull/19301>`_
* Expression tool format source backport by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19466 <https://github.com/galaxyproject/galaxy/pull/19466>`_
* Fail with error message when submitting invalid request by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19489 <https://github.com/galaxyproject/galaxy/pull/19489>`_
* Fix deleting lddas in batch by `@davelopez <https://github.com/davelopez>`_ in `#19506 <https://github.com/galaxyproject/galaxy/pull/19506>`_
* Fix ``test_storage_show`` API test by `@nsoranzo <https://github.com/nsoranzo>`_ in `#19522 <https://github.com/galaxyproject/galaxy/pull/19522>`_
* Fix error message when subworkflow input connection missing by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19526 <https://github.com/galaxyproject/galaxy/pull/19526>`_
* Fix admin cancel job message not being displayed to the user by `@davelopez <https://github.com/davelopez>`_ in `#19537 <https://github.com/galaxyproject/galaxy/pull/19537>`_

============
Enhancements
============

* Improve usability of Directory datatype by `@wm75 <https://github.com/wm75>`_ in `#17614 <https://github.com/galaxyproject/galaxy/pull/17614>`_
* Implement Declarative Testing for Workflow Behaviors by `@jmchilton <https://github.com/jmchilton>`_ in `#18542 <https://github.com/galaxyproject/galaxy/pull/18542>`_
* More tool test typing. by `@jmchilton <https://github.com/jmchilton>`_ in `#18590 <https://github.com/galaxyproject/galaxy/pull/18590>`_
* Better Typing for Tool Execution Plumbing by `@jmchilton <https://github.com/jmchilton>`_ in `#18626 <https://github.com/galaxyproject/galaxy/pull/18626>`_
* Parameter Model Improvements by `@jmchilton <https://github.com/jmchilton>`_ in `#18641 <https://github.com/galaxyproject/galaxy/pull/18641>`_
* Another round of parameter model improvements. by `@jmchilton <https://github.com/jmchilton>`_ in `#18673 <https://github.com/galaxyproject/galaxy/pull/18673>`_
* Allow access to invocation via shared or published history by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18707 <https://github.com/galaxyproject/galaxy/pull/18707>`_
* Migrate Visualizations API to FastAPI by `@arash77 <https://github.com/arash77>`_ in `#18721 <https://github.com/galaxyproject/galaxy/pull/18721>`_
* Refactor ``LibraryDatasetsManager`` and fix type annotation issue by `@nsoranzo <https://github.com/nsoranzo>`_ in `#18773 <https://github.com/galaxyproject/galaxy/pull/18773>`_
* Backend handling of setting user-role, user-group, and group-role associations by `@jdavcs <https://github.com/jdavcs>`_ in `#18777 <https://github.com/galaxyproject/galaxy/pull/18777>`_
* Workflow Landing Requests by `@jmchilton <https://github.com/jmchilton>`_ in `#18807 <https://github.com/galaxyproject/galaxy/pull/18807>`_
* Migrate Library Contents API to FastAPI by `@arash77 <https://github.com/arash77>`_ in `#18838 <https://github.com/galaxyproject/galaxy/pull/18838>`_
* Implement Pydantic model for workflow test format.  by `@jmchilton <https://github.com/jmchilton>`_ in `#18884 <https://github.com/galaxyproject/galaxy/pull/18884>`_
* Decouple user email from role name by `@jdavcs <https://github.com/jdavcs>`_ in `#18966 <https://github.com/galaxyproject/galaxy/pull/18966>`_
* More concise, readable tool execution testing. by `@jmchilton <https://github.com/jmchilton>`_ in `#18977 <https://github.com/galaxyproject/galaxy/pull/18977>`_
* Workflow landing improvements by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18979 <https://github.com/galaxyproject/galaxy/pull/18979>`_
* Allow recovering a normalized version of workflow request state from API by `@jmchilton <https://github.com/jmchilton>`_ in `#18985 <https://github.com/galaxyproject/galaxy/pull/18985>`_
* Do not skip CI tests on missing tools. by `@jmchilton <https://github.com/jmchilton>`_ in `#19002 <https://github.com/galaxyproject/galaxy/pull/19002>`_
* A variety of improvements around tool parameter modeling (second try) by `@jmchilton <https://github.com/jmchilton>`_ in `#19027 <https://github.com/galaxyproject/galaxy/pull/19027>`_
* Add job metrics per invocation by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19048 <https://github.com/galaxyproject/galaxy/pull/19048>`_
* Move TRS import into WorkflowContentManager by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19070 <https://github.com/galaxyproject/galaxy/pull/19070>`_
* Allow deferred datasets to behave as URIs by `@davelopez <https://github.com/davelopez>`_ in `#19077 <https://github.com/galaxyproject/galaxy/pull/19077>`_
* Implement workflow parameter validators. by `@jmchilton <https://github.com/jmchilton>`_ in `#19092 <https://github.com/galaxyproject/galaxy/pull/19092>`_
* Access public history in job cache / job search by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19108 <https://github.com/galaxyproject/galaxy/pull/19108>`_
* Always validate hashes when provided by `@nsoranzo <https://github.com/nsoranzo>`_ in `#19110 <https://github.com/galaxyproject/galaxy/pull/19110>`_
* Enable specifying dataset hash in test jobs by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19113 <https://github.com/galaxyproject/galaxy/pull/19113>`_
* Enhance UTF-8 support for filename handling in downloads by `@arash77 <https://github.com/arash77>`_ in `#19161 <https://github.com/galaxyproject/galaxy/pull/19161>`_
* Fix default value handling for parameters connected to required parameters by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19219 <https://github.com/galaxyproject/galaxy/pull/19219>`_

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
* Prevent job submission if input collection element is deleted by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18517 <https://github.com/galaxyproject/galaxy/pull/18517>`_
* Fix view parameter type in Job index API by `@davelopez <https://github.com/davelopez>`_ in `#18521 <https://github.com/galaxyproject/galaxy/pull/18521>`_
* Fix map over calculation for runtime inputs  by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18535 <https://github.com/galaxyproject/galaxy/pull/18535>`_
* Fix Archive header encoding by `@arash77 <https://github.com/arash77>`_ in `#18583 <https://github.com/galaxyproject/galaxy/pull/18583>`_
* Don't set file size to zero by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18653 <https://github.com/galaxyproject/galaxy/pull/18653>`_
* Fix extract workflow from history when implicit collection has no jobs by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18661 <https://github.com/galaxyproject/galaxy/pull/18661>`_
* Fix change datatype PJA on expression tool data outputs by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18691 <https://github.com/galaxyproject/galaxy/pull/18691>`_
* Fix subworkflow scheduling for delayed subworkflow steps connected to data inputs by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18731 <https://github.com/galaxyproject/galaxy/pull/18731>`_
* Catch and display exceptions when importing malformatted yaml workflows by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18734 <https://github.com/galaxyproject/galaxy/pull/18734>`_
* Fix infinitely delayed workflow scheduling if skipped step creates HDCA by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18751 <https://github.com/galaxyproject/galaxy/pull/18751>`_
* Fix copying workflow with subworkflow step for step that you own by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18802 <https://github.com/galaxyproject/galaxy/pull/18802>`_
* Raise MessageException instead of assertions on rerun problems by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18858 <https://github.com/galaxyproject/galaxy/pull/18858>`_
* Fix data_column ref to nested collection by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18875 <https://github.com/galaxyproject/galaxy/pull/18875>`_
* Access tool data table filters in workflow building mode by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18900 <https://github.com/galaxyproject/galaxy/pull/18900>`_

-------------------
24.1.3 (2024-10-25)
-------------------


=========
Bug fixes
=========

* Fix subwofklow tags serialization type by `@arash77 <https://github.com/arash77>`_ in `#18456 <https://github.com/galaxyproject/galaxy/pull/18456>`_
* Prevent job submission if input collection element is deleted by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18517 <https://github.com/galaxyproject/galaxy/pull/18517>`_
* Fix view parameter type in Job index API by `@davelopez <https://github.com/davelopez>`_ in `#18521 <https://github.com/galaxyproject/galaxy/pull/18521>`_
* Fix map over calculation for runtime inputs  by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18535 <https://github.com/galaxyproject/galaxy/pull/18535>`_
* Fix Archive header encoding by `@arash77 <https://github.com/arash77>`_ in `#18583 <https://github.com/galaxyproject/galaxy/pull/18583>`_
* Don't set file size to zero by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18653 <https://github.com/galaxyproject/galaxy/pull/18653>`_
* Fix extract workflow from history when implicit collection has no jobs by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18661 <https://github.com/galaxyproject/galaxy/pull/18661>`_
* Fix change datatype PJA on expression tool data outputs by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18691 <https://github.com/galaxyproject/galaxy/pull/18691>`_
* Fix subworkflow scheduling for delayed subworkflow steps connected to data inputs by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18731 <https://github.com/galaxyproject/galaxy/pull/18731>`_
* Catch and display exceptions when importing malformatted yaml workflows by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18734 <https://github.com/galaxyproject/galaxy/pull/18734>`_
* Fix infinitely delayed workflow scheduling if skipped step creates HDCA by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18751 <https://github.com/galaxyproject/galaxy/pull/18751>`_
* Fix copying workflow with subworkflow step for step that you own by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18802 <https://github.com/galaxyproject/galaxy/pull/18802>`_
* Raise MessageException instead of assertions on rerun problems by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18858 <https://github.com/galaxyproject/galaxy/pull/18858>`_
* Fix data_column ref to nested collection by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18875 <https://github.com/galaxyproject/galaxy/pull/18875>`_
* Access tool data table filters in workflow building mode by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18900 <https://github.com/galaxyproject/galaxy/pull/18900>`_

-------------------
24.1.2 (2024-09-25)
-------------------


=========
Bug fixes
=========

* Prevent job submission if input collection element is deleted by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18517 <https://github.com/galaxyproject/galaxy/pull/18517>`_
* Fix view parameter type in Job index API by `@davelopez <https://github.com/davelopez>`_ in `#18521 <https://github.com/galaxyproject/galaxy/pull/18521>`_
* Fix map over calculation for runtime inputs  by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18535 <https://github.com/galaxyproject/galaxy/pull/18535>`_
* Fix Archive header encoding by `@arash77 <https://github.com/arash77>`_ in `#18583 <https://github.com/galaxyproject/galaxy/pull/18583>`_
* Don't set file size to zero by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18653 <https://github.com/galaxyproject/galaxy/pull/18653>`_
* Fix extract workflow from history when implicit collection has no jobs by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18661 <https://github.com/galaxyproject/galaxy/pull/18661>`_
* Fix change datatype PJA on expression tool data outputs by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18691 <https://github.com/galaxyproject/galaxy/pull/18691>`_
* Fix subworkflow scheduling for delayed subworkflow steps connected to data inputs by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18731 <https://github.com/galaxyproject/galaxy/pull/18731>`_
* Catch and display exceptions when importing malformatted yaml workflows by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18734 <https://github.com/galaxyproject/galaxy/pull/18734>`_
* Fix infinitely delayed workflow scheduling if skipped step creates HDCA by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18751 <https://github.com/galaxyproject/galaxy/pull/18751>`_
* Fix copying workflow with subworkflow step for step that you own by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18802 <https://github.com/galaxyproject/galaxy/pull/18802>`_
* Raise MessageException instead of assertions on rerun problems by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18858 <https://github.com/galaxyproject/galaxy/pull/18858>`_
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
* Enable ``warn_unused_ignores`` mypy option by `@nsoranzo <https://github.com/nsoranzo>`_ in `#17991 <https://github.com/galaxyproject/galaxy/pull/17991>`_
* Add galaxy to user agent by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18003 <https://github.com/galaxyproject/galaxy/pull/18003>`_
* Refactor galaxy.files plugin loading + config handling. by `@jmchilton <https://github.com/jmchilton>`_ in `#18049 <https://github.com/galaxyproject/galaxy/pull/18049>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#18063 <https://github.com/galaxyproject/galaxy/pull/18063>`_

-------------------
24.0.3 (2024-06-28)
-------------------


=========
Bug fixes
=========

* Allow purge query param, deprecate purge body param by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18105 <https://github.com/galaxyproject/galaxy/pull/18105>`_
* Prevent anonymous and inactive users from running workflows by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#18192 <https://github.com/galaxyproject/galaxy/pull/18192>`_
* Check dataset state when attempting to acces dataset contents by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18214 <https://github.com/galaxyproject/galaxy/pull/18214>`_
* Fix update group API payload model by `@davelopez <https://github.com/davelopez>`_ in `#18374 <https://github.com/galaxyproject/galaxy/pull/18374>`_

-------------------
24.0.2 (2024-05-07)
-------------------


=========
Bug fixes
=========

* Improve error message for ``Extract dataset`` tool by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18078 <https://github.com/galaxyproject/galaxy/pull/18078>`_

-------------------
24.0.1 (2024-05-02)
-------------------


=========
Bug fixes
=========

* Fix tool version switch in editor by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17858 <https://github.com/galaxyproject/galaxy/pull/17858>`_
* Fix workflow run form failing on certain histories by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17869 <https://github.com/galaxyproject/galaxy/pull/17869>`_
* Always serialize element_count and populated when listing contents by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17890 <https://github.com/galaxyproject/galaxy/pull/17890>`_
* Make `wait_for_history_jobs` look at jobs, not datasets by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17892 <https://github.com/galaxyproject/galaxy/pull/17892>`_
* Fix missing implicit conversion for mapped over jobs by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17952 <https://github.com/galaxyproject/galaxy/pull/17952>`_
* Fix get_content_as_text for compressed text datatypes by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17976 <https://github.com/galaxyproject/galaxy/pull/17976>`_
* Raise appropriate exception if user forces a collection that is not populated with elements as input by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18023 <https://github.com/galaxyproject/galaxy/pull/18023>`_
* Fix ``test_get_tags_histories_content`` test by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18026 <https://github.com/galaxyproject/galaxy/pull/18026>`_
* Ensure that offset and limit are never negative by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18044 <https://github.com/galaxyproject/galaxy/pull/18044>`_
* Fix history update time after bulk operation by `@davelopez <https://github.com/davelopez>`_ in `#18068 <https://github.com/galaxyproject/galaxy/pull/18068>`_

-------------------
24.0.0 (2024-04-02)
-------------------


=========
Bug fixes
=========

* Only check access permissions in ``/api/{history_dataset_collection_id}/contents/{dataset_collection_id}`` by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#17444 <https://github.com/galaxyproject/galaxy/pull/17444>`_
* Fix ``test_index_advanced_filter`` API test re-running by `@nsoranzo <https://github.com/nsoranzo>`_ in `#17547 <https://github.com/galaxyproject/galaxy/pull/17547>`_
* Limit new anon histories by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17657 <https://github.com/galaxyproject/galaxy/pull/17657>`_
* Fix step type serialization for StoredWorkflowDetailed models by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17716 <https://github.com/galaxyproject/galaxy/pull/17716>`_
* Fix histories API index_query serialization by `@davelopez <https://github.com/davelopez>`_ in `#17726 <https://github.com/galaxyproject/galaxy/pull/17726>`_
* Fix source history update_time being updated when importing a public history by `@jmchilton <https://github.com/jmchilton>`_ in `#17728 <https://github.com/galaxyproject/galaxy/pull/17728>`_
* Also set extension and metadata on copies of job outputs when finishing job by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17777 <https://github.com/galaxyproject/galaxy/pull/17777>`_
* Fix change_datatype PJA for dynamic collections  by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17803 <https://github.com/galaxyproject/galaxy/pull/17803>`_
* Fix archived histories mixing with active in histories list by `@davelopez <https://github.com/davelopez>`_ in `#17856 <https://github.com/galaxyproject/galaxy/pull/17856>`_

============
Enhancements
============

* Python 3.8 as minimum by `@mr-c <https://github.com/mr-c>`_ in `#16954 <https://github.com/galaxyproject/galaxy/pull/16954>`_
* Toward declarative help for Galaxy markdown directives. by `@jmchilton <https://github.com/jmchilton>`_ in `#16979 <https://github.com/galaxyproject/galaxy/pull/16979>`_
* Extend regex groups in stdio regex matches by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#17016 <https://github.com/galaxyproject/galaxy/pull/17016>`_
* Create pydantic model for the return of show operation -  get: `/api/jobs/{job_id}`  by `@heisner-tillman <https://github.com/heisner-tillman>`_ in `#17153 <https://github.com/galaxyproject/galaxy/pull/17153>`_
* Don't require admin user to list ``/api/tool_data`` by `@jozh2008 <https://github.com/jozh2008>`_ in `#17161 <https://github.com/galaxyproject/galaxy/pull/17161>`_
* Vueifiy History Grids by `@guerler <https://github.com/guerler>`_ in `#17219 <https://github.com/galaxyproject/galaxy/pull/17219>`_
* Reuse test instance during non-integration tests by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17234 <https://github.com/galaxyproject/galaxy/pull/17234>`_
* Migrate models to pydantic 2 by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17262 <https://github.com/galaxyproject/galaxy/pull/17262>`_
* Add ``__KEEP_SUCCESS_DATASETS__`` by `@lldelisle <https://github.com/lldelisle>`_ in `#17294 <https://github.com/galaxyproject/galaxy/pull/17294>`_
* Enable ``warn_unreachable`` mypy option by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17365 <https://github.com/galaxyproject/galaxy/pull/17365>`_
* Combines legacy qv-pattern and advanced filter pattern in history index endpoint by `@guerler <https://github.com/guerler>`_ in `#17368 <https://github.com/galaxyproject/galaxy/pull/17368>`_
* Cancel all active jobs when the user is deleted by `@davelopez <https://github.com/davelopez>`_ in `#17390 <https://github.com/galaxyproject/galaxy/pull/17390>`_
* Update to black 2024 stable style by `@nsoranzo <https://github.com/nsoranzo>`_ in `#17391 <https://github.com/galaxyproject/galaxy/pull/17391>`_
* Purge `groups` and `roles` from DB (for real) by `@davelopez <https://github.com/davelopez>`_ in `#17411 <https://github.com/galaxyproject/galaxy/pull/17411>`_
* Refactor Workflow API routes - Part 1 by `@heisner-tillman <https://github.com/heisner-tillman>`_ in `#17463 <https://github.com/galaxyproject/galaxy/pull/17463>`_
* Consolidate resource grids into tab views by `@guerler <https://github.com/guerler>`_ in `#17487 <https://github.com/galaxyproject/galaxy/pull/17487>`_
* Filter out subworkflow invocations by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17558 <https://github.com/galaxyproject/galaxy/pull/17558>`_
* Restore histories API behavior for `keys` query parameter by `@davelopez <https://github.com/davelopez>`_ in `#17779 <https://github.com/galaxyproject/galaxy/pull/17779>`_
* Fix datasets API custom keys encoding by `@davelopez <https://github.com/davelopez>`_ in `#17793 <https://github.com/galaxyproject/galaxy/pull/17793>`_

-------------------
23.2.1 (2024-02-21)
-------------------


=========
Bug fixes
=========

* Fix: serialize `tool_shed_urls` directly from the API by `@davelopez <https://github.com/davelopez>`_ in `#16561 <https://github.com/galaxyproject/galaxy/pull/16561>`_
* Restore ToolsApi and create new api route for new panel structure by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#16872 <https://github.com/galaxyproject/galaxy/pull/16872>`_
* Ruff and flake8 fixes by `@nsoranzo <https://github.com/nsoranzo>`_ in `#16884 <https://github.com/galaxyproject/galaxy/pull/16884>`_
* Make payload optional again for create tag API by `@nsoranzo <https://github.com/nsoranzo>`_ in `#17144 <https://github.com/galaxyproject/galaxy/pull/17144>`_
* Only check access permissions in `/api/{history_dataset_collection_id}/contents/{dataset_collection_id}` by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17459 <https://github.com/galaxyproject/galaxy/pull/17459>`_

============
Enhancements
============

* Implement default locations for data and collection parameters. by `@jmchilton <https://github.com/jmchilton>`_ in `#14955 <https://github.com/galaxyproject/galaxy/pull/14955>`_
* Delete non-terminal jobs and subworkflow invocations when cancelling invocation by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16252 <https://github.com/galaxyproject/galaxy/pull/16252>`_
* Migrate a part of the users API to Fast API by `@heisner-tillman <https://github.com/heisner-tillman>`_ in `#16341 <https://github.com/galaxyproject/galaxy/pull/16341>`_
* Refactor Tool Panel views structures and combine ToolBox and ToolBoxWorkflow into one component by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#16739 <https://github.com/galaxyproject/galaxy/pull/16739>`_
* Don't copy collection elements in ``test_dataset_collection_hide_originals`` by `@nsoranzo <https://github.com/nsoranzo>`_ in `#16747 <https://github.com/galaxyproject/galaxy/pull/16747>`_
* Drop legacy server-side search by `@jdavcs <https://github.com/jdavcs>`_ in `#16755 <https://github.com/galaxyproject/galaxy/pull/16755>`_
* Migrate a part of the jobs API to Fast API by `@heisner-tillman <https://github.com/heisner-tillman>`_ in `#16778 <https://github.com/galaxyproject/galaxy/pull/16778>`_
* Vueify Visualizations Grid by `@guerler <https://github.com/guerler>`_ in `#16892 <https://github.com/galaxyproject/galaxy/pull/16892>`_
* Change `api/tool_panel` to `api/tool_panels/...` by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#16928 <https://github.com/galaxyproject/galaxy/pull/16928>`_
* Require name for workflows on save, set default to Unnamed Workflow by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#17038 <https://github.com/galaxyproject/galaxy/pull/17038>`_
* Migrate ItemTags API to FastAPI by `@arash77 <https://github.com/arash77>`_ in `#17064 <https://github.com/galaxyproject/galaxy/pull/17064>`_

=============
Other changes
=============

* Merge 23.1 into dev by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16534 <https://github.com/galaxyproject/galaxy/pull/16534>`_

-------------------
23.1.4 (2024-01-04)
-------------------


=========
Bug fixes
=========

* Assert that tus uploader instance has URL by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17133 <https://github.com/galaxyproject/galaxy/pull/17133>`_
* Fix workflow index total matches counting by `@davelopez <https://github.com/davelopez>`_ in `#17176 <https://github.com/galaxyproject/galaxy/pull/17176>`_

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

* Skip state filtering in ``__MERGE_COLLECTION__`` tool  by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16937 <https://github.com/galaxyproject/galaxy/pull/16937>`_
* Fix duplicated tools in tool panel view section copying by `@jmchilton <https://github.com/jmchilton>`_ in `#17036 <https://github.com/galaxyproject/galaxy/pull/17036>`_

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

* Ensure session is request-scoped for legacy endpoints by `@jdavcs <https://github.com/jdavcs>`_ in `#16207 <https://github.com/galaxyproject/galaxy/pull/16207>`_
* allow anon access for api/datasets/get_content_as_text by `@martenson <https://github.com/martenson>`_ in `#16226 <https://github.com/galaxyproject/galaxy/pull/16226>`_
* qualify querying for an api-key by `@martenson <https://github.com/martenson>`_ in `#16320 <https://github.com/galaxyproject/galaxy/pull/16320>`_
* Fix tags ownership by `@davelopez <https://github.com/davelopez>`_ in `#16339 <https://github.com/galaxyproject/galaxy/pull/16339>`_
* Job cache fixes for DCEs by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16384 <https://github.com/galaxyproject/galaxy/pull/16384>`_
* Fix histories count by `@davelopez <https://github.com/davelopez>`_ in `#16400 <https://github.com/galaxyproject/galaxy/pull/16400>`_
* Fix replacement parameters for subworkflows. by `@jmchilton <https://github.com/jmchilton>`_ in `#16592 <https://github.com/galaxyproject/galaxy/pull/16592>`_
* Fixes for conditional subworkflow steps by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16632 <https://github.com/galaxyproject/galaxy/pull/16632>`_
* Fix nested conditional workflow steps by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16641 <https://github.com/galaxyproject/galaxy/pull/16641>`_
* Fix expression evaluation for nested state by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16656 <https://github.com/galaxyproject/galaxy/pull/16656>`_
* Push to object store even if ``set_meta`` fails by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16667 <https://github.com/galaxyproject/galaxy/pull/16667>`_
* Copy the collection contents by default when copying a collection by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16717 <https://github.com/galaxyproject/galaxy/pull/16717>`_
* Fix allowlist deserialization in file sources by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16729 <https://github.com/galaxyproject/galaxy/pull/16729>`_
* Fix workflow import losing tool_version by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16869 <https://github.com/galaxyproject/galaxy/pull/16869>`_
* Fix tag ownership check by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16877 <https://github.com/galaxyproject/galaxy/pull/16877>`_
* Fix delete collection + elements by `@davelopez <https://github.com/davelopez>`_ in `#16879 <https://github.com/galaxyproject/galaxy/pull/16879>`_

============
Enhancements
============

* Empower Users to Select Storage Destination by `@jmchilton <https://github.com/jmchilton>`_ in `#14073 <https://github.com/galaxyproject/galaxy/pull/14073>`_
* Outline Deployment Tests by `@jmchilton <https://github.com/jmchilton>`_ in `#15420 <https://github.com/galaxyproject/galaxy/pull/15420>`_
* Unify url handling with filesources by `@nuwang <https://github.com/nuwang>`_ in `#15497 <https://github.com/galaxyproject/galaxy/pull/15497>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#15564 <https://github.com/galaxyproject/galaxy/pull/15564>`_
* Add API test and refactor code for related:hid history filter by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#15786 <https://github.com/galaxyproject/galaxy/pull/15786>`_
* Allow pending inputs in some collection operation tools by `@mvdbeek <https://github.com/mvdbeek>`_ in `#15892 <https://github.com/galaxyproject/galaxy/pull/15892>`_
* Record input datasets and collections at full parameter path by `@mvdbeek <https://github.com/mvdbeek>`_ in `#15978 <https://github.com/galaxyproject/galaxy/pull/15978>`_
* Add History Archival feature by `@davelopez <https://github.com/davelopez>`_ in `#16003 <https://github.com/galaxyproject/galaxy/pull/16003>`_
* Dataset chunking tests (and small fixes) by `@jmchilton <https://github.com/jmchilton>`_ in `#16069 <https://github.com/galaxyproject/galaxy/pull/16069>`_
* Improve histories and datasets immutability checks by `@davelopez <https://github.com/davelopez>`_ in `#16143 <https://github.com/galaxyproject/galaxy/pull/16143>`_
* Migrate display applications API to Fast API by `@heisner-tillman <https://github.com/heisner-tillman>`_ in `#16156 <https://github.com/galaxyproject/galaxy/pull/16156>`_
* bring grids for (published) pages on par with workflows by `@martenson <https://github.com/martenson>`_ in `#16209 <https://github.com/galaxyproject/galaxy/pull/16209>`_

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

* Display DCE in job parameter component, allow rerunning with DCE input by `@mvdbeek <https://github.com/mvdbeek>`_ in `#15744 <https://github.com/galaxyproject/galaxy/pull/15744>`_
* Fix folder listing via file browser by `@mvdbeek <https://github.com/mvdbeek>`_ in `#15950 <https://github.com/galaxyproject/galaxy/pull/15950>`_
* Fix case sensitive filtering by name in histories by `@davelopez <https://github.com/davelopez>`_ in `#16036 <https://github.com/galaxyproject/galaxy/pull/16036>`_
* Fix dataype_change not updating HDCA update_time by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16099 <https://github.com/galaxyproject/galaxy/pull/16099>`_
* Extract HDA for code_file validate_input hook by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16120 <https://github.com/galaxyproject/galaxy/pull/16120>`_

============
Enhancements
============

* Add support for launching workflows via Tutorial Mode by `@hexylena <https://github.com/hexylena>`_ in `#15684 <https://github.com/galaxyproject/galaxy/pull/15684>`_
* Allow setting auto_decompress property in staging interface by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16014 <https://github.com/galaxyproject/galaxy/pull/16014>`_

-------------------
20.9.0 (2020-10-15)
-------------------

* Initial import from dev branch of Galaxy during 20.09 branch of Galaxy.
