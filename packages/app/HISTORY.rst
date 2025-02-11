History
-------

.. to_doc

-------------------
24.2.0 (2025-02-11)
-------------------


=========
Bug fixes
=========

* Drop "Send to cloud" tool and associated cloudauthz code by `@jdavcs <https://github.com/jdavcs>`_ in `#18196 <https://github.com/galaxyproject/galaxy/pull/18196>`_
* Dynamics options add library dataset by `@gagayuan <https://github.com/gagayuan>`_ in `#18198 <https://github.com/galaxyproject/galaxy/pull/18198>`_
* Fix some deprecations by `@nsoranzo <https://github.com/nsoranzo>`_ in `#18433 <https://github.com/galaxyproject/galaxy/pull/18433>`_
* Fixes for errors reported by mypy 1.11.0 by `@nsoranzo <https://github.com/nsoranzo>`_ in `#18608 <https://github.com/galaxyproject/galaxy/pull/18608>`_
* Update mercurial by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18686 <https://github.com/galaxyproject/galaxy/pull/18686>`_
* Replace types-pkg-resources with types-setuptools by `@nsoranzo <https://github.com/nsoranzo>`_ in `#18708 <https://github.com/galaxyproject/galaxy/pull/18708>`_
* Fix tag processing in library upload by `@davelopez <https://github.com/davelopez>`_ in `#18714 <https://github.com/galaxyproject/galaxy/pull/18714>`_
* Update ruff to 0.6.1 by `@nsoranzo <https://github.com/nsoranzo>`_ in `#18716 <https://github.com/galaxyproject/galaxy/pull/18716>`_
* Fix new flake8-bugbear B039 and mypy type-var errors by `@nsoranzo <https://github.com/nsoranzo>`_ in `#18755 <https://github.com/galaxyproject/galaxy/pull/18755>`_
* Fixes and tests for data fetch models. by `@jmchilton <https://github.com/jmchilton>`_ in `#18834 <https://github.com/galaxyproject/galaxy/pull/18834>`_
* data_column params: offer same columns with and without use_header_names by `@wm75 <https://github.com/wm75>`_ in `#18879 <https://github.com/galaxyproject/galaxy/pull/18879>`_
* Fix issue with generating slug for sharing by `@arash77 <https://github.com/arash77>`_ in `#18986 <https://github.com/galaxyproject/galaxy/pull/18986>`_
* Fix the bioblend test failures by `@arash77 <https://github.com/arash77>`_ in `#18991 <https://github.com/galaxyproject/galaxy/pull/18991>`_
* Fix job directory not being cleaned up by `@davelopez <https://github.com/davelopez>`_ in `#18997 <https://github.com/galaxyproject/galaxy/pull/18997>`_
* Fixes random job failures in kubernetes  by `@mapk-amazon <https://github.com/mapk-amazon>`_ in `#19001 <https://github.com/galaxyproject/galaxy/pull/19001>`_
* Fix numerous issues with tool input format "21.01" by `@jmchilton <https://github.com/jmchilton>`_ in `#19030 <https://github.com/galaxyproject/galaxy/pull/19030>`_
* Fix test_stock.py unit test by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19037 <https://github.com/galaxyproject/galaxy/pull/19037>`_
* quota: do not complain on no-change of default by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#19045 <https://github.com/galaxyproject/galaxy/pull/19045>`_
* Normalize usernames to lowercase in OIDC authentication by `@arash77 <https://github.com/arash77>`_ in `#19131 <https://github.com/galaxyproject/galaxy/pull/19131>`_
* 2 small uv config fixes by `@nsoranzo <https://github.com/nsoranzo>`_ in `#19146 <https://github.com/galaxyproject/galaxy/pull/19146>`_
* Fix invocation metrics usability by providing job context. by `@jmchilton <https://github.com/jmchilton>`_ in `#19279 <https://github.com/galaxyproject/galaxy/pull/19279>`_
* Fix import of previously-deleted TRS workflow by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19311 <https://github.com/galaxyproject/galaxy/pull/19311>`_
* Fix quota usage with user object stores by `@davelopez <https://github.com/davelopez>`_ in `#19323 <https://github.com/galaxyproject/galaxy/pull/19323>`_
* Fix workflows with optional non-default parameter input by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19332 <https://github.com/galaxyproject/galaxy/pull/19332>`_
* Backport #19001 kubernetes api client fix by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19338 <https://github.com/galaxyproject/galaxy/pull/19338>`_
* Partial backport of #19331 by `@nsoranzo <https://github.com/nsoranzo>`_ in `#19342 <https://github.com/galaxyproject/galaxy/pull/19342>`_
* Use select_from_url test data from github, not usegalaxy.org by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19352 <https://github.com/galaxyproject/galaxy/pull/19352>`_
* Fix to only show ChatGXY when available. by `@dannon <https://github.com/dannon>`_ in `#19389 <https://github.com/galaxyproject/galaxy/pull/19389>`_
* Fix job parameter summary for inputs without label by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19427 <https://github.com/galaxyproject/galaxy/pull/19427>`_
* Show Keycloak provider label in UI by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#19447 <https://github.com/galaxyproject/galaxy/pull/19447>`_
* Expression tool format source backport by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19466 <https://github.com/galaxyproject/galaxy/pull/19466>`_
* backport of defensive refresh tokens by `@martenson <https://github.com/martenson>`_ in `#19471 <https://github.com/galaxyproject/galaxy/pull/19471>`_
* Improve relabel from file error if file doesn't contain enough lines by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19480 <https://github.com/galaxyproject/galaxy/pull/19480>`_
* Serialize message exceptions on execution error by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19483 <https://github.com/galaxyproject/galaxy/pull/19483>`_
* Fail with error message when submitting invalid request by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19489 <https://github.com/galaxyproject/galaxy/pull/19489>`_
* Fix deleting lddas in batch by `@davelopez <https://github.com/davelopez>`_ in `#19506 <https://github.com/galaxyproject/galaxy/pull/19506>`_
* Skip token refresh without refresh token in psa by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19514 <https://github.com/galaxyproject/galaxy/pull/19514>`_
* Downgrade 'InteractiveTools are not enabled' to warning by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19518 <https://github.com/galaxyproject/galaxy/pull/19518>`_
* Fix extracting workflows from purged and deleted histories by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19525 <https://github.com/galaxyproject/galaxy/pull/19525>`_
* Fix error message when subworkflow input connection missing by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19526 <https://github.com/galaxyproject/galaxy/pull/19526>`_
* Fix remap for parameter called id by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19532 <https://github.com/galaxyproject/galaxy/pull/19532>`_
* Fix admin cancel job message not being displayed to the user by `@davelopez <https://github.com/davelopez>`_ in `#19537 <https://github.com/galaxyproject/galaxy/pull/19537>`_
* Use instance wide default ``real_system_username`` if not defined on destination by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#19544 <https://github.com/galaxyproject/galaxy/pull/19544>`_
* Fix job paused on user defined object store by `@davelopez <https://github.com/davelopez>`_ in `#19578 <https://github.com/galaxyproject/galaxy/pull/19578>`_

============
Enhancements
============

* Add clean up job working directory as celery task by `@sanjaysrikakulam <https://github.com/sanjaysrikakulam>`_ in `#15816 <https://github.com/galaxyproject/galaxy/pull/15816>`_
* Experimental galactic wizard by `@dannon <https://github.com/dannon>`_ in `#15860 <https://github.com/galaxyproject/galaxy/pull/15860>`_
* Feature - stdout live reporting by `@gecage952 <https://github.com/gecage952>`_ in `#16975 <https://github.com/galaxyproject/galaxy/pull/16975>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#18226 <https://github.com/galaxyproject/galaxy/pull/18226>`_
* Allow OAuth 2.0 user defined file sources (w/Dropbox integration) by `@jmchilton <https://github.com/jmchilton>`_ in `#18272 <https://github.com/galaxyproject/galaxy/pull/18272>`_
* More data access tests, some refactoring and cleanup by `@jdavcs <https://github.com/jdavcs>`_ in `#18312 <https://github.com/galaxyproject/galaxy/pull/18312>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#18406 <https://github.com/galaxyproject/galaxy/pull/18406>`_
* Add Python 3.13 support by `@nsoranzo <https://github.com/nsoranzo>`_ in `#18449 <https://github.com/galaxyproject/galaxy/pull/18449>`_
* Add onedata templates by `@bwalkowi <https://github.com/bwalkowi>`_ in `#18457 <https://github.com/galaxyproject/galaxy/pull/18457>`_
* Support high-availability setups for the interactive tools proxy by `@kysrpex <https://github.com/kysrpex>`_ in `#18481 <https://github.com/galaxyproject/galaxy/pull/18481>`_
* Add unique constraints to the email and username fields in the galaxy_user table by `@jdavcs <https://github.com/jdavcs>`_ in `#18493 <https://github.com/galaxyproject/galaxy/pull/18493>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#18505 <https://github.com/galaxyproject/galaxy/pull/18505>`_
* Improvements for K8S deployment (especially ITs) by `@almahmoud <https://github.com/almahmoud>`_ in `#18514 <https://github.com/galaxyproject/galaxy/pull/18514>`_
* Add Tool-Centric APIs to the Tool Shed 2.0 by `@jmchilton <https://github.com/jmchilton>`_ in `#18524 <https://github.com/galaxyproject/galaxy/pull/18524>`_
* Improvements to Tool Test Parsing by `@jmchilton <https://github.com/jmchilton>`_ in `#18560 <https://github.com/galaxyproject/galaxy/pull/18560>`_
* Group tool templating exceptions in sentry by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18570 <https://github.com/galaxyproject/galaxy/pull/18570>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#18578 <https://github.com/galaxyproject/galaxy/pull/18578>`_
* Record container id and type in core job metrics by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18579 <https://github.com/galaxyproject/galaxy/pull/18579>`_
* Rev pinned gxformat2. by `@jmchilton <https://github.com/jmchilton>`_ in `#18624 <https://github.com/galaxyproject/galaxy/pull/18624>`_
* Better Typing for Tool Execution Plumbing by `@jmchilton <https://github.com/jmchilton>`_ in `#18626 <https://github.com/galaxyproject/galaxy/pull/18626>`_
* Remove unused functions in dataset managers by `@jmchilton <https://github.com/jmchilton>`_ in `#18631 <https://github.com/galaxyproject/galaxy/pull/18631>`_
* Parameter Model Improvements by `@jmchilton <https://github.com/jmchilton>`_ in `#18641 <https://github.com/galaxyproject/galaxy/pull/18641>`_
* Parse stored config details to script-based visualizations by `@guerler <https://github.com/guerler>`_ in `#18651 <https://github.com/galaxyproject/galaxy/pull/18651>`_
* Another round of parameter model improvements. by `@jmchilton <https://github.com/jmchilton>`_ in `#18673 <https://github.com/galaxyproject/galaxy/pull/18673>`_
* Allow access to invocation via shared or published history by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18707 <https://github.com/galaxyproject/galaxy/pull/18707>`_
* Allow specifying multi-select workflow parameters by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18715 <https://github.com/galaxyproject/galaxy/pull/18715>`_
* Improvements to help terms & tool help. by `@jmchilton <https://github.com/jmchilton>`_ in `#18722 <https://github.com/galaxyproject/galaxy/pull/18722>`_
* Add a retry when deleting a k8s job by `@afgane <https://github.com/afgane>`_ in `#18744 <https://github.com/galaxyproject/galaxy/pull/18744>`_
* More typing, docs, and decomposition around tool execution by `@jmchilton <https://github.com/jmchilton>`_ in `#18758 <https://github.com/galaxyproject/galaxy/pull/18758>`_
* Add Workflow Title and Annotation sections by `@hujambo-dunia <https://github.com/hujambo-dunia>`_ in `#18762 <https://github.com/galaxyproject/galaxy/pull/18762>`_
* Refactor ``LibraryDatasetsManager`` and fix type annotation issue by `@nsoranzo <https://github.com/nsoranzo>`_ in `#18773 <https://github.com/galaxyproject/galaxy/pull/18773>`_
* Backend handling of setting user-role, user-group, and group-role associations by `@jdavcs <https://github.com/jdavcs>`_ in `#18777 <https://github.com/galaxyproject/galaxy/pull/18777>`_
* Allow using tracks and groups in visualization xml by `@guerler <https://github.com/guerler>`_ in `#18779 <https://github.com/galaxyproject/galaxy/pull/18779>`_
* Workflow Landing Requests by `@jmchilton <https://github.com/jmchilton>`_ in `#18807 <https://github.com/galaxyproject/galaxy/pull/18807>`_
* Update Mypy to 1.11.2 and fix new signature override errors by `@nsoranzo <https://github.com/nsoranzo>`_ in `#18811 <https://github.com/galaxyproject/galaxy/pull/18811>`_
* Migrate Library Contents API to FastAPI by `@arash77 <https://github.com/arash77>`_ in `#18838 <https://github.com/galaxyproject/galaxy/pull/18838>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#18864 <https://github.com/galaxyproject/galaxy/pull/18864>`_
* Implement Pydantic model for workflow test format.  by `@jmchilton <https://github.com/jmchilton>`_ in `#18884 <https://github.com/galaxyproject/galaxy/pull/18884>`_
* Remove some unused dynamic drill down options. by `@jmchilton <https://github.com/jmchilton>`_ in `#18892 <https://github.com/galaxyproject/galaxy/pull/18892>`_
* Enable ``ignore-without-code`` mypy error code by `@nsoranzo <https://github.com/nsoranzo>`_ in `#18898 <https://github.com/galaxyproject/galaxy/pull/18898>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#18904 <https://github.com/galaxyproject/galaxy/pull/18904>`_
* Type annotations and fixes by `@nsoranzo <https://github.com/nsoranzo>`_ in `#18911 <https://github.com/galaxyproject/galaxy/pull/18911>`_
* Add filter null collection operation tool by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18928 <https://github.com/galaxyproject/galaxy/pull/18928>`_
* Remove outdated fimo wrapper and galaxy-sequence-utils dependency by `@nsoranzo <https://github.com/nsoranzo>`_ in `#18937 <https://github.com/galaxyproject/galaxy/pull/18937>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#18943 <https://github.com/galaxyproject/galaxy/pull/18943>`_
* Allow to overwrite `real_system_username` per destination by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#18945 <https://github.com/galaxyproject/galaxy/pull/18945>`_
* Assert that `data_column` parameters have a valid `data_ref` by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#18949 <https://github.com/galaxyproject/galaxy/pull/18949>`_
* Decouple user email from role name by `@jdavcs <https://github.com/jdavcs>`_ in `#18966 <https://github.com/galaxyproject/galaxy/pull/18966>`_
* Workflow landing improvements by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18979 <https://github.com/galaxyproject/galaxy/pull/18979>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#18982 <https://github.com/galaxyproject/galaxy/pull/18982>`_
* Allow recovering a normalized version of workflow request state from API by `@jmchilton <https://github.com/jmchilton>`_ in `#18985 <https://github.com/galaxyproject/galaxy/pull/18985>`_
* Enhance relabel_from_file to work with any column pair in mapping file by `@wm75 <https://github.com/wm75>`_ in `#19022 <https://github.com/galaxyproject/galaxy/pull/19022>`_
* A variety of improvements around tool parameter modeling (second try) by `@jmchilton <https://github.com/jmchilton>`_ in `#19027 <https://github.com/galaxyproject/galaxy/pull/19027>`_
* Better logging around tool loading by `@jmchilton <https://github.com/jmchilton>`_ in `#19029 <https://github.com/galaxyproject/galaxy/pull/19029>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#19031 <https://github.com/galaxyproject/galaxy/pull/19031>`_
* Silence the quota manager for updates by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#19046 <https://github.com/galaxyproject/galaxy/pull/19046>`_
* Add job metrics per invocation by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19048 <https://github.com/galaxyproject/galaxy/pull/19048>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#19062 <https://github.com/galaxyproject/galaxy/pull/19062>`_
* Annotate ``DatasetAssociationManager`` as generic type by `@nsoranzo <https://github.com/nsoranzo>`_ in `#19063 <https://github.com/galaxyproject/galaxy/pull/19063>`_
* Move TRS import into WorkflowContentManager by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19070 <https://github.com/galaxyproject/galaxy/pull/19070>`_
* Replace poetry with uv by `@nsoranzo <https://github.com/nsoranzo>`_ in `#19075 <https://github.com/galaxyproject/galaxy/pull/19075>`_
* Allow deferred datasets to behave as URIs by `@davelopez <https://github.com/davelopez>`_ in `#19077 <https://github.com/galaxyproject/galaxy/pull/19077>`_
* Implement workflow parameter validators. by `@jmchilton <https://github.com/jmchilton>`_ in `#19092 <https://github.com/galaxyproject/galaxy/pull/19092>`_
* Allow directory_uri workflow parameters.  by `@jmchilton <https://github.com/jmchilton>`_ in `#19093 <https://github.com/galaxyproject/galaxy/pull/19093>`_
* Better cleanup of sharing roles on user purge by `@jdavcs <https://github.com/jdavcs>`_ in `#19096 <https://github.com/galaxyproject/galaxy/pull/19096>`_
* Support deferred datasets in visualizations by `@davelopez <https://github.com/davelopez>`_ in `#19097 <https://github.com/galaxyproject/galaxy/pull/19097>`_
* uv: Do not recalculate dependencies when exporting by `@nsoranzo <https://github.com/nsoranzo>`_ in `#19099 <https://github.com/galaxyproject/galaxy/pull/19099>`_
* Access public history in job cache / job search by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19108 <https://github.com/galaxyproject/galaxy/pull/19108>`_
* Test hash validation also for upload by path by `@nsoranzo <https://github.com/nsoranzo>`_ in `#19109 <https://github.com/galaxyproject/galaxy/pull/19109>`_
* Always validate hashes when provided by `@nsoranzo <https://github.com/nsoranzo>`_ in `#19110 <https://github.com/galaxyproject/galaxy/pull/19110>`_
* Add type annotations to ``JobRunnerMapper`` and related code by `@nsoranzo <https://github.com/nsoranzo>`_ in `#19115 <https://github.com/galaxyproject/galaxy/pull/19115>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#19123 <https://github.com/galaxyproject/galaxy/pull/19123>`_
* Allow a posix file source to prefer linking. by `@jmchilton <https://github.com/jmchilton>`_ in `#19132 <https://github.com/galaxyproject/galaxy/pull/19132>`_
* Remove OpenLayers legacy files and add SVG logo by `@guerler <https://github.com/guerler>`_ in `#19135 <https://github.com/galaxyproject/galaxy/pull/19135>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#19149 <https://github.com/galaxyproject/galaxy/pull/19149>`_
* Fix default value handling for parameters connected to required parameters by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19219 <https://github.com/galaxyproject/galaxy/pull/19219>`_
* Workflow Inputs Activity by `@ElectronicBlueberry <https://github.com/ElectronicBlueberry>`_ in `#19252 <https://github.com/galaxyproject/galaxy/pull/19252>`_

=============
Other changes
=============

* Fix workflow invocation accessibility check by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18746 <https://github.com/galaxyproject/galaxy/pull/18746>`_
* Fix destentation typo by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19140 <https://github.com/galaxyproject/galaxy/pull/19140>`_

-------------------
24.1.4 (2024-12-11)
-------------------


=========
Bug fixes
=========

* Replace busybox:ubuntu-14.04 image with busybox:1.36.1-glibc by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18428 <https://github.com/galaxyproject/galaxy/pull/18428>`_
* Update mercurial to non-yanked 6.7.4 by `@nsoranzo <https://github.com/nsoranzo>`_ in `#18434 <https://github.com/galaxyproject/galaxy/pull/18434>`_
* Fix dropped when_expression on step upgrade by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18446 <https://github.com/galaxyproject/galaxy/pull/18446>`_
* Improve workflow-related exception reporting by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18447 <https://github.com/galaxyproject/galaxy/pull/18447>`_
* Fix subwofklow tags serialization type by `@arash77 <https://github.com/arash77>`_ in `#18456 <https://github.com/galaxyproject/galaxy/pull/18456>`_
* by `@laperlej <https://github.com/laperlej>`_ in `#18459 <https://github.com/galaxyproject/galaxy/pull/18459>`_
* Add input extra files to `get_input_fnames` by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18462 <https://github.com/galaxyproject/galaxy/pull/18462>`_
* Return generic message for password reset email by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#18479 <https://github.com/galaxyproject/galaxy/pull/18479>`_
* Increase API robustness to invalid requests, improve compressed data serving by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18494 <https://github.com/galaxyproject/galaxy/pull/18494>`_
* Don't call job_runner.stop_job on jobs in new state by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18495 <https://github.com/galaxyproject/galaxy/pull/18495>`_
* Prevent job submission if input collection element is deleted by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18517 <https://github.com/galaxyproject/galaxy/pull/18517>`_
* Strip unicode null from tool stdio by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18527 <https://github.com/galaxyproject/galaxy/pull/18527>`_
* Fix map over calculation for runtime inputs  by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18535 <https://github.com/galaxyproject/galaxy/pull/18535>`_
* Fix for not-null in 'column_list' object by `@hujambo-dunia <https://github.com/hujambo-dunia>`_ in `#18553 <https://github.com/galaxyproject/galaxy/pull/18553>`_
* Also fail ``ensure_dataset_on_disk`` if dataset is in new state by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18559 <https://github.com/galaxyproject/galaxy/pull/18559>`_
* Fix sqlalchemy statement in tooltagmanager reset output by `@dannon <https://github.com/dannon>`_ in `#18591 <https://github.com/galaxyproject/galaxy/pull/18591>`_
* Set minimum weasyprint version by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18606 <https://github.com/galaxyproject/galaxy/pull/18606>`_
* Improve relabel identifiers message when number of columns is not 2 by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18634 <https://github.com/galaxyproject/galaxy/pull/18634>`_
* Fix extract workflow from history when implicit collection has no jobs by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18661 <https://github.com/galaxyproject/galaxy/pull/18661>`_
* Make sure we set file size also for purged outputs by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18681 <https://github.com/galaxyproject/galaxy/pull/18681>`_
* File source and object store instance api fixes by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18685 <https://github.com/galaxyproject/galaxy/pull/18685>`_
* Fix change datatype PJA on expression tool data outputs by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18691 <https://github.com/galaxyproject/galaxy/pull/18691>`_
* Fill in missing help for cross product tools. by `@jmchilton <https://github.com/jmchilton>`_ in `#18698 <https://github.com/galaxyproject/galaxy/pull/18698>`_
* Fix subworkflow scheduling for delayed subworkflow steps connected to data inputs by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18731 <https://github.com/galaxyproject/galaxy/pull/18731>`_
* Catch and display exceptions when importing malformatted yaml workflows by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18734 <https://github.com/galaxyproject/galaxy/pull/18734>`_
* Fix infinitely delayed workflow scheduling if skipped step creates HDCA by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18751 <https://github.com/galaxyproject/galaxy/pull/18751>`_
* Fix directory get or create logic by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18752 <https://github.com/galaxyproject/galaxy/pull/18752>`_
* Fix job summary for optional unset job data inputs by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18754 <https://github.com/galaxyproject/galaxy/pull/18754>`_
* Allow to change only the description of a quota by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#18775 <https://github.com/galaxyproject/galaxy/pull/18775>`_
* Fix wrong extension on pick data output by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18798 <https://github.com/galaxyproject/galaxy/pull/18798>`_
* Fix unspecified ``oidc_endpoint`` variable overwriting specified ``redirect_url`` by `@bgruening <https://github.com/bgruening>`_ in `#18818 <https://github.com/galaxyproject/galaxy/pull/18818>`_
* Fix wrong celery_app config on job and workflow handlers by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18819 <https://github.com/galaxyproject/galaxy/pull/18819>`_
* Fix ``named cursor is not valid anymore`` by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18825 <https://github.com/galaxyproject/galaxy/pull/18825>`_
* Tighten TRS url check by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18841 <https://github.com/galaxyproject/galaxy/pull/18841>`_
* Fix Workflow index bookmark filter by `@itisAliRH <https://github.com/itisAliRH>`_ in `#18842 <https://github.com/galaxyproject/galaxy/pull/18842>`_
* Skip metric collection if job working directory doesn't exist by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18845 <https://github.com/galaxyproject/galaxy/pull/18845>`_
* Extend on disk checks to running, queued and error states by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18846 <https://github.com/galaxyproject/galaxy/pull/18846>`_
* Raise MessageException instead of assertions on rerun problems by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18858 <https://github.com/galaxyproject/galaxy/pull/18858>`_
* Fix data_column ref to nested collection by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18875 <https://github.com/galaxyproject/galaxy/pull/18875>`_
* Fix loading very old workflows with data inputs by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18876 <https://github.com/galaxyproject/galaxy/pull/18876>`_
* Access tool data table filters in workflow building mode by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18900 <https://github.com/galaxyproject/galaxy/pull/18900>`_
* Fix username used in invocation report by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18932 <https://github.com/galaxyproject/galaxy/pull/18932>`_
* Disable locking when opening h5 files, add missing ``with`` by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18976 <https://github.com/galaxyproject/galaxy/pull/18976>`_
* Fix job search statement building by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19010 <https://github.com/galaxyproject/galaxy/pull/19010>`_
* Put cached jobs back into queue on handler restart by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19012 <https://github.com/galaxyproject/galaxy/pull/19012>`_
* Fix various invocation export issues by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19215 <https://github.com/galaxyproject/galaxy/pull/19215>`_
* Create harmonized collections from correct tool outputs by `@wm75 <https://github.com/wm75>`_ in `#19222 <https://github.com/galaxyproject/galaxy/pull/19222>`_

============
Enhancements
============

* Include workflow invocation id in exception logs by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18594 <https://github.com/galaxyproject/galaxy/pull/18594>`_
* Implemented the generic OIDC backend from python-social-auth into Gal… by `@Edmontosaurus <https://github.com/Edmontosaurus>`_ in `#18670 <https://github.com/galaxyproject/galaxy/pull/18670>`_
* Collect job metrics also when job failed by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18809 <https://github.com/galaxyproject/galaxy/pull/18809>`_
* prevent "missing refresh_token" errors by supporting <extra_scopes> also with Keycloak backend by `@ljocha <https://github.com/ljocha>`_ in `#18826 <https://github.com/galaxyproject/galaxy/pull/18826>`_

-------------------
24.1.3 (2024-10-25)
-------------------


=========
Bug fixes
=========

* Replace busybox:ubuntu-14.04 image with busybox:1.36.1-glibc by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18428 <https://github.com/galaxyproject/galaxy/pull/18428>`_
* Update mercurial to non-yanked 6.7.4 by `@nsoranzo <https://github.com/nsoranzo>`_ in `#18434 <https://github.com/galaxyproject/galaxy/pull/18434>`_
* Fix dropped when_expression on step upgrade by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18446 <https://github.com/galaxyproject/galaxy/pull/18446>`_
* Improve workflow-related exception reporting by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18447 <https://github.com/galaxyproject/galaxy/pull/18447>`_
* Fix subwofklow tags serialization type by `@arash77 <https://github.com/arash77>`_ in `#18456 <https://github.com/galaxyproject/galaxy/pull/18456>`_
* by `@laperlej <https://github.com/laperlej>`_ in `#18459 <https://github.com/galaxyproject/galaxy/pull/18459>`_
* Add input extra files to `get_input_fnames` by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18462 <https://github.com/galaxyproject/galaxy/pull/18462>`_
* Return generic message for password reset email by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#18479 <https://github.com/galaxyproject/galaxy/pull/18479>`_
* Increase API robustness to invalid requests, improve compressed data serving by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18494 <https://github.com/galaxyproject/galaxy/pull/18494>`_
* Prevent job submission if input collection element is deleted by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18517 <https://github.com/galaxyproject/galaxy/pull/18517>`_
* Strip unicode null from tool stdio by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18527 <https://github.com/galaxyproject/galaxy/pull/18527>`_
* Fix map over calculation for runtime inputs  by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18535 <https://github.com/galaxyproject/galaxy/pull/18535>`_
* Fix for not-null in 'column_list' object by `@hujambo-dunia <https://github.com/hujambo-dunia>`_ in `#18553 <https://github.com/galaxyproject/galaxy/pull/18553>`_
* Also fail ``ensure_dataset_on_disk`` if dataset is in new state by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18559 <https://github.com/galaxyproject/galaxy/pull/18559>`_
* Fix sqlalchemy statement in tooltagmanager reset output by `@dannon <https://github.com/dannon>`_ in `#18591 <https://github.com/galaxyproject/galaxy/pull/18591>`_
* Set minimum weasyprint version by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18606 <https://github.com/galaxyproject/galaxy/pull/18606>`_
* Improve relabel identifiers message when number of columns is not 2 by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18634 <https://github.com/galaxyproject/galaxy/pull/18634>`_
* Fix extract workflow from history when implicit collection has no jobs by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18661 <https://github.com/galaxyproject/galaxy/pull/18661>`_
* Make sure we set file size also for purged outputs by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18681 <https://github.com/galaxyproject/galaxy/pull/18681>`_
* File source and object store instance api fixes by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18685 <https://github.com/galaxyproject/galaxy/pull/18685>`_
* Fix change datatype PJA on expression tool data outputs by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18691 <https://github.com/galaxyproject/galaxy/pull/18691>`_
* Fill in missing help for cross product tools. by `@jmchilton <https://github.com/jmchilton>`_ in `#18698 <https://github.com/galaxyproject/galaxy/pull/18698>`_
* Fix subworkflow scheduling for delayed subworkflow steps connected to data inputs by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18731 <https://github.com/galaxyproject/galaxy/pull/18731>`_
* Catch and display exceptions when importing malformatted yaml workflows by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18734 <https://github.com/galaxyproject/galaxy/pull/18734>`_
* Fix infinitely delayed workflow scheduling if skipped step creates HDCA by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18751 <https://github.com/galaxyproject/galaxy/pull/18751>`_
* Fix directory get or create logic by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18752 <https://github.com/galaxyproject/galaxy/pull/18752>`_
* Fix job summary for optional unset job data inputs by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18754 <https://github.com/galaxyproject/galaxy/pull/18754>`_
* Allow to change only the description of a quota by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#18775 <https://github.com/galaxyproject/galaxy/pull/18775>`_
* Fix wrong extension on pick data output by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18798 <https://github.com/galaxyproject/galaxy/pull/18798>`_
* Fix unspecified ``oidc_endpoint`` variable overwriting specified ``redirect_url`` by `@bgruening <https://github.com/bgruening>`_ in `#18818 <https://github.com/galaxyproject/galaxy/pull/18818>`_
* Fix wrong celery_app config on job and workflow handlers by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18819 <https://github.com/galaxyproject/galaxy/pull/18819>`_
* Fix ``named cursor is not valid anymore`` by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18825 <https://github.com/galaxyproject/galaxy/pull/18825>`_
* Tighten TRS url check by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18841 <https://github.com/galaxyproject/galaxy/pull/18841>`_
* Fix Workflow index bookmark filter by `@itisAliRH <https://github.com/itisAliRH>`_ in `#18842 <https://github.com/galaxyproject/galaxy/pull/18842>`_
* Skip metric collection if job working directory doesn't exist by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18845 <https://github.com/galaxyproject/galaxy/pull/18845>`_
* Extend on disk checks to running, queued and error states by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18846 <https://github.com/galaxyproject/galaxy/pull/18846>`_
* Raise MessageException instead of assertions on rerun problems by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18858 <https://github.com/galaxyproject/galaxy/pull/18858>`_
* Fix data_column ref to nested collection by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18875 <https://github.com/galaxyproject/galaxy/pull/18875>`_
* Fix loading very old workflows with data inputs by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18876 <https://github.com/galaxyproject/galaxy/pull/18876>`_
* Access tool data table filters in workflow building mode by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18900 <https://github.com/galaxyproject/galaxy/pull/18900>`_
* Fix username used in invocation report by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18932 <https://github.com/galaxyproject/galaxy/pull/18932>`_
* Disable locking when opening h5 files, add missing ``with`` by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18976 <https://github.com/galaxyproject/galaxy/pull/18976>`_
* Fix job search statement building by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19010 <https://github.com/galaxyproject/galaxy/pull/19010>`_
* Put cached jobs back into queue on handler restart by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19012 <https://github.com/galaxyproject/galaxy/pull/19012>`_

============
Enhancements
============

* Include workflow invocation id in exception logs by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18594 <https://github.com/galaxyproject/galaxy/pull/18594>`_
* Implemented the generic OIDC backend from python-social-auth into Gal… by `@Edmontosaurus <https://github.com/Edmontosaurus>`_ in `#18670 <https://github.com/galaxyproject/galaxy/pull/18670>`_
* Collect job metrics also when job failed by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18809 <https://github.com/galaxyproject/galaxy/pull/18809>`_
* prevent "missing refresh_token" errors by supporting <extra_scopes> also with Keycloak backend by `@ljocha <https://github.com/ljocha>`_ in `#18826 <https://github.com/galaxyproject/galaxy/pull/18826>`_

-------------------
24.1.2 (2024-09-25)
-------------------


=========
Bug fixes
=========

* Return generic message for password reset email by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#18479 <https://github.com/galaxyproject/galaxy/pull/18479>`_
* Increase API robustness to invalid requests, improve compressed data serving by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18494 <https://github.com/galaxyproject/galaxy/pull/18494>`_
* Prevent job submission if input collection element is deleted by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18517 <https://github.com/galaxyproject/galaxy/pull/18517>`_
* Strip unicode null from tool stdio by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18527 <https://github.com/galaxyproject/galaxy/pull/18527>`_
* Fix map over calculation for runtime inputs  by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18535 <https://github.com/galaxyproject/galaxy/pull/18535>`_
* Fix for not-null in 'column_list' object by `@hujambo-dunia <https://github.com/hujambo-dunia>`_ in `#18553 <https://github.com/galaxyproject/galaxy/pull/18553>`_
* Also fail ``ensure_dataset_on_disk`` if dataset is in new state by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18559 <https://github.com/galaxyproject/galaxy/pull/18559>`_
* Fix sqlalchemy statement in tooltagmanager reset output by `@dannon <https://github.com/dannon>`_ in `#18591 <https://github.com/galaxyproject/galaxy/pull/18591>`_
* Set minimum weasyprint version by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18606 <https://github.com/galaxyproject/galaxy/pull/18606>`_
* Improve relabel identifiers message when number of columns is not 2 by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18634 <https://github.com/galaxyproject/galaxy/pull/18634>`_
* Fix extract workflow from history when implicit collection has no jobs by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18661 <https://github.com/galaxyproject/galaxy/pull/18661>`_
* Make sure we set file size also for purged outputs by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18681 <https://github.com/galaxyproject/galaxy/pull/18681>`_
* File source and object store instance api fixes by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18685 <https://github.com/galaxyproject/galaxy/pull/18685>`_
* Fix change datatype PJA on expression tool data outputs by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18691 <https://github.com/galaxyproject/galaxy/pull/18691>`_
* Fill in missing help for cross product tools. by `@jmchilton <https://github.com/jmchilton>`_ in `#18698 <https://github.com/galaxyproject/galaxy/pull/18698>`_
* Fix subworkflow scheduling for delayed subworkflow steps connected to data inputs by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18731 <https://github.com/galaxyproject/galaxy/pull/18731>`_
* Catch and display exceptions when importing malformatted yaml workflows by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18734 <https://github.com/galaxyproject/galaxy/pull/18734>`_
* Fix infinitely delayed workflow scheduling if skipped step creates HDCA by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18751 <https://github.com/galaxyproject/galaxy/pull/18751>`_
* Fix directory get or create logic by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18752 <https://github.com/galaxyproject/galaxy/pull/18752>`_
* Fix job summary for optional unset job data inputs by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18754 <https://github.com/galaxyproject/galaxy/pull/18754>`_
* Allow to change only the description of a quota by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#18775 <https://github.com/galaxyproject/galaxy/pull/18775>`_
* Fix wrong extension on pick data output by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18798 <https://github.com/galaxyproject/galaxy/pull/18798>`_
* Fix unspecified ``oidc_endpoint`` variable overwriting specified ``redirect_url`` by `@bgruening <https://github.com/bgruening>`_ in `#18818 <https://github.com/galaxyproject/galaxy/pull/18818>`_
* Fix wrong celery_app config on job and workflow handlers by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18819 <https://github.com/galaxyproject/galaxy/pull/18819>`_
* Fix ``named cursor is not valid anymore`` by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18825 <https://github.com/galaxyproject/galaxy/pull/18825>`_
* Tighten TRS url check by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18841 <https://github.com/galaxyproject/galaxy/pull/18841>`_
* Fix Workflow index bookmark filter by `@itisAliRH <https://github.com/itisAliRH>`_ in `#18842 <https://github.com/galaxyproject/galaxy/pull/18842>`_
* Skip metric collection if job working directory doesn't exist by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18845 <https://github.com/galaxyproject/galaxy/pull/18845>`_
* Extend on disk checks to running, queued and error states by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18846 <https://github.com/galaxyproject/galaxy/pull/18846>`_
* Raise MessageException instead of assertions on rerun problems by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18858 <https://github.com/galaxyproject/galaxy/pull/18858>`_
* Fix data_column ref to nested collection by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18875 <https://github.com/galaxyproject/galaxy/pull/18875>`_
* Fix loading very old workflows with data inputs by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18876 <https://github.com/galaxyproject/galaxy/pull/18876>`_

============
Enhancements
============

* Include workflow invocation id in exception logs by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18594 <https://github.com/galaxyproject/galaxy/pull/18594>`_
* Implemented the generic OIDC backend from python-social-auth into Gal… by `@Edmontosaurus <https://github.com/Edmontosaurus>`_ in `#18670 <https://github.com/galaxyproject/galaxy/pull/18670>`_
* Collect job metrics also when job failed by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18809 <https://github.com/galaxyproject/galaxy/pull/18809>`_
* prevent "missing refresh_token" errors by supporting <extra_scopes> also with Keycloak backend by `@ljocha <https://github.com/ljocha>`_ in `#18826 <https://github.com/galaxyproject/galaxy/pull/18826>`_

-------------------
24.1.1 (2024-07-02)
-------------------


=========
Bug fixes
=========

* Unpin social-auth-core dependency by `@nsoranzo <https://github.com/nsoranzo>`_ in `#17607 <https://github.com/galaxyproject/galaxy/pull/17607>`_
* Dynamic tool fixes by `@dcore94 <https://github.com/dcore94>`_ in `#18085 <https://github.com/galaxyproject/galaxy/pull/18085>`_
* Fix for unexpected OIDC XML validation error by `@Edmontosaurus <https://github.com/Edmontosaurus>`_ in `#18106 <https://github.com/galaxyproject/galaxy/pull/18106>`_
* Revert some requests import changes by `@nsoranzo <https://github.com/nsoranzo>`_ in `#18199 <https://github.com/galaxyproject/galaxy/pull/18199>`_
* Small bug fixes for user data plugins by `@jmchilton <https://github.com/jmchilton>`_ in `#18246 <https://github.com/galaxyproject/galaxy/pull/18246>`_
* Fix handler: access to result row items changed in SA2.0 by `@jdavcs <https://github.com/jdavcs>`_ in `#18274 <https://github.com/galaxyproject/galaxy/pull/18274>`_
* Fix various packages' issues by `@nsoranzo <https://github.com/nsoranzo>`_ in `#18301 <https://github.com/galaxyproject/galaxy/pull/18301>`_
* Adapt Tool prediction API to Transformer-based deep learning architecture by `@anuprulez <https://github.com/anuprulez>`_ in `#18305 <https://github.com/galaxyproject/galaxy/pull/18305>`_
* Fix empty usernames in database + bug in username generation by `@jdavcs <https://github.com/jdavcs>`_ in `#18379 <https://github.com/galaxyproject/galaxy/pull/18379>`_
* Add TypedDict for JobsSummary by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18418 <https://github.com/galaxyproject/galaxy/pull/18418>`_
* Pin pydantic to >=2.7.4 by `@nsoranzo <https://github.com/nsoranzo>`_ in `#18423 <https://github.com/galaxyproject/galaxy/pull/18423>`_
* Update mercurial to non-yanked 6.7.4 by `@nsoranzo <https://github.com/nsoranzo>`_ in `#18434 <https://github.com/galaxyproject/galaxy/pull/18434>`_
* Fix dropped when_expression on step upgrade by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18446 <https://github.com/galaxyproject/galaxy/pull/18446>`_
* Improve workflow-related exception reporting by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18447 <https://github.com/galaxyproject/galaxy/pull/18447>`_
* Fix subwofklow tags serialization type by `@arash77 <https://github.com/arash77>`_ in `#18456 <https://github.com/galaxyproject/galaxy/pull/18456>`_
* Disable password reset for deleted users [GCC2024_COFEST]  by `@laperlej <https://github.com/laperlej>`_ in `#18459 <https://github.com/galaxyproject/galaxy/pull/18459>`_
* Add input extra files to `get_input_fnames` by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18462 <https://github.com/galaxyproject/galaxy/pull/18462>`_

============
Enhancements
============

* Only include tool stdout/stderr in HDA info by `@natefoo <https://github.com/natefoo>`_ in `#16730 <https://github.com/galaxyproject/galaxy/pull/16730>`_
* Adding object store plugin for Rucio by `@SergeyYakubov <https://github.com/SergeyYakubov>`_ in `#17156 <https://github.com/galaxyproject/galaxy/pull/17156>`_
* Enable all-vs-all collection analysis patterns. by `@jmchilton <https://github.com/jmchilton>`_ in `#17366 <https://github.com/galaxyproject/galaxy/pull/17366>`_
* Add onedata objectstore by `@bwalkowi <https://github.com/bwalkowi>`_ in `#17540 <https://github.com/galaxyproject/galaxy/pull/17540>`_
* Type annotation improvements by `@nsoranzo <https://github.com/nsoranzo>`_ in `#17601 <https://github.com/galaxyproject/galaxy/pull/17601>`_
* Type annotation and CWL-related improvements by `@nsoranzo <https://github.com/nsoranzo>`_ in `#17630 <https://github.com/galaxyproject/galaxy/pull/17630>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#17653 <https://github.com/galaxyproject/galaxy/pull/17653>`_
* Code cleanups from ruff and pyupgrade by `@nsoranzo <https://github.com/nsoranzo>`_ in `#17654 <https://github.com/galaxyproject/galaxy/pull/17654>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#17764 <https://github.com/galaxyproject/galaxy/pull/17764>`_
* SQLAlchemy 2.0 by `@jdavcs <https://github.com/jdavcs>`_ in `#17778 <https://github.com/galaxyproject/galaxy/pull/17778>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#17819 <https://github.com/galaxyproject/galaxy/pull/17819>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#17870 <https://github.com/galaxyproject/galaxy/pull/17870>`_
* Add `email` notifications channel by `@davelopez <https://github.com/davelopez>`_ in `#17914 <https://github.com/galaxyproject/galaxy/pull/17914>`_
* Model edits and bug fixes by `@jdavcs <https://github.com/jdavcs>`_ in `#17922 <https://github.com/galaxyproject/galaxy/pull/17922>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#17923 <https://github.com/galaxyproject/galaxy/pull/17923>`_
* Model typing and SA2.0 follow-up by `@jdavcs <https://github.com/jdavcs>`_ in `#17958 <https://github.com/galaxyproject/galaxy/pull/17958>`_
* Error reporting unit tests by `@jmchilton <https://github.com/jmchilton>`_ in `#17968 <https://github.com/galaxyproject/galaxy/pull/17968>`_
* Make urgent notifications mandatory by `@davelopez <https://github.com/davelopez>`_ in `#17975 <https://github.com/galaxyproject/galaxy/pull/17975>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#17982 <https://github.com/galaxyproject/galaxy/pull/17982>`_
* Enable ``warn_unused_ignores`` mypy option by `@nsoranzo <https://github.com/nsoranzo>`_ in `#17991 <https://github.com/galaxyproject/galaxy/pull/17991>`_
* Add galaxy to user agent by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18003 <https://github.com/galaxyproject/galaxy/pull/18003>`_
* Add Zenodo integration by `@davelopez <https://github.com/davelopez>`_ in `#18022 <https://github.com/galaxyproject/galaxy/pull/18022>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#18035 <https://github.com/galaxyproject/galaxy/pull/18035>`_
* Add stronger type annotations in file sources + refactoring by `@davelopez <https://github.com/davelopez>`_ in `#18050 <https://github.com/galaxyproject/galaxy/pull/18050>`_
* Add pagination support to Files Source plugins by `@davelopez <https://github.com/davelopez>`_ in `#18059 <https://github.com/galaxyproject/galaxy/pull/18059>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#18063 <https://github.com/galaxyproject/galaxy/pull/18063>`_
* Enable flake8-implicit-str-concat ruff rules by `@nsoranzo <https://github.com/nsoranzo>`_ in `#18067 <https://github.com/galaxyproject/galaxy/pull/18067>`_
* Ensure history `update_time` is set when exporting by `@davelopez <https://github.com/davelopez>`_ in `#18086 <https://github.com/galaxyproject/galaxy/pull/18086>`_
* Overhaul Azure storage infrastructure. by `@jmchilton <https://github.com/jmchilton>`_ in `#18087 <https://github.com/galaxyproject/galaxy/pull/18087>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#18095 <https://github.com/galaxyproject/galaxy/pull/18095>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#18125 <https://github.com/galaxyproject/galaxy/pull/18125>`_
* Revises handling of warnings in the workflow run form by `@guerler <https://github.com/guerler>`_ in `#18126 <https://github.com/galaxyproject/galaxy/pull/18126>`_
* Empower users to bring their own storage and file sources by `@jmchilton <https://github.com/jmchilton>`_ in `#18127 <https://github.com/galaxyproject/galaxy/pull/18127>`_
* Update s3fs dependency. by `@jmchilton <https://github.com/jmchilton>`_ in `#18135 <https://github.com/galaxyproject/galaxy/pull/18135>`_
* More unit testing for object store stuff. by `@jmchilton <https://github.com/jmchilton>`_ in `#18136 <https://github.com/galaxyproject/galaxy/pull/18136>`_
* Harden User Object Store and File Source Creation by `@jmchilton <https://github.com/jmchilton>`_ in `#18172 <https://github.com/galaxyproject/galaxy/pull/18172>`_
* Fix boto3-stubs typecheck dependency by `@nsoranzo <https://github.com/nsoranzo>`_ in `#18173 <https://github.com/galaxyproject/galaxy/pull/18173>`_
* More structured indexing for user data objects. by `@jmchilton <https://github.com/jmchilton>`_ in `#18291 <https://github.com/galaxyproject/galaxy/pull/18291>`_
* Onedada object store and files source stability fixes by `@bwalkowi <https://github.com/bwalkowi>`_ in `#18372 <https://github.com/galaxyproject/galaxy/pull/18372>`_
* Allow running and editing workflows for specific versions by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#18378 <https://github.com/galaxyproject/galaxy/pull/18378>`_

=============
Other changes
=============

* Chore: remove repetitive words by `@tianzedavid <https://github.com/tianzedavid>`_ in `#18076 <https://github.com/galaxyproject/galaxy/pull/18076>`_
* Fix #18316 (anonymous file sources) by `@jmchilton <https://github.com/jmchilton>`_ in `#18352 <https://github.com/galaxyproject/galaxy/pull/18352>`_
* Merge 24.0 into 24.1 by `@jdavcs <https://github.com/jdavcs>`_ in `#18353 <https://github.com/galaxyproject/galaxy/pull/18353>`_
* Merge 24.0 into 24.1 by `@jdavcs <https://github.com/jdavcs>`_ in `#18365 <https://github.com/galaxyproject/galaxy/pull/18365>`_

-------------------
24.0.3 (2024-06-28)
-------------------


=========
Bug fixes
=========

* Raise exception if collection elements missing during download by `@jdavcs <https://github.com/jdavcs>`_ in `#18094 <https://github.com/galaxyproject/galaxy/pull/18094>`_
* Allow purge query param, deprecate purge body param by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18105 <https://github.com/galaxyproject/galaxy/pull/18105>`_
* Backport OIDC schema fix by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18111 <https://github.com/galaxyproject/galaxy/pull/18111>`_
* Don't log exception if cancelled slurm job doesn't have stderr file by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18121 <https://github.com/galaxyproject/galaxy/pull/18121>`_
* Downgrade missing output file in working directory to warning for failed jobs by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18123 <https://github.com/galaxyproject/galaxy/pull/18123>`_
* Fix data default values not getting added to history by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18132 <https://github.com/galaxyproject/galaxy/pull/18132>`_
* Drop redundant error message by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18156 <https://github.com/galaxyproject/galaxy/pull/18156>`_
* Emit warning when user-cancelled job already complete by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18178 <https://github.com/galaxyproject/galaxy/pull/18178>`_
* Avoid object store path lookup when constructing JobState object by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18190 <https://github.com/galaxyproject/galaxy/pull/18190>`_
* Add string cast for dbkey / genome_build by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18207 <https://github.com/galaxyproject/galaxy/pull/18207>`_
* Check dataset state when attempting to acces dataset contents by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18214 <https://github.com/galaxyproject/galaxy/pull/18214>`_
* Don't set dataset peek for errored jobs by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18231 <https://github.com/galaxyproject/galaxy/pull/18231>`_
* Raise exception when extracting dataset from collection without datasets by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18249 <https://github.com/galaxyproject/galaxy/pull/18249>`_
* Skip tests if toolshed, dx.doi not responding by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18250 <https://github.com/galaxyproject/galaxy/pull/18250>`_
* Don't attempt to download purged datasets by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18278 <https://github.com/galaxyproject/galaxy/pull/18278>`_
* Check various preconditions in FeatureLocationIndexDataProvider by `@davelopez <https://github.com/davelopez>`_ in `#18283 <https://github.com/galaxyproject/galaxy/pull/18283>`_
* Don't serialize display application links for deleted datasets by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18307 <https://github.com/galaxyproject/galaxy/pull/18307>`_
* Downgrade doi fetch error to debug by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18330 <https://github.com/galaxyproject/galaxy/pull/18330>`_
* Fix authentication error for anonymous users querying jobs by `@davelopez <https://github.com/davelopez>`_ in `#18333 <https://github.com/galaxyproject/galaxy/pull/18333>`_
* Fix seek in slurm memory check by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18338 <https://github.com/galaxyproject/galaxy/pull/18338>`_
* Do not copy purged outputs to object store by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18342 <https://github.com/galaxyproject/galaxy/pull/18342>`_
* Kill pulsar job if job stopped on galaxy side by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18348 <https://github.com/galaxyproject/galaxy/pull/18348>`_
* Allow DCE as outer input to to_cwl by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18349 <https://github.com/galaxyproject/galaxy/pull/18349>`_
* Fix anonymous user job retrieval logic by `@davelopez <https://github.com/davelopez>`_ in `#18358 <https://github.com/galaxyproject/galaxy/pull/18358>`_
* Fix update group API payload model by `@davelopez <https://github.com/davelopez>`_ in `#18374 <https://github.com/galaxyproject/galaxy/pull/18374>`_
* Fix user's private role can be missing by `@davelopez <https://github.com/davelopez>`_ in `#18381 <https://github.com/galaxyproject/galaxy/pull/18381>`_
* Fix null inputs in database operation tools by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18385 <https://github.com/galaxyproject/galaxy/pull/18385>`_
* Assign default ``data`` extension on discovered collection output  by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18389 <https://github.com/galaxyproject/galaxy/pull/18389>`_
* Fix ``get_accessible_job`` if called without session by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18400 <https://github.com/galaxyproject/galaxy/pull/18400>`_
* Fix invocation step_job_summary for new collections by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18402 <https://github.com/galaxyproject/galaxy/pull/18402>`_
* Really allow in-range validator for txt by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#18411 <https://github.com/galaxyproject/galaxy/pull/18411>`_
* Fix collection map over status for dragged collections by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18416 <https://github.com/galaxyproject/galaxy/pull/18416>`_
* Serialize purged flag for datasets in collections by `@davelopez <https://github.com/davelopez>`_ in `#18420 <https://github.com/galaxyproject/galaxy/pull/18420>`_

=============
Other changes
=============

* Minor linting cleanup by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18421 <https://github.com/galaxyproject/galaxy/pull/18421>`_
* Replace busybox:ubuntu-14.04 image with busybox:1.36.1-glibc by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18428 <https://github.com/galaxyproject/galaxy/pull/18428>`_

-------------------
24.0.2 (2024-05-07)
-------------------


=========
Bug fixes
=========

* Adds logging of messageExceptions in the fastapi exception handler. by `@dannon <https://github.com/dannon>`_ in `#18041 <https://github.com/galaxyproject/galaxy/pull/18041>`_
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
* Fix saving workflows with freehand_comments only by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17901 <https://github.com/galaxyproject/galaxy/pull/17901>`_
* Always discard session after __handle_waiting_jobs is done by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17913 <https://github.com/galaxyproject/galaxy/pull/17913>`_
* Fix workflow run form for workflows with null rename PJA by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17929 <https://github.com/galaxyproject/galaxy/pull/17929>`_
* Revert unnecessary error change by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17948 <https://github.com/galaxyproject/galaxy/pull/17948>`_
* Fix missing implicit conversion for mapped over jobs by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17952 <https://github.com/galaxyproject/galaxy/pull/17952>`_
* Fix get_content_as_text for compressed text datatypes by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17976 <https://github.com/galaxyproject/galaxy/pull/17976>`_
* Backport: Fix bug: call unique() on result, not select stmt by `@jdavcs <https://github.com/jdavcs>`_ in `#17981 <https://github.com/galaxyproject/galaxy/pull/17981>`_
* Fix `LengthValidator` if no value passed by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17983 <https://github.com/galaxyproject/galaxy/pull/17983>`_
* Raise ``RequestParameterInvalidException`` if collection element has unknown extension by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17985 <https://github.com/galaxyproject/galaxy/pull/17985>`_
* Don't attempt to commit in dry_run mode by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17987 <https://github.com/galaxyproject/galaxy/pull/17987>`_
* Don't fail if reporting invalid parameter values by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18002 <https://github.com/galaxyproject/galaxy/pull/18002>`_
* Include exception info when something goes wrong while refreshing tokens by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18008 <https://github.com/galaxyproject/galaxy/pull/18008>`_
* Avoid exception when opening apply rules tool and no collection in history by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18011 <https://github.com/galaxyproject/galaxy/pull/18011>`_
* Don't commit without having set a hid by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18014 <https://github.com/galaxyproject/galaxy/pull/18014>`_
* Raise appropriate exception if user forces a collection that is not populated with elements as input by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18023 <https://github.com/galaxyproject/galaxy/pull/18023>`_
* Fix tag regex pattern by `@jdavcs <https://github.com/jdavcs>`_ in `#18025 <https://github.com/galaxyproject/galaxy/pull/18025>`_
* Fix History Dataset Association creation so that hid is always set by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18036 <https://github.com/galaxyproject/galaxy/pull/18036>`_
* Change wrong quota_source value from KeyError to ValueError by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18040 <https://github.com/galaxyproject/galaxy/pull/18040>`_
* Check database connection to issue a rollback if no connection by `@jdavcs <https://github.com/jdavcs>`_ in `#18070 <https://github.com/galaxyproject/galaxy/pull/18070>`_

============
Enhancements
============

* Fix remote files sources error handling by `@davelopez <https://github.com/davelopez>`_ in `#18027 <https://github.com/galaxyproject/galaxy/pull/18027>`_

=============
Other changes
=============

* Drop left-over debug statement by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17939 <https://github.com/galaxyproject/galaxy/pull/17939>`_

-------------------
24.0.0 (2024-04-02)
-------------------


=========
Bug fixes
=========

* Reload built-in converters on toolbox reload by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#17209 <https://github.com/galaxyproject/galaxy/pull/17209>`_
* Optional Reply-to SMTP header in tool error reports by `@neoformit <https://github.com/neoformit>`_ in `#17243 <https://github.com/galaxyproject/galaxy/pull/17243>`_
* Package tests fixes by `@nsoranzo <https://github.com/nsoranzo>`_ in `#17301 <https://github.com/galaxyproject/galaxy/pull/17301>`_
* Follow-up on #17274 and #17262 by `@nsoranzo <https://github.com/nsoranzo>`_ in `#17302 <https://github.com/galaxyproject/galaxy/pull/17302>`_
* Rollback invalidated transaction: catch them earlier by `@jdavcs <https://github.com/jdavcs>`_ in `#17312 <https://github.com/galaxyproject/galaxy/pull/17312>`_
* Fixes for flake8-bugbear 24.1.17 by `@nsoranzo <https://github.com/nsoranzo>`_ in `#17340 <https://github.com/galaxyproject/galaxy/pull/17340>`_
* Fix data_source and data_source_async bugs by `@wm75 <https://github.com/wm75>`_ in `#17422 <https://github.com/galaxyproject/galaxy/pull/17422>`_
* More efficient change_state queries, maybe fix deadlock by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17632 <https://github.com/galaxyproject/galaxy/pull/17632>`_
* Don't index tasks without task_uuid by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17646 <https://github.com/galaxyproject/galaxy/pull/17646>`_
* Separate `ConnectedValue` from `RuntimeValue` by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17678 <https://github.com/galaxyproject/galaxy/pull/17678>`_
* Fix step type serialization for StoredWorkflowDetailed models by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17716 <https://github.com/galaxyproject/galaxy/pull/17716>`_
* Fix usage of DISTINCT by `@jdavcs <https://github.com/jdavcs>`_ in `#17759 <https://github.com/galaxyproject/galaxy/pull/17759>`_
* Also set extension and metadata on copies of job outputs when finishing job by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17777 <https://github.com/galaxyproject/galaxy/pull/17777>`_
* Use ``hg clone --stream`` to clone repos by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17786 <https://github.com/galaxyproject/galaxy/pull/17786>`_
* Defer job attributes that are usually not needed by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17795 <https://github.com/galaxyproject/galaxy/pull/17795>`_
* Fix change_datatype PJA for dynamic collections  by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17803 <https://github.com/galaxyproject/galaxy/pull/17803>`_
* Fix archived histories mixing with active in histories list by `@davelopez <https://github.com/davelopez>`_ in `#17856 <https://github.com/galaxyproject/galaxy/pull/17856>`_
* Normalize extensions when loading tool by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17868 <https://github.com/galaxyproject/galaxy/pull/17868>`_
* Ignore user data table errors for now by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17880 <https://github.com/galaxyproject/galaxy/pull/17880>`_

============
Enhancements
============

* Add harmonize collections tool (or whatever other name) by `@lldelisle <https://github.com/lldelisle>`_ in `#16662 <https://github.com/galaxyproject/galaxy/pull/16662>`_
* Add support for Python 3.12 by `@tuncK <https://github.com/tuncK>`_ in `#16796 <https://github.com/galaxyproject/galaxy/pull/16796>`_
* SQLAlchemy 2.0 upgrades (part 5) by `@jdavcs <https://github.com/jdavcs>`_ in `#16932 <https://github.com/galaxyproject/galaxy/pull/16932>`_
* Python 3.8 as minimum by `@mr-c <https://github.com/mr-c>`_ in `#16954 <https://github.com/galaxyproject/galaxy/pull/16954>`_
* Support for OIDC API Auth and OIDC integration tests by `@nuwang <https://github.com/nuwang>`_ in `#16977 <https://github.com/galaxyproject/galaxy/pull/16977>`_
* Toward declarative help for Galaxy markdown directives. by `@jmchilton <https://github.com/jmchilton>`_ in `#16979 <https://github.com/galaxyproject/galaxy/pull/16979>`_
* Extend regex groups in stdio regex matches by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#17016 <https://github.com/galaxyproject/galaxy/pull/17016>`_
* Vueify Admin User Grid by `@guerler <https://github.com/guerler>`_ in `#17030 <https://github.com/galaxyproject/galaxy/pull/17030>`_
* Remove web framework dependency from tools by `@davelopez <https://github.com/davelopez>`_ in `#17058 <https://github.com/galaxyproject/galaxy/pull/17058>`_
* Add select parameter with options from remote resources by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17087 <https://github.com/galaxyproject/galaxy/pull/17087>`_
* Expose more tool information / navigability in UI. by `@jmchilton <https://github.com/jmchilton>`_ in `#17105 <https://github.com/galaxyproject/galaxy/pull/17105>`_
* Vueify Admin Roles Grid by `@guerler <https://github.com/guerler>`_ in `#17118 <https://github.com/galaxyproject/galaxy/pull/17118>`_
* SA2.0 updates: handling "object is being merged into a Session along the backref cascade path" by `@jdavcs <https://github.com/jdavcs>`_ in `#17122 <https://github.com/galaxyproject/galaxy/pull/17122>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#17123 <https://github.com/galaxyproject/galaxy/pull/17123>`_
* Vueify Admin Groups Grid by `@guerler <https://github.com/guerler>`_ in `#17126 <https://github.com/galaxyproject/galaxy/pull/17126>`_
* Towards SQLAlchemy 2.0: fix last cases of RemovedIn20Warning by `@jdavcs <https://github.com/jdavcs>`_ in `#17132 <https://github.com/galaxyproject/galaxy/pull/17132>`_
* Vueify Admin Forms and Quota grids by `@guerler <https://github.com/guerler>`_ in `#17141 <https://github.com/galaxyproject/galaxy/pull/17141>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#17157 <https://github.com/galaxyproject/galaxy/pull/17157>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#17201 <https://github.com/galaxyproject/galaxy/pull/17201>`_
* Vendorize fastapi-utls.cbv by `@jdavcs <https://github.com/jdavcs>`_ in `#17205 <https://github.com/galaxyproject/galaxy/pull/17205>`_
* Fix usage of graphene-sqlalchemy, bump to 3.0.0rc1 by `@jdavcs <https://github.com/jdavcs>`_ in `#17216 <https://github.com/galaxyproject/galaxy/pull/17216>`_
* Vueifiy History Grids by `@guerler <https://github.com/guerler>`_ in `#17219 <https://github.com/galaxyproject/galaxy/pull/17219>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#17230 <https://github.com/galaxyproject/galaxy/pull/17230>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#17235 <https://github.com/galaxyproject/galaxy/pull/17235>`_
* Allow job files to consume TUS uploads by `@jmchilton <https://github.com/jmchilton>`_ in `#17242 <https://github.com/galaxyproject/galaxy/pull/17242>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#17247 <https://github.com/galaxyproject/galaxy/pull/17247>`_
* Migrate models to pydantic 2 by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17262 <https://github.com/galaxyproject/galaxy/pull/17262>`_
* Consider Null inputs by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#17271 <https://github.com/galaxyproject/galaxy/pull/17271>`_
* Add OIDC backend configuration schema and validation by `@uwwint <https://github.com/uwwint>`_ in `#17274 <https://github.com/galaxyproject/galaxy/pull/17274>`_
* Adds delete, purge and undelete batch operations to History Grid by `@guerler <https://github.com/guerler>`_ in `#17282 <https://github.com/galaxyproject/galaxy/pull/17282>`_
* Add ``__KEEP_SUCCESS_DATASETS__`` by `@lldelisle <https://github.com/lldelisle>`_ in `#17294 <https://github.com/galaxyproject/galaxy/pull/17294>`_
* Improve ModelManager type hints by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17299 <https://github.com/galaxyproject/galaxy/pull/17299>`_
* API endpoint that allows "changing" the objectstore for "safe" scenarios.  by `@jmchilton <https://github.com/jmchilton>`_ in `#17329 <https://github.com/galaxyproject/galaxy/pull/17329>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#17333 <https://github.com/galaxyproject/galaxy/pull/17333>`_
* Add element_identifier and ext to inputs config file export by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#17357 <https://github.com/galaxyproject/galaxy/pull/17357>`_
* Remove unused statements in job search function by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17361 <https://github.com/galaxyproject/galaxy/pull/17361>`_
* Enable ``warn_unreachable`` mypy option by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17365 <https://github.com/galaxyproject/galaxy/pull/17365>`_
* Fix type annotation of code using XML etree by `@nsoranzo <https://github.com/nsoranzo>`_ in `#17367 <https://github.com/galaxyproject/galaxy/pull/17367>`_
* More specific type annotation for ``BaseJobExec.parse_status()`` by `@nsoranzo <https://github.com/nsoranzo>`_ in `#17381 <https://github.com/galaxyproject/galaxy/pull/17381>`_
* Cancel all active jobs when the user is deleted by `@davelopez <https://github.com/davelopez>`_ in `#17390 <https://github.com/galaxyproject/galaxy/pull/17390>`_
* Update to black 2024 stable style by `@nsoranzo <https://github.com/nsoranzo>`_ in `#17391 <https://github.com/galaxyproject/galaxy/pull/17391>`_
* Purge `groups` and `roles` from DB (for real) by `@davelopez <https://github.com/davelopez>`_ in `#17411 <https://github.com/galaxyproject/galaxy/pull/17411>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#17420 <https://github.com/galaxyproject/galaxy/pull/17420>`_
* Allow using tool data bundles as inputs to reference data select parameters by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17435 <https://github.com/galaxyproject/galaxy/pull/17435>`_
* Adds published histories to grid list by `@guerler <https://github.com/guerler>`_ in `#17449 <https://github.com/galaxyproject/galaxy/pull/17449>`_
* Allow filtering history datasets by object store ID and quota source. by `@jmchilton <https://github.com/jmchilton>`_ in `#17460 <https://github.com/galaxyproject/galaxy/pull/17460>`_
* `data_column` parameter: use `column_names` metadata if present by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#17478 <https://github.com/galaxyproject/galaxy/pull/17478>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#17486 <https://github.com/galaxyproject/galaxy/pull/17486>`_
* Consolidate resource grids into tab views by `@guerler <https://github.com/guerler>`_ in `#17487 <https://github.com/galaxyproject/galaxy/pull/17487>`_
* Update k8s docker python to 3.12 by `@nuwang <https://github.com/nuwang>`_ in `#17494 <https://github.com/galaxyproject/galaxy/pull/17494>`_
* add encode ID API endpoint by `@mira-miracoli <https://github.com/mira-miracoli>`_ in `#17510 <https://github.com/galaxyproject/galaxy/pull/17510>`_
* Fixing data_source tools and incrementing tool profile by `@wm75 <https://github.com/wm75>`_ in `#17515 <https://github.com/galaxyproject/galaxy/pull/17515>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#17541 <https://github.com/galaxyproject/galaxy/pull/17541>`_
* Add `image_diff` comparison method for test output verification using images by `@kostrykin <https://github.com/kostrykin>`_ in `#17556 <https://github.com/galaxyproject/galaxy/pull/17556>`_
* Filter out subworkflow invocations by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17558 <https://github.com/galaxyproject/galaxy/pull/17558>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#17580 <https://github.com/galaxyproject/galaxy/pull/17580>`_
* Restore histories API behavior for `keys` query parameter by `@davelopez <https://github.com/davelopez>`_ in `#17779 <https://github.com/galaxyproject/galaxy/pull/17779>`_
* Fix datasets API custom keys encoding by `@davelopez <https://github.com/davelopez>`_ in `#17793 <https://github.com/galaxyproject/galaxy/pull/17793>`_
* Improved error messages for runtime sharing problems. by `@jmchilton <https://github.com/jmchilton>`_ in `#17794 <https://github.com/galaxyproject/galaxy/pull/17794>`_
* Allow admin to sharpen language about selected object stores. by `@jmchilton <https://github.com/jmchilton>`_ in `#17806 <https://github.com/galaxyproject/galaxy/pull/17806>`_

=============
Other changes
=============

* consistently compare profile versions by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#16492 <https://github.com/galaxyproject/galaxy/pull/16492>`_

-------------------
23.2.1 (2024-02-21)
-------------------


=========
Bug fixes
=========

* pin fs.dropboxfs to >=1 by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#16451 <https://github.com/galaxyproject/galaxy/pull/16451>`_
* Remove unnecessary check: item cannot be None by `@jdavcs <https://github.com/jdavcs>`_ in `#16550 <https://github.com/galaxyproject/galaxy/pull/16550>`_
* Fix: serialize `tool_shed_urls` directly from the API by `@davelopez <https://github.com/davelopez>`_ in `#16561 <https://github.com/galaxyproject/galaxy/pull/16561>`_
* Fix dependency update GitHub workflow by `@nsoranzo <https://github.com/nsoranzo>`_ in `#16639 <https://github.com/galaxyproject/galaxy/pull/16639>`_
* Ensure Job belongs to current SA session by `@jdavcs <https://github.com/jdavcs>`_ in `#16647 <https://github.com/galaxyproject/galaxy/pull/16647>`_
* Account for shared usage between TS and galaxy apps by `@jdavcs <https://github.com/jdavcs>`_ in `#16746 <https://github.com/galaxyproject/galaxy/pull/16746>`_
* move the email and username redacting from the role loop by `@martenson <https://github.com/martenson>`_ in `#16805 <https://github.com/galaxyproject/galaxy/pull/16805>`_
* Fix shed unit test by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16811 <https://github.com/galaxyproject/galaxy/pull/16811>`_
* chore: fix typos by `@afuetterer <https://github.com/afuetterer>`_ in `#16851 <https://github.com/galaxyproject/galaxy/pull/16851>`_
* Fix bug in SQLAlchemy statement by `@jdavcs <https://github.com/jdavcs>`_ in `#16881 <https://github.com/galaxyproject/galaxy/pull/16881>`_
* Ruff and flake8 fixes by `@nsoranzo <https://github.com/nsoranzo>`_ in `#16884 <https://github.com/galaxyproject/galaxy/pull/16884>`_
* Update help in relabel_from_file.xml by `@lldelisle <https://github.com/lldelisle>`_ in `#16891 <https://github.com/galaxyproject/galaxy/pull/16891>`_
* Fix subtle bug in listify function + simplify list munging by `@jdavcs <https://github.com/jdavcs>`_ in `#16904 <https://github.com/galaxyproject/galaxy/pull/16904>`_
* prep for updated h5py and typos by `@mr-c <https://github.com/mr-c>`_ in `#16963 <https://github.com/galaxyproject/galaxy/pull/16963>`_
* Enhancement to Tool Form page, Repeating form fields implement parameter instructions by `@hujambo-dunia <https://github.com/hujambo-dunia>`_ in `#17018 <https://github.com/galaxyproject/galaxy/pull/17018>`_
* Expose file_name property in DatasetFilenameWrapper by `@jdavcs <https://github.com/jdavcs>`_ in `#17107 <https://github.com/galaxyproject/galaxy/pull/17107>`_
* Fix ``to_cwl`` for nested collections by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17276 <https://github.com/galaxyproject/galaxy/pull/17276>`_
* Rollback invalidated transaction by `@jdavcs <https://github.com/jdavcs>`_ in `#17280 <https://github.com/galaxyproject/galaxy/pull/17280>`_
* Install newer celery on python 3.8+ by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17309 <https://github.com/galaxyproject/galaxy/pull/17309>`_
* Backport Rollback invalidated transaction: catch them earlier by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17315 <https://github.com/galaxyproject/galaxy/pull/17315>`_
* Discard sqlalchemy session after task completion by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17317 <https://github.com/galaxyproject/galaxy/pull/17317>`_
* Scope session for job  runner monitor loop by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17319 <https://github.com/galaxyproject/galaxy/pull/17319>`_
* Fix History contents `genome_build` filter postgresql bug by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#17384 <https://github.com/galaxyproject/galaxy/pull/17384>`_
* Update python-multipart to 0.0.7 by `@nsoranzo <https://github.com/nsoranzo>`_ in `#17429 <https://github.com/galaxyproject/galaxy/pull/17429>`_
* Build param dict before creating entrypoint by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17440 <https://github.com/galaxyproject/galaxy/pull/17440>`_
* Fix bug: true >> True by `@jdavcs <https://github.com/jdavcs>`_ in `#17446 <https://github.com/galaxyproject/galaxy/pull/17446>`_
* Set metadata states on dataset association, not dataset by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17474 <https://github.com/galaxyproject/galaxy/pull/17474>`_
* Remove two print statements by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#17480 <https://github.com/galaxyproject/galaxy/pull/17480>`_
* Provide working routes.url_for every ASGI request by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17497 <https://github.com/galaxyproject/galaxy/pull/17497>`_

============
Enhancements
============

* Implement default locations for data and collection parameters. by `@jmchilton <https://github.com/jmchilton>`_ in `#14955 <https://github.com/galaxyproject/galaxy/pull/14955>`_
* Enable job resubmissions in k8s runner by `@pcm32 <https://github.com/pcm32>`_ in `#15238 <https://github.com/galaxyproject/galaxy/pull/15238>`_
* Add parameter name to validation errors by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#15440 <https://github.com/galaxyproject/galaxy/pull/15440>`_
* Tool Shed 2.0 by `@jmchilton <https://github.com/jmchilton>`_ in `#15639 <https://github.com/galaxyproject/galaxy/pull/15639>`_
* Add ability to assert metadata properties on input dataset parameters by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#15825 <https://github.com/galaxyproject/galaxy/pull/15825>`_
* Limit number of celery task executions per second per user by `@claudiofr <https://github.com/claudiofr>`_ in `#16232 <https://github.com/galaxyproject/galaxy/pull/16232>`_
* Delete non-terminal jobs and subworkflow invocations when cancelling invocation by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16252 <https://github.com/galaxyproject/galaxy/pull/16252>`_
* Towards SQLAlchemy 2.0 (upgrades to SA Core usage) by `@jdavcs <https://github.com/jdavcs>`_ in `#16264 <https://github.com/galaxyproject/galaxy/pull/16264>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#16305 <https://github.com/galaxyproject/galaxy/pull/16305>`_
* Add carbon emissions admin configuration options by `@Renni771 <https://github.com/Renni771>`_ in `#16307 <https://github.com/galaxyproject/galaxy/pull/16307>`_
* Migrate a part of the users API to Fast API by `@heisner-tillman <https://github.com/heisner-tillman>`_ in `#16341 <https://github.com/galaxyproject/galaxy/pull/16341>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#16360 <https://github.com/galaxyproject/galaxy/pull/16360>`_
* Add Invenio RDM repository integration by `@davelopez <https://github.com/davelopez>`_ in `#16381 <https://github.com/galaxyproject/galaxy/pull/16381>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#16389 <https://github.com/galaxyproject/galaxy/pull/16389>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#16409 <https://github.com/galaxyproject/galaxy/pull/16409>`_
* Refactor FilesDialog + Remote Files API schema improvements by `@davelopez <https://github.com/davelopez>`_ in `#16420 <https://github.com/galaxyproject/galaxy/pull/16420>`_
* Towards SQLAlchemy 2.0 (upgrades to SA ORM usage in /test) by `@jdavcs <https://github.com/jdavcs>`_ in `#16431 <https://github.com/galaxyproject/galaxy/pull/16431>`_
* SQLAlchemy 2.0 upgrades to ORM usage in /lib by `@jdavcs <https://github.com/jdavcs>`_ in `#16434 <https://github.com/galaxyproject/galaxy/pull/16434>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#16436 <https://github.com/galaxyproject/galaxy/pull/16436>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#16485 <https://github.com/galaxyproject/galaxy/pull/16485>`_
* Rename MetadataEqualsValidator by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#16489 <https://github.com/galaxyproject/galaxy/pull/16489>`_
* Add support for CILogon deployments in different regions than the US by `@uwwint <https://github.com/uwwint>`_ in `#16490 <https://github.com/galaxyproject/galaxy/pull/16490>`_
* Refactor/OIDC custos by `@uwwint <https://github.com/uwwint>`_ in `#16497 <https://github.com/galaxyproject/galaxy/pull/16497>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#16521 <https://github.com/galaxyproject/galaxy/pull/16521>`_
* Move database access code out of ``galaxy.util`` by `@jdavcs <https://github.com/jdavcs>`_ in `#16526 <https://github.com/galaxyproject/galaxy/pull/16526>`_
* Tweak tool memory use and optimize shared memory when using preload by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16536 <https://github.com/galaxyproject/galaxy/pull/16536>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#16577 <https://github.com/galaxyproject/galaxy/pull/16577>`_
* Vueify Tool Form Data Selector by `@guerler <https://github.com/guerler>`_ in `#16578 <https://github.com/galaxyproject/galaxy/pull/16578>`_
* Workflow Comments 💬 by `@ElectronicBlueberry <https://github.com/ElectronicBlueberry>`_ in `#16612 <https://github.com/galaxyproject/galaxy/pull/16612>`_
* Switch out conditional requirement parser by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16636 <https://github.com/galaxyproject/galaxy/pull/16636>`_
* Add scroll pagination and username filter to `HistoryPublishedList` by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#16642 <https://github.com/galaxyproject/galaxy/pull/16642>`_
* Bump samtools converters by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#16668 <https://github.com/galaxyproject/galaxy/pull/16668>`_
* Galaxy Markdown - add workflow image and license to Galaxy markdown. by `@jmchilton <https://github.com/jmchilton>`_ in `#16672 <https://github.com/galaxyproject/galaxy/pull/16672>`_
* Implement instance URLs in Galaxy markdown. by `@jmchilton <https://github.com/jmchilton>`_ in `#16675 <https://github.com/galaxyproject/galaxy/pull/16675>`_
* Change Sentry error reporting plug-in by `@kysrpex <https://github.com/kysrpex>`_ in `#16686 <https://github.com/galaxyproject/galaxy/pull/16686>`_
* Use fs.onedatarestfs for Onedata files source plugin implementation by `@lopiola <https://github.com/lopiola>`_ in `#16690 <https://github.com/galaxyproject/galaxy/pull/16690>`_
* Enhance task monitor composable by `@davelopez <https://github.com/davelopez>`_ in `#16695 <https://github.com/galaxyproject/galaxy/pull/16695>`_
* Misc. edits/refactorings to session handling  by `@jdavcs <https://github.com/jdavcs>`_ in `#16712 <https://github.com/galaxyproject/galaxy/pull/16712>`_
* SQLAlchemy 2.0 upgrades (part 2) by `@jdavcs <https://github.com/jdavcs>`_ in `#16724 <https://github.com/galaxyproject/galaxy/pull/16724>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#16735 <https://github.com/galaxyproject/galaxy/pull/16735>`_
* Convert ISO to UTC for Date/Time in workflow reports by `@assuntad23 <https://github.com/assuntad23>`_ in `#16758 <https://github.com/galaxyproject/galaxy/pull/16758>`_
* Replace ELIXIR AAI button with Life Science login by `@sebastian-schaaf <https://github.com/sebastian-schaaf>`_ in `#16762 <https://github.com/galaxyproject/galaxy/pull/16762>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#16770 <https://github.com/galaxyproject/galaxy/pull/16770>`_
* Migrate a part of the jobs API to Fast API by `@heisner-tillman <https://github.com/heisner-tillman>`_ in `#16778 <https://github.com/galaxyproject/galaxy/pull/16778>`_
* Add EGI Check-in as OIDC authentication option by `@enolfc <https://github.com/enolfc>`_ in `#16782 <https://github.com/galaxyproject/galaxy/pull/16782>`_
* Replace file_name property with get_file_name function by `@SergeyYakubov <https://github.com/SergeyYakubov>`_ in `#16783 <https://github.com/galaxyproject/galaxy/pull/16783>`_
* Updated path-based interactive tools with entry point path injection, support for ITs with relative links, shortened URLs, doc and config updates including Podman job_conf by `@sveinugu <https://github.com/sveinugu>`_ in `#16795 <https://github.com/galaxyproject/galaxy/pull/16795>`_
* Galaxy help forum integration by `@ElectronicBlueberry <https://github.com/ElectronicBlueberry>`_ in `#16798 <https://github.com/galaxyproject/galaxy/pull/16798>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#16807 <https://github.com/galaxyproject/galaxy/pull/16807>`_
* Another batch of SA2.0 edits in TS2.0 (part 3) by `@jdavcs <https://github.com/jdavcs>`_ in `#16833 <https://github.com/galaxyproject/galaxy/pull/16833>`_
* Remove remaining legacy backbone form input elements by `@guerler <https://github.com/guerler>`_ in `#16834 <https://github.com/galaxyproject/galaxy/pull/16834>`_
* SQLAlchemy 2.0 upgrades (part 4) by `@jdavcs <https://github.com/jdavcs>`_ in `#16852 <https://github.com/galaxyproject/galaxy/pull/16852>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#16853 <https://github.com/galaxyproject/galaxy/pull/16853>`_
* Drop unused HistoryContentManager code and related tests by `@jdavcs <https://github.com/jdavcs>`_ in `#16882 <https://github.com/galaxyproject/galaxy/pull/16882>`_
* Vueify Visualizations Grid by `@guerler <https://github.com/guerler>`_ in `#16892 <https://github.com/galaxyproject/galaxy/pull/16892>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#16896 <https://github.com/galaxyproject/galaxy/pull/16896>`_
* Enable some flake8-logging-format rules in ruff by `@nsoranzo <https://github.com/nsoranzo>`_ in `#16915 <https://github.com/galaxyproject/galaxy/pull/16915>`_
* Remove "Create Workflow" form and allow workflow creation in editor by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#16938 <https://github.com/galaxyproject/galaxy/pull/16938>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#16939 <https://github.com/galaxyproject/galaxy/pull/16939>`_
* Add helper to get dataset or collection via ``src`` and ``id`` by `@mr-c <https://github.com/mr-c>`_ in `#16953 <https://github.com/galaxyproject/galaxy/pull/16953>`_
* Allow non-optional integer/float params without value attribute by `@nsoranzo <https://github.com/nsoranzo>`_ in `#16966 <https://github.com/galaxyproject/galaxy/pull/16966>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#16978 <https://github.com/galaxyproject/galaxy/pull/16978>`_
* Fix invocation report to target correct workflow version. by `@jmchilton <https://github.com/jmchilton>`_ in `#17008 <https://github.com/galaxyproject/galaxy/pull/17008>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#17011 <https://github.com/galaxyproject/galaxy/pull/17011>`_
* Upgrade job manager's index_query method to SA2.0 by `@jdavcs <https://github.com/jdavcs>`_ in `#17020 <https://github.com/galaxyproject/galaxy/pull/17020>`_
* optimize object store cache operations by `@SergeyYakubov <https://github.com/SergeyYakubov>`_ in `#17025 <https://github.com/galaxyproject/galaxy/pull/17025>`_
* Require name for workflows on save, set default to Unnamed Workflow by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#17038 <https://github.com/galaxyproject/galaxy/pull/17038>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#17050 <https://github.com/galaxyproject/galaxy/pull/17050>`_
* Migrate groups API to fastAPI by `@arash77 <https://github.com/arash77>`_ in `#17051 <https://github.com/galaxyproject/galaxy/pull/17051>`_
* Migrate ItemTags API to FastAPI by `@arash77 <https://github.com/arash77>`_ in `#17064 <https://github.com/galaxyproject/galaxy/pull/17064>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#17084 <https://github.com/galaxyproject/galaxy/pull/17084>`_
* Use python-isal for fast zip deflate compression in rocrate export by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17342 <https://github.com/galaxyproject/galaxy/pull/17342>`_

=============
Other changes
=============

* Merge 23.1 into dev by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16534 <https://github.com/galaxyproject/galaxy/pull/16534>`_
* Revert "[23.1] Enable job resubmissions in k8s runner" by `@nuwang <https://github.com/nuwang>`_ in `#17323 <https://github.com/galaxyproject/galaxy/pull/17323>`_
* Fix succces typo by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17481 <https://github.com/galaxyproject/galaxy/pull/17481>`_

-------------------
23.1.4 (2024-01-04)
-------------------


=========
Bug fixes
=========

* Fix workflow index total matches counting by `@davelopez <https://github.com/davelopez>`_ in `#17176 <https://github.com/galaxyproject/galaxy/pull/17176>`_
* Fix `url_for` in tool error reports by `@davelopez <https://github.com/davelopez>`_ in `#17210 <https://github.com/galaxyproject/galaxy/pull/17210>`_

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

* Update pulsar client library to 0.15.5 by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16701 <https://github.com/galaxyproject/galaxy/pull/16701>`_

-------------------
23.0.5 (2023-07-29)
-------------------


=========
Bug fixes
=========

* Skip installing npm/yarn if available, fix conditional dependency parsing, create virtualenv via conda when conda active by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#16403 <https://github.com/galaxyproject/galaxy/pull/16403>`_
* Fix test discovery in vscode by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16413 <https://github.com/galaxyproject/galaxy/pull/16413>`_
* Fixes for (gitlab) error reporting by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#16424 <https://github.com/galaxyproject/galaxy/pull/16424>`_

-------------------
23.0.4 (2023-06-30)
-------------------


=========
Bug fixes
=========

* Fix default when statement evaluation by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16332 <https://github.com/galaxyproject/galaxy/pull/16332>`_
* Redact private role name and description when purging user by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16349 <https://github.com/galaxyproject/galaxy/pull/16349>`_

-------------------
23.0.3 (2023-06-26)
-------------------


=========
Bug fixes
=========

* Bump galaxy-release-util version to 0.1.2 by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16241 <https://github.com/galaxyproject/galaxy/pull/16241>`_

============
Enhancements
============

* When importing tool data bundles, use the first loc file for the matching table by `@natefoo <https://github.com/natefoo>`_ in `#16247 <https://github.com/galaxyproject/galaxy/pull/16247>`_

=============
Other changes
=============

* Forward port of slugify username received from oidc by `@nuwang <https://github.com/nuwang>`_ in `#16271 <https://github.com/galaxyproject/galaxy/pull/16271>`_

-------------------
23.0.2 (2023-06-13)
-------------------


=========
Bug fixes
=========

* Fix ``Text File Busy`` errors at the source by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16212 <https://github.com/galaxyproject/galaxy/pull/16212>`_

============
Enhancements
============

* Point release deps fixes and docs by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16214 <https://github.com/galaxyproject/galaxy/pull/16214>`_
* Use galaxy-release-util to upload python packages by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16240 <https://github.com/galaxyproject/galaxy/pull/16240>`_

-------------------
23.0.1 (2023-06-08)
-------------------


=========
Bug fixes
=========

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

* Startup fix when tool removed between reboot by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16175 <https://github.com/galaxyproject/galaxy/pull/16175>`_

-------------------
20.9.0 (2020-10-15)
-------------------

* First release from the 20.09 branch of Galaxy.

-------------------
20.5.0 (2020-07-04)
-------------------

* First release from the 20.05 branch of Galaxy.
