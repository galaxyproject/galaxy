Galaxy Code Documentation
*************************

Galaxy_ is an open, web-based platform for accessible, reproducible, and
transparent computational biomedical research.

- *Accessible:* Users without programming experience can easily specify parameters and run tools and workflows.
- *Reproducible:* Galaxy captures information so that any user can repeat and understand a complete computational analysis.
- *Transparent:* Users share and publish analyses via the web and create Pages, interactive, web-based documents that describe a complete analysis.

Two copies of the Galaxy code doumentation are published by the Galaxy Project

- Galaxy-Dist_:  This describes the code in the `most recent official release`_ of Galaxy.
- Galaxy-Central_: Describes the `current code in the development branch`_ of Galaxy.  This is the latest checkin, bleeding edge version of the code.  The documentation should never be more than an hour behind the code.

Both copies are hosted at ReadTheDocs_, a publicly supported web site for hosting project documentation.

If you have your own copy of the Galaxy source code, you can also generate your own version of this documentation:

::

    $ cd doc
    $ make html

The generated documentation will be in ``doc/build/html/`` and can be viewed with a web browser.  Note that you will need to install Sphinx and a fair number of module dependencies before this will produce output.

.. _Galaxy: http://galaxyproject.org/
.. _Galaxy-Dist: https://galaxy-dist.readthedocs.org/
.. _most recent official release: https://bitbucket.org/galaxy/galaxy-dist
.. _Galaxy-Central: https://galaxy-central.readthedocs.org/
.. _current code in the development branch: https://bitbucket.org/galaxy/galaxy-central
.. _ReadTheDocs: https://readthedocs.org/


For more on the Galaxy Project, please visit the `project home page`_.

.. _project home page: http://galaxyproject.org/


Contents
========
.. toctree::
   :maxdepth: 5

   API Documentation <lib/galaxy.webapps.galaxy.api>

   Application Documentation <lib/modules>

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

