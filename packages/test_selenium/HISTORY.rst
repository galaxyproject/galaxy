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

* Use focus/blur to prevent prop updates from changing \`FormText\` values while typing by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#21300 <https://github.com/galaxyproject/galaxy/pull/21300>`_
* Improve history multiview UX with load more option by `@dannon <https://github.com/dannon>`_ in `#21687 <https://github.com/galaxyproject/galaxy/pull/21687>`_
* Fix flaky Selenium tests \`\`test_refresh_preserves_state\`\` and \`\`test_tool_discovery_landing\`\` by `@mvdbeek <https://github.com/mvdbeek>`_ in `#22301 <https://github.com/galaxyproject/galaxy/pull/22301>`_
* Minor styling fixes for invocation view header and history list cards by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#22639 <https://github.com/galaxyproject/galaxy/pull/22639>`_
* Update test workflows to respect gxformat2 0.26.0 syntax by `@nsoranzo <https://github.com/nsoranzo>`_ in `#22642 <https://github.com/galaxyproject/galaxy/pull/22642>`_
* Update test workflows to respect gxformat2 0.26.0 syntax (part 2) by `@nsoranzo <https://github.com/nsoranzo>`_ in `#22645 <https://github.com/galaxyproject/galaxy/pull/22645>`_
* GalaxyAI minor chat history and interface display fixes and polish by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#22793 <https://github.com/galaxyproject/galaxy/pull/22793>`_
* Reuse the global, context-aware GalaxyAI for Galaxy Notebooks by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#22807 <https://github.com/galaxyproject/galaxy/pull/22807>`_
* Fix tool-form option pagination never updating the select (#23135) by `@mvdbeek <https://github.com/mvdbeek>`_ in `#23136 <https://github.com/galaxyproject/galaxy/pull/23136>`_

============
Enhancements
============

* Improve the workflow import UI by `@neoformit <https://github.com/neoformit>`_ in `#21516 <https://github.com/galaxyproject/galaxy/pull/21516>`_
* Introduce a new favorite tool panel and most-recent tools by `@bgruening <https://github.com/bgruening>`_ in `#21600 <https://github.com/galaxyproject/galaxy/pull/21600>`_
* Introduce reusable GTable component by `@itisAliRH <https://github.com/itisAliRH>`_ in `#21635 <https://github.com/galaxyproject/galaxy/pull/21635>`_
* Add Selenium tests for workflow extraction UI by `@jmchilton <https://github.com/jmchilton>`_ in `#21805 <https://github.com/galaxyproject/galaxy/pull/21805>`_
* Migrate more E2E tests to be Playwright compatible by `@jmchilton <https://github.com/jmchilton>`_ in `#21841 <https://github.com/galaxyproject/galaxy/pull/21841>`_
* Beta upload: create dataset collections directly via HdcaDataItemsTarget by `@mvdbeek <https://github.com/mvdbeek>`_ in `#21855 <https://github.com/galaxyproject/galaxy/pull/21855>`_
* Enhance Playwright tests by `@jmchilton <https://github.com/jmchilton>`_ in `#21893 <https://github.com/galaxyproject/galaxy/pull/21893>`_
* Migrate Library components from BTable to GTable and improve GTable by `@itisAliRH <https://github.com/itisAliRH>`_ in `#21894 <https://github.com/galaxyproject/galaxy/pull/21894>`_
* Convert workflow extraction interface to Vue by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#21935 <https://github.com/galaxyproject/galaxy/pull/21935>`_
* Attempt to fix transient failure in selenium test test_advanced_search by `@davelopez <https://github.com/davelopez>`_ in `#21967 <https://github.com/galaxyproject/galaxy/pull/21967>`_
* Migrate Python packages to \`src\` layout and pure namespace packages by `@mr-c <https://github.com/mr-c>`_ in `#21977 <https://github.com/galaxyproject/galaxy/pull/21977>`_
* Migrate User CustomBuilds and ReviewCleanupDialog components from BTable to GTable by `@itisAliRH <https://github.com/itisAliRH>`_ in `#22039 <https://github.com/galaxyproject/galaxy/pull/22039>`_
* Replace mocked agent tests with static YAML backend for deterministic API/E2E testing by `@jmchilton <https://github.com/jmchilton>`_ in `#22070 <https://github.com/galaxyproject/galaxy/pull/22070>`_
* Persist scratchbook windows across page reloads by `@dannon <https://github.com/dannon>`_ in `#22088 <https://github.com/galaxyproject/galaxy/pull/22088>`_
* Modernize the ConfirmDialog composable to use GModal by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#22091 <https://github.com/galaxyproject/galaxy/pull/22091>`_
* Replace WinBox with native Vue scratchbook component by `@dannon <https://github.com/dannon>`_ in `#22095 <https://github.com/galaxyproject/galaxy/pull/22095>`_
* Replace BModal usage with GModal in several components by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#22114 <https://github.com/galaxyproject/galaxy/pull/22114>`_
* Upgrade client build to Vite 8 (Rolldown) by `@dannon <https://github.com/dannon>`_ in `#22145 <https://github.com/galaxyproject/galaxy/pull/22145>`_
* Add test suite for running tool tests via Playwright using the tool form by `@jmchilton <https://github.com/jmchilton>`_ in `#22157 <https://github.com/galaxyproject/galaxy/pull/22157>`_
* Expand E2E testing by `@jmchilton <https://github.com/jmchilton>`_ in `#22164 <https://github.com/galaxyproject/galaxy/pull/22164>`_
* Extend the favorite tool panel concept by `@bgruening <https://github.com/bgruening>`_ in `#22212 <https://github.com/galaxyproject/galaxy/pull/22212>`_
* Substantially expand tool form testing by `@jmchilton <https://github.com/jmchilton>`_ in `#22216 <https://github.com/galaxyproject/galaxy/pull/22216>`_
* Add \`pick_value\` Workflow Module by `@jmchilton <https://github.com/jmchilton>`_ in `#22222 <https://github.com/galaxyproject/galaxy/pull/22222>`_
* Simplify gxformat2 contract - drop ImporterGalaxyInterface, convert_and_import_workflow by `@jmchilton <https://github.com/jmchilton>`_ in `#22241 <https://github.com/galaxyproject/galaxy/pull/22241>`_
* Search and paginate user and roles api by `@mvdbeek <https://github.com/mvdbeek>`_ in `#22311 <https://github.com/galaxyproject/galaxy/pull/22311>`_
* Galaxy Notebooks: Persistent Narrative for Human-AI Collaborative Science in Galaxy by `@jmchilton <https://github.com/jmchilton>`_ in `#22361 <https://github.com/galaxyproject/galaxy/pull/22361>`_
* Add Selenium/Playwright coverage to Beta Upload Activity by `@davelopez <https://github.com/davelopez>`_ in `#22467 <https://github.com/galaxyproject/galaxy/pull/22467>`_
* Server-Sent Events for history + notification updates by `@mvdbeek <https://github.com/mvdbeek>`_ in `#22513 <https://github.com/galaxyproject/galaxy/pull/22513>`_
* Paginate /api/tools/{tool_id}/build history options by `@mvdbeek <https://github.com/mvdbeek>`_ in `#22643 <https://github.com/galaxyproject/galaxy/pull/22643>`_
* Enhance workflow extraction by IDs with deduplication and UI improvements by `@jmchilton <https://github.com/jmchilton>`_ in `#22706 <https://github.com/galaxyproject/galaxy/pull/22706>`_
* Rebrand ChatGXY to GalaxyAI by `@dannon <https://github.com/dannon>`_ in `#22707 <https://github.com/galaxyproject/galaxy/pull/22707>`_
* Improve import workflow usability by `@davelopez <https://github.com/davelopez>`_ in `#22813 <https://github.com/galaxyproject/galaxy/pull/22813>`_
* Further polish/bugfixes for notebooks created from invocations by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#22873 <https://github.com/galaxyproject/galaxy/pull/22873>`_

-------------------
26.0.1 (2026-06-04)
-------------------


=========
Bug fixes
=========

* Fix testing, publishing and dependencies of packages by `@nsoranzo <https://github.com/nsoranzo>`_ in `#22445 <https://github.com/galaxyproject/galaxy/pull/22445>`_
* Fix TypeError when generating tour for tool with boolean conditional case by `@ahmedhamidawan <https://github.com/ahmedhamidawan>`_ in `#22532 <https://github.com/galaxyproject/galaxy/pull/22532>`_
* Backport rocrate<0.15.0 pin by `@nsoranzo <https://github.com/nsoranzo>`_ in `#22537 <https://github.com/galaxyproject/galaxy/pull/22537>`_
* Preserve falsy workflow parameter values on workflow rerun by `@mvdbeek <https://github.com/mvdbeek>`_ in `#22601 <https://github.com/galaxyproject/galaxy/pull/22601>`_
* Fix workflow rerun for unset optional data inputs by `@mvdbeek <https://github.com/mvdbeek>`_ in `#22664 <https://github.com/galaxyproject/galaxy/pull/22664>`_
* Fix data source tool redirect back to Galaxy SPA by `@mvdbeek <https://github.com/mvdbeek>`_ in `#22720 <https://github.com/galaxyproject/galaxy/pull/22720>`_

-------------------
20.9.0 (2020-10-15)
-------------------

* First release from the 20.09 branch of Galaxy.
