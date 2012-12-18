Galaxy API Documentation
************************

Background
==========
In addition to being accessible through a web interface, Galaxy can now also be
accessed programmatically, through shell scripts and other programs. The web
interface is appropriate for things like exploratory analysis, visualization,
construction of workflows, and rerunning workflows on new datasets.

The web interface is less suitable for things like
    - Connecting a Galaxy instance directly to your sequencer and running
      workflows whenever data is ready
    - Running a workflow against multiple datasets (which can be done with the
      web interface, but is tedious)
    - When the analysis involves complex control, such as looping and
      branching.

The Galaxy API addresses these and other situations by exposing Galaxy
internals through an additional interface, known as an Application Programming
Interface, or API.

Quickstart
==========

Set the following option in universe_wsgi.ini and start the server::

        enable_api = True

Log in as your user, navigate to the API Keys page in the User menu, and
generate a new API key.  Make a note of the API key, and then pull up a
terminal.  Now we'll use the display.py script in your galaxy/scripts/api
directory for a short example::

        % ./display.py my_key http://localhost:4096/api/histories
        Collection Members
        ------------------
        #1: /api/histories/8c49be448cfe29bc
          name: Unnamed history
          id: 8c49be448cfe29bc
        #2: /api/histories/33b43b4e7093c91f
          name: output test
          id: 33b43b4e7093c91f

The result is a Collection of the histories of the user specified by the API
key (you).  To look at the details of a particular history, say #1 above, do
the following::

        % ./display.py my_key http://localhost:4096/api/histories/8c49be448cfe29bc
        Member Information
        ------------------
        state_details: {'ok': 1, 'failed_metadata': 0, 'upload': 0, 'discarded': 0, 'running': 0, 'setting_metadata': 0, 'error': 0, 'new': 0, 'queued': 0, 'empty': 0}
        state: ok
        contents_url: /api/histories/8c49be448cfe29bc/contents
        id: 8c49be448cfe29bc
        name: Unnamed history

This gives detailed information about the specific member in question, in this
case the History.  To view history contents, do the following::


        % ./display.py my_key http://localhost:4096/api/histories/8c49be448cfe29bc/contents
        Collection Members
        ------------------
        #1: /api/histories/8c49be448cfe29bc/contents/6f91353f3eb0fa4a
          name: Pasted Entry
          type: file
          id: 6f91353f3eb0fa4a

What we have here is another Collection of items containing all of the datasets
in this particular history.  Finally, to view details of a particular dataset
in this collection, execute the following::

        % ./display.py my_key http://localhost:4096/api/histories/8c49be448cfe29bc/contents/6f91353f3eb0fa4a
        Member Information
        ------------------
        misc_blurb: 1 line
        name: Pasted Entry
        data_type: txt
        deleted: False
        file_name: /Users/yoplait/work/galaxy-stock/database/files/000/dataset_82.dat
        state: ok
        download_url: /datasets/6f91353f3eb0fa4a/display?to_ext=txt
        visible: True
        genome_build: ?
        model_class: HistoryDatasetAssociation
        file_size: 17
        metadata_data_lines: 1
        id: 6f91353f3eb0fa4a
        misc_info: uploaded txt file
        metadata_dbkey: ?

And now you've successfully used the API to request and select a history,
browse the contents of that history, and then look at detailed information
about a particular dataset.

For a more comprehensive Data Library example, set the following option in your
universe_wsgi.ini as well, and restart galaxy again::

        admin_users = you@example.org
        library_import_dir = /path/to/some/directory

In the directory you specified for 'library_import_dir', create some
subdirectories, and put (or symlink) files to import into Galaxy into those
subdirectories.

In Galaxy, create an account that matches the address you put in 'admin_users',
then browse to that user's preferences and generate a new API Key.  Copy the
key to your clipboard and then use these scripts::

        % ./display.py my_key http://localhost:4096/api/libraries
        Collection Members
        ------------------

        0 elements in collection

        % ./library_create_library.py my_key http://localhost:4096/api/libraries api_test 'API Test Library'
        Response
        --------
        /api/libraries/f3f73e481f432006
          name: api_test
          id: f3f73e481f432006

        % ./display.py my_key http://localhost:4096/api/libraries
        Collection Members
        ------------------
        /api/libraries/f3f73e481f432006
          name: api_test
          id: f3f73e481f432006

        % ./display.py my_key http://localhost:4096/api/libraries/f3f73e481f432006
        Member Information
        ------------------
        synopsis: None
        contents_url: /api/libraries/f3f73e481f432006/contents
        description: API Test Library
        name: api_test

        % ./display.py my_key http://localhost:4096/api/libraries/f3f73e481f432006/contents 
        Collection Members
        ------------------
        /api/libraries/f3f73e481f432006/contents/28202595c0d2591f61ddda595d2c3670
          name: /
          type: folder
          id: 28202595c0d2591f61ddda595d2c3670

        % ./library_create_folder.py my_key http://localhost:4096/api/libraries/f3f73e481f432006/contents 28202595c0d2591f61ddda595d2c3670 api_test_folder1 'API Test Folder 1'
        Response
        --------
        /api/libraries/f3f73e481f432006/contents/28202595c0d2591fa4f9089d2303fd89
          name: api_test_folder1
          id: 28202595c0d2591fa4f9089d2303fd89

        % ./library_upload_from_import_dir.py my_key http://localhost:4096/api/libraries/f3f73e481f432006/contents 28202595c0d2591fa4f9089d2303fd89 bed bed hg19
        Response
        --------
        /api/libraries/f3f73e481f432006/contents/e9ef7fdb2db87d7b
          name: 2.bed
          id: e9ef7fdb2db87d7b
        /api/libraries/f3f73e481f432006/contents/3b7f6a31f80a5018
          name: 3.bed
          id: 3b7f6a31f80a5018

        % ./display.py my_key http://localhost:4096/api/libraries/f3f73e481f432006/contents 
        Collection Members
        ------------------
        /api/libraries/f3f73e481f432006/contents/28202595c0d2591f61ddda595d2c3670
          name: /
          type: folder
          id: 28202595c0d2591f61ddda595d2c3670
        /api/libraries/f3f73e481f432006/contents/28202595c0d2591fa4f9089d2303fd89
          name: /api_test_folder1
          type: folder
          id: 28202595c0d2591fa4f9089d2303fd89
        /api/libraries/f3f73e481f432006/contents/e9ef7fdb2db87d7b
          name: /api_test_folder1/2.bed
          type: file
          id: e9ef7fdb2db87d7b
        /api/libraries/f3f73e481f432006/contents/3b7f6a31f80a5018
          name: /api_test_folder1/3.bed
          type: file
          id: 3b7f6a31f80a5018

        % ./display.py my_key http://localhost:4096/api/libraries/f3f73e481f432006/contents/e9ef7fdb2db87d7b
        Member Information
        ------------------
        misc_blurb: 68 regions
        metadata_endCol: 3
        data_type: bed
        metadata_columns: 6
        metadata_nameCol: 4
        uploaded_by: nate@...
        metadata_strandCol: 6
        name: 2.bed
        genome_build: hg19
        metadata_comment_lines: None
        metadata_startCol: 2
        metadata_chromCol: 1
        file_size: 4272
        metadata_data_lines: 68
        message:
        metadata_dbkey: hg19
        misc_info: uploaded bed file
        date_uploaded: 2010-06-22T17:01:51.266119
        metadata_column_types: str, int, int, str, int, str

Other parameters are valid when uploading, they are the same parameters as are
used in the web form, like 'link_data_only' and etc.

The request and response format should be considered alpha and are subject to change.


API Controllers
===============

:mod:`datasets` Module
----------------------

.. automodule:: galaxy.webapps.galaxy.api.datasets
    :members:
    :undoc-members:
    :show-inheritance:

:mod:`folder_contents` Module
-----------------------------

.. automodule:: galaxy.webapps.galaxy.api.folder_contents
    :members:
    :undoc-members:
    :show-inheritance:

:mod:`folders` Module
---------------------

.. automodule:: galaxy.webapps.galaxy.api.folders
    :members:
    :undoc-members:
    :show-inheritance:

:mod:`forms` Module
-------------------

.. automodule:: galaxy.webapps.galaxy.api.forms
    :members:
    :undoc-members:
    :show-inheritance:

:mod:`genomes` Module
---------------------

.. automodule:: galaxy.webapps.galaxy.api.genomes
    :members:
    :undoc-members:
    :show-inheritance:

:mod:`group_roles` Module
-------------------------

.. automodule:: galaxy.webapps.galaxy.api.group_roles
    :members:
    :undoc-members:
    :show-inheritance:

:mod:`group_users` Module
-------------------------

.. automodule:: galaxy.webapps.galaxy.api.group_users
    :members:
    :undoc-members:
    :show-inheritance:

:mod:`groups` Module
--------------------

.. automodule:: galaxy.webapps.galaxy.api.groups
    :members:
    :undoc-members:
    :show-inheritance:

:mod:`histories` Module
-----------------------

.. automodule:: galaxy.webapps.galaxy.api.histories
    :members:
    :undoc-members:
    :show-inheritance:

:mod:`history_contents` Module
------------------------------

.. automodule:: galaxy.webapps.galaxy.api.history_contents
    :members:
    :undoc-members:
    :show-inheritance:

:mod:`item_tags` Module
-----------------------

.. automodule:: galaxy.webapps.galaxy.api.item_tags
    :members:
    :undoc-members:
    :show-inheritance:

:mod:`libraries` Module
-----------------------

.. automodule:: galaxy.webapps.galaxy.api.libraries
    :members:
    :undoc-members:
    :show-inheritance:

:mod:`library_contents` Module
------------------------------

.. automodule:: galaxy.webapps.galaxy.api.library_contents
    :members:
    :undoc-members:
    :show-inheritance:

:mod:`permissions` Module
-------------------------

.. automodule:: galaxy.webapps.galaxy.api.permissions
    :members:
    :undoc-members:
    :show-inheritance:

:mod:`quotas` Module
--------------------

.. automodule:: galaxy.webapps.galaxy.api.quotas
    :members:
    :undoc-members:
    :show-inheritance:

:mod:`request_types` Module
---------------------------

.. automodule:: galaxy.webapps.galaxy.api.request_types
    :members:
    :undoc-members:
    :show-inheritance:

:mod:`requests` Module
----------------------

.. automodule:: galaxy.webapps.galaxy.api.requests
    :members:
    :undoc-members:
    :show-inheritance:

:mod:`roles` Module
-------------------

.. automodule:: galaxy.webapps.galaxy.api.roles
    :members:
    :undoc-members:
    :show-inheritance:

:mod:`samples` Module
---------------------

.. automodule:: galaxy.webapps.galaxy.api.samples
    :members:
    :undoc-members:
    :show-inheritance:

:mod:`tools` Module
-------------------

.. automodule:: galaxy.webapps.galaxy.api.tools
    :members:
    :undoc-members:
    :show-inheritance:

:mod:`users` Module
-------------------

.. automodule:: galaxy.webapps.galaxy.api.users
    :members:
    :undoc-members:
    :show-inheritance:

:mod:`visualizations` Module
----------------------------

.. automodule:: galaxy.webapps.galaxy.api.visualizations
    :members:
    :undoc-members:
    :show-inheritance:

:mod:`workflows` Module
-----------------------

.. automodule:: galaxy.webapps.galaxy.api.workflows
    :members:
    :undoc-members:
    :show-inheritance:

