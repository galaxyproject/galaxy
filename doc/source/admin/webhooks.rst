Galaxy webhooks - tiny plugin interface to extend the Galaxy client
-------------------------------------------------------------------

Galaxy webhooks provides a simple way of inserting icons, links, or other HTML elements into predefined locations.
For this Galaxy provides some entry points which can be used to extend the client with content. This content
can consists out of simple HTML, JS or dynamically generated content from a python function.

Entry points
------------

There are four currently available entry points (types):

- tool (after tool execution)
- workflow (after workflow execution)
- masthead (at the top level masthead)
- history-menu (inside History Panel menu)

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
******

The configuration file is just a .yml (or .yaml) file with a few options. The following options are mandatory:

- **name** - must be the same as the plugin's root directory name
- **type** (see Entry points) - can be combined with others
- **activate** - *true* or *false* - whether show the plugin on a page or not

All other options can be anything used by the plugin and accessed later via *webhook.config['...']*.


helper/__init__.py
******************

*__init__.py has* to have the **main()** function with the following (or similar) structure:

.. code-block:: python
   
   def main(trans, webhook):
      error = ''
      data = {}
      try:
         # some processing... 
      except Exception as e:
         error = str(e) 
      return {'success': not error, 'error': error, 'data': data}

As an example please look at the phdcomics example plugin: https://github.com/bgruening/galaxy/blob/feature/plugin-system/config/plugins/webhooks/phdcomics/helper/__init__.py


static
******

The *static* folder contains only two files with the specified above names (otherwise, they won’t be read on Galaxy run).

- script.js - all JavaScript code (with all third-party dependencies) must be here
- styles.css - all CSS styles, used by the plugin

Issues
------

tool/workflow
*************

If a tool or a workflow plugin has script.js and/or styles.css, the content of these files will be read as two strings and sent to the client and appended to DOM’s <head>.

Such approach is a possible bottleneck if the two files are big (however, this shouldn’t ever happen because plugins are supposed to be small and simple).

masthead
********

Topbar buttons are hard coded, so they’re rendered only after make client.

The plugin system is entirely dynamic. All plugins are detected during Galaxy load and their configs and statics are saved. So, every plugin must be shown/rendered dynamically.

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
************

History Panel items are again hard coded, but in the current implementation they’re rendered as html elements (so, they’re not even stored in a collection or any other object).

To add new menu items, I do the following:

.. code-block:: javascript

  menu.push({
    html : _l( ... ),
    anon : true,
    func : function() { ... }
  });

But in order to fetch all plugin menu items before rendering, I get them via API in a synchronous manner. The problem is that History Panel now loads longer.
