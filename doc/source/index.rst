Galaxy Documentation
********************

Galaxy is an open, web-based platform for accessible, reproducible, and transparent computational biomedical research.

For more information on the Galaxy Project, please visit the https://galaxyproject.org

This site contains documentation for administrators and developers. For user documentation, and admin and developer tutorials, please visit the `Galaxy Training Network <https://training.galaxyproject.org/>`__.

The community also maintains `a list of awesome Galaxy resources <https://github.com/galaxyproject/awesome-galaxy/>`__ related to all aspects of Galaxy.


* :ref:`release-docs`
* :ref:`admin-docs`
* :ref:`dev-docs`
* :ref:`about-docs`

.. _release-docs:

.. toctree::
   :maxdepth: 2
   :caption: Release Notes

   Releases <releases/index>

.. _admin-docs:

.. toctree::
   :maxdepth: 2
   :caption: Admin Documentation

   Administration <admin/index>
   Special topics <admin/special_topics/index>

.. _dev-docs:

.. toctree::
   :maxdepth: 2
   :caption: Developer Documentation

   Development <dev/index>
   Galaxy API <api_doc>
   Tool Shed API <ts_api_doc>
   Application Documentation <lib/modules>

.. _about-docs:

.. toctree::
   :maxdepth: 2
   :caption: About Project

   Project Governance <project/organization>
   Galaxy Release Process <project/releases>
   Issue Management <project/issues>

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`

Building this Documentation
===========================

If you have your own copy of the Galaxy source code, you can also generate your own version of this documentation. Run the following command from the Galaxy's root:

::

    $ make docs

The generated documentation will be in ``doc/build/html/`` and can be viewed with a web browser. Note that you will need to install Sphinx and other module dependencies which are listed in the Makefile in the Galaxy root folder.
