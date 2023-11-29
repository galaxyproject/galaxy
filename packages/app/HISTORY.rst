History
-------

.. to_doc

-------------------
23.1.2 (2023-11-29)
-------------------


=========
Bug fixes
=========

* Fix unbound ``runner`` variable when there is an error in the job config by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16906 <https://github.com/galaxyproject/galaxy/pull/16906>`_
* Fix discarded dataset ordering in Storage Dashboard by `@davelopez <https://github.com/davelopez>`_ in `#16929 <https://github.com/galaxyproject/galaxy/pull/16929>`_
* Include owner's annotation when exporting workflow by `@dannon <https://github.com/dannon>`_ in `#16930 <https://github.com/galaxyproject/galaxy/pull/16930>`_
* Skip state filtering in ``__MERGE_COLLECTION__`` tool  by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16937 <https://github.com/galaxyproject/galaxy/pull/16937>`_
* Prevent Singular external auth users from disconnecting identity by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#16961 <https://github.com/galaxyproject/galaxy/pull/16961>`_
* Prevent workflow submission with missing input values by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17048 <https://github.com/galaxyproject/galaxy/pull/17048>`_
* Fix extra files collection if using ``store_by="id"`` and `outputs_to_working_directory` by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17067 <https://github.com/galaxyproject/galaxy/pull/17067>`_
* Remove rollback from ``__check_jobs_at_startup`` by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17085 <https://github.com/galaxyproject/galaxy/pull/17085>`_

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

* read job_conf directly from `config_dir` instead of computing it again from `config_file` by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#15596 <https://github.com/galaxyproject/galaxy/pull/15596>`_
* Fix some drs handling issues by `@nuwang <https://github.com/nuwang>`_ in `#15777 <https://github.com/galaxyproject/galaxy/pull/15777>`_
* Fix filesource file url support by `@nuwang <https://github.com/nuwang>`_ in `#15794 <https://github.com/galaxyproject/galaxy/pull/15794>`_
* Fix revision scripts, run migrations in CI, add repair option, improve migrations utils by `@jdavcs <https://github.com/jdavcs>`_ in `#15811 <https://github.com/galaxyproject/galaxy/pull/15811>`_
* Change confusing pulsar logs message by `@kysrpex <https://github.com/kysrpex>`_ in `#16038 <https://github.com/galaxyproject/galaxy/pull/16038>`_
* Fix and test startup with Python 3.11 on macOS by `@nsoranzo <https://github.com/nsoranzo>`_ in `#16082 <https://github.com/galaxyproject/galaxy/pull/16082>`_
* Fix : Ignore error messages for admin created accounts by `@jvanbraekel <https://github.com/jvanbraekel>`_ in `#16132 <https://github.com/galaxyproject/galaxy/pull/16132>`_
* Ensure session is request-scoped for legacy endpoints by `@jdavcs <https://github.com/jdavcs>`_ in `#16207 <https://github.com/galaxyproject/galaxy/pull/16207>`_
* Fix "database is locked" error (occurring in the context of workflow testing under SQLite) by `@jdavcs <https://github.com/jdavcs>`_ in `#16208 <https://github.com/galaxyproject/galaxy/pull/16208>`_
* Fix ordering of data libraries from API by `@martenson <https://github.com/martenson>`_ in `#16300 <https://github.com/galaxyproject/galaxy/pull/16300>`_
* qualify querying for an api-key by `@martenson <https://github.com/martenson>`_ in `#16320 <https://github.com/galaxyproject/galaxy/pull/16320>`_
* Fix tags ownership by `@davelopez <https://github.com/davelopez>`_ in `#16339 <https://github.com/galaxyproject/galaxy/pull/16339>`_
* Job cache fixes for DCEs by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16384 <https://github.com/galaxyproject/galaxy/pull/16384>`_
* Fix histories count by `@davelopez <https://github.com/davelopez>`_ in `#16400 <https://github.com/galaxyproject/galaxy/pull/16400>`_
* Fix select statement syntax for SQLAlchemy 2.0 by `@jdavcs <https://github.com/jdavcs>`_ in `#16421 <https://github.com/galaxyproject/galaxy/pull/16421>`_
* Fix up unit tests for local use by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16483 <https://github.com/galaxyproject/galaxy/pull/16483>`_
* Run through tmp_dir_creation_statement only once by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16529 <https://github.com/galaxyproject/galaxy/pull/16529>`_
* Fix double-encoding notification content by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16530 <https://github.com/galaxyproject/galaxy/pull/16530>`_
* Limit tool document cache to tool configs with explicit cache path by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16537 <https://github.com/galaxyproject/galaxy/pull/16537>`_
* Fix `multiple` remote test data by `@davelopez <https://github.com/davelopez>`_ in `#16542 <https://github.com/galaxyproject/galaxy/pull/16542>`_
* Ignore errors with user-set job resources by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16579 <https://github.com/galaxyproject/galaxy/pull/16579>`_
* Fix replacement parameters for subworkflows. by `@jmchilton <https://github.com/jmchilton>`_ in `#16592 <https://github.com/galaxyproject/galaxy/pull/16592>`_
* make sure that TMP, TEMP, and TMPDIR are set by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#16594 <https://github.com/galaxyproject/galaxy/pull/16594>`_
* Bump minimum tpv version to 2.3.2 by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16597 <https://github.com/galaxyproject/galaxy/pull/16597>`_
* Backport tool mem fixes by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16601 <https://github.com/galaxyproject/galaxy/pull/16601>`_
* Reload toolbox after forking when using `--preload` by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16620 <https://github.com/galaxyproject/galaxy/pull/16620>`_
* Account for expires/expires_in when refreshing token by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16621 <https://github.com/galaxyproject/galaxy/pull/16621>`_
* Fixes for conditional subworkflow steps by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16632 <https://github.com/galaxyproject/galaxy/pull/16632>`_
* Fix nested conditional workflow steps by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16641 <https://github.com/galaxyproject/galaxy/pull/16641>`_
* Ensure Job belongs to current SA session by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16655 <https://github.com/galaxyproject/galaxy/pull/16655>`_
* Fix expression evaluation for nested state by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16656 <https://github.com/galaxyproject/galaxy/pull/16656>`_
* Make sort_collection tool require terminal datasets by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16661 <https://github.com/galaxyproject/galaxy/pull/16661>`_
* Push to object store even if ``set_meta`` fails by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16667 <https://github.com/galaxyproject/galaxy/pull/16667>`_
* Fix metadata setting in extended metadata + outputs_to_working_directory mode by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16678 <https://github.com/galaxyproject/galaxy/pull/16678>`_
* Fix regex validation for global inline flags by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16683 <https://github.com/galaxyproject/galaxy/pull/16683>`_
* Fix closed transaction error on galaxy startup/check jobs by `@jdavcs <https://github.com/jdavcs>`_ in `#16687 <https://github.com/galaxyproject/galaxy/pull/16687>`_
* Add missing join condition in job search by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16710 <https://github.com/galaxyproject/galaxy/pull/16710>`_
* Fix job search query by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16714 <https://github.com/galaxyproject/galaxy/pull/16714>`_
* Copy the collection contents by default when copying a collection by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16717 <https://github.com/galaxyproject/galaxy/pull/16717>`_
* Fix collection id encoding by `@davelopez <https://github.com/davelopez>`_ in `#16718 <https://github.com/galaxyproject/galaxy/pull/16718>`_
* Workaround for XML nodes of job resource parameters losing their children by `@kysrpex <https://github.com/kysrpex>`_ in `#16728 <https://github.com/galaxyproject/galaxy/pull/16728>`_
* move the email and username redacting from the role loop by `@martenson <https://github.com/martenson>`_ in `#16820 <https://github.com/galaxyproject/galaxy/pull/16820>`_
* Fix parameter display in job info page for tools with sections by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16821 <https://github.com/galaxyproject/galaxy/pull/16821>`_
* Fix workflow preview display if tool state does not contain all parameter values by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16829 <https://github.com/galaxyproject/galaxy/pull/16829>`_
* Fix up local tool version handling by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16836 <https://github.com/galaxyproject/galaxy/pull/16836>`_
* Fix and prevent persisting null file_size by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16855 <https://github.com/galaxyproject/galaxy/pull/16855>`_
* Allow referring to steps by label only in markdown editor by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16861 <https://github.com/galaxyproject/galaxy/pull/16861>`_
* Fix safe update version handling in run form by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16865 <https://github.com/galaxyproject/galaxy/pull/16865>`_
* Remove more flushes in database operation tools by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16875 <https://github.com/galaxyproject/galaxy/pull/16875>`_
* Fix tag ownership check by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16877 <https://github.com/galaxyproject/galaxy/pull/16877>`_

============
Enhancements
============

* Empower Users to Select Storage Destination by `@jmchilton <https://github.com/jmchilton>`_ in `#14073 <https://github.com/galaxyproject/galaxy/pull/14073>`_
* External Login Flow: Redirect users if account already exists by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#15019 <https://github.com/galaxyproject/galaxy/pull/15019>`_
* Add slack error reporting plugin by `@hexylena <https://github.com/hexylena>`_ in `#15025 <https://github.com/galaxyproject/galaxy/pull/15025>`_
* Various Tool Shed Cleanup by `@jmchilton <https://github.com/jmchilton>`_ in `#15247 <https://github.com/galaxyproject/galaxy/pull/15247>`_
* Add Storage Management API by `@davelopez <https://github.com/davelopez>`_ in `#15295 <https://github.com/galaxyproject/galaxy/pull/15295>`_
* OIDC tokens by `@SergeyYakubov <https://github.com/SergeyYakubov>`_ in `#15300 <https://github.com/galaxyproject/galaxy/pull/15300>`_
* Expose additional beaker caching backends  by `@claudiofr <https://github.com/claudiofr>`_ in `#15349 <https://github.com/galaxyproject/galaxy/pull/15349>`_
* Add support for visualizing HDF5 datasets. by `@jarrah42 <https://github.com/jarrah42>`_ in `#15394 <https://github.com/galaxyproject/galaxy/pull/15394>`_
* Towards SQLAlchemy 2.0: drop session autocommit setting by `@jdavcs <https://github.com/jdavcs>`_ in `#15421 <https://github.com/galaxyproject/galaxy/pull/15421>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#15435 <https://github.com/galaxyproject/galaxy/pull/15435>`_
* Fix for new style conda packages by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#15446 <https://github.com/galaxyproject/galaxy/pull/15446>`_
* Move database access code out of tool_util by `@jdavcs <https://github.com/jdavcs>`_ in `#15467 <https://github.com/galaxyproject/galaxy/pull/15467>`_
* Protection against problematic boolean parameters. by `@jmchilton <https://github.com/jmchilton>`_ in `#15493 <https://github.com/galaxyproject/galaxy/pull/15493>`_
* Use connection instead of session for ItemGrabber by `@jdavcs <https://github.com/jdavcs>`_ in `#15496 <https://github.com/galaxyproject/galaxy/pull/15496>`_
* Unify url handling with filesources by `@nuwang <https://github.com/nuwang>`_ in `#15497 <https://github.com/galaxyproject/galaxy/pull/15497>`_
* Move TS to Alembic by `@jdavcs <https://github.com/jdavcs>`_ in `#15509 <https://github.com/galaxyproject/galaxy/pull/15509>`_
* Explore tool remote test data by `@davelopez <https://github.com/davelopez>`_ in `#15510 <https://github.com/galaxyproject/galaxy/pull/15510>`_
* Handle "email_from" config option consistently, as per schema description by `@jdavcs <https://github.com/jdavcs>`_ in `#15557 <https://github.com/galaxyproject/galaxy/pull/15557>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#15564 <https://github.com/galaxyproject/galaxy/pull/15564>`_
* Drop workflow exports to myexperiment.org by `@dannon <https://github.com/dannon>`_ in `#15576 <https://github.com/galaxyproject/galaxy/pull/15576>`_
* Update database_heartbeat for SA 2.0 compatibility by `@jdavcs <https://github.com/jdavcs>`_ in `#15611 <https://github.com/galaxyproject/galaxy/pull/15611>`_
* Add suggested Training material to Tool Form by `@ElectronicBlueberry <https://github.com/ElectronicBlueberry>`_ in `#15628 <https://github.com/galaxyproject/galaxy/pull/15628>`_
* Wrap check_jobs_at_startup operation in a transaction (SA 2.0 compatibility) by `@jdavcs <https://github.com/jdavcs>`_ in `#15643 <https://github.com/galaxyproject/galaxy/pull/15643>`_
* Add Galaxy Notification System by `@davelopez <https://github.com/davelopez>`_ in `#15663 <https://github.com/galaxyproject/galaxy/pull/15663>`_
* Unpin Beaker requirement by `@nsoranzo <https://github.com/nsoranzo>`_ in `#15665 <https://github.com/galaxyproject/galaxy/pull/15665>`_
* Add transactional state to JobHandlerStopQueue by `@jdavcs <https://github.com/jdavcs>`_ in `#15671 <https://github.com/galaxyproject/galaxy/pull/15671>`_
* Verify that activation and reset emails are properly generated by `@guerler <https://github.com/guerler>`_ in `#15681 <https://github.com/galaxyproject/galaxy/pull/15681>`_
* Add transactional state to workflow scheduling manager by `@jdavcs <https://github.com/jdavcs>`_ in `#15683 <https://github.com/galaxyproject/galaxy/pull/15683>`_
* Remove DELETED_NEW job state from code base by `@jdavcs <https://github.com/jdavcs>`_ in `#15690 <https://github.com/galaxyproject/galaxy/pull/15690>`_
* Fix/Enhance recalculate disk usage API endpoint by `@davelopez <https://github.com/davelopez>`_ in `#15739 <https://github.com/galaxyproject/galaxy/pull/15739>`_
* Add API test and refactor code for related:hid history filter by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#15786 <https://github.com/galaxyproject/galaxy/pull/15786>`_
* Migrate to MyST-Parser for Markdown docs by `@nsoranzo <https://github.com/nsoranzo>`_ in `#15844 <https://github.com/galaxyproject/galaxy/pull/15844>`_
* Drop use_legacy_history from config  by `@dannon <https://github.com/dannon>`_ in `#15861 <https://github.com/galaxyproject/galaxy/pull/15861>`_
* Drop database views by `@jdavcs <https://github.com/jdavcs>`_ in `#15876 <https://github.com/galaxyproject/galaxy/pull/15876>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#15890 <https://github.com/galaxyproject/galaxy/pull/15890>`_
* Allow pending inputs in some collection operation tools by `@mvdbeek <https://github.com/mvdbeek>`_ in `#15892 <https://github.com/galaxyproject/galaxy/pull/15892>`_
* Updated doc and tests for attribute value filter by `@tuncK <https://github.com/tuncK>`_ in `#15929 <https://github.com/galaxyproject/galaxy/pull/15929>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#15942 <https://github.com/galaxyproject/galaxy/pull/15942>`_
* Record input datasets and collections at full parameter path by `@mvdbeek <https://github.com/mvdbeek>`_ in `#15978 <https://github.com/galaxyproject/galaxy/pull/15978>`_
* Export tool citations configurable message by `@minh-biocommons <https://github.com/minh-biocommons>`_ in `#15998 <https://github.com/galaxyproject/galaxy/pull/15998>`_
* Add History Archival feature by `@davelopez <https://github.com/davelopez>`_ in `#16003 <https://github.com/galaxyproject/galaxy/pull/16003>`_
* Code cleanups from ruff and pyupgrade by `@nsoranzo <https://github.com/nsoranzo>`_ in `#16035 <https://github.com/galaxyproject/galaxy/pull/16035>`_
* Add missing fields to HistorySummary schema model by `@davelopez <https://github.com/davelopez>`_ in `#16041 <https://github.com/galaxyproject/galaxy/pull/16041>`_
* Vendorise ``packaging.versions.LegacyVersion`` by `@nsoranzo <https://github.com/nsoranzo>`_ in `#16058 <https://github.com/galaxyproject/galaxy/pull/16058>`_
* Add Repository owner field to ToolSearch by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#16061 <https://github.com/galaxyproject/galaxy/pull/16061>`_
* Add count support for listing filters by `@davelopez <https://github.com/davelopez>`_ in `#16075 <https://github.com/galaxyproject/galaxy/pull/16075>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#16086 <https://github.com/galaxyproject/galaxy/pull/16086>`_
* Improved Cache Monitoring for Object Stores by `@jmchilton <https://github.com/jmchilton>`_ in `#16110 <https://github.com/galaxyproject/galaxy/pull/16110>`_
* Integrate accessibility testing into Selenium testing by `@jmchilton <https://github.com/jmchilton>`_ in `#16122 <https://github.com/galaxyproject/galaxy/pull/16122>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#16123 <https://github.com/galaxyproject/galaxy/pull/16123>`_
* Improve histories and datasets immutability checks by `@davelopez <https://github.com/davelopez>`_ in `#16143 <https://github.com/galaxyproject/galaxy/pull/16143>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#16153 <https://github.com/galaxyproject/galaxy/pull/16153>`_
* Migrate display applications API to Fast API by `@heisner-tillman <https://github.com/heisner-tillman>`_ in `#16156 <https://github.com/galaxyproject/galaxy/pull/16156>`_
* adjust grid sharing indicators by `@martenson <https://github.com/martenson>`_ in `#16163 <https://github.com/galaxyproject/galaxy/pull/16163>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#16182 <https://github.com/galaxyproject/galaxy/pull/16182>`_
* Drop workarounds for old ro-crate-py and docutils versions by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16198 <https://github.com/galaxyproject/galaxy/pull/16198>`_
* Remove various fallback behaviors by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16199 <https://github.com/galaxyproject/galaxy/pull/16199>`_
* bring grids for (published) pages on par with workflows by `@martenson <https://github.com/martenson>`_ in `#16209 <https://github.com/galaxyproject/galaxy/pull/16209>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#16227 <https://github.com/galaxyproject/galaxy/pull/16227>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#16267 <https://github.com/galaxyproject/galaxy/pull/16267>`_
* Fix tool remote test data by `@davelopez <https://github.com/davelopez>`_ in `#16311 <https://github.com/galaxyproject/galaxy/pull/16311>`_
* Hide conditionally skipped output by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16356 <https://github.com/galaxyproject/galaxy/pull/16356>`_
* Fix Storage Dashboard missing archived histories by `@davelopez <https://github.com/davelopez>`_ in `#16473 <https://github.com/galaxyproject/galaxy/pull/16473>`_
* Bump bx-python to 0.10.0 by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16484 <https://github.com/galaxyproject/galaxy/pull/16484>`_
* Drop expunge_all() call in WebTransactionRequest by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16606 <https://github.com/galaxyproject/galaxy/pull/16606>`_

=============
Other changes
=============

* Follow up on object store selection PR. by `@jmchilton <https://github.com/jmchilton>`_ in `#15654 <https://github.com/galaxyproject/galaxy/pull/15654>`_
* merge release_23.0 into dev by `@martenson <https://github.com/martenson>`_ in `#15830 <https://github.com/galaxyproject/galaxy/pull/15830>`_
* Move axe-selenium-python to dev dependencies by `@nsoranzo <https://github.com/nsoranzo>`_ in `#16162 <https://github.com/galaxyproject/galaxy/pull/16162>`_
* Bump msal version by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16285 <https://github.com/galaxyproject/galaxy/pull/16285>`_
* Fix error_reports linting by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16465 <https://github.com/galaxyproject/galaxy/pull/16465>`_

-------------------
23.0.6 (2023-10-23)
-------------------


=========
Bug fixes
=========

* 
* Fix upload paramfile handling (for real user setups) by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#16504 <https://github.com/galaxyproject/galaxy/pull/16504>`_
* Fix extra files path handling by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16541 <https://github.com/galaxyproject/galaxy/pull/16541>`_
* Make sure job_wrapper uses a consistent metadata strategy by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16569 <https://github.com/galaxyproject/galaxy/pull/16569>`_
* Fix conditional step evaluation with datasets in repeats by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16584 <https://github.com/galaxyproject/galaxy/pull/16584>`_
* Don't read request body into memory by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16585 <https://github.com/galaxyproject/galaxy/pull/16585>`_
* Fixes for extra files handling and cached object stores  by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16595 <https://github.com/galaxyproject/galaxy/pull/16595>`_
* Lazy load tool data tables in celery worker by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16640 <https://github.com/galaxyproject/galaxy/pull/16640>`_
* Force `__DUPLICATE_FILE_TO_COLLECTION__` 'size' param to integer by `@simonbray <https://github.com/simonbray>`_ in `#16659 <https://github.com/galaxyproject/galaxy/pull/16659>`_

============
Enhancements
============

* 
* Update pulsar client library to 0.15.5 by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16701 <https://github.com/galaxyproject/galaxy/pull/16701>`_

-------------------
23.0.5 (2023-07-29)
-------------------


=========
Bug fixes
=========

* 
* 
* Skip installing npm/yarn if available, fix conditional dependency parsing, create virtualenv via conda when conda active by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#16403 <https://github.com/galaxyproject/galaxy/pull/16403>`_
* Fix test discovery in vscode by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16413 <https://github.com/galaxyproject/galaxy/pull/16413>`_
* Fixes for (gitlab) error reporting by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#16424 <https://github.com/galaxyproject/galaxy/pull/16424>`_

-------------------
23.0.4 (2023-06-30)
-------------------


=========
Bug fixes
=========

* 
* 
* 
* Fix default when statement evaluation by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16332 <https://github.com/galaxyproject/galaxy/pull/16332>`_
* Redact private role name and description when purging user by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16349 <https://github.com/galaxyproject/galaxy/pull/16349>`_

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
* Bump galaxy-release-util version to 0.1.2 by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16241 <https://github.com/galaxyproject/galaxy/pull/16241>`_

============
Enhancements
============

* 
* 
* When importing tool data bundles, use the first loc file for the matching table by `@natefoo <https://github.com/natefoo>`_ in `#16247 <https://github.com/galaxyproject/galaxy/pull/16247>`_

=============
Other changes
=============

* 
* Forward port of slugify username received from oidc by `@nuwang <https://github.com/nuwang>`_ in `#16271 <https://github.com/galaxyproject/galaxy/pull/16271>`_

-------------------
23.0.2 (2023-06-13)
-------------------


=========
Bug fixes
=========

* 
* 
* 
* 
* 
* Fix ``Text File Busy`` errors at the source by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16212 <https://github.com/galaxyproject/galaxy/pull/16212>`_

============
Enhancements
============

* 
* 
* 
* 
* 
* Point release deps fixes and docs by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16214 <https://github.com/galaxyproject/galaxy/pull/16214>`_
* Use galaxy-release-util to upload python packages by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16240 <https://github.com/galaxyproject/galaxy/pull/16240>`_

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
* 
* Display DCE in job parameter component, allow rerunning with DCE input by `@mvdbeek <https://github.com/mvdbeek>`_ in `#15744 <https://github.com/galaxyproject/galaxy/pull/15744>`_
* Fix mixed outputs_to_working_directory pulsar destinations by `@mvdbeek <https://github.com/mvdbeek>`_ in `#15927 <https://github.com/galaxyproject/galaxy/pull/15927>`_
* Update Gravity to 1.0.3 by `@natefoo <https://github.com/natefoo>`_ in `#15939 <https://github.com/galaxyproject/galaxy/pull/15939>`_
* Various fixes to path prefix handling by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16033 <https://github.com/galaxyproject/galaxy/pull/16033>`_
* Fix case sensitive filtering by name in histories by `@davelopez <https://github.com/davelopez>`_ in `#16036 <https://github.com/galaxyproject/galaxy/pull/16036>`_
* Fix gcsfs test discovery by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16039 <https://github.com/galaxyproject/galaxy/pull/16039>`_
* Replace httpbin service with pytest-httpserver by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16042 <https://github.com/galaxyproject/galaxy/pull/16042>`_
* Update pulsar to 0.15.2 by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16050 <https://github.com/galaxyproject/galaxy/pull/16050>`_
* Anonymous User tool link bug fix by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#16065 <https://github.com/galaxyproject/galaxy/pull/16065>`_
* Fix BCO export by updating gxformat2 by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16081 <https://github.com/galaxyproject/galaxy/pull/16081>`_
* Fix job failure handling when condor indicates job failure by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16096 <https://github.com/galaxyproject/galaxy/pull/16096>`_
* Fix dataype_change not updating HDCA update_time by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16099 <https://github.com/galaxyproject/galaxy/pull/16099>`_
* Extract HDA for code_file validate_input hook by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16120 <https://github.com/galaxyproject/galaxy/pull/16120>`_
* Fix sort error when re-running job with DCE collection input by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16126 <https://github.com/galaxyproject/galaxy/pull/16126>`_
* Fix related-hid in bulk contents API by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16128 <https://github.com/galaxyproject/galaxy/pull/16128>`_
* Fix rank calculation for jobs waiting to be run by anonymous users by `@jdavcs <https://github.com/jdavcs>`_ in `#16137 <https://github.com/galaxyproject/galaxy/pull/16137>`_
* Tool warnings can either be None or a Dictionary but not a String by `@guerler <https://github.com/guerler>`_ in `#16183 <https://github.com/galaxyproject/galaxy/pull/16183>`_
* Pin minimum tpv version by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16201 <https://github.com/galaxyproject/galaxy/pull/16201>`_

=============
Other changes
=============

* 
* 
* 
* 
* 
* Startup fix when tool removed between reboot by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16175 <https://github.com/galaxyproject/galaxy/pull/16175>`_

-------------------
20.9.0 (2020-10-15)
-------------------

* First release from the 20.09 branch of Galaxy.

-------------------
20.5.0 (2020-07-04)
-------------------

* First release from the 20.05 branch of Galaxy.
