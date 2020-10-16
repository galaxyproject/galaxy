Tool Panel Administration
=========================

Galaxy tool panel is located in the left of the 'Analysis page' and offers the following ways of modification.

Configuration
-------------
The contents of the tool panel are defined by the following configuration files.

Local tools
~~~~~~~~~~~
In the past, the file named by your ``tool_config_file`` configuration setting in your ``config/galaxy.yml`` file was the only file used to populate your Galaxy tool panel. The default name for this file is ``tool_conf.xml``. Since this was the only file involved in populating your Galaxy tool panel, it defined the items (tools, workflows, sections and labels) that would be displayed and the way in which they would be arranged.

Tool Shed tools
~~~~~~~~~~~~~~~
For purposes of the Galaxy [Tool Shed](/src/toolshed/index.md) the ``tool_config_file`` setting allows for a comma-separated list of files (e.g., ``tool_config_file = tool_conf.xml,shed_tool_conf.xml``,etc.). The additional shed-related tool panel configuration files (``shed_tool_conf.xml``, etc.) are automatically modified when you install or uninstall a Tool Shed repository (that contains tools) to your Galaxy.

Migrated tools
~~~~~~~~~~~~~~
Another configuration file named ``migrated_tools_conf.xml.sample`` is in the Galaxy installation directory. If you start your Galaxy server using ``sh run.sh`` or something similar, this sample file will automatically be copied to a file named ``migrated_tools_conf.xml`` in the same directory. You'll be required to manually copy this file if you start your Galaxy server differently. The migrated_tools_conf.xml file is reserved to contain the XML tag sets for repositories that contain tools that were once included in the Galaxy distribution but have been moved to the Tool Shed. Similar to the approach used with the other shed-related tool panel configuration files describe above, this file's contents will be changed automatically for certain tools contained in repositories that are installed into your local Galaxy instance. More information about this process is described in the following sections.

Layout
------

The 3 or more files described in the previous section (``tool_conf.xml``, one or more ``shed_tool_conf.xml`` files, and ``migrated_tools_conf.xml``) are all used to load tool panel items (tools, sections, labels and workflows). A file named ``integrated_tool_panel.xml`` defines the arrangement for displaying these loaded items in your Galaxy tool panel.
If this file does not exist in your Galaxy installation directory, it will be automatically created and populated when you start your Galaxy server. It is initially populated based on the order in which the tool panel items are loaded. The items are loaded as each tool panel configuration file is parsed and its items are loaded. The order in which these configuration files are parsed is the order of the comma-separated list of files defined in your ``tool_config_file`` setting in your ``config/galaxy.yml`` configuration file. The ``migrated_tools_conf.xml`` file is always parsed and loaded last. Let's look at an example to help clarify how this works.

If you uninstall a repository that contains tools, entries for those tools will automatically be removed from the shed-related tool panel config file and the integrated_tool_panel.xml file.

The best approach for managing the new integrated_tool_panel.xml file is to allow Galaxy to add or remove entries as manually adding or removing them will likely result in undesired behavior. Manual changes to the file should simply be moving entries around to produce the desired arrangement of your tool panel.

Sections & Labels
~~~~~~~~~~~~~~~~~
* You can add ``labels="updated"`` to the ``<tool>`` XML element to render a label next to the tool in the tool panel.
* You can add ``<section>`` tag as a child of``<toolbox>`` to create a section that can contains tools.

.. code-block:: xml

    <?xml version="1.0"?>
    <toolbox tool_path="database/shed_tools">
        <section id="mts" name="MTS" version="">
          <tool file="toolshed.g2.bx.psu.edu/repos/devteam/fastqc/a00a6402d09a/fastqc/rgFastQC.xml" guid="toolshed.g2.bx.psu.edu/repos/devteam/fastqc/fastqc/0.67" labels="new">
              <tool_shed>toolshed.g2.bx.psu.edu</tool_shed>
                <repository_name>fastqc</repository_name>
                <repository_owner>devteam</repository_owner>
                <installed_changeset_revision>a00a6402d09a</installed_changeset_revision>
                <id>toolshed.g2.bx.psu.edu/repos/devteam/fastqc/fastqc/0.67</id>
                <version>0.67</version>
            </tool>
        </section>
    </toolbox>
