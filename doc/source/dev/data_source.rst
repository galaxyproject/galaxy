Data Source
===========

Data Source is a special type of Galaxy tool which allows for the download of data that is stored within external resources.

Example Implementations
-----------------------

Explore example implementations and communication protocols in Python-based server flavors available on GitHub: `galaxy-data_source-examples <https://github.com/hexylena/galaxy-data_source-examples>`_.

Data Source Configuration
-------------------------

Follow this checklist to configure a new data source using the `data_source` tool:

1. The `tool` tag set must have the attribute "tool_type" with the value "data_source" or "data_source_async".
2. The `command` tag set, inside the `tool` tag set, contains either "data_source.py" for the built-in synchronous/asynchronous single file downloader or a custom command for advanced downloading.
 - If using "data_source.py," the first parameter passed should be the name of the data tag in the outputs tag set (likely "$output").
 - If using "data_source.py," the second parameter passed is the maximum file size allowed by this Galaxy instance (use "$__app__.config.output_size_limit").
3. The `inputs` tag set, inside the `tool` tag set, has attributes defined for "action," "check_values," and "method."
 - The "action" attribute contains the URL to redirect the Galaxy user to.
 - The "method" attribute specifies the HTTP method (e.g., GET or POST).
 - The "check_values" attribute provides additional validation if needed.
4. Optionally, use the `request_param_translation` tag set inside the `tool` tag set for translating URL parameters between the remote web server and Galaxy.
5. The `outputs` tag set, inside the `tool` tag set, contains a single `data` tag if using the built-in "data_source.py" script.
 - The "format" attribute can be used to set the data format if fixed.
 - If using "data_source.py," the "name" attribute value must match the first parameter passed to "data_source.py" in the `command` tag set.
6. Finally, the tag should be inside the tag set.

Example Data Source Tools
-------------------------

Explore some example data source tools from repositories:

- `ucsc_tablebrowser.xml <https://github.com/galaxyproject/galaxy/blob/dev/tools/data_source/ucsc_tablebrowser.xml>`_
- `galaxy-data_source-examples <https://github.com/hexylena/galaxy-data_source-examples>`_

Data Connection Protocols
-------------------------

This section describes the protocols for depositing data in a Galaxy user account from an independent web site. The protocols operate via HTTP calls, with support for remote procedural calls via XML-RPC in development.

Data Generation Modes
~~~~~~~~~~~~~~~~~~~~

Two data generation modes are distinguished:

- **Synchronous Data Generation:** Services that stream data, generating data "on the fly" in response to parameters.
- **Asynchronous Data Generation:** Services that collect parameters and run a background process to generate results, notifying Galaxy when the data is ready for download.

Synchronous Data Depositing
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The process proceeds as follows:

1. Upon choosing the datasource, Galaxy performs an HTTP POST request to the external datasource's URL, passing the parameter `GALAXY_URL`.
2. As the user navigates the external datasource, it behaves as if the request did not originate from Galaxy.
3. At the point where the parameter submission would return data, the external datasource posts these parameters to the URL specified in the `GALAXY_URL` parameter.
4. Galaxy receives the parameters and runs a background process to resubmit them to the datasource, depositing the returned data in the user's account.

Asynchronous Data Depositing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This process is similar to synchronous data depositing, with the difference that the datasource later notifies Galaxy of the data location.

1. Follow steps 1-4 of synchronous data depositing. For step 4, Galaxy creates another parameter `GALAXY_URL` that uniquely characterizes the data returned.
2. When the data created by the datasource is ready, the datasource reconnects to the URL specified in `GALAXY_URL` and submits via HTTP GET the `STATUS` and `URL` parameters.
3. Galaxy makes a background request to fetch the data stored at the location specified in `URL`.

**Inter-process communication** is performed via simple text outputs. Commands that execute correctly end with `OK`. Messages not ending with `OK` are treated as errors, serving primarily for informational/debugging purposes.

Example Usage
-------------

Upon returning to the datasource, Galaxy submits the following:

.. code-block:: bash

    http://www.data.org/search?value=1&limit=10&gene=HBB1&GALAXY_URL=http://test.g2.bx.psu.edu/async/search/a4mr3ks4j1


The datasource may then write the following as response:

.. code-block:: bash

    received parameters:
    value=1
    limit=10
    gene=HBB1
    GALAXY_URL=http://test.g2.bx.psu.edu/async/search/a4mr3ks4j1
    running query in the background
    closing connection
    OK

Then, upon a finished data generation this same datasource would make the following request:

.. code-block:: bash

    http://test.g2.bx.psu.edu/async/search/a4mr3ks4j1?STATUS=OK&URL=http://www.data.org/temp/1299292.dat

to which Galaxy could answer:

.. code-block:: bash

    Data will be retrieved
    OK

in which case it will also go and fetch the data from http://www.data.org/temp/1299292.dat. But the output could also be:

.. code-block:: bash

    This data has already been deleted.

Providing an error message for unsuccessful submissions.


Notes: Both parameters `STATUS` and `URL` must be present. If `STATUS` is different than `OK`, the data will be treated as failed. For errors, include detailed values for both `STATUS` and `URL`, which will be copied into the metadata and displayed
as the reason for the failure.

Citation
--------

If you add a new data source to Galaxy in your published work, please cite:

`Blankenberg D, Coraor N, Von Kuster G, Taylor J, Nekrutenko A; Galaxy Team. Integrating diverse databases into a unified analysis framework: a Galaxy approach. Database (Oxford). 2011 Apr 29;2011:bar011. Print 2011. <http://www.ncbi.nlm.nih.gov/pubmed/21531983>`_