History
-------

.. to_doc

-----------
26.0.3.dev0
-----------



-------------------
26.0.2 (2026-10-25)
-------------------


=========
Bug fixes
=========

* Quit selenium driver in test teardown to stop leaking chromedriver processes by `@mvdbeek <https://github.com/mvdbeek>`_ in `#23901 <https://github.com/galaxyproject/galaxy/pull/23901>`_
* Fix CI failures and flaky tests by `@mvdbeek <https://github.com/mvdbeek>`_ in `#24028 <https://github.com/galaxyproject/galaxy/pull/24028>`_
* Show workflow integer/float input bounds on the run form by `@jmchilton <https://github.com/jmchilton>`_ in `#24212 <https://github.com/galaxyproject/galaxy/pull/24212>`_
* Restore batch info for collections mapped over a collection input by `@jmchilton <https://github.com/jmchilton>`_ in `#24223 <https://github.com/galaxyproject/galaxy/pull/24223>`_
* Backport flaky test fixes by `@mvdbeek <https://github.com/mvdbeek>`_ in `#24251 <https://github.com/galaxyproject/galaxy/pull/24251>`_

=============
Other changes
=============

* Merge release_25.1 into release_26.0 by `@mvdbeek <https://github.com/mvdbeek>`_ in `#24274 <https://github.com/galaxyproject/galaxy/pull/24274>`_

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
