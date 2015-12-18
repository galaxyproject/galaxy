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


.. toctree::
   :maxdepth: 3

    Galaxy API Quickstart <api/quickstart>

    Galaxy API Guidelines <api/guidelines>

    Galaxy API Documentation <lib/galaxy.webapps.galaxy.api>
