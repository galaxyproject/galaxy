History
-------

.. to_doc

---------
24.2.dev0
---------



-------------------
24.1.2 (2024-09-25)
-------------------


=========
Bug fixes
=========

* Handle error when workflow is unowned in Invocation view by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#18730 <https://github.com/galaxyproject/galaxy/pull/18730>`_
* Fix datatype validation of newly built collection by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18738 <https://github.com/galaxyproject/galaxy/pull/18738>`_
* Fix job summary for optional unset job data inputs by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18754 <https://github.com/galaxyproject/galaxy/pull/18754>`_
* Fix ``TypeError`` from Pydantic 2.9.0 by `@nsoranzo <https://github.com/nsoranzo>`_ in `#18788 <https://github.com/galaxyproject/galaxy/pull/18788>`_
* Fix wrong extension on pick data output by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18798 <https://github.com/galaxyproject/galaxy/pull/18798>`_
* Make all fields optional for HelpForumPost by `@davelopez <https://github.com/davelopez>`_ in `#18839 <https://github.com/galaxyproject/galaxy/pull/18839>`_

============
Enhancements
============

* Include workflow invocation id in exception logs by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18594 <https://github.com/galaxyproject/galaxy/pull/18594>`_

-------------------
24.1.1 (2024-07-02)
-------------------


============
Enhancements
============

* Visualizing workflow runs with an invocation graph view by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#17413 <https://github.com/galaxyproject/galaxy/pull/17413>`_
* Add `email` notifications channel by `@davelopez <https://github.com/davelopez>`_ in `#17914 <https://github.com/galaxyproject/galaxy/pull/17914>`_
* Enable ``warn_unused_ignores`` mypy option by `@nsoranzo <https://github.com/nsoranzo>`_ in `#17991 <https://github.com/galaxyproject/galaxy/pull/17991>`_
* Add pagination support to Files Source plugins by `@davelopez <https://github.com/davelopez>`_ in `#18059 <https://github.com/galaxyproject/galaxy/pull/18059>`_
* Enable flake8-implicit-str-concat ruff rules by `@nsoranzo <https://github.com/nsoranzo>`_ in `#18067 <https://github.com/galaxyproject/galaxy/pull/18067>`_
* Empower users to bring their own storage and file sources by `@jmchilton <https://github.com/jmchilton>`_ in `#18127 <https://github.com/galaxyproject/galaxy/pull/18127>`_
* Display DOIs in Archived Histories by `@davelopez <https://github.com/davelopez>`_ in `#18134 <https://github.com/galaxyproject/galaxy/pull/18134>`_
* Allow running and editing workflows for specific versions by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#18378 <https://github.com/galaxyproject/galaxy/pull/18378>`_

-------------------
24.0.3 (2024-06-28)
-------------------


=========
Bug fixes
=========

* do not expand datasets that are known to be inaccessible by `@martenson <https://github.com/martenson>`_ in `#17818 <https://github.com/galaxyproject/galaxy/pull/17818>`_
* Allow purge query param, deprecate purge body param by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18105 <https://github.com/galaxyproject/galaxy/pull/18105>`_
* Fix deprecated `deprecated` argument by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18119 <https://github.com/galaxyproject/galaxy/pull/18119>`_
* Fix users API serialization when listing users by `@davelopez <https://github.com/davelopez>`_ in `#18329 <https://github.com/galaxyproject/galaxy/pull/18329>`_
* Fix update group API payload model by `@davelopez <https://github.com/davelopez>`_ in `#18374 <https://github.com/galaxyproject/galaxy/pull/18374>`_
* Serialize purged flag for datasets in collections by `@davelopez <https://github.com/davelopez>`_ in `#18420 <https://github.com/galaxyproject/galaxy/pull/18420>`_

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

* Fix tag regex pattern by `@jdavcs <https://github.com/jdavcs>`_ in `#18025 <https://github.com/galaxyproject/galaxy/pull/18025>`_
* Fix History Dataset Association creation so that hid is always set by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18036 <https://github.com/galaxyproject/galaxy/pull/18036>`_

-------------------
24.0.0 (2024-04-02)
-------------------


=========
Bug fixes
=========

* Fix Workflow Comment Model for Pydantic 2 by `@ElectronicBlueberry <https://github.com/ElectronicBlueberry>`_ in `#17296 <https://github.com/galaxyproject/galaxy/pull/17296>`_
* Add basic model import attribute validation by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17628 <https://github.com/galaxyproject/galaxy/pull/17628>`_
* Make latest_workflow_uuid optional by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17629 <https://github.com/galaxyproject/galaxy/pull/17629>`_
* Fix workflow person validation by `@dannon <https://github.com/dannon>`_ in `#17636 <https://github.com/galaxyproject/galaxy/pull/17636>`_
* Make WorkflowInput label, value and uuid optional by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17638 <https://github.com/galaxyproject/galaxy/pull/17638>`_
* Fix step type serialization for StoredWorkflowDetailed models by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17716 <https://github.com/galaxyproject/galaxy/pull/17716>`_
* Fix input parameter step type by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17767 <https://github.com/galaxyproject/galaxy/pull/17767>`_
* Fix optional types in Help Forum API by `@davelopez <https://github.com/davelopez>`_ in `#17832 <https://github.com/galaxyproject/galaxy/pull/17832>`_
* Fix archived histories mixing with active in histories list by `@davelopez <https://github.com/davelopez>`_ in `#17856 <https://github.com/galaxyproject/galaxy/pull/17856>`_

============
Enhancements
============

* port invocation API to fastapi by `@martenson <https://github.com/martenson>`_ in `#16707 <https://github.com/galaxyproject/galaxy/pull/16707>`_
* Python 3.8 as minimum by `@mr-c <https://github.com/mr-c>`_ in `#16954 <https://github.com/galaxyproject/galaxy/pull/16954>`_
* Toward declarative help for Galaxy markdown directives. by `@jmchilton <https://github.com/jmchilton>`_ in `#16979 <https://github.com/galaxyproject/galaxy/pull/16979>`_
* Create pydantic model for the return of show operation -  get: `/api/jobs/{job_id}`  by `@heisner-tillman <https://github.com/heisner-tillman>`_ in `#17153 <https://github.com/galaxyproject/galaxy/pull/17153>`_
* Vueifiy History Grids by `@guerler <https://github.com/guerler>`_ in `#17219 <https://github.com/galaxyproject/galaxy/pull/17219>`_
* Refactor two of the missing invocation routes to FastAPI by `@heisner-tillman <https://github.com/heisner-tillman>`_ in `#17237 <https://github.com/galaxyproject/galaxy/pull/17237>`_
* Migrate models to pydantic 2 by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17262 <https://github.com/galaxyproject/galaxy/pull/17262>`_
* Combines legacy qv-pattern and advanced filter pattern in history index endpoint by `@guerler <https://github.com/guerler>`_ in `#17368 <https://github.com/galaxyproject/galaxy/pull/17368>`_
* Update to black 2024 stable style by `@nsoranzo <https://github.com/nsoranzo>`_ in `#17391 <https://github.com/galaxyproject/galaxy/pull/17391>`_
* Allow using tool data bundles as inputs to reference data select parameters by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17435 <https://github.com/galaxyproject/galaxy/pull/17435>`_
* Refactor Workflow API routes - Part 1 by `@heisner-tillman <https://github.com/heisner-tillman>`_ in `#17463 <https://github.com/galaxyproject/galaxy/pull/17463>`_
* Consolidate resource grids into tab views by `@guerler <https://github.com/guerler>`_ in `#17487 <https://github.com/galaxyproject/galaxy/pull/17487>`_
* Display workflow invocation counts. by `@jmchilton <https://github.com/jmchilton>`_ in `#17488 <https://github.com/galaxyproject/galaxy/pull/17488>`_
* Filter out subworkflow invocations by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17558 <https://github.com/galaxyproject/galaxy/pull/17558>`_
* Restore histories API behavior for `keys` query parameter by `@davelopez <https://github.com/davelopez>`_ in `#17779 <https://github.com/galaxyproject/galaxy/pull/17779>`_
* Fix datasets API custom keys encoding by `@davelopez <https://github.com/davelopez>`_ in `#17793 <https://github.com/galaxyproject/galaxy/pull/17793>`_

-------------------
23.2.1 (2024-02-21)
-------------------

First release
