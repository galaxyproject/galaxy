Tool Panel Administration
=========================

The Galaxy tool panel is located on the left of the 'Analysis page' and offers the
following ways of modification.

Configuration
-------------
The contents of the tool panel are defined by the following configuration files.

Three configuration options define the content of the toolbox:

- ``tool_config_file`` (default: ``tool_conf.xml``)
- ``shed_tool_config_file`` (default: ``shed_tool_conf.xml``)
- ``migrated_tools_config`` (default ``migrated_tools_conf.xml``)

Built-in and custom tools
~~~~~~~~~~~~~~~~~~~~~~~~~
Built-in tools are defined in the file ``tool_conf.xml.sample`` which
is loaded by default. This is because of the default value of the
``tool_config_file`` configuration setting in the ``galaxy.yml`` file
which is ``tool_conf.xml`` (Galaxy loads the sample file
automatically when ``tool_conf.xml`` is absent).

Further custom tool config files can be listed in ``tool_config_file``.
These files could for instance contain custom local tools that are not
installed from the ToolShed.
Note that, if custom tool config files are listed, then this list also
should contain a tool configuration file containing the built-in tools.
It's favorable to just use ``tool_conf.xml.sample`` to obtain
automatic updates for built-in tools.

It's important to note that the tool configuration files, i.e. the sections,
labels, and tools included in them, are added in the order in which they are
specified. 
Therefore, to setup the order of the sections and labels a
custom tool conf file (e.g. ``tool_conf_labels.xml``) which contains
only the sections and labels appearing in any other tool config file can be used.

Since tools and sections are added in the order of installation
and modifying large XML files is tedious, the following setup
should cover most instances:

``tool_config_file: tool_conf_labels.xml,tool_conf.xml.sample``

A section containing built-in converters can be added to the tool panel
by enabling the ``display_builtin_converters`` setting.

Tool Shed tools
~~~~~~~~~~~~~~~
Tools that are installed from a `Tool Shed <https://galaxyproject.org/toolshed/>`__,
are added to the file named by the ``shed_tool_config_file`` configuration setting.

Migrated tools
~~~~~~~~~~~~~~

The ``migrated_tools_conf.xml(.sample)`` can typically be ignored, it's used
for local tool repositories that have been moved to the ToolShed. 
The configuration file ``migrated_tools_conf.xml.sample`` is in the
Galaxy configuration directory. If you start your Galaxy server using ``sh
run.sh`` or something similar, this sample file will automatically be copied to
a file named ``migrated_tools_conf.xml`` in the same directory. You'll be
required to manually copy this file if you start your Galaxy server differently.
The migrated_tools_conf.xml file is reserved to contain the XML tag sets for
repositories that contain tools that were once included in the Galaxy
distribution but have been moved to the Tool Shed. Similar to the approach used
with the other shed-related tool panel configuration files described above, this
file's contents will be changed automatically for certain tools contained in
repositories that are installed into your local Galaxy instance.

Layout
------

The various tool configuration files described in the previous section are all used
to load tool panel items (tools, sections, labels, and workflows). A file named
``integrated_tool_panel.xml`` defines the arrangement for displaying these
loaded items in your Galaxy tool panel.  If this file does not exist in your
Galaxy installation directory, it will be automatically created and populated
when you start your Galaxy server. It is initially populated based on the order
in which the tool panel items are loaded. The items are loaded as each tool
panel configuration file is parsed and its items are loaded. The order in which
these configuration files are parsed is the order of the comma-separated list of
files defined in your ``tool_config_file`` setting in your ``config/galaxy.yml``
configuration file. The ``migrated_tools_conf.xml`` file is always parsed and
loaded last.

If you uninstall a repository that contains tools, entries for those tools will
automatically be removed from the shed-related tool panel config file and the
``integrated_tool_panel.xml`` file.

The best approach for managing the ``integrated_tool_panel.xml`` file is to
allow Galaxy to add or remove entries as manually adding or removing them will
likely result in undesired behavior. 
The order of sections and labels can be changed using a ``tool_conf_labels.xml``
file as described above.

Tool conf XML syntax
~~~~~~~~~~~~~~~~~~~~

A tool configuration file is an XML file containing mainly four elements:

1. ``toolbox`` is the root tag. It has two optional attributes:
  - ``tool_path`` is used to set the path (relative to Galaxy's root dir)
    containing the tools.
  - ``monitor`` is a boolean that indicates if Galaxy should monitor
    changes to the file.
2. ``section`` defines a section in the tool panel. It needs to have
   an ``id`` attribute which should have no spaces, and has an optional
   ``name`` attribute which defines the text shown to the user (otherwise ``id`` is used.)
3. ``label`` adds a header line to the tool panel. It needs to have an ``id`` attribute
   and optionally define a ``text`` attribute which gives the text shown to the user.
4. ``tool`` defines a tool. 
  - The ``file`` attribute gives the path to the tool XML file (relative to the
    ``tool_path`` of the toolbox).
  - An optional ``labels`` render a label next to the tool in the tool panel, e.g. ``labels="updated"``.
  - An additional ``guid`` attribute is set by Galaxy for tools installed from a ToolShed.

Typically ``section`` and ``label`` tags are used as child of ``toolbox``, and
``tools`` are used as child of ``section``. In the following two examples are shown.

.. code-block:: xml

    <toolbox monitor="true">
      <label id="general_text_label" text="General Text Tools" />
      <section id="getext" name="Get Data">
        <tool file="data_source/upload.xml" />
      </section>
    </toolbox>

.. code-block:: xml

    <toolbox tool_path="shed_tools">
        <section id="metagenomics" name="Metagenomics" version="">
            <tool file="toolshed.g2.bx.psu.edu/repos/iuc/picrust_predict_metagenomes/2d4c0825cfe6/picrust_predict_metagenomes/predict_metagenomes.xml" guid="toolshed.g2.bx.psu.edu/repos/iuc/picrust_predict_metagenomes/picrust_predict_metagenomes/1.0.1.0">
                <tool_shed>toolshed.g2.bx.psu.edu</tool_shed>
                <repository_name>picrust_predict_metagenomes</repository_name>
                <repository_owner>iuc</repository_owner>
                <installed_changeset_revision>2d4c0825cfe6</installed_changeset_revision>
                <id>toolshed.g2.bx.psu.edu/repos/iuc/picrust_predict_metagenomes/picrust_predict_metagenomes/1.0.1.0</id>
                <version>1.0.1.0</version>
            </tool>
        </section>
    </toolbox>

Tool panel views
----------------

For large Galaxy instances the tool panel typically grows to hundreds of tools, which makes it
inconvenient to use. Also, the structure of the tool panel is difficult
to change using the XML files. 

Tool panel views allow admins to define custom static tool panels, i.e. subsets
of the tools in a custom easy-to-define structure. In addition, some automatically
structured tool panel views are generated by Galaxy itself. At the moment
these are the tool panel views defined by the EDAM ontology (see configuration
``edam_panel_views``).

The static admin-defined tool panel views are defined by YAML files contained
in the directory specified by ``panel_views_dir``. A default tool panel views
can be defined by ``default_tool_panel``.

The following example defines a tool panel view ``rna_analysis`` that will be
shown to the user as ``"RNA Analysis"``. The tool panel view just uses existing
sections as they are.

.. code-block:: yaml

    name: RNA Analysis
    id: rna_analysis
    type: activity
    items:
    - label: General Tools
    - sections: [text_manipulation, get_data,collection_operations,convert_formats,expression_tools]
    - label: NGS Tools
    - sections: [deeptools,bed,sam_bam,fasta_fastq,mapping]
    - label: RNA Analysis
    - section: rna_seq 
    - section: annotation 
    - section: rna_analysis

Many more operations are available. For instance, panels can be filtered by
individual tool IDs or regular expressions matching tool IDs. So if one wants to
discourage the use of Bowtie and TopHat in favor of HiSat, and might want to
disable mappers that come bundled with Galaxy in this view, this can be done by
using the ``excludes`` directive on a section definition or reference.

.. code-block:: yaml

    - section: mapping
      excludes:
      - tool_id_regex: '.*bowtie.*'
      - tool_id_regex: '.*tophat.*'
      - tool_id: 'bfast_wrapper'
      - tool_id: 'srma_wrapper'
      - tool_id: 'PerM'

It's possible to combine multiple sections into a new section - e.g. creating a
"Mass Spec" section from proteomics and metabolomics sections in the original
integrated tool panel. This can be done with the ``items_from`` directive and a new
explicit section definition as shown next.

.. code-block:: yaml

    - id: mass-spec
      name: "Mass Spec"
      type: section
      items:
      - items_from: proteomics
      - items_from: metabolomics
      excludes:
      - tool_id_regex: '.*maxquant.*'
      - types: [label]


Notice this can also be filtered the same way. Here we're also removing all the
labels from the original sections and the max quant tool.

One can also just use tools, workflows, labels, and sections to create a whole
new tool panel without referencing the original sections at all.

.. code-block:: yaml

    name: Custom Panel Filter
    type: generic
    items:
    - type: label
      text: The Start
    - type: tool
      id: empty_list
    - type: section
      id: my-section
      name: My Custom Section
      items:
      - type: tool
        id: count_list
