History
-------

.. to_doc

-------------------
25.0.1 (2025-06-20)
-------------------


=========
Bug fixes
=========

* Fix single data element identifier to be a regular string by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20438 <https://github.com/galaxyproject/galaxy/pull/20438>`_
* Relax validation of XML test assertion parsing by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20511 <https://github.com/galaxyproject/galaxy/pull/20511>`_
* Add id-token: write for npm publishing by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20519 <https://github.com/galaxyproject/galaxy/pull/20519>`_
* Do not expose user info to non authenticated users by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#20524 <https://github.com/galaxyproject/galaxy/pull/20524>`_
* names of package extras cannot contain underscores by `@mr-c <https://github.com/mr-c>`_ in `#20525 <https://github.com/galaxyproject/galaxy/pull/20525>`_
* Pin isa-rwval 0.10.11, drop conditional import handling by `@natefoo <https://github.com/natefoo>`_ in `#20527 <https://github.com/galaxyproject/galaxy/pull/20527>`_
* Fix import of ``galaxy.tool_util.cwl`` module by `@nsoranzo <https://github.com/nsoranzo>`_ in `#20529 <https://github.com/galaxyproject/galaxy/pull/20529>`_
* Fix `galaxy-config` script, move install to `galaxy-dependencies` in app package by `@natefoo <https://github.com/natefoo>`_ in `#20531 <https://github.com/galaxyproject/galaxy/pull/20531>`_

============
Enhancements
============

* Bump gravity dependency to 1.1.0 by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20520 <https://github.com/galaxyproject/galaxy/pull/20520>`_
* Update the dev package build and install script by `@natefoo <https://github.com/natefoo>`_ in `#20526 <https://github.com/galaxyproject/galaxy/pull/20526>`_

=============
Other changes
=============

* Merge Release 25.0 into the master branch by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#20514 <https://github.com/galaxyproject/galaxy/pull/20514>`_
* Fixes for static handling and the web_client package by `@natefoo <https://github.com/natefoo>`_ in `#20516 <https://github.com/galaxyproject/galaxy/pull/20516>`_
* Fix link in user release notes by `@bgruening <https://github.com/bgruening>`_ in `#20518 <https://github.com/galaxyproject/galaxy/pull/20518>`_
* Bump Gravity to 1.1.1 by `@natefoo <https://github.com/natefoo>`_ in `#20533 <https://github.com/galaxyproject/galaxy/pull/20533>`_

-------------------
25.0.0 (2025-06-18)
-------------------


=========
Bug fixes
=========

* Stabilize HistoryView.test.js by `@jmchilton <https://github.com/jmchilton>`_ in `#19165 <https://github.com/galaxyproject/galaxy/pull/19165>`_
* Cleanup Jest Test Output (part 2) by `@jmchilton <https://github.com/jmchilton>`_ in `#19178 <https://github.com/galaxyproject/galaxy/pull/19178>`_
* Fix Pesky warning with PersistentTaskProgressMonitorAlert.test.ts  by `@ElectronicBlueberry <https://github.com/ElectronicBlueberry>`_ in `#19180 <https://github.com/galaxyproject/galaxy/pull/19180>`_
* Cleanup Jest Test Output (part 3) by `@jmchilton <https://github.com/jmchilton>`_ in `#19185 <https://github.com/galaxyproject/galaxy/pull/19185>`_
* Cleanup Jest Test Output (part 4) by `@jmchilton <https://github.com/jmchilton>`_ in `#19186 <https://github.com/galaxyproject/galaxy/pull/19186>`_
* Bump tornado from 6.4.1 to 6.4.2 in /lib/galaxy/dependencies by `@dependabot[bot] <https://github.com/dependabot[bot]>`_ in `#19189 <https://github.com/galaxyproject/galaxy/pull/19189>`_
* Don't calculate dataset hash for datasets in non-OK state by `@nsoranzo <https://github.com/nsoranzo>`_ in `#19191 <https://github.com/galaxyproject/galaxy/pull/19191>`_
* Cleanup test output console for tool panel tests. by `@jmchilton <https://github.com/jmchilton>`_ in `#19210 <https://github.com/galaxyproject/galaxy/pull/19210>`_
* Update Vizarr package version to 0.1.6 by `@davelopez <https://github.com/davelopez>`_ in `#19228 <https://github.com/galaxyproject/galaxy/pull/19228>`_
* Bump python-multipart from 0.0.17 to 0.0.18 in /lib/galaxy/dependencies by `@dependabot[bot] <https://github.com/dependabot[bot]>`_ in `#19233 <https://github.com/galaxyproject/galaxy/pull/19233>`_
* Use ``resource_path()`` to access datatypes_conf.xml.sample as a package resource by `@nsoranzo <https://github.com/nsoranzo>`_ in `#19331 <https://github.com/galaxyproject/galaxy/pull/19331>`_
* Require importlib-resources also for Python 3.9-3.11 by `@nsoranzo <https://github.com/nsoranzo>`_ in `#19358 <https://github.com/galaxyproject/galaxy/pull/19358>`_
* Bump jinja2 from 3.1.4 to 3.1.5 in /lib/galaxy/dependencies by `@dependabot[bot] <https://github.com/dependabot[bot]>`_ in `#19369 <https://github.com/galaxyproject/galaxy/pull/19369>`_
* Node 22 unreachable fixes by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19378 <https://github.com/galaxyproject/galaxy/pull/19378>`_
* Better handling of public pages and workflows authored by deleted users by `@jdavcs <https://github.com/jdavcs>`_ in `#19394 <https://github.com/galaxyproject/galaxy/pull/19394>`_
* Alternative `format_source` fix by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19395 <https://github.com/galaxyproject/galaxy/pull/19395>`_
* Use ``id`` entity attribute when setting ``exampleOfWork`` property by `@nsoranzo <https://github.com/nsoranzo>`_ in `#19396 <https://github.com/galaxyproject/galaxy/pull/19396>`_
* Display email activation help only if user activation is enabled by `@jdavcs <https://github.com/jdavcs>`_ in `#19402 <https://github.com/galaxyproject/galaxy/pull/19402>`_
* Prevent negative offset by `@jdavcs <https://github.com/jdavcs>`_ in `#19409 <https://github.com/galaxyproject/galaxy/pull/19409>`_
* Avoid using custos refresh tokens which are expired by `@martenson <https://github.com/martenson>`_ in `#19411 <https://github.com/galaxyproject/galaxy/pull/19411>`_
* Fix wrong id in test_combined_mapping_and_subcollection_mapping by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19481 <https://github.com/galaxyproject/galaxy/pull/19481>`_
* Fix preferred object store id reactivity by `@ElectronicBlueberry <https://github.com/ElectronicBlueberry>`_ in `#19491 <https://github.com/galaxyproject/galaxy/pull/19491>`_
* Fix wrong URI written to `ExportObjectResultMetadata` when exporting histories to eLabFTW by `@kysrpex <https://github.com/kysrpex>`_ in `#19541 <https://github.com/galaxyproject/galaxy/pull/19541>`_
* Fix `test_mulled_build.py::test_mulled_build_files_cli` with `use_mamba=True` by `@kysrpex <https://github.com/kysrpex>`_ in `#19545 <https://github.com/galaxyproject/galaxy/pull/19545>`_
* Fix package test errors: Ignore mypy errors caused by social-auth-core 4.5.5 by `@jdavcs <https://github.com/jdavcs>`_ in `#19620 <https://github.com/galaxyproject/galaxy/pull/19620>`_
* Update eLabFTW file source template docs by `@kysrpex <https://github.com/kysrpex>`_ in `#19632 <https://github.com/galaxyproject/galaxy/pull/19632>`_
* Fix more vue tsc indicated type issues by `@jmchilton <https://github.com/jmchilton>`_ in `#19650 <https://github.com/galaxyproject/galaxy/pull/19650>`_
* Yet More Vue Typing Error Fixes by `@jmchilton <https://github.com/jmchilton>`_ in `#19680 <https://github.com/galaxyproject/galaxy/pull/19680>`_
* Fix incorrect type in tool_util.deps and fix package structure. by `@jmchilton <https://github.com/jmchilton>`_ in `#19702 <https://github.com/galaxyproject/galaxy/pull/19702>`_
* Add linter argument to linter report function calls by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#19708 <https://github.com/galaxyproject/galaxy/pull/19708>`_
* Refactor tool panel handling, resolve transiently failing jest test by `@guerler <https://github.com/guerler>`_ in `#19733 <https://github.com/galaxyproject/galaxy/pull/19733>`_
* Jest Cleanup (Part 5) by `@jmchilton <https://github.com/jmchilton>`_ in `#19743 <https://github.com/galaxyproject/galaxy/pull/19743>`_
* Use fissix also when python3-lib2to3 is not installed by `@nsoranzo <https://github.com/nsoranzo>`_ in `#19749 <https://github.com/galaxyproject/galaxy/pull/19749>`_
* Fix setting env and tags on resubmission by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#19753 <https://github.com/galaxyproject/galaxy/pull/19753>`_
* Revise consistently failing edam tool panel view test. by `@jmchilton <https://github.com/jmchilton>`_ in `#19762 <https://github.com/galaxyproject/galaxy/pull/19762>`_
* Add missing tool test file by `@jmchilton <https://github.com/jmchilton>`_ in `#19763 <https://github.com/galaxyproject/galaxy/pull/19763>`_
* Bump axios from 1.7.4 to 1.8.2 in /client by `@dependabot[bot] <https://github.com/dependabot[bot]>`_ in `#19773 <https://github.com/galaxyproject/galaxy/pull/19773>`_
* Fix wording of API doc string by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#19776 <https://github.com/galaxyproject/galaxy/pull/19776>`_
* Add better `WorkflowSummary` type by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#19779 <https://github.com/galaxyproject/galaxy/pull/19779>`_
* Fix workflow run graph non input steps not appearing bug by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#19781 <https://github.com/galaxyproject/galaxy/pull/19781>`_
* Update webdav user file source template help text by `@sanjaysrikakulam <https://github.com/sanjaysrikakulam>`_ in `#19784 <https://github.com/galaxyproject/galaxy/pull/19784>`_
* HelpText improvements (content, sizing) and WorkflowInvocationHeader tweaks. by `@dannon <https://github.com/dannon>`_ in `#19792 <https://github.com/galaxyproject/galaxy/pull/19792>`_
* Remove unused (define* - compiler macro) imports from TextEditor.vue by `@dannon <https://github.com/dannon>`_ in `#19793 <https://github.com/galaxyproject/galaxy/pull/19793>`_
* Fix Selenium workflow tests not updating param type properly.  by `@jmchilton <https://github.com/jmchilton>`_ in `#19810 <https://github.com/galaxyproject/galaxy/pull/19810>`_
* Fix Galaxy ignoring job object_store_id for quota check by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#19854 <https://github.com/galaxyproject/galaxy/pull/19854>`_
* Cleanup circular dependencies around utils.ts. by `@jmchilton <https://github.com/jmchilton>`_ in `#19857 <https://github.com/galaxyproject/galaxy/pull/19857>`_
* Remove circular dependency around user store. by `@jmchilton <https://github.com/jmchilton>`_ in `#19859 <https://github.com/galaxyproject/galaxy/pull/19859>`_
* Move some store types out into own file to reduce circular dependencies. by `@jmchilton <https://github.com/jmchilton>`_ in `#19860 <https://github.com/galaxyproject/galaxy/pull/19860>`_
* Fix most new vue typescript errors discovered in #19851 by `@jmchilton <https://github.com/jmchilton>`_ in `#19862 <https://github.com/galaxyproject/galaxy/pull/19862>`_
* Create rucio.cfg from inside Rucio objectstore by `@SergeyYakubov <https://github.com/SergeyYakubov>`_ in `#19863 <https://github.com/galaxyproject/galaxy/pull/19863>`_
* Fix broken optimisation introduced in #19852 by `@nsoranzo <https://github.com/nsoranzo>`_ in `#19871 <https://github.com/galaxyproject/galaxy/pull/19871>`_
* Fix various mypy issues around mapped attributes by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19883 <https://github.com/galaxyproject/galaxy/pull/19883>`_
* More fixes to `FormData` drag and drop and typing by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#19900 <https://github.com/galaxyproject/galaxy/pull/19900>`_
* Use FA Component (w/svg) instead of span+font in RunWorkflow header by `@dannon <https://github.com/dannon>`_ in `#19901 <https://github.com/galaxyproject/galaxy/pull/19901>`_
* Change wording in the google drive user file source template by `@sanjaysrikakulam <https://github.com/sanjaysrikakulam>`_ in `#19927 <https://github.com/galaxyproject/galaxy/pull/19927>`_
* Move `FormBoolean` back to `FormElement` field in workflow run form by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#19938 <https://github.com/galaxyproject/galaxy/pull/19938>`_
* Fix ``test_in_directory`` on osx by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19943 <https://github.com/galaxyproject/galaxy/pull/19943>`_
* Fix adding tags popup closing logic on focus out by `@itisAliRH <https://github.com/itisAliRH>`_ in `#19950 <https://github.com/galaxyproject/galaxy/pull/19950>`_
* Use lower case extension for setting datatype in data discovery by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#19954 <https://github.com/galaxyproject/galaxy/pull/19954>`_
* Fix ownership check in history contents update route by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19969 <https://github.com/galaxyproject/galaxy/pull/19969>`_
* Remove hgv_sift from tool_conf.xml.sample by `@natefoo <https://github.com/natefoo>`_ in `#19972 <https://github.com/galaxyproject/galaxy/pull/19972>`_
* Unwind more client dependencies at top of stack.  by `@jmchilton <https://github.com/jmchilton>`_ in `#19983 <https://github.com/galaxyproject/galaxy/pull/19983>`_
* Fix `keyedCache` never allowing multiple fetches by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#20020 <https://github.com/galaxyproject/galaxy/pull/20020>`_
* Pass host url to visualizations by `@guerler <https://github.com/guerler>`_ in `#20022 <https://github.com/galaxyproject/galaxy/pull/20022>`_
* Also chown R lib in RStudio BioC tool by `@natefoo <https://github.com/natefoo>`_ in `#20025 <https://github.com/galaxyproject/galaxy/pull/20025>`_
* Add new line to vtpascii test file by `@guerler <https://github.com/guerler>`_ in `#20051 <https://github.com/galaxyproject/galaxy/pull/20051>`_
* Fix linting with markdown in tool help by `@bgruening <https://github.com/bgruening>`_ in `#20058 <https://github.com/galaxyproject/galaxy/pull/20058>`_
* Update breadcrumb item 'to' type for better routing support by `@itisAliRH <https://github.com/itisAliRH>`_ in `#20065 <https://github.com/galaxyproject/galaxy/pull/20065>`_
* Always render Outputs tab in invocation view by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#20073 <https://github.com/galaxyproject/galaxy/pull/20073>`_
* Remove collapse invocations panel on mouseleave feature by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#20074 <https://github.com/galaxyproject/galaxy/pull/20074>`_
* Bump http-proxy-middleware from 2.0.7 to 2.0.9 in /client by `@dependabot[bot] <https://github.com/dependabot[bot]>`_ in `#20086 <https://github.com/galaxyproject/galaxy/pull/20086>`_
* Fix `test_workflow_run` export selenium by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#20089 <https://github.com/galaxyproject/galaxy/pull/20089>`_
* Fix and migrate Drawrna by `@guerler <https://github.com/guerler>`_ in `#20102 <https://github.com/galaxyproject/galaxy/pull/20102>`_
* Add hid to selection field in visualization creation form by `@guerler <https://github.com/guerler>`_ in `#20108 <https://github.com/galaxyproject/galaxy/pull/20108>`_
* Remove only the Docker images specific for the test by `@nsoranzo <https://github.com/nsoranzo>`_ in `#20109 <https://github.com/galaxyproject/galaxy/pull/20109>`_
* Fixes for GButtons with disabled state by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#20121 <https://github.com/galaxyproject/galaxy/pull/20121>`_
* Sort visualization datasets by hid by `@guerler <https://github.com/guerler>`_ in `#20123 <https://github.com/galaxyproject/galaxy/pull/20123>`_
* Wait for Gbutton to become enabled by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20131 <https://github.com/galaxyproject/galaxy/pull/20131>`_
* Allow deferred and ok state datasets for vis by `@guerler <https://github.com/guerler>`_ in `#20143 <https://github.com/galaxyproject/galaxy/pull/20143>`_
* Fix certain cases of collection parameter handling during workflow execution. by `@jmchilton <https://github.com/jmchilton>`_ in `#20152 <https://github.com/galaxyproject/galaxy/pull/20152>`_
* Yaml parser fixes part2 by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20162 <https://github.com/galaxyproject/galaxy/pull/20162>`_
* Fix tapis module typing errors by `@jdavcs <https://github.com/jdavcs>`_ in `#20175 <https://github.com/galaxyproject/galaxy/pull/20175>`_
* Use ``backports.zoneinfo`` in ``job_metrics`` package under Python <3.9 by `@nsoranzo <https://github.com/nsoranzo>`_ in `#20178 <https://github.com/galaxyproject/galaxy/pull/20178>`_
* Update tabular_csv.py to use less memory in tsv->csv conversion by `@cat-bro <https://github.com/cat-bro>`_ in `#20187 <https://github.com/galaxyproject/galaxy/pull/20187>`_
* Corrects header levels in Visualization Help Markdown by `@guerler <https://github.com/guerler>`_ in `#20199 <https://github.com/galaxyproject/galaxy/pull/20199>`_
* Move UnprivilegedToolResponse into api by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20207 <https://github.com/galaxyproject/galaxy/pull/20207>`_
* Package fixes by `@nsoranzo <https://github.com/nsoranzo>`_ in `#20208 <https://github.com/galaxyproject/galaxy/pull/20208>`_
* Fix NFDI auth by `@bgruening <https://github.com/bgruening>`_ in `#20217 <https://github.com/galaxyproject/galaxy/pull/20217>`_
* Fix next milestone by `@martenson <https://github.com/martenson>`_ in `#20219 <https://github.com/galaxyproject/galaxy/pull/20219>`_
* Group Tool Versions in IT Panel by `@dannon <https://github.com/dannon>`_ in `#20244 <https://github.com/galaxyproject/galaxy/pull/20244>`_
* Fix vue-tsc issue in ParameterStep by `@dannon <https://github.com/dannon>`_ in `#20245 <https://github.com/galaxyproject/galaxy/pull/20245>`_
* Replace Bootstrap Popover with Popper wrapper by `@guerler <https://github.com/guerler>`_ in `#20246 <https://github.com/galaxyproject/galaxy/pull/20246>`_
* Fix tool-provided metadata for CONVERTER_tar_to_directory by `@mr-c <https://github.com/mr-c>`_ in `#20260 <https://github.com/galaxyproject/galaxy/pull/20260>`_
* Fix theme selector by `@guerler <https://github.com/guerler>`_ in `#20275 <https://github.com/galaxyproject/galaxy/pull/20275>`_
* Fix interactive activity highlighting by `@guerler <https://github.com/guerler>`_ in `#20276 <https://github.com/galaxyproject/galaxy/pull/20276>`_
* Fix inconsistent header sizes by `@guerler <https://github.com/guerler>`_ in `#20277 <https://github.com/galaxyproject/galaxy/pull/20277>`_
* Add non-dev httpx dependency by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20281 <https://github.com/galaxyproject/galaxy/pull/20281>`_
* Remove duplicated job id in job success view by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#20289 <https://github.com/galaxyproject/galaxy/pull/20289>`_
* Skip multiple pasted URLs when checking for remote Zip by `@davelopez <https://github.com/davelopez>`_ in `#20300 <https://github.com/galaxyproject/galaxy/pull/20300>`_
* Fix masthead logo height by `@guerler <https://github.com/guerler>`_ in `#20302 <https://github.com/galaxyproject/galaxy/pull/20302>`_
* Increase proxy API robustness by validating URL before use by `@davelopez <https://github.com/davelopez>`_ in `#20311 <https://github.com/galaxyproject/galaxy/pull/20311>`_
* Rerun workflows for the correct version/instance by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#20313 <https://github.com/galaxyproject/galaxy/pull/20313>`_
* Avoid displaying dataset tab view in window manager by `@guerler <https://github.com/guerler>`_ in `#20317 <https://github.com/galaxyproject/galaxy/pull/20317>`_
* Fix display urls by `@dannon <https://github.com/dannon>`_ in `#20318 <https://github.com/galaxyproject/galaxy/pull/20318>`_
* Fix workflow bookmark filtering by `@davelopez <https://github.com/davelopez>`_ in `#20325 <https://github.com/galaxyproject/galaxy/pull/20325>`_
* Add test for workflow instance download fix by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#20326 <https://github.com/galaxyproject/galaxy/pull/20326>`_
* Add basic validation to workflow creator attribute by `@jdavcs <https://github.com/jdavcs>`_ in `#20328 <https://github.com/galaxyproject/galaxy/pull/20328>`_
* Fix broken admin navigation option and add missing menu items by `@dannon <https://github.com/dannon>`_ in `#20333 <https://github.com/galaxyproject/galaxy/pull/20333>`_
* Error on duplicate labels by `@ElectronicBlueberry <https://github.com/ElectronicBlueberry>`_ in `#20335 <https://github.com/galaxyproject/galaxy/pull/20335>`_
* Small UI fixes for ag-grid based rule grid. by `@jmchilton <https://github.com/jmchilton>`_ in `#20358 <https://github.com/galaxyproject/galaxy/pull/20358>`_
* Fix selection issue when adding tags to workflows in bulk by `@davelopez <https://github.com/davelopez>`_ in `#20362 <https://github.com/galaxyproject/galaxy/pull/20362>`_
* Log invalid vault paths by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20363 <https://github.com/galaxyproject/galaxy/pull/20363>`_
* Remove redundant badge when creating collection from upload by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#20367 <https://github.com/galaxyproject/galaxy/pull/20367>`_
* Make invocation errors more compact by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#20369 <https://github.com/galaxyproject/galaxy/pull/20369>`_
* Generate a tenant-unique UID for tapis. by `@dannon <https://github.com/dannon>`_ in `#20370 <https://github.com/galaxyproject/galaxy/pull/20370>`_
* Use router to route to creating a new file source by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#20374 <https://github.com/galaxyproject/galaxy/pull/20374>`_
* Fix radio button options in CopyModal by `@davelopez <https://github.com/davelopez>`_ in `#20378 <https://github.com/galaxyproject/galaxy/pull/20378>`_
* Fix conda_link to use platform.machine() for architecture detection by `@chrisagrams <https://github.com/chrisagrams>`_ in `#20381 <https://github.com/galaxyproject/galaxy/pull/20381>`_
* Fix create file source button, show only at root by `@davelopez <https://github.com/davelopez>`_ in `#20385 <https://github.com/galaxyproject/galaxy/pull/20385>`_
* Force Monaco into a separate bundle by `@dannon <https://github.com/dannon>`_ in `#20396 <https://github.com/galaxyproject/galaxy/pull/20396>`_
* Prevent waiting for history item state to be ok in uploader by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#20397 <https://github.com/galaxyproject/galaxy/pull/20397>`_
* Fix toolshed-installed tool icons by `@dannon <https://github.com/dannon>`_ in `#20399 <https://github.com/galaxyproject/galaxy/pull/20399>`_
* Add job config variable for singularity `--contain` by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#20400 <https://github.com/galaxyproject/galaxy/pull/20400>`_
* Fix form select input sorting by `@davelopez <https://github.com/davelopez>`_ in `#20401 <https://github.com/galaxyproject/galaxy/pull/20401>`_
* Bug fix: allow any collection type in FormCollectionType. by `@jmchilton <https://github.com/jmchilton>`_ in `#20403 <https://github.com/galaxyproject/galaxy/pull/20403>`_
* Fixes for the admin jobs interface by `@martenson <https://github.com/martenson>`_ in `#20405 <https://github.com/galaxyproject/galaxy/pull/20405>`_
* Fix $app attribute access in cheetah templates by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20414 <https://github.com/galaxyproject/galaxy/pull/20414>`_
* Fix job rerun with tool version change by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20417 <https://github.com/galaxyproject/galaxy/pull/20417>`_
* Update pulsar-galaxy-lib to 0.15.8 by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20419 <https://github.com/galaxyproject/galaxy/pull/20419>`_
* Update triggers by `@jdavcs <https://github.com/jdavcs>`_ in `#20425 <https://github.com/galaxyproject/galaxy/pull/20425>`_
* Fix workflow logo URL not being persisted. by `@jmchilton <https://github.com/jmchilton>`_ in `#20428 <https://github.com/galaxyproject/galaxy/pull/20428>`_
* Fix css alignment styling of login page by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#20429 <https://github.com/galaxyproject/galaxy/pull/20429>`_
* Add user-facing explanation for legacy workflow run form usage by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#20431 <https://github.com/galaxyproject/galaxy/pull/20431>`_
* Upgrade tensorflow conditional dependency version to 2.15.1 by `@cat-bro <https://github.com/cat-bro>`_ in `#20434 <https://github.com/galaxyproject/galaxy/pull/20434>`_
* Fix copying of job metrics for cached jobs by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20436 <https://github.com/galaxyproject/galaxy/pull/20436>`_
* Dataset Display and Preferred Viz fixes by `@dannon <https://github.com/dannon>`_ in `#20439 <https://github.com/galaxyproject/galaxy/pull/20439>`_
* Wrap Tool and Workflow run headers properly by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#20440 <https://github.com/galaxyproject/galaxy/pull/20440>`_
* Fix inconsistent styling in List Collection Builder selector by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#20442 <https://github.com/galaxyproject/galaxy/pull/20442>`_
* Fix add button is enabled when empty tag list by `@davelopez <https://github.com/davelopez>`_ in `#20443 <https://github.com/galaxyproject/galaxy/pull/20443>`_
* Set ``GALAXY_CONFIG_FILE`` env var if starting handler with `-c` by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20449 <https://github.com/galaxyproject/galaxy/pull/20449>`_
* Fix pagination state in FilesDialog by `@davelopez <https://github.com/davelopez>`_ in `#20452 <https://github.com/galaxyproject/galaxy/pull/20452>`_
* Data Libraries - persist number of entries displayed in folders by `@dannon <https://github.com/dannon>`_ in `#20455 <https://github.com/galaxyproject/galaxy/pull/20455>`_
* Fix multiple remote file upload to collection creator by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#20456 <https://github.com/galaxyproject/galaxy/pull/20456>`_
* Bug fix: paired_or_unpaired also endswith paired. by `@jmchilton <https://github.com/jmchilton>`_ in `#20458 <https://github.com/galaxyproject/galaxy/pull/20458>`_
* Fix bug with handling compressed file names while auto-pairing.  by `@jmchilton <https://github.com/jmchilton>`_ in `#20459 <https://github.com/galaxyproject/galaxy/pull/20459>`_
* Fix dataset error button not using router by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#20472 <https://github.com/galaxyproject/galaxy/pull/20472>`_
* Don't fit workflow if it doesn't have steps by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20480 <https://github.com/galaxyproject/galaxy/pull/20480>`_
* Remove rename modal from List Collection Creator by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#20487 <https://github.com/galaxyproject/galaxy/pull/20487>`_
* Use DatasetAsImage component for DatasetView image display by `@dannon <https://github.com/dannon>`_ in `#20488 <https://github.com/galaxyproject/galaxy/pull/20488>`_
* Recreate triggers by `@jdavcs <https://github.com/jdavcs>`_ in `#20491 <https://github.com/galaxyproject/galaxy/pull/20491>`_
* Allow workflow description to show full text by `@davelopez <https://github.com/davelopez>`_ in `#20500 <https://github.com/galaxyproject/galaxy/pull/20500>`_

============
Enhancements
============

* Dynamic options: add data table filter by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#12941 <https://github.com/galaxyproject/galaxy/pull/12941>`_
* Run the tool working dir backup/restore on Pulsar by `@natefoo <https://github.com/natefoo>`_ in `#16696 <https://github.com/galaxyproject/galaxy/pull/16696>`_
* Strip galaxy filename annotation on upload by `@GomeChas <https://github.com/GomeChas>`_ in `#18561 <https://github.com/galaxyproject/galaxy/pull/18561>`_
* Isolate singularity containers more thoroughly for better reproducibility. by `@rhpvorderman <https://github.com/rhpvorderman>`_ in `#18628 <https://github.com/galaxyproject/galaxy/pull/18628>`_
* Upgrade bundled/requested node version to 22.15.0 by `@dannon <https://github.com/dannon>`_ in `#18710 <https://github.com/galaxyproject/galaxy/pull/18710>`_
* Workflow Editor Activity Bar by `@ElectronicBlueberry <https://github.com/ElectronicBlueberry>`_ in `#18729 <https://github.com/galaxyproject/galaxy/pull/18729>`_
* Add author and tools details in RO-Crate by `@Marie59 <https://github.com/Marie59>`_ in `#18820 <https://github.com/galaxyproject/galaxy/pull/18820>`_
* Extend image metadata by `@kostrykin <https://github.com/kostrykin>`_ in `#18951 <https://github.com/galaxyproject/galaxy/pull/18951>`_
* Implement tool markdown reports. by `@jmchilton <https://github.com/jmchilton>`_ in `#19054 <https://github.com/galaxyproject/galaxy/pull/19054>`_
* Avoid persisting credentials on checkout step of the Github actions by `@arash77 <https://github.com/arash77>`_ in `#19089 <https://github.com/galaxyproject/galaxy/pull/19089>`_
* Let file sources choose a path for uploaded files by `@kysrpex <https://github.com/kysrpex>`_ in `#19154 <https://github.com/galaxyproject/galaxy/pull/19154>`_
* Move heatmap visualization to new script endpoint by `@guerler <https://github.com/guerler>`_ in `#19176 <https://github.com/galaxyproject/galaxy/pull/19176>`_
* Calculate hash for new non-deferred datasets when finishing a job by `@nsoranzo <https://github.com/nsoranzo>`_ in `#19181 <https://github.com/galaxyproject/galaxy/pull/19181>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#19190 <https://github.com/galaxyproject/galaxy/pull/19190>`_
* Move phylocanvas to script entry point by `@guerler <https://github.com/guerler>`_ in `#19193 <https://github.com/galaxyproject/galaxy/pull/19193>`_
* Fix UP031 errors - Part 1 by `@nsoranzo <https://github.com/nsoranzo>`_ in `#19194 <https://github.com/galaxyproject/galaxy/pull/19194>`_
* Drop thumbs up reaction as pull request approval method by `@nsoranzo <https://github.com/nsoranzo>`_ in `#19202 <https://github.com/galaxyproject/galaxy/pull/19202>`_
* Fix UP031 errors - Part 2 by `@nsoranzo <https://github.com/nsoranzo>`_ in `#19204 <https://github.com/galaxyproject/galaxy/pull/19204>`_
* Add plotly.js by `@guerler <https://github.com/guerler>`_ in `#19206 <https://github.com/galaxyproject/galaxy/pull/19206>`_
* Switch h5web to script endpoint by `@guerler <https://github.com/guerler>`_ in `#19211 <https://github.com/galaxyproject/galaxy/pull/19211>`_
* Update visualizations to latest charts package by `@guerler <https://github.com/guerler>`_ in `#19213 <https://github.com/galaxyproject/galaxy/pull/19213>`_
* Fix UP031 errors - Part 3 by `@nsoranzo <https://github.com/nsoranzo>`_ in `#19218 <https://github.com/galaxyproject/galaxy/pull/19218>`_
* Add Vitessce Viewer by `@guerler <https://github.com/guerler>`_ in `#19227 <https://github.com/galaxyproject/galaxy/pull/19227>`_
* Fix UP031 errors - Part 4 by `@nsoranzo <https://github.com/nsoranzo>`_ in `#19235 <https://github.com/galaxyproject/galaxy/pull/19235>`_
* Explicitly add cwl-utils to dependencies by `@nsoranzo <https://github.com/nsoranzo>`_ in `#19257 <https://github.com/galaxyproject/galaxy/pull/19257>`_
* Refactor for better reuse of workflow parameter type constants by `@nsoranzo <https://github.com/nsoranzo>`_ in `#19260 <https://github.com/galaxyproject/galaxy/pull/19260>`_
* Fix UP031 errors - Part 5 by `@nsoranzo <https://github.com/nsoranzo>`_ in `#19282 <https://github.com/galaxyproject/galaxy/pull/19282>`_
* Workflow Run Form Enhancements by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#19294 <https://github.com/galaxyproject/galaxy/pull/19294>`_
* Minor drag style adjustment for activities by `@guerler <https://github.com/guerler>`_ in `#19299 <https://github.com/galaxyproject/galaxy/pull/19299>`_
* Extract and typescript-ify datatype selection in wfeditor. by `@jmchilton <https://github.com/jmchilton>`_ in `#19304 <https://github.com/galaxyproject/galaxy/pull/19304>`_
* Migrate WF Collection Input Form Definition to Client Side by `@jmchilton <https://github.com/jmchilton>`_ in `#19313 <https://github.com/galaxyproject/galaxy/pull/19313>`_
* Fix UP031 errors - Part 6 by `@nsoranzo <https://github.com/nsoranzo>`_ in `#19314 <https://github.com/galaxyproject/galaxy/pull/19314>`_
* eLabFTW integration via Galaxy file source by `@kysrpex <https://github.com/kysrpex>`_ in `#19319 <https://github.com/galaxyproject/galaxy/pull/19319>`_
* Update pydantic to 2.10.3 by `@nsoranzo <https://github.com/nsoranzo>`_ in `#19326 <https://github.com/galaxyproject/galaxy/pull/19326>`_
* Add workflow selection and bulk actions by `@itisAliRH <https://github.com/itisAliRH>`_ in `#19336 <https://github.com/galaxyproject/galaxy/pull/19336>`_
* Refactor and add tests for Popovers by `@guerler <https://github.com/guerler>`_ in `#19337 <https://github.com/galaxyproject/galaxy/pull/19337>`_
* Use popper wrapper for help text popover by `@guerler <https://github.com/guerler>`_ in `#19340 <https://github.com/galaxyproject/galaxy/pull/19340>`_
* Misc fixes 202412 by `@nsoranzo <https://github.com/nsoranzo>`_ in `#19341 <https://github.com/galaxyproject/galaxy/pull/19341>`_
* Rework some form components for reuse. by `@jmchilton <https://github.com/jmchilton>`_ in `#19347 <https://github.com/galaxyproject/galaxy/pull/19347>`_
* Hide outdated visualizations from visualizations activity panel by `@guerler <https://github.com/guerler>`_ in `#19353 <https://github.com/galaxyproject/galaxy/pull/19353>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#19366 <https://github.com/galaxyproject/galaxy/pull/19366>`_
* Add Dataverse RDM repository integration by `@KaiOnGitHub <https://github.com/KaiOnGitHub>`_ in `#19367 <https://github.com/galaxyproject/galaxy/pull/19367>`_
* Type annotation fixes for mypy 1.14.0 by `@nsoranzo <https://github.com/nsoranzo>`_ in `#19372 <https://github.com/galaxyproject/galaxy/pull/19372>`_
* Make conditional discriminators literals instead of generic string/bool by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19374 <https://github.com/galaxyproject/galaxy/pull/19374>`_
* Empower Users to Build More Kinds of Collections, More Intelligently by `@jmchilton <https://github.com/jmchilton>`_ in `#19377 <https://github.com/galaxyproject/galaxy/pull/19377>`_
* Remove apptainer-version pin by `@nsoranzo <https://github.com/nsoranzo>`_ in `#19380 <https://github.com/galaxyproject/galaxy/pull/19380>`_
* Clarify that extra_scopes is sometimes non-optional by `@martenson <https://github.com/martenson>`_ in `#19385 <https://github.com/galaxyproject/galaxy/pull/19385>`_
* SQLAlchemy 2.0 follow-up by `@jdavcs <https://github.com/jdavcs>`_ in `#19388 <https://github.com/galaxyproject/galaxy/pull/19388>`_
* Documentation around highlighting PRs for release notes. by `@jmchilton <https://github.com/jmchilton>`_ in `#19390 <https://github.com/galaxyproject/galaxy/pull/19390>`_
* Change galaxy system user uid for K8s image by `@afgane <https://github.com/afgane>`_ in `#19403 <https://github.com/galaxyproject/galaxy/pull/19403>`_
* Gulp build improvements, update. by `@dannon <https://github.com/dannon>`_ in `#19405 <https://github.com/galaxyproject/galaxy/pull/19405>`_
* Set safe default extraction filter for tar archives by `@nsoranzo <https://github.com/nsoranzo>`_ in `#19406 <https://github.com/galaxyproject/galaxy/pull/19406>`_
* Remove transaction helper by `@jdavcs <https://github.com/jdavcs>`_ in `#19407 <https://github.com/galaxyproject/galaxy/pull/19407>`_
* Prevent users from reusing a banned email after account is purged by `@jdavcs <https://github.com/jdavcs>`_ in `#19413 <https://github.com/galaxyproject/galaxy/pull/19413>`_
* Irods objectstore templates by `@pauldg <https://github.com/pauldg>`_ in `#19415 <https://github.com/galaxyproject/galaxy/pull/19415>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#19418 <https://github.com/galaxyproject/galaxy/pull/19418>`_
* Enable cloning subworkflows by `@ElectronicBlueberry <https://github.com/ElectronicBlueberry>`_ in `#19420 <https://github.com/galaxyproject/galaxy/pull/19420>`_
* Allow controlling strict channel priority in mulled-build by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#19425 <https://github.com/galaxyproject/galaxy/pull/19425>`_
* Add IGB display support for CRAM files by `@paige-kulzer <https://github.com/paige-kulzer>`_ in `#19428 <https://github.com/galaxyproject/galaxy/pull/19428>`_
* Document `$__user_name__` by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#19433 <https://github.com/galaxyproject/galaxy/pull/19433>`_
* Add User-Defined Tools by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19434 <https://github.com/galaxyproject/galaxy/pull/19434>`_
* Type annotations improvements by `@nsoranzo <https://github.com/nsoranzo>`_ in `#19442 <https://github.com/galaxyproject/galaxy/pull/19442>`_
* Handles S3 listing errors by `@itisAliRH <https://github.com/itisAliRH>`_ in `#19446 <https://github.com/galaxyproject/galaxy/pull/19446>`_
* Improve asynchronous tasks error handling and reporting by `@davelopez <https://github.com/davelopez>`_ in `#19448 <https://github.com/galaxyproject/galaxy/pull/19448>`_
* Reset invocation export wizard after completion by `@davelopez <https://github.com/davelopez>`_ in `#19449 <https://github.com/galaxyproject/galaxy/pull/19449>`_
* Workflow Editor Auto Zoom by `@ElectronicBlueberry <https://github.com/ElectronicBlueberry>`_ in `#19451 <https://github.com/galaxyproject/galaxy/pull/19451>`_
* Update main citation to 2024 community paper by `@nsoranzo <https://github.com/nsoranzo>`_ in `#19453 <https://github.com/galaxyproject/galaxy/pull/19453>`_
* Add test that verifies workflow source_metadata is preserved on landing claim by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19454 <https://github.com/galaxyproject/galaxy/pull/19454>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#19464 <https://github.com/galaxyproject/galaxy/pull/19464>`_
* Type annotation improvements by `@nsoranzo <https://github.com/nsoranzo>`_ in `#19485 <https://github.com/galaxyproject/galaxy/pull/19485>`_
* Add eLabFTW file source from file source templates by `@kysrpex <https://github.com/kysrpex>`_ in `#19493 <https://github.com/galaxyproject/galaxy/pull/19493>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#19510 <https://github.com/galaxyproject/galaxy/pull/19510>`_
* Remote File Sources and Storage Locations redesign by `@itisAliRH <https://github.com/itisAliRH>`_ in `#19521 <https://github.com/galaxyproject/galaxy/pull/19521>`_
* Support setting and displaying timezone with the core metrics plugin by `@natefoo <https://github.com/natefoo>`_ in `#19527 <https://github.com/galaxyproject/galaxy/pull/19527>`_
* Allow to send notifications when Admins cancel jobs by `@davelopez <https://github.com/davelopez>`_ in `#19547 <https://github.com/galaxyproject/galaxy/pull/19547>`_
* Add config options for tool dependency installs by `@afgane <https://github.com/afgane>`_ in `#19565 <https://github.com/galaxyproject/galaxy/pull/19565>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#19567 <https://github.com/galaxyproject/galaxy/pull/19567>`_
* Remove tags used by `@ElectronicBlueberry <https://github.com/ElectronicBlueberry>`_ in `#19576 <https://github.com/galaxyproject/galaxy/pull/19576>`_
* Support setting masthead height in a theme by `@ksuderman <https://github.com/ksuderman>`_ in `#19581 <https://github.com/galaxyproject/galaxy/pull/19581>`_
* Expand workflow metadata for readme.  by `@jmchilton <https://github.com/jmchilton>`_ in `#19591 <https://github.com/galaxyproject/galaxy/pull/19591>`_
* Add vue-tsc baseline comparison to client-lint workflow by `@dannon <https://github.com/dannon>`_ in `#19593 <https://github.com/galaxyproject/galaxy/pull/19593>`_
* Add failed jobs working directory cleanup as a celery periodic task by `@sanjaysrikakulam <https://github.com/sanjaysrikakulam>`_ in `#19594 <https://github.com/galaxyproject/galaxy/pull/19594>`_
* Enhance OpenAI Chat Integration by `@uwwint <https://github.com/uwwint>`_ in `#19612 <https://github.com/galaxyproject/galaxy/pull/19612>`_
* Add InvenioRDM file source template by `@davelopez <https://github.com/davelopez>`_ in `#19619 <https://github.com/galaxyproject/galaxy/pull/19619>`_
* Use discriminated unions in object stores and file source template configs by `@davelopez <https://github.com/davelopez>`_ in `#19621 <https://github.com/galaxyproject/galaxy/pull/19621>`_
* Use correct `plugin_kind` in user file sources by `@davelopez <https://github.com/davelopez>`_ in `#19622 <https://github.com/galaxyproject/galaxy/pull/19622>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#19623 <https://github.com/galaxyproject/galaxy/pull/19623>`_
* Format code with black 25.1.0 by `@nsoranzo <https://github.com/nsoranzo>`_ in `#19625 <https://github.com/galaxyproject/galaxy/pull/19625>`_
* Add Zenodo file source template by `@davelopez <https://github.com/davelopez>`_ in `#19638 <https://github.com/galaxyproject/galaxy/pull/19638>`_
* Type annotation improvements by `@nsoranzo <https://github.com/nsoranzo>`_ in `#19642 <https://github.com/galaxyproject/galaxy/pull/19642>`_
* Workflow landing request - collapse activity bar by default. by `@dannon <https://github.com/dannon>`_ in `#19652 <https://github.com/galaxyproject/galaxy/pull/19652>`_
* Enhance ListHeader Component for Reusability by `@itisAliRH <https://github.com/itisAliRH>`_ in `#19655 <https://github.com/galaxyproject/galaxy/pull/19655>`_
* Add Breadcrumb Heading Component by `@itisAliRH <https://github.com/itisAliRH>`_ in `#19656 <https://github.com/galaxyproject/galaxy/pull/19656>`_
* Mention default values for truevalue and falsevalue by `@pvanheus <https://github.com/pvanheus>`_ in `#19657 <https://github.com/galaxyproject/galaxy/pull/19657>`_
* Update test_create_dataset_in_subfolder to check for the dataset presence by `@davelopez <https://github.com/davelopez>`_ in `#19660 <https://github.com/galaxyproject/galaxy/pull/19660>`_
* Relax job status check in test_delete_user_cancel_all_jobs by `@davelopez <https://github.com/davelopez>`_ in `#19661 <https://github.com/galaxyproject/galaxy/pull/19661>`_
* Refactor dependencies for tool output actions. by `@jmchilton <https://github.com/jmchilton>`_ in `#19662 <https://github.com/galaxyproject/galaxy/pull/19662>`_
* More Vue Typescript Fixes by `@jmchilton <https://github.com/jmchilton>`_ in `#19663 <https://github.com/galaxyproject/galaxy/pull/19663>`_
* Click to edit history name in `HistoryPanel` by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#19665 <https://github.com/galaxyproject/galaxy/pull/19665>`_
* Generate correct types for Dataset source transformations on backend. by `@jmchilton <https://github.com/jmchilton>`_ in `#19666 <https://github.com/galaxyproject/galaxy/pull/19666>`_
* Remove unused(?) data_dialog form element type. by `@jmchilton <https://github.com/jmchilton>`_ in `#19669 <https://github.com/galaxyproject/galaxy/pull/19669>`_
* Add webdavclient3 to conditional-requirements.txt by `@bgruening <https://github.com/bgruening>`_ in `#19671 <https://github.com/galaxyproject/galaxy/pull/19671>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#19682 <https://github.com/galaxyproject/galaxy/pull/19682>`_
* Drop support for Python 3.8 by `@nsoranzo <https://github.com/nsoranzo>`_ in `#19685 <https://github.com/galaxyproject/galaxy/pull/19685>`_
* Define simple models for job messages. by `@jmchilton <https://github.com/jmchilton>`_ in `#19688 <https://github.com/galaxyproject/galaxy/pull/19688>`_
* Data-source tool for DICED database (https://diced.lerner.ccf.org/) added. by `@jaidevjoshi83 <https://github.com/jaidevjoshi83>`_ in `#19689 <https://github.com/galaxyproject/galaxy/pull/19689>`_
* Add forgotten linter test by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#19690 <https://github.com/galaxyproject/galaxy/pull/19690>`_
* Fix MarkdownDialog types by `@davelopez <https://github.com/davelopez>`_ in `#19703 <https://github.com/galaxyproject/galaxy/pull/19703>`_
* Move RequiredAppT back into galaxy packages. by `@jmchilton <https://github.com/jmchilton>`_ in `#19704 <https://github.com/galaxyproject/galaxy/pull/19704>`_
* Use model classes from ``galaxy.model`` instead of ``app.model`` object - Part 1 by `@nsoranzo <https://github.com/nsoranzo>`_ in `#19706 <https://github.com/galaxyproject/galaxy/pull/19706>`_
* Improved simplicity and isolation in transiently failing test. by `@jmchilton <https://github.com/jmchilton>`_ in `#19709 <https://github.com/galaxyproject/galaxy/pull/19709>`_
* Update RStudio IT by `@afgane <https://github.com/afgane>`_ in `#19711 <https://github.com/galaxyproject/galaxy/pull/19711>`_
* Speedup mulled build test by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#19712 <https://github.com/galaxyproject/galaxy/pull/19712>`_
* Update TypeScript version to 5.7.3 by `@davelopez <https://github.com/davelopez>`_ in `#19713 <https://github.com/galaxyproject/galaxy/pull/19713>`_
* Augments popper wrapper, add click and escape handler by `@guerler <https://github.com/guerler>`_ in `#19717 <https://github.com/galaxyproject/galaxy/pull/19717>`_
* Move vega wrapper to shared common directory and add error handler by `@guerler <https://github.com/guerler>`_ in `#19718 <https://github.com/galaxyproject/galaxy/pull/19718>`_
* Move Markdown components to subdirectory for modularity by `@guerler <https://github.com/guerler>`_ in `#19719 <https://github.com/galaxyproject/galaxy/pull/19719>`_
* Rucio templates by `@SergeyYakubov <https://github.com/SergeyYakubov>`_ in `#19720 <https://github.com/galaxyproject/galaxy/pull/19720>`_
* Preserve workflow labels in final invocation reports by `@guerler <https://github.com/guerler>`_ in `#19721 <https://github.com/galaxyproject/galaxy/pull/19721>`_
* ToolShed 2.1 - Various bugfixes and enhancements.  by `@jmchilton <https://github.com/jmchilton>`_ in `#19722 <https://github.com/galaxyproject/galaxy/pull/19722>`_
* Use model classes from ``galaxy.model`` instead of ``app.model`` object - Part 2 by `@nsoranzo <https://github.com/nsoranzo>`_ in `#19726 <https://github.com/galaxyproject/galaxy/pull/19726>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#19727 <https://github.com/galaxyproject/galaxy/pull/19727>`_
* Add a script to reorganize tool data based on the new layout for genomic Data Managers by `@natefoo <https://github.com/natefoo>`_ in `#19728 <https://github.com/galaxyproject/galaxy/pull/19728>`_
* Move history watcher and minor fixes by `@guerler <https://github.com/guerler>`_ in `#19732 <https://github.com/galaxyproject/galaxy/pull/19732>`_
* Fix Tours and add tooltips to history items by `@guerler <https://github.com/guerler>`_ in `#19734 <https://github.com/galaxyproject/galaxy/pull/19734>`_
* Show workflow help (and readme?) in run form by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#19736 <https://github.com/galaxyproject/galaxy/pull/19736>`_
* Enhance breadcrumb navigation UX in small screen sizes by `@itisAliRH <https://github.com/itisAliRH>`_ in `#19737 <https://github.com/galaxyproject/galaxy/pull/19737>`_
* ToolShed2 - Add more context when navigating between tools an repositories. by `@jmchilton <https://github.com/jmchilton>`_ in `#19738 <https://github.com/galaxyproject/galaxy/pull/19738>`_
* Improvements to package decomposition.  by `@jmchilton <https://github.com/jmchilton>`_ in `#19759 <https://github.com/galaxyproject/galaxy/pull/19759>`_
* Add cell-based markdown editor for pages by `@guerler <https://github.com/guerler>`_ in `#19769 <https://github.com/galaxyproject/galaxy/pull/19769>`_
* Rename tool "Citations" to "References" by `@nsoranzo <https://github.com/nsoranzo>`_ in `#19770 <https://github.com/galaxyproject/galaxy/pull/19770>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#19772 <https://github.com/galaxyproject/galaxy/pull/19772>`_
* Add visualization framework interface to cell-based markdown editor by `@guerler <https://github.com/guerler>`_ in `#19775 <https://github.com/galaxyproject/galaxy/pull/19775>`_
* Allow overriding datatypes for planemo lint by `@selten <https://github.com/selten>`_ in `#19780 <https://github.com/galaxyproject/galaxy/pull/19780>`_
* Introduce reusable GCard component for unified card layout by `@itisAliRH <https://github.com/itisAliRH>`_ in `#19785 <https://github.com/galaxyproject/galaxy/pull/19785>`_
* Add history sharing and accessibility management view by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#19786 <https://github.com/galaxyproject/galaxy/pull/19786>`_
* Add bigbed to bed converter and tests by `@d-callan <https://github.com/d-callan>`_ in `#19787 <https://github.com/galaxyproject/galaxy/pull/19787>`_
* xsd: use CollectionType for collections in tests by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#19802 <https://github.com/galaxyproject/galaxy/pull/19802>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#19816 <https://github.com/galaxyproject/galaxy/pull/19816>`_
* Workflow Run Form Enhancements follow up by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#19825 <https://github.com/galaxyproject/galaxy/pull/19825>`_
* More user feedback in FormRulesEdit (for Apply Rules tool) by `@jmchilton <https://github.com/jmchilton>`_ in `#19827 <https://github.com/galaxyproject/galaxy/pull/19827>`_
* Use direct icon references in FormSelectMany.vue. by `@jmchilton <https://github.com/jmchilton>`_ in `#19829 <https://github.com/galaxyproject/galaxy/pull/19829>`_
* Populate image metadata without allocating memory for the entire image content by `@kostrykin <https://github.com/kostrykin>`_ in `#19830 <https://github.com/galaxyproject/galaxy/pull/19830>`_
* Syntactic sugar to ease TPV configuration. by `@jmchilton <https://github.com/jmchilton>`_ in `#19834 <https://github.com/galaxyproject/galaxy/pull/19834>`_
* Improve markdown editor modularity and structure by `@guerler <https://github.com/guerler>`_ in `#19835 <https://github.com/galaxyproject/galaxy/pull/19835>`_
* Add mandatory RO-Crate metadata when exporting by `@elichad <https://github.com/elichad>`_ in `#19846 <https://github.com/galaxyproject/galaxy/pull/19846>`_
* Enable lazy loading for ace-builds by `@ElectronicBlueberry <https://github.com/ElectronicBlueberry>`_ in `#19847 <https://github.com/galaxyproject/galaxy/pull/19847>`_
* Add basic support for icons in tools by `@davelopez <https://github.com/davelopez>`_ in `#19850 <https://github.com/galaxyproject/galaxy/pull/19850>`_
* Webpack build performance improvements by `@dannon <https://github.com/dannon>`_ in `#19851 <https://github.com/galaxyproject/galaxy/pull/19851>`_
* Improve type annotations of ``ModelPersistenceContext`` and derived classes by `@nsoranzo <https://github.com/nsoranzo>`_ in `#19852 <https://github.com/galaxyproject/galaxy/pull/19852>`_
* Client circular dependency check by `@dannon <https://github.com/dannon>`_ in `#19858 <https://github.com/galaxyproject/galaxy/pull/19858>`_
* Migrate from Prism to Monaco for ToolSource display. by `@dannon <https://github.com/dannon>`_ in `#19861 <https://github.com/galaxyproject/galaxy/pull/19861>`_
* Drop old galaxy_session records by `@jdavcs <https://github.com/jdavcs>`_ in `#19872 <https://github.com/galaxyproject/galaxy/pull/19872>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#19874 <https://github.com/galaxyproject/galaxy/pull/19874>`_
* Add Tapis auth support by `@dannon <https://github.com/dannon>`_ in `#19887 <https://github.com/galaxyproject/galaxy/pull/19887>`_
* Make preferences drop down available in single user deployments by `@ksuderman <https://github.com/ksuderman>`_ in `#19888 <https://github.com/galaxyproject/galaxy/pull/19888>`_
* Clarify is_active method usage for Python Social Auth in Galaxy by `@dannon <https://github.com/dannon>`_ in `#19899 <https://github.com/galaxyproject/galaxy/pull/19899>`_
* FITS Graph Viewer - script name tweak. by `@dannon <https://github.com/dannon>`_ in `#19902 <https://github.com/galaxyproject/galaxy/pull/19902>`_
* Improve docs for output filters by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#19904 <https://github.com/galaxyproject/galaxy/pull/19904>`_
* Various styling improvements to Workflow Run and Invocation views by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#19905 <https://github.com/galaxyproject/galaxy/pull/19905>`_
* Overhaul workflow runtime settings display. by `@dannon <https://github.com/dannon>`_ in `#19906 <https://github.com/galaxyproject/galaxy/pull/19906>`_
* Allow embedding vitessce visualizations by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19909 <https://github.com/galaxyproject/galaxy/pull/19909>`_
* Replace backend-based page creation controller endpoint by `@guerler <https://github.com/guerler>`_ in `#19914 <https://github.com/galaxyproject/galaxy/pull/19914>`_
* Remove unnecessary code duplications by `@nsoranzo <https://github.com/nsoranzo>`_ in `#19921 <https://github.com/galaxyproject/galaxy/pull/19921>`_
* Migrate Page editing controller endpoint to API by `@guerler <https://github.com/guerler>`_ in `#19923 <https://github.com/galaxyproject/galaxy/pull/19923>`_
* RStudio IT updates to work on .org by `@afgane <https://github.com/afgane>`_ in `#19924 <https://github.com/galaxyproject/galaxy/pull/19924>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#19929 <https://github.com/galaxyproject/galaxy/pull/19929>`_
* Show pre-populated landing data values in workflow run form by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#19935 <https://github.com/galaxyproject/galaxy/pull/19935>`_
* Drop old job metrics by `@jdavcs <https://github.com/jdavcs>`_ in `#19936 <https://github.com/galaxyproject/galaxy/pull/19936>`_
* Fix local import in ``__resolvers_dict`` by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19944 <https://github.com/galaxyproject/galaxy/pull/19944>`_
* First steps of bootstrap replacement by `@ElectronicBlueberry <https://github.com/ElectronicBlueberry>`_ in `#19946 <https://github.com/galaxyproject/galaxy/pull/19946>`_
* Decrease sentry_sdk.errors log level to INFO by `@natefoo <https://github.com/natefoo>`_ in `#19951 <https://github.com/galaxyproject/galaxy/pull/19951>`_
* Allow PathLike parameters in ``make_fast_zipfile()`` by `@nsoranzo <https://github.com/nsoranzo>`_ in `#19955 <https://github.com/galaxyproject/galaxy/pull/19955>`_
* Add link to view history on dataset info page by `@natefoo <https://github.com/natefoo>`_ in `#19956 <https://github.com/galaxyproject/galaxy/pull/19956>`_
* Allow resizing Visualizations in Markdown editor by `@guerler <https://github.com/guerler>`_ in `#19958 <https://github.com/galaxyproject/galaxy/pull/19958>`_
* Add share button for invocations by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#19959 <https://github.com/galaxyproject/galaxy/pull/19959>`_
* Add type hints around collection copying and job things by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19961 <https://github.com/galaxyproject/galaxy/pull/19961>`_
* Job cache allow different names when possible by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19962 <https://github.com/galaxyproject/galaxy/pull/19962>`_
* Button replacement batch 1 by `@ElectronicBlueberry <https://github.com/ElectronicBlueberry>`_ in `#19963 <https://github.com/galaxyproject/galaxy/pull/19963>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#19964 <https://github.com/galaxyproject/galaxy/pull/19964>`_
* Adds a trimInputs prop to FormGeneric to trim string values on submit. by `@dannon <https://github.com/dannon>`_ in `#19971 <https://github.com/galaxyproject/galaxy/pull/19971>`_
* Add Katex Equation rendering plugin to Markdown Editor by `@guerler <https://github.com/guerler>`_ in `#19988 <https://github.com/galaxyproject/galaxy/pull/19988>`_
* Allow different AI providers (as long as they are openai compatible) by `@uwwint <https://github.com/uwwint>`_ in `#19989 <https://github.com/galaxyproject/galaxy/pull/19989>`_
* Button replacement batch 2 by `@ElectronicBlueberry <https://github.com/ElectronicBlueberry>`_ in `#19990 <https://github.com/galaxyproject/galaxy/pull/19990>`_
* Improve type annotation of tool parameter wrapping by `@nsoranzo <https://github.com/nsoranzo>`_ in `#19991 <https://github.com/galaxyproject/galaxy/pull/19991>`_
* Add Niivue viewer by `@guerler <https://github.com/guerler>`_ in `#19995 <https://github.com/galaxyproject/galaxy/pull/19995>`_
* IT Activity Panel by `@dannon <https://github.com/dannon>`_ in `#19996 <https://github.com/galaxyproject/galaxy/pull/19996>`_
* Selenium test cases for running workflow from form upload. by `@jmchilton <https://github.com/jmchilton>`_ in `#19997 <https://github.com/galaxyproject/galaxy/pull/19997>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#19998 <https://github.com/galaxyproject/galaxy/pull/19998>`_
* Restore Visualization insertion options in Reports Editor by `@guerler <https://github.com/guerler>`_ in `#20000 <https://github.com/galaxyproject/galaxy/pull/20000>`_
* Implement dataset collection support in workflow landing requests by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20004 <https://github.com/galaxyproject/galaxy/pull/20004>`_
* Add kepler.gl visualization by `@guerler <https://github.com/guerler>`_ in `#20005 <https://github.com/galaxyproject/galaxy/pull/20005>`_
* Enable ``warn_redundant_casts`` mypy option and drop redundant casts by `@nsoranzo <https://github.com/nsoranzo>`_ in `#20008 <https://github.com/galaxyproject/galaxy/pull/20008>`_
* Update vitessce version by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20016 <https://github.com/galaxyproject/galaxy/pull/20016>`_
* Merge Inputs/Parameters and Outputs/Collections Tabs by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#20019 <https://github.com/galaxyproject/galaxy/pull/20019>`_
* Show workflow README in split view next to the form inputs by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#20026 <https://github.com/galaxyproject/galaxy/pull/20026>`_
* Add vitesscejson datatype by `@guerler <https://github.com/guerler>`_ in `#20027 <https://github.com/galaxyproject/galaxy/pull/20027>`_
* Add VTK Visualization Toolkit Plugin by `@guerler <https://github.com/guerler>`_ in `#20028 <https://github.com/galaxyproject/galaxy/pull/20028>`_
* Move README to center panel in workflow editor by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#20029 <https://github.com/galaxyproject/galaxy/pull/20029>`_
* Add help text popovers for workflow runtime settings by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#20031 <https://github.com/galaxyproject/galaxy/pull/20031>`_
* Add rerun option for workflows by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#20032 <https://github.com/galaxyproject/galaxy/pull/20032>`_
* Add DOI to workflow metadata by `@jdavcs <https://github.com/jdavcs>`_ in `#20033 <https://github.com/galaxyproject/galaxy/pull/20033>`_
* Add support for Markdown help text in visualizations by `@guerler <https://github.com/guerler>`_ in `#20043 <https://github.com/galaxyproject/galaxy/pull/20043>`_
* Add sample datasets for visualizations by `@guerler <https://github.com/guerler>`_ in `#20046 <https://github.com/galaxyproject/galaxy/pull/20046>`_
* Add ZIP explorer to import individual files from local or remote ZIP archives by `@davelopez <https://github.com/davelopez>`_ in `#20054 <https://github.com/galaxyproject/galaxy/pull/20054>`_
* Add docx datatype by `@bgruening <https://github.com/bgruening>`_ in `#20055 <https://github.com/galaxyproject/galaxy/pull/20055>`_
* Add markdown datatype by `@bgruening <https://github.com/bgruening>`_ in `#20056 <https://github.com/galaxyproject/galaxy/pull/20056>`_
* Add flac audio format by `@bgruening <https://github.com/bgruening>`_ in `#20057 <https://github.com/galaxyproject/galaxy/pull/20057>`_
* Client refactorings ahead of #19377.   by `@jmchilton <https://github.com/jmchilton>`_ in `#20059 <https://github.com/galaxyproject/galaxy/pull/20059>`_
* Add rd datatype by `@richard-burhans <https://github.com/richard-burhans>`_ in `#20060 <https://github.com/galaxyproject/galaxy/pull/20060>`_
* GLink implementation by `@ElectronicBlueberry <https://github.com/ElectronicBlueberry>`_ in `#20063 <https://github.com/galaxyproject/galaxy/pull/20063>`_
* GCard Full Description by `@itisAliRH <https://github.com/itisAliRH>`_ in `#20064 <https://github.com/galaxyproject/galaxy/pull/20064>`_
* Enhance Storage Dashboard Selected Item UI by `@itisAliRH <https://github.com/itisAliRH>`_ in `#20070 <https://github.com/galaxyproject/galaxy/pull/20070>`_
* Add activity panel width to local storage by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#20072 <https://github.com/galaxyproject/galaxy/pull/20072>`_
* Hide non-functional and replaced visualizations (e.g. Nora, MSA) by `@guerler <https://github.com/guerler>`_ in `#20077 <https://github.com/galaxyproject/galaxy/pull/20077>`_
* Flexible mapping from collection parameter types to collection builder components. by `@jmchilton <https://github.com/jmchilton>`_ in `#20082 <https://github.com/galaxyproject/galaxy/pull/20082>`_
* Route to creating a new file source in remote file browser modal by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#20084 <https://github.com/galaxyproject/galaxy/pull/20084>`_
* Use visualization dropdown solely for examples by `@guerler <https://github.com/guerler>`_ in `#20094 <https://github.com/galaxyproject/galaxy/pull/20094>`_
* Set node version to 22.13.0 by `@davelopez <https://github.com/davelopez>`_ in `#20095 <https://github.com/galaxyproject/galaxy/pull/20095>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#20096 <https://github.com/galaxyproject/galaxy/pull/20096>`_
* Adds Example Datasets and Help Text for Visualizations by `@guerler <https://github.com/guerler>`_ in `#20097 <https://github.com/galaxyproject/galaxy/pull/20097>`_
* Enhance external login interface styling by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#20100 <https://github.com/galaxyproject/galaxy/pull/20100>`_
* Add Molstar by `@guerler <https://github.com/guerler>`_ in `#20101 <https://github.com/galaxyproject/galaxy/pull/20101>`_
* Improve type annotation of `galaxy.util` submodules by `@nsoranzo <https://github.com/nsoranzo>`_ in `#20104 <https://github.com/galaxyproject/galaxy/pull/20104>`_
* Add alignment.js for multiple sequence alignment rendering by `@guerler <https://github.com/guerler>`_ in `#20110 <https://github.com/galaxyproject/galaxy/pull/20110>`_
* Add specific datatypes for Cytoscape and Kepler.gl by `@guerler <https://github.com/guerler>`_ in `#20117 <https://github.com/galaxyproject/galaxy/pull/20117>`_
* Run integration tests on latest Ubuntu by `@nsoranzo <https://github.com/nsoranzo>`_ in `#20118 <https://github.com/galaxyproject/galaxy/pull/20118>`_
* Add role creation form by `@guerler <https://github.com/guerler>`_ in `#20119 <https://github.com/galaxyproject/galaxy/pull/20119>`_
* Migrate Transition Systems Visualization by `@guerler <https://github.com/guerler>`_ in `#20125 <https://github.com/galaxyproject/galaxy/pull/20125>`_
* Add logo, description and help for aequatus by `@guerler <https://github.com/guerler>`_ in `#20128 <https://github.com/galaxyproject/galaxy/pull/20128>`_
* Drop now unused controller method by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20129 <https://github.com/galaxyproject/galaxy/pull/20129>`_
* Add updated PCA plot by `@guerler <https://github.com/guerler>`_ in `#20140 <https://github.com/galaxyproject/galaxy/pull/20140>`_
* Browse multiple trees in phylocanvas by `@guerler <https://github.com/guerler>`_ in `#20141 <https://github.com/galaxyproject/galaxy/pull/20141>`_
* Add more metadata, esp `infer_from` to datatypes configuration by `@bgruening <https://github.com/bgruening>`_ in `#20142 <https://github.com/galaxyproject/galaxy/pull/20142>`_
* Show job ids on job success by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#20145 <https://github.com/galaxyproject/galaxy/pull/20145>`_
* Additional type hints for ``toolbox.get_tool`` / ``toolbox.has_tool`` by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20150 <https://github.com/galaxyproject/galaxy/pull/20150>`_
* Create working dir output outside of tool evaluator by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20153 <https://github.com/galaxyproject/galaxy/pull/20153>`_
* Improved rule builder display for non-nested lists (most of them). by `@jmchilton <https://github.com/jmchilton>`_ in `#20156 <https://github.com/galaxyproject/galaxy/pull/20156>`_
* Revise transiently failing data source test. by `@jmchilton <https://github.com/jmchilton>`_ in `#20157 <https://github.com/galaxyproject/galaxy/pull/20157>`_
* Yaml parser fixes and improvements (part 1) by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20158 <https://github.com/galaxyproject/galaxy/pull/20158>`_
* Fix remaining vue-tsc errors by `@dannon <https://github.com/dannon>`_ in `#20163 <https://github.com/galaxyproject/galaxy/pull/20163>`_
* Add three AAI providers by `@martenson <https://github.com/martenson>`_ in `#20165 <https://github.com/galaxyproject/galaxy/pull/20165>`_
* Add replacement_dataset option to collection filter tools by `@simonbray <https://github.com/simonbray>`_ in `#20166 <https://github.com/galaxyproject/galaxy/pull/20166>`_
* Implement file source to integrate Galaxy with RSpace by `@kysrpex <https://github.com/kysrpex>`_ in `#20167 <https://github.com/galaxyproject/galaxy/pull/20167>`_
* G modal implementation by `@ElectronicBlueberry <https://github.com/ElectronicBlueberry>`_ in `#20168 <https://github.com/galaxyproject/galaxy/pull/20168>`_
* Add client package by `@natefoo <https://github.com/natefoo>`_ in `#20171 <https://github.com/galaxyproject/galaxy/pull/20171>`_
* Add JupyterLite by `@guerler <https://github.com/guerler>`_ in `#20174 <https://github.com/galaxyproject/galaxy/pull/20174>`_
* Standalone Galaxy API Client Package by `@dannon <https://github.com/dannon>`_ in `#20181 <https://github.com/galaxyproject/galaxy/pull/20181>`_
* Add visualization test data by `@nilchia <https://github.com/nilchia>`_ in `#20183 <https://github.com/galaxyproject/galaxy/pull/20183>`_
* Bump vega from 5.30.0 to 5.32.0 in /client by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20188 <https://github.com/galaxyproject/galaxy/pull/20188>`_
* Visualization-First Display functionality by `@dannon <https://github.com/dannon>`_ in `#20190 <https://github.com/galaxyproject/galaxy/pull/20190>`_
* Improve type annotation of ``galaxy.model.dataset_collections`` by `@nsoranzo <https://github.com/nsoranzo>`_ in `#20194 <https://github.com/galaxyproject/galaxy/pull/20194>`_
* Have `make dist` in the web_client package build the client by `@natefoo <https://github.com/natefoo>`_ in `#20195 <https://github.com/galaxyproject/galaxy/pull/20195>`_
* Add plotly 6.0.1 to JupyterLite by `@guerler <https://github.com/guerler>`_ in `#20201 <https://github.com/galaxyproject/galaxy/pull/20201>`_
* Enable visualizations for anonymous user by `@guerler <https://github.com/guerler>`_ in `#20210 <https://github.com/galaxyproject/galaxy/pull/20210>`_
* Migrate ChiraViz by `@guerler <https://github.com/guerler>`_ in `#20214 <https://github.com/galaxyproject/galaxy/pull/20214>`_
* Display invocation inputs and outputs in workflow report by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20222 <https://github.com/galaxyproject/galaxy/pull/20222>`_
* Use TUS streaming and remove redundant IndexDB temp store in Zip Explorer by `@davelopez <https://github.com/davelopez>`_ in `#20226 <https://github.com/galaxyproject/galaxy/pull/20226>`_
* Add more descriptions to custom tool source schema by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20266 <https://github.com/galaxyproject/galaxy/pull/20266>`_
* Improve handling of very large files in Tabulator by `@guerler <https://github.com/guerler>`_ in `#20271 <https://github.com/galaxyproject/galaxy/pull/20271>`_
* Touch up Dataset View by `@guerler <https://github.com/guerler>`_ in `#20290 <https://github.com/galaxyproject/galaxy/pull/20290>`_
* Improve performance of job cache query by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20319 <https://github.com/galaxyproject/galaxy/pull/20319>`_
* Remove type import side-effects by `@ElectronicBlueberry <https://github.com/ElectronicBlueberry>`_ in `#20321 <https://github.com/galaxyproject/galaxy/pull/20321>`_
* Enable retrieving contents from extra file paths when request contains leading `/` by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20336 <https://github.com/galaxyproject/galaxy/pull/20336>`_
* DatasetView and Card Polish by `@dannon <https://github.com/dannon>`_ in `#20342 <https://github.com/galaxyproject/galaxy/pull/20342>`_
* Release notes by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#20386 <https://github.com/galaxyproject/galaxy/pull/20386>`_
* Deprecate ``enable_tool_document_cache`` by `@nsoranzo <https://github.com/nsoranzo>`_ in `#20433 <https://github.com/galaxyproject/galaxy/pull/20433>`_
* Update tiffviewer to latest version supporting more formats by `@davelopez <https://github.com/davelopez>`_ in `#20457 <https://github.com/galaxyproject/galaxy/pull/20457>`_
* Add Aladin as standard FITS viewer by `@bgruening <https://github.com/bgruening>`_ in `#20465 <https://github.com/galaxyproject/galaxy/pull/20465>`_
* Add molstar as default viewer for some molecule formats by `@bgruening <https://github.com/bgruening>`_ in `#20467 <https://github.com/galaxyproject/galaxy/pull/20467>`_
* Add ``/api/datasets/{dataset_id}/extra_files/raw/{filename:path}`` by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20468 <https://github.com/galaxyproject/galaxy/pull/20468>`_

=============
Other changes
=============

* Merge 24.2 into dev. by `@jmchilton <https://github.com/jmchilton>`_ in `#19273 <https://github.com/galaxyproject/galaxy/pull/19273>`_
* Fix package versions by `@jdavcs <https://github.com/jdavcs>`_ in `#19566 <https://github.com/galaxyproject/galaxy/pull/19566>`_
* Merge 24.2 into dev by `@jdavcs <https://github.com/jdavcs>`_ in `#19590 <https://github.com/galaxyproject/galaxy/pull/19590>`_
* Bump @babel/runtime-corejs3 from 7.23.2 to 7.26.10 in /client by `@dependabot[bot] <https://github.com/dependabot[bot]>`_ in `#19788 <https://github.com/galaxyproject/galaxy/pull/19788>`_
* Rebuild API schema for latest dev.  by `@jmchilton <https://github.com/jmchilton>`_ in `#19789 <https://github.com/galaxyproject/galaxy/pull/19789>`_
* Make job cache generally available by `@dannon <https://github.com/dannon>`_ in `#19798 <https://github.com/galaxyproject/galaxy/pull/19798>`_
* Fix workflow license component typing by `@guerler <https://github.com/guerler>`_ in `#19878 <https://github.com/galaxyproject/galaxy/pull/19878>`_
* Fix import and update_page type signature by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19932 <https://github.com/galaxyproject/galaxy/pull/19932>`_
* Merge 24.2 into dev by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#19933 <https://github.com/galaxyproject/galaxy/pull/19933>`_
* Log controller exceptions by `@natefoo <https://github.com/natefoo>`_ in `#19974 <https://github.com/galaxyproject/galaxy/pull/19974>`_
* Fix copying job output from discovered outputs by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19999 <https://github.com/galaxyproject/galaxy/pull/19999>`_
* Add env var to skip CircularDependencyPlugin in development mode by `@dannon <https://github.com/dannon>`_ in `#20038 <https://github.com/galaxyproject/galaxy/pull/20038>`_
* Bump h11 from 0.14.0 to 0.16.0 in /lib/galaxy/dependencies by `@dependabot[bot] <https://github.com/dependabot[bot]>`_ in `#20088 <https://github.com/galaxyproject/galaxy/pull/20088>`_
* Fix formatting in webapp and client/install.py by `@dannon <https://github.com/dannon>`_ in `#20185 <https://github.com/galaxyproject/galaxy/pull/20185>`_
* Bump default milestone to 25.1 by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20189 <https://github.com/galaxyproject/galaxy/pull/20189>`_
* Bump axios from 1.7.4 to 1.8.2 in /client by `@dependabot[bot] <https://github.com/dependabot[bot]>`_ in `#20205 <https://github.com/galaxyproject/galaxy/pull/20205>`_
* Bug fixes around wizard usage. by `@jmchilton <https://github.com/jmchilton>`_ in `#20224 <https://github.com/galaxyproject/galaxy/pull/20224>`_
* Bug fix - allow file drops into PasteData widget. by `@jmchilton <https://github.com/jmchilton>`_ in `#20232 <https://github.com/galaxyproject/galaxy/pull/20232>`_
* Only show custom tool editor in activity bar settings when user has access by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20247 <https://github.com/galaxyproject/galaxy/pull/20247>`_
* Fix job rerun for dynamic tools by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20259 <https://github.com/galaxyproject/galaxy/pull/20259>`_
* Add 25.0 migration tags by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#20265 <https://github.com/galaxyproject/galaxy/pull/20265>`_
* Update version to 25.0.rc1 by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#20267 <https://github.com/galaxyproject/galaxy/pull/20267>`_
* Bug fix - auto-pairing step not connected to collection builder in wizard. by `@jmchilton <https://github.com/jmchilton>`_ in `#20345 <https://github.com/galaxyproject/galaxy/pull/20345>`_
* Fix minor IT panel/display issues by `@dannon <https://github.com/dannon>`_ in `#20404 <https://github.com/galaxyproject/galaxy/pull/20404>`_
* Rename vitessce_json file_ext to vitessce.json by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20473 <https://github.com/galaxyproject/galaxy/pull/20473>`_

-------------------
24.2.4 (2025-06-17)
-------------------


=========
Bug fixes
=========

* Fix #19515 - invalid citation handling changed with 24.2. by `@jmchilton <https://github.com/jmchilton>`_ in `#19716 <https://github.com/galaxyproject/galaxy/pull/19716>`_
* Fix collection builder input states by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19797 <https://github.com/galaxyproject/galaxy/pull/19797>`_
* Reduce default framework tool test timeout to 60 seconds by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19819 <https://github.com/galaxyproject/galaxy/pull/19819>`_
* Backport #19810: Fix workflow param tests not updating param type. by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19820 <https://github.com/galaxyproject/galaxy/pull/19820>`_
* Fix various job concurrency limit issues by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19824 <https://github.com/galaxyproject/galaxy/pull/19824>`_
* Do not reorder options in FormSelect component when multiselect disabled by `@jdavcs <https://github.com/jdavcs>`_ in `#19837 <https://github.com/galaxyproject/galaxy/pull/19837>`_
* Decode/encode FormDirectory paths to allow spaces (and other characters) by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#19841 <https://github.com/galaxyproject/galaxy/pull/19841>`_
* Try to recover from recurring activation link error by `@jdavcs <https://github.com/jdavcs>`_ in `#19844 <https://github.com/galaxyproject/galaxy/pull/19844>`_
* Add spacing between workflow author and invocation count by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#19849 <https://github.com/galaxyproject/galaxy/pull/19849>`_
* Fix default ordering of items sorted by name by `@jdavcs <https://github.com/jdavcs>`_ in `#19853 <https://github.com/galaxyproject/galaxy/pull/19853>`_
* Handle directories with percents directories with export_remote.xml. by `@jmchilton <https://github.com/jmchilton>`_ in `#19865 <https://github.com/galaxyproject/galaxy/pull/19865>`_
* Fix drag and drop for dataset collection elements by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#19866 <https://github.com/galaxyproject/galaxy/pull/19866>`_
* Don't collect unnamed outputs twice in extended metadata mode by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19868 <https://github.com/galaxyproject/galaxy/pull/19868>`_
* Check if index exists before creating by `@jdavcs <https://github.com/jdavcs>`_ in `#19873 <https://github.com/galaxyproject/galaxy/pull/19873>`_
* Lazy-load invocation step jobs as needed by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19877 <https://github.com/galaxyproject/galaxy/pull/19877>`_
* Fix tabular metadata setting on pulsar with remote metadata by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19891 <https://github.com/galaxyproject/galaxy/pull/19891>`_
* Skip ``data_meta`` filter in run form by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19895 <https://github.com/galaxyproject/galaxy/pull/19895>`_
* Drop unused alembic-utils from galaxy-data package requirements by `@nsoranzo <https://github.com/nsoranzo>`_ in `#19896 <https://github.com/galaxyproject/galaxy/pull/19896>`_
* Fix duplicate extensions for data inputs by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#19903 <https://github.com/galaxyproject/galaxy/pull/19903>`_
* Skip implicit HDA conversions in DataToolParameter options by `@davelopez <https://github.com/davelopez>`_ in `#19911 <https://github.com/galaxyproject/galaxy/pull/19911>`_
* Fix duplicate entries when using drag and drop in multiple mode by `@davelopez <https://github.com/davelopez>`_ in `#19913 <https://github.com/galaxyproject/galaxy/pull/19913>`_
* Let pysam use extra threads available in job by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19917 <https://github.com/galaxyproject/galaxy/pull/19917>`_
* Handle special charater in raw SQL by `@jdavcs <https://github.com/jdavcs>`_ in `#19925 <https://github.com/galaxyproject/galaxy/pull/19925>`_
* Report TestCaseValidation as linter error for 24.2 and above by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#19928 <https://github.com/galaxyproject/galaxy/pull/19928>`_
* Better interactive tool entry point query by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19942 <https://github.com/galaxyproject/galaxy/pull/19942>`_
* Drop unnecessary job cache job subquery by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19945 <https://github.com/galaxyproject/galaxy/pull/19945>`_
* Use ``make_fast_zipfile`` directly by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19947 <https://github.com/galaxyproject/galaxy/pull/19947>`_
* Fix attempt restriction on multiple connections by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19948 <https://github.com/galaxyproject/galaxy/pull/19948>`_
* Fix various parameter validation issues. by `@jmchilton <https://github.com/jmchilton>`_ in `#19949 <https://github.com/galaxyproject/galaxy/pull/19949>`_
* Sort intersected options by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19953 <https://github.com/galaxyproject/galaxy/pull/19953>`_
* Do not print OIDC access tokens to the logs by `@kysrpex <https://github.com/kysrpex>`_ in `#19966 <https://github.com/galaxyproject/galaxy/pull/19966>`_
* Renew OIDC access tokens using valid refresh tokens by `@kysrpex <https://github.com/kysrpex>`_ in `#19967 <https://github.com/galaxyproject/galaxy/pull/19967>`_
* Fix bug in psa-authnz redirect handling by `@dannon <https://github.com/dannon>`_ in `#19968 <https://github.com/galaxyproject/galaxy/pull/19968>`_
* Add missing job state history entry for queued state by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19977 <https://github.com/galaxyproject/galaxy/pull/19977>`_
* Restrict job cache to terminal jobs (and other fixes) by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19978 <https://github.com/galaxyproject/galaxy/pull/19978>`_
* Do not display default labels obscuring selectable options in a vue-multiselect component by `@jdavcs <https://github.com/jdavcs>`_ in `#19981 <https://github.com/galaxyproject/galaxy/pull/19981>`_
* Fix dynamic filter option access when building command line by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19982 <https://github.com/galaxyproject/galaxy/pull/19982>`_
* Always set copy_elements to true by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19985 <https://github.com/galaxyproject/galaxy/pull/19985>`_
* ChatGXY Error Handling by `@dannon <https://github.com/dannon>`_ in `#19987 <https://github.com/galaxyproject/galaxy/pull/19987>`_
* Ensure job states are fetched in invocation view by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#20010 <https://github.com/galaxyproject/galaxy/pull/20010>`_
* Renew access tokens from PSA using valid refresh tokens by `@kysrpex <https://github.com/kysrpex>`_ in `#20040 <https://github.com/galaxyproject/galaxy/pull/20040>`_
* Fix edit permission for datasets delete button in storage dashboard overview by location by `@itisAliRH <https://github.com/itisAliRH>`_ in `#20066 <https://github.com/galaxyproject/galaxy/pull/20066>`_
* Job cache backports by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20078 <https://github.com/galaxyproject/galaxy/pull/20078>`_
* Fix `mulled-search --destination quay`, add index reuse by `@natefoo <https://github.com/natefoo>`_ in `#20107 <https://github.com/galaxyproject/galaxy/pull/20107>`_
* Fix edam selenium test by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20134 <https://github.com/galaxyproject/galaxy/pull/20134>`_
* Skip ``param_value`` filter if ref value is runtime value by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20144 <https://github.com/galaxyproject/galaxy/pull/20144>`_
* Fix ``DataCollectionParameterModel`` factory by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20164 <https://github.com/galaxyproject/galaxy/pull/20164>`_
* Fix invocation failure dataset reference by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20200 <https://github.com/galaxyproject/galaxy/pull/20200>`_
* Conditionally import from `galaxy.config` in `galaxy.model.mapping` if `TYPE_CHECKING` by `@natefoo <https://github.com/natefoo>`_ in `#20209 <https://github.com/galaxyproject/galaxy/pull/20209>`_
* Refactor display_as URL generation for UCSC links and fix to remove double slashes in URL by `@natefoo <https://github.com/natefoo>`_ in `#20239 <https://github.com/galaxyproject/galaxy/pull/20239>`_
* Fall back to name in job summary if no input label given by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20258 <https://github.com/galaxyproject/galaxy/pull/20258>`_
* Fix WF Run RO-Crate logo width in Firefox by `@davelopez <https://github.com/davelopez>`_ in `#20305 <https://github.com/galaxyproject/galaxy/pull/20305>`_
* Fix searching roles in admin UI by `@jdavcs <https://github.com/jdavcs>`_ in `#20394 <https://github.com/galaxyproject/galaxy/pull/20394>`_
* Skip validation of expression.json input in workflow parameter validator by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20412 <https://github.com/galaxyproject/galaxy/pull/20412>`_
* Fix unit tests returning values by `@nsoranzo <https://github.com/nsoranzo>`_ in `#20413 <https://github.com/galaxyproject/galaxy/pull/20413>`_
* Fix ``mull_targets()`` with mamba 2.x by `@nsoranzo <https://github.com/nsoranzo>`_ in `#20416 <https://github.com/galaxyproject/galaxy/pull/20416>`_
* Make response header values strings by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20475 <https://github.com/galaxyproject/galaxy/pull/20475>`_
* Fix legacy get_metadata_file controller route by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20477 <https://github.com/galaxyproject/galaxy/pull/20477>`_
* Prevent running datatype autodetect on purged datasets by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20479 <https://github.com/galaxyproject/galaxy/pull/20479>`_
* Link workflow invocation outputs upon importing invocation by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20485 <https://github.com/galaxyproject/galaxy/pull/20485>`_
* Make optional edam-ontology in datatypes registry optional by `@natefoo <https://github.com/natefoo>`_ in `#20492 <https://github.com/galaxyproject/galaxy/pull/20492>`_

============
Enhancements
============

* Bump up max_peek_size to 50MB by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19823 <https://github.com/galaxyproject/galaxy/pull/19823>`_
* Point install_requires at requirements.txt file by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19864 <https://github.com/galaxyproject/galaxy/pull/19864>`_
* Fix Invenio file source downloads not working with some Invenio instances by `@davelopez <https://github.com/davelopez>`_ in `#19930 <https://github.com/galaxyproject/galaxy/pull/19930>`_
* Update selectable object stores after adding or editing them by `@davelopez <https://github.com/davelopez>`_ in `#19992 <https://github.com/galaxyproject/galaxy/pull/19992>`_

=============
Other changes
=============

* Backport parts of #19659 by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#19805 <https://github.com/galaxyproject/galaxy/pull/19805>`_
* Remove unused client route for standalone wizard interface by `@dannon <https://github.com/dannon>`_ in `#19836 <https://github.com/galaxyproject/galaxy/pull/19836>`_
* Publish pre-built client with (point-)release by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19879 <https://github.com/galaxyproject/galaxy/pull/19879>`_
* Update dev package version in meta package by `@natefoo <https://github.com/natefoo>`_ in `#20159 <https://github.com/galaxyproject/galaxy/pull/20159>`_

-------------------
19.9.0 (2019-11-21)
-------------------

* Initial import from dev branch of Galaxy during 19.09 development cycle.
