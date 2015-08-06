Tool Shed API Documentation
***************************

Introduction
============
The Galaxy Tool Shed can be accessed programmatically using API described
here via shell scripts and other programs.
To interact with the API you first need to log in as your user, navigate
to the API Keys page in the User menu, and generate a new API key. This
key you have to attach to every request as a parameter. Example:

::

    GET https://toolshed.g2.bx.psu.edu/api/repositories?q=fastq?key=SOME_KEY_HERE


.. include:: api/guidelines.rst

.. include:: lib/galaxy.webapps.tool_shed.api.rst
