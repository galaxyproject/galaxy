History
-------

.. to_doc

-----------
26.1.2.dev0
-----------



-------------------
26.1.1 (2026-08-04)
-------------------

No recorded changes since last release

-------------------
26.1.0 (2026-08-02)
-------------------


=========
Bug fixes
=========

* Fix mapOver terminology typo and minor polish by `@martenson <https://github.com/martenson>`_ in `#22226 <https://github.com/galaxyproject/galaxy/pull/22226>`_
* Fix RST syntax and other small bugs in help Markdown term YAML by `@jmchilton <https://github.com/jmchilton>`_ in `#22374 <https://github.com/galaxyproject/galaxy/pull/22374>`_
* Fix tool id handling for shed-installed tools by `@guerler <https://github.com/guerler>`_ in `#22553 <https://github.com/galaxyproject/galaxy/pull/22553>`_
* Skip missing history item ids in job exports by `@guerler <https://github.com/guerler>`_ in `#22563 <https://github.com/galaxyproject/galaxy/pull/22563>`_
* Fix workflow extraction not including user-defined tool steps by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#22694 <https://github.com/galaxyproject/galaxy/pull/22694>`_

============
Enhancements
============

* Migrate tool execution request from api/tools to api/jobs by `@guerler <https://github.com/guerler>`_ in `#21842 <https://github.com/galaxyproject/galaxy/pull/21842>`_
* Add the History Graph API by `@guerler <https://github.com/guerler>`_ in `#21932 <https://github.com/galaxyproject/galaxy/pull/21932>`_
* Add Workflow Report generator agent by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#21934 <https://github.com/galaxyproject/galaxy/pull/21934>`_
* Convert workflow extraction interface to Vue by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#21935 <https://github.com/galaxyproject/galaxy/pull/21935>`_
* ChatGXY UI improvements and exchange management by `@dannon <https://github.com/dannon>`_ in `#21950 <https://github.com/galaxyproject/galaxy/pull/21950>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#21951 <https://github.com/galaxyproject/galaxy/pull/21951>`_
* Migrate Python packages to \`src\` layout and pure namespace packages by `@mr-c <https://github.com/mr-c>`_ in `#21977 <https://github.com/galaxyproject/galaxy/pull/21977>`_
* More concise test logging by `@jmchilton <https://github.com/jmchilton>`_ in `#21983 <https://github.com/galaxyproject/galaxy/pull/21983>`_
* Add persistent docked ChatGXY panel with context awareness by `@dannon <https://github.com/dannon>`_ in `#22096 <https://github.com/galaxyproject/galaxy/pull/22096>`_
* Extend the favorite tool panel concept by `@bgruening <https://github.com/bgruening>`_ in `#22212 <https://github.com/galaxyproject/galaxy/pull/22212>`_
* Search and paginate user and roles api by `@mvdbeek <https://github.com/mvdbeek>`_ in `#22311 <https://github.com/galaxyproject/galaxy/pull/22311>`_
* Use a help popover for TRS search field by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#22330 <https://github.com/galaxyproject/galaxy/pull/22330>`_
* Galaxy Notebooks: Persistent Narrative for Human-AI Collaborative Science in Galaxy by `@jmchilton <https://github.com/jmchilton>`_ in `#22361 <https://github.com/galaxyproject/galaxy/pull/22361>`_
* Clean up Pydantic v2 deprecation warnings by `@mvdbeek <https://github.com/mvdbeek>`_ in `#22463 <https://github.com/galaxyproject/galaxy/pull/22463>`_
* Add bulk dataset storage migration by `@davelopez <https://github.com/davelopez>`_ in `#22606 <https://github.com/galaxyproject/galaxy/pull/22606>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#22619 <https://github.com/galaxyproject/galaxy/pull/22619>`_
* Add user-defined-tool operations to the agent-operations layer by `@dannon <https://github.com/dannon>`_ in `#22625 <https://github.com/galaxyproject/galaxy/pull/22625>`_
* Re-introduce IWC tools in agent-operations layer by `@dannon <https://github.com/dannon>`_ in `#22626 <https://github.com/galaxyproject/galaxy/pull/22626>`_
* Enhance workflow extraction by IDs with deduplication and UI improvements by `@jmchilton <https://github.com/jmchilton>`_ in `#22706 <https://github.com/galaxyproject/galaxy/pull/22706>`_
* More structured HistoryGraph API references by `@jmchilton <https://github.com/jmchilton>`_ in `#22732 <https://github.com/galaxyproject/galaxy/pull/22732>`_
* Further polish/bugfixes for notebooks created from invocations by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#22873 <https://github.com/galaxyproject/galaxy/pull/22873>`_

-------------------
26.0.1 (2026-06-04)
-------------------


=========
Bug fixes
=========

* Backport FastAPI/Starlette upgrade for BadHost (CVE-2026-48710) by `@mvdbeek <https://github.com/mvdbeek>`_ in `#22778 <https://github.com/galaxyproject/galaxy/pull/22778>`_

-------------------
26.0.0 (2026-04-08)
-------------------


=========
Bug fixes
=========

* Provide more accurate step hints for failing subworkflow steps by `@mvdbeek <https://github.com/mvdbeek>`_ in `#21514 <https://github.com/galaxyproject/galaxy/pull/21514>`_
* Add missing types to visualization model by `@guerler <https://github.com/guerler>`_ in `#21672 <https://github.com/galaxyproject/galaxy/pull/21672>`_
* Fix Pydantic UnsupportedFieldAttributeWarning for Field defaults in Annotated by `@mvdbeek <https://github.com/mvdbeek>`_ in `#21923 <https://github.com/galaxyproject/galaxy/pull/21923>`_
* Fix dict leaking to process_dataset() during workflow execution by `@mvdbeek <https://github.com/mvdbeek>`_ in `#21982 <https://github.com/galaxyproject/galaxy/pull/21982>`_
* Fix AttributeError when fetching citations for missing tools by `@mvdbeek <https://github.com/mvdbeek>`_ in `#22029 <https://github.com/galaxyproject/galaxy/pull/22029>`_
* Add batch celery task for history dataset purging by `@mvdbeek <https://github.com/mvdbeek>`_ in `#22180 <https://github.com/galaxyproject/galaxy/pull/22180>`_
* Fix batch history purge not updating user's update_time by `@mvdbeek <https://github.com/mvdbeek>`_ in `#22238 <https://github.com/galaxyproject/galaxy/pull/22238>`_
* Validate workflow invocation parameters values are dicts by `@mvdbeek <https://github.com/mvdbeek>`_ in `#22388 <https://github.com/galaxyproject/galaxy/pull/22388>`_

============
Enhancements
============

* Replace Copy Dataset Mako with Vue Component by `@guerler <https://github.com/guerler>`_ in `#17507 <https://github.com/galaxyproject/galaxy/pull/17507>`_
* Add Support for HTTP Headers in URL Fetch Requests with Secure Storage for Landing Requests by `@davelopez <https://github.com/davelopez>`_ in `#20924 <https://github.com/galaxyproject/galaxy/pull/20924>`_
* Tool Request API  by `@jmchilton <https://github.com/jmchilton>`_ in `#20935 <https://github.com/galaxyproject/galaxy/pull/20935>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#21043 <https://github.com/galaxyproject/galaxy/pull/21043>`_
* Remove legacy Visualization Mako and Controllers by `@guerler <https://github.com/guerler>`_ in `#21133 <https://github.com/galaxyproject/galaxy/pull/21133>`_
* Allow filtering job searches by history ID by `@nsoranzo <https://github.com/nsoranzo>`_ in `#21257 <https://github.com/galaxyproject/galaxy/pull/21257>`_
* Implement GA4GH WES API by `@jmchilton <https://github.com/jmchilton>`_ in `#21335 <https://github.com/galaxyproject/galaxy/pull/21335>`_
* Add AI Agent Framework and ChatGXY 2.0 by `@dannon <https://github.com/dannon>`_ in `#21434 <https://github.com/galaxyproject/galaxy/pull/21434>`_
* Enable attaching sample sheet to landing requests by `@mvdbeek <https://github.com/mvdbeek>`_ in `#21489 <https://github.com/galaxyproject/galaxy/pull/21489>`_
* Include subworkflow jobs in invocation metrics by `@mvdbeek <https://github.com/mvdbeek>`_ in `#21511 <https://github.com/galaxyproject/galaxy/pull/21511>`_
* Add support for workflow landing requests using simple URLs by `@mvdbeek <https://github.com/mvdbeek>`_ in `#21525 <https://github.com/galaxyproject/galaxy/pull/21525>`_
* Implement workflow completion monitoring with extensible hooks by `@mvdbeek <https://github.com/mvdbeek>`_ in `#21532 <https://github.com/galaxyproject/galaxy/pull/21532>`_
* Clean up code with pyupgrade by `@nsoranzo <https://github.com/nsoranzo>`_ in `#21540 <https://github.com/galaxyproject/galaxy/pull/21540>`_
* Add discarded_data option to model store import API by `@mvdbeek <https://github.com/mvdbeek>`_ in `#21582 <https://github.com/galaxyproject/galaxy/pull/21582>`_
* Drop support for Python 3.9 by `@nsoranzo <https://github.com/nsoranzo>`_ in `#21583 <https://github.com/galaxyproject/galaxy/pull/21583>`_
* Standardize agent API schemas and response metadata by `@dannon <https://github.com/dannon>`_ in `#21692 <https://github.com/galaxyproject/galaxy/pull/21692>`_
* Backport chat API improvements by `@dannon <https://github.com/dannon>`_ in `#21973 <https://github.com/galaxyproject/galaxy/pull/21973>`_

=============
Other changes
=============

* Merge 25.1 into dev, fix openapi schema generation for TypedDict by `@mvdbeek <https://github.com/mvdbeek>`_ in `#21168 <https://github.com/galaxyproject/galaxy/pull/21168>`_

-------------------
25.1.2 (2026-03-09)
-------------------


=========
Bug fixes
=========

* Fix help forum integration by `@davelopez <https://github.com/davelopez>`_ in `#21773 <https://github.com/galaxyproject/galaxy/pull/21773>`_

-------------------
25.1.1 (2026-02-03)
-------------------


=========
Bug fixes
=========

* Usability fixes for sample sheet selection.  by `@jmchilton <https://github.com/jmchilton>`_ in `#21503 <https://github.com/galaxyproject/galaxy/pull/21503>`_
* Fix type annotation for invocation report ``errors`` field by `@mvdbeek <https://github.com/mvdbeek>`_ in `#21508 <https://github.com/galaxyproject/galaxy/pull/21508>`_

-------------------
25.1.0 (2025-12-12)
-------------------


=========
Bug fixes
=========

* Collection API related spelling fix. by `@jmchilton <https://github.com/jmchilton>`_ in `#20470 <https://github.com/galaxyproject/galaxy/pull/20470>`_

============
Enhancements
============

* Don't serialize view of item in delete/purge request by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18732 <https://github.com/galaxyproject/galaxy/pull/18732>`_
* Support credentials(secrets/variables) in tool requirements by `@arash77 <https://github.com/arash77>`_ in `#19084 <https://github.com/galaxyproject/galaxy/pull/19084>`_
* Allow several Galaxy Markdown directives to be embedded. by `@jmchilton <https://github.com/jmchilton>`_ in `#19086 <https://github.com/galaxyproject/galaxy/pull/19086>`_
* Implement Sample Sheets  by `@jmchilton <https://github.com/jmchilton>`_ in `#19305 <https://github.com/galaxyproject/galaxy/pull/19305>`_
* Add short term storage expiration indicator to history items by `@davelopez <https://github.com/davelopez>`_ in `#20332 <https://github.com/galaxyproject/galaxy/pull/20332>`_
* Update create_time field to be required in history content items by `@davelopez <https://github.com/davelopez>`_ in `#20357 <https://github.com/galaxyproject/galaxy/pull/20357>`_
* Implement Data Landing Requests by `@jmchilton <https://github.com/jmchilton>`_ in `#20592 <https://github.com/galaxyproject/galaxy/pull/20592>`_
* Add a "Debug" (email report) tab to Workflow Invocations by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#20624 <https://github.com/galaxyproject/galaxy/pull/20624>`_
* Clean up code from pyupgrade by `@nsoranzo <https://github.com/nsoranzo>`_ in `#20642 <https://github.com/galaxyproject/galaxy/pull/20642>`_
* Refactor Files Sources Framework for stronger typing using pydantic models by `@davelopez <https://github.com/davelopez>`_ in `#20728 <https://github.com/galaxyproject/galaxy/pull/20728>`_
* Hierarchical display collection dataset states by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20731 <https://github.com/galaxyproject/galaxy/pull/20731>`_
* Change Advanced Tool Search to a Tool Discovery View by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#20747 <https://github.com/galaxyproject/galaxy/pull/20747>`_
* Add configfiles support and various enhancements for user defined tools by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20761 <https://github.com/galaxyproject/galaxy/pull/20761>`_
* Support remote file source hashes by `@davelopez <https://github.com/davelopez>`_ in `#20853 <https://github.com/galaxyproject/galaxy/pull/20853>`_
* Replace tour_generator webhook with internal API and frontend by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#20868 <https://github.com/galaxyproject/galaxy/pull/20868>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#20905 <https://github.com/galaxyproject/galaxy/pull/20905>`_
* Add resource docs and tweak tool source schema title generation by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20951 <https://github.com/galaxyproject/galaxy/pull/20951>`_
* Allow sending and tracking landing request origin by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20957 <https://github.com/galaxyproject/galaxy/pull/20957>`_
* Track landing request with invocation by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20960 <https://github.com/galaxyproject/galaxy/pull/20960>`_
* Move tours schema to schema directory (to fix package structure) by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#20965 <https://github.com/galaxyproject/galaxy/pull/20965>`_
* Use workflow-style payload in data landing request by `@mvdbeek <https://github.com/mvdbeek>`_ in `#21107 <https://github.com/galaxyproject/galaxy/pull/21107>`_

-------------------
25.0.4 (2025-11-18)
-------------------

No recorded changes since last release

-------------------
25.0.3 (2025-09-23)
-------------------

No recorded changes since last release

-------------------
25.0.2 (2025-08-13)
-------------------


=========
Bug fixes
=========

* Correct visualization response schema by `@guerler <https://github.com/guerler>`_ in `#20627 <https://github.com/galaxyproject/galaxy/pull/20627>`_
* Fix dataset serializers and response models by `@arash77 <https://github.com/arash77>`_ in `#20694 <https://github.com/galaxyproject/galaxy/pull/20694>`_

=============
Other changes
=============

* Merge 24.2 into 25.0 by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#20681 <https://github.com/galaxyproject/galaxy/pull/20681>`_

-------------------
25.0.1 (2025-06-20)
-------------------

No recorded changes since last release

-------------------
25.0.0 (2025-06-18)
-------------------


=========
Bug fixes
=========

* Better handling of public pages and workflows authored by deleted users by `@jdavcs <https://github.com/jdavcs>`_ in `#19394 <https://github.com/galaxyproject/galaxy/pull/19394>`_

============
Enhancements
============

* Implement tool markdown reports. by `@jmchilton <https://github.com/jmchilton>`_ in `#19054 <https://github.com/galaxyproject/galaxy/pull/19054>`_
* Let file sources choose a path for uploaded files by `@kysrpex <https://github.com/kysrpex>`_ in `#19154 <https://github.com/galaxyproject/galaxy/pull/19154>`_
* Calculate hash for new non-deferred datasets when finishing a job by `@nsoranzo <https://github.com/nsoranzo>`_ in `#19181 <https://github.com/galaxyproject/galaxy/pull/19181>`_
* Fix UP031 errors - Part 4 by `@nsoranzo <https://github.com/nsoranzo>`_ in `#19235 <https://github.com/galaxyproject/galaxy/pull/19235>`_
* Update pydantic to 2.10.3 by `@nsoranzo <https://github.com/nsoranzo>`_ in `#19326 <https://github.com/galaxyproject/galaxy/pull/19326>`_
* Empower Users to Build More Kinds of Collections, More Intelligently by `@jmchilton <https://github.com/jmchilton>`_ in `#19377 <https://github.com/galaxyproject/galaxy/pull/19377>`_
* Add User-Defined Tools by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19434 <https://github.com/galaxyproject/galaxy/pull/19434>`_
* Improve asynchronous tasks error handling and reporting by `@davelopez <https://github.com/davelopez>`_ in `#19448 <https://github.com/galaxyproject/galaxy/pull/19448>`_
* Allow to send notifications when Admins cancel jobs by `@davelopez <https://github.com/davelopez>`_ in `#19547 <https://github.com/galaxyproject/galaxy/pull/19547>`_
* Remove tags used by `@ElectronicBlueberry <https://github.com/ElectronicBlueberry>`_ in `#19576 <https://github.com/galaxyproject/galaxy/pull/19576>`_
* Generate correct types for Dataset source transformations on backend. by `@jmchilton <https://github.com/jmchilton>`_ in `#19666 <https://github.com/galaxyproject/galaxy/pull/19666>`_
* Define simple models for job messages. by `@jmchilton <https://github.com/jmchilton>`_ in `#19688 <https://github.com/galaxyproject/galaxy/pull/19688>`_
* Show workflow help (and readme?) in run form by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#19736 <https://github.com/galaxyproject/galaxy/pull/19736>`_
* Migrate Page editing controller endpoint to API by `@guerler <https://github.com/guerler>`_ in `#19923 <https://github.com/galaxyproject/galaxy/pull/19923>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#19929 <https://github.com/galaxyproject/galaxy/pull/19929>`_
* Enable ``warn_redundant_casts`` mypy option and drop redundant casts by `@nsoranzo <https://github.com/nsoranzo>`_ in `#20008 <https://github.com/galaxyproject/galaxy/pull/20008>`_
* Add DOI to workflow metadata by `@jdavcs <https://github.com/jdavcs>`_ in `#20033 <https://github.com/galaxyproject/galaxy/pull/20033>`_

-------------------
24.2.4 (2025-06-17)
-------------------


=========
Bug fixes
=========

* ChatGXY Error Handling by `@dannon <https://github.com/dannon>`_ in `#19987 <https://github.com/galaxyproject/galaxy/pull/19987>`_

-------------------
24.2.3 (2025-03-16)
-------------------

No recorded changes since last release

-------------------
24.2.2 (2025-03-08)
-------------------


============
Enhancements
============

* Add bwa_mem2_index directory datatype, framework enhancements for testing directories by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19694 <https://github.com/galaxyproject/galaxy/pull/19694>`_

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

* Drop "Send to cloud" tool and associated cloudauthz code by `@jdavcs <https://github.com/jdavcs>`_ in `#18196 <https://github.com/galaxyproject/galaxy/pull/18196>`_
* Fix issue with generating slug for sharing by `@arash77 <https://github.com/arash77>`_ in `#18986 <https://github.com/galaxyproject/galaxy/pull/18986>`_
* Fix invocation metrics usability by providing job context. by `@jmchilton <https://github.com/jmchilton>`_ in `#19279 <https://github.com/galaxyproject/galaxy/pull/19279>`_

============
Enhancements
============

* Experimental galactic wizard by `@dannon <https://github.com/dannon>`_ in `#15860 <https://github.com/galaxyproject/galaxy/pull/15860>`_
* Feature - stdout live reporting by `@gecage952 <https://github.com/gecage952>`_ in `#16975 <https://github.com/galaxyproject/galaxy/pull/16975>`_
* Add errors fast api by `@arash77 <https://github.com/arash77>`_ in `#18093 <https://github.com/galaxyproject/galaxy/pull/18093>`_
* Allow OAuth 2.0 user defined file sources (w/Dropbox integration) by `@jmchilton <https://github.com/jmchilton>`_ in `#18272 <https://github.com/galaxyproject/galaxy/pull/18272>`_
* Improve datasets permissions API schema typing by `@davelopez <https://github.com/davelopez>`_ in `#18563 <https://github.com/galaxyproject/galaxy/pull/18563>`_
* Improve typing for archived histories API schema by `@davelopez <https://github.com/davelopez>`_ in `#18586 <https://github.com/galaxyproject/galaxy/pull/18586>`_
* Tighten user notification API response types by `@davelopez <https://github.com/davelopez>`_ in `#18599 <https://github.com/galaxyproject/galaxy/pull/18599>`_
* Improve update user API payload schema by `@davelopez <https://github.com/davelopez>`_ in `#18602 <https://github.com/galaxyproject/galaxy/pull/18602>`_
* Improve update history payload schema by `@davelopez <https://github.com/davelopez>`_ in `#18618 <https://github.com/galaxyproject/galaxy/pull/18618>`_
* Improve types around User in schema and client by `@davelopez <https://github.com/davelopez>`_ in `#18645 <https://github.com/galaxyproject/galaxy/pull/18645>`_
* Improve accept header API schema by `@davelopez <https://github.com/davelopez>`_ in `#18668 <https://github.com/galaxyproject/galaxy/pull/18668>`_
* Migrate Visualizations API to FastAPI by `@arash77 <https://github.com/arash77>`_ in `#18721 <https://github.com/galaxyproject/galaxy/pull/18721>`_
* Backend handling of setting user-role, user-group, and group-role associations by `@jdavcs <https://github.com/jdavcs>`_ in `#18777 <https://github.com/galaxyproject/galaxy/pull/18777>`_
* Update Visualization FastAPI by `@arash77 <https://github.com/arash77>`_ in `#18792 <https://github.com/galaxyproject/galaxy/pull/18792>`_
* Workflow Landing Requests by `@jmchilton <https://github.com/jmchilton>`_ in `#18807 <https://github.com/galaxyproject/galaxy/pull/18807>`_
* Migrate Library Contents API to FastAPI by `@arash77 <https://github.com/arash77>`_ in `#18838 <https://github.com/galaxyproject/galaxy/pull/18838>`_
* Enable ``ignore-without-code`` mypy error code by `@nsoranzo <https://github.com/nsoranzo>`_ in `#18898 <https://github.com/galaxyproject/galaxy/pull/18898>`_
* Decouple user email from role name by `@jdavcs <https://github.com/jdavcs>`_ in `#18966 <https://github.com/galaxyproject/galaxy/pull/18966>`_
* Workflow landing improvements by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18979 <https://github.com/galaxyproject/galaxy/pull/18979>`_
* Allow recovering a normalized version of workflow request state from API by `@jmchilton <https://github.com/jmchilton>`_ in `#18985 <https://github.com/galaxyproject/galaxy/pull/18985>`_
* Add job metrics per invocation by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19048 <https://github.com/galaxyproject/galaxy/pull/19048>`_
* Implement workflow parameter validators. by `@jmchilton <https://github.com/jmchilton>`_ in `#19092 <https://github.com/galaxyproject/galaxy/pull/19092>`_
* Access public history in job cache / job search by `@mvdbeek <https://github.com/mvdbeek>`_ in `#19108 <https://github.com/galaxyproject/galaxy/pull/19108>`_
* Always validate hashes when provided by `@nsoranzo <https://github.com/nsoranzo>`_ in `#19110 <https://github.com/galaxyproject/galaxy/pull/19110>`_

-------------------
24.1.4 (2024-12-11)
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
* Remove the default `Incoming` suffix in `GenericModel` class by `@davelopez <https://github.com/davelopez>`_ in `#19174 <https://github.com/galaxyproject/galaxy/pull/19174>`_

============
Enhancements
============

* Include workflow invocation id in exception logs by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18594 <https://github.com/galaxyproject/galaxy/pull/18594>`_

-------------------
24.1.3 (2024-10-25)
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
