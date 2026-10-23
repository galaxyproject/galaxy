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

Galaxy uses two settings for tool data table config files:

- `tool_data_table_config_path`: one or more comma-separated config paths; by default
  `tool_data_table_conf.xml` in Galaxy's `config/` directory.
- `shed_tool_data_table_config`: by default `shed_tool_data_table_conf.xml` in
Galaxy's `config/` directory. This file lists all tool data tables of tools
installed from a toolshed. Note that the entries are versioned, i.e. there is a
separate entry for each tool and tool version.

The tool data table config files can (and do) contain multiple entries for the same data table
(identified by the same name). The contents of the corresponding `loc` files are merged when
they are loaded.

When a new tool is installed that uses a data table a new entry is added to
`shed_tool_data_table_config` and a `loc` file is placed in a versioned
subdirectory in `tool_data_path` (in a subdirectory that has the name of the
toolshed). By default this is `tool-data/toolshed.g2.bx.psu.edu/`. Note that
these directories will also contain tool data table config files, but they are unused.

### Load order and duplicate values

At startup, Galaxy loads data table entries in this order:

1. Files in `tool_data_table_config_path`, in the order configured.
2. The file in `shed_tool_data_table_config`, after all of the above.

Within each config file, table definitions and their `<file>` elements are read in XML
order. Rows in each `.loc` file retain their file order. Later definitions of the same
table append their rows, skipping identical incoming rows. Rows that share a `value`
but differ in another column are retained so tools can filter them, for example by
index version. Reloading a table preserves the order of its loaded definitions.

For a tool select, the tool's filters, including any sorting filters, run before Galaxy
resolves a submitted value. If several rows still match, field lookup uses the first
one and logs a warning. The submitted value comes from the select's configured `value`
column, which may override the table's column mapping. Table-backed dropdowns show
one choice per submitted string value, keeping the first label after filtering;
dataset-backed choices remain separate. The data-table field API has no tool-specific
filters and returns the first raw match.

There is no inherent preference for local data, CVMFS, or IDC. For example, if two
rows submit `hg38`, with paths `/local/hg38.fa` and `/idc/hg38.fa`, loading the local
row first keeps `/local/hg38.fa` as the resolved path when both survive the tool's
filters in that order. Adding the IDC row afterward makes the reference available without changing
that existing selection. This precedence allows references to be deployed to IDC
while local copies still exist.

Appending an IDC config to `tool_data_table_config_path` places it after the other
files in that setting, but **before** `shed_tool_data_table_config`. Check where local
entries are defined when choosing the order. Reordering configs or rows, or removing
the first matching row, can change the reference used when rerunning a job with the
same submitted value. Keep this precedence stable when reproducibility depends on
which reference copy is selected.

## The `huggingface` shared data table

Galaxy tools that consume pre-downloaded Hugging Face models share a single
data table named `huggingface`.  Using one shared table means admins maintain
one `.loc` file and all tools benefit from every registered model entry.

### Declaring the table

Add the following block to `tool_data_table_conf.xml`:

```xml
<!-- Hugging Face models -->
<table name="huggingface" comment_char="#" allow_duplicate_entries="False">
    <columns>value, name, pipeline_tag, domain, free_tag, version, path</columns>
    <file path="/opt/galaxy/tool-data/huggingface.loc" />
</table>
```

Each tool ships a `tool-data/huggingface.loc.sample` that uses the same
7-column layout.

### Column reference

| # | Column | Purpose |
|---|--------|---------|
| 0 | `value` | Unique row ID across the whole table |
| 1 | `name` | Human-readable label shown in the Galaxy select widget |
| 2 | `pipeline_tag` | Model role — see controlled vocabulary below |
| 3 | `domain` | Coarse data domain — see controlled vocabulary below |
| 4 | `free_tag` | Optional narrowing tag; fallback filter when `pipeline_tag`/`domain` alone are not specific enough |
| 5 | `version` | Model version string |
| 6 | `path` | Path to the model data, a directory or a specific file, depending on the model structure |

**`value` (column 0)**

Must be globally unique across every row in `huggingface.loc`, regardless of
which tool added it.  Use the Hugging Face model ID (`<owner>/<model-name>`)
directly — it is stable and unambiguous.  If the same model is registered at
more than one version, append the version:

```
black-forest-labs/FLUX.1-dev
sentence-transformers/all-MiniLM-L6-v2
openai/whisper-large-v3_3.0
```

**`pipeline_tag` (column 2)**

Use the official [Hugging Face pipeline tag](https://huggingface.co/models).
Common values:

| Value | When to use |
|-------|-------------|
| `text-to-image` | Image generation models |
| `automatic-speech-recognition` | ASR / transcription models |
| `feature-extraction` | Sentence / document embedding models |
| `tabular-classification` | Tabular ML classifiers |
| `tabular-regression` | Tabular ML regressors |
| `text-generation` | Causal / instruction-tuned LLMs |

Do not invent synonyms for existing Hugging Face tags.

**`domain` (column 3)**

A broad category for the data type the model works with:
`image` · `text` · `audio` · `tabular` · `sequence` · `video` · `multimodal`

**`free_tag` (column 4)**

An optional short identifier used as a fallback narrowing filter when
`pipeline_tag` and `domain` alone are not specific enough.  Because a model
can be consumed by multiple tools, `free_tag` must not encode a specific tool
name.  Choose a short, lowercase, descriptive value and document it alongside
the tool that introduces it.

**`version` (column 5)**

The model version string.  A tool declares in its XML which version(s) it
accepts, allowing multiple versions of the same model to coexist.  Where
possible, rows are only added, never removed or edited.

**`path` (column 6)**

The path to the model data on the production server (maintained by admins).
Can be a directory (when the tool reads the whole Hugging Face cache layout)
or a specific file (e.g. a `.ckpt` checkpoint).

### XML filter convention

Filter primarily by `pipeline_tag` (column 2) and/or `domain` (column 3) so
only relevant model types are shown to the user.  Add a `version` or
`free_tag` filter only when you need to narrow the selection further:

```xml
<param name="model" type="select" label="Model">
    <options from_data_table="huggingface">
        <filter type="static_value" column="2" value="<pipeline_tag>"/>
        <filter type="static_value" column="3" value="<domain>"/>
        <!-- optional: narrow further by version or free_tag -->
        <!-- <filter type="static_value" column="5" value="<version>"/> -->
        <!-- <filter type="static_value" column="4" value="<free_tag>"/> -->
    </options>
</param>
```

Example from the Flux tool (filters by `free_tag` to restrict to Flux-specific model variants):

```xml
<options from_data_table="huggingface">
    <filter type="static_value" column="4" value="flux"/>
    <filter type="static_value" column="5" value="1"/>
</options>
```

### Example `.loc` entry

Each row is TAB-separated (7 columns):

```
# Columns: value <TAB> name <TAB> pipeline_tag <TAB> domain <TAB> free_tag <TAB> version <TAB> path
#
# Flux
black-forest-labs/FLUX.1-dev	FLUX.1 [dev]	text-to-image	image	flux	1	/data/hf_models
```
