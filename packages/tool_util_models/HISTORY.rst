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

* Fix workflow implicit mapping of flat collections over paired_or_unpaired by `@jmchilton <https://github.com/jmchilton>`_ in `#21933 <https://github.com/galaxyproject/galaxy/pull/21933>`_
* [26.1 (spiritually)] Fix UDT collection outputs being silently dropped in YAML tool parser by `@jmchilton <https://github.com/jmchilton>`_ in `#22761 <https://github.com/galaxyproject/galaxy/pull/22761>`_
* Relax legacy doi:-prefixed citation handling (#22795) by `@mvdbeek <https://github.com/mvdbeek>`_ in `#22799 <https://github.com/galaxyproject/galaxy/pull/22799>`_
* Add fixed color set from webcolors package by `@guerler <https://github.com/guerler>`_ in `#22869 <https://github.com/galaxyproject/galaxy/pull/22869>`_
* Always attempt to build tool request for new API endpoint by `@mvdbeek <https://github.com/mvdbeek>`_ in `#22894 <https://github.com/galaxyproject/galaxy/pull/22894>`_
* Accept dce collection references in the tool request model by `@mvdbeek <https://github.com/mvdbeek>`_ in `#22926 <https://github.com/galaxyproject/galaxy/pull/22926>`_
* Make the user-defined tool schema robust for LLM authoring (CustomToolAgent) by `@mvdbeek <https://github.com/mvdbeek>`_ in `#22968 <https://github.com/galaxyproject/galaxy/pull/22968>`_
* Custom-tool agent: verified container resolution + authoring safeguards (with a reusable mulled-recommend CLI) by `@mvdbeek <https://github.com/mvdbeek>`_ in `#22981 <https://github.com/galaxyproject/galaxy/pull/22981>`_

============
Enhancements
============

* Various YAML Tool Hardening and Progress toward Tool State Goals by `@jmchilton <https://github.com/jmchilton>`_ in `#21828 <https://github.com/galaxyproject/galaxy/pull/21828>`_
* Migrate tool execution request from api/tools to api/jobs by `@guerler <https://github.com/guerler>`_ in `#21842 <https://github.com/galaxyproject/galaxy/pull/21842>`_
* Fix tool.parameters initialization by `@mvdbeek <https://github.com/mvdbeek>`_ in `#21914 <https://github.com/galaxyproject/galaxy/pull/21914>`_
* Allow tools to specify time limits by `@jmchilton <https://github.com/jmchilton>`_ in `#21927 <https://github.com/galaxyproject/galaxy/pull/21927>`_
* Migrate Python packages to \`src\` layout and pure namespace packages by `@mr-c <https://github.com/mr-c>`_ in `#21977 <https://github.com/galaxyproject/galaxy/pull/21977>`_
* Model subcollection mapping (map_over_type) and DCE in tool parameter schema by `@jmchilton <https://github.com/jmchilton>`_ in `#21991 <https://github.com/galaxyproject/galaxy/pull/21991>`_
* Enrich tool parameter JSON Schema with Galaxy metadata via model methods by `@mvdbeek <https://github.com/mvdbeek>`_ in `#22020 <https://github.com/galaxyproject/galaxy/pull/22020>`_
* More Complete, Robust, and Tested JSON-Schema for Tool State Models by `@jmchilton <https://github.com/jmchilton>`_ in `#22362 <https://github.com/galaxyproject/galaxy/pull/22362>`_
* Clean up Pydantic v2 deprecation warnings by `@mvdbeek <https://github.com/mvdbeek>`_ in `#22463 <https://github.com/galaxyproject/galaxy/pull/22463>`_
* Clean up various pytest warnings by `@mvdbeek <https://github.com/mvdbeek>`_ in `#22472 <https://github.com/galaxyproject/galaxy/pull/22472>`_
* Narrow YAML schema by `@jmchilton <https://github.com/jmchilton>`_ in `#22507 <https://github.com/galaxyproject/galaxy/pull/22507>`_
* Tighten the workflow test schema by `@jmchilton <https://github.com/jmchilton>`_ in `#22566 <https://github.com/galaxyproject/galaxy/pull/22566>`_
* Push UserToolSource semantic validation onto the pydantic model by `@mvdbeek <https://github.com/mvdbeek>`_ in `#22615 <https://github.com/galaxyproject/galaxy/pull/22615>`_
* Lift legacy UserToolSource representations on read by `@mvdbeek <https://github.com/mvdbeek>`_ in `#22624 <https://github.com/galaxyproject/galaxy/pull/22624>`_
* Expose more metadata in ParsedTool abstraction by `@jmchilton <https://github.com/jmchilton>`_ in `#22667 <https://github.com/galaxyproject/galaxy/pull/22667>`_

-------------------
26.0.1 (2026-06-04)
-------------------

No recorded changes since last release

-------------------
26.0.0 (2026-04-08)
-------------------


=========
Bug fixes
=========

* Fix Pydantic UnsupportedFieldAttributeWarning for Field defaults in Annotated by `@mvdbeek <https://github.com/mvdbeek>`_ in `#21923 <https://github.com/galaxyproject/galaxy/pull/21923>`_
* Backport paired or unpaired mapping fix by `@mvdbeek <https://github.com/mvdbeek>`_ in `#21936 <https://github.com/galaxyproject/galaxy/pull/21936>`_
* Fix validation of certain classes of text validators in tools. by `@jmchilton <https://github.com/jmchilton>`_ in `#22280 <https://github.com/galaxyproject/galaxy/pull/22280>`_

============
Enhancements
============

* Tool Request API  by `@jmchilton <https://github.com/jmchilton>`_ in `#20935 <https://github.com/galaxyproject/galaxy/pull/20935>`_
* Update fastapi to 0.123.4 and ``get_openapi()`` fork by `@nsoranzo <https://github.com/nsoranzo>`_ in `#21384 <https://github.com/galaxyproject/galaxy/pull/21384>`_
* Enable attaching sample sheet to landing requests by `@mvdbeek <https://github.com/mvdbeek>`_ in `#21489 <https://github.com/galaxyproject/galaxy/pull/21489>`_
* Apply 2026 black style by `@galaxybot <https://github.com/galaxybot>`_ in `#21618 <https://github.com/galaxyproject/galaxy/pull/21618>`_

=============
Other changes
=============

* Merge 25.1 into dev, fix openapi schema generation for TypedDict by `@mvdbeek <https://github.com/mvdbeek>`_ in `#21168 <https://github.com/galaxyproject/galaxy/pull/21168>`_
* Fix tool request API for multiple select parameters with defaults. by `@jmchilton <https://github.com/jmchilton>`_ in `#21416 <https://github.com/galaxyproject/galaxy/pull/21416>`_

-------------------
25.1.2 (2026-03-09)
-------------------

No recorded changes since last release

-------------------
25.1.1 (2026-02-03)
-------------------

No recorded changes since last release

-------------------
25.1.0 (2025-12-12)
-------------------


============
Enhancements
============

* Implement Sample Sheets  by `@jmchilton <https://github.com/jmchilton>`_ in `#19305 <https://github.com/galaxyproject/galaxy/pull/19305>`_
* Prepare ``ToolBox.dynamic_tool_to_tool()`` for CWL formats by `@nsoranzo <https://github.com/nsoranzo>`_ in `#20364 <https://github.com/galaxyproject/galaxy/pull/20364>`_
* Type annotation fixes for mypy 1.16.0 by `@nsoranzo <https://github.com/nsoranzo>`_ in `#20424 <https://github.com/galaxyproject/galaxy/pull/20424>`_
* Add configfiles support and various enhancements for user defined tools by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20761 <https://github.com/galaxyproject/galaxy/pull/20761>`_
* Add support for picking ``from_work_dir`` directory by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20916 <https://github.com/galaxyproject/galaxy/pull/20916>`_
* Include format in internal json model by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20917 <https://github.com/galaxyproject/galaxy/pull/20917>`_
* Add resource docs and tweak tool source schema title generation by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20951 <https://github.com/galaxyproject/galaxy/pull/20951>`_
* Use workflow-style payload in data landing request by `@mvdbeek <https://github.com/mvdbeek>`_ in `#21107 <https://github.com/galaxyproject/galaxy/pull/21107>`_

-------------------
25.0.4 (2025-11-18)
-------------------

No recorded changes since last release

-------------------
25.0.3 (2025-09-23)
-------------------


=========
Bug fixes
=========

* Fix collection element sorting in extended_metadata by `@mvdbeek <https://github.com/mvdbeek>`_ in `#20928 <https://github.com/galaxyproject/galaxy/pull/20928>`_

-------------------
25.0.2 (2025-08-13)
-------------------


=========
Bug fixes
=========

* Fix parameter models for optional color params. by `@jmchilton <https://github.com/jmchilton>`_ in `#20705 <https://github.com/galaxyproject/galaxy/pull/20705>`_

-------------------
25.0.1 (2025-06-20)
-------------------

No recorded changes since last release

-------------------
25.0.0 (2025-06-18)
-------------------

First release
