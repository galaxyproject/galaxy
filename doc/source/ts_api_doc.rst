Tool Shed API Documentation
===========================

The Galaxy Tool Shed can be accessed programmatically using API described
here via shell scripts and other programs.
To interact with the API you first need to log in as your user, navigate
to the API Keys page in the User menu, and generate a new API key. This
key you have to attach to every request as a parameter. Example:

::

    GET https://toolshed.g2.bx.psu.edu/api/repositories?q=fastq?key=SOME_KEY_HERE

.. toctree::
   :maxdepth: 3

    Toolshed API Documentation <lib/galaxy.webapps.tool_shed.api>
