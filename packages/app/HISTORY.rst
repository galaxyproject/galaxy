History
-------

.. to_doc

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

* 
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

* 
* 
* Fix ``Text File Busy`` errors at the source by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16212 <https://github.com/galaxyproject/galaxy/pull/16212>`_

============
Enhancements
============

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
* Startup fix when tool removed between reboot by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16175 <https://github.com/galaxyproject/galaxy/pull/16175>`_

-------------------
20.9.0 (2020-10-15)
-------------------

* First release from the 20.09 branch of Galaxy.

-------------------
20.5.0 (2020-07-04)
-------------------

* First release from the 20.05 branch of Galaxy.
