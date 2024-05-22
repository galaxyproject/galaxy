# Tool data

Galaxy stores tool data in the path defined by `tool_data_path` (by default `tool-data/`).
It's possible to separate tool data of toolshed-installed tools by setting `shed_tool_data_path`.

Tool data consists of:

1. the actual data
2. one or more `loc` files
3. entries in a tool data table (config) file


## History

In order to understand the naming and structure of these three components it might be of advantage
to look in the history. Tool data was organized in tabular `loc` that contained metadata and paths
of the data. Those files were installed with the tool and could be accessed with the
[`from_file`](https://docs.galaxyproject.org/en/master/dev/schema.html#from-file) mechanism from tools.
Since each tool version had it's own `loc` file the maintenance was difficult. With tool data tables
an additional abstraction layer was introduced that is used from tools via
[`from_datatable`](https://docs.galaxyproject.org/en/master/dev/schema.html#from-data-table).

## Tool data

This is the actual data that is stored by default in `tool_data_path`. It may be favorable to store the
actual tool data in a separate folder. For manually managed tool data this can be achieved by simply
storing the data in another folder. For data that is added by data managers this can be achieved by
setting `galaxy_data_manager_data_path`.

## `loc` files

In order to make tool data usable from Galaxy tools `loc` files are used. 
Those are tabular (by default tab separated) files with the extension `.loc`.
Besides the actual paths, the entries can contain IDs, names, or other metadata
that can be used in tools to select reference data. The paths should be given as absolute paths,
but can also be given relative to the Galaxy root dir.
By default `loc` files are installed in `tool_data_path` (where also built-in `loc` files
are stored). By setting `shed_tool_data_path` this can be separated.

## Tool data tables

The tool data tables that should be used in a Galaxy instance are listed
in tool data table config files. In addition these contain metadata.

Tool data table config files are XML files listing tool data table configurations:

```xml
<tables>
    ....
</tables>
```

An entry for a tool data looks like this

```xml
<table name="bwa_indexes_color" comment_char="#" allow_duplicate_entries="False">
    <columns>value, dbkey, name, path</columns>
    <file path="bwa_index_color.loc" />
</table>
```

- `table`: `name`, `comment_char` (default `"#"`), `separator` (default `"\t"`), `allow_duplicate_entries` (default `True`), `empty_field_value` (default `""`)
- `columns`: a comma separated list of column names
- `file`: `path` (alternatively `url`, `from_config`)

Tool data table entries for tools installed from a toolshed have an additional
element `tool_shed_repository` and sub-tags `tool_shed`
`repository_name`, `repository_owner`, `installed_changeset_revision`, e.g.:

```xml
<table name="plasmidfinder_database" comment_char="#">
    <columns>value, name, date, path</columns>
    <file path="/home/berntm/projects/galaxy/tool-data/toolshed.g2.bx.psu.edu/repos/iuc/plasmidfinder/7075b7a5441b/plasmidfinder_database.loc.sample"/>
    <tool_shed_repository>
        <tool_shed>toolshed.g2.bx.psu.edu</tool_shed>
        <repository_name>plasmidfinder</repository_name>
        <repository_owner>iuc</repository_owner>
        <installed_changeset_revision>7075b7a5441b</installed_changeset_revision>
    </tool_shed_repository>
</table>
```

The file path points to a `loc` file and can be given relative (to the
`tool_data_path`) or absolute. If a given relative path does not exist also the
base name is checked (many tools use something like `tool-data/xyz.loc` and
store example `loc` files in a `tool-data/` directory in the tool repository).
Currently also `.loc.sample` may be used in case the specified `.loc` is absent.

Galaxy uses two tool data table config files:

- `tool_data_table_config_path`: by default `tool_data_table_conf.xml` in Galaxy's `config/` directory.
- `shed_tool_data_table_config`: by default `shed_tool_data_table_conf.xml` in
Galaxy's `config/` directory. This file lists all tool data tables of tools
installed from a toolshed. Note that the entries are versioned, i.e. there is a
separate entry for each tool and tool version.

The tool data table config files can (and do) contain multiple entries for the same data table
(identified by the same name). These content of the corresponding `loc` files are merged when
they are loaded.

When a new tool is installed that uses a data table a new entry is added to
`shed_tool_data_table_config` and a `loc` file is placed in a versioned
subdirectory in `tool_data_path` (in a subdirectory that has the name of the
toolshed). By default this is `tool-data/toolshed.g2.bx.psu.edu/`. Note that
these directories will also contain tool data table config files, but they are unused.
