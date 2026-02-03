History
-------

.. to_doc

-------
26.0rc1
-------



-------------------
25.1.1 (2026-02-03)
-------------------


=========
Bug fixes
=========

* Sample sheet column fix by `@mvdbeek <https://github.com/mvdbeek>`_ in `#21446 <https://github.com/galaxyproject/galaxy/pull/21446>`_
* Record input parameter invocation inputs by `@mvdbeek <https://github.com/mvdbeek>`_ in `#21452 <https://github.com/galaxyproject/galaxy/pull/21452>`_
* Remove ref and polish release-drafter workflow by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#21467 <https://github.com/galaxyproject/galaxy/pull/21467>`_
* Maintain column definitions on map over by `@mvdbeek <https://github.com/mvdbeek>`_ in `#21468 <https://github.com/galaxyproject/galaxy/pull/21468>`_
* Add missing test file for sig datatype by `@SaimMomin12 <https://github.com/SaimMomin12>`_ in `#21473 <https://github.com/galaxyproject/galaxy/pull/21473>`_
* Remove `release-drafter` workflow and add a release config file to improve generated notes by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#21478 <https://github.com/galaxyproject/galaxy/pull/21478>`_
* Do not update a user's update_time when an admin archives (and purges) a history by `@natefoo <https://github.com/natefoo>`_ in `#21484 <https://github.com/galaxyproject/galaxy/pull/21484>`_
* Add missing ending newline to test.sig test data file by `@nsoranzo <https://github.com/nsoranzo>`_ in `#21485 <https://github.com/galaxyproject/galaxy/pull/21485>`_
* Fix subworkflow runs for disconnected required inputs with defaults by `@mvdbeek <https://github.com/mvdbeek>`_ in `#21488 <https://github.com/galaxyproject/galaxy/pull/21488>`_
* change locuszoom package version to 0.0.7 by `@elmedjadjirayane <https://github.com/elmedjadjirayane>`_ in `#21494 <https://github.com/galaxyproject/galaxy/pull/21494>`_
* Pin release prebuilt client package exactly by `@dannon <https://github.com/dannon>`_ in `#21498 <https://github.com/galaxyproject/galaxy/pull/21498>`_
* Usability fixes for sample sheet selection.  by `@jmchilton <https://github.com/jmchilton>`_ in `#21503 <https://github.com/galaxyproject/galaxy/pull/21503>`_
* Fix exception message to enable debugging of missing dataset issue. by `@jmchilton <https://github.com/jmchilton>`_ in `#21504 <https://github.com/galaxyproject/galaxy/pull/21504>`_
* Fix type annotation for invocation report ``errors`` field by `@mvdbeek <https://github.com/mvdbeek>`_ in `#21508 <https://github.com/galaxyproject/galaxy/pull/21508>`_
* Add missing dependencies to ``galaxy-files`` package by `@nsoranzo <https://github.com/nsoranzo>`_ in `#21518 <https://github.com/galaxyproject/galaxy/pull/21518>`_
* Filter out failed_metadata HDAs from job cache by `@mvdbeek <https://github.com/mvdbeek>`_ in `#21544 <https://github.com/galaxyproject/galaxy/pull/21544>`_
* Fix pulsar with ``rewrite_parameters: false`` by `@mvdbeek <https://github.com/mvdbeek>`_ in `#21557 <https://github.com/galaxyproject/galaxy/pull/21557>`_
* Fix job cache collection copy by `@mvdbeek <https://github.com/mvdbeek>`_ in `#21558 <https://github.com/galaxyproject/galaxy/pull/21558>`_
* Show "Expires today" instead of "Expires soon" in Expiration Warning by `@mvdbeek <https://github.com/mvdbeek>`_ in `#21560 <https://github.com/galaxyproject/galaxy/pull/21560>`_
* Use quotes for Galaxy citation bibtex by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#21563 <https://github.com/galaxyproject/galaxy/pull/21563>`_
* Supports Dataverse file access via both persistent and database IDs by `@davelopez <https://github.com/davelopez>`_ in `#21569 <https://github.com/galaxyproject/galaxy/pull/21569>`_
* Fix passing user id to preferences by `@guerler <https://github.com/guerler>`_ in `#21576 <https://github.com/galaxyproject/galaxy/pull/21576>`_
* Fix Pulsar with ``default_file_action: none`` by `@mvdbeek <https://github.com/mvdbeek>`_ in `#21578 <https://github.com/galaxyproject/galaxy/pull/21578>`_
* Fix #21542 - allow workbook bootstrap generation for sample sheet collection types. by `@jmchilton <https://github.com/jmchilton>`_ in `#21584 <https://github.com/galaxyproject/galaxy/pull/21584>`_
* Add belated deprecation of Python 3.9 support by `@nsoranzo <https://github.com/nsoranzo>`_ in `#21598 <https://github.com/galaxyproject/galaxy/pull/21598>`_
* Fix loading of credentials when associated tools are missing by `@arash77 <https://github.com/arash77>`_ in `#21599 <https://github.com/galaxyproject/galaxy/pull/21599>`_
* Fix race condition in workflow collection populated state check by `@mvdbeek <https://github.com/mvdbeek>`_ in `#21613 <https://github.com/galaxyproject/galaxy/pull/21613>`_
* Harden Dataverse integration by `@davelopez <https://github.com/davelopez>`_ in `#21624 <https://github.com/galaxyproject/galaxy/pull/21624>`_
* Add split paired or unpaired tool to sample tool conf by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#21647 <https://github.com/galaxyproject/galaxy/pull/21647>`_
* Fix secret credential editing and add clear button by `@itisAliRH <https://github.com/itisAliRH>`_ in `#21650 <https://github.com/galaxyproject/galaxy/pull/21650>`_
* Fix condor typo by `@gsaudade99 <https://github.com/gsaudade99>`_ in `#21651 <https://github.com/galaxyproject/galaxy/pull/21651>`_
* Fix HTCondor runner unwatching jobs when stopping containers by `@kysrpex <https://github.com/kysrpex>`_ in `#21656 <https://github.com/galaxyproject/galaxy/pull/21656>`_
* Fix data manager .loc file selection logic by `@jdavcs <https://github.com/jdavcs>`_ in `#21664 <https://github.com/galaxyproject/galaxy/pull/21664>`_
* Fixes storage management check for anonymous users by `@davelopez <https://github.com/davelopez>`_ in `#21680 <https://github.com/galaxyproject/galaxy/pull/21680>`_
* Resets selection filter when loading dialog by `@davelopez <https://github.com/davelopez>`_ in `#21681 <https://github.com/galaxyproject/galaxy/pull/21681>`_
* Fixes duplicated entries in "share with individual users" component by `@davelopez <https://github.com/davelopez>`_ in `#21683 <https://github.com/galaxyproject/galaxy/pull/21683>`_
* Simplify docker build, use node as specified in requirements by `@mvdbeek <https://github.com/mvdbeek>`_ in `#21695 <https://github.com/galaxyproject/galaxy/pull/21695>`_
* Remove Discover Tools button in the workflow tool panel by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#21697 <https://github.com/galaxyproject/galaxy/pull/21697>`_
* Fix option propagation for workflow inputs connected to multiple subworkflows by `@mvdbeek <https://github.com/mvdbeek>`_ in `#21712 <https://github.com/galaxyproject/galaxy/pull/21712>`_
* Fix collection job state not preserved during history export/import by `@mvdbeek <https://github.com/mvdbeek>`_ in `#21716 <https://github.com/galaxyproject/galaxy/pull/21716>`_
* Add missing filter_failed_collection_1.1.0.xml tool by `@mvdbeek <https://github.com/mvdbeek>`_ in `#21719 <https://github.com/galaxyproject/galaxy/pull/21719>`_
* Strip inline comments in conditional requirements by `@mvdbeek <https://github.com/mvdbeek>`_ in `#21720 <https://github.com/galaxyproject/galaxy/pull/21720>`_
* Exclude node_modules at all depths in Docker builds by `@mvdbeek <https://github.com/mvdbeek>`_ in `#21721 <https://github.com/galaxyproject/galaxy/pull/21721>`_

============
Enhancements
============

* add new datatype for kmindex index data by `@Smeds <https://github.com/Smeds>`_ in `#21429 <https://github.com/galaxyproject/galaxy/pull/21429>`_
* Add sample sheet support to many database operation tools by `@mvdbeek <https://github.com/mvdbeek>`_ in `#21465 <https://github.com/galaxyproject/galaxy/pull/21465>`_
* Add Sourmash sig new datatype by `@SaimMomin12 <https://github.com/SaimMomin12>`_ in `#21469 <https://github.com/galaxyproject/galaxy/pull/21469>`_
* Add new jupyter version by `@bgruening <https://github.com/bgruening>`_ in `#21531 <https://github.com/galaxyproject/galaxy/pull/21531>`_
* Adds object_expires_after_days example usage to sample config by `@davelopez <https://github.com/davelopez>`_ in `#21547 <https://github.com/galaxyproject/galaxy/pull/21547>`_
* Add tool credentials system documentation and schema updates by `@arash77 <https://github.com/arash77>`_ in `#21561 <https://github.com/galaxyproject/galaxy/pull/21561>`_
* Add a few datatypes from the digital humanities domain by `@bgruening <https://github.com/bgruening>`_ in `#21596 <https://github.com/galaxyproject/galaxy/pull/21596>`_
* Add new datatype pg and hg for pangenomics by `@SaimMomin12 <https://github.com/SaimMomin12>`_ in `#21620 <https://github.com/galaxyproject/galaxy/pull/21620>`_
* Add database operation tool to convert sample sheets to list collections by `@mvdbeek <https://github.com/mvdbeek>`_ in `#21625 <https://github.com/galaxyproject/galaxy/pull/21625>`_
* Add new datatypes required for VG tool by `@SaimMomin12 <https://github.com/SaimMomin12>`_ in `#21644 <https://github.com/galaxyproject/galaxy/pull/21644>`_
* Document security considerations for using secrets by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#21654 <https://github.com/galaxyproject/galaxy/pull/21654>`_

=============
Other changes
=============

* Update 25.1 release notes with config changes by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#21444 <https://github.com/galaxyproject/galaxy/pull/21444>`_
* Fix 25.1 release month on user facing notes by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#21450 <https://github.com/galaxyproject/galaxy/pull/21450>`_
* Fix sample_sheet column display by `@mvdbeek <https://github.com/mvdbeek>`_ in `#21457 <https://github.com/galaxyproject/galaxy/pull/21457>`_
* Merge 25.1 into master by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#21482 <https://github.com/galaxyproject/galaxy/pull/21482>`_
* Improve tempdir cleanup in integration tests by `@mvdbeek <https://github.com/mvdbeek>`_ in `#21520 <https://github.com/galaxyproject/galaxy/pull/21520>`_

-------------------
25.1.0 (2025-12-12)
-------------------


=========
Bug fixes
=========

* Workaround to numeric sorting in the local portion of tool versions if they are galaxy "build" numbers by `@natefoo <https://github.com/natefoo>`_ in `#13570 <https://github.com/galaxyproject/galaxy/pull/13570>`_
* Change wording of the client side storage handling by `@bgruening <https://github.com/bgruening>`_ in `#19815 <https://github.com/galaxyproject/galaxy/pull/19815>`_
* Check for ``format="input"`` as well as ``format="auto"`` in datatype linter by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#20177 <https://github.com/galaxyproject/galaxy/pull/20177>`_
* Add missing galaxy slots and memory tool by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20262 <https://github.com/galaxyproject/galaxy/pull/20262>`_
* Fix a transiently failing API test. by `@jmchilton <https://github.com/jmchilton>`_ in `#20278 <https://github.com/galaxyproject/galaxy/pull/20278>`_
* Fix test timeout in k8s ``test_slots_and_memory`` test by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20284 <https://github.com/galaxyproject/galaxy/pull/20284>`_
* Fix memory and slots test by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20291 <https://github.com/galaxyproject/galaxy/pull/20291>`_
* Add built visualizations path to .gitignore by `@guerler <https://github.com/guerler>`_ in `#20355 <https://github.com/galaxyproject/galaxy/pull/20355>`_
* Remove 8 year old note that points at a non-existent subdomain by `@scottcain <https://github.com/scottcain>`_ in `#20361 <https://github.com/galaxyproject/galaxy/pull/20361>`_
* Restore Nora by `@guerler <https://github.com/guerler>`_ in `#20387 <https://github.com/galaxyproject/galaxy/pull/20387>`_
* Bump requests from 2.32.3 to 2.32.4 in /lib/galaxy/dependencies by `@dependabot[bot] <https://github.com/dependabot[bot]>`_ in `#20422 <https://github.com/galaxyproject/galaxy/pull/20422>`_
* Fix client build, set create_time by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20445 <https://github.com/galaxyproject/galaxy/pull/20445>`_
* Update mulled_containers.rst by `@ccoulombe <https://github.com/ccoulombe>`_ in `#20446 <https://github.com/galaxyproject/galaxy/pull/20446>`_
* Fix transient selenium error when adding collection input. by `@jmchilton <https://github.com/jmchilton>`_ in `#20460 <https://github.com/galaxyproject/galaxy/pull/20460>`_
* Collection API related spelling fix. by `@jmchilton <https://github.com/jmchilton>`_ in `#20470 <https://github.com/galaxyproject/galaxy/pull/20470>`_
* Fix alembic down_revision for trigger replacement migration by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20501 <https://github.com/galaxyproject/galaxy/pull/20501>`_
* Add a merge migration, revert previous edit by `@jdavcs <https://github.com/jdavcs>`_ in `#20507 <https://github.com/galaxyproject/galaxy/pull/20507>`_
* Update core.history tour by `@pavanvidem <https://github.com/pavanvidem>`_ in `#20576 <https://github.com/galaxyproject/galaxy/pull/20576>`_
* Add missing cleanup table by `@jdavcs <https://github.com/jdavcs>`_ in `#20594 <https://github.com/galaxyproject/galaxy/pull/20594>`_
* Fix UI Bug - don't allow checking deferred for local files. by `@jmchilton <https://github.com/jmchilton>`_ in `#20609 <https://github.com/galaxyproject/galaxy/pull/20609>`_
* Require user for visualizations create endpoint by `@guerler <https://github.com/guerler>`_ in `#20615 <https://github.com/galaxyproject/galaxy/pull/20615>`_
* Use store to cache step jobs summary by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#20638 <https://github.com/galaxyproject/galaxy/pull/20638>`_
* Fix typo in lib/galaxy/config/sample/job_conf.sample.yml: enviroment --> environment by `@blankenberg <https://github.com/blankenberg>`_ in `#20652 <https://github.com/galaxyproject/galaxy/pull/20652>`_
* Remove select and deselect labels from visualization select field by `@guerler <https://github.com/guerler>`_ in `#20665 <https://github.com/galaxyproject/galaxy/pull/20665>`_
* Fix assertion on python version by `@ccoulombe <https://github.com/ccoulombe>`_ in `#20696 <https://github.com/galaxyproject/galaxy/pull/20696>`_
* Remove decoded ids from job/dataset error report email by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#20714 <https://github.com/galaxyproject/galaxy/pull/20714>`_
* Fix various collection descriptions in history panel. by `@jmchilton <https://github.com/jmchilton>`_ in `#20736 <https://github.com/galaxyproject/galaxy/pull/20736>`_
* Various client unit test fixes and cleanup. by `@jmchilton <https://github.com/jmchilton>`_ in `#20752 <https://github.com/galaxyproject/galaxy/pull/20752>`_
* More client unit test clean up. by `@jmchilton <https://github.com/jmchilton>`_ in `#20755 <https://github.com/galaxyproject/galaxy/pull/20755>`_
* More cleanup for Jest output.  by `@jmchilton <https://github.com/jmchilton>`_ in `#20769 <https://github.com/galaxyproject/galaxy/pull/20769>`_
* Fix anndata metadata by `@nilchia <https://github.com/nilchia>`_ in `#20778 <https://github.com/galaxyproject/galaxy/pull/20778>`_
* Fix Switch to history link click actions and add extensive jests by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#20783 <https://github.com/galaxyproject/galaxy/pull/20783>`_
* Fix visualization installs by `@dannon <https://github.com/dannon>`_ in `#20788 <https://github.com/galaxyproject/galaxy/pull/20788>`_
* Only show breadcrumb when on history permissions route (not in sharing view) by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#20800 <https://github.com/galaxyproject/galaxy/pull/20800>`_
* Fix Ipynb datatype sniffer and add unit tests. by `@ksuderman <https://github.com/ksuderman>`_ in `#20811 <https://github.com/galaxyproject/galaxy/pull/20811>`_
* Ignore yaml and json in prettier pre-commit hook by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20823 <https://github.com/galaxyproject/galaxy/pull/20823>`_
* Bump requirement of directory converters by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#20834 <https://github.com/galaxyproject/galaxy/pull/20834>`_
* Fix lint error in `WorkflowRunSuccess` by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#20837 <https://github.com/galaxyproject/galaxy/pull/20837>`_
* Fix `multiple="true"` data collection map over for shell_command tools by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20859 <https://github.com/galaxyproject/galaxy/pull/20859>`_
* Fix test in ``configfile_user_defined.yml`` by `@nsoranzo <https://github.com/nsoranzo>`_ in `#20873 <https://github.com/galaxyproject/galaxy/pull/20873>`_
* Likely fix for transiently failing published histories test. by `@jmchilton <https://github.com/jmchilton>`_ in `#20890 <https://github.com/galaxyproject/galaxy/pull/20890>`_
* Update requirements of sort1 tool by `@nsoranzo <https://github.com/nsoranzo>`_ in `#20892 <https://github.com/galaxyproject/galaxy/pull/20892>`_
* Avoid overscroll behavior by `@guerler <https://github.com/guerler>`_ in `#20908 <https://github.com/galaxyproject/galaxy/pull/20908>`_
* Bump codecov/codecov-action from 3 to 5 by `@dependabot[bot] <https://github.com/dependabot[bot]>`_ in `#20920 <https://github.com/galaxyproject/galaxy/pull/20920>`_
* Extract: do not use common prefix dir by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#20929 <https://github.com/galaxyproject/galaxy/pull/20929>`_
* Fix default conditional test parameters... by `@jmchilton <https://github.com/jmchilton>`_ in `#20942 <https://github.com/galaxyproject/galaxy/pull/20942>`_
* Fix JupyterLite History Identifier Retrieval Without Dataset by `@guerler <https://github.com/guerler>`_ in `#20971 <https://github.com/galaxyproject/galaxy/pull/20971>`_
* Apply overscroll behavior setting to html by `@guerler <https://github.com/guerler>`_ in `#20975 <https://github.com/galaxyproject/galaxy/pull/20975>`_
* Ensure that conversion_key is defined by `@guerler <https://github.com/guerler>`_ in `#20984 <https://github.com/galaxyproject/galaxy/pull/20984>`_
* Tsc fixes and pin by `@dannon <https://github.com/dannon>`_ in `#20985 <https://github.com/galaxyproject/galaxy/pull/20985>`_
* Fix jest tests -- wait for async calls in grid list by `@dannon <https://github.com/dannon>`_ in `#20986 <https://github.com/galaxyproject/galaxy/pull/20986>`_
* Fix comp1 / test_subworkflow_map_over_data_column by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20992 <https://github.com/galaxyproject/galaxy/pull/20992>`_
* Save IGV locus and improve error handling by `@guerler <https://github.com/guerler>`_ in `#20996 <https://github.com/galaxyproject/galaxy/pull/20996>`_
* Fix content wrapping in cards and preference title by `@guerler <https://github.com/guerler>`_ in `#21009 <https://github.com/galaxyproject/galaxy/pull/21009>`_
* Fix horizontal scrolling w/ GButton in input-group-append by `@dannon <https://github.com/dannon>`_ in `#21025 <https://github.com/galaxyproject/galaxy/pull/21025>`_
* Fix GCS file source to handle virtual directories without marker objects by `@dannon <https://github.com/dannon>`_ in `#21051 <https://github.com/galaxyproject/galaxy/pull/21051>`_
* Fix Huggingface timestamp parsing when `last_commit` is missing by `@davelopez <https://github.com/davelopez>`_ in `#21072 <https://github.com/galaxyproject/galaxy/pull/21072>`_
* Allow cors on data and tool landing pages by `@mvdbeek <https://github.com/mvdbeek>`_ in `#21078 <https://github.com/galaxyproject/galaxy/pull/21078>`_
* Fix invocation export dataset exclusion by `@davelopez <https://github.com/davelopez>`_ in `#21091 <https://github.com/galaxyproject/galaxy/pull/21091>`_
* Fix copy export download link for old exports by `@davelopez <https://github.com/davelopez>`_ in `#21094 <https://github.com/galaxyproject/galaxy/pull/21094>`_
* Test and fix CORS on exceptions by `@mvdbeek <https://github.com/mvdbeek>`_ in `#21105 <https://github.com/galaxyproject/galaxy/pull/21105>`_
* Fix invalid invocation tab handling and unify disabled tab components by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#21115 <https://github.com/galaxyproject/galaxy/pull/21115>`_
* Fix shift+click range select not working in history list by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#21117 <https://github.com/galaxyproject/galaxy/pull/21117>`_
* Restore job.get_param_values by `@mvdbeek <https://github.com/mvdbeek>`_ in `#21130 <https://github.com/galaxyproject/galaxy/pull/21130>`_
* Improve _touch_collection_update_time_cte performance by `@mvdbeek <https://github.com/mvdbeek>`_ in `#21134 <https://github.com/galaxyproject/galaxy/pull/21134>`_
* Fix type annotation in test_run_workflow_use_cached_job_implicit_conv… by `@mvdbeek <https://github.com/mvdbeek>`_ in `#21138 <https://github.com/galaxyproject/galaxy/pull/21138>`_
* Use corepack to link yarn into $VIRTUALENV/bin by `@mvdbeek <https://github.com/mvdbeek>`_ in `#21140 <https://github.com/galaxyproject/galaxy/pull/21140>`_
* Pin Ansible version by `@ksuderman <https://github.com/ksuderman>`_ in `#21141 <https://github.com/galaxyproject/galaxy/pull/21141>`_
* Remove invocation view connection animations by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#21145 <https://github.com/galaxyproject/galaxy/pull/21145>`_
* Mark user creation API endpoint as admin-only by `@mvdbeek <https://github.com/mvdbeek>`_ in `#21149 <https://github.com/galaxyproject/galaxy/pull/21149>`_
* Set minimum profile version for expression tools by `@mvdbeek <https://github.com/mvdbeek>`_ in `#21151 <https://github.com/galaxyproject/galaxy/pull/21151>`_
* Fix subworkflow editing by `@mvdbeek <https://github.com/mvdbeek>`_ in `#21159 <https://github.com/galaxyproject/galaxy/pull/21159>`_
* Add Convert characters1 to workflow safe updates by `@mvdbeek <https://github.com/mvdbeek>`_ in `#21160 <https://github.com/galaxyproject/galaxy/pull/21160>`_
* Use yarn instead of npx to use pinned openapi-typescript by `@mvdbeek <https://github.com/mvdbeek>`_ in `#21164 <https://github.com/galaxyproject/galaxy/pull/21164>`_
* Bump up minimal tpv version by `@mvdbeek <https://github.com/mvdbeek>`_ in `#21166 <https://github.com/galaxyproject/galaxy/pull/21166>`_
* Fix proxy endpoint encoding by `@davelopez <https://github.com/davelopez>`_ in `#21169 <https://github.com/galaxyproject/galaxy/pull/21169>`_
* Enable drag-and-drop of collection elements in IGV by `@guerler <https://github.com/guerler>`_ in `#21173 <https://github.com/galaxyproject/galaxy/pull/21173>`_
* Save build date to GITHUB_OUTPUT by `@ksuderman <https://github.com/ksuderman>`_ in `#21181 <https://github.com/galaxyproject/galaxy/pull/21181>`_
* Don't show the "view sheet" button for non-sample sheet collections.  by `@jmchilton <https://github.com/jmchilton>`_ in `#21191 <https://github.com/galaxyproject/galaxy/pull/21191>`_
* Allow collection builder to be invoked consecutively by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#21193 <https://github.com/galaxyproject/galaxy/pull/21193>`_
* Add Hyphy Vision Result Viewer by `@guerler <https://github.com/guerler>`_ in `#21196 <https://github.com/galaxyproject/galaxy/pull/21196>`_
* Don't create extra watchers when switching tabs by `@natefoo <https://github.com/natefoo>`_ in `#21197 <https://github.com/galaxyproject/galaxy/pull/21197>`_
* Drop single 'pair' from standard upload UI, preferring lists, or lists of pairs as options for user by `@dannon <https://github.com/dannon>`_ in `#21200 <https://github.com/galaxyproject/galaxy/pull/21200>`_
* Assorted workbook upload fixes.  by `@jmchilton <https://github.com/jmchilton>`_ in `#21203 <https://github.com/galaxyproject/galaxy/pull/21203>`_
* Wrap ontology card in tool discovery view below list view selector by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#21212 <https://github.com/galaxyproject/galaxy/pull/21212>`_
* Add missing more-itertools dependency by `@nsoranzo <https://github.com/nsoranzo>`_ in `#21214 <https://github.com/galaxyproject/galaxy/pull/21214>`_
* Fix downloading subworkflows without stored workflow by `@mvdbeek <https://github.com/mvdbeek>`_ in `#21223 <https://github.com/galaxyproject/galaxy/pull/21223>`_
* Fix href for tool links by `@mvdbeek <https://github.com/mvdbeek>`_ in `#21232 <https://github.com/galaxyproject/galaxy/pull/21232>`_
* Apply tool test timeout only once by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#21246 <https://github.com/galaxyproject/galaxy/pull/21246>`_
* Fix workbook download link by `@jmchilton <https://github.com/jmchilton>`_ in `#21261 <https://github.com/galaxyproject/galaxy/pull/21261>`_
* Fixes download for restricted Zenodo records by `@davelopez <https://github.com/davelopez>`_ in `#21274 <https://github.com/galaxyproject/galaxy/pull/21274>`_
* Update the mulled.py script to check json output by `@nilchia <https://github.com/nilchia>`_ in `#21276 <https://github.com/galaxyproject/galaxy/pull/21276>`_
* Prevent duplicate `current_history_json` calls by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#21282 <https://github.com/galaxyproject/galaxy/pull/21282>`_
* Prevent duplicate fetches for full workflow in invocation view by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#21284 <https://github.com/galaxyproject/galaxy/pull/21284>`_
* Add a rate limiter to the API client factory by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#21286 <https://github.com/galaxyproject/galaxy/pull/21286>`_
* Fix keyed cache fetching over and over if fetched value is 0 by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#21293 <https://github.com/galaxyproject/galaxy/pull/21293>`_
* Fix invocations scroll list cards to show update time by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#21294 <https://github.com/galaxyproject/galaxy/pull/21294>`_
* Set `create_time` as the default time for sorting/display for invocations by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#21314 <https://github.com/galaxyproject/galaxy/pull/21314>`_
* Fix `TERMINAL_STATES` array has a duplicate state by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#21342 <https://github.com/galaxyproject/galaxy/pull/21342>`_
* Force correct client build by `@mvdbeek <https://github.com/mvdbeek>`_ in `#21346 <https://github.com/galaxyproject/galaxy/pull/21346>`_
* Fix fastapi package conflict by `@mvdbeek <https://github.com/mvdbeek>`_ in `#21349 <https://github.com/galaxyproject/galaxy/pull/21349>`_
* Backport smoke-test and pr jobs from dev branch by `@ksuderman <https://github.com/ksuderman>`_ in `#21350 <https://github.com/galaxyproject/galaxy/pull/21350>`_
* Use anaconda API to find package download URL by `@nsoranzo <https://github.com/nsoranzo>`_ in `#21360 <https://github.com/galaxyproject/galaxy/pull/21360>`_
* Fix database revision tags by `@jdavcs <https://github.com/jdavcs>`_ in `#21377 <https://github.com/galaxyproject/galaxy/pull/21377>`_
* Use a new format tox environment in lint GitHub action by `@nsoranzo <https://github.com/nsoranzo>`_ in `#21419 <https://github.com/galaxyproject/galaxy/pull/21419>`_
* Skip mako for rendering tool help by `@mvdbeek <https://github.com/mvdbeek>`_ in `#21428 <https://github.com/galaxyproject/galaxy/pull/21428>`_
* Fix optional subworkflow input scheduling bug by `@mvdbeek <https://github.com/mvdbeek>`_ in `#21435 <https://github.com/galaxyproject/galaxy/pull/21435>`_
* Maintain columns on sample sheet map over by `@mvdbeek <https://github.com/mvdbeek>`_ in `#21436 <https://github.com/galaxyproject/galaxy/pull/21436>`_

============
Enhancements
============

* Don't serialize view of item in delete/purge request by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18732 <https://github.com/galaxyproject/galaxy/pull/18732>`_
* Support credentials(secrets/variables) in tool requirements by `@arash77 <https://github.com/arash77>`_ in `#19084 <https://github.com/galaxyproject/galaxy/pull/19084>`_
* Allow several Galaxy Markdown directives to be embedded. by `@jmchilton <https://github.com/jmchilton>`_ in `#19086 <https://github.com/galaxyproject/galaxy/pull/19086>`_
* Add tags to output datasets from tool form by `@PlushZ <https://github.com/PlushZ>`_ in `#19225 <https://github.com/galaxyproject/galaxy/pull/19225>`_
* Implement Sample Sheets  by `@jmchilton <https://github.com/jmchilton>`_ in `#19305 <https://github.com/galaxyproject/galaxy/pull/19305>`_
* Refactor and use `ScrollList` component in more places by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19318 <https://github.com/galaxyproject/galaxy/pull/19318>`_
* User preferences redesign by `@itisAliRH <https://github.com/itisAliRH>`_ in `#19658 <https://github.com/galaxyproject/galaxy/pull/19658>`_
* Refactor Object Store Selection Modals UI by `@itisAliRH <https://github.com/itisAliRH>`_ in `#19697 <https://github.com/galaxyproject/galaxy/pull/19697>`_
* Consider collections in on_strings for parameters accepting multiple datasets by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#19817 <https://github.com/galaxyproject/galaxy/pull/19817>`_
* Remove backbone-based charts modules by `@guerler <https://github.com/guerler>`_ in `#19892 <https://github.com/galaxyproject/galaxy/pull/19892>`_
* Add `selectedItems` composable by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#19973 <https://github.com/galaxyproject/galaxy/pull/19973>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#20139 <https://github.com/galaxyproject/galaxy/pull/20139>`_
* Remove legacy visualizations by `@guerler <https://github.com/guerler>`_ in `#20173 <https://github.com/galaxyproject/galaxy/pull/20173>`_
* Add rerun.io web viewer by `@guerler <https://github.com/guerler>`_ in `#20202 <https://github.com/galaxyproject/galaxy/pull/20202>`_
* Selenium tests for various 24.2 features. by `@jmchilton <https://github.com/jmchilton>`_ in `#20215 <https://github.com/galaxyproject/galaxy/pull/20215>`_
* Update Javascript package licenses to MIT by `@mr-c <https://github.com/mr-c>`_ in `#20264 <https://github.com/galaxyproject/galaxy/pull/20264>`_
* Split Login and Register, enable OIDC Registration. by `@uwwint <https://github.com/uwwint>`_ in `#20287 <https://github.com/galaxyproject/galaxy/pull/20287>`_
* Empower Users to More Pragmatically Import Datasets & Collections From Tables by `@jmchilton <https://github.com/jmchilton>`_ in `#20288 <https://github.com/galaxyproject/galaxy/pull/20288>`_
* Update GitHub workflows to use PostgreSQL 17 image by `@nsoranzo <https://github.com/nsoranzo>`_ in `#20292 <https://github.com/galaxyproject/galaxy/pull/20292>`_
* Switch Default Visualization Endpoint to script, migrate to YAML by `@guerler <https://github.com/guerler>`_ in `#20303 <https://github.com/galaxyproject/galaxy/pull/20303>`_
* Add short term storage expiration indicator to history items by `@davelopez <https://github.com/davelopez>`_ in `#20332 <https://github.com/galaxyproject/galaxy/pull/20332>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#20347 <https://github.com/galaxyproject/galaxy/pull/20347>`_
* Install Visualization plugins as self-contained packages by `@guerler <https://github.com/guerler>`_ in `#20348 <https://github.com/galaxyproject/galaxy/pull/20348>`_
* Add LocusZoom Visualization by `@elmedjadjirayane <https://github.com/elmedjadjirayane>`_ in `#20354 <https://github.com/galaxyproject/galaxy/pull/20354>`_
* Refactor CollectionDescription component props to use HDCASummary by `@davelopez <https://github.com/davelopez>`_ in `#20356 <https://github.com/galaxyproject/galaxy/pull/20356>`_
* Update create_time field to be required in history content items by `@davelopez <https://github.com/davelopez>`_ in `#20357 <https://github.com/galaxyproject/galaxy/pull/20357>`_
* Prepare ``ToolBox.dynamic_tool_to_tool()`` for CWL formats by `@nsoranzo <https://github.com/nsoranzo>`_ in `#20364 <https://github.com/galaxyproject/galaxy/pull/20364>`_
* Install visualizations directly to static path, avoid duplication by `@guerler <https://github.com/guerler>`_ in `#20372 <https://github.com/galaxyproject/galaxy/pull/20372>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#20383 <https://github.com/galaxyproject/galaxy/pull/20383>`_
* Use full page width in reports and pages by `@guerler <https://github.com/guerler>`_ in `#20384 <https://github.com/galaxyproject/galaxy/pull/20384>`_
* Workflow Graph Search by `@ElectronicBlueberry <https://github.com/ElectronicBlueberry>`_ in `#20390 <https://github.com/galaxyproject/galaxy/pull/20390>`_
* History CitationsList export improvements by `@dannon <https://github.com/dannon>`_ in `#20402 <https://github.com/galaxyproject/galaxy/pull/20402>`_
* Enhance citations page by `@davelopez <https://github.com/davelopez>`_ in `#20408 <https://github.com/galaxyproject/galaxy/pull/20408>`_
* Base Implementation of GFormInput by `@ElectronicBlueberry <https://github.com/ElectronicBlueberry>`_ in `#20418 <https://github.com/galaxyproject/galaxy/pull/20418>`_
* Type annotation fixes for mypy 1.16.0 by `@nsoranzo <https://github.com/nsoranzo>`_ in `#20424 <https://github.com/galaxyproject/galaxy/pull/20424>`_
* Allow larger viz in pages by `@guerler <https://github.com/guerler>`_ in `#20427 <https://github.com/galaxyproject/galaxy/pull/20427>`_
* Implement dataset source requested transformations. by `@jmchilton <https://github.com/jmchilton>`_ in `#20435 <https://github.com/galaxyproject/galaxy/pull/20435>`_
* Add username_key setting to configure python-social-auth OIDC by `@marius-mather <https://github.com/marius-mather>`_ in `#20497 <https://github.com/galaxyproject/galaxy/pull/20497>`_
* Test case for using URL-based workflow inputs with implicit conversions. by `@jmchilton <https://github.com/jmchilton>`_ in `#20509 <https://github.com/galaxyproject/galaxy/pull/20509>`_
* Remove deprecated tool document cache by `@nsoranzo <https://github.com/nsoranzo>`_ in `#20510 <https://github.com/galaxyproject/galaxy/pull/20510>`_
* Fixes for invocation import. by `@jmchilton <https://github.com/jmchilton>`_ in `#20528 <https://github.com/galaxyproject/galaxy/pull/20528>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#20537 <https://github.com/galaxyproject/galaxy/pull/20537>`_
* Decode OIDC access token as part of authentication pipeline by `@marius-mather <https://github.com/marius-mather>`_ in `#20547 <https://github.com/galaxyproject/galaxy/pull/20547>`_
* Add Dataverse template by `@davelopez <https://github.com/davelopez>`_ in `#20551 <https://github.com/galaxyproject/galaxy/pull/20551>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#20577 <https://github.com/galaxyproject/galaxy/pull/20577>`_
* Display the Galaxy Citation within the Export Tool References List by `@mschatz <https://github.com/mschatz>`_ in `#20584 <https://github.com/galaxyproject/galaxy/pull/20584>`_
* Add recent downloads page for STS requests by `@davelopez <https://github.com/davelopez>`_ in `#20585 <https://github.com/galaxyproject/galaxy/pull/20585>`_
* Implement Data Landing Requests by `@jmchilton <https://github.com/jmchilton>`_ in `#20592 <https://github.com/galaxyproject/galaxy/pull/20592>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#20601 <https://github.com/galaxyproject/galaxy/pull/20601>`_
* Improve BreadcrumbHeading and add unit tests by `@itisAliRH <https://github.com/itisAliRH>`_ in `#20618 <https://github.com/galaxyproject/galaxy/pull/20618>`_
* Remove vue-tsc diff comparison from CI by `@dannon <https://github.com/dannon>`_ in `#20620 <https://github.com/galaxyproject/galaxy/pull/20620>`_
* Add a "Debug" (email report) tab to Workflow Invocations by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#20624 <https://github.com/galaxyproject/galaxy/pull/20624>`_
* Clean up code from pyupgrade by `@nsoranzo <https://github.com/nsoranzo>`_ in `#20642 <https://github.com/galaxyproject/galaxy/pull/20642>`_
* Update location of latest tpv shared db by `@nuwang <https://github.com/nuwang>`_ in `#20651 <https://github.com/galaxyproject/galaxy/pull/20651>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#20653 <https://github.com/galaxyproject/galaxy/pull/20653>`_
* Add markdown hint to schema by `@bgruening <https://github.com/bgruening>`_ in `#20654 <https://github.com/galaxyproject/galaxy/pull/20654>`_
* Update tiffviewer visualization to version 0.0.3 by `@davelopez <https://github.com/davelopez>`_ in `#20658 <https://github.com/galaxyproject/galaxy/pull/20658>`_
* Improve GCard visibility handling and type definitions by `@itisAliRH <https://github.com/itisAliRH>`_ in `#20663 <https://github.com/galaxyproject/galaxy/pull/20663>`_
* Removes `entries` from purged filter label in history grid by `@guerler <https://github.com/guerler>`_ in `#20664 <https://github.com/galaxyproject/galaxy/pull/20664>`_
* Unify History export UX using wizard by `@davelopez <https://github.com/davelopez>`_ in `#20666 <https://github.com/galaxyproject/galaxy/pull/20666>`_
* Sort collection dialog by HID descending. by `@jmchilton <https://github.com/jmchilton>`_ in `#20674 <https://github.com/galaxyproject/galaxy/pull/20674>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#20680 <https://github.com/galaxyproject/galaxy/pull/20680>`_
* Fix resource watcher composable race condition by `@davelopez <https://github.com/davelopez>`_ in `#20690 <https://github.com/galaxyproject/galaxy/pull/20690>`_
* Add special case for BAM files in RStudio by `@bgruening <https://github.com/bgruening>`_ in `#20692 <https://github.com/galaxyproject/galaxy/pull/20692>`_
* Add `fsspec` base implementation for File Source plugins by `@davelopez <https://github.com/davelopez>`_ in `#20698 <https://github.com/galaxyproject/galaxy/pull/20698>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#20699 <https://github.com/galaxyproject/galaxy/pull/20699>`_
* Add more info to inheritance chain by `@arash77 <https://github.com/arash77>`_ in `#20701 <https://github.com/galaxyproject/galaxy/pull/20701>`_
* History Components Navigation/Heading Improvements by `@itisAliRH <https://github.com/itisAliRH>`_ in `#20702 <https://github.com/galaxyproject/galaxy/pull/20702>`_
* Improve cli and slurmcli runner traceability for job status and failure reasons by `@selten <https://github.com/selten>`_ in `#20717 <https://github.com/galaxyproject/galaxy/pull/20717>`_
* Attempt to reuse previously materialized datasets by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20718 <https://github.com/galaxyproject/galaxy/pull/20718>`_
* Make workflow invocation tabs routable by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#20719 <https://github.com/galaxyproject/galaxy/pull/20719>`_
* Drop ucsc test server from sample build sites by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20723 <https://github.com/galaxyproject/galaxy/pull/20723>`_
* Refactor Files Sources Framework for stronger typing using pydantic models by `@davelopez <https://github.com/davelopez>`_ in `#20728 <https://github.com/galaxyproject/galaxy/pull/20728>`_
* Hierarchical display collection dataset states by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20731 <https://github.com/galaxyproject/galaxy/pull/20731>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#20732 <https://github.com/galaxyproject/galaxy/pull/20732>`_
* Fix Client Linting Run Error by `@itisAliRH <https://github.com/itisAliRH>`_ in `#20734 <https://github.com/galaxyproject/galaxy/pull/20734>`_
* Add embed-compatible view for galaxy pages by `@dannon <https://github.com/dannon>`_ in `#20737 <https://github.com/galaxyproject/galaxy/pull/20737>`_
* Make invocations panel reactive using the invocation store by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#20738 <https://github.com/galaxyproject/galaxy/pull/20738>`_
* New History List Using GCard by `@itisAliRH <https://github.com/itisAliRH>`_ in `#20744 <https://github.com/galaxyproject/galaxy/pull/20744>`_
* Change Advanced Tool Search to a Tool Discovery View by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#20747 <https://github.com/galaxyproject/galaxy/pull/20747>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#20753 <https://github.com/galaxyproject/galaxy/pull/20753>`_
* Consolidate visualization mako, avoid user agent styles by `@guerler <https://github.com/guerler>`_ in `#20760 <https://github.com/galaxyproject/galaxy/pull/20760>`_
* Add configfiles support and various enhancements for user defined tools by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20761 <https://github.com/galaxyproject/galaxy/pull/20761>`_
* Fix WorkflowComment tests warnings by `@davelopez <https://github.com/davelopez>`_ in `#20762 <https://github.com/galaxyproject/galaxy/pull/20762>`_
* A production data types checklist to aid creating/reviewing new data types by `@jmchilton <https://github.com/jmchilton>`_ in `#20768 <https://github.com/galaxyproject/galaxy/pull/20768>`_
* Fail Jest tests on warn/error console logging. by `@jmchilton <https://github.com/jmchilton>`_ in `#20770 <https://github.com/galaxyproject/galaxy/pull/20770>`_
* Modernize and Refactor Tour components by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#20771 <https://github.com/galaxyproject/galaxy/pull/20771>`_
* Increase wait time (retry) in UCSC data source test by `@davelopez <https://github.com/davelopez>`_ in `#20772 <https://github.com/galaxyproject/galaxy/pull/20772>`_
* Drop old load_workflow controller method, use API by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20774 <https://github.com/galaxyproject/galaxy/pull/20774>`_
* Apply eslint fixes by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20775 <https://github.com/galaxyproject/galaxy/pull/20775>`_
* Allow fine-grained selection of included files in Invocation Export Wizard by `@davelopez <https://github.com/davelopez>`_ in `#20776 <https://github.com/galaxyproject/galaxy/pull/20776>`_
* Stabilize client build after client-dev-server  by `@davelopez <https://github.com/davelopez>`_ in `#20777 <https://github.com/galaxyproject/galaxy/pull/20777>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#20779 <https://github.com/galaxyproject/galaxy/pull/20779>`_
* Remove Backbone from UI bootstrap initialization by `@guerler <https://github.com/guerler>`_ in `#20786 <https://github.com/galaxyproject/galaxy/pull/20786>`_
* Adapt S3 file source to fsspec by `@davelopez <https://github.com/davelopez>`_ in `#20794 <https://github.com/galaxyproject/galaxy/pull/20794>`_
* Remove Backbone dependency from webhook wrappers by `@guerler <https://github.com/guerler>`_ in `#20797 <https://github.com/galaxyproject/galaxy/pull/20797>`_
* Fix fsspec fs path handling by `@davelopez <https://github.com/davelopez>`_ in `#20799 <https://github.com/galaxyproject/galaxy/pull/20799>`_
* Add Hugging Face 🤗 file source and user-defined template by `@davelopez <https://github.com/davelopez>`_ in `#20805 <https://github.com/galaxyproject/galaxy/pull/20805>`_
* Refactor MESSAGES constant in FileSourceTypeSpan.vue by `@davelopez <https://github.com/davelopez>`_ in `#20806 <https://github.com/galaxyproject/galaxy/pull/20806>`_
* Fix new linting errors in unit test mounts by `@davelopez <https://github.com/davelopez>`_ in `#20807 <https://github.com/galaxyproject/galaxy/pull/20807>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#20812 <https://github.com/galaxyproject/galaxy/pull/20812>`_
* Enable data label column selection in basic Plotly plots and add heatmap by `@guerler <https://github.com/guerler>`_ in `#20813 <https://github.com/galaxyproject/galaxy/pull/20813>`_
* Upgrade Prettier 3 by `@dannon <https://github.com/dannon>`_ in `#20815 <https://github.com/galaxyproject/galaxy/pull/20815>`_
* Update 2 docs pages by `@nsoranzo <https://github.com/nsoranzo>`_ in `#20824 <https://github.com/galaxyproject/galaxy/pull/20824>`_
* Add small improvements for running CWL tools by `@nsoranzo <https://github.com/nsoranzo>`_ in `#20826 <https://github.com/galaxyproject/galaxy/pull/20826>`_
* Bump jspdf from 2.5.1 to 3.0.2 in /client by `@dependabot[bot] <https://github.com/dependabot[bot]>`_ in `#20828 <https://github.com/galaxyproject/galaxy/pull/20828>`_
* Migrate icon defs in CollectionOperations.vue to best practices. by `@jmchilton <https://github.com/jmchilton>`_ in `#20829 <https://github.com/galaxyproject/galaxy/pull/20829>`_
* Update pytest to v8 by `@nsoranzo <https://github.com/nsoranzo>`_ in `#20838 <https://github.com/galaxyproject/galaxy/pull/20838>`_
* Modernize tools in the filters/ dir by `@natefoo <https://github.com/natefoo>`_ in `#20840 <https://github.com/galaxyproject/galaxy/pull/20840>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#20841 <https://github.com/galaxyproject/galaxy/pull/20841>`_
* Update Integration tests by `@nsoranzo <https://github.com/nsoranzo>`_ in `#20844 <https://github.com/galaxyproject/galaxy/pull/20844>`_
* Allow adding extra steps to the default pipeline of the OIDC authentication by `@marius-mather <https://github.com/marius-mather>`_ in `#20845 <https://github.com/galaxyproject/galaxy/pull/20845>`_
* Use a streaming based parser (ijson) when setting metadata for biom1 files. by `@ksuderman <https://github.com/ksuderman>`_ in `#20851 <https://github.com/galaxyproject/galaxy/pull/20851>`_
* Support remote file source hashes by `@davelopez <https://github.com/davelopez>`_ in `#20853 <https://github.com/galaxyproject/galaxy/pull/20853>`_
* Various Container Execution Enhancements (including GCP Batch support) by `@jmchilton <https://github.com/jmchilton>`_ in `#20862 <https://github.com/galaxyproject/galaxy/pull/20862>`_
* Update maf tools with profiles, required_files, and requirements. by `@natefoo <https://github.com/natefoo>`_ in `#20865 <https://github.com/galaxyproject/galaxy/pull/20865>`_
* Add support for hierarchical module systems in lmod + module dependency resolvers by `@t1mk1k <https://github.com/t1mk1k>`_ in `#20866 <https://github.com/galaxyproject/galaxy/pull/20866>`_
* Replace tour_generator webhook with internal API and frontend by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#20868 <https://github.com/galaxyproject/galaxy/pull/20868>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#20869 <https://github.com/galaxyproject/galaxy/pull/20869>`_
* Improve type annotation for job runners and ``InteractiveToolManager`` by `@nsoranzo <https://github.com/nsoranzo>`_ in `#20871 <https://github.com/galaxyproject/galaxy/pull/20871>`_
* Add axt and maf to auto_compressed_types by `@richard-burhans <https://github.com/richard-burhans>`_ in `#20875 <https://github.com/galaxyproject/galaxy/pull/20875>`_
* Drop Python helper script from sort1 tool by `@nsoranzo <https://github.com/nsoranzo>`_ in `#20876 <https://github.com/galaxyproject/galaxy/pull/20876>`_
* Update JupyterLite version to 0.6.4 by `@guerler <https://github.com/guerler>`_ in `#20877 <https://github.com/galaxyproject/galaxy/pull/20877>`_
* Add visualization navigation guard by `@dannon <https://github.com/dannon>`_ in `#20881 <https://github.com/galaxyproject/galaxy/pull/20881>`_
* Add main tool CI tests by `@nsoranzo <https://github.com/nsoranzo>`_ in `#20884 <https://github.com/galaxyproject/galaxy/pull/20884>`_
* Bump vite from 6.3.5 to 6.3.6 in /client-api by `@dependabot[bot] <https://github.com/dependabot[bot]>`_ in `#20885 <https://github.com/galaxyproject/galaxy/pull/20885>`_
* Set default option to make datasets accessible only to individual users when sharing histories with particular users by `@davelopez <https://github.com/davelopez>`_ in `#20886 <https://github.com/galaxyproject/galaxy/pull/20886>`_
* Refactor sharing logic for unified type handling by `@davelopez <https://github.com/davelopez>`_ in `#20888 <https://github.com/galaxyproject/galaxy/pull/20888>`_
* Replace deprecated ``codecs.open()`` by `@nsoranzo <https://github.com/nsoranzo>`_ in `#20891 <https://github.com/galaxyproject/galaxy/pull/20891>`_
* Small cleanup of tool execution code. by `@jmchilton <https://github.com/jmchilton>`_ in `#20899 <https://github.com/galaxyproject/galaxy/pull/20899>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#20905 <https://github.com/galaxyproject/galaxy/pull/20905>`_
* Add Multiple Sequence Alignment Viewer 2.0 by `@guerler <https://github.com/guerler>`_ in `#20907 <https://github.com/galaxyproject/galaxy/pull/20907>`_
* Improve Invocation View step display by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#20912 <https://github.com/galaxyproject/galaxy/pull/20912>`_
* Allow creation of visualizations without dataset by `@guerler <https://github.com/guerler>`_ in `#20914 <https://github.com/galaxyproject/galaxy/pull/20914>`_
* Enable dependabot version updates for GitHub actions by `@nsoranzo <https://github.com/nsoranzo>`_ in `#20915 <https://github.com/galaxyproject/galaxy/pull/20915>`_
* Add support for picking ``from_work_dir`` directory by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20916 <https://github.com/galaxyproject/galaxy/pull/20916>`_
* Include format in internal json model by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20917 <https://github.com/galaxyproject/galaxy/pull/20917>`_
* Bump docker/login-action from 2 to 3 by `@dependabot[bot] <https://github.com/dependabot[bot]>`_ in `#20918 <https://github.com/galaxyproject/galaxy/pull/20918>`_
* Bump docker/build-push-action from 4 to 6 by `@dependabot[bot] <https://github.com/dependabot[bot]>`_ in `#20919 <https://github.com/galaxyproject/galaxy/pull/20919>`_
* Bump actions/setup-node from 4 to 5 by `@dependabot[bot] <https://github.com/dependabot[bot]>`_ in `#20921 <https://github.com/galaxyproject/galaxy/pull/20921>`_
* Bump docker/setup-buildx-action from 2 to 3 by `@dependabot[bot] <https://github.com/dependabot[bot]>`_ in `#20922 <https://github.com/galaxyproject/galaxy/pull/20922>`_
* Add tool to add nesting level to collection by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#20926 <https://github.com/galaxyproject/galaxy/pull/20926>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#20930 <https://github.com/galaxyproject/galaxy/pull/20930>`_
* Make jupyterlite default visualization for ipynb by `@guerler <https://github.com/guerler>`_ in `#20931 <https://github.com/galaxyproject/galaxy/pull/20931>`_
* Allow addressing user defined tools in job config by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20932 <https://github.com/galaxyproject/galaxy/pull/20932>`_
* Wire up and test resource requirement via tpv  by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20936 <https://github.com/galaxyproject/galaxy/pull/20936>`_
* Bump actions/checkout from 4 to 5 by `@dependabot[bot] <https://github.com/dependabot[bot]>`_ in `#20937 <https://github.com/galaxyproject/galaxy/pull/20937>`_
* Bump peter-evans/create-pull-request from 6 to 7 by `@dependabot[bot] <https://github.com/dependabot[bot]>`_ in `#20938 <https://github.com/galaxyproject/galaxy/pull/20938>`_
* Bump docker/metadata-action from 4 to 5 by `@dependabot[bot] <https://github.com/dependabot[bot]>`_ in `#20939 <https://github.com/galaxyproject/galaxy/pull/20939>`_
* Bump actions/setup-python from 5 to 6 by `@dependabot[bot] <https://github.com/dependabot[bot]>`_ in `#20940 <https://github.com/galaxyproject/galaxy/pull/20940>`_
* Bump actions/github-script from 7 to 8 by `@dependabot[bot] <https://github.com/dependabot[bot]>`_ in `#20941 <https://github.com/galaxyproject/galaxy/pull/20941>`_
* Adds IGV.js Visualization by `@guerler <https://github.com/guerler>`_ in `#20943 <https://github.com/galaxyproject/galaxy/pull/20943>`_
* Add a dedicated `ToolFormTags` component for tool form output tags by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#20945 <https://github.com/galaxyproject/galaxy/pull/20945>`_
* Limit admin requirement of selected tool data api endpoints by `@guerler <https://github.com/guerler>`_ in `#20949 <https://github.com/galaxyproject/galaxy/pull/20949>`_
* Add resource docs and tweak tool source schema title generation by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20951 <https://github.com/galaxyproject/galaxy/pull/20951>`_
* Allow specifying a command for determining a docker host port by `@natefoo <https://github.com/natefoo>`_ in `#20953 <https://github.com/galaxyproject/galaxy/pull/20953>`_
* Allow sending and tracking landing request origin by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20957 <https://github.com/galaxyproject/galaxy/pull/20957>`_
* Track landing request with invocation by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20960 <https://github.com/galaxyproject/galaxy/pull/20960>`_
* Use nodejs-wheel to install node by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20963 <https://github.com/galaxyproject/galaxy/pull/20963>`_
* Move tours schema to schema directory (to fix package structure) by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#20965 <https://github.com/galaxyproject/galaxy/pull/20965>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#20968 <https://github.com/galaxyproject/galaxy/pull/20968>`_
* Log task execution errors with log.exception by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20970 <https://github.com/galaxyproject/galaxy/pull/20970>`_
* Bump actions/labeler from 5 to 6 by `@dependabot[bot] <https://github.com/dependabot[bot]>`_ in `#20976 <https://github.com/galaxyproject/galaxy/pull/20976>`_
* Simplify plugin staging with explicit clean step by `@dannon <https://github.com/dannon>`_ in `#20983 <https://github.com/galaxyproject/galaxy/pull/20983>`_
* Bump vitessce to 3.8.2 by `@guerler <https://github.com/guerler>`_ in `#21003 <https://github.com/galaxyproject/galaxy/pull/21003>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#21005 <https://github.com/galaxyproject/galaxy/pull/21005>`_
* Fix and migrate HIV-TRACE to Charts Visualization Framework by `@guerler <https://github.com/guerler>`_ in `#21006 <https://github.com/galaxyproject/galaxy/pull/21006>`_
* Add README and update the minimal visualization example by `@guerler <https://github.com/guerler>`_ in `#21007 <https://github.com/galaxyproject/galaxy/pull/21007>`_
* Add freq.json datatype subclass by `@guerler <https://github.com/guerler>`_ in `#21012 <https://github.com/galaxyproject/galaxy/pull/21012>`_
* Bump up total-perspective-vortex dependency by `@mvdbeek <https://github.com/mvdbeek>`_ in `#21014 <https://github.com/galaxyproject/galaxy/pull/21014>`_
* Fix GCard Layout and White Spaces by `@itisAliRH <https://github.com/itisAliRH>`_ in `#21026 <https://github.com/galaxyproject/galaxy/pull/21026>`_
* Add Keyboard Navigation to History Lists by `@itisAliRH <https://github.com/itisAliRH>`_ in `#21035 <https://github.com/galaxyproject/galaxy/pull/21035>`_
* Add 2 net utilities to the min image by `@afgane <https://github.com/afgane>`_ in `#21085 <https://github.com/galaxyproject/galaxy/pull/21085>`_
* Use workflow-style payload in data landing request by `@mvdbeek <https://github.com/mvdbeek>`_ in `#21107 <https://github.com/galaxyproject/galaxy/pull/21107>`_
* Release notes by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#21162 <https://github.com/galaxyproject/galaxy/pull/21162>`_
* Add Release Drafter GitHub Action integration by `@dannon <https://github.com/dannon>`_ in `#21195 <https://github.com/galaxyproject/galaxy/pull/21195>`_
* Tighter API for tool run tagging. by `@jmchilton <https://github.com/jmchilton>`_ in `#21210 <https://github.com/galaxyproject/galaxy/pull/21210>`_
* Makes "set as current" the primary action in history list by `@davelopez <https://github.com/davelopez>`_ in `#21233 <https://github.com/galaxyproject/galaxy/pull/21233>`_
* Optimize /api/invocations/steps/{step_id} by `@mvdbeek <https://github.com/mvdbeek>`_ in `#21249 <https://github.com/galaxyproject/galaxy/pull/21249>`_
* [igv] Allow selection of genomes from history fasta/2bit by `@guerler <https://github.com/guerler>`_ in `#21269 <https://github.com/galaxyproject/galaxy/pull/21269>`_
* Update tool profile version for credentials by `@davelopez <https://github.com/davelopez>`_ in `#21273 <https://github.com/galaxyproject/galaxy/pull/21273>`_
* New datatype addition: HAL by `@SaimMomin12 <https://github.com/SaimMomin12>`_ in `#21379 <https://github.com/galaxyproject/galaxy/pull/21379>`_
* Add PNTS datatype for 3D Tiles Point Cloud by `@kgerb <https://github.com/kgerb>`_ in `#21414 <https://github.com/galaxyproject/galaxy/pull/21414>`_
* A better way to designate config_watcher by `@jdavcs <https://github.com/jdavcs>`_ in `#21426 <https://github.com/galaxyproject/galaxy/pull/21426>`_
* Optionally include column headers in sample sheet file by `@mvdbeek <https://github.com/mvdbeek>`_ in `#21439 <https://github.com/galaxyproject/galaxy/pull/21439>`_

=============
Other changes
=============

* Small tweaks and cleanup from sample sheets branch by `@jmchilton <https://github.com/jmchilton>`_ in `#20229 <https://github.com/galaxyproject/galaxy/pull/20229>`_
* Version 25.1.dev by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#20268 <https://github.com/galaxyproject/galaxy/pull/20268>`_
* Merge `release_25.0` into `dev` by `@davelopez <https://github.com/davelopez>`_ in `#20484 <https://github.com/galaxyproject/galaxy/pull/20484>`_
* Merge release_25.0 into dev by `@davelopez <https://github.com/davelopez>`_ in `#20490 <https://github.com/galaxyproject/galaxy/pull/20490>`_
* Bump pillow from 11.2.1 to 11.3.0 in /lib/galaxy/dependencies by `@dependabot[bot] <https://github.com/dependabot[bot]>`_ in `#20591 <https://github.com/galaxyproject/galaxy/pull/20591>`_
* Bump linkifyjs from 4.1.1 to 4.3.2 in /client by `@dependabot[bot] <https://github.com/dependabot[bot]>`_ in `#20707 <https://github.com/galaxyproject/galaxy/pull/20707>`_
* Sample Sheet Bug Fixes around Preserving Collection Metadata by `@jmchilton <https://github.com/jmchilton>`_ in `#20749 <https://github.com/galaxyproject/galaxy/pull/20749>`_
* Add tool_id and tool_version column to tool_landing_request table by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20795 <https://github.com/galaxyproject/galaxy/pull/20795>`_
* Implement bare-bones view of sample sheet collections as sheet. by `@jmchilton <https://github.com/jmchilton>`_ in `#20798 <https://github.com/galaxyproject/galaxy/pull/20798>`_
* Fix webpack dev server detection by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20822 <https://github.com/galaxyproject/galaxy/pull/20822>`_
* Fix optional numeric column definitions for sample sheets. by `@jmchilton <https://github.com/jmchilton>`_ in `#20830 <https://github.com/galaxyproject/galaxy/pull/20830>`_
* Validate sample sheet column definitions in workflow definitions on backend. by `@jmchilton <https://github.com/jmchilton>`_ in `#20880 <https://github.com/galaxyproject/galaxy/pull/20880>`_
* Bump axios from 1.8.2 to 1.12.0 in /client by `@dependabot[bot] <https://github.com/dependabot[bot]>`_ in `#20906 <https://github.com/galaxyproject/galaxy/pull/20906>`_
* Merge 25.0 into dev by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#20911 <https://github.com/galaxyproject/galaxy/pull/20911>`_
* Bump default milestone to 26.0 by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#20946 <https://github.com/galaxyproject/galaxy/pull/20946>`_
* Add 25.1 migration tags by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#21017 <https://github.com/galaxyproject/galaxy/pull/21017>`_
* Update version to 25.1.rc1 by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#21019 <https://github.com/galaxyproject/galaxy/pull/21019>`_
* Restore .get_metadata function by `@mvdbeek <https://github.com/mvdbeek>`_ in `#21045 <https://github.com/galaxyproject/galaxy/pull/21045>`_
* Fix ``TOOL_WITH_SHELL_COMMAND``  import source by `@mvdbeek <https://github.com/mvdbeek>`_ in `#21070 <https://github.com/galaxyproject/galaxy/pull/21070>`_
* Drop fastapi extra dep from sentry-sdk by `@mvdbeek <https://github.com/mvdbeek>`_ in `#21156 <https://github.com/galaxyproject/galaxy/pull/21156>`_
* Resolve possible symlink before establishing tool file location by `@mvdbeek <https://github.com/mvdbeek>`_ in `#21175 <https://github.com/galaxyproject/galaxy/pull/21175>`_
* Fix forward merge by `@mvdbeek <https://github.com/mvdbeek>`_ in `#21307 <https://github.com/galaxyproject/galaxy/pull/21307>`_
* Fix db revision tags by `@mvdbeek <https://github.com/mvdbeek>`_ in `#21442 <https://github.com/galaxyproject/galaxy/pull/21442>`_

-------------------
25.0.4 (2025-11-18)
-------------------


=========
Bug fixes
=========

* Add safetensors datatype by `@nilchia <https://github.com/nilchia>`_ in `#20754 <https://github.com/galaxyproject/galaxy/pull/20754>`_
* Skip sam metadata if we have too many references by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20820 <https://github.com/galaxyproject/galaxy/pull/20820>`_
* Fix select field cut off in dataset view by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#20947 <https://github.com/galaxyproject/galaxy/pull/20947>`_
* Check for expiration in refresh token dictionary by `@jdavcs <https://github.com/jdavcs>`_ in `#20954 <https://github.com/galaxyproject/galaxy/pull/20954>`_
* Deactivate user file source on unknown error by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20962 <https://github.com/galaxyproject/galaxy/pull/20962>`_
* Don't create workflow outputs to recover input parameter outputs by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20980 <https://github.com/galaxyproject/galaxy/pull/20980>`_
* Fix ``test_multiple_decorators`` unit test for FastAPI 0.118.0 by `@nsoranzo <https://github.com/nsoranzo>`_ in `#20982 <https://github.com/galaxyproject/galaxy/pull/20982>`_
* Fix PUT /api/workflows for user defined tools by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20987 <https://github.com/galaxyproject/galaxy/pull/20987>`_
* Backport of #20984 by `@davelopez <https://github.com/davelopez>`_ in `#20994 <https://github.com/galaxyproject/galaxy/pull/20994>`_
* Improves zip file type detection for uploads under windows by `@caroott <https://github.com/caroott>`_ in `#20999 <https://github.com/galaxyproject/galaxy/pull/20999>`_
* Store pulsar job prep error messages by `@mvdbeek <https://github.com/mvdbeek>`_ in `#21013 <https://github.com/galaxyproject/galaxy/pull/21013>`_
* Require OK datasets for filtering empty datasets by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#21023 <https://github.com/galaxyproject/galaxy/pull/21023>`_
* Fix `InvalidRequestError` when saving workflow step with dynamic tool by `@mvdbeek <https://github.com/mvdbeek>`_ in `#21056 <https://github.com/galaxyproject/galaxy/pull/21056>`_
* Fix has_size assertion  by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#21081 <https://github.com/galaxyproject/galaxy/pull/21081>`_
* Run landing request state through validator by `@mvdbeek <https://github.com/mvdbeek>`_ in `#21087 <https://github.com/galaxyproject/galaxy/pull/21087>`_
* Fix workflow run form input restrictions by `@mvdbeek <https://github.com/mvdbeek>`_ in `#21095 <https://github.com/galaxyproject/galaxy/pull/21095>`_
* Backport fix anndata datatype update by `@nilchia <https://github.com/nilchia>`_ in `#21111 <https://github.com/galaxyproject/galaxy/pull/21111>`_
* Prefix download link by `@martenson <https://github.com/martenson>`_ in `#21112 <https://github.com/galaxyproject/galaxy/pull/21112>`_
* Create new datasets when creating skipped database operation tool outputs by `@mvdbeek <https://github.com/mvdbeek>`_ in `#21142 <https://github.com/galaxyproject/galaxy/pull/21142>`_
* Fix workflow landing rendering if public query param not provided by `@mvdbeek <https://github.com/mvdbeek>`_ in `#21165 <https://github.com/galaxyproject/galaxy/pull/21165>`_
* Fix optional param unset in RO-Crate export by `@davelopez <https://github.com/davelopez>`_ in `#21192 <https://github.com/galaxyproject/galaxy/pull/21192>`_
* Fix MIME type for LAZ datatype by `@kysrpex <https://github.com/kysrpex>`_ in `#21202 <https://github.com/galaxyproject/galaxy/pull/21202>`_
* Fix refresh token expiration retrieval logic by `@nuwang <https://github.com/nuwang>`_ in `#21213 <https://github.com/galaxyproject/galaxy/pull/21213>`_
* Fix direct tool execution not using the latest version by `@jmchilton <https://github.com/jmchilton>`_ in `#21240 <https://github.com/galaxyproject/galaxy/pull/21240>`_
* Fix proxy url validation for non-printable characters by `@davelopez <https://github.com/davelopez>`_ in `#21280 <https://github.com/galaxyproject/galaxy/pull/21280>`_
* Swap to NPM trusted publishing for prebuilt client by `@dannon <https://github.com/dannon>`_ in `#21290 <https://github.com/galaxyproject/galaxy/pull/21290>`_

============
Enhancements
============

* Add Auspice JSON datatype by `@pvanheus <https://github.com/pvanheus>`_ in `#20466 <https://github.com/galaxyproject/galaxy/pull/20466>`_
* Add SpatialData datatype by `@nilchia <https://github.com/nilchia>`_ in `#21000 <https://github.com/galaxyproject/galaxy/pull/21000>`_
* Use job cache also for implicit conversions by `@mvdbeek <https://github.com/mvdbeek>`_ in `#21021 <https://github.com/galaxyproject/galaxy/pull/21021>`_
* Add LAS and LAZ file format by `@bgruening <https://github.com/bgruening>`_ in `#21049 <https://github.com/galaxyproject/galaxy/pull/21049>`_
* New datatype addition: gam for vg toolkit by `@SaimMomin12 <https://github.com/SaimMomin12>`_ in `#21096 <https://github.com/galaxyproject/galaxy/pull/21096>`_
* Harden proxy redirect validation by `@davelopez <https://github.com/davelopez>`_ in `#21185 <https://github.com/galaxyproject/galaxy/pull/21185>`_
* support ZARR v3 for  Spatialdata dt by `@nilchia <https://github.com/nilchia>`_ in `#21265 <https://github.com/galaxyproject/galaxy/pull/21265>`_

=============
Other changes
=============

* New datatype addition: beast.trees datatype by `@SaimMomin12 <https://github.com/SaimMomin12>`_ in `#21055 <https://github.com/galaxyproject/galaxy/pull/21055>`_
* Add display_in_upload to LAZ and LAS by `@bgruening <https://github.com/bgruening>`_ in `#21060 <https://github.com/galaxyproject/galaxy/pull/21060>`_
* Backport `Fix proxy endpoint encoding` by `@davelopez <https://github.com/davelopez>`_ in `#21184 <https://github.com/galaxyproject/galaxy/pull/21184>`_

-------------------
25.0.3 (2025-09-23)
-------------------


=========
Bug fixes
=========

* Cascade newly created windows in window manager by `@guerler <https://github.com/guerler>`_ in `#20780 <https://github.com/galaxyproject/galaxy/pull/20780>`_
* Remove ``packages/meta/requirements.txt`` by `@nsoranzo <https://github.com/nsoranzo>`_ in `#20782 <https://github.com/galaxyproject/galaxy/pull/20782>`_
* Ensure that workflow invocations are persisted with state by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20784 <https://github.com/galaxyproject/galaxy/pull/20784>`_
* Fix password reset functionality for lowercase emails by `@jdavcs <https://github.com/jdavcs>`_ in `#20801 <https://github.com/galaxyproject/galaxy/pull/20801>`_
* Fix token refresh bug (cilogon) by `@jdavcs <https://github.com/jdavcs>`_ in `#20821 <https://github.com/galaxyproject/galaxy/pull/20821>`_
* Disable Run Tool button when there are errors by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#20839 <https://github.com/galaxyproject/galaxy/pull/20839>`_
* Update Celery section in admin docs by `@jdavcs <https://github.com/jdavcs>`_ in `#20856 <https://github.com/galaxyproject/galaxy/pull/20856>`_
* Drop eager argument from invocation related methods by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20863 <https://github.com/galaxyproject/galaxy/pull/20863>`_
* Improve dataset collection fetch performance in the invocation view by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#20870 <https://github.com/galaxyproject/galaxy/pull/20870>`_
* Use ``populated_optimized`` when serializing collection by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20872 <https://github.com/galaxyproject/galaxy/pull/20872>`_
* Fix role.description bug by `@jdavcs <https://github.com/jdavcs>`_ in `#20883 <https://github.com/galaxyproject/galaxy/pull/20883>`_
* Speed up ``ImplicitCollectionJobs.job_list`` by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20887 <https://github.com/galaxyproject/galaxy/pull/20887>`_
* Bump up integration test k8s version by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20889 <https://github.com/galaxyproject/galaxy/pull/20889>`_
* Make check for existing user in custos_authnz.py case insensitive by `@cat-bro <https://github.com/cat-bro>`_ in `#20893 <https://github.com/galaxyproject/galaxy/pull/20893>`_
* Add LDDA purged property by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20895 <https://github.com/galaxyproject/galaxy/pull/20895>`_
* Avoid potential race condition in replacement_for_connection by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20909 <https://github.com/galaxyproject/galaxy/pull/20909>`_
* Fix sessionless tag creation by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20925 <https://github.com/galaxyproject/galaxy/pull/20925>`_
* Fix collection element sorting in extended_metadata by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20928 <https://github.com/galaxyproject/galaxy/pull/20928>`_

============
Enhancements
============

* Render Tool Descriptions in Markdown in TRS imports by `@itisAliRH <https://github.com/itisAliRH>`_ in `#20814 <https://github.com/galaxyproject/galaxy/pull/20814>`_
* Fix DOCX detection and add PPTX support by `@arash77 <https://github.com/arash77>`_ in `#20827 <https://github.com/galaxyproject/galaxy/pull/20827>`_
* Include galaxy user agent in data source tools by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20836 <https://github.com/galaxyproject/galaxy/pull/20836>`_
* Add HiC datatype by `@abretaud <https://github.com/abretaud>`_ in `#20874 <https://github.com/galaxyproject/galaxy/pull/20874>`_

=============
Other changes
=============

* Undo accidental push by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#20854 <https://github.com/galaxyproject/galaxy/pull/20854>`_
* Merge 25.0 into dev by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#20911 <https://github.com/galaxyproject/galaxy/pull/20911>`_

-------------------
25.0.2 (2025-08-13)
-------------------


=========
Bug fixes
=========

* Remove ``num_unique_values`` tiff metadata element by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20464 <https://github.com/galaxyproject/galaxy/pull/20464>`_
* Bump up python for for pulsar package tests by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20521 <https://github.com/galaxyproject/galaxy/pull/20521>`_
* Update Gravity to 1.0.8 by `@natefoo <https://github.com/natefoo>`_ in `#20523 <https://github.com/galaxyproject/galaxy/pull/20523>`_
* Prevent DCE collections from being renamed by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#20534 <https://github.com/galaxyproject/galaxy/pull/20534>`_
* Use venv instead of virtualenv in package `make setup-venv` by `@natefoo <https://github.com/natefoo>`_ in `#20536 <https://github.com/galaxyproject/galaxy/pull/20536>`_
* Move definition of ``DatasetCollectionDescriptionT`` before its use by `@nsoranzo <https://github.com/nsoranzo>`_ in `#20539 <https://github.com/galaxyproject/galaxy/pull/20539>`_
* Fix docs versioning by `@nsoranzo <https://github.com/nsoranzo>`_ in `#20542 <https://github.com/galaxyproject/galaxy/pull/20542>`_
* Fix restricting user defined tool input datasets extensions by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20545 <https://github.com/galaxyproject/galaxy/pull/20545>`_
* Fix description and metadata of some packages by `@nsoranzo <https://github.com/nsoranzo>`_ in `#20546 <https://github.com/galaxyproject/galaxy/pull/20546>`_
* Fix activity bar reordering persistence by `@dannon <https://github.com/dannon>`_ in `#20550 <https://github.com/galaxyproject/galaxy/pull/20550>`_
* Fix PDF preview functionality in dataset view by `@dannon <https://github.com/dannon>`_ in `#20552 <https://github.com/galaxyproject/galaxy/pull/20552>`_
* Propagate cached job output replacement to copies of outputs by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20553 <https://github.com/galaxyproject/galaxy/pull/20553>`_
* Fix workflow invocation report pdf generate by `@itisAliRH <https://github.com/itisAliRH>`_ in `#20558 <https://github.com/galaxyproject/galaxy/pull/20558>`_
* Fix Storage Dashboard Link to Dataset Details by `@itisAliRH <https://github.com/itisAliRH>`_ in `#20565 <https://github.com/galaxyproject/galaxy/pull/20565>`_
* Upgrade requests-unixsocket for requests compatibility by `@natefoo <https://github.com/natefoo>`_ in `#20566 <https://github.com/galaxyproject/galaxy/pull/20566>`_
* Don't assume cwd = job directory when running prepare dirs by `@natefoo <https://github.com/natefoo>`_ in `#20571 <https://github.com/galaxyproject/galaxy/pull/20571>`_
* Fix planemo serve, need user list by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20575 <https://github.com/galaxyproject/galaxy/pull/20575>`_
* Fix apply rules ownership check by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20582 <https://github.com/galaxyproject/galaxy/pull/20582>`_
* Don't fail volume mount construction for tools without tool directory by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20593 <https://github.com/galaxyproject/galaxy/pull/20593>`_
* Prevent importing workflows with invalid step UUID by `@davelopez <https://github.com/davelopez>`_ in `#20596 <https://github.com/galaxyproject/galaxy/pull/20596>`_
* Fix workflow loading error handling by `@davelopez <https://github.com/davelopez>`_ in `#20597 <https://github.com/galaxyproject/galaxy/pull/20597>`_
* Do not set attribute on a namedtuple by `@jdavcs <https://github.com/jdavcs>`_ in `#20599 <https://github.com/galaxyproject/galaxy/pull/20599>`_
* Constraint conditional `redis` version to allow only minor updates by `@davelopez <https://github.com/davelopez>`_ in `#20603 <https://github.com/galaxyproject/galaxy/pull/20603>`_
* fix Admin job limit query by `@martenson <https://github.com/martenson>`_ in `#20626 <https://github.com/galaxyproject/galaxy/pull/20626>`_
* Correct visualization response schema by `@guerler <https://github.com/guerler>`_ in `#20627 <https://github.com/galaxyproject/galaxy/pull/20627>`_
* Ignore webob http exceptions for logging purposes by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20630 <https://github.com/galaxyproject/galaxy/pull/20630>`_
* Fix HistoryDatasetAsTable by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20636 <https://github.com/galaxyproject/galaxy/pull/20636>`_
* Fix bug: tool output file may be overwritten by Runner's multi work t… by `@jianzuoyi <https://github.com/jianzuoyi>`_ in `#20639 <https://github.com/galaxyproject/galaxy/pull/20639>`_
* Fix IntersectionObserver updates when replacing items by `@davelopez <https://github.com/davelopez>`_ in `#20646 <https://github.com/galaxyproject/galaxy/pull/20646>`_
* Fix optional unspecified input to conditional step by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20647 <https://github.com/galaxyproject/galaxy/pull/20647>`_
* Avoid postgres truncation of aliases and labels by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20649 <https://github.com/galaxyproject/galaxy/pull/20649>`_
* Fix deferred datasets in multiple dataset parameters. by `@jmchilton <https://github.com/jmchilton>`_ in `#20650 <https://github.com/galaxyproject/galaxy/pull/20650>`_
* Fix empty default Optionals for tool_shed_repositories API. by `@jmchilton <https://github.com/jmchilton>`_ in `#20656 <https://github.com/galaxyproject/galaxy/pull/20656>`_
* Remove content from ``packages/meta/requirements.txt`` by `@nsoranzo <https://github.com/nsoranzo>`_ in `#20662 <https://github.com/galaxyproject/galaxy/pull/20662>`_
* Add `num_unique_values` tiff metadata element, fixed by `@kostrykin <https://github.com/kostrykin>`_ in `#20669 <https://github.com/galaxyproject/galaxy/pull/20669>`_
* Bump up pulsar dependency to 0.15.9 by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20672 <https://github.com/galaxyproject/galaxy/pull/20672>`_
* Fix invocation header by `@qchiujunhao <https://github.com/qchiujunhao>`_ in `#20676 <https://github.com/galaxyproject/galaxy/pull/20676>`_
* Fix scratchbook display by `@dannon <https://github.com/dannon>`_ in `#20684 <https://github.com/galaxyproject/galaxy/pull/20684>`_
* Fix Invenio file downloads for published records with draft by `@davelopez <https://github.com/davelopez>`_ in `#20685 <https://github.com/galaxyproject/galaxy/pull/20685>`_
* Input linter: add missing attribute to `sort_by` by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#20693 <https://github.com/galaxyproject/galaxy/pull/20693>`_
* Fix dataset serializers and response models by `@arash77 <https://github.com/arash77>`_ in `#20694 <https://github.com/galaxyproject/galaxy/pull/20694>`_
* Add username filter to published pages grid by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#20703 <https://github.com/galaxyproject/galaxy/pull/20703>`_
* Fix parameter models for optional color params. by `@jmchilton <https://github.com/jmchilton>`_ in `#20705 <https://github.com/galaxyproject/galaxy/pull/20705>`_
* Prevent negative offset in historyStore handleTotalCountChange by `@davelopez <https://github.com/davelopez>`_ in `#20708 <https://github.com/galaxyproject/galaxy/pull/20708>`_
* Fix click to edit link by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20710 <https://github.com/galaxyproject/galaxy/pull/20710>`_
* Fix ``test_base_image_for_targets`` mulled test to use mzmine by `@nsoranzo <https://github.com/nsoranzo>`_ in `#20713 <https://github.com/galaxyproject/galaxy/pull/20713>`_
* DatasetView Header - fixes text wrapping issues on small screens by `@dannon <https://github.com/dannon>`_ in `#20721 <https://github.com/galaxyproject/galaxy/pull/20721>`_
* Update galaxy-release-util by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20727 <https://github.com/galaxyproject/galaxy/pull/20727>`_
* Fix maximum workflow invocation duration test by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20729 <https://github.com/galaxyproject/galaxy/pull/20729>`_
* Remove base_dir from zip in make_fast_zipfile by `@davelopez <https://github.com/davelopez>`_ in `#20739 <https://github.com/galaxyproject/galaxy/pull/20739>`_
* fix config for nginx in docs by `@martenson <https://github.com/martenson>`_ in `#20757 <https://github.com/galaxyproject/galaxy/pull/20757>`_

============
Enhancements
============

* add fasta.bz2 as auto_compressed type by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#20496 <https://github.com/galaxyproject/galaxy/pull/20496>`_
* Add redis conditional dependency by `@davelopez <https://github.com/davelopez>`_ in `#20502 <https://github.com/galaxyproject/galaxy/pull/20502>`_
* Improve workflow monitor loop times by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20522 <https://github.com/galaxyproject/galaxy/pull/20522>`_
* Add datatype for LexicMap index by `@Smeds <https://github.com/Smeds>`_ in `#20586 <https://github.com/galaxyproject/galaxy/pull/20586>`_
* Clarify how to separate job and workflow scheduling by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20625 <https://github.com/galaxyproject/galaxy/pull/20625>`_
* Add mzMLb and MBI datatypes by `@chambm <https://github.com/chambm>`_ in `#20632 <https://github.com/galaxyproject/galaxy/pull/20632>`_
* Pairtool updated format and sniffers by `@Smeds <https://github.com/Smeds>`_ in `#20634 <https://github.com/galaxyproject/galaxy/pull/20634>`_
* Add support for M4A audio files by `@arash77 <https://github.com/arash77>`_ in `#20667 <https://github.com/galaxyproject/galaxy/pull/20667>`_

=============
Other changes
=============

* Require user for visualizations create endpoint by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20629 <https://github.com/galaxyproject/galaxy/pull/20629>`_
* Merge 24.2 into 25.0 by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#20681 <https://github.com/galaxyproject/galaxy/pull/20681>`_

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
