History
-------

.. to_doc

-----------
24.2.5.dev0
-----------



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
