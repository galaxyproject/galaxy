History
-------

.. to_doc

-----------
24.2.1.dev0
-----------



-------------------
24.2.0 (2025-02-11)
-------------------


=========
Bug fixes
=========

* Drop "Send to cloud" tool and associated cloudauthz code by `@jdavcs <https://github.com/jdavcs>`_ in `#18196 <https://github.com/galaxyproject/galaxy/pull/18196>`_
* Raise Message Exception when displaying binary data by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18503 <https://github.com/galaxyproject/galaxy/pull/18503>`_
* Fixes for errors reported by mypy 1.11.0 by `@nsoranzo <https://github.com/nsoranzo>`_ in `#18608 <https://github.com/galaxyproject/galaxy/pull/18608>`_
* Fix new flake8-bugbear B039 and mypy type-var errors by `@nsoranzo <https://github.com/nsoranzo>`_ in `#18755 <https://github.com/galaxyproject/galaxy/pull/18755>`_
* Fix migration data fixes tests by `@jdavcs <https://github.com/jdavcs>`_ in `#18885 <https://github.com/galaxyproject/galaxy/pull/18885>`_
* Fix backend role sharing bug by `@jdavcs <https://github.com/jdavcs>`_ in `#18942 <https://github.com/galaxyproject/galaxy/pull/18942>`_
* Add merge migration to merge 2 heads by `@jdavcs <https://github.com/jdavcs>`_ in `#19163 <https://github.com/galaxyproject/galaxy/pull/19163>`_
* Record implicitly converted dataset as input dataset by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19301 <https://github.com/galaxyproject/galaxy/pull/19301>`_
* Fix quota usage with user object stores by `@davelopez <https://github.com/davelopez>`_ in `#19323 <https://github.com/galaxyproject/galaxy/pull/19323>`_
* Fix workflows with optional non-default parameter input by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19332 <https://github.com/galaxyproject/galaxy/pull/19332>`_
* Fix importing shared workflows with deeply nested subworkflows by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19335 <https://github.com/galaxyproject/galaxy/pull/19335>`_
* Backport fix from #19396 by `@nsoranzo <https://github.com/nsoranzo>`_ in `#19399 <https://github.com/galaxyproject/galaxy/pull/19399>`_
* Prevent cycling through failing conversion jobs in trackster by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19494 <https://github.com/galaxyproject/galaxy/pull/19494>`_
* Fix extracting workflows from purged and deleted histories by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19525 <https://github.com/galaxyproject/galaxy/pull/19525>`_
* Fix error message when subworkflow input connection missing by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19526 <https://github.com/galaxyproject/galaxy/pull/19526>`_
* Fix admin cancel job message not being displayed to the user by `@davelopez <https://github.com/davelopez>`_ in `#19537 <https://github.com/galaxyproject/galaxy/pull/19537>`_
* Add tool_id index on job table by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19543 <https://github.com/galaxyproject/galaxy/pull/19543>`_
* Update 24.2 db revision tags by `@jdavcs <https://github.com/jdavcs>`_ in `#19550 <https://github.com/galaxyproject/galaxy/pull/19550>`_
* Provide guidance in case of deadlock during db migration by `@jdavcs <https://github.com/jdavcs>`_ in `#19551 <https://github.com/galaxyproject/galaxy/pull/19551>`_
* Fix job paused on user defined object store by `@davelopez <https://github.com/davelopez>`_ in `#19578 <https://github.com/galaxyproject/galaxy/pull/19578>`_
* Handle isatools dependency by `@jdavcs <https://github.com/jdavcs>`_ in `#19582 <https://github.com/galaxyproject/galaxy/pull/19582>`_

============
Enhancements
============

* Experimental galactic wizard by `@dannon <https://github.com/dannon>`_ in `#15860 <https://github.com/galaxyproject/galaxy/pull/15860>`_
* Improve usability of Directory datatype by `@wm75 <https://github.com/wm75>`_ in `#17614 <https://github.com/galaxyproject/galaxy/pull/17614>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#18226 <https://github.com/galaxyproject/galaxy/pull/18226>`_
* Allow OAuth 2.0 user defined file sources (w/Dropbox integration) by `@jmchilton <https://github.com/jmchilton>`_ in `#18272 <https://github.com/galaxyproject/galaxy/pull/18272>`_
* More data access tests, some refactoring and cleanup by `@jdavcs <https://github.com/jdavcs>`_ in `#18312 <https://github.com/galaxyproject/galaxy/pull/18312>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#18406 <https://github.com/galaxyproject/galaxy/pull/18406>`_
* Add pod5 datatype by `@TomHarrop <https://github.com/TomHarrop>`_ in `#18419 <https://github.com/galaxyproject/galaxy/pull/18419>`_
* Prepare for NumPy 2.0 by `@nsoranzo <https://github.com/nsoranzo>`_ in `#18422 <https://github.com/galaxyproject/galaxy/pull/18422>`_
* Add unique constraints to the email and username fields in the galaxy_user table by `@jdavcs <https://github.com/jdavcs>`_ in `#18493 <https://github.com/galaxyproject/galaxy/pull/18493>`_
* Improvements for K8S deployment (especially ITs) by `@almahmoud <https://github.com/almahmoud>`_ in `#18514 <https://github.com/galaxyproject/galaxy/pull/18514>`_
* Refactor ``LibraryDatasetsManager`` and fix type annotation issue by `@nsoranzo <https://github.com/nsoranzo>`_ in `#18773 <https://github.com/galaxyproject/galaxy/pull/18773>`_
* Handle compressed content in dataset preview for all sequence classes by `@PlushZ <https://github.com/PlushZ>`_ in `#18776 <https://github.com/galaxyproject/galaxy/pull/18776>`_
* Backend handling of setting user-role, user-group, and group-role associations by `@jdavcs <https://github.com/jdavcs>`_ in `#18777 <https://github.com/galaxyproject/galaxy/pull/18777>`_
* Workflow Landing Requests by `@jmchilton <https://github.com/jmchilton>`_ in `#18807 <https://github.com/galaxyproject/galaxy/pull/18807>`_
* Update Mypy to 1.11.2 and fix new signature override errors by `@nsoranzo <https://github.com/nsoranzo>`_ in `#18811 <https://github.com/galaxyproject/galaxy/pull/18811>`_
* Refactor migration testing setup code by `@jdavcs <https://github.com/jdavcs>`_ in `#18886 <https://github.com/galaxyproject/galaxy/pull/18886>`_
* Allow setting a few global defaults for file source plugin types. by `@jmchilton <https://github.com/jmchilton>`_ in `#18909 <https://github.com/galaxyproject/galaxy/pull/18909>`_
* Type annotations and fixes by `@nsoranzo <https://github.com/nsoranzo>`_ in `#18911 <https://github.com/galaxyproject/galaxy/pull/18911>`_
* Add filter null collection operation tool by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18928 <https://github.com/galaxyproject/galaxy/pull/18928>`_
* Fix extra files path type hint by `@davelopez <https://github.com/davelopez>`_ in `#18958 <https://github.com/galaxyproject/galaxy/pull/18958>`_
* Decouple user email from role name by `@jdavcs <https://github.com/jdavcs>`_ in `#18966 <https://github.com/galaxyproject/galaxy/pull/18966>`_
* Optimize to_history_dataset_association in create_datasets_from_library_folder by `@arash77 <https://github.com/arash77>`_ in `#18970 <https://github.com/galaxyproject/galaxy/pull/18970>`_
* Workflow landing improvements by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18979 <https://github.com/galaxyproject/galaxy/pull/18979>`_
* Allow recovering a normalized version of workflow request state from API by `@jmchilton <https://github.com/jmchilton>`_ in `#18985 <https://github.com/galaxyproject/galaxy/pull/18985>`_
* Add some Zarr-based datatypes by `@davelopez <https://github.com/davelopez>`_ in `#19040 <https://github.com/galaxyproject/galaxy/pull/19040>`_
* Run installed Galaxy with no config and a simplified entry point by `@natefoo <https://github.com/natefoo>`_ in `#19050 <https://github.com/galaxyproject/galaxy/pull/19050>`_
* Annotate ``DatasetAssociationManager`` as generic type by `@nsoranzo <https://github.com/nsoranzo>`_ in `#19063 <https://github.com/galaxyproject/galaxy/pull/19063>`_
* Move TRS import into WorkflowContentManager by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19070 <https://github.com/galaxyproject/galaxy/pull/19070>`_
* Allow deferred datasets to behave as URIs by `@davelopez <https://github.com/davelopez>`_ in `#19077 <https://github.com/galaxyproject/galaxy/pull/19077>`_
* Better cleanup of sharing roles on user purge by `@jdavcs <https://github.com/jdavcs>`_ in `#19096 <https://github.com/galaxyproject/galaxy/pull/19096>`_
* Add XML based `vtk` datatype by `@tStehling <https://github.com/tStehling>`_ in `#19104 <https://github.com/galaxyproject/galaxy/pull/19104>`_
* Access public history in job cache / job search by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19108 <https://github.com/galaxyproject/galaxy/pull/19108>`_
* Always validate hashes when provided by `@nsoranzo <https://github.com/nsoranzo>`_ in `#19110 <https://github.com/galaxyproject/galaxy/pull/19110>`_
* Enable specifying dataset hash in test jobs by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19113 <https://github.com/galaxyproject/galaxy/pull/19113>`_
* Enhance UTF-8 support for filename handling in downloads by `@arash77 <https://github.com/arash77>`_ in `#19161 <https://github.com/galaxyproject/galaxy/pull/19161>`_
* Backport of Workflow Editor Activity Bar by `@dannon <https://github.com/dannon>`_ in `#19212 <https://github.com/galaxyproject/galaxy/pull/19212>`_
* Fix default value handling for parameters connected to required parameters by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19219 <https://github.com/galaxyproject/galaxy/pull/19219>`_

=============
Other changes
=============

* Merge 24.1 by `@jdavcs <https://github.com/jdavcs>`_ in `#18386 <https://github.com/galaxyproject/galaxy/pull/18386>`_
* Format dev to fix linting. by `@jmchilton <https://github.com/jmchilton>`_ in `#18860 <https://github.com/galaxyproject/galaxy/pull/18860>`_
* Add 24.2 migration tags by `@jdavcs <https://github.com/jdavcs>`_ in `#19169 <https://github.com/galaxyproject/galaxy/pull/19169>`_
* Fix type annotations for pysam 0.23.0 by `@nsoranzo <https://github.com/nsoranzo>`_ in `#19571 <https://github.com/galaxyproject/galaxy/pull/19571>`_

-------------------
24.1.4 (2024-12-11)
-------------------


=========
Bug fixes
=========

* Replace busybox:ubuntu-14.04 image with busybox:1.36.1-glibc by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18428 <https://github.com/galaxyproject/galaxy/pull/18428>`_
* Improve workflow-related exception reporting by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18447 <https://github.com/galaxyproject/galaxy/pull/18447>`_
* Increase API robustness to invalid requests, improve compressed data serving by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18494 <https://github.com/galaxyproject/galaxy/pull/18494>`_
* Prevent job submission if input collection element is deleted by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18517 <https://github.com/galaxyproject/galaxy/pull/18517>`_
* Fix shared caches with extended metadata collection. by `@jmchilton <https://github.com/jmchilton>`_ in `#18520 <https://github.com/galaxyproject/galaxy/pull/18520>`_
* Also check dataset.deleted when determining if data can be displayed by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18547 <https://github.com/galaxyproject/galaxy/pull/18547>`_
* Fix for not-null in 'column_list' object by `@hujambo-dunia <https://github.com/hujambo-dunia>`_ in `#18553 <https://github.com/galaxyproject/galaxy/pull/18553>`_
* Fix h5ad metadata by `@nilchia <https://github.com/nilchia>`_ in `#18635 <https://github.com/galaxyproject/galaxy/pull/18635>`_
* Don't set file size to zero by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18653 <https://github.com/galaxyproject/galaxy/pull/18653>`_
* Make sure we set file size also for purged outputs by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18681 <https://github.com/galaxyproject/galaxy/pull/18681>`_
* Fix wrong extension on pick data output by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18798 <https://github.com/galaxyproject/galaxy/pull/18798>`_
* Fix copying workflow with subworkflow step for step that you own by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18802 <https://github.com/galaxyproject/galaxy/pull/18802>`_
* Make pylibmagic import optional by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18813 <https://github.com/galaxyproject/galaxy/pull/18813>`_
* Ignore converted datasets in invalid input states by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18850 <https://github.com/galaxyproject/galaxy/pull/18850>`_
* Fix discovered outputs with directory metadata and distributed object by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18855 <https://github.com/galaxyproject/galaxy/pull/18855>`_
* Raise MessageException instead of assertions on rerun problems by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18858 <https://github.com/galaxyproject/galaxy/pull/18858>`_
* Fix wrong final state when init_from is used by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18871 <https://github.com/galaxyproject/galaxy/pull/18871>`_
* Fix history import when parent_hda not serialized by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18873 <https://github.com/galaxyproject/galaxy/pull/18873>`_
* Limit max number of items in dataproviders by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18881 <https://github.com/galaxyproject/galaxy/pull/18881>`_
* Allow cors in biom and q2view display applications by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18890 <https://github.com/galaxyproject/galaxy/pull/18890>`_
* Disable locking when opening h5 files, add missing ``with`` by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18976 <https://github.com/galaxyproject/galaxy/pull/18976>`_
* Optimize/fix sqlite hid update statement by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19106 <https://github.com/galaxyproject/galaxy/pull/19106>`_
* Prefer auto-decompressed datatype when picking conversion target  by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19162 <https://github.com/galaxyproject/galaxy/pull/19162>`_
* Fix various invocation export issues by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19215 <https://github.com/galaxyproject/galaxy/pull/19215>`_
* Fix bad merge conflict resolution by `@nsoranzo <https://github.com/nsoranzo>`_ in `#19297 <https://github.com/galaxyproject/galaxy/pull/19297>`_

=============
Other changes
=============

* Backport pod5 datatype by `@TomHarrop <https://github.com/TomHarrop>`_ in `#18507 <https://github.com/galaxyproject/galaxy/pull/18507>`_

-------------------
24.1.3 (2024-10-25)
-------------------


=========
Bug fixes
=========

* Replace busybox:ubuntu-14.04 image with busybox:1.36.1-glibc by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18428 <https://github.com/galaxyproject/galaxy/pull/18428>`_
* Improve workflow-related exception reporting by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18447 <https://github.com/galaxyproject/galaxy/pull/18447>`_
* Increase API robustness to invalid requests, improve compressed data serving by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18494 <https://github.com/galaxyproject/galaxy/pull/18494>`_
* Prevent job submission if input collection element is deleted by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18517 <https://github.com/galaxyproject/galaxy/pull/18517>`_
* Fix shared caches with extended metadata collection. by `@jmchilton <https://github.com/jmchilton>`_ in `#18520 <https://github.com/galaxyproject/galaxy/pull/18520>`_
* Also check dataset.deleted when determining if data can be displayed by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18547 <https://github.com/galaxyproject/galaxy/pull/18547>`_
* Fix for not-null in 'column_list' object by `@hujambo-dunia <https://github.com/hujambo-dunia>`_ in `#18553 <https://github.com/galaxyproject/galaxy/pull/18553>`_
* Fix h5ad metadata by `@nilchia <https://github.com/nilchia>`_ in `#18635 <https://github.com/galaxyproject/galaxy/pull/18635>`_
* Don't set file size to zero by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18653 <https://github.com/galaxyproject/galaxy/pull/18653>`_
* Make sure we set file size also for purged outputs by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18681 <https://github.com/galaxyproject/galaxy/pull/18681>`_
* Fix wrong extension on pick data output by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18798 <https://github.com/galaxyproject/galaxy/pull/18798>`_
* Fix copying workflow with subworkflow step for step that you own by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18802 <https://github.com/galaxyproject/galaxy/pull/18802>`_
* Make pylibmagic import optional by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18813 <https://github.com/galaxyproject/galaxy/pull/18813>`_
* Ignore converted datasets in invalid input states by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18850 <https://github.com/galaxyproject/galaxy/pull/18850>`_
* Fix discovered outputs with directory metadata and distributed object by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18855 <https://github.com/galaxyproject/galaxy/pull/18855>`_
* Raise MessageException instead of assertions on rerun problems by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18858 <https://github.com/galaxyproject/galaxy/pull/18858>`_
* Fix wrong final state when init_from is used by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18871 <https://github.com/galaxyproject/galaxy/pull/18871>`_
* Fix history import when parent_hda not serialized by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18873 <https://github.com/galaxyproject/galaxy/pull/18873>`_
* Limit max number of items in dataproviders by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18881 <https://github.com/galaxyproject/galaxy/pull/18881>`_
* Allow cors in biom and q2view display applications by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18890 <https://github.com/galaxyproject/galaxy/pull/18890>`_
* Disable locking when opening h5 files, add missing ``with`` by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18976 <https://github.com/galaxyproject/galaxy/pull/18976>`_

=============
Other changes
=============

* Backport pod5 datatype by `@TomHarrop <https://github.com/TomHarrop>`_ in `#18507 <https://github.com/galaxyproject/galaxy/pull/18507>`_

-------------------
24.1.2 (2024-09-25)
-------------------


=========
Bug fixes
=========

* Increase API robustness to invalid requests, improve compressed data serving by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18494 <https://github.com/galaxyproject/galaxy/pull/18494>`_
* Prevent job submission if input collection element is deleted by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18517 <https://github.com/galaxyproject/galaxy/pull/18517>`_
* Fix shared caches with extended metadata collection. by `@jmchilton <https://github.com/jmchilton>`_ in `#18520 <https://github.com/galaxyproject/galaxy/pull/18520>`_
* Also check dataset.deleted when determining if data can be displayed by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18547 <https://github.com/galaxyproject/galaxy/pull/18547>`_
* Fix for not-null in 'column_list' object by `@hujambo-dunia <https://github.com/hujambo-dunia>`_ in `#18553 <https://github.com/galaxyproject/galaxy/pull/18553>`_
* Fix h5ad metadata by `@nilchia <https://github.com/nilchia>`_ in `#18635 <https://github.com/galaxyproject/galaxy/pull/18635>`_
* Don't set file size to zero by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18653 <https://github.com/galaxyproject/galaxy/pull/18653>`_
* Make sure we set file size also for purged outputs by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18681 <https://github.com/galaxyproject/galaxy/pull/18681>`_
* Fix wrong extension on pick data output by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18798 <https://github.com/galaxyproject/galaxy/pull/18798>`_
* Fix copying workflow with subworkflow step for step that you own by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18802 <https://github.com/galaxyproject/galaxy/pull/18802>`_
* Make pylibmagic import optional by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18813 <https://github.com/galaxyproject/galaxy/pull/18813>`_
* Ignore converted datasets in invalid input states by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18850 <https://github.com/galaxyproject/galaxy/pull/18850>`_
* Fix discovered outputs with directory metadata and distributed object by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18855 <https://github.com/galaxyproject/galaxy/pull/18855>`_
* Raise MessageException instead of assertions on rerun problems by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18858 <https://github.com/galaxyproject/galaxy/pull/18858>`_
* Fix wrong final state when init_from is used by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18871 <https://github.com/galaxyproject/galaxy/pull/18871>`_
* Fix history import when parent_hda not serialized by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18873 <https://github.com/galaxyproject/galaxy/pull/18873>`_

=============
Other changes
=============

* Backport pod5 datatype by `@TomHarrop <https://github.com/TomHarrop>`_ in `#18507 <https://github.com/galaxyproject/galaxy/pull/18507>`_

-------------------
24.1.1 (2024-07-02)
-------------------


=========
Bug fixes
=========

* Fix syntax for SA2.0 by `@jdavcs <https://github.com/jdavcs>`_ in `#17663 <https://github.com/galaxyproject/galaxy/pull/17663>`_
* Fix empty usernames in database + bug in username generation by `@jdavcs <https://github.com/jdavcs>`_ in `#18379 <https://github.com/galaxyproject/galaxy/pull/18379>`_
* Fix `input_step_parameters` missing values that don't have a label by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#18405 <https://github.com/galaxyproject/galaxy/pull/18405>`_
* Improve workflow-related exception reporting by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18447 <https://github.com/galaxyproject/galaxy/pull/18447>`_

============
Enhancements
============

* Enable all-vs-all collection analysis patterns. by `@jmchilton <https://github.com/jmchilton>`_ in `#17366 <https://github.com/galaxyproject/galaxy/pull/17366>`_
* Visualizing workflow runs with an invocation graph view by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#17413 <https://github.com/galaxyproject/galaxy/pull/17413>`_
* Better display of estimated line numbers and add number of columns for tabular by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#17492 <https://github.com/galaxyproject/galaxy/pull/17492>`_
* Enable storage management by object store by `@jmchilton <https://github.com/jmchilton>`_ in `#17500 <https://github.com/galaxyproject/galaxy/pull/17500>`_
* Set minimal metadata also for empty bed datasets by `@wm75 <https://github.com/wm75>`_ in `#17586 <https://github.com/galaxyproject/galaxy/pull/17586>`_
* Type annotation improvements by `@nsoranzo <https://github.com/nsoranzo>`_ in `#17601 <https://github.com/galaxyproject/galaxy/pull/17601>`_
* Type annotation and CWL-related improvements by `@nsoranzo <https://github.com/nsoranzo>`_ in `#17630 <https://github.com/galaxyproject/galaxy/pull/17630>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#17653 <https://github.com/galaxyproject/galaxy/pull/17653>`_
* Code cleanups from ruff and pyupgrade by `@nsoranzo <https://github.com/nsoranzo>`_ in `#17654 <https://github.com/galaxyproject/galaxy/pull/17654>`_
* SQLAlchemy 2.0 by `@jdavcs <https://github.com/jdavcs>`_ in `#17778 <https://github.com/galaxyproject/galaxy/pull/17778>`_
* Outline use of type_annotation_map to fix mypy issues by `@jmchilton <https://github.com/jmchilton>`_ in `#17902 <https://github.com/galaxyproject/galaxy/pull/17902>`_
* Add `email` notifications channel by `@davelopez <https://github.com/davelopez>`_ in `#17914 <https://github.com/galaxyproject/galaxy/pull/17914>`_
* Model edits and bug fixes by `@jdavcs <https://github.com/jdavcs>`_ in `#17922 <https://github.com/galaxyproject/galaxy/pull/17922>`_
* Model typing and SA2.0 follow-up by `@jdavcs <https://github.com/jdavcs>`_ in `#17958 <https://github.com/galaxyproject/galaxy/pull/17958>`_
* Enable ``warn_unused_ignores`` mypy option by `@nsoranzo <https://github.com/nsoranzo>`_ in `#17991 <https://github.com/galaxyproject/galaxy/pull/17991>`_
* Add galaxy to user agent by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18003 <https://github.com/galaxyproject/galaxy/pull/18003>`_
* Refactor galaxy.files plugin loading + config handling. by `@jmchilton <https://github.com/jmchilton>`_ in `#18049 <https://github.com/galaxyproject/galaxy/pull/18049>`_
* Add stronger type annotations in file sources + refactoring by `@davelopez <https://github.com/davelopez>`_ in `#18050 <https://github.com/galaxyproject/galaxy/pull/18050>`_
* Add support for additional media types by `@arash77 <https://github.com/arash77>`_ in `#18054 <https://github.com/galaxyproject/galaxy/pull/18054>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#18063 <https://github.com/galaxyproject/galaxy/pull/18063>`_
* Enable flake8-implicit-str-concat ruff rules by `@nsoranzo <https://github.com/nsoranzo>`_ in `#18067 <https://github.com/galaxyproject/galaxy/pull/18067>`_
* Script for deleting userless histories from database + testing + drop unused model testing code by `@jdavcs <https://github.com/jdavcs>`_ in `#18079 <https://github.com/galaxyproject/galaxy/pull/18079>`_
* Add Net datatype by `@martenson <https://github.com/martenson>`_ in `#18080 <https://github.com/galaxyproject/galaxy/pull/18080>`_
* Empower users to bring their own storage and file sources by `@jmchilton <https://github.com/jmchilton>`_ in `#18127 <https://github.com/galaxyproject/galaxy/pull/18127>`_
* Harden User Object Store and File Source Creation by `@jmchilton <https://github.com/jmchilton>`_ in `#18172 <https://github.com/galaxyproject/galaxy/pull/18172>`_
* Update db revision 24.1 release tags by `@jdavcs <https://github.com/jdavcs>`_ in `#18183 <https://github.com/galaxyproject/galaxy/pull/18183>`_
* Tighten axt sniffer by `@martenson <https://github.com/martenson>`_ in `#18204 <https://github.com/galaxyproject/galaxy/pull/18204>`_
* More structured indexing for user data objects. by `@jmchilton <https://github.com/jmchilton>`_ in `#18291 <https://github.com/galaxyproject/galaxy/pull/18291>`_

=============
Other changes
=============

* Chore: remove repetitive words by `@tianzedavid <https://github.com/tianzedavid>`_ in `#18076 <https://github.com/galaxyproject/galaxy/pull/18076>`_
* Fix import broken with forward merge by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18152 <https://github.com/galaxyproject/galaxy/pull/18152>`_

-------------------
24.0.3 (2024-06-28)
-------------------


=========
Bug fixes
=========

* Downgrade count lines error to warning by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18175 <https://github.com/galaxyproject/galaxy/pull/18175>`_
* Don't set dataset peek for errored jobs by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18231 <https://github.com/galaxyproject/galaxy/pull/18231>`_
* Transparently open compressed files in DatasetDataProvider by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18248 <https://github.com/galaxyproject/galaxy/pull/18248>`_
* Raise exception when extracting dataset from collection without datasets by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18249 <https://github.com/galaxyproject/galaxy/pull/18249>`_
* Set page importable to false when serializing by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18263 <https://github.com/galaxyproject/galaxy/pull/18263>`_
* Fix first_dataset_element type hint by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18284 <https://github.com/galaxyproject/galaxy/pull/18284>`_
* Do not copy purged outputs to object store by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18342 <https://github.com/galaxyproject/galaxy/pull/18342>`_
* Fix user's private role can be missing by `@davelopez <https://github.com/davelopez>`_ in `#18381 <https://github.com/galaxyproject/galaxy/pull/18381>`_
* Assign default ``data`` extension on discovered collection output  by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18389 <https://github.com/galaxyproject/galaxy/pull/18389>`_

=============
Other changes
=============

* Replace busybox:ubuntu-14.04 image with busybox:1.36.1-glibc by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18428 <https://github.com/galaxyproject/galaxy/pull/18428>`_

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

* Always serialize element_count and populated when listing contents by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17890 <https://github.com/galaxyproject/galaxy/pull/17890>`_
* Fix deadlock that can occur when changing job state by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17896 <https://github.com/galaxyproject/galaxy/pull/17896>`_
* Fix tool form building if select filters from unavailable dataset metadata by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17930 <https://github.com/galaxyproject/galaxy/pull/17930>`_
* Fix ``InvalidRequestError: Can't operate on closed transaction inside context manager.  Please complete the context manager before emitting further commands.`` by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17932 <https://github.com/galaxyproject/galaxy/pull/17932>`_
* Never fail dataset serialization if display_peek fails by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17937 <https://github.com/galaxyproject/galaxy/pull/17937>`_
* Fix output datatype when uncompressing a dataset with incorrect datatype by `@nsoranzo <https://github.com/nsoranzo>`_ in `#17944 <https://github.com/galaxyproject/galaxy/pull/17944>`_
* Use or copy StoredWorkflow when copying step by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17988 <https://github.com/galaxyproject/galaxy/pull/17988>`_
* Raise ``MessageException`` when report references invalid workflow output by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18009 <https://github.com/galaxyproject/galaxy/pull/18009>`_
* Fix tag regex pattern by `@jdavcs <https://github.com/jdavcs>`_ in `#18025 <https://github.com/galaxyproject/galaxy/pull/18025>`_
* Fix History Dataset Association creation so that hid is always set by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18036 <https://github.com/galaxyproject/galaxy/pull/18036>`_
* Fix history export with missing dataset hids by `@davelopez <https://github.com/davelopez>`_ in `#18052 <https://github.com/galaxyproject/galaxy/pull/18052>`_
* Fix comments lost on import by `@ElectronicBlueberry <https://github.com/ElectronicBlueberry>`_ in `#18060 <https://github.com/galaxyproject/galaxy/pull/18060>`_
* Fix history update time after bulk operation by `@davelopez <https://github.com/davelopez>`_ in `#18068 <https://github.com/galaxyproject/galaxy/pull/18068>`_

-------------------
24.0.0 (2024-04-02)
-------------------


=========
Bug fixes
=========

* Fix for converter tests by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#17188 <https://github.com/galaxyproject/galaxy/pull/17188>`_
* correct dbkey for minerva display app by `@hexylena <https://github.com/hexylena>`_ in `#17196 <https://github.com/galaxyproject/galaxy/pull/17196>`_
* Fix invocation serialization if no state was set by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17278 <https://github.com/galaxyproject/galaxy/pull/17278>`_
* Fix quotas ID encoding by `@davelopez <https://github.com/davelopez>`_ in `#17335 <https://github.com/galaxyproject/galaxy/pull/17335>`_
* Fix model store exports that include implicit conversions.  by `@jmchilton <https://github.com/jmchilton>`_ in `#17346 <https://github.com/galaxyproject/galaxy/pull/17346>`_
* Fix bug: create new PSAAssociation if not in database by `@jdavcs <https://github.com/jdavcs>`_ in `#17516 <https://github.com/galaxyproject/galaxy/pull/17516>`_
* Fix social_core methods by `@jdavcs <https://github.com/jdavcs>`_ in `#17530 <https://github.com/galaxyproject/galaxy/pull/17530>`_
* Fix ancient bug: incorrect usage of func.coalesce in User model by `@jdavcs <https://github.com/jdavcs>`_ in `#17577 <https://github.com/galaxyproject/galaxy/pull/17577>`_
* Account for newlines in CIF Datatype sniffer by `@patrick-austin <https://github.com/patrick-austin>`_ in `#17582 <https://github.com/galaxyproject/galaxy/pull/17582>`_
* Anticipate PendingRollbackError in ``check_database_connection`` by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17598 <https://github.com/galaxyproject/galaxy/pull/17598>`_
* Add basic model import attribute validation by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17628 <https://github.com/galaxyproject/galaxy/pull/17628>`_
* More efficient change_state queries, maybe fix deadlock by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17632 <https://github.com/galaxyproject/galaxy/pull/17632>`_
* Npz sniffing: do not read the whole file by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#17672 <https://github.com/galaxyproject/galaxy/pull/17672>`_
* Assert that at least one file in npz zipfile ends with .npy by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17679 <https://github.com/galaxyproject/galaxy/pull/17679>`_
* Workflow Comment Indexing by `@ElectronicBlueberry <https://github.com/ElectronicBlueberry>`_ in `#17700 <https://github.com/galaxyproject/galaxy/pull/17700>`_
* Fix source history update_time being updated when importing a public history by `@jmchilton <https://github.com/jmchilton>`_ in `#17728 <https://github.com/galaxyproject/galaxy/pull/17728>`_
* Also set extension and metadata on copies of job outputs when finishing job by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17777 <https://github.com/galaxyproject/galaxy/pull/17777>`_
* Defer job attributes that are usually not needed by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17795 <https://github.com/galaxyproject/galaxy/pull/17795>`_
* Fix change_datatype PJA for dynamic collections  by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17803 <https://github.com/galaxyproject/galaxy/pull/17803>`_
* Simplify nested collection joins by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17817 <https://github.com/galaxyproject/galaxy/pull/17817>`_
* Fix very slow user data table query by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17830 <https://github.com/galaxyproject/galaxy/pull/17830>`_
* Update db revision 24.0 release tags by `@jdavcs <https://github.com/jdavcs>`_ in `#17834 <https://github.com/galaxyproject/galaxy/pull/17834>`_
* Minor refactor of query building logic for readability by `@jdavcs <https://github.com/jdavcs>`_ in `#17835 <https://github.com/galaxyproject/galaxy/pull/17835>`_
* Fix user login when duplicate UserRoleAssociation exists by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17854 <https://github.com/galaxyproject/galaxy/pull/17854>`_

============
Enhancements
============

* Make columns types an empty list for empty tabular data  by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#13918 <https://github.com/galaxyproject/galaxy/pull/13918>`_
* port invocation API to fastapi by `@martenson <https://github.com/martenson>`_ in `#16707 <https://github.com/galaxyproject/galaxy/pull/16707>`_
* SQLAlchemy 2.0 upgrades (part 5) by `@jdavcs <https://github.com/jdavcs>`_ in `#16932 <https://github.com/galaxyproject/galaxy/pull/16932>`_
* Python 3.8 as minimum by `@mr-c <https://github.com/mr-c>`_ in `#16954 <https://github.com/galaxyproject/galaxy/pull/16954>`_
* Expose more tool information / navigability in UI. by `@jmchilton <https://github.com/jmchilton>`_ in `#17105 <https://github.com/galaxyproject/galaxy/pull/17105>`_
* Add support for (fast5.tar).xz binary compressed files by `@tuncK <https://github.com/tuncK>`_ in `#17106 <https://github.com/galaxyproject/galaxy/pull/17106>`_
* SA2.0 updates: handling "object is being merged into a Session along the backref cascade path" by `@jdavcs <https://github.com/jdavcs>`_ in `#17122 <https://github.com/galaxyproject/galaxy/pull/17122>`_
* Towards SQLAlchemy 2.0: fix last cases of RemovedIn20Warning by `@jdavcs <https://github.com/jdavcs>`_ in `#17132 <https://github.com/galaxyproject/galaxy/pull/17132>`_
* Create pydantic model for the return of show operation -  get: `/api/jobs/{job_id}`  by `@heisner-tillman <https://github.com/heisner-tillman>`_ in `#17153 <https://github.com/galaxyproject/galaxy/pull/17153>`_
* Much simpler default dataset permissions for typical users. by `@jmchilton <https://github.com/jmchilton>`_ in `#17166 <https://github.com/galaxyproject/galaxy/pull/17166>`_
* Add future=True flag to SA engine by `@jdavcs <https://github.com/jdavcs>`_ in `#17174 <https://github.com/galaxyproject/galaxy/pull/17174>`_
* Add future=True flag to SA session by `@jdavcs <https://github.com/jdavcs>`_ in `#17179 <https://github.com/galaxyproject/galaxy/pull/17179>`_
* Vueifiy History Grids by `@guerler <https://github.com/guerler>`_ in `#17219 <https://github.com/galaxyproject/galaxy/pull/17219>`_
* Convert sample object store configuration to YAML and support configuring inline by `@natefoo <https://github.com/natefoo>`_ in `#17222 <https://github.com/galaxyproject/galaxy/pull/17222>`_
* Migrate models to pydantic 2 by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17262 <https://github.com/galaxyproject/galaxy/pull/17262>`_
* API endpoint that allows "changing" the objectstore for "safe" scenarios.  by `@jmchilton <https://github.com/jmchilton>`_ in `#17329 <https://github.com/galaxyproject/galaxy/pull/17329>`_
* Enable ``warn_unreachable`` mypy option by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17365 <https://github.com/galaxyproject/galaxy/pull/17365>`_
* Fix type annotation of code using XML etree by `@nsoranzo <https://github.com/nsoranzo>`_ in `#17367 <https://github.com/galaxyproject/galaxy/pull/17367>`_
* Add explicit cache_ok attribute to JSONType subclass by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17376 <https://github.com/galaxyproject/galaxy/pull/17376>`_
* More specific type annotation for ``BaseJobExec.parse_status()`` by `@nsoranzo <https://github.com/nsoranzo>`_ in `#17381 <https://github.com/galaxyproject/galaxy/pull/17381>`_
* Update to black 2024 stable style by `@nsoranzo <https://github.com/nsoranzo>`_ in `#17391 <https://github.com/galaxyproject/galaxy/pull/17391>`_
* Allow using tool data bundles as inputs to reference data select parameters by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17435 <https://github.com/galaxyproject/galaxy/pull/17435>`_
* UI for "relocating" a dataset to a new object store (when safe) by `@jmchilton <https://github.com/jmchilton>`_ in `#17437 <https://github.com/galaxyproject/galaxy/pull/17437>`_
* Allow filtering history datasets by object store ID and quota source. by `@jmchilton <https://github.com/jmchilton>`_ in `#17460 <https://github.com/galaxyproject/galaxy/pull/17460>`_
* Faster FASTA and FASTQ metadata setting by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#17462 <https://github.com/galaxyproject/galaxy/pull/17462>`_
* Feature SBOL datatypes by `@guillaume-gricourt <https://github.com/guillaume-gricourt>`_ in `#17482 <https://github.com/galaxyproject/galaxy/pull/17482>`_
* Display workflow invocation counts. by `@jmchilton <https://github.com/jmchilton>`_ in `#17488 <https://github.com/galaxyproject/galaxy/pull/17488>`_
* add npy datatype by `@astrovsky01 <https://github.com/astrovsky01>`_ in `#17517 <https://github.com/galaxyproject/galaxy/pull/17517>`_
* Enhance Avivator display app to support regular Tiffs by `@davelopez <https://github.com/davelopez>`_ in `#17554 <https://github.com/galaxyproject/galaxy/pull/17554>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#17580 <https://github.com/galaxyproject/galaxy/pull/17580>`_
* Add migrations revision identifier for 24.0 by `@jdavcs <https://github.com/jdavcs>`_ in `#17589 <https://github.com/galaxyproject/galaxy/pull/17589>`_

-------------------
23.2.1 (2024-02-21)
-------------------


=========
Bug fixes
=========

* Rename to_dict to populate in FormDefintion to fix bug by `@jdavcs <https://github.com/jdavcs>`_ in `#16553 <https://github.com/galaxyproject/galaxy/pull/16553>`_
* MINERVA display application: enable cors, add for tabular by `@hexylena <https://github.com/hexylena>`_ in `#16737 <https://github.com/galaxyproject/galaxy/pull/16737>`_
* Use AlignedSegment.to_string by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16803 <https://github.com/galaxyproject/galaxy/pull/16803>`_
* Ruff and flake8 fixes by `@nsoranzo <https://github.com/nsoranzo>`_ in `#16884 <https://github.com/galaxyproject/galaxy/pull/16884>`_
* prep for updated h5py and typos by `@mr-c <https://github.com/mr-c>`_ in `#16963 <https://github.com/galaxyproject/galaxy/pull/16963>`_
* Fix cardinality violation error: subquery returns multiple results by `@jdavcs <https://github.com/jdavcs>`_ in `#17224 <https://github.com/galaxyproject/galaxy/pull/17224>`_
* Fix Display Application link generation by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17227 <https://github.com/galaxyproject/galaxy/pull/17227>`_
* Display application fixes and tests by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17233 <https://github.com/galaxyproject/galaxy/pull/17233>`_
* Rollback invalidated transaction by `@jdavcs <https://github.com/jdavcs>`_ in `#17280 <https://github.com/galaxyproject/galaxy/pull/17280>`_
* Set metadata states on dataset association, not dataset by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17474 <https://github.com/galaxyproject/galaxy/pull/17474>`_
* Provide working routes.url_for every ASGI request by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17497 <https://github.com/galaxyproject/galaxy/pull/17497>`_

============
Enhancements
============

* Implement default locations for data and collection parameters. by `@jmchilton <https://github.com/jmchilton>`_ in `#14955 <https://github.com/galaxyproject/galaxy/pull/14955>`_
* Display beginning of non-text files as text instead of triggering a download by `@SergeyYakubov <https://github.com/SergeyYakubov>`_ in `#15447 <https://github.com/galaxyproject/galaxy/pull/15447>`_
* Tool Shed 2.0 by `@jmchilton <https://github.com/jmchilton>`_ in `#15639 <https://github.com/galaxyproject/galaxy/pull/15639>`_
* Limit number of celery task executions per second per user by `@claudiofr <https://github.com/claudiofr>`_ in `#16232 <https://github.com/galaxyproject/galaxy/pull/16232>`_
* Delete non-terminal jobs and subworkflow invocations when cancelling invocation by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16252 <https://github.com/galaxyproject/galaxy/pull/16252>`_
* Towards SQLAlchemy 2.0 (upgrades to SA Core usage) by `@jdavcs <https://github.com/jdavcs>`_ in `#16264 <https://github.com/galaxyproject/galaxy/pull/16264>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#16409 <https://github.com/galaxyproject/galaxy/pull/16409>`_
* Towards SQLAlchemy 2.0 (upgrades to SA ORM usage in /test) by `@jdavcs <https://github.com/jdavcs>`_ in `#16431 <https://github.com/galaxyproject/galaxy/pull/16431>`_
* SQLAlchemy 2.0 upgrades to ORM usage in /lib by `@jdavcs <https://github.com/jdavcs>`_ in `#16434 <https://github.com/galaxyproject/galaxy/pull/16434>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#16436 <https://github.com/galaxyproject/galaxy/pull/16436>`_
* Implement datatype upload warnings by `@jmchilton <https://github.com/jmchilton>`_ in `#16564 <https://github.com/galaxyproject/galaxy/pull/16564>`_
* Support new genome browser chain file format by `@claudiofr <https://github.com/claudiofr>`_ in `#16576 <https://github.com/galaxyproject/galaxy/pull/16576>`_
* Workflow Comments 💬 by `@ElectronicBlueberry <https://github.com/ElectronicBlueberry>`_ in `#16612 <https://github.com/galaxyproject/galaxy/pull/16612>`_
* Bump samtools converters by `@bernt-matthias <https://github.com/bernt-matthias>`_ in `#16668 <https://github.com/galaxyproject/galaxy/pull/16668>`_
* Misc. edits/refactorings to session handling  by `@jdavcs <https://github.com/jdavcs>`_ in `#16712 <https://github.com/galaxyproject/galaxy/pull/16712>`_
* SQLAlchemy 2.0 upgrades (part 2) by `@jdavcs <https://github.com/jdavcs>`_ in `#16724 <https://github.com/galaxyproject/galaxy/pull/16724>`_
* Migrate `collection elements` store to Pinia by `@davelopez <https://github.com/davelopez>`_ in `#16725 <https://github.com/galaxyproject/galaxy/pull/16725>`_
* Reset autocommit to False by `@jdavcs <https://github.com/jdavcs>`_ in `#16745 <https://github.com/galaxyproject/galaxy/pull/16745>`_
* Drop legacy server-side search by `@jdavcs <https://github.com/jdavcs>`_ in `#16755 <https://github.com/galaxyproject/galaxy/pull/16755>`_
* Optimize iteration in DatasetInstance model + SA2.0 fix by `@jdavcs <https://github.com/jdavcs>`_ in `#16776 <https://github.com/galaxyproject/galaxy/pull/16776>`_
* Migrate a part of the jobs API to Fast API by `@heisner-tillman <https://github.com/heisner-tillman>`_ in `#16778 <https://github.com/galaxyproject/galaxy/pull/16778>`_
* Replace file_name property with get_file_name function by `@SergeyYakubov <https://github.com/SergeyYakubov>`_ in `#16783 <https://github.com/galaxyproject/galaxy/pull/16783>`_
* Updated path-based interactive tools with entry point path injection, support for ITs with relative links, shortened URLs, doc and config updates including Podman job_conf by `@sveinugu <https://github.com/sveinugu>`_ in `#16795 <https://github.com/galaxyproject/galaxy/pull/16795>`_
* Allow partial matches in workflow name tag search and search all tags for unquoted query by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#16860 <https://github.com/galaxyproject/galaxy/pull/16860>`_
* Vueify Visualizations Grid by `@guerler <https://github.com/guerler>`_ in `#16892 <https://github.com/galaxyproject/galaxy/pull/16892>`_
* Standardize to W3C naming for color. by `@dannon <https://github.com/dannon>`_ in `#16949 <https://github.com/galaxyproject/galaxy/pull/16949>`_
* Move and re-use persist_extra_files by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16955 <https://github.com/galaxyproject/galaxy/pull/16955>`_
* Fix invocation report to target correct workflow version. by `@jmchilton <https://github.com/jmchilton>`_ in `#17008 <https://github.com/galaxyproject/galaxy/pull/17008>`_
* optimize object store cache operations by `@SergeyYakubov <https://github.com/SergeyYakubov>`_ in `#17025 <https://github.com/galaxyproject/galaxy/pull/17025>`_
* Use python-isal for fast zip deflate compression in rocrate export by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17342 <https://github.com/galaxyproject/galaxy/pull/17342>`_
* Add magres datatype by `@martenson <https://github.com/martenson>`_ in `#17499 <https://github.com/galaxyproject/galaxy/pull/17499>`_

=============
Other changes
=============

* Merge 23.1 into dev by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16534 <https://github.com/galaxyproject/galaxy/pull/16534>`_
* Merge release_23.1 into dev by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16768 <https://github.com/galaxyproject/galaxy/pull/16768>`_
* Create db head merge revision. by `@dannon <https://github.com/dannon>`_ in `#16838 <https://github.com/galaxyproject/galaxy/pull/16838>`_
* merge release_23.1 into dev by `@martenson <https://github.com/martenson>`_ in `#16933 <https://github.com/galaxyproject/galaxy/pull/16933>`_
* Minor clarification/typo fix in datatypes.data by `@dannon <https://github.com/dannon>`_ in `#16993 <https://github.com/galaxyproject/galaxy/pull/16993>`_
* Fix `.file_name` access in merge forward by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17097 <https://github.com/galaxyproject/galaxy/pull/17097>`_
* Backport model store fixes by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17439 <https://github.com/galaxyproject/galaxy/pull/17439>`_
* Fix succces typo by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17481 <https://github.com/galaxyproject/galaxy/pull/17481>`_

-------------------
23.1.4 (2024-01-04)
-------------------


=========
Bug fixes
=========

* Fix User.current_galaxy_session by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17232 <https://github.com/galaxyproject/galaxy/pull/17232>`_

=============
Other changes
=============

* Backport #17188: Fix for converter tests by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17231 <https://github.com/galaxyproject/galaxy/pull/17231>`_

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

* Fix extra files path handling by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16541 <https://github.com/galaxyproject/galaxy/pull/16541>`_
* Don't fail invocation message without dependent_workflow_step_id by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16628 <https://github.com/galaxyproject/galaxy/pull/16628>`_

-------------------
23.0.5 (2023-07-29)
-------------------


=========
Bug fixes
=========

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
