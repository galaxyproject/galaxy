Galaxy API Documentation
========================

In addition to being accessible through a web interface, Galaxy can also be
accessed programmatically, through shell scripts and other programs. The web
interface is appropriate for things like exploratory analysis, visualization,
construction of workflows, and rerunning workflows on new datasets.

The web interface is less suitable for things like
    - Connecting a Galaxy instance directly to your sequencer and running
      workflows whenever data is ready.
    - Running a workflow against multiple datasets (which can be done with the
      web interface, but is tedious).
    - When the analysis involves complex control, such as looping and
      branching.

The Galaxy API addresses these and other situations by exposing Galaxy
internals through an additional interface, known as an Application Programming
Interface, or API.

The up-to-date Galaxy API documentation can be accessed by appending ``/api/docs`` or ``/api/redoc``
to the base URL of a Galaxy server, e.g. https://usegalaxy.org/api/docs

Various language specific bindings for interfacing with the Galaxy API have been
developed by the Galaxy community including
`Python <https://bioblend.readthedocs.io/>`__,
`PHP <https://github.com/galaxyproject/blend4php>`__,
`Java <https://github.com/galaxyproject/blend4j>`__, and
`TypeScript <https://github.com/galaxyproject/galaxy/tree/dev/client/src/api/schema>`__.

Overview of available API resources is available at https://galaxyproject.org/develop/api/ .


.. toctree::
   :maxdepth: 2

    Quickstart <api/quickstart>

    Documentation <api/api>
