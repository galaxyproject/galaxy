History
-------

.. to_doc

---------
26.1.dev0
---------



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
