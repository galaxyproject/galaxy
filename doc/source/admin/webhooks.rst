Galaxy webhooks
===============

Tiny plugin interface to extend the Galaxy client.

Galaxy webhooks provides a simple way of inserting icons, links, or other HTML elements into predefined locations.
For this Galaxy provides some entry points which can be used to extend the client with content. This content
can consists out of simple HTML, JS or dynamically generated content from a python function.

  Please note that the webhooks interface is new and can change in the coming releases. Consider it as beta as we don't
  make promises to keep the API stable at the moment.

Plugin activation
-----------------
All webhooks that are included in the main Galaxy distribution are located in the ``config/plugins/webhooks/demo`` folder
and are deactivated by default.
To activate these demo webhooks make sure this path is added to ``webhooks_dir`` in your ``galaxy.ini``. You can add as many
webhook folders as you like as a comma separated list.
Webhooks supports one additional layer of activating/deactivating by changing the ``activate: true`` in each config of each webhook.


Entry points
------------

Currently there are four entry points (types) available:

- tool (after tool execution)
- workflow (after workflow execution)
- masthead (at the top level masthead)
- history-menu (inside History Panel menu)

For each type there is an example provided:

- Tool and workflow: A comic strip can be shown when a tool or a workflow is running. Right now PhD_ and XKCD_ comics are provided.

.. _PhD: http://phdcomics.com
.. _XKCD: http://xkcd.com/

 .. image:: images_webhooks/tool.png
    :scale: 50 %

 .. image:: images_webhooks/workflow.png
    :scale: 50 %

- Additional functionality can be added to the top menu. Two dummy buttons are implemented to show the idea:

  - A button that links to biostars
   .. image:: images_webhooks/masthead.png
      :scale: 50 %

  - A button that shows a pop-up with information about an user.
   .. image:: images_webhooks/masthead_trans_object.png
      :scale: 50 %

- The history menu can be extended. In this case we use two dummy entries 'History Menu Webhook Item 1' and  'History Menu Webhook Item 2'.
 .. image:: images_webhooks/history-menu.png
    :scale: 25 %

Plugin structure
----------------

Each plugin has the following folder structure:

.. code-block::

   - plugin_name
      - config
         - plugin_name.yaml (mandatory)
      - helper
         - __init__.py (optional)
      - static
         - script.js (optional)
         - styles.css (optional)


config
------

The configuration file is just a .yml (or .yaml) file with a few options. The following options are mandatory:

- **name** - must be the same as the plugin's root directory name
- **type** (see Entry points) - can be combined with others
- **activate** - *true* or *false* - whether show the plugin on a page or not

All other options can be anything used by the plugin and accessed later via *webhook.config['...']*.


helper/__init__.py
------------------

*__init__.py has* to have the **main()** function with the following (or similar) structure:

.. code-block:: python

   import logging
   log = logging.getLogger(__name__)

   def main(trans, webhook):
      error = ''
      data = {}
      try:
         # Third-party dependencies
         try:
            from bs4 import BeautifulSoup
         except ImportError as e:
             log.exception(e)
             return {}
         # some processing...
      except Exception as e:
         error = str(e)
      return {'success': not error, 'error': error, 'data': data}

As an example please take a look at the *phdcomics* example plugin: https://github.com/bgruening/galaxy/blob/feature/plugin-system/config/plugins/webhooks/phdcomics/helper/__init__.py


static
------

The *static* folder contains only two files with the specified above names (otherwise, they won’t be read on Galaxy run).

- script.js - all JavaScript code (with all third-party dependencies) must be here
- styles.css - all CSS styles, used by the plugin


Plugin dependencies
-------------------

Some plugins might have additional dependencies that needs to be installed into the Galaxy environment.
For example the PhD-Comic plugin requires the library beautifulsoup4. If these dependencies are not present
plugins should deactivate themself and issue an error into the Galaxy log.

To install these additional plugin do the following:

.. code-block:: python

  . GALAXY_ROOT/.venv/bin/activate  # activate Galaxy's virtualenv
  pip install beautifulsoup4        # install the requirements


Issues
------

tool/workflow
-------------

If a tool or a workflow plugin has script.js and/or styles.css, the content of these files will be read as two strings and sent to the client and appended to DOM’s <head>.

Such approach is a possible bottleneck if the two files are big (however, this shouldn’t ever happen because plugins are supposed to be small and simple).

masthead
--------

Topbar buttons are hard coded, so they’re rendered only after *make client*.

The plugin system is entirely dynamic. All plugins are detected during Galaxy load and their configs and statics are being saved. So, every plugin must be shown/rendered dynamically.

I found a not very optimal way to add buttons to the topbar (masthead):

.. code-block:: javascript

  $(document).ready(function() {
     Galaxy.page.masthead.collection.add({
          id      : ... ,
          icon    : ... ,
          url     : ... ,
          tooltip : ... ,
          onlick  : function() { ... }
      });
  });

history-menu
------------

History Panel items are again hard coded, but in the current implementation they’re rendered as html elements (so, they’re not even stored in a collection or any other object).

To add new menu items, I do the following:

.. code-block:: javascript

  menu.push({
    html : _l( ... ),
    anon : true,
    func : function() { ... }
  });

But in order to fetch all plugin menu items before rendering, I get them via API in a synchronous manner. The problem is that History Panel now may load a bit longer.
