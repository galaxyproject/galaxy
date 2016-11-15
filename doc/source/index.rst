Galaxy Code Documentation
*************************

Galaxy_ is an open, web-based platform for accessible, reproducible, and
transparent computational biomedical research.

- *Accessible:* Users without programming experience can easily specify parameters and run tools and workflows.
- *Reproducible:* Galaxy captures information so that any user can repeat and understand a complete computational analysis.
- *Transparent:* Users share and publish analyses via the web and create Pages, interactive, web-based documents that describe a complete analysis.

Things to know:

- There are multiple choices_ when it comes to using Galaxy.
- You can explore the `current code in the development branch`_ on GitHub.
- This documentation is hosted at readthedocs_.

For more information on the Galaxy Project, please visit the `project home page`_.

.. _Galaxy: http://galaxyproject.org
.. _choices: https://wiki.galaxyproject.org/BigPicture/Choices
.. _current code in the development branch: https://github.com/galaxyproject/galaxy
.. _readthedocs: http://galaxy.readthedocs.org
.. _project home page: http://galaxyproject.org


Contents
========
.. toctree::
   :maxdepth: 5

   Galaxy API Documentation <api_doc>

   Tool Shed API Documentation <ts_api_doc>

   Application Documentation <lib/modules>

   Releases <releases/index>

   Developer Documentation <dev/index>

   Special topics in Administration <admin/index>

   Project Governance <project/organization>

   Issue Management <project/issues>

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

Building this Documentation
===========================

If you have your own copy of the Galaxy source code, you can also generate your own version of this documentation:

::

    $ make -C doc/ html

The generated documentation will be in ``doc/build/html/`` and can be viewed with a web browser.  Note that you will need to install Sphinx and a fair number of module dependencies before this will produce output.
