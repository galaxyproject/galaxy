History
-------

.. to_doc

---------
24.2.dev0
---------



-------------------
24.1.1 (2024-07-02)
-------------------


=========
Bug fixes
=========

* Fix (I think) a transiently failing selenium error. by `@jmchilton <https://github.com/jmchilton>`_ in `#18065 <https://github.com/galaxyproject/galaxy/pull/18065>`_

============
Enhancements
============

* Add admin activity to activity bar by `@guerler <https://github.com/guerler>`_ in `#17877 <https://github.com/galaxyproject/galaxy/pull/17877>`_
* Add galaxy to user agent by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18003 <https://github.com/galaxyproject/galaxy/pull/18003>`_
* Consolidate Visualization container, avoid using default iframe by `@guerler <https://github.com/guerler>`_ in `#18016 <https://github.com/galaxyproject/galaxy/pull/18016>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#18063 <https://github.com/galaxyproject/galaxy/pull/18063>`_
* Empower users to bring their own storage and file sources by `@jmchilton <https://github.com/jmchilton>`_ in `#18127 <https://github.com/galaxyproject/galaxy/pull/18127>`_

-------------------
24.0.3 (2024-06-28)
-------------------

No recorded changes since last release

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

* Set from_tool_form: true when saving new workflow by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17972 <https://github.com/galaxyproject/galaxy/pull/17972>`_

-------------------
24.0.0 (2024-04-02)
-------------------


=========
Bug fixes
=========

* Update tour testing selector usage. by `@jmchilton <https://github.com/jmchilton>`_ in `#14005 <https://github.com/galaxyproject/galaxy/pull/14005>`_
* Fix history filters taking up space in `GridList` by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#17652 <https://github.com/galaxyproject/galaxy/pull/17652>`_

============
Enhancements
============

* New Workflow List and Card View by `@itisAliRH <https://github.com/itisAliRH>`_ in `#16607 <https://github.com/galaxyproject/galaxy/pull/16607>`_
* Python 3.8 as minimum by `@mr-c <https://github.com/mr-c>`_ in `#16954 <https://github.com/galaxyproject/galaxy/pull/16954>`_
* Vueifiy History Grids by `@guerler <https://github.com/guerler>`_ in `#17219 <https://github.com/galaxyproject/galaxy/pull/17219>`_
* Adds delete, purge and undelete batch operations to History Grid by `@guerler <https://github.com/guerler>`_ in `#17282 <https://github.com/galaxyproject/galaxy/pull/17282>`_
* Custom Multiselect by `@ElectronicBlueberry <https://github.com/ElectronicBlueberry>`_ in `#17331 <https://github.com/galaxyproject/galaxy/pull/17331>`_
* Enable ``warn_unreachable`` mypy option by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17365 <https://github.com/galaxyproject/galaxy/pull/17365>`_
* Update to black 2024 stable style by `@nsoranzo <https://github.com/nsoranzo>`_ in `#17391 <https://github.com/galaxyproject/galaxy/pull/17391>`_
* Adds published histories to grid list by `@guerler <https://github.com/guerler>`_ in `#17449 <https://github.com/galaxyproject/galaxy/pull/17449>`_
* Consolidate resource grids into tab views by `@guerler <https://github.com/guerler>`_ in `#17487 <https://github.com/galaxyproject/galaxy/pull/17487>`_

-------------------
23.2.1 (2024-02-21)
-------------------


============
Enhancements
============

* Vueify Data Uploader by `@guerler <https://github.com/guerler>`_ in `#16472 <https://github.com/galaxyproject/galaxy/pull/16472>`_
* Create reusable `FilterMenu` with advanced options by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#16522 <https://github.com/galaxyproject/galaxy/pull/16522>`_
* Implement datatype upload warnings by `@jmchilton <https://github.com/jmchilton>`_ in `#16564 <https://github.com/galaxyproject/galaxy/pull/16564>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#16577 <https://github.com/galaxyproject/galaxy/pull/16577>`_
* Vueify Tool Form Data Selector by `@guerler <https://github.com/guerler>`_ in `#16578 <https://github.com/galaxyproject/galaxy/pull/16578>`_
* Workflow Comments 💬 by `@ElectronicBlueberry <https://github.com/ElectronicBlueberry>`_ in `#16612 <https://github.com/galaxyproject/galaxy/pull/16612>`_
* Workflow Embed by `@ElectronicBlueberry <https://github.com/ElectronicBlueberry>`_ in `#16657 <https://github.com/galaxyproject/galaxy/pull/16657>`_
* Remove "Create Workflow" form and allow workflow creation in editor by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#16938 <https://github.com/galaxyproject/galaxy/pull/16938>`_

-------------------
23.1.4 (2024-01-04)
-------------------

No recorded changes since last release

-------------------
23.1.3 (2023-12-01)
-------------------

No recorded changes since last release

-------------------
23.1.2 (2023-11-29)
-------------------

No recorded changes since last release

-------------------
23.1.1 (2023-10-23)
-------------------


=========
Bug fixes
=========

* Improve robustness of collection upload tests. by `@jmchilton <https://github.com/jmchilton>`_ in `#16093 <https://github.com/galaxyproject/galaxy/pull/16093>`_
* Accessibility fixes for workflows, login, and registration. by `@jmchilton <https://github.com/jmchilton>`_ in `#16146 <https://github.com/galaxyproject/galaxy/pull/16146>`_
* Login/Register fixes by `@dannon <https://github.com/dannon>`_ in `#16652 <https://github.com/galaxyproject/galaxy/pull/16652>`_

============
Enhancements
============

* Upgraded to new multiselect Tags component for Workflows, DatasetList, Attributes by `@hujambo-dunia <https://github.com/hujambo-dunia>`_ in `#15225 <https://github.com/galaxyproject/galaxy/pull/15225>`_
* Add basic selenium test for shared histories by `@davelopez <https://github.com/davelopez>`_ in `#15538 <https://github.com/galaxyproject/galaxy/pull/15538>`_
* Initial end-to-end tests for separate quota sources per object store by `@jmchilton <https://github.com/jmchilton>`_ in `#15800 <https://github.com/galaxyproject/galaxy/pull/15800>`_
* Vueify Select field by `@guerler <https://github.com/guerler>`_ in `#16010 <https://github.com/galaxyproject/galaxy/pull/16010>`_
* implement admin jobs filtering by `@martenson <https://github.com/martenson>`_ in `#16020 <https://github.com/galaxyproject/galaxy/pull/16020>`_
* Selenium test for displaying workflows with problems in pages. by `@jmchilton <https://github.com/jmchilton>`_ in `#16085 <https://github.com/galaxyproject/galaxy/pull/16085>`_
* Integrate accessibility testing into Selenium testing by `@jmchilton <https://github.com/jmchilton>`_ in `#16122 <https://github.com/galaxyproject/galaxy/pull/16122>`_
* bring grids for (published) pages on par with workflows by `@martenson <https://github.com/martenson>`_ in `#16209 <https://github.com/galaxyproject/galaxy/pull/16209>`_
* Small test decorator improvements. by `@jmchilton <https://github.com/jmchilton>`_ in `#16220 <https://github.com/galaxyproject/galaxy/pull/16220>`_
* Initial e2e test for history storage. by `@jmchilton <https://github.com/jmchilton>`_ in `#16221 <https://github.com/galaxyproject/galaxy/pull/16221>`_
* Selenium test for page history links. by `@jmchilton <https://github.com/jmchilton>`_ in `#16222 <https://github.com/galaxyproject/galaxy/pull/16222>`_
* E2E Tests for Edit Dataset Attributes Page by `@jmchilton <https://github.com/jmchilton>`_ in `#16224 <https://github.com/galaxyproject/galaxy/pull/16224>`_
* Selenium type fixes and annotations. by `@jmchilton <https://github.com/jmchilton>`_ in `#16242 <https://github.com/galaxyproject/galaxy/pull/16242>`_
* e2e test for workflow license selector by `@jmchilton <https://github.com/jmchilton>`_ in `#16243 <https://github.com/galaxyproject/galaxy/pull/16243>`_

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


============
Enhancements
============

* Port selenium setup to non-deprecated selenium options by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16215 <https://github.com/galaxyproject/galaxy/pull/16215>`_

-------------------
23.0.1 (2023-06-08)
-------------------


============
Enhancements
============

* Add support for launching workflows via Tutorial Mode by `@hexylena <https://github.com/hexylena>`_ in `#15684 <https://github.com/galaxyproject/galaxy/pull/15684>`_

-------------------
20.9.0 (2020-10-15)
-------------------

* First release from the 20.09 branch of Galaxy.

-------------------
20.5.0 (2020-07-04)
-------------------

* First release from the 20.05 branch of Galaxy.
