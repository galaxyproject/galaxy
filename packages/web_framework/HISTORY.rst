History
-------

.. to_doc

-------------------
24.1.3 (2024-10-25)
-------------------


=========
Bug fixes
=========

* Increase API robustness to invalid requests, improve compressed data serving by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18494 <https://github.com/galaxyproject/galaxy/pull/18494>`_
* Apply statsd arg sanitization to all pages by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18509 <https://github.com/galaxyproject/galaxy/pull/18509>`_
* Close install model session when request ends by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18629 <https://github.com/galaxyproject/galaxy/pull/18629>`_

-------------------
24.1.2 (2024-09-25)
-------------------


=========
Bug fixes
=========

* Increase API robustness to invalid requests, improve compressed data serving by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18494 <https://github.com/galaxyproject/galaxy/pull/18494>`_
* Apply statsd arg sanitization to all pages by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18509 <https://github.com/galaxyproject/galaxy/pull/18509>`_
* Close install model session when request ends by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18629 <https://github.com/galaxyproject/galaxy/pull/18629>`_

-------------------
24.1.1 (2024-07-02)
-------------------


============
Enhancements
============

* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#17653 <https://github.com/galaxyproject/galaxy/pull/17653>`_
* Code cleanups from ruff and pyupgrade by `@nsoranzo <https://github.com/nsoranzo>`_ in `#17654 <https://github.com/galaxyproject/galaxy/pull/17654>`_
* SQLAlchemy 2.0 by `@jdavcs <https://github.com/jdavcs>`_ in `#17778 <https://github.com/galaxyproject/galaxy/pull/17778>`_
* Add galaxy to user agent by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18003 <https://github.com/galaxyproject/galaxy/pull/18003>`_
* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#18063 <https://github.com/galaxyproject/galaxy/pull/18063>`_

-------------------
24.0.3 (2024-06-28)
-------------------


=========
Bug fixes
=========

* Reset content-length for unhandled exceptions by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18233 <https://github.com/galaxyproject/galaxy/pull/18233>`_
* More fixes for running the TS with external hgweb by `@mvdbeek <https://github.com/mvdbeek>`_ in `#18279 <https://github.com/galaxyproject/galaxy/pull/18279>`_

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

* Fix KeyError in ``XForwardedHostMiddleware`` by `@nsoranzo <https://github.com/nsoranzo>`_ in `#17955 <https://github.com/galaxyproject/galaxy/pull/17955>`_

-------------------
24.0.0 (2024-04-02)
-------------------


============
Enhancements
============

* Python 3.8 as minimum by `@mr-c <https://github.com/mr-c>`_ in `#16954 <https://github.com/galaxyproject/galaxy/pull/16954>`_
* Vueify Admin User Grid by `@guerler <https://github.com/guerler>`_ in `#17030 <https://github.com/galaxyproject/galaxy/pull/17030>`_
* Remove web framework dependency from tools by `@davelopez <https://github.com/davelopez>`_ in `#17058 <https://github.com/galaxyproject/galaxy/pull/17058>`_
* Vueify Admin Groups Grid by `@guerler <https://github.com/guerler>`_ in `#17126 <https://github.com/galaxyproject/galaxy/pull/17126>`_
* Migrate models to pydantic 2 by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17262 <https://github.com/galaxyproject/galaxy/pull/17262>`_
* Update to black 2024 stable style by `@nsoranzo <https://github.com/nsoranzo>`_ in `#17391 <https://github.com/galaxyproject/galaxy/pull/17391>`_
* Removes outdated Grid controller and backbone modules by `@guerler <https://github.com/guerler>`_ in `#17434 <https://github.com/galaxyproject/galaxy/pull/17434>`_

-------------------
23.2.1 (2024-02-21)
-------------------


=========
Bug fixes
=========

* Ruff and flake8 fixes by `@nsoranzo <https://github.com/nsoranzo>`_ in `#16884 <https://github.com/galaxyproject/galaxy/pull/16884>`_
* Provide working routes.url_for every ASGI request by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17497 <https://github.com/galaxyproject/galaxy/pull/17497>`_

============
Enhancements
============

* Drop (admin only) userskeys controller by `@dannon <https://github.com/dannon>`_ in `#16318 <https://github.com/galaxyproject/galaxy/pull/16318>`_

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


=========
Bug fixes
=========

* Workaround issue in Routes by `@nsoranzo <https://github.com/nsoranzo>`_ in `#16981 <https://github.com/galaxyproject/galaxy/pull/16981>`_

============
Enhancements
============

* Add HEAD route to job_files endpoint by `@mvdbeek <https://github.com/mvdbeek>`_ in `#17072 <https://github.com/galaxyproject/galaxy/pull/17072>`_

-------------------
23.1.1 (2023-10-23)
-------------------


=========
Bug fixes
=========

* Fix some drs handling issues by `@nuwang <https://github.com/nuwang>`_ in `#15777 <https://github.com/galaxyproject/galaxy/pull/15777>`_
* Ensure session is request-scoped for legacy endpoints by `@jdavcs <https://github.com/jdavcs>`_ in `#16207 <https://github.com/galaxyproject/galaxy/pull/16207>`_

============
Enhancements
============

* Update Python dependencies by `@galaxybot <https://github.com/galaxybot>`_ in `#15435 <https://github.com/galaxyproject/galaxy/pull/15435>`_
* Don't error on missing parameters or unused parameters in UI controllers by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16246 <https://github.com/galaxyproject/galaxy/pull/16246>`_

-------------------
23.0.6 (2023-10-23)
-------------------


=========
Bug fixes
=========

* Don't read request body into memory by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16585 <https://github.com/galaxyproject/galaxy/pull/16585>`_

-------------------
23.0.5 (2023-07-29)
-------------------


=========
Bug fixes
=========

* Media player fix issue 16415 by `@bdwheele <https://github.com/bdwheele>`_ in `#16443 <https://github.com/galaxyproject/galaxy/pull/16443>`_
* Fix static file serving for ``robots.txt`` and ``favicon.ico`` when using per_host settings by `@mira-miracoli <https://github.com/mira-miracoli>`_ in `#16459 <https://github.com/galaxyproject/galaxy/pull/16459>`_

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

* Various fixes to path prefix handling by `@mvdbeek <https://github.com/mvdbeek>`_ in `#16033 <https://github.com/galaxyproject/galaxy/pull/16033>`_

-------------------
20.9.0 (2020-10-15)
-------------------

* First release from the 20.09 branch of Galaxy.

-------------------
20.5.0 (2020-07-04)
-------------------

* First release from the 20.05 branch of Galaxy.
