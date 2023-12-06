from dataclasses import field
from decimal import Decimal
from enum import Enum
from typing import (
    List,
    Optional,
    Union,
)

from pydantic.dataclasses import dataclass

from .config import (
    BaseSetting,
    ClassCollectionField,
    ClassFileField,
)


class ActionType(Enum):
    """
    Documentation for ActionType.
    """

    FORMAT = "format"
    METADATA = "metadata"


class ActionsConditionalFilterType(Enum):
    PARAM_VALUE = "param_value"
    INSERT_COLUMN = "insert_column"
    COLUMN_STRIP = "column_strip"
    MULTIPLE_SPLITTER = "multiple_splitter"
    ATTRIBUTE_VALUE_SPLITTER = "attribute_value_splitter"
    COLUMN_REPLACE = "column_replace"
    METADATA_VALUE = "metadata_value"
    BOOLEAN = "boolean"
    STRING_FUNCTION = "string_function"


class ActionsOptionType(Enum):
    """
    Documentation for ActionsOptionType.
    """

    FROM_DATA_TABLE = "from_data_table"
    FROM_PARAM = "from_param"
    FROM_FILE = "from_file"


@dataclass(kw_only=True)
class AssertHasH5Attribute(BaseSetting):
    """Asserts HDF5 output contains the specified ``value`` for an attribute (``key``), e.g.
    ```xml
    &lt;has_h5_attribute key="nchroms" value="15" /&gt;
    ```
    $attribute_list::5"""

    key: Optional[str] = field(
        default=None, metadata={"type": "Attribute", "description": "HDF5 attribute to check value of."}
    )
    value: Optional[str] = field(
        default=None, metadata={"type": "Attribute", "description": "Expected value of HDF5 attribute to check."}
    )


@dataclass(kw_only=True)
class AssertHasH5Keys(BaseSetting):
    """Asserts HDF5 output has a set of attributes (``keys``), specified as a
    comma-separated list, e.g.
    ```xml
    &lt;has_h5_keys keys="bins,chroms,indexes,pixels,chroms/lengths" /&gt;
    ```
    $attribute_list::5"""

    keys: Optional[str] = field(
        default=None,
        metadata={"type": "Attribute", "description": "Comma-separated list of HDF5 attributes to check for."},
    )


@dataclass(kw_only=True)
class AssertHasJsonPropertyWithText(BaseSetting):
    """Asserts the JSON document contains a property or key with the specified text
    (i.e. string) value.

    ```xml
    &lt;has_json_property_with_text property="color" text="red" /&gt;
    ```
    $attribute_list::5
    """

    property: str = field(
        metadata={"type": "Attribute", "required": True, "description": "JSON property to search the target for."}
    )
    text: str = field(metadata={"type": "Attribute", "required": True, "description": "Text value to search for."})


@dataclass(kw_only=True)
class AssertHasJsonPropertyWithValue(BaseSetting):
    """Asserts the JSON document contains a property or key with the specified JSON
    value.

    ```xml
    &lt;has_json_property_with_value property="skipped_columns" value="[1, 3, 5]" /&gt;
    ```
    $attribute_list::5
    """

    property: str = field(
        metadata={"type": "Attribute", "required": True, "description": "JSON property to search the target for."}
    )
    value: str = field(
        metadata={
            "type": "Attribute",
            "required": True,
            "description": "JSON-ified value to search for. This will be converted from an XML string to JSON with Python's json.loads function.",
        }
    )


@dataclass(kw_only=True)
class AssertIsValidXml(BaseSetting):
    """Asserts the output is a valid XML file (e.g. ``&lt;is_valid_xml /&gt;``).

    $attribute_list::5
    """

    class Meta:
        name = "AssertIsValidXML"


@dataclass(kw_only=True)
class AssertNotHasText(BaseSetting):
    """Asserts the specified ``text`` does not appear in the output (e.g.
    ``&lt;not_has_text text="chr8" /&gt;``).

    $attribute_list::5
    """

    text: str = field(metadata={"type": "Attribute", "required": True, "description": "Text to check for"})


@dataclass(kw_only=True)
class ChangeFormatWhen(BaseSetting):
    """If the data type of the output dataset is the specified type, the data type
    is changed to the desired type.

    ### Examples
    Assume that your tool config includes the following select list parameter
    structure:
    ```xml
    &lt;param name="out_format" type="select" label="Output data type"&gt;
    &lt;option value="fasta"&gt;FASTA&lt;/option&gt;
    &lt;option value="interval"&gt;Interval&lt;/option&gt;
    &lt;/param&gt;
    ```
    Then whenever the user selects the ``interval`` option from the select list, the
    following structure in your tool config will override the ``format="fasta"`` setting
    in the ``&lt;data&gt;`` tag set with ``format="interval"``.
    ```xml
    &lt;outputs&gt;
    &lt;data format="fasta" name="out_file1"&gt;
    &lt;change_format&gt;
    &lt;when input="out_format" value="interval" format="interval" /&gt;
    &lt;/change_format&gt;
    &lt;/data&gt;
    &lt;/outputs&gt;
    ```
    See
    [extract_genomic_dna.xml](https://github.com/galaxyproject/tools-iuc/blob/main/tools/extract_genomic_dna/extract_genomic_dna.xml)
    or the test tool
    [output_format.xml](https://github.com/galaxyproject/galaxy/blob/dev/test/functional/tools/output_format.xml)
    for more examples.
    """

    input: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": 'This attribute should be the name of\nthe desired input parameter (e.g. ``input="out_format"`` above).',
        },
    )
    value: str = field(
        metadata={
            "type": "Attribute",
            "required": True,
            "description": 'This must be a possible value of the ``input``\nparameter (e.g. ``value="interval"`` above), or of the deprecated ``input_dataset``\'s\nattribute.',
        }
    )
    format: str = field(
        metadata={
            "type": "Attribute",
            "required": True,
            "description": 'This value must be a supported data type\n(e.g. ``format="interval"``). See\n[/config/datatypes_conf.xml.sample](https://github.com/galaxyproject/galaxy/blob/dev/config/datatypes_conf.xml.sample)\nfor a list of supported formats.',
        }
    )
    input_dataset: Optional[str] = field(default=None, metadata={"type": "Attribute", "description": "*Deprecated*."})
    attribute: Optional[str] = field(default=None, metadata={"type": "Attribute", "description": "*Deprecated*."})


class CitationType(Enum):
    """
    Type of citation represented.
    """

    BIBTEX = "bibtex"
    DOI = "doi"


@dataclass(kw_only=True)
class CodeHook(BaseSetting):
    """*Deprecated*.

    Map a hook to a function defined in the code file.
    """

    exec_after_process: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Function defined in the code file to which the ``exec_after_process`` hook should be mapped",
        },
    )


@dataclass(kw_only=True)
class Column(BaseSetting):
    """Optionally contained within an
    ``&lt;options&gt;`` tag set - specifies columns used in building select options from a
    file stored locally (i.e. index or tool data) or a dataset in the
    current history.
    Any number of columns may be described, but at least one must be given the name
    ``value`` and it will serve as the value of this parameter in the Cheetah
    template and elsewhwere (e.g. in API for instance).
    If a column named ``name`` is defined, this too has special meaning and it will
    be the value the tool form user sees for each option. If no ``name`` column
    appears, ``value`` will serve as the name.
    ### Examples
    The following fragment shows options from the dataset in the current history
    that has been selected as the value of the parameter named ``input1``.
    ```xml
    &lt;options from_dataset="input1"&gt;
    &lt;column name="name" index="0"/&gt;
    &lt;column name="value" index="0"/&gt;
    &lt;/options&gt;
    ```
    The [gff_filter_by_feature_count](https://github.com/galaxyproject/galaxy/blob/dev/tools/filters/gff/gff_filter_by_feature_count.xml)
    tool makes use of this tag with files from a history, and the
    [star_fusion](https://github.com/galaxyproject/tools-iuc/blob/main/tools/star_fusion/star_fusion.xml)
    tool makes use of this to reference a data table."""

    name: str = field(
        metadata={
            "type": "Attribute",
            "required": True,
            "description": "Name given to the column with index\n``index``, the names ``name`` and ``value`` have special meaning as described\nabove.",
        }
    )
    index: Decimal = field(
        metadata={
            "type": "Attribute",
            "required": True,
            "description": "0-based index of the column in the\ntarget file.",
        }
    )


class CompareType(Enum):
    """
    Documentation for CompareType.
    """

    STARTSWITH = "startswith"
    RE_SEARCH = "re_search"


@dataclass(kw_only=True)
class ConfigFile(BaseSetting):
    """This tag set is contained within the ``&lt;configfiles&gt;`` tag set.

    It allows for
    the creation of a temporary file for file-based parameter transfer.
    *Example*
    The following is taken from the [xy_plot.xml](https://github.com/galaxyproject/tools-devteam/blob/main/tools/xy_plot/xy_plot.xml)
    tool config.
    ```xml
    &lt;configfiles&gt;
    &lt;configfile name="script_file"&gt;
    ## Setup R error handling to go to stderr
    options(show.error.messages=F, error = function () { cat(geterrmessage(), file=stderr()); q("no", 1, F) })
    ## Determine range of all series in the plot
    xrange = c(NULL, NULL)
    yrange = c(NULL, NULL)
    #for $i, $s in enumerate($series)
    s${i} = read.table("${s.input.get_file_name()}")
    x${i} = s${i}[,${s.xcol}]
    y${i} = s${i}[,${s.ycol}]
    xrange = range(x${i}, xrange)
    yrange = range(y${i}, yrange)
    #end for
    ## Open output PDF file
    pdf("${out_file1}")
    ## Dummy plot for axis / labels
    plot(NULL, type="n", xlim=xrange, ylim=yrange, main="${main}", xlab="${xlab}", ylab="${ylab}")
    ## Plot each series
    #for $i, $s in enumerate($series)
    #if $s.series_type['type'] == "line"
    lines(x${i}, y${i}, lty=${s.series_type.lty}, lwd=${s.series_type.lwd}, col=${s.series_type.col})
    #elif $s.series_type.type == "points"
    points(x${i}, y${i}, pch=${s.series_type.pch}, cex=${s.series_type.cex}, col=${s.series_type.col})
    #end if
    #end for
    ## Close the PDF file
    devname = dev.off()
    &lt;/configfile&gt;
    &lt;/configfiles&gt;
    ```
    This file is then used in the ``command`` block of the tool as follows:
    ```xml
    &lt;command&gt;bash '$__tool_directory__/r_wrapper.sh' '$script_file'&lt;/command&gt;
    ```
    """

    value: str = field(default="", metadata={"required": True})
    name: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Cheetah variable used to reference\nthe path to the file created with this directive.",
        },
    )
    filename: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Path relative to the working directory of the tool for the configfile created in response to this directive.",
        },
    )


@dataclass(kw_only=True)
class ConfigFileSources(BaseSetting):
    value: str = field(default="", metadata={"required": True})
    name: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Cheetah variable to populate the path to the inputs JSON file created in\nresponse to this directive.",
        },
    )
    filename: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Path relative to the working directory of the tool for the file sources JSON configuration file created in response to this directive.",
        },
    )


@dataclass(kw_only=True)
class ConfigInputs(BaseSetting):
    """This tag set is contained within the ``&lt;configfiles&gt;`` tag set.

    It tells Galaxy to
    write out a JSON representation of the tool parameters.
    *Example*
    The following will create a Cheetah variable that can be evaluated as ``$inputs`` that
    will contain the tool parameter inputs.
    ```xml
    &lt;configfiles&gt;
    &lt;inputs name="inputs" /&gt;
    &lt;/configfiles&gt;
    ```
    The following will instead write the inputs to the tool's working directory with
    the specified name (i.e. ``inputs.json``).
    ```xml
    &lt;configfiles&gt;
    &lt;inputs name="inputs" filename="inputs.json" /&gt;
    &lt;/configfiles&gt;
    ```
    A contrived example of a tool that uses this is the test tool
    [inputs_as_json.xml](https://github.com/galaxyproject/galaxy/blob/dev/test/functional/tools/inputs_as_json.xml).
    By default this file will not contain paths for data or collection inputs. To include simple
    paths for data or collection inputs set the ``data_style`` attribute to ``paths`` (see [inputs_as_json_with_paths.xml](https://github.com/galaxyproject/galaxy/blob/dev/test/functional/tools/inputs_as_json_with_paths.xml) for an example).
    To include a dictionary with staging paths, paths and metadata files set the ``data_style`` attribute to ``staging_path_and_source_path``.
    An example tool that uses ``staging_path_and_source_path`` is [inputs_as_json_with_staging_path_and_source_path.xml](https://github.com/galaxyproject/galaxy/blob/dev/test/functional/tools/inputs_as_json_with_staging_path_and_source_path.xml)
    For tools with profile &gt;= 20.05 a select with ``multiple="true"`` is rendered as an array which is empty if nothing is selected. For older profile versions select lists are rendered as comma separated strings or a literal ``null`` in case nothing is selected.
    """

    value: str = field(default="", metadata={"required": True})
    name: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Cheetah variable to populate the path to the inputs JSON file created in\nresponse to this directive.",
        },
    )
    filename: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Path relative to the working directory of the tool for the inputs JSON file created in response to this directive.",
        },
    )
    data_style: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Set to 'paths' to include dataset paths in the resulting file. Set to 'staging_path_and_source_path' to include a staging path, a source path and all metadata files.",
        },
    )


class ContainerType(Enum):
    """
    Type of container for tool execution.
    """

    DOCKER = "docker"
    SINGULARITY = "singularity"


class DetectErrorType(Enum):
    DEFAULT = "default"
    EXIT_CODE = "exit_code"
    AGGRESSIVE = "aggressive"


class DisplayType(Enum):
    """
    Documentation for DisplayType.
    """

    CHECKBOXES = "checkboxes"
    RADIO = "radio"


@dataclass(kw_only=True)
class EdamOperations(BaseSetting):
    """Container tag set for the ``&lt;edam_operation&gt;`` tags.

    A tool can have any number of EDAM operation references.
    ```xml
    &lt;!-- Example: this tool performs a 'Conversion' operation (http://edamontology.org/operation_3434) --&gt;
    &lt;edam_operations&gt;
    &lt;edam_operation&gt;operation_3434&lt;/edam_operation&gt;
    &lt;/edam_operations&gt;
    ```
    """

    edam_operation: List[str] = field(default_factory=list, metadata={"type": "Element"})


@dataclass(kw_only=True)
class EdamTopics(BaseSetting):
    """Container tag set for the ``&lt;edam_topic&gt;`` tags.

    A tool can have any number of EDAM topic references.
    ```xml
    &lt;!-- Example: this tool is about 'Statistics and probability' (http://edamontology.org/topic_2269) --&gt;
    &lt;edam_topics&gt;
    &lt;edam_topic&gt;topic_2269&lt;/edam_topic&gt;
    &lt;/edam_topics&gt;
    ```
    """

    edam_topic: List[str] = field(default_factory=list, metadata={"type": "Element"})


@dataclass(kw_only=True)
class EntryPointPort(BaseSetting):
    """This tag set is contained within the ``&lt;entry_point&gt;`` tag set.

    It contains the entry port.
    """

    content: List[object] = field(
        default_factory=list, metadata={"type": "Wildcard", "namespace": "##any", "mixed": True}
    )


@dataclass(kw_only=True)
class EntryPointUrl(BaseSetting):
    """This tag set is contained within the ``&lt;entry_point&gt;`` tag set.

    It contains the entry URL.
    """

    class Meta:
        name = "EntryPointURL"

    content: List[object] = field(
        default_factory=list, metadata={"type": "Wildcard", "namespace": "##any", "mixed": True}
    )


class EnvironmentVariableInject(Enum):
    API_KEY = "api_key"
    ENTRY_POINT_PATH_FOR_LABEL = "entry_point_path_for_label"


class ExpressionType(Enum):
    ECMA5_1 = "ecma5.1"


class FilterType(Enum):
    DATA_META = "data_meta"
    PARAM_VALUE = "param_value"
    STATIC_VALUE = "static_value"
    REGEXP = "regexp"
    UNIQUE_VALUE = "unique_value"
    MULTIPLE_SPLITTER = "multiple_splitter"
    ATTRIBUTE_VALUE_SPLITTER = "attribute_value_splitter"
    ADD_VALUE = "add_value"
    REMOVE_VALUE = "remove_value"
    SORT_BY = "sort_by"


class HierarchyType(Enum):
    """
    Documentation for HierarchyType.
    """

    EXACT = "exact"
    RECURSE = "recurse"


@dataclass(kw_only=True)
class InputType(BaseSetting):
    """
    Documentation for InputType.
    """


class LevelType(Enum):
    """
    Documentation for LevelType.
    """

    FATAL_OOM = "fatal_oom"
    FATAL = "fatal"
    WARNING = "warning"
    LOG = "log"
    QC = "qc"


@dataclass(kw_only=True)
class Macros(BaseSetting):
    """Frequently, tools may require the same XML fragments be repeated in a file
    (for instance similar conditional branches, repeated options, etc...) or among
    tools in the same repository.

    Galaxy tools
    have a macro system to address this problem.
    For more information, see [planemo documentation](https://planemo.readthedocs.io/en/latest/writing_advanced.html#macros-reusable-elements)
    """

    import_value: List[str] = field(
        default_factory=list,
        metadata={
            "name": "import",
            "type": "Element",
            "description": "The ``import`` element allows specifying an XML file containing shared macro definitions that can then\nbe reused by all the tools contained in the same directory/repository.\nExample:\n````\n&lt;macros&gt;\n&lt;import&gt;macros.xml&lt;/import&gt;\n&lt;/macros&gt;\n````",
        },
    )
    token: List[object] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "description": 'The ``token`` element defines a value, like a constant, that can then be replaced anywhere in any tool importing the token.\nDefinition example:\n````\n&lt;macros&gt;\n&lt;token name="@TOOL_VERSION@"&gt;1.0.0&lt;/token&gt;\n&lt;/macros&gt;\n````\nUsage example:\n````\n&lt;requirements&gt;\n&lt;requirement type="package" version="@TOOL_VERSION@"&gt;mypackage&lt;/requirement&gt;\n&lt;/requirements&gt;\n````',
        },
    )
    xml: List[object] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "description": 'The ``xml`` element, inside macros, allows defining a named XML fragment that can be reused (expanded) anywhere in the tool or tools that use the macro.\nDefinition example:\n````\n&lt;macros&gt;\n&lt;xml name="citations"&gt;\n&lt;citations&gt;\n....\n&lt;/citations&gt;\n&lt;/xml&gt;\n&lt;/macros&gt;\n````\nUsage example:\n````\n&lt;expand macro="citations" /&gt;\n````',
        },
    )


class MethodType(Enum):
    """
    Documentation for MethodType.
    """

    BASIC = "basic"
    MULTI = "multi"


@dataclass(kw_only=True)
class Organization(BaseSetting):
    """Describes an organization.

    Tries to stay close to [schema.org/Organization](https://schema.org/Organization).
    """

    name: Optional[str] = field(
        default=None, metadata={"type": "Attribute", "description": "[schema.org/name](https://schema.org/name)"}
    )
    url: Optional[str] = field(
        default=None, metadata={"type": "Attribute", "description": "[schema.org/url](https://schema.org/url)"}
    )
    identifier: Optional[str] = field(
        default=None,
        metadata={"type": "Attribute", "description": "[schema.org/identifier](https://schema.org/identifier)"},
    )
    image: Optional[str] = field(
        default=None, metadata={"type": "Attribute", "description": "[schema.org/image](https://schema.org/image)"}
    )
    address: Optional[str] = field(
        default=None, metadata={"type": "Attribute", "description": "[schema.org/address](https://schema.org/address)"}
    )
    email: Optional[str] = field(
        default=None, metadata={"type": "Attribute", "description": "[schema.org/email](https://schema.org/email)"}
    )
    telephone: Optional[str] = field(
        default=None,
        metadata={"type": "Attribute", "description": "[schema.org/telephone](https://schema.org/telephone)"},
    )
    fax_number: Optional[str] = field(
        default=None,
        metadata={
            "name": "faxNumber",
            "type": "Attribute",
            "description": "[schema.org/faxNumber](https://schema.org/faxNumber)",
        },
    )
    alternate_name: Optional[str] = field(
        default=None,
        metadata={
            "name": "alternateName",
            "type": "Attribute",
            "description": "[schema.org/alternateName](https://schema.org/alternateName)",
        },
    )


@dataclass(kw_only=True)
class OutputCollectionDiscoverDatasets(BaseSetting):
    """This tag allows one to describe the datasets contained within an output
    collection dynamically, such that the outputs are "discovered" based on regular
    expressions after the job is complete.

    There are many simple tools with examples of this element distributed with
    Galaxy, including:
    * [collection_split_on_column.xml](https://github.com/galaxyproject/galaxy/blob/dev/test/functional/tools/collection_split_on_column.xml)
    * [collection_creates_dynamic_list_of_pairs.xml](https://github.com/galaxyproject/galaxy/blob/dev/test/functional/tools/collection_creates_dynamic_list_of_pairs.xml)
    * [collection_creates_dynamic_nested.xml](https://github.com/galaxyproject/galaxy/blob/dev/test/functional/tools/collection_creates_dynamic_nested.xml)
    """

    from_provided_metadata: Optional[bool] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Indicate that dataset filenames should simply be read from the provided metadata file (e.g. galaxy.json). If this is set - pattern and sort_by must not be set.",
        },
    )
    pattern: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Regular expression used to find filenames and parse dynamic properties.",
        },
    )
    directory: Optional[str] = field(
        default=None,
        metadata={"type": "Attribute", "description": "Directory (relative to working directory) to search for files."},
    )
    recurse: Optional[bool] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Indicates that the specified directory should be searched recursively for matching files.",
        },
    )
    match_relative_path: Optional[bool] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Indicates that the entire path of the discovered dataset relative to the specified directory should be available for matching patterns.",
        },
    )
    format: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Format (or datatype) of discovered datasets (an alias with ``ext``).",
        },
    )
    ext: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Format (or datatype) of discovered datasets (an alias with ``format``).",
        },
    )
    sort_by: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "A string `[reverse_][SORT_COMP_]SORTBY` describing the desired sort order of the collection elements. `SORTBY` can be `filename`, `name`, `designation`, `dbkey` and the optional `SORT_COMP` can be either `lexical` or `numeric`. Default is lexical sorting by filename.",
        },
    )
    visible: Optional[bool] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Indication if this dataset is visible in the history. This defaults to ``false``, but probably shouldn't - be sure to set to ``true`` if that is your intention.",
        },
    )


@dataclass(kw_only=True)
class OutputDiscoverDatasets(BaseSetting):
    """Describe datasets to dynamically collect after the job complete.

    There are many simple tools with examples of this element distributed with
    Galaxy, including:
    * [multi_output.xml](https://github.com/galaxyproject/galaxy/blob/dev/test/functional/tools/multi_output.xml)
    * [multi_output_assign_primary.xml](https://github.com/galaxyproject/galaxy/blob/dev/test/functional/tools/multi_output_assign_primary.xml)
    * [multi_output_configured.xml](https://github.com/galaxyproject/galaxy/blob/dev/test/functional/tools/multi_output_configured.xml)
    More information can be found on Planemo's documentation for
    [multiple output files](https://planemo.readthedocs.io/en/latest/writing_advanced.html#multiple-output-files).
    """

    from_provided_metadata: Optional[bool] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Indicate that dataset filenames should simply be read from the provided metadata file (e.g. galaxy.json). If this is set - pattern and sort must not be set.",
        },
    )
    pattern: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Regular expression used to find filenames and parse dynamic properties.",
        },
    )
    directory: Optional[str] = field(
        default=None,
        metadata={"type": "Attribute", "description": "Directory (relative to working directory) to search for files."},
    )
    recurse: Optional[bool] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Indicates that the specified directory should be searched recursively for matching files.",
        },
    )
    match_relative_path: Optional[bool] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Indicates that the entire path of the discovered dataset relative to the specified directory should be available for matching patterns.",
        },
    )
    format: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Format (or datatype) of discovered datasets (an alias with ``ext``).",
        },
    )
    ext: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Format (or datatype) of discovered datasets (an alias with ``format``).",
        },
    )
    sort_by: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "A string `[reverse_][SORT_COMP_]SORTBY` describing the desired sort order of the collection elements. `SORTBY` can be `filename`, `name`, `designation`, `dbkey` and the optional `SORT_COMP` can be either `lexical` or `numeric`. Default is lexical sorting by filename.",
        },
    )
    visible: Optional[bool] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Indication if this dataset is visible in output history. This defaults to ``false``, but probably shouldn't - be sure to set to ``true`` if that is your intention.",
        },
    )
    assign_primary_output: Optional[bool] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Replace the primary dataset described by the parameter ``data`` parameter with the first output discovered.",
        },
    )


@dataclass(kw_only=True)
class ParamConversion(BaseSetting):
    """A contrived example of a tool that uses this is the test tool
    [explicit_conversion.xml](https://github.com/galaxyproject/galaxy/blob/dev/test/functional/tools/explicit_conversion.xml).
    This directive is optionally contained within the ``&lt;param&gt;`` tag when the
    ``type`` attribute value is ``data`` and is used to dynamically generated a converted
    dataset for the contained input of the type specified using the ``type`` tag."""

    name: str = field(
        metadata={
            "type": "Attribute",
            "required": True,
            "description": "Name of Cheetah variable to create for converted dataset.",
        }
    )
    type_value: str = field(
        metadata={
            "name": "type",
            "type": "Attribute",
            "required": True,
            "description": "The short extension describing the datatype to convert to - Galaxy must have a datatype converter from the parent input's type to this.",
        }
    )


@dataclass(kw_only=True)
class ParamDefaultCollection(BaseSetting):
    element: List["ParamDefaultElement"] = field(default_factory=list, metadata={"type": "Element"})
    collection_type: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Collection type for default collection (if param type is data_collection). Simple collection types are\neither ``list`` or ``paired``, nested collections are specified as colon separated list of simple\ncollection types (the most common types are ``list``, ``paired``,\n``list:paired``, or ``list:list``).",
        },
    )


@dataclass(kw_only=True)
class ParamDrillDownOption(BaseSetting):
    """See [drill_down.xml](https://github.com/galaxyproject/galaxy/blob/dev/test/functional/tools/drill_down.xml)"""

    option: List["ParamDrillDownOption"] = field(default_factory=list, metadata={"type": "Element"})
    name: str = field(
        metadata={"type": "Attribute", "required": True, "description": "Name of the ``drill_down`` option."}
    )
    value: str = field(
        metadata={"type": "Attribute", "required": True, "description": "Value of the ``drill_down`` option."}
    )


class ParamType(Enum):
    """
    Documentation for ParamType.
    """

    TEXT = "text"
    INTEGER = "integer"
    FLOAT = "float"
    COLOR = "color"
    BOOLEAN = "boolean"
    GENOMEBUILD = "genomebuild"
    SELECT = "select"
    DATA_COLUMN = "data_column"
    HIDDEN = "hidden"
    HIDDEN_DATA = "hidden_data"
    BASEURL = "baseurl"
    FILE = "file"
    DATA = "data"
    DRILL_DOWN = "drill_down"
    GROUP_TAG = "group_tag"
    DATA_COLLECTION = "data_collection"
    DIRECTORY_URI = "directory_uri"


class PermissiveBooleanValue(Enum):
    VALUE_0 = "0"
    VALUE_1 = "1"
    TRUE = "true"
    FALSE = "false"
    TRUE_1 = "True"
    FALSE_1 = "False"
    YES = "yes"
    NO = "no"


@dataclass(kw_only=True)
class Person(BaseSetting):
    """Describes a person.

    Tries to stay close to [schema.org/Person](https://schema.org/Person).
    """

    name: Optional[str] = field(
        default=None, metadata={"type": "Attribute", "description": "[schema.org/name](https://schema.org/name)"}
    )
    url: Optional[str] = field(
        default=None, metadata={"type": "Attribute", "description": "[schema.org/url](https://schema.org/url)"}
    )
    identifier: Optional[str] = field(
        default=None,
        metadata={"type": "Attribute", "description": "[schema.org/identifier](https://schema.org/identifier)"},
    )
    image: Optional[str] = field(
        default=None, metadata={"type": "Attribute", "description": "[schema.org/image](https://schema.org/image)"}
    )
    address: Optional[str] = field(
        default=None, metadata={"type": "Attribute", "description": "[schema.org/address](https://schema.org/address)"}
    )
    email: Optional[str] = field(
        default=None, metadata={"type": "Attribute", "description": "[schema.org/email](https://schema.org/email)"}
    )
    telephone: Optional[str] = field(
        default=None,
        metadata={"type": "Attribute", "description": "[schema.org/telephone](https://schema.org/telephone)"},
    )
    fax_number: Optional[str] = field(
        default=None,
        metadata={
            "name": "faxNumber",
            "type": "Attribute",
            "description": "[schema.org/faxNumber](https://schema.org/faxNumber)",
        },
    )
    alternate_name: Optional[str] = field(
        default=None,
        metadata={
            "name": "alternateName",
            "type": "Attribute",
            "description": "[schema.org/alternateName](https://schema.org/alternateName)",
        },
    )
    given_name: Optional[str] = field(
        default=None,
        metadata={
            "name": "givenName",
            "type": "Attribute",
            "description": "[schema.org/givenName](https://schema.org/givenName)",
        },
    )
    family_name: Optional[str] = field(
        default=None,
        metadata={
            "name": "familyName",
            "type": "Attribute",
            "description": "[schema.org/familyName](https://schema.org/familyName)",
        },
    )
    honorific_prefix: Optional[str] = field(
        default=None,
        metadata={
            "name": "honorificPrefix",
            "type": "Attribute",
            "description": "[schema.org/honorificPrefix](https://schema.org/honorificPrefix)",
        },
    )
    honorific_suffix: Optional[str] = field(
        default=None,
        metadata={
            "name": "honorificSuffix",
            "type": "Attribute",
            "description": "[schema.org/honorificSuffix](https://schema.org/honorificSuffix)",
        },
    )
    job_title: Optional[str] = field(
        default=None,
        metadata={
            "name": "jobTitle",
            "type": "Attribute",
            "description": "[schema.org/jobTitle](https://schema.org/jobTitle)",
        },
    )


@dataclass(kw_only=True)
class RequestParameterAppendValue(BaseSetting):
    """Contained within the [append_param](#tool-request-param-translation-request-
    param-append-param) tag set.

    Allows for appending a param name / value pair to the value of URL.
    Example:
    ```xml
    &lt;request_param_translation&gt;
    &lt;request_param galaxy_name="URL" remote_name="URL" missing=""&gt;
    &lt;append_param separator="&amp;amp;" first_separator="?" join="="&gt;
    &lt;value name="_export" missing="1" /&gt;
    &lt;/append_param&gt;
    &lt;/request_param&gt;
    &lt;/request_param_tranlsation&gt;
    ```
    """

    name: str = field(
        metadata={
            "type": "Attribute",
            "required": True,
            "description": 'Any valid HTTP request parameter name. The name / value pair must be received from the remote data source and will be appended to the value of URL as something like ``"&amp;_export=1"`` (e.g. ``name="_export"``).',
        }
    )
    missing: str = field(
        metadata={
            "type": "Attribute",
            "required": True,
            "description": 'Must be a valid HTTP request parameter value (e.g. ``missing="1"``).',
        }
    )


class RequestParameterGalaxyNameType(Enum):
    URL = "URL"
    URL_METHOD = "URL_method"
    DBKEY = "dbkey"
    ORGANISM = "organism"
    TABLE = "table"
    DESCRIPTION = "description"
    NAME = "name"
    INFO = "info"
    DATA_TYPE = "data_type"


@dataclass(kw_only=True)
class RequestParameterValueTranslationValue(BaseSetting):
    """Contained within the [value_translation](#tool-request-param-translation-request-param-value-translation) tag set - allows for changing the data type value to something supported by Galaxy.
    Example:
    ```xml
    &lt;request_param_translation&gt;
    &lt;request_param galaxy_name="data_type" remote_name="hgta_outputType" missing="bed" &gt;
    &lt;value_translation&gt;
    &lt;value galaxy_value="tabular" remote_value="primaryTable" /&gt;
    &lt;/value_translation&gt;
    &lt;/request_param&gt;
    &lt;/request_param_tranlsation&gt;
    ```"""

    galaxy_value: str = field(
        metadata={
            "type": "Attribute",
            "required": True,
            "description": "The target value (e.g. for setting data format: the list of supported data formats is contained in the\n[/config/datatypes_conf.xml.sample](https://github.com/galaxyproject/galaxy/blob/dev/config/datatypes_conf.xml.sample).",
        }
    )
    remote_value: str = field(
        metadata={
            "type": "Attribute",
            "required": True,
            "description": "The value supplied by the remote data source application",
        }
    )


class RequiredFileReferenceType(Enum):
    """How are files referenced in RequiredFileIncludes and RequiredFileExcludes.

    Paths are matched relative to the tool directory. `literal` must match the filename exactly. `prefix` will match paths based on their start. `glob` and `regex` use patterns to match files.
    """

    LITERAL = "literal"
    PREFIX = "prefix"
    GLOB = "glob"
    REGEX = "regex"


class RequirementType(Enum):
    """
    Documentation for RequirementType.
    """

    PYTHON_MODULE = "python-module"
    BINARY = "binary"
    PACKAGE = "package"
    SET_ENVIRONMENT = "set_environment"


class ResourceType(Enum):
    """
    Type of resource specification.
    """

    CORES_MIN = "cores_min"
    CORES_MAX = "cores_max"
    RAM_MIN = "ram_min"
    RAM_MAX = "ram_max"
    TMPDIR_MIN = "tmpdir_min"
    TMPDIR_MAX = "tmpdir_max"
    CUDA_VERSION_MIN = "cuda_version_min"
    CUDA_COMPUTE_CAPABILITY = "cuda_compute_capability"
    GPU_MEMORY_MIN = "gpu_memory_min"
    CUDA_DEVICE_COUNT_MIN = "cuda_device_count_min"
    CUDA_DEVICE_COUNT_MAX = "cuda_device_count_max"


ResourceType.CORES_MIN.__doc__ = (
    "Minimum reserved number of CPU cores, if runtime allows it (not yet implemented in Galaxy)."
)
ResourceType.CORES_MAX.__doc__ = (
    "Maximum reserved number of CPU cores, if runtime allows it (not yet implemented in Galaxy)."
)
ResourceType.RAM_MIN.__doc__ = (
    "Minimum reserved RAM in mebibytes (2**20 bytes), if runtime allows it (not yet implemented in Galaxy)."
)
ResourceType.RAM_MAX.__doc__ = (
    "Maximum reserved RAM in mebibytes (2**20 bytes), if runtime allows it (not yet implemented in Galaxy)."
)
ResourceType.TMPDIR_MIN.__doc__ = "Minimum reserved filesystem-based storage for the designated temporary directory in mebibytes (2**20 bytes), if runtime allows it (not yet implemented in Galaxy)."
ResourceType.TMPDIR_MAX.__doc__ = "Maximum reserved filesystem based storage for the designated temporary directory, in mebibytes (2**20 bytes), if runtime allows it (not yet implemented in Galaxy)."
ResourceType.CUDA_VERSION_MIN.__doc__ = (
    "Minimum CUDA (runtime link library) runtime version, if runtime allows it (not yet implemented in Galaxy)."
)
ResourceType.CUDA_COMPUTE_CAPABILITY.__doc__ = "Minimum NVIDIA (hardware+driver) Compute capabilities (major, minor (can be a range or a list), if runtime allows it (not yet implemented in Galaxy)."
ResourceType.GPU_MEMORY_MIN.__doc__ = (
    "Minimum Memory of the GPU in mebibytes, if runtime allows it (not yet implemented in Galaxy)."
)
ResourceType.CUDA_DEVICE_COUNT_MIN.__doc__ = (
    "Minimum CUDA device count, if runtime allows it (not yet implemented in Galaxy)."
)
ResourceType.CUDA_DEVICE_COUNT_MAX.__doc__ = (
    "Maximum CUDA device count, if runtime allows it (not yet implemented in Galaxy)."
)


@dataclass(kw_only=True)
class SanitizerMappingAdd(BaseSetting):
    """Use to add character mapping during sanitization.

    Character must not be allowed as a valid input for the mapping to occur.
    """

    source: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Replace all occurrences of this character with the string of ``target``.",
        },
    )
    target: Optional[str] = field(
        default=None,
        metadata={"type": "Attribute", "description": "Replace all occurrences of ``source`` with this string"},
    )


@dataclass(kw_only=True)
class SanitizerMappingRemove(BaseSetting):
    """
    Use to remove character mapping during sanitization.
    """

    source: Optional[str] = field(
        default=None, metadata={"type": "Attribute", "description": "Character to remove from mapping."}
    )


@dataclass(kw_only=True)
class SanitizerValidAdd(BaseSetting):
    """This directive is used to add individual characters or preset lists of
    characters.

    Character must not be allowed as a valid input for the mapping to occur.
    """

    preset: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Add the characters contained in the specified character preset (as defined above) to the list of valid characters. The default\nis the ``none`` preset.",
        },
    )
    value: Optional[str] = field(
        default=None, metadata={"type": "Attribute", "description": "Add a character to the list of valid characters."}
    )


@dataclass(kw_only=True)
class SanitizerValidRemove(BaseSetting):
    """This directive is used to remove individual characters or preset lists of
    characters.

    Character must not be allowed as a valid input for the mapping to occur.
    """

    preset: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Remove the characters contained in the specified character preset (as defined above) from the list of valid characters. The default\nis the ``none`` preset.",
        },
    )
    value: Optional[str] = field(
        default=None,
        metadata={"type": "Attribute", "description": "A character to remove from the list of valid characters."},
    )


class SourceType(Enum):
    """
    Documentation for SourceType.
    """

    STDOUT = "stdout"
    STDERR = "stderr"
    BOTH = "both"


class TargetType(Enum):
    """
    Documentation for TargetType.
    """

    TOP = "_top"
    PARENT = "_parent"


@dataclass(kw_only=True)
class TestCollection(BaseSetting):
    """
    Definition of a collection for test input.
    """

    element: List["TestParam"] = field(default_factory=list, metadata={"type": "Element"})
    type_value: str = field(
        metadata={"name": "type", "type": "Attribute", "required": True, "description": "Type of collection to create."}
    )
    name: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": 'The identifier of the collection. Default is ``"Unnamed Collection"``',
        },
    )
    tags: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Comma separated list of tags to apply to the dataset (only works for elements of collections - e.g. ``element`` XML tags).",
        },
    )


@dataclass(kw_only=True)
class TestCompositeData(BaseSetting):
    """Define extra composite input files for test input.

    The specified ``ftype`` on the parent ``param`` should specify a composite
    datatype with defined static composite files. The order of the defined composite
    files on the datatype must match the order specified with these elements and All
    non-optional composite inputs must be specified as part of the ``param``.
    """

    value: str = field(
        metadata={"type": "Attribute", "required": True, "description": "Path relative to test-data of composite file."}
    )


class TestOutputCompareType(Enum):
    """Type of comparison to use when comparing test generated output files to
    expected output files.

    Currently valid value are
    ``diff`` (the default), ``re_match``, ``re_match_multiline``,
    and ``contains``. In addition there is ``sim_size`` which is discouraged in favour of a ``has_size`` assertion.
    """

    DIFF = "diff"
    RE_MATCH = "re_match"
    SIM_SIZE = "sim_size"
    RE_MATCH_MULTILINE = "re_match_multiline"
    CONTAINS = "contains"


@dataclass(kw_only=True)
class TestOutputMetadata(BaseSetting):
    """This directive specifies a test for an output's metadata as an expected key-
    value pair.

    ### Example
    The functional test tool
    [tool_provided_metadata_1.xml](https://github.com/galaxyproject/galaxy/blob/dev/test/functional/tools/tool_provided_metadata_1.xml)
    provides a demonstration of using this tag.
    ```xml
    &lt;test&gt;
    &lt;param name="input1" value="simple_line.txt" /&gt;
    &lt;output name="out1" file="simple_line.txt" ftype="txt"&gt;
    &lt;metadata name="name" value="my dynamic name" /&gt;
    &lt;metadata name="info" value="my dynamic info" /&gt;
    &lt;metadata name="dbkey" value="cust1" /&gt;
    &lt;/output&gt;
    &lt;/test&gt;
    ```
    """

    name: str = field(
        metadata={"type": "Attribute", "required": True, "description": "Name of the metadata element to check."}
    )
    value: str = field(
        metadata={
            "type": "Attribute",
            "required": True,
            "description": "Expected value (as a string) of metadata value.",
        }
    )


@dataclass(kw_only=True)
class TestParamMetadata(BaseSetting):
    """This directive specifies metadata that should be set for a test data
    parameter.

    See [planemo documentation](https://planemo.readthedocs.io/en/latest/writing_how_do_i.html#test-metadata)
    """

    name: str = field(
        metadata={
            "type": "Attribute",
            "required": True,
            "description": "Name of the metadata element of the data parameter",
        }
    )
    value: str = field(metadata={"type": "Attribute", "required": True, "description": "Value to set"})


@dataclass(kw_only=True)
class ToolAction(BaseSetting):
    """
    Describe the backend Python action to execute for this Galaxy tool.
    """

    module: str = field(metadata={"type": "Attribute", "required": True})
    class_value: str = field(metadata={"name": "class", "type": "Attribute", "required": True})


class ToolTypeType(Enum):
    """
    Documentation for ToolTypeType.
    """

    DATA_SOURCE = "data_source"
    MANAGE_DATA = "manage_data"
    INTERACTIVE = "interactive"
    EXPRESSION = "expression"


@dataclass(kw_only=True)
class TracksterAction(BaseSetting):
    name: Optional[str] = field(default=None, metadata={"type": "Attribute"})
    output_name: Optional[str] = field(default=None, metadata={"type": "Attribute"})


@dataclass(kw_only=True)
class Uihints(BaseSetting):
    """
    Used only for data source tools, this directive contains UI options (currently
    only ``minwidth`` is valid).
    """

    class Meta:
        name = "UIhints"

    minwidth: Optional[int] = field(
        default=None, metadata={"type": "Attribute", "description": "Documentation for minwidth"}
    )


class UrlmethodType(Enum):
    """
    Documentation for URLmethodType.
    """

    GET = "get"
    POST = "post"


class ValidatorType(Enum):
    """
    Documentation for ValidatorType.
    """

    EMPTY_DATASET = "empty_dataset"
    EMPTY_EXTRA_FILES_PATH = "empty_extra_files_path"
    EXPRESSION = "expression"
    REGEX = "regex"
    IN_RANGE = "in_range"
    LENGTH = "length"
    METADATA = "metadata"
    DATASET_METADATA_EQUAL = "dataset_metadata_equal"
    UNSPECIFIED_BUILD = "unspecified_build"
    NO_OPTIONS = "no_options"
    EMPTY_FIELD = "empty_field"
    DATASET_METADATA_IN_FILE = "dataset_metadata_in_file"
    DATASET_METADATA_IN_DATA_TABLE = "dataset_metadata_in_data_table"
    DATASET_METADATA_NOT_IN_DATA_TABLE = "dataset_metadata_not_in_data_table"
    VALUE_IN_DATA_TABLE = "value_in_data_table"
    VALUE_NOT_IN_DATA_TABLE = "value_not_in_data_table"
    DATASET_METADATA_IN_RANGE = "dataset_metadata_in_range"
    DATASET_OK_VALIDATOR = "dataset_ok_validator"


@dataclass(kw_only=True)
class VersionCommand(BaseSetting):
    """Specifies the command to be run in
    order to get the tool's version string. The resulting value will be found in the
    "Info" field of the history dataset.
    Unlike the [command](#tool-command) tag, with the exception of the string
    ``$__tool_directory__`` this value is taken as a literal and so there is no
    need to escape values like ``$`` and command inputs are not available for variable
    substitution.
    ### Examples
    A simple example for a [TopHat](https://ccb.jhu.edu/software/tophat/index.shtml)
    tool definition might just be:
    ```xml
    &lt;version_command&gt;tophat -version&lt;/version_command&gt;
    ```
    An example that leverages a Python script (e.g. ``count_reads.py``) shipped with
    the tool might be:
    ```xml
    &lt;version_command&gt;python '$__tool_directory__/count_reads.py'&lt;/version_command&gt;
    ```
    Examples are included in the test tools directory including:
    - [version_command_plain.xml](https://github.com/galaxyproject/galaxy/blob/dev/test/functional/tools/version_command_plain.xml)
    - [version_command_tool_dir.xml](https://github.com/galaxyproject/galaxy/blob/dev/test/functional/tools/version_command_tool_dir.xml)
    - [version_command_interpreter.xml](https://github.com/galaxyproject/galaxy/blob/dev/test/functional/tools/version_command_interpreter.xml) (*deprecated*)
    """

    value: str = field(default="", metadata={"required": True})
    interpreter: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "*Deprecated*. This will prefix the version command with the value of this attribute (e.g. ``python`` or ``perl``) and the tool directory, in order to run an executable file shipped with the tool. It is recommended to instead use ``&lt;interpreter&gt; '$__tool_directory__/&lt;executable_name&gt;'`` in the tag content. If this attribute is not specified, the tag should contain a Bash command calling executable(s) available in the ``$PATH``, as modified after loading the requirements.",
        },
    )


class XrefType(Enum):
    """
    Type of Reference.
    """

    BIO_TOOLS = "bio.tools"
    BIOCONDUCTOR = "bioconductor"
    BIII = "biii"


@dataclass(kw_only=True)
class ActionsConditionalFilter(BaseSetting):
    type_value: ActionsConditionalFilterType = field(
        metadata={
            "name": "type",
            "type": "Attribute",
            "required": True,
            "description": "``param_value``\n- get the value of a refered parameter (``ref``) or the value given by ``value``\n- if ``param_attribute`` is given the corresponding attribute of the value of the reffered parameter is used ``ref``\n- cast this value with the function given by ``cast``\n- compare the each the value in the column given by ``column`` (also casted) with the determined value using the function given by ``compare``\n- if the result of the comparison is equal to the boolean given by ``keep`` the value is kept\n``insert_column``\n- insert a column with a value in the options\n- if ``column`` is given then the column is inserted before this column, otherwise the column is appended\n- the value can be given by ``ref`` or ``value``\n``column_strip``\nStrip (remove certain characters from the suffix / prefix) values in a column.\nThe characters to strip can be given by ``strip`` (deafult is whitespace\ncharacters)\n``multiple_splitter``\nSplit the values in a ``column`` by a given ``separator``. And replace the\noriginal column with the with columns containing the result of splitting.\n``column_replace``\nReplace values in a column. The old and new values can be given\n- as static values ``old_value`` or ``new_value``\n- dynamically by the contents in (another) column ``old_column`` or ``new_colum``\n``metadata_value``\nFilter values in ``column`` by the metadata element ``name`` of the referred\nparameter ``ref`` depending on the results of the comparison function given by\nwith ``compare`` and the value of ``keep`` (i.e. if the result of the\ncomparision is equal to ``keep`` then keep the option).\n``boolean``\nCast the values in ``column`` using the cast function given by ``cast``\n(unaccessible / uncastable values are interpreted as False).  The result of this\ncast is then casted with the bool function. If the final result is equal to\n``keep`` the option.\n``string_function``\nApply a string function to the values in ``column``. The string function is given by ``name``.",
        }
    )
    compare: Optional[CompareType] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Function to use for the comparision. One of startswith, re_search.\nApplies to: ``param_value``, ``metadata_value``",
        },
    )
    ref: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Name of an input parameter (parameters in conditionals or sections are referred using the dot syntax, e.g. ``cond.paramname``).\nApplies to ``param_value``, ``insert_column``, ``metadata_value``",
        },
    )
    value: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Fixed value to use for the comparison.\nApplies to ``param_value``, ``insert_column``",
        },
    )
    column: Optional[int] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Column of the options (0 based).\nApplies to ``param_value``, ``insert_column``, ``column_strip``, ``multiple_splitter``, ``column_replace``, ``metadata_value``, ``boolean``, ``string_function``",
        },
    )
    keep: Optional[Union[bool, PermissiveBooleanValue]] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Keep the value if the filter condition is met. default: true\nApplies to ``param_value``, ``metadata_value``, ``boolean``",
        },
    )
    cast: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "one of string_as_bool, int, str function used for casting the value.\nApplies to ``param_value``, ``boolean``&lt;/xs:documentation&gt;",
        },
    )
    iterate: Optional[Union[bool, PermissiveBooleanValue]] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Applies to ``insert_column``. Default is ``False``&lt;/xs:documentation&gt;",
        },
    )
    param_attribute: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Which atttribute of the parameter value referred by ``ref`` to use. Separate with ``.``.\nApplies to ``param_value``",
        },
    )
    separator: Optional[str] = field(
        default=None, metadata={"type": "Attribute", "description": "Applies to ``multiple_splitter``"}
    )
    strip: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Applies to ``column_strip``. The given string is removed from the start or end of the column.",
        },
    )
    old_column: Optional[str] = field(
        default=None, metadata={"type": "Attribute", "description": "Applies to ``column_replace``"}
    )
    old_value: Optional[str] = field(
        default=None, metadata={"type": "Attribute", "description": "Applies to ``column_replace``"}
    )
    new_column: Optional[str] = field(
        default=None, metadata={"type": "Attribute", "description": "Applies to ``column_replace``"}
    )
    new_value: Optional[str] = field(
        default=None, metadata={"type": "Attribute", "description": "Applies to ``column_replace``"}
    )
    name: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "For ``metadata_value`` this is the name of the metadata to use. For ``string``\nfunction the string function to use (currently ``lower`` or ``upper``).\nApplies to ``metadata_value``, ``string_function``",
        },
    )


@dataclass(kw_only=True)
class AssertAttributeIs(BaseSetting):
    """Asserts the XML ``attribute`` for the element (or tag) with the specified
    XPath-like ``path`` is the specified ``text``, e.g. ```xml &lt;attribute_is
    path="outerElement/innerElement1" attribute="foo" text="bar" /&gt; ``` The
    assertion implicitly also asserts that an element matching ``path`` exists.

    With ``negate`` the result of the assertion (on the equality) can be inverted (the
    implicit assertion on the existence of the path is not affected).
    $attribute_list::5
    """

    path: str = field(
        metadata={
            "type": "Attribute",
            "required": True,
            "description": "Path to check for. Valid paths are the simplified subsets of XPath implemented by lxml.etree; https://lxml.de/xpathxslt.html for more information.",
        }
    )
    text: str = field(metadata={"type": "Attribute", "required": True, "description": "Text to check for."})
    negate: Union[bool, PermissiveBooleanValue] = field(
        default=PermissiveBooleanValue.FALSE,
        metadata={"type": "Attribute", "description": "Negate the outcome of the assertion."},
    )


@dataclass(kw_only=True)
class AssertAttributeMatches(BaseSetting):
    """Asserts the XML ``attribute`` for the element (or tag) with the specified
    XPath-like ``path`` matches the regular expression specified by ``expression``,
    e.g. ```xml &lt;attribute_matches path="outerElement/innerElement2"
    attribute="foo2" expression="bar\\d+" /&gt; ``` The assertion implicitly also
    asserts that an element matching ``path`` exists.

    With ``negate`` the result of the assertion (on the matching) can be inverted (the
    implicit assertion on the existence of the path is not affected).
    $attribute_list::5
    """

    path: str = field(
        metadata={
            "type": "Attribute",
            "required": True,
            "description": "Path to check for. Valid paths are the simplified subsets of XPath implemented by lxml.etree; https://lxml.de/xpathxslt.html for more information.",
        }
    )
    expression: str = field(
        metadata={"type": "Attribute", "required": True, "description": "The regular expression to use."}
    )
    negate: Union[bool, PermissiveBooleanValue] = field(
        default=PermissiveBooleanValue.FALSE,
        metadata={"type": "Attribute", "description": "Negate the outcome of the assertion."},
    )


@dataclass(kw_only=True)
class AssertElementTextIs(BaseSetting):
    """Asserts the text of the XML element with the specified XPath-like ``path``
    is the specified ``text``, e.g. ```xml &lt;element_text_is
    path="BlastOutput_program" text="blastp" /&gt; ``` The assertion implicitly
    also asserts that an element matching ``path`` exists.

    With ``negate`` the result of the assertion (on the equality) can be inverted (the
    implicit assertion on the existence of the path is not affected).
    $attribute_list::5
    """

    path: str = field(
        metadata={
            "type": "Attribute",
            "required": True,
            "description": "Path to check for. Valid paths are the simplified subsets of XPath implemented by lxml.etree; https://lxml.de/xpathxslt.html for more information.",
        }
    )
    text: str = field(metadata={"type": "Attribute", "required": True, "description": "Text to check for."})
    negate: Union[bool, PermissiveBooleanValue] = field(
        default=PermissiveBooleanValue.FALSE,
        metadata={"type": "Attribute", "description": "Negate the outcome of the assertion."},
    )


@dataclass(kw_only=True)
class AssertElementTextMatches(BaseSetting):
    """Asserts the text of the XML element with the specified XPath-like ``path``
    matches the regular expression defined by ``expression``, e.g. ```xml
    &lt;element_text_matches path="BlastOutput_version"
    expression="BLASTP\\s+2\\.2.*"/&gt; ``` The assertion implicitly also asserts
    that an element matching ``path`` exists.

    With ``negate`` the result of the assertion (on the matching) can be inverted (the
    implicit assertion on the existence of the path is not affected).
    $attribute_list::5
    """

    path: str = field(
        metadata={
            "type": "Attribute",
            "required": True,
            "description": "Path to check for. Valid paths are the simplified subsets of XPath implemented by lxml.etree; https://lxml.de/xpathxslt.html for more information.",
        }
    )
    expression: str = field(
        metadata={"type": "Attribute", "required": True, "description": "The regular expression to use."}
    )
    negate: Union[bool, PermissiveBooleanValue] = field(
        default=PermissiveBooleanValue.FALSE,
        metadata={"type": "Attribute", "description": "Negate the outcome of the assertion."},
    )


@dataclass(kw_only=True)
class AssertHasElementWithPath(BaseSetting):
    """Asserts the XML output contains at least one element (or tag) with the
    specified XPath-like ``path``, e.g. ```xml &lt;has_element_with_path
    path="BlastOutput_param/Parameters/Parameters_matrix" /&gt; ``` With ``negate``
    the result of the assertion can be inverted.

    $attribute_list::5
    """

    path: str = field(
        metadata={
            "type": "Attribute",
            "required": True,
            "description": "Path to check for. Valid paths are the simplified subsets of XPath implemented by lxml.etree; https://lxml.de/xpathxslt.html for more information.",
        }
    )
    negate: Union[bool, PermissiveBooleanValue] = field(
        default=PermissiveBooleanValue.FALSE,
        metadata={"type": "Attribute", "description": "Negate the outcome of the assertion."},
    )


@dataclass(kw_only=True)
class AssertHasLine(BaseSetting):
    """Asserts a line matching the specified string (``line``) appears in the
    output (e.g. ``&lt;has_line line="A full example line." /&gt;``).

    If the ``line`` is expected
    to occur a particular number of times, this value can be specified using ``n``.
    Optionally also with a certain ``delta``. Alternatively the range of expected
    occurences can be specified by ``min`` and/or ``max``.
    $attribute_list::5
    """

    line: str = field(metadata={"type": "Attribute", "required": True, "description": "The line to check for"})
    n: Optional[Union[int, str]] = field(
        default=None,
        metadata={"type": "Attribute", "description": "Desired number, can be suffixed by ``(k|M|G|T|P|E)i?``"},
    )
    delta: Optional[Union[int, str]] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Allowed difference with respect to n (default: 0), can be suffixed by ``(k|M|G|T|P|E)i?``",
        },
    )
    min: Optional[Union[int, str]] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Minimum number (default: -infinity), can be suffixed by ``(k|M|G|T|P|E)i?``",
        },
    )
    max: Optional[Union[int, str]] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Maximum number (default: infinity), can be suffixed by ``(k|M|G|T|P|E)i?``",
        },
    )
    negate: Union[bool, PermissiveBooleanValue] = field(
        default=PermissiveBooleanValue.FALSE,
        metadata={"type": "Attribute", "description": "Negate the outcome of the assertion."},
    )


@dataclass(kw_only=True)
class AssertHasLineMatching(BaseSetting):
    """Asserts a line matching the specified regular expression (``expression``)
    appears in the output (e.g. ``&lt;has_line_matching
    expression=".*\\s+127489808\\s+127494553" /&gt;``).

    If a particular number of matching lines is expected, this value can be
    specified using ``n``.  Optionally also with ``delta``. Alternatively the range
    of expected occurences can be specified by ``min`` and/or ``max``.
    $attribute_list::5
    """

    expression: str = field(
        metadata={"type": "Attribute", "required": True, "description": "Regular expression to check for"}
    )
    n: Optional[Union[int, str]] = field(
        default=None,
        metadata={"type": "Attribute", "description": "Desired number, can be suffixed by ``(k|M|G|T|P|E)i?``"},
    )
    delta: Optional[Union[int, str]] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Allowed difference with respect to n (default: 0), can be suffixed by ``(k|M|G|T|P|E)i?``",
        },
    )
    min: Optional[Union[int, str]] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Minimum number (default: -infinity), can be suffixed by ``(k|M|G|T|P|E)i?``",
        },
    )
    max: Optional[Union[int, str]] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Maximum number (default: infinity), can be suffixed by ``(k|M|G|T|P|E)i?``",
        },
    )
    negate: Union[bool, PermissiveBooleanValue] = field(
        default=PermissiveBooleanValue.FALSE,
        metadata={"type": "Attribute", "description": "Negate the outcome of the assertion."},
    )


@dataclass(kw_only=True)
class AssertHasNcolumns(BaseSetting):
    """Asserts tabular output (actually only the first line) contains the specified
    number (``n``) of columns (e.g. ``&lt;has_n_columns n="3"/&gt;``) optionally
    also with ``delta``.

    Alternatively the range of expected occurences can be specified by
    ``min`` and/or ``max``.  Optionally a column separator (``sep``, default is
    ``\\t``) `and comment character(s) can be specified (``comment``, default is
    empty string), then the first non-comment line is used for determining the
    number of columns.
    $attribute_list::5
    """

    class Meta:
        name = "AssertHasNColumns"

    n: Optional[Union[int, str]] = field(
        default=None,
        metadata={"type": "Attribute", "description": "Desired number, can be suffixed by ``(k|M|G|T|P|E)i?``"},
    )
    delta: Optional[Union[int, str]] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Allowed difference with respect to n (default: 0), can be suffixed by ``(k|M|G|T|P|E)i?``",
        },
    )
    min: Optional[Union[int, str]] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Minimum number (default: -infinity), can be suffixed by ``(k|M|G|T|P|E)i?``",
        },
    )
    max: Optional[Union[int, str]] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Maximum number (default: infinity), can be suffixed by ``(k|M|G|T|P|E)i?``",
        },
    )
    negate: Union[bool, PermissiveBooleanValue] = field(
        default=PermissiveBooleanValue.FALSE,
        metadata={"type": "Attribute", "description": "Negate the outcome of the assertion."},
    )
    sep: str = field(
        default="&#9;", metadata={"type": "Attribute", "description": "Separator defining columns, default: tab"}
    )
    comment: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Comment character(s) used to skip comment lines (which should not be used for counting columns)",
        },
    )


@dataclass(kw_only=True)
class AssertHasNelementsWithPath(BaseSetting):
    """Asserts the XML output contains the specified number (``n``, optionally with
    ``delta``) of elements (or tags) with the specified XPath-like ``path``, e.g.
    ```xml &lt;has_n_elements_with_path n="9"
    path="BlastOutput_iterations/Iteration/Iteration_hits/Hit/Hit_num" /&gt; ```
    Alternatively to ``n`` and ``delta`` also the ``min`` and ``max`` attributes
    can be used to specify the range of the expected number of occurences.

    With ``negate`` the result of the assertion can be inverted.
    $attribute_list::5
    """

    class Meta:
        name = "AssertHasNElementsWithPath"

    path: str = field(
        metadata={
            "type": "Attribute",
            "required": True,
            "description": "Path to check for. Valid paths are the simplified subsets of XPath implemented by lxml.etree; https://lxml.de/xpathxslt.html for more information.",
        }
    )
    n: Optional[Union[int, str]] = field(
        default=None,
        metadata={"type": "Attribute", "description": "Desired number, can be suffixed by ``(k|M|G|T|P|E)i?``"},
    )
    delta: Optional[Union[int, str]] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Allowed difference with respect to n (default: 0), can be suffixed by ``(k|M|G|T|P|E)i?``",
        },
    )
    min: Optional[Union[int, str]] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Minimum number (default: -infinity), can be suffixed by ``(k|M|G|T|P|E)i?``",
        },
    )
    max: Optional[Union[int, str]] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Maximum number (default: infinity), can be suffixed by ``(k|M|G|T|P|E)i?``",
        },
    )
    negate: Union[bool, PermissiveBooleanValue] = field(
        default=PermissiveBooleanValue.FALSE,
        metadata={"type": "Attribute", "description": "Negate the outcome of the assertion."},
    )


@dataclass(kw_only=True)
class AssertHasNlines(BaseSetting):
    """Asserts that an output contains ``n`` lines, allowing for a difference of
    ``delta`` (default is 0), e.g. ``&lt;has_n_lines n="3" delta="1"/&gt;``.

    Alternatively the range of expected occurences can be specified by ``min``
    and/or ``max``.
    $attribute_list::5
    """

    class Meta:
        name = "AssertHasNLines"

    n: Optional[Union[int, str]] = field(
        default=None,
        metadata={"type": "Attribute", "description": "Desired number, can be suffixed by ``(k|M|G|T|P|E)i?``"},
    )
    delta: Optional[Union[int, str]] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Allowed difference with respect to n (default: 0), can be suffixed by ``(k|M|G|T|P|E)i?``",
        },
    )
    min: Optional[Union[int, str]] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Minimum number (default: -infinity), can be suffixed by ``(k|M|G|T|P|E)i?``",
        },
    )
    max: Optional[Union[int, str]] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Maximum number (default: infinity), can be suffixed by ``(k|M|G|T|P|E)i?``",
        },
    )
    negate: Union[bool, PermissiveBooleanValue] = field(
        default=PermissiveBooleanValue.FALSE,
        metadata={"type": "Attribute", "description": "Negate the outcome of the assertion."},
    )


@dataclass(kw_only=True)
class AssertHasSize(BaseSetting):
    """Asserts the output has a specific size (in bytes) of ``value`` plus minus
    ``delta``, e.g. ``&lt;has_size value="10000" delta="100" /&gt;``.

    Alternatively the range of the expected size can be specified by ``min`` and/or
    ``max``.
    $attribute_list::5
    """

    value: Optional[Union[int, str]] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Desired size of the output (in bytes), can be suffixed by ``(k|M|G|T|P|E)i?``",
        },
    )
    delta: Optional[Union[int, str]] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Maximum allowed size difference (default is 0). The observed size has to be in the range ``value +- delta``. Can be suffixed by ``(k|M|G|T|P|E)i?``",
        },
    )
    min: Optional[Union[int, str]] = field(
        default=None,
        metadata={"type": "Attribute", "description": "Minimum expected size, can be suffixed by ``(k|M|G|T|P|E)i?``"},
    )
    max: Optional[Union[int, str]] = field(
        default=None,
        metadata={"type": "Attribute", "description": "Maximum expected size, can be suffixed by ``(k|M|G|T|P|E)i?``"},
    )
    negate: Union[bool, PermissiveBooleanValue] = field(
        default=PermissiveBooleanValue.FALSE,
        metadata={"type": "Attribute", "description": "Negate the outcome of the assertion."},
    )


@dataclass(kw_only=True)
class AssertHasText(BaseSetting):
    """Asserts the specified ``text`` appears in the output (e.g. ``&lt;has_text
    text="chr7"&gt;``).

    If the ``text`` is expected to occur a particular number of
    times, this value can be specified using ``n``. Optionally also with a certain
    ``delta``. Alternatively the range of expected occurences can be specified by
    ``min`` and/or ``max``.
    $attribute_list::5
    """

    text: str = field(metadata={"type": "Attribute", "required": True, "description": "Text to check for"})
    n: Optional[Union[int, str]] = field(
        default=None,
        metadata={"type": "Attribute", "description": "Desired number, can be suffixed by ``(k|M|G|T|P|E)i?``"},
    )
    delta: Optional[Union[int, str]] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Allowed difference with respect to n (default: 0), can be suffixed by ``(k|M|G|T|P|E)i?``",
        },
    )
    min: Optional[Union[int, str]] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Minimum number (default: -infinity), can be suffixed by ``(k|M|G|T|P|E)i?``",
        },
    )
    max: Optional[Union[int, str]] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Maximum number (default: infinity), can be suffixed by ``(k|M|G|T|P|E)i?``",
        },
    )
    negate: Union[bool, PermissiveBooleanValue] = field(
        default=PermissiveBooleanValue.FALSE,
        metadata={"type": "Attribute", "description": "Negate the outcome of the assertion."},
    )


@dataclass(kw_only=True)
class AssertHasTextMatching(BaseSetting):
    """Asserts text matching the specified regular expression (``expression``)
    appears in the output (e.g. ``&lt;has_text_matching expression="1274\\d+53"
    /&gt;`` ).

    If the
    regular expression is expected to match a particular number of times, this value
    can be specified using ``n``.  Note only non-overlapping occurences are counted.
    Optionally also with a certain ``delta``. Alternatively the range of expected
    occurences can be specified by ``min`` and/or ``max``.
    $attribute_list::5
    """

    expression: str = field(
        metadata={"type": "Attribute", "required": True, "description": "Regular expression to check for"}
    )
    n: Optional[Union[int, str]] = field(
        default=None,
        metadata={"type": "Attribute", "description": "Desired number, can be suffixed by ``(k|M|G|T|P|E)i?``"},
    )
    delta: Optional[Union[int, str]] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Allowed difference with respect to n (default: 0), can be suffixed by ``(k|M|G|T|P|E)i?``",
        },
    )
    min: Optional[Union[int, str]] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Minimum number (default: -infinity), can be suffixed by ``(k|M|G|T|P|E)i?``",
        },
    )
    max: Optional[Union[int, str]] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Maximum number (default: infinity), can be suffixed by ``(k|M|G|T|P|E)i?``",
        },
    )
    negate: Union[bool, PermissiveBooleanValue] = field(
        default=PermissiveBooleanValue.FALSE,
        metadata={"type": "Attribute", "description": "Negate the outcome of the assertion."},
    )


@dataclass(kw_only=True)
class AssertXmlelement(BaseSetting):
    """Assert if the XML file contains element(s) or tag(s) with the specified
    [XPath-like ``path``](https://lxml.de/xpathxslt.html).  If ``n`` and ``delta``
    or ``min`` and ``max`` are given also the number of occurences is checked.
    ```xml
    &lt;assert_contents&gt;
    &lt;xml_element path="./elem"/&gt;
    &lt;xml_element path="./elem/more[2]"/&gt;
    &lt;xml_element path=".//more" n="3" delta="1"/&gt;
    &lt;/assert_contents&gt;
    ```
    With ``negate="true"`` the outcome of the assertions wrt the precence and number
    of ``path`` can be negated. If there are any sub assertions then check them against
    - the content of the attribute ``attribute``
    - the element's text if no attribute is given
    ```xml
    &lt;assert_contents&gt;
    &lt;xml_element path="./elem/more[2]" attribute="name"&gt;
    &lt;has_text_matching expression="foo$"/&gt;
    &lt;/xml_element&gt;
    &lt;/assert_contents&gt;
    ```
    Sub-assertions are not subject to the ``negate`` attribute of ``xml_element``.
    If ``all`` is ``true`` then the sub assertions are checked for all occurences.
    Note that all other XML assertions can be expressed by this assertion (Galaxy
    also implements the other assertions by calling this one).
    $attribute_list::5"""

    class Meta:
        name = "AssertXMLElement"

    path: str = field(
        metadata={
            "type": "Attribute",
            "required": True,
            "description": "Path to check for. Valid paths are the simplified subsets of XPath implemented by lxml.etree; https://lxml.de/xpathxslt.html for more information.",
        }
    )
    all: Union[bool, PermissiveBooleanValue] = field(
        default=PermissiveBooleanValue.FALSE,
        metadata={
            "type": "Attribute",
            "description": "Check the sub-assertions for all paths matching the path. Default: false, i.e. only the first",
        },
    )
    attribute: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "The name of the attribute to apply sub-assertion on. If not given then the element text is used",
        },
    )
    n: Optional[Union[int, str]] = field(
        default=None,
        metadata={"type": "Attribute", "description": "Desired number, can be suffixed by ``(k|M|G|T|P|E)i?``"},
    )
    delta: Optional[Union[int, str]] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Allowed difference with respect to n (default: 0), can be suffixed by ``(k|M|G|T|P|E)i?``",
        },
    )
    min: Optional[Union[int, str]] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Minimum number (default: -infinity), can be suffixed by ``(k|M|G|T|P|E)i?``",
        },
    )
    max: Optional[Union[int, str]] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Maximum number (default: infinity), can be suffixed by ``(k|M|G|T|P|E)i?``",
        },
    )
    negate: Union[bool, PermissiveBooleanValue] = field(
        default=PermissiveBooleanValue.FALSE,
        metadata={"type": "Attribute", "description": "Negate the outcome of the assertion."},
    )


@dataclass(kw_only=True)
class ChangeFormat(BaseSetting):
    """See
    [extract_genomic_dna.xml](https://github.com/galaxyproject/tools-iuc/blob/main/tools/extract_genomic_dna/extract_genomic_dna.xml)
    or the test tool
    [output_format.xml](https://github.com/galaxyproject/galaxy/blob/dev/test/functional/tools/output_format.xml)
    for simple examples of how this tag set is used in a tool. This tag set is
    optionally contained within the ``&lt;data&gt;`` tag set and is the container tag set
    for the following ``&lt;when&gt;`` tag set."""

    when: List[ChangeFormatWhen] = field(default_factory=list, metadata={"type": "Element", "min_occurs": 1})


@dataclass(kw_only=True)
class Citation(BaseSetting):
    """Each citations element can contain one or
    more ``citation`` tag elements - each of which specifies tool citation
    information using either a DOI or a BibTeX entry."""

    value: str = field(default="", metadata={"required": True})
    type_value: CitationType = field(
        metadata={
            "name": "type",
            "type": "Attribute",
            "required": True,
            "description": "Type of citation - currently ``doi``\nand ``bibtex`` are the only supported options.",
        }
    )


@dataclass(kw_only=True)
class Code(BaseSetting):
    """*Deprecated*.

    Do not use this unless absolutely necessary.
    The extensions described here can cause problems using your tool with certain components
    of Galaxy (like the workflow system). It is highly recommended to avoid these constructs
    unless absolutely necessary.
    This tag set provides detailed control of the way the tool is executed. This
    (optional) code can be deployed in a separate file in the same directory as the
    tool's config file. These hooks are being replaced by new tool config features
    and methods in the [/lib/galaxy/tools/\\__init__.py](https://github.com/galaxyproject/galaxy/blob/dev/lib/galaxy/tools/__init__.py) code file.
    ### Examples
    #### Dynamic Options
    Use associated dynamic select lists where selecting an option in the first
    select list dynamically re-renders the options in the second select list. In
    this example, we are populating both dynamic select lists from metadata elements
    associated with a tool's single input dataset. The 2 metadata elements we're
    using look like this.
    ```python
    MetadataElement(name="field_names", default=[], desc="Field names", readonly=True, optional=True, visible=True, no_value=[])
    # The keys in the field_components map to the list of field_names in the above element
    # which ensures order for select list options that are built from it.
    MetadataElement(name="field_components", default={}, desc="Field names and components", readonly=True, optional=True, visible=True, no_value={})
    ```
    Our tool config includes a code file tag like this.
    ```xml
    &lt;code file="tool_form_utils.py" /&gt;
    ```
    Here are the relevant input parameters in our tool config. The first parameter
    is the input dataset that includes the above metadata elements.
    ```xml
    &lt;param name="input" type="data" format="vtkascii,vtkbinary" label="Shape with uncolored surface field"&gt;
    &lt;validator type="expression" message="Shape must have an uncolored surface field."&gt;value is not None and len(value.metadata.field_names) &gt; 0&lt;/validator&gt;
    &lt;/param&gt;
    ```
    The following parameter dynamically renders a select list consisting of the
    elements in the ``field_names`` metadata element associated with the selected
    input dataset.
    ```xml
    &lt;param name="field_name" type="select" label="Field name" refresh_on_change="true"&gt;
    &lt;options&gt;
    &lt;filter type="data_meta" ref="input" key="field_names"/&gt;
    &lt;/options&gt;
    &lt;validator type="no_options" message="The selected shape has no uncolored surface fields." /&gt;
    &lt;/param&gt;
    ```
    The following parameter calls the ``get_field_components_options()`` function in
    the ``tool_form_utils.py`` code file discussed above. This function returns the
    value of the input dataset's ``field_components`` metadata element dictionary
    whose key is the currently selected ``field_name`` from the select list parameter
    above.
    ```xml
    &lt;param name="field_component_index" type="select" label="Field component index" dynamic_options="get_field_components_options(input, field_name=field_name)" help="Color will be applied to the selected field's component associated with this index." /&gt;
    ```
    Changing the selected option in the ``field_name`` select list will dynamically
    re-render the options available in the associated ``field_component_index`` select
    list, which is the behavior we want.
    The ``get_field_components_options()`` method looks like this.
    ```python
    def get_field_components_options(dataset, field_name):
    options = []
    if dataset.metadata is None:
    return options
    if not hasattr(dataset.metadata, 'field_names'):
    return options
    if dataset.metadata.field_names is None:
    return options
    if field_name is None:
    # The expression validator that helps populate the select list of input
    # datsets in the icqsol_color_surface_field tool does not filter out
    # datasets with no field field_names, so we need this check.
    if len(dataset.metadata.field_names) == 0:
    return options
    field_name = dataset.metadata.field_names[0]
    field_components = dataset.metadata.field_components.get(field_name, [])
    for i, field_component in enumerate(field_components):
    options.append((field_component, field_component, i == 0))
    return options
    ```
    #### Parameter Validation
    This function is called before the tool is executed. If it raises any exceptions the tool execution will be aborted and the exception's value will be displayed in an error message box. Here is an example:
    ```python
    def validate(incoming):
    '''Validator for the plotting program'''
    bins = incoming.get("bins","")
    col = incoming.get("col","")
    if not bins or not col:
    raise Exception, "You need to specify a number for bins and columns"
    try:
    bins = int(bins)
    col = int(col)
    except:
    raise Exception, "Parameters are not integers, columns:%s, bins:%s" % (col, bins)
    if not 1&lt;bins&lt;100:
    raise Exception, "The number of bins %s must be a number between 1 and 100" % bins
    ```
    This code will intercept a number of parameter errors and return corresponding error messages. The parameter ``incoming`` contains a dictionary with all the parameters that were sent through the web.
    #### Pre-job and pre-process code
    The signature of both of these is the same:
    ```python
    def exec_before_job(inp_data, out_data, param_dict, tool):
    def exec_before_process(inp_data, out_data, param_dict, tool):
    ```
    The ``param_dict`` is a dictionary that contains all the values in the ``incoming`` parameter above plus a number of keys and values generated internally by galaxy. The ``inp_data`` and the ``out_data`` are dictionaries keyed by parameter name containing the classes that represent the data.
    Example:
    ```python
    def exec_before_process(inp_data, out_data, param_dict, tool):
    for name, data in out_data.items():
    data.name = 'New name'
    ```
    This custom code will change the name of the data that was created for this tool to **New name**. The difference between these two functions is that the ``exec_before_job`` executes before the page returns and the user will see the new name right away. If one were to use ``exec_before_process`` the new name would be set only once the job starts to execute.
    #### Post-process code
    This code executes after the background process running the tool finishes its run. The example below is more advanced one that replaces the type of the output data depending on the parameter named ``extension``:
    ```python
    from galaxy import datatypes
    def exec_after_process(app, inp_data, out_data, param_dict, tool, stdout, stderr):
    ext = param_dict.get('extension', 'text')
    items = out_data.items()
    for name, data in items:
    newdata = datatypes.factory(ext)(id=data.id)
    for key, value in data. __dict__.items():
    setattr(newdata, key, value)
    newdata.ext = ext
    out_data[name] = newdata
    ```
    The content of ``stdout`` and ``stderr`` are strings containing the output of the process.
    """

    hook: List[CodeHook] = field(default_factory=list, metadata={"type": "Element"})
    file: str = field(
        metadata={
            "type": "Attribute",
            "required": True,
            "description": "This value is the name of the executable code file, and is called in the ``exec_before_process()``, ``exec_before_job()``, ``exec_after_process()`` and ``exec_after_job()`` methods.",
        }
    )


@dataclass(kw_only=True)
class Command(BaseSetting):
    """This tag specifies how Galaxy should invoke the tool's executable, passing its
    required input parameter values (the command line specification links the
    parameters supplied in the form with the actual tool executable). Any word
    inside it starting with a dollar sign (``$``) will be treated as a variable whose
    values can be acquired from one of three sources: parameters, metadata, or
    output files. After the substitution of variables with their values, the content
    is interpreted with [Cheetah](https://pythonhosted.org/Cheetah/) and finally given
    to the interpreter specified in the corresponding attribute (if any).
    ### Examples
    The following uses a compiled executable ([bedtools](https://bedtools.readthedocs.io/en/latest/)).
    ```xml
    &lt;command&gt;&lt;![CDATA[
    bed12ToBed6 -i '$input' &gt; '$output'
    ]]&gt;&lt;/command&gt;
    ```
    A few things to note about even this simple example:
    * Input and output variables (boringly named ``input`` and ``output``)
    are expanded into paths using the ``$`` Cheetah directive.
    * Paths should be quoted so that the Galaxy database files may contain spaces.
    * We are building up a shell script - so special characters like ``&gt;`` can be used
    (in this case the standard output of the bedtools call is written to the path
    specified by ``'$output'``).
    The bed12ToBed6 tool can be found [here](https://github.com/galaxyproject/tools-iuc/blob/main/tools/bedtools/bed12ToBed6.xml).
    A more sophisticated bedtools example demonstrates the use of loops, conditionals,
    and uses whitespace to make a complex command very readable can be found in
    [annotateBed](https://github.com/galaxyproject/tools-iuc/blob/main/tools/bedtools/annotateBed.xml)
    tool.
    ```xml
    &lt;command&gt;&lt;![CDATA[
    bedtools annotate
    -i '${inputA}'
    #if $names.names_select == 'yes':
    -files
    #for $bed in $names.beds:
    '${bed.input}'
    #end for
    -names
    #for $bed in $names.beds:
    '${bed.inputName}'
    #end for
    #else:
    #set files = '" "'.join([str($file) for $file in $names.beds])
    -files '${files}'
    #set names = '" "'.join([str($name.display_name) for $name in $names.beds])
    -names '${names}'
    #end if
    $strand
    $counts
    $both
    &gt; '${output}'
    ]]&gt;&lt;/command&gt;
    ```
    The following example (taken from [xpath](https://github.com/galaxyproject/tools-iuc/blob/main/tools/xpath/xpath.xml) tool)
    uses an interpreted executable. In this case a Perl script is shipped with the
    tool and the directory of the tool itself is referenced with ``$__tool_directory__``.
    ```xml
    &lt;command&gt;&lt;![CDATA[
    perl '$__tool_directory__/xpath' -q -e '$expression' '$input' &gt; '$output'
    ]]&gt;&lt;/command&gt;
    ```
    The following example demonstrates accessing metadata from datasets. Metadata values
    (e.g., ``${input.metadata.chromCol}``) are acquired from the ``Metadata`` model associated
    with the objects selected as the values of each of the relative form field
    parameters in the tool form. Accessing this information is generally enabled using
    the following feature components.
    A set of "metadata information" is defined for each supported data type (see the
    ``MetadataElement`` objects in the various data types classes in
    [/lib/galaxy/datatypes](https://github.com/galaxyproject/galaxy/tree/dev/lib/galaxy/datatypes).
    The ``DatasetFilenameWrapper`` class in the
    [/lib/galaxy/tools/wrappers.py](https://github.com/galaxyproject/galaxy/blob/dev/lib/galaxy/tools/wrappers.py)
    code file wraps a metadata collection to return metadata parameters wrapped
    according to the Metadata spec.
    ```xml
    &lt;command&gt;&lt;![CDATA[
    #set genome = $input.metadata.dbkey
    #set datatype = $input.datatype
    mkdir -p output_dir &amp;&amp;
    python '$__tool_directory__/extract_genomic_dna.py'
    --input '$input'
    --genome '$genome'
    #if $input.is_of_type("gff"):
    --input_format "gff"
    --columns "1,4,5,7"
    --interpret_features $interpret_features
    #else:
    --input_format "interval"
    --columns "${input.metadata.chromCol},${input.metadata.startCol},${input.metadata.endCol},${input.metadata.strandCol},${input.metadata.nameCol}"
    #end if
    --reference_genome_source $reference_genome_cond.reference_genome_source
    #if str($reference_genome_cond.reference_genome_source) == "cached"
    --reference_genome $reference_genome_cond.reference_genome.fields.path
    #else:
    --reference_genome $reference_genome_cond.reference_genome
    #end if
    --output_format $output_format_cond.output_format
    #if str($output_format_cond.output_format) == "fasta":
    --fasta_header_type $output_format_cond.fasta_header_type_cond.fasta_header_type
    #if str($output_format_cond.fasta_header_type_cond.fasta_header_type) == "char_delimited":
    --fasta_header_delimiter $output_format_cond.fasta_header_type_cond.fasta_header_delimiter
    #end if
    #end if
    --output '$output'
    ]]&gt;&lt;/command&gt;
    ```
    In additon to demonstrating accessing metadata, this example demonstrates:
    * ``$input.is_of_type("gff")`` which can be used to check if an input is of a
    given datatype.
    * ``#set datatype = $input.datatype`` which is the syntax for defining variables
    in Cheetah.
    ### Reserved Variables
    Galaxy provides a few pre-defined variables which can be used in your command line,
    even though they don't appear in your tool's parameters.
    Name | Description
    ---- | -----------
    ``$__tool_directory__`` | The directory the tool description (XML file) currently resides in (new in 15.03)
    ``$__new_file_path__`` | ``config/galaxy.ini``'s ``new_file_path`` value
    ``$__tool_data_path__`` | ``config/galaxy.ini``'s tool_data_path value
    ``$__root_dir__`` | Top-level Galaxy source directory made absolute via ``os.path.abspath()``
    ``$__datatypes_config__`` | ``config/galaxy.ini``'s datatypes_config value
    ``$__user_id__`` | Email's numeric ID (id column of ``galaxy_user`` table in the database)
    ``$__user_email__`` | User's email address
    ``$__app__`` | The ``galaxy.app.UniverseApplication`` instance, gives access to all other configuration file variables (e.g. $__app__.config.output_size_limit). Should be used as a last resort, may go away in future releases.
    ``$__target_datatype__`` | Only available in converter tools when run internally by Galaxy. Contains the target datatype of the conversion
    Additional runtime properties are available as environment variables. Since these
    are not Cheetah variables (the values aren't available until runtime) these should likely
    be escaped with a backslash (``\\``) when appearing in ``command`` or ``configfile`` elements.
    For internal converter tools using ``$__target_datatype__`` it is recommended to add a select
    input parameter with name ``__target_datatype__`` in order to make the tool testable, see
    for instance the [biom converter](https://github.com/galaxyproject/galaxy/blob/dev/lib/galaxy/datatypes/converters/biom.xml).
    Name | Description
    ---- | -----------
    ``\\${GALAXY_SLOTS:-4}`` | Number of cores/threads allocated by the job runner or resource manager to the tool for the given job (here 4 is the default number of threads to use if running via custom runner that does not configure GALAXY_SLOTS or in an older Galaxy runtime).
    ``\\$GALAXY_MEMORY_MB`` | Total amount of memory in megabytes (1024^2 bytes) allocated by the administrator (via the resource manager) to the tool for the given job. If unset, tools should not attempt to limit memory usage.
    ``\\$GALAXY_MEMORY_MB_PER_SLOT`` | Amount of memory per slot in megabytes (1024^2 bytes) allocated by the administrator (via the resource manager) to the tool for the given job. If unset, tools should not attempt to limit memory usage.
    ``\\$_GALAXY_JOB_TMP_DIR`` | Path to an empty directory in the job's working directory that can be used as a temporary directory.
    See the [Planemo docs](https://planemo.readthedocs.io/en/latest/writing_advanced.html#cluster-usage)
    on the topic of ``GALAXY_SLOTS`` for more information and examples.
    ### Error detection
    The ``detect_errors`` attribute of ``command``, if present, loads a preset of error detection checks (for exit codes and content of stdio to indicate fatal tool errors or fatal out of memory errors). It can be one of:
    * ``default``: for non-legacy tools with absent stdio block non-zero exit codes are added. For legacy tools or if a stdio block is present nothing is added.
    * ``exit_code``: adds checks for non zero exit codes (The @jmchilton recommendation). The ``oom_exit_code`` parameter can be used to add an additional out of memory indicating exit code.
    * ``aggressive``: adds checks for non zero exit codes, and checks for ``Exception:``, ``Error:`` in the standard error. Additionally checks for messages in the standard error that indicate an out of memory error (``MemoryError``, ``std::bad_alloc``, ``java.lang.OutOfMemoryError``, ``Out of memory``). (The @bgruening recommendation).
    Prior to Galaxy release 19.01 the stdio block has only been used for non-legacy tools using ``default``. From release 19.01 checks defined in the stdio tag are prepended to the checks defined by the presets loaded in the command block.
    """

    value: str = field(default="", metadata={"required": True})
    detect_errors: Optional[DetectErrorType] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "The ``detect_errors`` attribute of ``command``, if present, loads a preset of error detection checks (for exit codes and content of stdio to indicate fatal tool errors or fatal out of memory errors). It can be one of:\n* ``default``: for non-legacy tools with absent stdio block non-zero exit codes are added. For legacy tools or if a stdio block is present nothing is added.\n* ``exit_code``: adds checks for non zero exit codes. The ``oom_exit_code`` parameter can be used to add an additional out of memory indicating exit code. This is the default when a tool specifies a ``profile`` &gt;= 16.04.\n* ``aggressive``: adds checks for non zero exit codes, and checks for ``Exception:``, ``Error:`` in the standard error. Additionally checks for messages in the standard error that indicate an out of memory error (``MemoryError``, ``std::bad_alloc``, ``java.lang.OutOfMemoryError``, ``Out of memory``).",
        },
    )
    oom_exit_code: Optional[int] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": 'Only used if ``detect_errors="exit_code"``, tells Galaxy the specified exit code indicates an out of memory error. Galaxy instances may be configured to retry such jobs on resources with more memory.',
        },
    )
    use_shared_home: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "When running a job for this tool, do not isolate its ``$HOME`` directory within the job's directory - use either the ``shared_home_dir`` setting in Galaxy or the default ``$HOME`` specified in the job's default environment.",
        },
    )
    interpreter: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "*Deprecated*. This will prefix the command with the value of this attribute (e.g. ``python`` or ``perl``) and the tool directory, in order to run an executable file shipped with the tool. It is recommended to instead use ``&lt;interpreter&gt; '$__tool_directory__/&lt;executable_name&gt;'`` in the tag content. If this attribute is not specified, the tag should contain a Bash command calling executable(s) available in the ``$PATH``, as modified after loading the requirements.",
        },
    )
    strict: Optional[bool] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "This boolean forces the ``#set -e`` directive on in shell scripts - so that in a multi-part command if any part fails the job exits with a non-zero exit code. This is enabled by default for tools with ``profile&gt;=20.09`` and disabled on legacy tools.",
        },
    )


@dataclass(kw_only=True)
class ConfigFiles(BaseSetting):
    """See
    [xy_plot.xml](https://github.com/galaxyproject/tools-devteam/blob/main/tools/xy_plot/xy_plot.xml)
    for an example of how this tag set is used in a tool. This tag set is a
    container for ``&lt;configfile&gt;`` and ``&lt;inputs&gt;`` tag sets - which can be used
    to setup configuration files for use by tools."""

    inputs: List[ConfigInputs] = field(default_factory=list, metadata={"type": "Element"})
    file_sources: List[ConfigFileSources] = field(default_factory=list, metadata={"type": "Element"})
    configfile: List[ConfigFile] = field(default_factory=list, metadata={"type": "Element"})


@dataclass(kw_only=True)
class Container(BaseSetting):
    """This tag set is contained within the 'requirements' tag set. Galaxy can be.

    configured to run tools within [Docker](https://www.docker.com/) or [Singularity](https://www.sylabs.io/singularity/)
    containers - this tag allows the tool to suggest possible valid containers for this tool. The contents of the tag should
    be a container image identifier appropriate for the particular container runtime being used, e.g.
    ``quay.io/biocontainers/fastqc:0.11.2--1`` for Docker or ``docker://quay.io/biocontainers/fastqc:0.11.2--1``
    (or alternatively ``/opt/containers/fastqc.simg`` if your Galaxy installation will be loading the image from a filesystem path)
    for Singularity. The ``requirements`` tag can contain multiple ``container`` tags describing suitable container options, in
    which case the first container that is found by the Galaxy container resolver at runtime will be used.
    Example:
    ```xml
    &lt;requirements&gt;
    &lt;container type="docker"&gt;quay.io/biocontainers/fastqc:0.11.2--1&lt;/container&gt;
    &lt;/requirements&gt;
    ```
    Read more about configuring Galaxy to run Docker jobs
    [here](https://docs.galaxyproject.org/en/master/admin/container_resolvers.html).
    """

    value: str = field(default="", metadata={"required": True})
    type_value: ContainerType = field(
        metadata={
            "name": "type",
            "type": "Attribute",
            "required": True,
            "description": "This value describes the type of container that the tool may be executed in and currently may be ``docker`` or ``singularity``.",
        }
    )


@dataclass(kw_only=True)
class Creator(BaseSetting):
    """The creator(s) of this work.

    See [schema.org/creator](https://schema.org/creator).
    """

    person: List[Person] = field(default_factory=list, metadata={"type": "Element"})
    organization: List[Organization] = field(default_factory=list, metadata={"type": "Element"})


@dataclass(kw_only=True)
class EntryPoint(BaseSetting):
    """This tag set is contained within the ``&lt;entry_point&gt;`` tag set.

    Access to entry point
    ports and urls are included in this tag set. These are used by InteractiveTools
    to provide access to graphical tools in real-time.
    ```xml
    &lt;entry_points&gt;
    &lt;entry_point name="Example name" label="example"&gt;
    &lt;port&gt;80&lt;/port&gt;
    &lt;url&gt;landing/${template_enabled}/index.html&lt;/url&gt;
    &lt;/entry_point&gt;
    &lt;/entry_points&gt;
    ```
    """

    name: str = field(metadata={"type": "Attribute", "required": True, "description": "The name of the entry point."})
    label: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "A unique label to identify the entry point. Used by interactive client tools to connect.",
        },
    )
    requires_domain: Union[bool, PermissiveBooleanValue] = field(
        default=PermissiveBooleanValue.TRUE,
        metadata={
            "type": "Attribute",
            "description": "Whether domain-based proxying is required for the entry point. Default is True.",
        },
    )
    requires_path_in_url: Union[bool, PermissiveBooleanValue] = field(
        default=PermissiveBooleanValue.FALSE,
        metadata={
            "type": "Attribute",
            "description": 'Whether the InteractiveTool proxy will add the entry point path to the URL provided to the interactive tool. Only\nrelevant when path-based proxying is configured (``requires_domain=False``). A value of False implies that the web service\nfor the interactive tool fully operates with relative links. A value of True implies that the unique entry point path,\nwhich is autogenerated each run, must be somehow provided to the web service. This can be done by injecting the path\ninto an environment variable by setting the attribute ``inject="entry_point_path_for_label"`` in the tool XML.\nAlternatively, the attribute ``requires_path_in_header_named`` can be set to provide the path in the specified HTTP header.\nThe entry point path should in any case be used to configure the web service in the interactive tool to serve the content\nfrom the provided URL path. Default value of ``requires_path_in_url`` is False.',
        },
    )
    requires_path_in_header_named: str = field(
        default="",
        metadata={
            "type": "Attribute",
            "description": "Whether the InteractiveTool proxy will add the entry point path to an HTTP header. An empty string as value (default) means\nthat the path will not be provided in an HTTP header. Any other string value will define the name of the HTTP header\nwhere the path will be injected by the proxy. See the documentation of ``requires_path_in_url`` for more information.\nDefault value of ``requires_path_in_header_named`` is False.",
        },
    )
    content: List[object] = field(
        default_factory=list,
        metadata={
            "type": "Wildcard",
            "namespace": "##any",
            "mixed": True,
            "choices": ({"name": "port", "type": EntryPointPort}, {"name": "url", "type": EntryPointUrl}),
        },
    )


@dataclass(kw_only=True)
class EnvironmentVariable(BaseSetting):
    """This directive defines an environment variable that will be available when
    the tool executes.

    The body should be a Cheetah template block that may reference
    the tool's inputs as demonstrated below.
    ### Example
    The following demonstrates a couple ``environment_variable`` definitions.
    ```xml
    &lt;environment_variables&gt;
    &lt;environment_variable name="INTVAR"&gt;$inttest&lt;/environment_variable&gt;
    &lt;environment_variable name="IFTEST"&gt;#if int($inttest) == 3
    ISTHREE
    #else#
    NOTTHREE
    #end if#&lt;/environment_variable&gt;
    &lt;/environment_variables&gt;
    &lt;/environment_variables&gt;
    ```
    If these environment variables are used in another Cheetah context, such as in
    the ``command`` block, the ``$`` used indicate shell expansion of a variable
    should be escaped with a ``\\`` so prevent it from being evaluated as a Cheetah
    variable instead of shell variable.
    ```xml
    &lt;command&gt;
    echo "\\$INTVAR"  &gt;  $out_file1;
    echo "\\$IFTEST"  &gt;&gt; $out_file1;
    &lt;/command&gt;
    ```
    ### inject
    The Galaxy user's API key can be injected into an environment variable by setting ``inject``
    attribute to ``api_key`` (e.g. ``inject="api_key"``).
    ```xml
    &lt;environment_variables&gt;
    &lt;environment_variable name="GALAXY_API_KEY" inject="api_key" /&gt;
    &lt;/environment_variables&gt;
    ```
    The framework allows setting this via environment variable and not via templating variables
    in order to discourage setting the actual values of these keys as command line arguments.
    On shared systems this provides some security by preventing a simple process listing command
    from exposing keys.
    """

    value: str = field(default="", metadata={"required": True})
    name: Optional[str] = field(
        default=None, metadata={"type": "Attribute", "description": "Name of the environment variable to\ndefine."}
    )
    inject: Optional[EnvironmentVariableInject] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Special variable to inject into the environment variable. Currently 'api_key' is the only option and will cause the user's API key to be injected via this environment variable.",
        },
    )
    strip: Union[bool, PermissiveBooleanValue] = field(
        default=PermissiveBooleanValue.FALSE,
        metadata={
            "type": "Attribute",
            "description": "Whether to strip leading and trailing whitespace from the calculated value before exporting the environment variable.",
        },
    )


@dataclass(kw_only=True)
class ExitCode(BaseSetting):
    """Tools may use exit codes to indicate specific execution errors.

    Many programs use 0 to indicate success and non-zero exit codes to indicate errors. Galaxy allows each tool to specify exit codes that indicate errors. Each ``&lt;exit_code&gt;`` tag defines a range of exit codes, and each range can be associated with a description of the error (e.g., "Out of Memory", "Invalid Sequence File") and an error level. The description just describes the condition and can be anything. The error level is either log, warning, fatal error, or fatal_oom. A warning means that stderr will be updated with the error's description. A fatal error means that the tool's execution will be marked as having an error and the workflow will stop. A fatal_oom indicates an out of memory condition and the job might be resubmitted if Galaxy is configured appropriately. Note that, if the error level is not supplied, then a fatal error is assumed to have occurred.
    The exit code's range can be any consecutive group of integers. More advanced ranges, such as noncontiguous ranges, are currently not supported. Ranges can be specified in the form "m:n", where m is the start integer and n is the end integer. If ":n" is specified, then the exit code will be compared against all integers less than or equal to n. If "m:" is used, then the exit code will be compared against all integers greater than or equal to m. If the exit code matches, then the error level is applied and the error's description is added to stderr. If a tool's exit code does not match any of the supplied ``&lt;exit_code&gt;`` tags' ranges, then no errors are applied to the tool's execution.
    Note that most Unix and Linux variants only support positive integers 0 to 255 for exit codes. If an exit code falls outside of this range, the usual convention is to only use the lower 8 bits for the exit code. The only known exception is if a job is broken into subtasks using the tasks runner and one of those tasks is stopped with a POSIX signal. (Note that signals should be used as a last resort for terminating processes.) In those cases, the task will receive -1 times the signal number. For example, suppose that a job uses the tasks runner and 8 tasks are created for the job. If one of the tasks hangs, then a sysadmin may choose to send the "kill" signal, SIGKILL, to the process. In that case, the task (and its job) will exit with an exit code of -9. More on POSIX signals can be found on [Wikipedia](https://en.wikipedia.org/wiki/Signal_(IPC)) as well as on the man page for "signal" (``man 7 signal``).
    The ``&lt;exit_code&gt;`` tag's supported attributes are as follows:
    * ``range``: This indicates the range of exit codes to check. The range can be one of the following:
    * ``n``: the exit code will only be compared to n;
    * ``m:n``: the exit code must be greater than or equal to m and less than or equal to n;
    * ``m:``: the exit code must be greater than or equal to m;
    * ``:n``: the exit code must be less than or equal to n.
    * ``level``: This indicates the error level of the exit code. If no level is specified, then the fatal error level will be assumed to have occurred. The level can have one of following values:
    * ``log``, ``qc``, and ``warning``: If an exit code falls in the given range, then a description of the error will be added to the beginning of the source, prepended with either 'QC:', 'Log:' or 'Warning:'. This will not cause the tool to fail.
    * ``fatal``: If an exit code falls in the given range, then a description of the error will be added to the beginning of stderr. A fatal-level error will cause the tool to fail.
    * ``fatal_oom``: If an exit code falls in the given range, then a description of the error will be added to the beginning of stderr. Depending on the job configuration, a fatal_oom-level error will cause the tool to be resubmitted or fail.
    * ``description``: This is an optional description of the error that corresponds to the exit code.
    The following is an example of the ``&lt;exit_code&gt;`` tag:
    ```xml
    &lt;stdio&gt;
    &lt;exit_code range="3:5" level="warning" description="Low disk space" /&gt;
    &lt;exit_code range="6:" level="fatal" description="Bad input dataset" /&gt;
    &lt;!-- Catching fatal_oom allows the job runner to potentially resubmit to a resource with more
    memory if Galaxy is configured to do this. --&gt;
    &lt;exit_code range="2" level="fatal_oom" description="Out of Memory" /&gt;
    &lt;/stdio&gt;
    ```
    If the tool returns 0 or 1, then the tool will not be marked as having an error.
    If the exit code is 2, then the tool will fail with the description ``Out of
    Memory`` added to stderr. If the tool returns 3, 4, or 5, then the tool will not
    be marked as having failed, but ``Low disk space`` will be added to stderr.
    Finally, if the tool returns any number greater than or equal to 6, then the
    description ``Bad input dataset`` will be added to stderr and the tool will be
    marked as having failed.
    """

    range: str = field(
        metadata={
            "type": "Attribute",
            "required": True,
            "description": "Exit code range. Can be a single number or a range given by ``start:end``, where start and end are integers, if omitted negative or positive infinity is assumed",
        }
    )
    level: Optional[LevelType] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Error level: one of ``qc``, ``warning``, ``log``, ``fatal`` (default), ``fatal_oom``",
        },
    )
    description: Optional[str] = field(
        default=None, metadata={"type": "Attribute", "description": "Description. Error message presented to the user"}
    )


@dataclass(kw_only=True)
class Expression(BaseSetting):
    """For "Expression Tools" (tools with ``tool_type="expression``) this block
    describes the expression used to evaluate inputs and produce outputs.

    The semantics are going to vary based on the value of "type" specified for this expression block.
    """

    value: str = field(default="", metadata={"required": True})
    type_value: Optional[ExpressionType] = field(
        default=None,
        metadata={
            "name": "type",
            "type": "Attribute",
            "description": "Type of expression defined by this expression block. The only current valid option is ecma5.1 - which will evaluate the expression in a sandbox using node. The option still must be specified to allow a different default in the future.",
        },
    )


@dataclass(kw_only=True)
class Filter(BaseSetting):
    """Optionally contained within an
    ``&lt;options&gt;`` tag set - modify (e.g. remove, add, sort, ...) the list of values obtained from a locally stored file (e.g.
    a tool data table) or a dataset in the current history.
    Currently the following filters are defined:
    * ``static_value`` filter options for which the entry in a given ``column`` of the referenced file based on equality to the ``value`` attribute of the filter.
    * ``regexp`` similar to the ``static_value`` filter, but checks if the regular expression given by ``value`` matches the entry.
    * ``param_value`` filter options for which the entry in a given ``column`` of the referenced file based on properties of another input parameter specified by ``ref``. This property is by default the value of the parameter, but also the values of another attribute (``ref_attribute``) of the parameter can be used, e.g. the extension of a data input.
    * ``data_meta`` populate or filter options based on the metadata of another input parameter specified by ``ref``. If a ``column`` is given options are filtered for which the entry in this column ``column`` is equal to metadata of the input parameter specified by ``ref``.
    If no ``column`` is given the metadata value of the referenced input is added to the options list (in this case the corresponding ``options`` tag must not have the ``from_data_table`` or ``from_dataset`` attributes).
    In both cases the desired metadata is selected by ``key``.
    The ``static_value`` and ``regexp`` filters can be inverted by setting ``keep`` to true.
    * ``add_value``: add an option with a given ``name`` and ``value`` to the options. By default, the new option is appended, with ``index`` the insertion position can be specified.
    * ``remove_value``: remove a value from the options. Either specified explicitly with ``value``, the value of another input specified with ``ref``, or the metadata ``key`` of another input ``meta_ref``.
    * ``unique_value``: remove options that have duplicate entries in the given ``column``.
    * ``sort_by``: sort options by the entries of a given ``column``. If ``reverse_sort_order`` is set to ``true``, reverse sort order from ascending to descending.
    * ``multiple_splitter``: split the entries of the specified ``column``(s) in the referenced file using a ``separator``. Thereby the number of columns is increased.
    * ``attribute_value_splitter``: split the attribute-value pairs within the specified ``column`` in the referenced file using ``pair_separator`` and ``name_val_separator``. Thereby a new column is introduced before ``column`` containing a list of all attribute names.
    ### Examples
    The following example from Mothur's
    [remove.groups.xml](https://github.com/galaxyproject/tools-iuc/blob/main/tools/mothur/remove.groups.xml)
    tool demonstrates filtering a select list based on the metadata of an input to
    to the tool.
    ```xml
    &lt;param name="group_in" type="data" format="mothur.groups,mothur.count_table" label="group or count table - Groups"/&gt;
    &lt;param name="groups" type="select" label="groups - Pick groups to remove" multiple="true" optional="false"&gt;
    &lt;options&gt;
    &lt;filter type="data_meta" ref="group_in" key="groups"/&gt;
    &lt;/options&gt;
    &lt;/param&gt;
    ```
    This more advanced example, taken from Mothur's
    [remove.lineage.xml](https://github.com/galaxyproject/tools-iuc/blob/main/tools/mothur/remove.lineage.xml)
    tool demonstrates using filters to sort a list and remove duplicate entries.
    ```xml
    &lt;param name="taxonomy" type="data" format="mothur.cons.taxonomy" label="constaxonomy - Constaxonomy file. Provide either a constaxonomy file or a taxonomy file" help="please make sure your file has no quotation marks in it"/&gt;
    &lt;param name="taxons" type="select" optional="true" multiple="true" label="Browse Taxons from Taxonomy"&gt;
    &lt;options from_dataset="taxonomy"&gt;
    &lt;column name="name" index="2"/&gt;
    &lt;column name="value" index="2"/&gt;
    &lt;filter type="unique_value" name="unique_taxon" column="2"/&gt;
    &lt;filter type="sort_by" name="sorted_taxon" column="2"/&gt;
    &lt;/options&gt;
    &lt;sanitizer&gt;
    &lt;valid initial="default"&gt;
    &lt;add preset="string.printable"/&gt;
    &lt;add value=";"/&gt;
    &lt;remove value="&amp;quot;"/&gt;
    &lt;remove value="&amp;apos;"/&gt;
    &lt;/valid&gt;
    &lt;/sanitizer&gt;
    &lt;/param&gt;
    ```
    This example taken from the
    [hisat2](https://github.com/galaxyproject/tools-iuc/blob/main/tools/hisat2/hisat2.xml)
    tool demonstrates filtering values from a tool data table.
    ```xml
    &lt;param help="If your genome of interest is not listed, contact the Galaxy team" label="Select a reference genome" name="index" type="select"&gt;
    &lt;options from_data_table="hisat2_indexes"&gt;
    &lt;filter column="2" type="sort_by" /&gt;
    &lt;/options&gt;
    &lt;validator message="No genomes are available for the selected input dataset" type="no_options" /&gt;
    &lt;/param&gt;
    ```
    The
    [gemini_load.xml](https://github.com/galaxyproject/tools-iuc/blob/main/tools/gemini/gemini_load.xml)
    tool demonstrates adding values to an option list using ``filter``s.
    ```xml
    &lt;param name="infile" type="data" format="vcf" label="VCF file to be loaded in the GEMINI database" help="Only build 37 (aka hg19) of the human genome is supported."&gt;
    &lt;options&gt;
    &lt;filter type="add_value" value="hg19" /&gt;
    &lt;filter type="add_value" value="Homo_sapiens_nuHg19_mtrCRS" /&gt;
    &lt;filter type="add_value" value="hg_g1k_v37" /&gt;
    &lt;/options&gt;
    &lt;/param&gt;
    ```
    While this fragment from [maf_to_interval.xml](https://github.com/galaxyproject/galaxy/blob/dev/tools/maf/maf_to_interval.xml) demonstrates removing items.
    ```xml
    &lt;param name="species" type="select" label="Select additional species"
    display="checkboxes" multiple="true"
    help="The species matching the dbkey of the alignment is always included.
    A separate history item will be created for each species."&gt;
    &lt;options&gt;
    &lt;filter type="data_meta" ref="input1" key="species" /&gt;
    &lt;filter type="remove_value" meta_ref="input1" key="dbkey" /&gt;
    &lt;/options&gt;
    &lt;/param&gt;
    ```
    This example taken from
    [snpSift_dbnsfp.xml](https://github.com/galaxyproject/tools-iuc/blob/main/tool_collections/snpsift/snpsift_dbnsfp/snpSift_dbnsfp.xml)
    demonstrates splitting up strings into multiple values.
    ```xml
    &lt;param name="annotations" type="select" multiple="true" display="checkboxes" label="Annotate with"&gt;
    &lt;options from_data_table="snpsift_dbnsfps"&gt;
    &lt;column name="name" index="4"/&gt;
    &lt;column name="value" index="4"/&gt;
    &lt;filter type="param_value" ref="dbnsfp" column="3" /&gt;
    &lt;filter type="multiple_splitter" column="4" separator=","/&gt;
    &lt;/options&gt;
    &lt;/param&gt;
    ```
    This example demonstrates compiling a list of available attributes by parsing a GFF containing a column of multiple attribute-value pairs formatted in the input as ``gene_id=ABC;transcript_id=abc;transcript_biotype=mRNA``
    ```xml
    &lt;param name="available_attributes" type="select" label="List of all attributes mentioned in a GFF"&gt;
    &lt;options from_data_table="a_gff_as_table"&gt;
    &lt;column name="name" index="8"/&gt;
    &lt;column name="value" index="8"/&gt;
    &lt;filter type="attribute_value_splitter" column="8" pair_separator=";" name_val_separator="="/&gt;
    &lt;/options&gt;
    &lt;/param&gt;
    ```"""

    type_value: FilterType = field(
        metadata={
            "name": "type",
            "type": "Attribute",
            "required": True,
            "description": "Currently the filters in the ``filter_types`` dictionary in the module\n[/lib/galaxy/tools/parameters/dynamic_options.py](https://github.com/galaxyproject/galaxy/blob/dev/lib/galaxy/tools/parameters/dynamic_options.py) are defined.",
        }
    )
    column: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Column targeted by this filter given as column index or a column name. Invalid if ``type`` is ``add_value`` or ``remove_value``.",
        },
    )
    name: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Name displayed for value to add (only\nused with ``type`` of ``add_value``).",
        },
    )
    ref: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "The attribute name of the reference file\n(tool data) or input dataset. Only used when ``type`` is\n``data_meta`` (required), ``param_value`` (required), or ``remove_value``\n(optional).",
        },
    )
    key: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "When ``type`` is ``data_meta``, ``param_value``,\nor ``remove_value`` - this is the name of the metadata key to filter by.",
        },
    )
    multiple: Union[bool, PermissiveBooleanValue] = field(
        default=PermissiveBooleanValue.FALSE,
        metadata={
            "type": "Attribute",
            "description": "For types ``data_meta`` and\n``remove_value``, whether option values are multiple. Columns will be split by\nseparator. Defaults to ``false``.",
        },
    )
    separator: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "When ``type`` is ``data_meta``,\n``multiple_splitter``, or ``remove_value`` - this is used to split one value\ninto multiple parts. When ``type`` is ``data_meta`` or ``remove_value`` this is\nonly used if ``multiple`` is set to ``true``.",
        },
    )
    keep: Union[bool, PermissiveBooleanValue] = field(
        default=PermissiveBooleanValue.TRUE,
        metadata={
            "type": "Attribute",
            "description": "If ``true``, keep columns matching the\nvalue, if ``false`` discard columns matching the value. Used when ``type`` is\neither ``static_value``, ``regexp`` or ``param_value``. Default: true",
        },
    )
    value: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Target value of the operations - has\nslightly different meanings depending on ``type``. For instance when ``type`` is\n``add_value`` it is the value to add to the list and when ``type`` is\n``static_value`` or ``regexp`` it is the value compared against.",
        },
    )
    ref_attribute: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Only used when ``type`` is\n``param_value``. Period (``.``) separated attribute chain of input (``ref``)\nattributes to use as value for filter.",
        },
    )
    index: Optional[int] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Used when ``type`` is ``add_value``, it\nis the index into the list to add the option to. If not set, the option will be\nadded to the end of the list.",
        },
    )
    meta_ref: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Only used when ``type`` is\n``remove_value``. Dataset to look for the value of metadata ``key`` to remove\nfrom the list.",
        },
    )
    reverse_sort_order: bool = field(
        default=False,
        metadata={
            "type": "Attribute",
            "description": "Used when ``type`` is ``sort_by``, if set to\n``true`` it will reverse the sort order from ascending to descending. Default\nis ``false``.",
        },
    )
    pair_separator: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Only used if ``type`` is ``attribute_value_splitter``. This is used to separate attribute-value pairs from other pairs, i.e. ``;`` if the target content is ``A=V; B=W; C=Y`` . Default is ``,``.",
        },
    )
    name_val_separator: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Only used if ``type`` is ``attribute_value_splitter``. This is used to separate attributes and values from each other within an attribute-value pair, i.e. ``=`` if the target content is ``A=V; B=W; C=Y``. Defaults to whitespace.",
        },
    )


@dataclass(kw_only=True)
class Options(BaseSetting):
    """
    This directive is used to specify some rarely modified options.
    """

    refresh: Optional[Union[bool, PermissiveBooleanValue]] = field(
        default=None, metadata={"type": "Attribute", "description": "*Deprecated*. Unused attribute."}
    )
    sanitize: Union[bool, PermissiveBooleanValue] = field(
        default=PermissiveBooleanValue.TRUE,
        metadata={
            "type": "Attribute",
            "description": "This attribute can be used to turn off all input sanitization for a tool.",
        },
    )


@dataclass(kw_only=True)
class Parallelism(BaseSetting):
    """
    Documentation for Parallelism.
    """

    method: Optional[MethodType] = field(
        default=None, metadata={"type": "Attribute", "description": "Documentation for method"}
    )
    merge_outputs: Optional[str] = field(
        default=None, metadata={"type": "Attribute", "description": "Documentation for merge_outputs"}
    )
    split_inputs: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "A comma-separated list of data inputs to split for job parallelization.",
        },
    )
    split_size: Optional[str] = field(
        default=None, metadata={"type": "Attribute", "description": "Documentation for split_size"}
    )
    split_mode: Optional[str] = field(
        default=None, metadata={"type": "Attribute", "description": "Documentation for split_mode"}
    )
    shared_inputs: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "A comma-separated list of data inputs that should not be split for this tool, Galaxy will infer this if not present and so this potentially never needs to be set.",
        },
    )


@dataclass(kw_only=True)
class ParamDefaultElement(BaseSetting):
    collection: Optional[ParamDefaultCollection] = field(default=None, metadata={"type": "Element"})
    name: Optional[str] = field(
        default=None, metadata={"type": "Attribute", "description": "Name (and element identifier) for this element"}
    )
    location: Optional[str] = field(
        default=None,
        metadata={"type": "Attribute", "description": "Galaxy-aware URI for the default file for collection element."},
    )


@dataclass(kw_only=True)
class ParamSelectOption(BaseSetting):
    """See [/tools/filters/sorter.xml](https://github.com/galaxyproject/galaxy/blob/dev/tools/filters/sorter.xml)
    for typical examples of how to use this tag set. This directive is used to described
    static lists of options and is contained
    within the [param](#tool-inputs-param) directive when the ``type`` attribute
    value is ``select`` (i.e. ``&lt;param type="select" ...&gt;``).
    ### Example
    ```xml
    &lt;param name="style" type="select" label="with flavor"&gt;
    &lt;option value="num"&gt;Numerical sort&lt;/option&gt;
    &lt;option value="gennum"&gt;General numeric sort&lt;/option&gt;
    &lt;option value="alpha"&gt;Alphabetical sort&lt;/option&gt;
    &lt;/param&gt;
    ```
    An option can also be annotated with ``selected="true"`` to specify a
    default option (note that the first option is selected automatically
    if ``optional="false"``).
    ```xml
    &lt;param name="col" type="select" label="From"&gt;
    &lt;option value="0"&gt;Column 1 / Sequence name&lt;/option&gt;
    &lt;option value="1" selected="true"&gt;Column 2 / Source&lt;/option&gt;
    &lt;option value="2"&gt;Column 3 / Feature&lt;/option&gt;
    &lt;option value="6"&gt;Column 7 / Strand&lt;/option&gt;
    &lt;option value="7"&gt;Column 8 / Frame&lt;/option&gt;
    &lt;/param&gt;
    ```
    In general the values and the texts for the options need to be unique,
    but it is possible to specify an option two times if the 2nd has a different
    value for the ``selected`` attribute. This is handy if an option list is
    defined in a macro and different default value(s) are used."""

    value: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "The value of the\ncorresponding variable when used the Cheetah template. Also the value that\nshould be used in building test cases and used when building requests for the\nAPI.",
        },
    )
    selected: Union[bool, PermissiveBooleanValue] = field(
        default=PermissiveBooleanValue.FALSE,
        metadata={
            "type": "Attribute",
            "description": "A boolean parameter indicating\nif the corresponding option is selected by default (the default is ``false``).",
        },
    )


@dataclass(kw_only=True)
class Regex(BaseSetting):
    """A regular expression defines a pattern of characters. The patterns include the following:
    * ``GCTA``, which matches on the fixed string "GCTA";
    * ``[abcd]``, which matches on the characters a, b, c, or d;
    * ``[CG]{12}``, which matches on 12 consecutive characters that are C or G;
    * ``a.*z``, which matches on the character "a", followed by 0 or more characters of any type, followed by a "z";
    * ``^X``, which matches the letter X at the beginning of a string;
    * ``Y$``, which matches the letter Y at the end of a string.
    There are many more possible regular expressions. A reference to all supported
    regular expressions can be found under
    [Python Regular Expression Syntax](https://docs.python.org/3/library/re.html#regular-expression-syntax).
    A regular expression includes the following attributes:
    * ``source``: This tells whether the regular expression should be matched against stdout, stderr, or both. If this attribute is missing or is incorrect, then both stdout and stderr will be checked. The source can be one of the following values:
    * ``stdout``: the regular expression will be applied to stdout;
    * ``stderr``: the regular expression will be applied to stderr;
    * ``both``: the regular expression will be applied to both stderr and stdout (which is the default case).
    * ``match``: This is the regular expression that will be used to match against stdout and/or stderr. If the ``&lt;regex&gt;`` tag does not contain the match attribute, then the ``&lt;regex&gt;`` tag will be ignored. The regular expression can be any valid Python regular expression. All regular expressions are performed case insensitively. For example, if match contains the regular expression "actg", then the regular expression will match against "actg", "ACTG", "AcTg", and so on. Also note that, if double quotes (") are to be used in the match attribute, then the value " can be used in place of double quotes. Likewise, if single quotes (') are to be used in the match attribute, then the value ' can be used if necessary.
    * ``level``: This works very similarly to the ``&lt;exit_code&gt;`` tag, except that, when a regular expression matches against its source, the description is added to the beginning of the source. For example, if stdout matches on a regular expression, then the regular expression's description is added to the beginning of stdout (instead of stderr). If no level is specified, then the fatal error level will be assumed to have occurred. The level can have one of following values:
    * ``log``, ``qc``, and ``warning``: If the regular expression matches against its source input (i.e., stdout and/or stderr), then a description of the error will be added to the beginning of the source, prepended with either 'QC:', 'Log:', or 'Warning:'. This will not cause the tool to fail.
    * ``fatal``: If the regular expression matches against its source input, then a description of the error will be added to the beginning of the source. A fatal-level error will cause the tool to fail.
    * ``fatal_oom``: In contrast to fatal the job might be resubmitted if possible according to the job configuration.
    * ``description``: Just like its ``exit_code`` counterpart, this is an optional description of the regular expression that has matched.
    The following is an example of regular expressions that may be used:
    ```xml
    &lt;stdio&gt;
    &lt;regex match="low space"
    source="both"
    level="warning"
    description="Low space on device" /&gt;
    &lt;regex match="error"
    source="stdout"
    level="fatal"
    description="Unknown error encountered" /&gt;
    &lt;!-- Catching fatal_oom allows the job runner to potentially resubmit to a resource with more
    memory if Galaxy is configured to do this. --&gt;
    &lt;regex match="out of memory"
    source="stdout"
    level="fatal_oom"
    description="Out of memory error occurred" /&gt;
    &lt;regex match="[CG]{12}"
    description="Fatal error - CG island 12 nts long found" /&gt;
    &lt;regex match="^Branch A"
    level="warning"
    description="Branch A was taken in execution" /&gt;
    &lt;/stdio&gt;
    ```
    The regular expression matching proceeds as follows. First, if either stdout or
    stderr match on ``low space``, then a warning is registered. If stdout contained
    the string ``---LOW SPACE---``, then stdout has the string ``Warning: Low space
    on device`` added to its beginning. The same goes for if stderr had contained the
    string ``low space``. Since only a warning could have occurred, the processing
    continues.
    Next, the regular expression ``error`` is matched only against stdout. If stdout
    contains the string ``error`` regardless of its capitalization, then a fatal
    error has occurred and the processing stops. In that case, stdout would be
    prepended with the string ``Fatal: Unknown error encountered``. Note that, if
    stderr contained ``error``, ``ERROR``, or ``ErRor`` then it would not matter -
    stderr was not being scanned.
    If the second regular expression does not match, the regular expression "out of memory"
    is checked on stdout. If found, Galaxy tries to resubmit the job with more memory
    if configured correctly, otherwise the job fails.
    If the previous regular expressions does not match, then the fourth regular
    expression is checked. The fourth regular expression does not contain an error
    level, so an error level of ``fatal`` is assumed. The fourth regular expression
    also does not contain a source, so both stdout and stderr are checked. The fourth
    regular expression looks for 12 consecutive "C"s or "G"s in any order and in
    uppercase or lowercase. If stdout contained ``cgccGGCCcGGcG`` or stderr
    contained ``CCCCCCgggGGG``, then the regular expression would match, the tool
    would be marked with a fatal error, and the stream that contained the
    12-nucleotide CG island would be prepended with ``Fatal: Fatal error - CG island
    12 nts long found``.
    Finally, if the tool did not match any of the fatal errors, then the fifth
    regular expression is checked. Since no source is specified, both stdout and
    stderr are checked. If ``Branch A`` is at the beginning of stdout or stderr, then
    a warning will be registered and the source that contained ``Branch A`` will be
    prepended with the warning ``Warning: Branch A was taken in execution``."""

    source: Optional[SourceType] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "This tells whether the regular expression should be matched against stdout, stderr, or both. If this attribute is missing or is incorrect, then both stdout and stderr will be checked.",
        },
    )
    match: str = field(
        metadata={
            "type": "Attribute",
            "required": True,
            "description": "This is the regular expression that will be used to match against stdout and/or stderr.",
        }
    )
    level: Optional[LevelType] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "This works very similarly to the 'exit_code' tag, except that, when a regular expression matches against its source, the description is added to the beginning of the source.",
        },
    )
    description: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "an optional description of the regular expression that has matched.",
        },
    )


@dataclass(kw_only=True)
class RequestParameterAppend(BaseSetting):
    """Optionally contained within the [request_param](#tool-request-param-
    translation-request-param) element if ``galaxy_name="URL"``.

    Some remote data sources (e.g., Gbrowse, Biomart) send parameters back to Galaxy in the initial response that must be added to the value of "URL" prior to Galaxy sending the secondary request to the remote data source via URL.
    """

    value: List[RequestParameterAppendValue] = field(default_factory=list, metadata={"type": "Element"})
    separator: str = field(
        metadata={
            "type": "Attribute",
            "required": True,
            "description": 'The text to use to join the requested parameters together (example ``separator="&amp;amp;"``).',
        }
    )
    first_separator: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": 'The text to use to join the ``request_param`` parameters to the first requested parameter (example ``first_separator="?"``).',
        },
    )
    join: str = field(
        metadata={
            "type": "Attribute",
            "required": True,
            "description": 'The text to use to join the param name to its value (example ``join="="``).',
        }
    )


@dataclass(kw_only=True)
class RequestParameterValueTranslation(BaseSetting):
    """Optionally contained within the [request_param](#tool-request-param-
    translation-request-param) tag set.

    The parameter value received from a remote data source may be named differently in Galaxy, and this tag set allows for the value to be appropriately translated.
    """

    value: List[RequestParameterValueTranslationValue] = field(default_factory=list, metadata={"type": "Element"})


@dataclass(kw_only=True)
class RequiredFileExclude(BaseSetting):
    """
    Describe files to exclude when relocating tool directory for remote execution.
    """

    type_value: Optional[RequiredFileReferenceType] = field(
        default=None, metadata={"name": "type", "type": "Attribute", "description": "Type of file reference `path` is."}
    )
    path: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Path to referenced files - this should be relative to the tool's directory (this is the file the tool is located in not the repository directory if these conflict).",
        },
    )


@dataclass(kw_only=True)
class RequiredFileInclude(BaseSetting):
    """
    Describe files to include when relocating tool directory for remote execution.
    """

    type_value: Optional[RequiredFileReferenceType] = field(
        default=None, metadata={"name": "type", "type": "Attribute", "description": "Type of file reference `path` is."}
    )
    path: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Path to referenced files - this should be relative to the tool's directory (this is the file the tool is located in not the repository directory if these conflict).",
        },
    )


@dataclass(kw_only=True)
class Requirement(BaseSetting):
    """This tag set is contained within the ``&lt;requirements&gt;`` tag set. Third party
    programs or modules that the tool depends upon are included in this tag set.
    When a tool runs, Galaxy attempts to *resolve* these requirements (also called
    dependencies). ``requirement``s are meant to be abstract and resolvable by
    multiple different [dependency resolvers](../admin/dependency_resolvers) (e.g. [conda](https://conda.io/), the
    [Galaxy Tool Shed dependency management system](https://galaxyproject.org/toolshed/tool-features/),
    or [environment modules](https://modules.sourceforge.net/)).
    The current best practice for tool dependencies is to [target Conda](../admin/conda_faq).
    ### Examples
    This example shows a tool that requires the samtools 0.0.18 package.
    This package is available via the Tool Shed (see
    [Tool Shed dependency management](https://galaxyproject.org/toolshed/tool-features/)
    ) as well as [Conda](../admin/conda_faq)
    and can be configured locally to adapt to any other package management system.
    ```xml
    &lt;requirements&gt;
    &lt;requirement type="package" version="0.1.18"&gt;samtools&lt;/requirement&gt;
    &lt;/requirements&gt;
    ```
    This older example shows a tool that requires R version 2.15.1. The
    ``tool_dependencies.xml`` should contain matching declarations for Galaxy to
    actually install the R runtime. The ``set_envirornment`` type is only respected
    by the tool shed and is ignored by the newer and preferred conda dependency
    resolver.
    ```xml
    &lt;requirements&gt;
    &lt;requirement type="set_environment"&gt;R_SCRIPT_PATH&lt;/requirement&gt;
    &lt;requirement type="package" version="2.15.1"&gt;R&lt;/requirement&gt;
    &lt;/requirements&gt;
    ```"""

    value: str = field(default="", metadata={"required": True})
    type_value: RequirementType = field(
        metadata={
            "name": "type",
            "type": "Attribute",
            "required": True,
            "description": "Valid values are ``package``, ``set_environment``, ``python-module`` (deprecated), ``binary`` (deprecated)",
        }
    )
    version: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "For requirements of type ``package`` this value defines a specific version of the tool dependency.",
        },
    )


@dataclass(kw_only=True)
class Resource(BaseSetting):
    value: str = field(default="", metadata={"required": True})
    type_value: ResourceType = field(
        metadata={
            "name": "type",
            "type": "Attribute",
            "required": True,
            "description": "This value describes the type of resource required by the tool at runtime. Not yet implemented in Galaxy.",
        }
    )


@dataclass(kw_only=True)
class SanitizerMapping(BaseSetting):
    """Contained within the ``&lt;sanitizer&gt;`` tag set.

    Used to specify a mapping of disallowed character to replacement string. Contains ``&lt;add&gt;`` and ``&lt;remove&gt;`` tags.
    """

    add: List[SanitizerMappingAdd] = field(default_factory=list, metadata={"type": "Element"})
    remove: List[SanitizerMappingRemove] = field(default_factory=list, metadata={"type": "Element"})
    initial: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Initial character mapping (default is ``galaxy.util.mapped_chars``)",
        },
    )


@dataclass(kw_only=True)
class SanitizerValid(BaseSetting):
    """Contained within the ``&lt;sanitizer&gt;`` tag set, these are used to
    specify a list of allowed characters.

    Contains ``&lt;add&gt;`` and ``&lt;remove&gt;`` tags.
    """

    add: List[SanitizerValidAdd] = field(default_factory=list, metadata={"type": "Element"})
    remove: List[SanitizerValidRemove] = field(default_factory=list, metadata={"type": "Element"})
    initial: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "This describes the initial characters to\nallow as valid, specified as a character preset (as defined above). The default\nis the ``default`` preset.",
        },
    )


@dataclass(kw_only=True)
class TestParam(BaseSetting):
    """This tag set defines the tool's input parameters for executing the tool via
    the functional test framework.

    See [test](#tool-tests-test) documentation for
    some simple examples of parameters.
    ### Parameter Types
    #### ``text``, ``integer``, and ``float``
    Values for these parameters are simply given by the desired value.
    #### ``boolean``
    The value of the test parameter should be set to `true` or `false` corresponding
    to the cases that the parameter is checked or not. It is also possible, but
    discouraged, to use the value specified as `truevalue` or `falsevalue`.
    #### ``data``
    Data input parameters can be given as a file name. The file should exist in the
    `test-data` folder. Multiple files can be specified as comma separated list.
    #### ``select``
    The value of a select parameter should be specified as the value of one of the
    legal options. If more than one option is selected (`multiple="true"`) they
    should be given as comma separated list. For optional selects
    (`optional="true"`) the case that no option is selected can be specified with
    `value=""`.
    While in general it is preferred to specify the selected cases by their values it
    is also possible to specify them by their name (i.e. the content of the
    `option` tag that is shown to the user). One use case is a dynamic select that is
    generated from a data table with two columns: name and value where the value is
    a path. Since the path changes with the test environment it can not be used to
    select an option for a test.
    """

    collection: Optional[TestCollection] = field(default=None, metadata={"type": "Element"})
    composite_data: List[TestCompositeData] = field(default_factory=list, metadata={"type": "Element"})
    metadata: List[TestParamMetadata] = field(default_factory=list, metadata={"type": "Element"})
    name: str = field(
        metadata={
            "type": "Attribute",
            "required": True,
            "description": "This value must match the name of the\nassociated input parameter (``param``).",
        }
    )
    value: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "This value must be one of the legal\nvalues that can be assigned to an input parameter.",
        },
    )
    value_json: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "This variant of the value parameters can be\nused to load typed parameters. This string will be loaded as JSON and its type will\nattempt to be preserved through API requests to Galaxy.",
        },
    )
    ftype: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "This attribute name should be included\nonly with parameters of ``type`` ``data`` for the tool. If this\nattribute name is not included, the functional test framework will attempt to\ndetermine the data type for the input dataset using the data type sniffers.",
        },
    )
    dbkey: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Specifies a ``dbkey`` value for the\nreferenced input dataset. This is only valid if the corresponding parameter is\nof ``type`` ``data``.",
        },
    )
    tags: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Comma separated list of tags to apply to the dataset (only works for elements of collections - e.g. ``element`` XML tags).",
        },
    )
    location: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "URL that points to a remote input file that will be downloaded and used as input.\nPlease use this option only when is not possible to include the files in the `test-data` folder, since\nthis is more error prone due to external factors like remote availability.\nYou can use it in two ways:\n- If only ``location`` is given (and `value` is absent), the input file will be uploaded directly to Galaxy from the URL specified by the ``location``  (same as regular pasted URL upload).\n- If ``location`` as well as ``value`` are given, the input file specified in ``value`` will be used from the tes data directory, if it's not available on disk it will use the ``location`` to upload the input as the previous case.",
        },
    )


@dataclass(kw_only=True)
class TracksterConf(BaseSetting):
    """
    This directive is used to specify some rarely modified trackster options.
    """

    action: List[TracksterAction] = field(default_factory=list, metadata={"type": "Element"})


@dataclass(kw_only=True)
class Validator(BaseSetting):
    """This tag set is contained within the ``&lt;param&gt;`` tag set - it applies a
    validator to the containing parameter. Tool submission will fail if a
    single validator fails. See the
    [annotation_profiler](https://github.com/galaxyproject/tools-devteam/blob/main/tools/annotation_profiler/annotation_profiler.xml)
    tool for an example of how to use this tag set.
    Note that validators for parameters with ``optional="true"`` are not
    executed if no value is given.
    ### Generic validators
    - ``expression``: Check if a one line python expression given expression
    evaluates to True. The expression is given is the content of the validator tag.
    ### Validators for ``data`` and ``data_collection`` parameters
    In case of ``data_collection`` parameters and
    ``data`` parameters with ``multiple="true"`` these validators are executed
    separately for each of the contained data sets. Note that, for ``data``
    parameters a ``metadata`` validator is added automatically.
    - ``metadata``: Check for missing metadata. The set of (optional) metadata
    to be checked can be set using either the ``check`` or ``skip`` attribute.
    Note that each data parameter has automatically a metadata validator that checks
    if all non-optional metadata are set, i.e. ``&lt;validator type="metadata/&gt;``.
    - ``unspecified_build``: Check of a build is defined.
    - ``dataset_ok_validator``: Check if the data set is in state OK.
    - ``dataset_metadata_equal``: Check if metadata (given by ``metadata_name``) is equal to a given string value (given by ``value``) or JSON encoded value (given by ``value_json``). ``value_json`` needs to be used for all non string types (e.g. int, float, list, dict).
    - ``dataset_metadata_in_range``: Check if a numeric metadata value is within
    a given range.
    - ``dataset_metadata_in_data_table``: Check if a metadata value is contained in a column of a data table.
    - ``dataset_metadata_not_in_data_table``: Equivalent to ``dataset_metadata_in_data_table`` with ``negate="true"``.
    Deprecated data validators:
    - ``dataset_metadata_in_file``: Use data tables with ``dataset_metadata_in_data_table``.
    Check if a metadata value is contained in a specific column of a file in the ``tool_data_path``
    (which is set in Galaxy's config).
    ### Validators for textual inputs (``text``, ``select``, ...)
    - ``regex``: Check if a regular expression **matches** the value, i.e. appears
    at the beginning of the value. To enforce a match of the complete value use
    ``$`` at the end of the expression. The expression is given is the content
    of the validator tag. Note that for ``selects`` each option is checked
    separately.
    - ``length``: Check if the length of the value is within a range.
    - ``empty_field``: Check if the string is not empty
    - ``value_in_data_table``: Check if the value is
    contained in a column of a given data table.
    - ``value_not_in_data_table``: Equivalent to ``value_in_data_table`` with ``negate="true"``.
    For selects (in particular with dynamically defined options) the following
    validator is useful:
    ``no_options``: Check if options are available for a ``select`` parameter.
    Useful for parameters with dynamically defined options.
    ### Validators for numeric inputs (``integer``, ``float``)
    ``in_range``: Check if the value is in a given range.
    ### Examples
    The following demonstrates a simple validator ``unspecified_build`` ensuring
    that a dbkey is present on the selected dataset. This example is taken from the
    [extract_genomic_dna](https://github.com/galaxyproject/tools-iuc/blob/main/tools/extract_genomic_dna/extract_genomic_dna.xml#L42)
    tool.
    ```xml
    &lt;param name="input" type="data" format="gff,interval" label="Fetch sequences for intervals in"&gt;
    &lt;validator type="unspecified_build" /&gt;
    &lt;/param&gt;
    ```
    Along the same line, the following example taken from
    [samtools_mpileup](https://github.com/galaxyproject/tools-devteam/blob/main/tool_collections/samtools/samtools_mpileup/samtools_mpileup.xml)
    ensures that a dbkey is present and that FASTA indices in the ``fasta_indexes``
    tool data table are present.
    ```xml
    &lt;param format="bam" label="BAM file(s)" name="input_bam" type="data" min="1" multiple="true"&gt;
    &lt;validator type="unspecified_build" /&gt;
    &lt;validator type="dataset_metadata_in_data_table" metadata_name="dbkey" table_name="fasta_indexes" metadata_column="1"
    message="Sequences are not currently available for the specified build." /&gt;
    &lt;/param&gt;
    ```
    In this older, somewhat deprecated example - a genome build of the dataset must
    be stored in Galaxy clusters and the name of the genome (``dbkey``) must be one
    of the values in the first column of file ``alignseq.loc`` - that could be
    expressed with the validator. In general, ``dataset_metadata_in_file`` should be
    considered deprecated in favor of
    ```xml
    &lt;validator type="dataset_metadata_in_data_table"
    metadata_name="dbkey"
    metadata_column="1"
    message="Sequences are not currently available for the specified build." /&gt;
    ```
    A very common validator is simply ensure a Python expression is valid for a
    specified value. In the following example - paths/names that downstream tools
    use in filenames may not contain ``..``.
    ```xml
    &lt;validator type="expression" message="No two dots (..) allowed"&gt;'..' not in value&lt;/validator&gt;
    ```"""

    type_value: ValidatorType = field(
        metadata={
            "name": "type",
            "type": "Attribute",
            "required": True,
            "description": "Valid values are: ``expression``, ``regex``, ``in_range``, ``length``,\n``metadata``, ``metadata_eq`` ``unspecified_build``, ``no_options``, ``empty_field``,\n``dataset_metadata_in_data_table``, ``dataset_metadata_not_in_data_table``,\n``value_in_data_table``, ``value_not_in_data_table``,\n``dataset_ok_validator``, ``dataset_metadata_in_range``.\nDeprecated validator: ``dataset_metadata_in_file``.\nThe list of supported\nvalidators is in the ``validator_types`` dictionary in\n[/lib/galaxy/tools/parameters/validation.py](https://github.com/galaxyproject/galaxy/blob/dev/lib/galaxy/tools/parameters/validation.py).",
        }
    )
    message: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "The error message displayed on the tool form if validation fails. A placeholder string ``%s`` will be repaced by the ``value``",
        },
    )
    negate: bool = field(
        default=False, metadata={"type": "Attribute", "description": "Negates the result of the validator."}
    )
    check: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Comma-seperated list of metadata\nfields to check for if type is ``metadata``. If not specified, all non-optional\nmetadata fields will be checked unless they appear in the list of fields\nspecified by the ``skip`` attribute.",
        },
    )
    table_name: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Tool data table name to check against\nif ``type`` is ``dataset_metadata_in_data_table``, ``dataset_metadata_not_in_data_table``, ``value_in_data_table``, or ``value_not_in_data_table``. See the documentation for\n[tool data tables](https://galaxyproject.org/admin/tools/data-tables)\nand [data managers](https://galaxyproject.org/admin/tools/data-managers/) for\nmore information.",
        },
    )
    filename: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Deprecated: use ``dataset_metadata_in_data_table``. Tool data filename to check against\nif ``type`` is ``dataset_metadata_in_file``. File should be present Galaxy's\n``tool-data`` directory.",
        },
    )
    metadata_name: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Target metadata attribute name for\n``dataset_metadata_in_data_table``, ``dataset_metadata_not_in_data_table``, ``dataset_metadata_in_file`` and ``dataset_metadata_in_range`` options.",
        },
    )
    metadata_column: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Target column for metadata attribute\nin ``dataset_metadata_in_data_table``, ``dataset_metadata_not_in_data_table``, ``value_in_data_table``, ``value_not_in_data_table``, and ``dataset_metadata_in_file`` options.\nThis can be an integer index to the column or a column name.",
        },
    )
    min: Optional[Decimal] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "When the ``type`` attribute value is\n``in_range``, ``length``, or ``dataset_metadata_in_range`` - this is the minimum number allowed.",
        },
    )
    max: Optional[Decimal] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "When the ``type`` attribute value is\n``in_range``, ``length``, or ``dataset_metadata_in_range`` - this is the maximum number allowed.",
        },
    )
    exclude_min: bool = field(
        default=False,
        metadata={
            "type": "Attribute",
            "description": "When the ``type`` attribute value is\n``in_range``, ``length``, or ``dataset_metadata_in_range`` - this boolean indicates if the ``min`` value is allowed.",
        },
    )
    exclude_max: bool = field(
        default=False,
        metadata={
            "type": "Attribute",
            "description": "When the ``type`` attribute value is\n``in_range``, ``length``, or ``dataset_metadata_in_range`` - this boolean indicates if the ``max`` value is allowed.",
        },
    )
    split: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "If ``type`` is ``dataset_metadata_in_file``,\nthis attribute is the column separator to use for values in the specified file.\nThis default is ``\\t`` and due to a bug in older versions of Galaxy, should\nnot be modified.",
        },
    )
    skip: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Comma-seperated list of metadata\nfields to skip if type is ``metadata``. If not specified, all non-optional\nmetadata fields will be checked unless ``check`` attribute is specified.",
        },
    )
    value: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Value to check the metadata against. Only\napplicable to ``dataset_metadata_equal``. Mutually exclusive with ``value_json``.",
        },
    )
    value_json: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "JSON encoded value to check the metadata against. Only\napplicable to ``dataset_metadata_equal``. Mutually exclusive with ``value``.",
        },
    )
    line_startswith: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Deprecated. Used to indicate lines in the file\nbeing used for validation start with a this attribute value.\nFor use with validator ``dataset_metadata_in_file``",
        },
    )
    substitute_value_in_message: Optional[str] = field(
        default=None, metadata={"type": "Attribute", "description": "Deprecated. This is now always done."}
    )


@dataclass(kw_only=True)
class Xref(BaseSetting):
    """
    The ``xref`` element specifies reference information according to a catalog.
    """

    class Meta:
        name = "xref"

    value: str = field(default="", metadata={"required": True})
    type_value: XrefType = field(
        metadata={
            "name": "type",
            "type": "Attribute",
            "required": True,
            "description": "Type of reference - currently ``bio.tools``, ``bioconductor``, and ``biii`` are\nthe only supported options.",
        }
    )


@dataclass(kw_only=True)
class ActionsOption(BaseSetting):
    """1. Load options from a data table, a parameter (or its metadata), or a file
    2. Filter the options using all filters defined by the contained ``filter`` tags.
    3. Chose a value in a given line (``offset``) and ``column``
    The options can be considered as a table where each line is an option. The values
    in the columns can be used for filtering.
    The different data sources can be loaded as follows:
    - ``from_data_table``: load the options from the data table with the given ``name``.
    - ``from_param``: Initialize a single option containing the value of the
    referred parameter (``name``) or its metadata (``param_attribute``)
    - ``from_file``: Load the file the given ``name`` (in Galaxy's tool data path), columns
    are defined by the given ``separator`` (default is tab)."""

    filter: List[ActionsConditionalFilter] = field(default_factory=list, metadata={"type": "Element"})
    type_value: ActionsOptionType = field(
        metadata={
            "name": "type",
            "type": "Attribute",
            "required": True,
            "description": "Source of the tabular data ``from_data_table``, ``from_param``, or ``from_file``.",
        }
    )
    name: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Name of the referred data table, parameter, or file (required).",
        },
    )
    column: Optional[int] = field(
        default=None, metadata={"type": "Attribute", "description": "The column to choose the value from (required)"}
    )
    offset: Optional[int] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "The row (of the options) to choose the value from (by default -1, ie. last row)",
        },
    )
    param_attribute: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Applies to ``from_param``. The attribute of the parameter to use.",
        },
    )


@dataclass(kw_only=True)
class AssertElementText(BaseSetting):
    """This tag allows the developer to recurisively specify additional assertions
    as child elements about just the text contained in the element specified by the
    XPath-like ``path``, e.g. ```xml &lt;element_text
    path="BlastOutput_iterations/Iteration/Iteration_hits/Hit/Hit_def"&gt;
    &lt;not_has_text text="EDK72998.1" /&gt; &lt;/element_text&gt; ``` The
    assertion implicitly also asserts that an element matching ``path`` exists.

    With ``negate`` the result of the implicit assertions can be inverted.
    The sub-assertions, which have their own ``negate`` attribute, are not affected
    by ``negate``.
    $attribute_list::5
    """

    has_text: List[AssertHasText] = field(default_factory=list, metadata={"type": "Element"})
    not_has_text: List[AssertNotHasText] = field(default_factory=list, metadata={"type": "Element"})
    has_text_matching: List[AssertHasTextMatching] = field(default_factory=list, metadata={"type": "Element"})
    has_line: List[AssertHasLine] = field(default_factory=list, metadata={"type": "Element"})
    has_line_matching: List[AssertHasLineMatching] = field(default_factory=list, metadata={"type": "Element"})
    has_n_lines: List[AssertHasNlines] = field(default_factory=list, metadata={"type": "Element"})
    path: str = field(
        metadata={
            "type": "Attribute",
            "required": True,
            "description": "Path to check for. Valid paths are the simplified subsets of XPath implemented by lxml.etree; https://lxml.de/xpathxslt.html for more information.",
        }
    )
    negate: Union[bool, PermissiveBooleanValue] = field(
        default=PermissiveBooleanValue.FALSE,
        metadata={"type": "Attribute", "description": "Negate the outcome of the assertion."},
    )


@dataclass(kw_only=True)
class Citations(BaseSetting):
    """Tool files may declare one.

    citations element. Each citations element can contain one or more citation tag
    elements - each of which specifies tool citation information using either a DOI
    or a BibTeX entry.
    These citations will appear at the bottom of the tool form in a formatted way
    but the user will have to option to select RAW BibTeX for copying and pasting as
    well. Likewise, the history menu includes an option allowing users to aggregate
    all such citations across an analysis in a list of citations.
    BibTeX entries for citations annotated with DOIs will be fetched by Galaxy from
    https://doi.org/ and cached.
    ```xml
    &lt;citations&gt;
    &lt;!-- Example of annotating a citation using a DOI. --&gt;
    &lt;citation type="doi"&gt;10.1093/bioinformatics/btq281&lt;/citation&gt;
    &lt;!-- Example of annotating a citation using a BibTex entry. --&gt;
    &lt;citation type="bibtex"&gt;@ARTICLE{Kim07aninterior-point,
    author = {Seung-jean Kim and Kwangmoo Koh and Michael Lustig and Stephen Boyd and Dimitry Gorinevsky},
    title = {An interior-point method for large-scale l1-regularized logistic regression},
    journal = {Journal of Machine Learning Research},
    year = {2007},
    volume = {8},
    pages = {1519-1555}
    }&lt;/citation&gt;
    &lt;/citations&gt;
    ```
    For more implementation information see the
    [pull request](https://bitbucket.org/galaxy/galaxy-central/pull-requests/440/initial-bibtex-doi-citation-support-in/diff)
    adding this feature. For more examples of how to add this to tools checkout the
    following commits adding this to the
    [NCBI BLAST+ suite](https://github.com/peterjc/galaxy_blast/commit/9d2e3906915895765ecc3f48421b91fabf2ccd8b),
    [phenotype association tools](https://bitbucket.org/galaxy/galaxy-central/commits/39c983151fe328ff5d415f6da81ce5b21a7e18a4),
    [MAF suite](https://bitbucket.org/galaxy/galaxy-central/commits/60f63d6d4cb7b73286f3c747e8acaa475e4b6fa8),
    and [MACS2 suite](https://github.com/jmchilton/galaxytools/commit/184971dea73e236f11e82b77adb5cab615b8391b).
    This feature was added to the August 2014 release of Galaxy, tools annotated
    with citations will work in older releases of Galaxy but no citation information
    will be available to the end user.
    """

    citation: List[Citation] = field(default_factory=list, metadata={"type": "Element"})


@dataclass(kw_only=True)
class EntryPoints(BaseSetting):
    """This is a container tag set for the ``entry_point`` tag that contains
    ``port`` and ``url`` tags described in greater detail below.

    ``entry_point``s describe InteractiveTool entry points
    to a tool.
    """

    entry_point: List[EntryPoint] = field(default_factory=list, metadata={"type": "Element"})


@dataclass(kw_only=True)
class EnvironmentVariables(BaseSetting):
    """
    This directive should contain one or more ``environment_variable`` definition.
    """

    environment_variable: List[EnvironmentVariable] = field(default_factory=list, metadata={"type": "Element"})


@dataclass(kw_only=True)
class ParamDefault(BaseSetting):
    element: List[ParamDefaultElement] = field(default_factory=list, metadata={"type": "Element"})
    collection_type: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Collection type for default collection (if param type is data_collection). Simple collection types are\neither ``list`` or ``paired``, nested collections are specified as colon separated list of simple\ncollection types (the most common types are ``list``, ``paired``,\n``list:paired``, or ``list:list``).",
        },
    )
    location: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": 'Galaxy-aware URI for the default file. This should only be used with parameters of type "data".',
        },
    )


@dataclass(kw_only=True)
class ParamOptions(BaseSetting):
    """See [/tools/extract/liftOver_wrapper.xml](https://github.com/galaxyproject/galaxy/blob/dev/tools/extract/liftOver_wrapper.xml)
    for an example of how to use this tag set. This tag set is optionally contained
    within the ``&lt;param&gt;`` tag when the ``type`` attribute value is ``select`` or
    ``data`` and used to dynamically generated lists of options.
    For data parameters this tag can be used to restrict possible input datasets to datasets that match the ``dbkey`` of another data input by including a ``data_meta`` filter. See for
    instance here: [/tools/maf/interval2maf.xml](https://github.com/galaxyproject/galaxy/blob/dev/tools/maf/interval2maf.xml)
    For select parameters this tag set dynamically creates a list of options whose
    values can be obtained from a predefined file stored locally or a dataset
    selected from the current history.
    There are at least five basic ways to use this tag - four of these correspond to
    a ``from_XXX`` attribute on the ``options`` directive and the other is to
    exclusively use ``filter``s to populate options.
    * ``from_data_table`` - The options for the select list are dynamically obtained
    from a file specified in the Galaxy configuration file
    ``tool_data_table_conf.xml`` or from a Tool Shed installed data manager.
    * ``from_dataset`` - The options for the select list are dynamically obtained
    from input dataset selected for the tool from the current history.
    * ``from_file`` - The options for the select list are dynamically obtained from
    a file. This mechanism is discouraged in favor of the more generic
    ``from_data_table``.
    * ``from_parameter`` - The options for the select list are dynamically obtained
    from a parameter.
    * Using ``filter``s - various filters can be used to populate options, see
    examples in the [filter](#tool-inputs-param-options-filter) documentation.
    ### ``from_data_table``
    See Galaxy's
    [data tables documentation](https://galaxyproject.org/admin/tools/data-tables)
    for information on setting up data tables.
    Once a data table has been configured and populated, these can be easily
    leveraged via tools.
    This ``conditional`` block in the
    [bowtie2](https://github.com/galaxyproject/tools-devteam/blob/main/tools/bowtie2/bowtie2_wrapper.xml)
    wrapper demonstrates using ``from_data_table`` options as an
    alternative to local reference data.
    ```xml
    &lt;conditional name="reference_genome"&gt;
    &lt;param name="source" type="select" label="Will you select a reference genome from your history or use a built-in index?" help="Built-ins were indexed using default options. See `Indexes` section of help below"&gt;
    &lt;option value="indexed"&gt;Use a built-in genome index&lt;/option&gt;
    &lt;option value="history"&gt;Use a genome from the history and build index&lt;/option&gt;
    &lt;/param&gt;
    &lt;when value="indexed"&gt;
    &lt;param name="index" type="select" label="Select reference genome" help="If your genome of interest is not listed, contact the Galaxy team"&gt;
    &lt;options from_data_table="bowtie2_indexes"&gt;
    &lt;filter type="sort_by" column="2"/&gt;
    &lt;/options&gt;
    &lt;validator type="no_options" message="No indexes are available for the selected input dataset"/&gt;
    &lt;/param&gt;
    &lt;/when&gt;
    &lt;when value="history"&gt;
    &lt;param name="own_file" type="data" format="fasta" label="Select reference genome" /&gt;
    &lt;/when&gt;
    &lt;/conditional&gt;
    ```
    A minimal example wouldn't even need the ``filter`` or ``validator`` above, but
    they are frequently nice features to add to your wrapper and can improve the user
    experience of a tool.
    ### ``from_dataset``
    The following example is taken from the Mothur tool
    [remove.lineage.xml](https://github.com/galaxyproject/tools-iuc/blob/main/tools/mothur/remove.lineage.xml)
    and demonstrates generating options from a dataset directly.
    ```xml
    &lt;param name="taxonomy" type="data" format="mothur.seq.taxonomy" label="taxonomy - Taxonomy" help="please make sure your file has no quotation marks in it"/&gt;
    &lt;param name="taxons" type="select" optional="true" multiple="true" label="Browse Taxons from Taxonomy"&gt;
    &lt;options from_dataset="taxonomy"&gt;
    &lt;column name="name" index="1"/&gt;
    &lt;column name="value" index="1"/&gt;
    &lt;filter type="unique_value" name="unique_taxon" column="1"/&gt;
    &lt;filter type="sort_by" name="sorted_taxon" column="1"/&gt;
    &lt;/options&gt;
    &lt;sanitizer&gt;
    &lt;valid initial="default"&gt;
    &lt;add preset="string.printable"/&gt;
    &lt;add value=";"/&gt;
    &lt;remove value="&amp;quot;"/&gt;
    &lt;remove value="&amp;apos;"/&gt;
    &lt;/valid&gt;
    &lt;/sanitizer&gt;
    &lt;/param&gt;
    ```
    Starting from Galaxy v21.01, ``meta_file_key`` can be used together with
    ``from_dataset``. In such cases, options are generated using the dataset's
    medadata file that the ``meta_file_key`` implies, instead of the dataset
    itself.
    Note that in any case only the first mega byte of the referred dataset (or file)
    is considered. Lines starting with ``#`` are ignored. By using the ``startswith``
    attribute also lines starting with other strings can be ignored.
    ```xml
    &lt;param name="input" type="data" format="maf" label="MAF File"/&gt;
    &lt;param name="species" type="select" optional="False" label="Select species for the input dataset" multiple="True"&gt;
    &lt;options from_dataset="input" meta_file_key="species_chromosomes"&gt;
    &lt;column name="name" index="0"/&gt;
    &lt;column name="value" index="0"/&gt;
    &lt;/options&gt;
    &lt;/param&gt;
    &lt;param name="input_2" type="data_collection" collection_type="list" format="maf" label="MAF Collection" multiple="true" /&gt;
    &lt;param name="species_2" type="select" optional="false" label="Select species for the input dataset" multiple="true"&gt;
    &lt;options from_dataset="input_2" meta_file_key="species_chromosomes" &gt;
    &lt;column name="name" index="0"/&gt;
    &lt;column name="value" index="0"/&gt;
    &lt;filter type="unique_value" name="unique_param" column="0"/&gt;
    &lt;/options&gt;
    &lt;/param&gt;
    ```
    Filters can be used to generate options from dataset directly also as the
    example below demonstrates (many more examples are present in the
    [filter](#tool-inputs-param-options-filter) documentation).
    ```xml
    &lt;param name="species1" type="select" label="When Species" multiple="false"&gt;
    &lt;options&gt;
    &lt;filter type="data_meta" ref="input1" key="species" /&gt;
    &lt;/options&gt;
    &lt;/param&gt;
    ```
    ### ``from_file``
    The following example is for Blast databases. In this example users maybe select
    a database that is pre-formatted and cached in Galaxy clusters. When a new
    dataset is available, admins must add the database to the local file named
    "blastdb.loc". All such databases in that file are included in the options of
    the select list. For a local instance, the file (e.g. ``blastdb.loc`` or
    ``alignseq.loc``) must be stored in the configured
    [tool_data_path](https://github.com/galaxyproject/galaxy/tree/dev/tool-data)
    directory. In this example, the option names and values are taken from column 0
    of the file.
    ```xml
    &lt;param name="source_select" type="select" display="radio" label="Choose target database"&gt;
    &lt;options from_file="blastdb.loc"&gt;
    &lt;column name="name" index="0"/&gt;
    &lt;column name="value" index="0"/&gt;
    &lt;/options&gt;
    &lt;/param&gt;
    ```
    In general, ``from_file`` should be considered deprecated and  ``from_data_table``
    should be prefered.
    ### ``from_parameter``
    This variant of the ``options`` directive is discouraged because it exposes
    internal Galaxy structures. See the older
    [bowtie](https://github.com/galaxyproject/tools-devteam/blob/main/tools/bowtie_wrappers/bowtie_wrapper.xml)
    wrappers for an example of these.
    ### Other Ways to Dynamically Generate Options
    Though deprecated and discouraged, [code](#tool-code) blocks can also be
    used to generate dynamic options."""

    filter: List[Filter] = field(default_factory=list, metadata={"type": "Element"})
    column: List[Column] = field(default_factory=list, metadata={"type": "Element"})
    validator: List[Validator] = field(default_factory=list, metadata={"type": "Element"})
    file: List[str] = field(default_factory=list, metadata={"type": "Element", "description": "Documentation for file"})
    option: List[ParamDrillDownOption] = field(default_factory=list, metadata={"type": "Element"})
    from_dataset: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Determine options from (the first MB of) the dataset given in the referred input parameter. If 'meta_file_key' is given, the options are determined from (the first MB of) the data in the metadata file of the input.",
        },
    )
    from_file: Optional[str] = field(default=None, metadata={"type": "Attribute", "description": "Deprecated."})
    from_data_table: Optional[str] = field(
        default=None, metadata={"type": "Attribute", "description": "Determine options from a data table."}
    )
    from_parameter: Optional[str] = field(default=None, metadata={"type": "Attribute", "description": "Deprecated."})
    options_filter_attribute: Optional[str] = field(
        default=None, metadata={"type": "Attribute", "description": "Deprecated."}
    )
    transform_lines: Optional[str] = field(default=None, metadata={"type": "Attribute", "description": "Deprecated."})
    startswith: Optional[str] = field(
        default=None, metadata={"type": "Attribute", "description": "Keep only lines starting with the given string."}
    )
    meta_file_key: Optional[str] = field(
        default=None,
        metadata={"type": "Attribute", "description": "Works with from_dataset only. See [docs](#from-dataset)"},
    )
    separator: Optional[str] = field(
        default=None,
        metadata={"type": "Attribute", "description": "Split tabular data with this character (default is tab)"},
    )


@dataclass(kw_only=True)
class RequestParameter(BaseSetting):
    """Contained within the [request_param_translation](#tool-request-param-
    translation) tag set (used only in "data_source" tools).

    The external data source application may send back parameter names like "GENOME" which must be translated to "dbkey" in Galaxy.
    """

    append_param: List[RequestParameterAppend] = field(default_factory=list, metadata={"type": "Element"})
    value_translation: List[RequestParameterValueTranslation] = field(
        default_factory=list, metadata={"type": "Element"}
    )
    galaxy_name: RequestParameterGalaxyNameType = field(
        metadata={
            "type": "Attribute",
            "required": True,
            "description": "Each of these maps directly to a ``remote_name`` value",
        }
    )
    remote_name: str = field(
        metadata={
            "type": "Attribute",
            "required": True,
            "description": "The string representing the name of the parameter in the remote data source",
        }
    )
    missing: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "The default value to use for ``galaxy_name`` if the ``remote_name`` parameter is not included in the request",
        },
    )


@dataclass(kw_only=True)
class RequiredFiles(BaseSetting):
    """This declaration is used to define files that must be shipped from the tool
    directory for the tool to function properly in remote environments where the
    tool directory is not available to the job.

    All includes should be list before excludes. By default, the exclude list includes the tool-data/**, test-data/**, and .hg/** glob patterns. Pulsar hacks to implicitly find referenced files from the tool directory will be disabled when this block is used. A future Galaxy tool profile version may disable these hacks altogether and specifying this block for all referenced files should be considered a best practice.
    """

    include: List[RequiredFileInclude] = field(default_factory=list, metadata={"type": "Element"})
    exclude: List[RequiredFileExclude] = field(default_factory=list, metadata={"type": "Element"})
    extend_default_excludes: bool = field(
        default=True,
        metadata={
            "type": "Attribute",
            "description": "Set this to `false` to override the default excludes for mercurial, reference, and test data.",
        },
    )


@dataclass(kw_only=True)
class Requirements(BaseSetting):
    """This is a container tag set for the ``requirement``, ``resource`` and
    ``container`` tags described in greater detail below.

    ``requirement``s describe software packages
    and other individual computing requirements required to execute a tool, while
    ``container``s describe Docker or Singularity containers that should be able to
    serve as complete descriptions of the runtime of a tool.
    """

    requirement: List[Requirement] = field(default_factory=list, metadata={"type": "Element"})
    container: List[Container] = field(default_factory=list, metadata={"type": "Element"})
    resource: List[Resource] = field(default_factory=list, metadata={"type": "Element"})


@dataclass(kw_only=True)
class Sanitizer(BaseSetting):
    """See
    [/tools/filters/grep.xml](https://github.com/galaxyproject/galaxy/blob/dev/tools/filters/grep.xml)
    for a typical example of how to use this tag set. This tag set is used to
    replace the basic parameter sanitization with custom directives. This tag set is
    contained within the ``&lt;param&gt;`` tag set - it contains a set of ``&lt;valid&gt;`` and
    ``&lt;mapping&gt;`` tags.
    ### Character presets
    The following presets can be used when specifying the valid characters: the
    [constants](https://docs.python.org/3/library/string.html#string-constants) from the ``string`` Python3 module,
    plus ``default`` (equal to ``string.ascii_letters + string.digits + " -=_.()/+*^,:?!"``)
    and ``none`` (empty set).
    The ``string.letters``, ``string.lowercase`` and ``string.uppercase`` Python2
    constants are accepted for backward compatibility, but are aliased to the
    corresponding not locale-dependent constant (i.e. ``string.ascii_letters``,
    ``string.ascii_lowercase`` and ``string.ascii_uppercase`` respectively).
    ### Examples
    This example specifies to use the empty string as the invalid character (instead
    of the default ``X``, so invalid characters are effectively dropped instead of
    replaced with ``X``) and indicates that the only valid characters for this input
    are ASCII letters, digits, and ``_``.
    ```xml
    &lt;param name="mystring" type="text" label="Say something interesting"&gt;
    &lt;sanitizer invalid_char=""&gt;
    &lt;valid initial="string.ascii_letters,string.digits"&gt;
    &lt;add value="_" /&gt;
    &lt;/valid&gt;
    &lt;/sanitizer&gt;
    &lt;/param&gt;
    ```
    This example allows many more valid characters and specifies that ``&amp;`` will just
    be dropped from the input.
    ```xml
    &lt;sanitizer&gt;
    &lt;valid initial="string.printable"&gt;
    &lt;remove value="&amp;amp;"/&gt;
    &lt;/valid&gt;
    &lt;mapping initial="none"&gt;
    &lt;add source="&amp;amp;" target=""/&gt;
    &lt;/mapping&gt;
    &lt;/sanitizer&gt;
    ```"""

    valid: List[SanitizerValid] = field(default_factory=list, metadata={"type": "Element"})
    mapping: List[SanitizerMapping] = field(default_factory=list, metadata={"type": "Element"})
    sanitize: Union[bool, PermissiveBooleanValue] = field(
        default=PermissiveBooleanValue.TRUE,
        metadata={
            "type": "Attribute",
            "description": "This boolean parameter determines if the\ninput is sanitized at all (the default is ``true``).",
        },
    )
    invalid_char: str = field(
        default="X",
        metadata={
            "type": "Attribute",
            "description": "The attribute specifies the character\nused as a replacement for invalid characters (the default is ``X``).",
        },
    )


@dataclass(kw_only=True)
class Stdio(BaseSetting):
    """Tools write the bulk of useful data to datasets, but they can also write
    messages to standard I/O (stdio) channels known as standard output (stdout) and
    standard error (stderr).

    Both stdout and stderr are typically written to the executing program's console or terminal. Previous versions of Galaxy checked stderr for execution errors - if any text showed up on stderr, then the tool's execution was marked as failed. However, many tools write messages to stderr that are not errors, and using stderr allows programs to redirect other interesting messages to a separate file. Programs may also exit with codes that indicate success or failure. One convention is for programs to return 0 on success and a non-zero exit code on failure.
    Legacy tools (ones with ``profile`` unspecified or a ``profile`` of less than
    16.04) will default to checking stderr for errors as described above. Newer
    tools will instead treat an exit code other than 0 as an error. The
    ``detect_errors`` on ``command`` can swap between these behaviors but the
    ``stdio`` directive allows more options in defining error conditions (though
    these aren't always intuitive).
    With ``stdio`` directive, Galaxy can use regular expressions to scan stdout and
    stderr, and it also allows exit codes to be scanned for ranges. The ``&lt;stdio&gt;``
    tag has two subtags, ``&lt;regex&gt;`` and ``&lt;exit_code&gt;``, to define regular
    expressions and exit code processing, respectively. They are defined below. If a
    tool does not have any valid ``&lt;regex&gt;`` or ``&lt;exit_code&gt;`` tags, then Galaxy
    will use the previous technique for finding errors.
    A note should be made on the order in which exit codes and regular expressions
    are applied and how the processing stops. Exit code rules are applied before
    regular expression rules. The rationale is that exit codes are more clearly
    defined and are easier to check computationally, so they are applied first. Exit
    code rules are applied in the order in which they appear in the tool's
    configuration file, and regular expressions are also applied in the order in
    which they appear in the tool's configuration file. However, once a rule is
    triggered that causes a fatal error, no further rules are
    checked.
    """

    regex: List[Regex] = field(default_factory=list, metadata={"type": "Element"})
    exit_code: List[ExitCode] = field(default_factory=list, metadata={"type": "Element"})


@dataclass(kw_only=True)
class Xrefs(BaseSetting):
    """Container tag set for the ``&lt;xref&gt;`` tags.

    A tool can refer multiple reference IDs.
    ```xml
    &lt;!-- Example: this tool is dada2 --&gt;
    &lt;xrefs&gt;
    &lt;xref type="bio.tools"&gt;dada2&lt;/xref&gt;
    &lt;xref type="bioconductor"&gt;dada2&lt;/xref&gt;
    &lt;/xrefs&gt;
    &lt;!-- https://bio.tools/dada2 --&gt;
    ```
    """

    class Meta:
        name = "xrefs"

    xref: List[Xref] = field(default_factory=list, metadata={"type": "Element"})


@dataclass(kw_only=True)
class Action(BaseSetting):
    """This directive is contained within an output ``data``'s  ``actions``
    directive (either directly or beneath a parent ``conditional`` tag).

    This directive
    describes modifications to either the output's format or metadata (based on
    whether ``type`` is ``format`` or ``metadata``).
    See [actions](#tool-outputs-data-actions) documentation for examples
    of this directive.
    """

    option: List[ActionsOption] = field(default_factory=list, metadata={"type": "Element"})
    type_value: ActionType = field(
        metadata={
            "name": "type",
            "type": "Attribute",
            "required": True,
            "description": "Type of action (either ``format`` or\n``metadata`` currently).",
        }
    )
    name: Optional[str] = field(
        default=None,
        metadata={"type": "Attribute", "description": 'If ``type="metadata"``, the name of the\nmetadata element.'},
    )
    default: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": 'If ``type="format"``, the default format\nif none of the nested options apply.',
        },
    )


@dataclass(kw_only=True)
class AssertHasArchiveMember(BaseSetting):
    """This tag allows to check if ``path`` is contained in a compressed file. The
    path is a regular expression that is matched against the full paths of the
    objects in the compressed file (remember that "matching" means it is checked if
    a prefix of the full path of an archive member is described by the regular
    expression). Valid archive formats include ``.zip``, ``.tar``, and ``.tar.gz``.
    Note that.

    depending on the archive creation method:
    - full paths of the members may be prefixed with ``./``
    - directories may be treated as empty files
    ```xml
    &lt;has_archive_member path="./path/to/my-file.txt"/&gt;
    ```
    With ``n`` and ``delta`` (or ``min`` and ``max``) assertions on the number of
    archive members matching ``path`` can be expressed. The following could be used,
    e.g., to assert an archive containing n&amp;plusmn;1 elements out of which at least
    4 need to have a ``txt`` extension.
    ```xml
    &lt;has_archive_member path=".*" n="10" delta="1"/&gt;
    &lt;has_archive_member path=".*\\.txt" min="4"/&gt;
    ```
    In addition the tag can contain additional assertions as child elements about
    the first member in the archive matching the regular expression ``path``. For
    instance
    ```xml
    &lt;has_archive_member path=".*/my-file.txt"&gt;
    &lt;not_has_text text="EDK72998.1"/&gt;
    &lt;/has_archive_member&gt;
    ```
    If the ``all`` attribute is set to ``true`` then all archive members are subject
    to the assertions. Note that, archive members matching the ``path`` are sorted
    alphabetically.
    The ``negate`` attribute of the ``has_archive_member`` assertion only affects
    the asserts on the presence and number of matching archive members, but not any
    sub-assertions (which can offer the ``negate`` attribute on their own).  The
    check if the file is an archive at all, which is also done by the function, is
    not affected.
    $attribute_list::5
    """

    has_size: List[AssertHasSize] = field(default_factory=list, metadata={"type": "Element"})
    has_text: List[AssertHasText] = field(default_factory=list, metadata={"type": "Element"})
    not_has_text: List[AssertNotHasText] = field(default_factory=list, metadata={"type": "Element"})
    has_text_matching: List[AssertHasTextMatching] = field(default_factory=list, metadata={"type": "Element"})
    has_line: List[AssertHasLine] = field(default_factory=list, metadata={"type": "Element"})
    has_line_matching: List[AssertHasLineMatching] = field(default_factory=list, metadata={"type": "Element"})
    has_n_lines: List[AssertHasNlines] = field(default_factory=list, metadata={"type": "Element"})
    has_n_columns: List[AssertHasNcolumns] = field(default_factory=list, metadata={"type": "Element"})
    has_json_property_with_value: List[AssertHasJsonPropertyWithValue] = field(
        default_factory=list, metadata={"type": "Element"}
    )
    has_json_property_with_text: List[AssertHasJsonPropertyWithText] = field(
        default_factory=list, metadata={"type": "Element"}
    )
    is_valid_xml: List[AssertIsValidXml] = field(default_factory=list, metadata={"type": "Element"})
    xml_element: List[AssertXmlelement] = field(default_factory=list, metadata={"type": "Element"})
    has_element_with_path: List[AssertHasElementWithPath] = field(default_factory=list, metadata={"type": "Element"})
    has_n_elements_with_path: List[AssertHasNelementsWithPath] = field(
        default_factory=list, metadata={"type": "Element"}
    )
    element_text_matches: List[AssertElementTextMatches] = field(default_factory=list, metadata={"type": "Element"})
    element_text_is: List[AssertElementTextIs] = field(default_factory=list, metadata={"type": "Element"})
    attribute_matches: List[AssertAttributeMatches] = field(default_factory=list, metadata={"type": "Element"})
    attribute_is: List[AssertAttributeIs] = field(default_factory=list, metadata={"type": "Element"})
    element_text: List[AssertElementText] = field(default_factory=list, metadata={"type": "Element"})
    has_h5_keys: List[AssertHasH5Keys] = field(default_factory=list, metadata={"type": "Element"})
    has_h5_attribute: List[AssertHasH5Attribute] = field(default_factory=list, metadata={"type": "Element"})
    path: Optional[str] = field(
        default=None,
        metadata={"type": "Attribute", "description": "The regular expression specifying the archive member."},
    )
    all: Union[bool, PermissiveBooleanValue] = field(
        default=PermissiveBooleanValue.FALSE,
        metadata={
            "type": "Attribute",
            "description": "Check the sub-assertions for all paths matching the path. Default: false, i.e. only the first",
        },
    )
    n: Optional[Union[int, str]] = field(
        default=None,
        metadata={"type": "Attribute", "description": "Desired number, can be suffixed by ``(k|M|G|T|P|E)i?``"},
    )
    delta: Optional[Union[int, str]] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Allowed difference with respect to n (default: 0), can be suffixed by ``(k|M|G|T|P|E)i?``",
        },
    )
    min: Optional[Union[int, str]] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Minimum number (default: -infinity), can be suffixed by ``(k|M|G|T|P|E)i?``",
        },
    )
    max: Optional[Union[int, str]] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Maximum number (default: infinity), can be suffixed by ``(k|M|G|T|P|E)i?``",
        },
    )


@dataclass(kw_only=True)
class Param(InputType, BaseSetting):
    """Contained within the ``&lt;inputs&gt;`` tag set - each of these specifies a field that
    will be displayed on the tool form. Ultimately, the values of these form fields
    will be passed as the command line parameters to the tool's executable.
    ### Common Attributes
    The attributes valid for this tag vary wildly based on the ``type`` of the
    parameter being described. All the attributes for the ``param`` element are
    documented below for completeness, but here are the common ones for each
    type are as follows:
    $attribute_list:name,type,optional,label,help,argument,refresh_on_change:4
    ### Parameter Types
    #### ``text``
    When ``type="text"``, the parameter is free form text and appears as a text box
    in the tool form.
    ##### Examples
    Sometimes you need labels for data or graph axes, chart titles, etc. This can be
    done using a text field. The following will create a text box with the default
    value of "V1".
    ```xml
    &lt;param name="xlab" type="text" value="V1" label="Label for x axis" /&gt;
    ```
    Unlike other types of parameters, type="text" parameters are always optional, and tool
    author need to restrict the input with validator elements. By using a profile of at
    least 23.0 text parameters that set ``optional="false"`` or define a validator are
    indicated as required, but without validator the tool can be executed in any case.
    That is a mandatory text parameter should be implemented as:
    ```
    &lt;param name="mandatory" type="text" optional="false"&gt;
    &lt;validator type="empty_field"/&gt;
    &lt;/param&gt;
    ```
    The ``area`` boolean attribute can be used to change the ``text`` parameter to a
    two-dimensional text area instead of a single line text box.
    ```xml
    &lt;param name="foo" type="text" area="true" /&gt;
    ```
    Since release 17.01, ``text`` parameters can also supply a static list of preset
    defaults options. The user **may** be presented with the option to select one of
    these but will be allowed to supply an arbitrary text value.
    ```xml
    &lt;param name="foo" type="text" value="foo 1"&gt;
    &lt;option value="foo 1"&gt;Foo 1 Display&lt;/option&gt;
    &lt;option value="foo 2"&gt;Foo 2 Display&lt;/option&gt;
    &lt;/param&gt;
    ```
    See [param_text_option.xml](https://github.com/galaxyproject/galaxy/blob/dev/test/functional/tools/param_text_option.xml)
    for a demonstration of this.
    $attribute_list:value,size,area:5
    #### ``integer`` and ``float``
    These parameters represent whole number and real numbers, respectively.
    ##### Example
    ```xml
    &lt;param name="region_size" type="integer" value="1" label="Size of the flanking regions" /&gt;
    ```
    $attribute_list:value,min,max:5
    #### ``boolean``
    This represents a binary true or false value.
    $attribute_list:checked,truevalue,falsevalue:5
    #### ``data``
    A dataset from the current history. Multiple types might be used for the param form.
    ##### Examples
    The following will find all "coordinate interval files" contained within the
    current history and dynamically populate a select list with them. If they are
    selected, their destination and internal file name will be passed to the
    appropriate command line variable.
    ```xml
    &lt;param name="interval_file" type="data" format="interval" label="near intervals in"/&gt;
    ```
    The following demonstrates a ``param`` which may accept multiple files and
    multiple formats.
    ```xml
    &lt;param format="sam,bam" multiple="true" name="bamOrSamFile" type="data"
    label="Alignments in BAM or SAM format"
    help="The set of aligned reads." /&gt;
    ```
    Perhaps counter-intuitively, a ``multiple="true"`` data parameter requires at least one
    data input. If ``optional="true"`` is specified, this condition is relaxed and the user
    is allowed to select 0 datasets. Unfortunately, if 0 datasets are selected the resulting
    value for the parameter during Cheetah templating (such as in a ``command`` block) will
    effectively be a list with one ``None``-like entity in it.
    The following idiom can be used to iterate over such a list and build a hypothetical ``-B``
    parameter for each file - the ``if`` block is used to handle the case where a ``None``-like
    entity appears in the list because no files were selected:
    ```
    #for $input in $input1
    #if $input
    -B "$input"
    #end if
    #end for
    ```
    Some example tools using ``multiple="true"`` data parameters include:
    - [multi_data_param.xml](https://github.com/galaxyproject/galaxy/blob/dev/test/functional/tools/multi_data_param.xml)
    - [multi_data_optional.xml](https://github.com/galaxyproject/galaxy/blob/dev/test/functional/tools/multi_data_optional.xml)
    Additionally, a detailed discussion of handling multiple homogenous files can be found in the
    the [Planemo Documentation](https://planemo.readthedocs.io/en/latest/writing_advanced.html#consuming-collections)
    on this topic.
    $attribute_list:format,multiple,optional,min,max,load_contents:5
    #### ``group_tag``
    $attribute_list:multiple,date_ref:5
    #### ``select``
    The following will create a select list containing the options "Downstream" and
    "Upstream". Depending on the selection, a ``d`` or ``u`` value will be passed to
    the ``$upstream_or_down`` variable on the command line.
    ```xml
    &lt;param name="upstream_or_down" type="select" label="Get"&gt;
    &lt;option value="u"&gt;Upstream&lt;/option&gt;
    &lt;option value="d"&gt;Downstream&lt;/option&gt;
    &lt;/param&gt;
    ```
    The following will create a checkbox list allowing the user to select
    "Downstream", "Upstream", both, or neither. Depending on the selection, the
    value of ``$upstream_or_down`` will be ``d``, ``u``, ``u,d``, or "".
    ```xml
    &lt;param name="upstream_or_down" type="select" label="Get" multiple="true" display="checkboxes"&gt;
    &lt;option value="u"&gt;Upstream&lt;/option&gt;
    &lt;option value="d"&gt;Downstream&lt;/option&gt;
    &lt;/param&gt;
    ```
    $attribute_list:data_ref,dynamic_options,display,multiple:5
    #### ``data_column``
    This parameter type is used to select columns from a parameter.
    $attribute_list:force_select,numerical,use_header_name,multiple:5
    #### ``drill_down``
    Allows to select values from a hierarchy. The default (``hierarchy="exact"``) is
    that only exactly the selected options are used. With ``hierarchy="recurse"``
    all leaf nodes in the subtree are used.
    See [drill_down.xml](https://github.com/galaxyproject/galaxy/blob/dev/test/functional/tools/drill_down.xml)
    $attribute_list:hierarchy,multiple:5
    #### ``data_collection``
    The following will create a parameter that only accepts paired FASTQ files grouped into a collection.
    ##### Examples
    ```xml
    &lt;param name="inputs" type="data_collection" collection_type="paired" label="Input FASTQs" format="fastq"&gt;
    &lt;/param&gt;
    ```
    More detailed information on writing tools that consume collections can be found
    in the [planemo documentation](https://planemo.readthedocs.io/en/latest/writing_advanced.html#collections).
    $attribute_list:format,collection_type:5
    #### ``color``
    ##### Examples
    The following example will create a color selector parameter.
    ```xml
    &lt;param name="feature_color" type="color" label="Default feature color" value="#ff00ff"&gt;
    &lt;/param&gt;
    ```
    Given that the output includes a pound sign, it is often convenient to use a
    sanitizer to prevent Galaxy from escaping the result.
    ```xml
    &lt;param name="feature_color" type="color" label="Default feature color" value="#ff00ff"&gt;
    &lt;sanitizer&gt;
    &lt;valid initial="string.ascii_letters,string.digits"&gt;
    &lt;add value="#" /&gt;
    &lt;/valid&gt;
    &lt;/sanitizer&gt;
    &lt;/param&gt;
    ```
    $attribute_list:value,rgb:5
    #### ``directory_uri``
    This is used to tie into galaxy.files URI infrastructure. This should only be used by
    core Galaxy tools until the interface around files has stabilized.
    Currently ``directory_uri`` parameters provide user's the option of selecting a writable
    directory destination for unstructured outputs of tools (e.g. history exports).
    This covers examples of the most common parameter types, the remaining parameter
    types are more obsecure and less likely to be useful for most tool authors."""

    label: List[str] = field(
        default_factory=list, metadata={"type": "Element", "description": "Documentation for label"}
    )
    conversion: List[ParamConversion] = field(default_factory=list, metadata={"type": "Element"})
    option: List[ParamSelectOption] = field(default_factory=list, metadata={"type": "Element"})
    options: List[ParamOptions] = field(default_factory=list, metadata={"type": "Element"})
    validator: List[Validator] = field(default_factory=list, metadata={"type": "Element"})
    sanitizer: List[Sanitizer] = field(default_factory=list, metadata={"type": "Element"})
    default: List[ParamDefault] = field(default_factory=list, metadata={"type": "Element"})
    help: List[str] = field(default_factory=list, metadata={"type": "Element", "description": "Documentation for help"})
    type_value: ParamType = field(
        metadata={
            "name": "type",
            "type": "Attribute",
            "required": True,
            "description": "Describes the parameter type - each different type as different semantics and\nthe tool form widget is different. Currently valid parameter types are:\n``text``,  ``integer``,  ``float``,  ``boolean``,  ``genomebuild``,  ``select``,\n``color``,  ``data_column``,  ``hidden``,  ``hidden_data``,  ``baseurl``,\n``file``,  ``ftpfile``,  ``data``,  ``data_collection``,\n``drill_down``. The definition of supported parameter types as defined in the\n``parameter_types`` dictionary in\n[/lib/galaxy/tools/parameters/basic.py](https://github.com/galaxyproject/galaxy/blob/dev/lib/galaxy/tools/parameters/basic.py).",
        }
    )
    name: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": 'Name for this element. This ``name``\nis used as the Cheetah variable containing the user-supplied parameter name in\n``command`` and ``configfile`` elements. The name should not contain pipes or\nperiods (e.g. ``.``). Some "reserved" names are ``REDIRECT_URL``,\n``DATA_URL``, ``GALAXY_URL``.',
        },
    )
    area: Optional[Union[bool, PermissiveBooleanValue]] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Boolean indicating if this should be\nrendered as a one line text box (if ``false``, the default) or a multi-line text\narea (if ``true``). Used only when the ``type`` attribute value is ``text``.",
        },
    )
    argument: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": 'If the parameter reflects just one command line argument of a certain tool, this\ntag should be set to that particular argument. It is rendered in parenthesis\nafter the help section, and it will create the name attribute (if not given explicitly)\nfrom the argument attribute by stripping leading dashes and replacing all remaining\ndashes by underscores (e.g. if ``argument="--long-parameter"`` then\n``name="long_parameter"`` is implicit).',
        },
    )
    label_attribute: Optional[str] = field(
        default=None,
        metadata={
            "name": "label",
            "type": "Attribute",
            "description": 'The attribute value will be\ndisplayed on the tool page as the label of the form field\n(``label="Sort Query"``).',
        },
    )
    help_attribute: Optional[str] = field(
        default=None,
        metadata={
            "name": "help",
            "type": "Attribute",
            "description": "Short bit of text, rendered on the\ntool form just below the associated field to provide information about the\nfield.",
        },
    )
    load_contents: Optional[int] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Number of bytes that should be\nloaded into the `contents` attribute of the jobs dictionary provided to Expression\nTools. Used only when the ``type`` attribute value is ``data``.",
        },
    )
    value: Optional[str] = field(
        default=None, metadata={"type": "Attribute", "description": "The default value for this\nparameter."}
    )
    default_value: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "*Deprecated*. Specify default value for column parameters (use ``value`` instead).",
        },
    )
    optional: str = field(
        default="false",
        metadata={
            "type": "Attribute",
            "description": "If ``false``, parameter must have a\nvalue. Defaults to ``false`` except when the ``type`` attribute value is\n``select`` and ``multiple`` is ``true``.",
        },
    )
    rgb: str = field(
        default="false",
        metadata={
            "type": "Attribute",
            "description": "If ``false``, the returned value\nwill be in Hex color code. If ``true``, it will be a RGB value e.g. ``0,0,255``.\nUsed only when the ``type`` attribute value is ``color``.",
        },
    )
    min: Optional[float] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Minimum valid parameter value. Used\nonly when the ``type`` attribute value is ``data``, ``float``, or ``integer``.",
        },
    )
    max: Optional[float] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Maximum valid parameter value. Used\nonly when the ``type`` attribute value is ``data``, ``float``, or ``integer``.",
        },
    )
    format: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "The comma-separated list of accepted\ndata formats for this input. The list of supported data formats is contained in the\n[/config/datatypes_conf.xml.sample](https://github.com/galaxyproject/galaxy/blob/dev/config/datatypes_conf.xml.sample)\nfile (use the file extension). Used only when the ``type`` attribute value is\n``data`` or ``data_collection``.",
        },
    )
    collection_type: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Restrict the kind of collection that can be consumed by this parameter. Simple\ncollections are either ``list`` or ``paired``), nested collections are specified\nas colon separated list of simple collection types (the most common types are\n``list``, ``paired``, ``list:paired``, or ``list:list``). Multiple such\ncollection types can be specified here as a comma-separated list. Used only when\nthe ``type`` attribute value is ``data_collection``.",
        },
    )
    data_ref: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Used with select lists whose options are dynamically generated\nbased on certain metadata attributes of the dataset or collection upon which\nthis parameter depends (usually but not always the tool's input dataset).\nUsed only when the ``type`` attribute value is ``data_column``, ``group_tag``,\nor ``select``.",
        },
    )
    accept_default: Optional[Union[bool, PermissiveBooleanValue]] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Deprecated. Take the value given by ``default_value`` (or ``value``) and ``1``\nif no ``value`` is given. Applies to ``data_column`` and ``group_tag``\nparameters.",
        },
    )
    refresh_on_change: Optional[Union[bool, PermissiveBooleanValue]] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Force a reload of the tool panel\nwhen the value of this parameter changes to allow ``code`` file processing.\nSee deprecation-like notice for ``code`` blocks.",
        },
    )
    force_select: Optional[Union[bool, PermissiveBooleanValue]] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "*Deprecated*. This is the inverse of\n``optional``. Set to ``false`` to not force user to select an option in the\nlist. Used only when the ``type`` attribute value is ``data_column``.",
        },
    )
    use_header_names: Optional[Union[bool, PermissiveBooleanValue]] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "If ``true``, Galaxy assumes the\nfirst row of ``data_ref`` is a header and builds the select list with these\nvalues rather than the more generic ``c1`` ... ``cN`` (i.e. it will be\n``c1: head1`` ... ``cN: headN``). Note that the content of the Cheetah variable\nis still the column index. Used only when the ``type`` attribute value is\n``data_column``.",
        },
    )
    display: Optional[DisplayType] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": 'Render a select list as a set of\ncheckboxes (``checkboxes``; note this is incompatible with ``multiple="false"``\nand ``optional="false"``) or radio buttons (``radio``; note this is\nincompatible with ``multiple="true"`` and ``optional="true"``). Defaults to a\ndrop-down menu select list. Used only when the ``type`` attribute value is\n``select``.',
        },
    )
    multiple: Optional[Union[bool, PermissiveBooleanValue]] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": 'Allow multiple values to be\nselected. ``select`` parameters with ``multiple="true"`` are optional by\ndefault. Used only when the ``type`` attribute value is ``data``, ``group_tag``,\nor ``select``. Default is ``false``',
        },
    )
    numerical: Optional[Union[bool, PermissiveBooleanValue]] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "If ``true`` a data column will be\ntreated as numerical when filtering columns based on metadata. Used only when\nthe ``type`` attribute value is ``data_column``.",
        },
    )
    hierarchy: Optional[HierarchyType] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Determine if a drill down is\n``recursive`` or ``exact``. Used only when the ``type`` attribute value is\n``drill_down``.",
        },
    )
    checked: Union[bool, PermissiveBooleanValue] = field(
        default=PermissiveBooleanValue.FALSE,
        metadata={
            "type": "Attribute",
            "description": "Set to ``true`` if the ``boolean``\nparameter should be checked (or ``true``) by default. Used only when the\n``type`` attribute value is ``boolean``.",
        },
    )
    truevalue: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "The parameter value in the Cheetah\ntemplate if the parameter is ``true`` or checked by the user. Used only when the\n``type`` attribute value is ``boolean``.",
        },
    )
    falsevalue: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "The parameter value in the Cheetah\ntemplate if the parameter is ``false`` or not checked by the user. Used only\nwhen the ``type`` attribute value is ``boolean``.",
        },
    )
    size: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "*Deprecated*. Completely ignored\nsince release 16.10. Used only when the ``type`` attribute value is ``text``.",
        },
    )
    dynamic_options: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Deprecated/discouraged method to\nallow access to Python code to generate options for a select list. See\n``code``'s documentation for an example.",
        },
    )


@dataclass(kw_only=True)
class RequestParameterTranslation(BaseSetting):
    """See [/tools/data_source/ucsc_tablebrowser.xml](https://github.com/galaxyproject/galaxy/blob/dev/tools/data_source/ucsc_tablebrowser.xml) for an example of how to use this tag set. This tag set is used only in "data_source" tools (i.e. whose ``tool_type`` attribute is ``data_source``). This tag set contains a set of [request_param](#tool-request-param-translation-request-param) elements."""

    request_param: List[RequestParameter] = field(default_factory=list, metadata={"type": "Element"})


@dataclass(kw_only=True)
class ActionsConditionalWhen(BaseSetting):
    """
    See [actions](#tool-outputs-data-actions) documentation for examples of this
    directive.
    """

    action: List[Action] = field(default_factory=list, metadata={"type": "Element"})
    conditional: List["ActionsConditional"] = field(default_factory=list, metadata={"type": "Element"})
    value: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Value to match conditional input value\nagainst. This needs to be the python string representation of the parameter value,\ne.g. ``True`` or ``False`` if the referred parameter is a boolean.",
        },
    )
    datatype_isinstance: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Datatype to match against (if ``value`` is unspecified). This should be the short string describing the format (e.g. ``interval``).",
        },
    )


@dataclass(kw_only=True)
class Section(BaseSetting):
    """This tag is used to group parameters into sections of the interface.

    Sections
    are implemented to replace the commonly used tactic of hiding advanced options
    behind a conditional, with sections you can easily visually group a related set
    of options.
    ### Example
    The XML configuration is relatively trivial for sections:
    ```xml
    &lt;inputs&gt;
    &lt;section name="section_name" title="Section Title" &gt;
    &lt;param name="parameter_name" type="text" label="A parameter  label" /&gt;
    &lt;/section&gt;
    &lt;/inputs&gt;
    ```
    In your command template, you'll need to include the section name to access the
    variable:
    ```
    $section_name.parameter_name
    ```
    In output filters sections are represented as dictionary with the same name as the section:
    ```
    &lt;filter&gt;section_name['parameter_name']&lt;/filter&gt;
    ```
    In order to reference parameters in sections from tags in the `&lt;outputs&gt;` section, e.g. in the `format_source` attribute of `&lt;data&gt;` tags, the syntax is currently:
    ```
    &lt;data name="output" format_source="parameter_name" metadata_source="parameter_name"/&gt;
    ```
    Note that references to other parameters in the `&lt;inputs&gt;` section are only possible if the reference is in the same section or its parents (and is defined earlier), therefore only `parameter_name` is used.
    ```
    &lt;param name="foo" type="data" format="tabular"/&gt;
    &lt;param name="bar" type="data_column" data_ref="foo"/&gt;
    &lt;section&gt;
    &lt;param name="qux" type="data_column" data_ref="foo"/&gt;
    &lt;param name="foo" type="data" format="tabular"/&gt;
    &lt;param name="baz" type="data_column" data_ref="foo"/&gt;
    &lt;/section&gt;
    ```
    In the above example `bar` and `qux` will refer to the first foo outside of the section and `baz` to the `foo` inside the section. This illustrates why non-unique parameter names are strongly discouraged.
    The following will not work:
    ```
    &lt;section&gt;
    &lt;param name="foo" type="data" format="tabular"/&gt;
    &lt;/section&gt;
    &lt;param name="bar" type="data_column" data_ref="foo"/&gt;
    ```
    Further examples can be found in the [test case](https://github.com/galaxyproject/galaxy/blob/dev/test/functional/tools/section.xml) from [pull request #35](https://github.com/galaxyproject/galaxy/pull/35).
    """

    param: List[Param] = field(default_factory=list, metadata={"type": "Element"})
    repeat: List["Repeat"] = field(default_factory=list, metadata={"type": "Element"})
    conditional: List["Conditional"] = field(default_factory=list, metadata={"type": "Element"})
    section: List["Section"] = field(default_factory=list, metadata={"type": "Element"})
    upload_dataset: List[object] = field(
        default_factory=list,
        metadata={"type": "Element", "description": "Internal, intentionally undocumented feature."},
    )
    display: List[str] = field(
        default_factory=list, metadata={"type": "Element", "description": "Documentation for display"}
    )
    name: str = field(
        metadata={"type": "Attribute", "required": True, "description": "The internal key used for the section."}
    )
    title: str = field(
        metadata={"type": "Attribute", "required": True, "description": "Human readable label for the section."}
    )
    expanded: Union[bool, PermissiveBooleanValue] = field(
        default=PermissiveBooleanValue.FALSE,
        metadata={
            "type": "Attribute",
            "description": "Whether the section should be expanded by default or not. If not, the default set values are used.",
        },
    )
    help: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Short help description for section, rendered just below the section.",
        },
    )


@dataclass(kw_only=True)
class TestAssertions(BaseSetting):
    """This tag set defines a sequence of checks or assertions to run against the
    target output.

    This tag requires no attributes, but child tags should be used to
    define the assertions to make about the output. The functional test framework
    makes it easy to extend Galaxy with such tags, the following table summarizes
    many of the default assertion tags that come with Galaxy and examples of each
    can be found below.
    The implementation of these tags are simply Python functions defined in the
    [/lib/galaxy/tool_util/verify/asserts](https://github.com/galaxyproject/galaxy/tree/dev/lib/galaxy/tool_util/verify/asserts)
    module.
    """

    has_size: Union[List[AssertHasSize], AssertHasSize, None] = field(default=None, metadata={"type": "Element"})
    has_text: Union[List[AssertHasText], AssertHasText, None] = field(default=None, metadata={"type": "Element"})
    not_has_text: Union[List[AssertNotHasText], AssertNotHasText, None] = field(
        default=None, metadata={"type": "Element"}
    )
    has_text_matching: Union[List[AssertHasTextMatching], AssertHasTextMatching, None] = field(
        default=None, metadata={"type": "Element"}
    )
    has_line: Union[List[AssertHasLine], AssertHasLine, None] = field(default=None, metadata={"type": "Element"})
    has_line_matching: Union[List[AssertHasLineMatching], AssertHasLineMatching, None] = field(
        default=None, metadata={"type": "Element"}
    )
    has_n_lines: Union[List[AssertHasNlines], AssertHasNlines, None] = field(default=None, metadata={"type": "Element"})
    has_n_columns: Union[List[AssertHasNcolumns], AssertHasNcolumns, None] = field(
        default=None, metadata={"type": "Element"}
    )
    has_archive_member: List[AssertHasArchiveMember] = field(default_factory=list, metadata={"type": "Element"})
    is_valid_xml: Union[List[AssertIsValidXml], AssertIsValidXml, None] = field(
        default=None, metadata={"type": "Element"}
    )
    xml_element: Union[List[AssertXmlelement], AssertXmlelement, None] = field(
        default=None, metadata={"type": "Element"}
    )
    has_element_with_path: Union[List[AssertHasElementWithPath], AssertHasElementWithPath, None] = field(
        default=None, metadata={"type": "Element"}
    )
    has_n_elements_with_path: Union[List[AssertHasNelementsWithPath], AssertHasNelementsWithPath, None] = field(
        default=None, metadata={"type": "Element"}
    )
    element_text_matches: Union[List[AssertElementTextMatches], AssertElementTextMatches, None] = field(
        default=None, metadata={"type": "Element"}
    )
    element_text_is: Union[List[AssertElementTextIs], AssertElementTextIs, None] = field(
        default=None, metadata={"type": "Element"}
    )
    attribute_matches: Union[List[AssertAttributeMatches], AssertAttributeMatches, None] = field(
        default=None, metadata={"type": "Element"}
    )
    attribute_is: Union[List[AssertAttributeIs], AssertAttributeIs, None] = field(
        default=None, metadata={"type": "Element"}
    )
    element_text: Union[List[AssertElementText], AssertElementText, None] = field(
        default=None, metadata={"type": "Element"}
    )
    has_json_property_with_value: Union[
        List[AssertHasJsonPropertyWithValue], AssertHasJsonPropertyWithValue, None
    ] = field(default=None, metadata={"type": "Element"})
    has_json_property_with_text: Union[
        List[AssertHasJsonPropertyWithText], AssertHasJsonPropertyWithText, None
    ] = field(default=None, metadata={"type": "Element"})
    has_h5_keys: Union[List[AssertHasH5Keys], AssertHasH5Keys, None] = field(default=None, metadata={"type": "Element"})
    has_h5_attribute: Union[List[AssertHasH5Attribute], AssertHasH5Attribute, None] = field(
        default=None, metadata={"type": "Element"}
    )


@dataclass(kw_only=True)
class ActionsConditional(BaseSetting):
    """This directive is contained within an output ``data``'s  ``actions``
    directive.

    This directive describes the state of the inputs required to apply an ``action``
    (specified as children of the child ``when`` directives to this element) to an
    output.
    See [actions](#tool-outputs-data-actions) documentation for examples
    of this directive.
    """

    when: List[ActionsConditionalWhen] = field(default_factory=list, metadata={"type": "Element"})
    name: str = field(
        metadata={
            "type": "Attribute",
            "required": True,
            "description": "Name of the input parameter to base\nconditional logic on. The value of this parameter will be matched against nested\n``when`` directives.",
        }
    )


@dataclass(kw_only=True)
class ConditionalWhen(BaseSetting):
    """This directive describes one potential set of input for the tool at this
    depth.

    See documentation for the [conditional](#tool-inputs-conditional) block for more details and examples (XML and corresponding Cheetah conditionals).
    """

    param: List[Param] = field(default_factory=list, metadata={"type": "Element"})
    repeat: List["Repeat"] = field(default_factory=list, metadata={"type": "Element"})
    conditional: List["Conditional"] = field(default_factory=list, metadata={"type": "Element"})
    section: List[Section] = field(default_factory=list, metadata={"type": "Element"})
    upload_dataset: List[object] = field(
        default_factory=list,
        metadata={"type": "Element", "description": "Internal, intentionally undocumented feature."},
    )
    display: List[str] = field(
        default_factory=list, metadata={"type": "Element", "description": "Documentation for display"}
    )
    value: str = field(
        metadata={
            "type": "Attribute",
            "required": True,
            "description": "Value for the tool form test parameter\ncorresponding to this ``when`` block.",
        }
    )


@dataclass(kw_only=True)
class TestOutput(BaseSetting, ClassFileField):
    """This tag set defines the variable that names the output dataset for the
    functional test framework. The functional test framework will execute the tool
    using the parameters defined in the ``&lt;param&gt;`` tag sets and generate a
    temporary file, which will either be compared with the file named in the
    ``file`` attribute value or checked against assertions made by a child
    ``assert_contents`` tag to verify that the tool is functionally correct.
    Different methods can be chosen for the comparison with the local file
    specified.

    by ``file`` using the ``compare`` attribute:
    - ``diff``: uses diff to compare the history data set and the file provided by
    ``file``. Compressed files are decompressed before the compariopm if
    ``decompress`` is set to ``true``. BAM files are converted to SAM before the
    comparision and for pdf some special rules are implemented. The number of
    allowed differences can be set with ``lines_diff``.  If ``sort="true"`` history
    and local data is sorted before the comparison.
    - ``re_match``: each line of the history data set is compared to the regular
    expression specified in the corresponding line of the ``file``. The allowed
    number of non matching lines can be set with ``lines_diff`` and the history
    dataset is sorted if ``sort`` is set to ``true``.
    - ``re_match_multiline``: it is checked if the history data sets matches the
    multi line regular expression given in ``file``. The history dataset is sorted
    before the comparison if the ``sort`` atrribute is set to ``true``.
    - ``contains``: check if each line in ``file`` is contained in the history data set.
    The allowed number of lines that are not contained in the history dataset
    can be set with ``lines_diff``.
    - ``sim_size``: compares the size of the history dataset and the ``file`` subject to
    the values of the ``delta`` and ``delta_frac`` attributes. Note that a ``has_size``
    content assertion should be preferred, because this avoids storing the test file.
    """

    discovered_dataset: List["TestDiscoveredDataset"] = field(default_factory=list, metadata={"type": "Element"})
    assert_contents: Union[List[TestAssertions], TestAssertions, None] = field(
        default=None,
        metadata={
            "type": "Element",
            "description": '$assertions\n### Examples\nThe following demonstrates a wide variety of text-based and tabular\nassertion statements.\n```xml\n&lt;output name="out_file1"&gt;\n&lt;assert_contents&gt;\n&lt;has_text text="chr7" /&gt;\n&lt;not_has_text text="chr8" /&gt;\n&lt;has_text_matching expression="1274\\d+53" /&gt;\n&lt;has_line_matching expression=".*\\s+127489808\\s+127494553" /&gt;\n&lt;!-- &amp;#009; is XML escape code for tab --&gt;\n&lt;has_line line="chr7&amp;#009;127471195&amp;#009;127489808" /&gt;\n&lt;has_n_columns n="3" /&gt;\n&lt;/assert_contents&gt;\n&lt;/output&gt;\n```\nThe following demonstrates a wide variety of XML assertion statements.\n```xml\n&lt;output name="out_file1"&gt;\n&lt;assert_contents&gt;\n&lt;is_valid_xml /&gt;\n&lt;has_element_with_path path="BlastOutput_param/Parameters/Parameters_matrix" /&gt;\n&lt;has_n_elements_with_path n="9" path="BlastOutput_iterations/Iteration/Iteration_hits/Hit/Hit_num" /&gt;\n&lt;element_text_matches path="BlastOutput_version" expression="BLASTP\\s+2\\.2.*" /&gt;\n&lt;element_text_is path="BlastOutput_program" text="blastp" /&gt;\n&lt;element_text path="BlastOutput_iterations/Iteration/Iteration_hits/Hit/Hit_def"&gt;\n&lt;not_has_text text="EDK72998.1" /&gt;\n&lt;has_text_matching expression="ABK[\\d\\.]+" /&gt;\n&lt;/element_text&gt;\n&lt;/assert_contents&gt;\n&lt;/output&gt;\n```\nThe following demonstrates verifying XML content with XPath-like expressions.\n```xml\n&lt;output name="out_file1"&gt;\n&lt;assert_contents&gt;\n&lt;attribute_is path="outerElement/innerElement1" attribute="foo" text="bar" /&gt;\n&lt;attribute_matches path="outerElement/innerElement2" attribute="foo2" expression="bar\\d+" /&gt;\n&lt;/assert_contents&gt;\n&lt;/output&gt;\n```',
        },
    )
    extra_files: List["TestExtraFile"] = field(default_factory=list, metadata={"type": "Element"})
    metadata: List[TestOutputMetadata] = field(default_factory=list, metadata={"type": "Element"})
    name: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "This value is the same as the value of the ``name`` attribute of the ``&lt;data&gt;``\ntag set contained within the tool's ``&lt;outputs&gt;`` tag set.",
        },
    )
    file: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "If specified, this value is the name of the output file stored in the target\n``test-data`` directory which will be used to compare the results of executing\nthe tool via the functional test framework.",
        },
    )
    value_json: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "If specified, this value will be loaded as JSON and compared against the output\ngenerated as JSON. This can be useful for testing tool outputs that are not files.",
        },
    )
    ftype: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "If specified, this value will be checked against the corresponding output's\ndata type. If these do not match, the test will fail.",
        },
    )
    sort: Optional[Union[bool, PermissiveBooleanValue]] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Applies only if ``compare`` is ``diff``, ``re_match`` or ``re_match_multiline``. This flag causes the lines of the history data set to be sorted before the comparison. In case of ``diff`` and ``re_match`` also the local file is sorted. This could be\nuseful for non-deterministic output.",
        },
    )
    value: Optional[str] = field(default=None, metadata={"type": "Attribute", "description": "An alias for ``file``."})
    md5: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "If specified, the target output's MD5 hash should match the value specified\nhere. For large static files it may be inconvenient to upload the entiry file\nand this can be used instead.",
        },
    )
    checksum: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "If specified, the target output's checksum should match the value specified\nhere. This value should have the form ``hash_type$hash_value``\n(e.g. ``sha1$8156d7ca0f46ed7abac98f82e36cfaddb2aca041``). For large static files\nit may be inconvenient to upload the entiry file and this can be used instead.",
        },
    )
    compare: Optional[TestOutputCompareType] = field(default=None, metadata={"type": "Attribute"})
    lines_diff: Optional[int] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Applies only if ``compare`` is set to ``diff``, ``re_match``, and ``contains``. If ``compare`` is set to ``diff``, the number of lines of difference to allow (each line with a modification is a line added and a line removed so this counts as two lines).",
        },
    )
    decompress: Optional[Union[bool, PermissiveBooleanValue]] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "If this attribute is true then try to decompress files if needed. This applies to\ntest assertions expressed with ``assert_contents`` or ``compare`` set to anything\nbut ``sim_size``.\nThis flag is useful for testing compressed outputs that are non-deterministic\ndespite having deterministic decompressed contents. By default, only files compressed\nwith bz2, gzip and zip will be automatically decompressed.\nNote, for specifying assertions for compressed as well as decompressed output\nthe corresponding output tag can be specified multiple times.\nThis is available in Galaxy since release 17.05 and was introduced in [pull request #3550](https://github.com/galaxyproject/galaxy/pull/3550).",
        },
    )
    delta: int = field(
        default=10000,
        metadata={
            "type": "Attribute",
            "description": "If ``compare`` is set to ``sim_size``, this is the maximum allowed absolute size difference (in bytes) between the data set that is generated in the test and the file in ``test-data/`` that is referenced by the ``file`` attribute. Default value is 10000 bytes. Can be combined with ``delta_frac``.",
        },
    )
    delta_frac: Optional[float] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "If ``compare`` is set to ``sim_size``, this is the maximum allowed relative size difference between the data set that is generated in the test and the file in ``test-data/`` that is referenced by the ``file`` attribute. A value of 0.1 means that the file that is generated in the test can differ by at most 10% of the file in ``test-data``. The default is not to check for  relative size difference. Can be combined with ``delta``.",
        },
    )
    count: Optional[int] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Number or datasets for this output. Should be used for outputs with ``discover_datasets``",
        },
    )
    location: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": 'URL that points to a remote output file that will downloaded and used for output comparison.\nPlease use this option only when is not possible to include the files in the `test-data` folder, since\nthis is more error prone due to external factors like remote availability.\nYou can use it in two ways:\n- In combination with `file` it will look for the output file in the `test-data` folder, if it\'s not available on disk it will\ndownload the file pointed by `location` using the same name as in `file` (or `value`).\n- Specifiying the `location` without a `file` (or `value`), it will download the file and use it as an alias of `file`. The name of the file\nwill be infered from the last component of the location URL. For example, `location="https://my_url/my_file.txt"` will be equivalent to `file="my_file.txt"`.\nIf you specify a `checksum`, it will be also used to check the integrity of the download.',
        },
    )


@dataclass(kw_only=True)
class Actions(BaseSetting):
    """The ``actions`` directive allows tools to dynamically take actions related to an
    ``output`` either unconditionally or conditionally based on inputs. These
    actions currently include setting metadata values and the output's data format.
    The examples below will demonstrate that the ``actions`` tag contains child
    ``conditional`` tags. The these conditionals are met, additional ``action``
    directives below the conditional are apply to the ``data`` output.
    ### Metadata
    The ``&lt;actions&gt;`` in the Bowtie 2 wrapper is used in lieu of the deprecated
    ``&lt;code&gt;`` tag to set the ``dbkey`` of the output dataset. In
    [bowtie2_wrapper.xml](https://github.com/galaxyproject/tools-devteam/blob/main/tools/bowtie2/bowtie2_wrapper.xml)
    (see below), according to the first action block, if the
    ``reference_genome.source`` is ``indexed`` (not ``history``), then it will assign
    the ``dbkey`` of the output file to be the same as that of the reference file. It
    does this by looking at through the data table and finding the entry that has the
    value that's been selected in the index dropdown box as column 1 of the loc file
    entry and using the dbkey, in column 0 (ignoring comment lines (starting with #)
    along the way).
    If ``reference_genome.source`` is ``history``, it pulls the ``dbkey`` from the
    supplied file.
    ```xml
    &lt;data format="bam" name="output" label="${tool.name} on ${on_string}: aligned reads (sorted BAM)"&gt;
    &lt;filter&gt;analysis_type['analysis_type_selector'] == "simple" or analysis_type['sam_opt'] is False&lt;/filter&gt;
    &lt;actions&gt;
    &lt;conditional name="reference_genome.source"&gt;
    &lt;when value="indexed"&gt;
    &lt;action type="metadata" name="dbkey"&gt;
    &lt;option type="from_data_table" name="bowtie2_indexes" column="1" offset="0"&gt;
    &lt;filter type="param_value" column="0" value="#" compare="startswith" keep="false"/&gt;
    &lt;filter type="param_value" ref="reference_genome.index" column="0"/&gt;
    &lt;/option&gt;
    &lt;/action&gt;
    &lt;/when&gt;
    &lt;when value="history"&gt;
    &lt;action type="metadata" name="dbkey"&gt;
    &lt;option type="from_param" name="reference_genome.own_file" param_attribute="dbkey" /&gt;
    &lt;/action&gt;
    &lt;/when&gt;
    &lt;/conditional&gt;
    &lt;/actions&gt;
    &lt;/data&gt;
    ```
    ### Format
    The Bowtie 2 example also demonstrates conditionally setting an output format
    based on inputs, as shown below:
    ```xml
    &lt;data format="fastqsanger" name="output_unaligned_reads_r" label="${tool.name} on ${on_string}: unaligned reads (R)"&gt;
    &lt;filter&gt;(library['type'] == "paired" or library['type'] == "paired_collection") and library['unaligned_file'] is True&lt;/filter&gt;
    &lt;actions&gt;
    &lt;conditional name="library.type"&gt;
    &lt;when value="paired"&gt;
    &lt;action type="format"&gt;
    &lt;option type="from_param" name="library.input_2" param_attribute="ext" /&gt;
    &lt;/action&gt;
    &lt;/when&gt;
    &lt;when value="paired_collection"&gt;
    &lt;action type="format"&gt;
    &lt;option type="from_param" name="library.input_1" param_attribute="reverse.ext" /&gt;
    &lt;/action&gt;
    &lt;/when&gt;
    &lt;/conditional&gt;
    &lt;/actions&gt;
    &lt;/data&gt;
    ```
    Note that the value given in ``when`` tags needs to be the python string representation
    of the value of the referred parameter, e.g. ``True`` or ``False`` if the referred
    parameter is a boolean.
    ### Unconditional Actions and Column Names
    For a static file that contains a fixed number of columns, it is straight forward:
    ```xml
    &lt;outputs&gt;
    &lt;data format="tabular" name="table"&gt;
    &lt;actions&gt;
    &lt;action name="column_names" type="metadata" default="Firstname,Lastname,Age" /&gt;
    &lt;/actions&gt;
    &lt;/data&gt;
    &lt;/outputs&gt;
    ```
    It may also be necessary to use column names based on a variable from another
    input file. This is implemented in the
    [htseq-count](https://github.com/galaxyproject/tools-iuc/blob/main/tools/htseq_count/htseq-count.xml)
    and
    [featureCounts](https://github.com/galaxyproject/tools-iuc/blob/main/tools/featurecounts/featurecounts.xml)
    wrappers:
    ```xml
    &lt;inputs&gt;
    &lt;data name="input_file" type="data" multiple="false"&gt;
    &lt;/inputs&gt;
    &lt;outputs&gt;
    &lt;data format="tabular" name="output_short"&gt;
    &lt;actions&gt;
    &lt;action name="column_names" type="metadata" default="Geneid,${input_file.name}" /&gt;
    &lt;/actions&gt;
    &lt;/data&gt;
    &lt;/outputs&gt;
    ```
    Or in case of multiple files:
    ```xml
    &lt;inputs&gt;
    &lt;data name="input_files" type="data" multiple="true"&gt;
    &lt;/inputs&gt;
    &lt;outputs&gt;
    &lt;data format="tabular" name="output_short"&gt;
    &lt;actions&gt;
    &lt;action name="column_names" type="metadata" default="Geneid,${','.join([a.name for a in $input_files])}" /&gt;
    &lt;/actions&gt;
    &lt;/data&gt;
    &lt;/outputs&gt;
    ```
    ### Unconditional Actions - An Older Example
    The first approach above to setting ``dbkey`` based on tool data tables is
    prefered, but an older example using so called "loc files" directly is found
    below.
    In addition to demonstrating this lower-level direct access of .loc files, it
    demonstrates an unconditional action. The second block would not be needed for
    most cases - it was required in this tool to handle the specific case of a small
    reference file used for functional testing. It says that if the dbkey has been
    set to ``equCab2chrM`` (which is what the ``&lt;filter type="metadata_value"...
    column="1" /&gt;`` tag does), then it should be changed to ``equCab2`` (which is the
    ``&lt;option type="from_param" ... column="0" ...&gt;`` tag does).
    ```xml
    &lt;actions&gt;
    &lt;conditional name="refGenomeSource.genomeSource"&gt;
    &lt;when value="indexed"&gt;
    &lt;action type="metadata" name="dbkey"&gt;
    &lt;option type="from_file" name="bowtie_indices.loc" column="0" offset="0"&gt;
    &lt;filter type="param_value" column="0" value="#" compare="startswith" keep="false"/&gt;
    &lt;filter type="param_value" ref="refGenomeSource.index" column="1"/&gt;
    &lt;/option&gt;
    &lt;/action&gt;
    &lt;/when&gt;
    &lt;/conditional&gt;
    &lt;!-- Special casing equCab2chrM to equCab2 --&gt;
    &lt;action type="metadata" name="dbkey"&gt;
    &lt;option type="from_param" name="refGenomeSource.genomeSource" column="0" offset="0"&gt;
    &lt;filter type="insert_column" column="0" value="equCab2chrM"/&gt;
    &lt;filter type="insert_column" column="0" value="equCab2"/&gt;
    &lt;filter type="metadata_value" ref="output" name="dbkey" column="1" /&gt;
    &lt;/option&gt;
    &lt;/action&gt;
    &lt;/actions&gt;
    ```"""

    action: List[Action] = field(default_factory=list, metadata={"type": "Element"})
    conditional: List[ActionsConditional] = field(default_factory=list, metadata={"type": "Element"})


@dataclass(kw_only=True)
class Conditional(InputType, BaseSetting):
    """This is a container for conditional parameters in the tool (must contain 'when'
    tag sets) - the command line (or portions thereof) are then wrapped in an if-else
    statement. A good example tool that demonstrates many conditional parameters is
    [biom_convert.xml](https://github.com/galaxyproject/tools-iuc/blob/main/tools/biom_format/biom_convert.xml).
    ```xml
    &lt;conditional name="input_type"&gt;
    &lt;param name="input_type_selector" type="select" label="Choose the source BIOM format"&gt;
    &lt;option value="tsv" selected="true"&gt;Tabular File&lt;/option&gt;
    &lt;option value="biom"&gt;BIOM File&lt;/option&gt;
    &lt;/param&gt;
    &lt;when value="tsv"&gt;
    &lt;param name="input_table" type="data" format="tabular" label="Tabular File" argument="--input-fp"/&gt;
    &lt;param argument="--process-obs-metadata" type="select" label="Process metadata associated with observations when converting"&gt;
    &lt;option value="" selected="true"&gt;Do Not process metadata&lt;/option&gt;
    &lt;option value="taxonomy"&gt;taxonomy&lt;/option&gt;
    &lt;option value="naive"&gt;naive&lt;/option&gt;
    &lt;option value="sc_separated"&gt;sc_separated&lt;/option&gt;
    &lt;/param&gt;
    &lt;/when&gt;
    &lt;when value="biom"&gt;
    &lt;param name="input_table" type="data" format="biom1" label="Tabular File" argument="--input-fp"/&gt;
    &lt;/when&gt;
    &lt;/conditional&gt;
    ```
    The first directive following the conditional is a [param](#tool-inputs-param),
    this param must be of type ``select`` or ``boolean``. Depending on the value a
    user selects for this "test" parameter - different UI elements will be shown.
    These different paths are described by the following the ``when`` blocks shown
    above.
    The following Cheetah block demonstrates the use of the ``conditional``
    shown above:
    ```
    biom convert -i "${input_type.input_table}" -o "${output_table}"
    #if str($input_type.input_type_selector) == "tsv":
    #if $input_type.process_obs_metadata:
    --process-obs-metadata "${input_type.process_obs_metadata}"
    #end if
    #end if
    ```
    Notice that the parameter ``input_table`` appears down both ``when`` clauses
    so ``${input_type.input_table}`` appears unconditionally but we need to
    conditionally reference ``${input_type.process_obs_metadata}`` with a Cheetah
    ``if`` statement.
    A common use of the conditional wrapper is to select between reference data
    managed by the Galaxy admins (for instance via
    [data managers](https://galaxyproject.org/admin/tools/data-managers/)
    ) and
    history files. A good example tool that demonstrates this is
    the [Bowtie 2](https://github.com/galaxyproject/tools-iuc/blob/main/tools/bowtie2/bowtie2_wrapper.xml) wrapper.
    ```xml
    &lt;conditional name="reference_genome"&gt;
    &lt;param name="source" type="select" label="Will you select a reference genome from your history or use a built-in index?" help="Built-ins were indexed using default options. See `Indexes` section of help below"&gt;
    &lt;option value="indexed"&gt;Use a built-in genome index&lt;/option&gt;
    &lt;option value="history"&gt;Use a genome from the history and build index&lt;/option&gt;
    &lt;/param&gt;
    &lt;when value="indexed"&gt;
    &lt;param name="index" type="select" label="Select reference genome" help="If your genome of interest is not listed, contact the Galaxy team"&gt;
    &lt;options from_data_table="bowtie2_indexes"&gt;
    &lt;filter type="sort_by" column="2"/&gt;
    &lt;/options&gt;
    &lt;validator type="no_options" message="No indexes are available for the selected input dataset"/&gt;
    &lt;/param&gt;
    &lt;/when&gt;
    &lt;when value="history"&gt;
    &lt;param name="own_file" type="data" format="fasta" label="Select reference genome" /&gt;
    &lt;/when&gt;
    &lt;/conditional&gt;
    ```
    The Bowtie 2 wrapper also demonstrates other conditional paths - such as choosing
    between paired inputs of single stranded inputs."""

    param: Optional[Param] = field(default=None, metadata={"type": "Element"})
    repeat: Optional["Repeat"] = field(default=None, metadata={"type": "Element"})
    conditional: Optional["Conditional"] = field(default=None, metadata={"type": "Element"})
    section: Optional[Section] = field(default=None, metadata={"type": "Element"})
    upload_dataset: Optional[object] = field(
        default=None, metadata={"type": "Element", "description": "Internal, intentionally undocumented feature."}
    )
    display: Optional[str] = field(
        default=None, metadata={"type": "Element", "description": "Documentation for display"}
    )
    when: List[ConditionalWhen] = field(default_factory=list, metadata={"type": "Element"})
    name: Optional[str] = field(default=None, metadata={"type": "Attribute", "description": "Name for this element"})
    value_from: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Infrequently used option to dynamically access Galaxy internals, this should be avoided.\nGalaxy method to execute.",
        },
    )
    value_ref: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Infrequently used option to dynamically access Galaxy internals, this should be avoided.\nReferenced parameter to pass method.",
        },
    )
    value_ref_in_group: Optional[Union[bool, PermissiveBooleanValue]] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Infrequently used option to dynamically access Galaxy internals, this should be avoided.\nIs referenced parameter is the same group.",
        },
    )
    label: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Human readable description for the conditional, unused in the Galaxy UI currently.",
        },
    )


@dataclass(kw_only=True)
class TestDiscoveredDataset(TestOutput, BaseSetting):
    """This directive specifies a test for an output's discovered dataset.

    It acts as an
    ``output`` test tag in many ways and can define any tests of that tag (e.g.
    ``assert_contents``, ``value``, ``compare``, ``md5``, ``checksum``, ``metadata``, etc...).
    ### Example
    The functional test tool
    [multi_output_assign_primary.xml](https://github.com/galaxyproject/galaxy/blob/dev/test/functional/tools/multi_output_assign_primary.xml)
    provides a demonstration of using this tag.
    ```xml
    &lt;outputs&gt;
    &lt;data format="tabular" name="sample"&gt;
    &lt;discover_datasets pattern="(?P&amp;lt;designation&amp;gt;.+)\\.report\\.tsv" ext="tabular" visible="true" assign_primary_output="true" /&gt;
    &lt;/data&gt;
    &lt;/outputs&gt;
    &lt;test&gt;
    &lt;param name="num_param" value="7" /&gt;
    &lt;param name="input" ftype="txt" value="simple_line.txt"/&gt;
    &lt;output name="sample"&gt;
    &lt;assert_contents&gt;
    &lt;has_line line="1" /&gt;
    &lt;/assert_contents&gt;
    &lt;!-- no sample1 it was consumed by named output "sample" --&gt;
    &lt;discovered_dataset designation="sample2" ftype="tabular"&gt;
    &lt;assert_contents&gt;&lt;has_line line="2" /&gt;&lt;/assert_contents&gt;
    &lt;/discovered_dataset&gt;
    &lt;discovered_dataset designation="sample3" ftype="tabular"&gt;
    &lt;assert_contents&gt;&lt;has_line line="3" /&gt;&lt;/assert_contents&gt;
    &lt;/discovered_dataset&gt;
    &lt;/output&gt;
    &lt;/test&gt;
    ```
    Note that this tool uses ``assign_primary_output="true"`` for ``&lt;discover_datasets&gt;``. Hence, the content of the first discovered dataset (which is the first in the alphabetically sorted list of discovered designations) is checked directly in the ``&lt;output&gt;`` tag of the test.
    """

    designation: Optional[str] = field(
        default=None, metadata={"type": "Attribute", "description": "The designation of the discovered dataset."}
    )


@dataclass(kw_only=True)
class TestExtraFile(TestOutput, BaseSetting):
    """
    Define test for extra files on corresponding output.
    """

    type_value: Optional[str] = field(
        default=None,
        metadata={
            "name": "type",
            "type": "Attribute",
            "description": "Extra file type (either ``file`` or ``directory``).",
        },
    )


@dataclass(kw_only=True)
class TestOutputCollection(BaseSetting, ClassCollectionField):
    """Define tests for extra datasets and metadata corresponding to an output
    collection.

    ``output_collection`` directives should specify a ``name`` and ``type``
    attribute to describe the expected output collection as a whole.
    Expectations about collection contents are described using child ``element``
    directives. For nested collections, these child ``element`` directives may
    themselves contain children.
    For tools marked as having profile 20.09 or newer, the order of elements within
    an ``output_collection`` declaration are meaningful. The test definition may
    omit any number of elements from a collection, but the ones that are specified
    will be checked against the actual resulting collection from the tool run and the
    order within the collection verified.
    ### Examples
    The [genetrack](https://github.com/galaxyproject/tools-iuc/blob/main/tools/genetrack/genetrack.xml)
    tool demonstrates basic usage of an ``output_collection`` test expectation.
    ```xml
    &lt;test&gt;
    &lt;param name="input" value="genetrack_input2.gff" ftype="gff" /&gt;
    &lt;param name="input_format" value="gff" /&gt;
    &lt;param name="sigma" value="5" /&gt;
    &lt;param name="exclusion" value="20" /&gt;
    &lt;param name="up_width" value="10" /&gt;
    &lt;param name="down_width" value="10" /&gt;
    &lt;param name="filter" value="3" /&gt;
    &lt;output_collection name="genetrack_output" type="list"&gt;
    &lt;element name="s5e20u10d10F3_on_data_1" file="genetrack_output2.gff" ftype="gff" /&gt;
    &lt;/output_collection&gt;
    &lt;/test&gt;
    ```
    The [CWPair2](https://github.com/galaxyproject/tools-iuc/blob/main/tools/cwpair2/cwpair2.xml)
    tool demonstrates that ``element``s can specify a ``compare`` attribute just
    like [output](#tool-tests-test-output).
    ```xml
    &lt;test&gt;
    &lt;param name="input" value="cwpair2_input1.gff" /&gt;
    &lt;param name="up_distance" value="25" /&gt;
    &lt;param name="down_distance" value="100" /&gt;
    &lt;param name="method" value="all" /&gt;
    &lt;param name="binsize" value="1" /&gt;
    &lt;param name="threshold_format" value="relative_threshold" /&gt;
    &lt;param name="relative_threshold" value="0.0" /&gt;
    &lt;param name="output_files" value="matched_pair" /&gt;
    &lt;output name="statistics_output" file="statistics1.tabular" ftype="tabular" /&gt;
    &lt;output_collection name="MP" type="list"&gt;
    &lt;element name="data_MP_closest_f0u25d100_on_data_1.gff" file="closest_mp_output1.gff" ftype="gff" compare="contains"/&gt;
    &lt;element name="data_MP_largest_f0u25d100_on_data_1.gff" file="largest_mp_output1.gff" ftype="gff" compare="contains"/&gt;
    &lt;element name="data_MP_mode_f0u25d100_on_data_1.gff" file="mode_mp_output1.gff" ftype="gff" compare="contains"/&gt;
    &lt;/output_collection&gt;
    &lt;/test&gt;
    ```
    The
    [collection_creates_dynamic_nested](https://github.com/galaxyproject/galaxy/blob/dev/test/functional/tools/collection_creates_dynamic_nested.xml)
    test tool demonstrates the use of nested ``element`` directives as described
    above. Notice also that it tests the output with ``assert_contents`` instead of
    supplying a ``file`` attribute. Like hinted at with with ``compare`` attribute
    above, the ``element`` tag can specify any of the test attributes that apply to
    the [output](#tool-tests-test-output) (e.g. ``md5``, ``compare``, ``diff``,
    etc...).
    ```xml
    &lt;test&gt;
    &lt;param name="foo" value="bar" /&gt;
    &lt;output_collection name="list_output" type="list:list"&gt;
    &lt;element name="oe1"&gt;
    &lt;element name="ie1"&gt;
    &lt;assert_contents&gt;
    &lt;has_text_matching expression="^A\\n$" /&gt;
    &lt;/assert_contents&gt;
    &lt;/element&gt;
    &lt;element name="ie2"&gt;
    &lt;assert_contents&gt;
    &lt;has_text_matching expression="^B\\n$" /&gt;
    &lt;/assert_contents&gt;
    &lt;/element&gt;
    &lt;/element&gt;
    &lt;element name="oe2"&gt;
    &lt;element name="ie1"&gt;
    &lt;assert_contents&gt;
    &lt;has_text_matching expression="^C\\n$" /&gt;
    &lt;/assert_contents&gt;
    &lt;/element&gt;
    &lt;element name="ie2"&gt;
    &lt;assert_contents&gt;
    &lt;has_text_matching expression="^D\\n$" /&gt;
    &lt;/assert_contents&gt;
    &lt;/element&gt;
    &lt;/element&gt;
    &lt;element name="oe3"&gt;
    &lt;element name="ie1"&gt;
    &lt;assert_contents&gt;
    &lt;has_text_matching expression="^E\\n$" /&gt;
    &lt;/assert_contents&gt;
    &lt;/element&gt;
    &lt;element name="ie2"&gt;
    &lt;assert_contents&gt;
    &lt;has_text_matching expression="^F\\n$" /&gt;
    &lt;/assert_contents&gt;
    &lt;/element&gt;
    &lt;/element&gt;
    &lt;/output_collection&gt;
    &lt;/test&gt;
    ```
    """

    element: Union[List[TestOutput], TestOutput, None] = field(default=None, metadata={"type": "Element"})
    count: Optional[int] = field(
        default=None, metadata={"type": "Attribute", "description": "Number of elements in output collection."}
    )


@dataclass(kw_only=True)
class OutputData(BaseSetting):
    """This tag set is contained within the ``&lt;outputs&gt;`` tag set, and it defines the
    output data description for the files resulting from the tool's execution. The
    value of the attribute ``label`` can be acquired from input parameters or metadata
    in the same way that the command line parameters are (discussed in the
    ``&lt;command&gt;`` tag set section above).
    ### Examples
    The following will create a variable called ``$out_file1`` with data type
    ``pdf``.
    ```xml
    &lt;outputs&gt;
    &lt;data format="pdf" name="out_file1" /&gt;
    &lt;/outputs&gt;
    ```
    The valid values for format can be found in
    [/config/datatypes_conf.xml.sample](https://github.com/galaxyproject/galaxy/blob/dev/config/datatypes_conf.xml.sample).
    The following will create a dataset in the history panel whose data type is the
    same as that of the input dataset selected (and named ``input1``) for the tool.
    ```xml
    &lt;outputs&gt;
    &lt;data format_source="input1" name="out_file1" metadata_source="input1"/&gt;
    &lt;/outputs&gt;
    ```
    The following will create datasets in the history panel, setting the output data
    type to be the same as that of an input dataset named by the ``format_source``
    attribute. Note that a conditional name is not included, so 2 separate
    conditional blocks should not contain parameters with the same name.
    ```xml
    &lt;inputs&gt;
    &lt;!-- fasta may be an aligned fasta that subclasses Fasta --&gt;
    &lt;param name="fasta" type="data" format="fasta" label="fasta - Sequences"/&gt;
    &lt;conditional name="qual"&gt;
    &lt;param name="add" type="select" label="Trim based on a quality file?" help=""&gt;
    &lt;option value="no"&gt;no&lt;/option&gt;
    &lt;option value="yes"&gt;yes&lt;/option&gt;
    &lt;/param&gt;
    &lt;when value="no"/&gt;
    &lt;when value="yes"&gt;
    &lt;!-- qual454, qualsolid, qualillumina --&gt;
    &lt;param name="qfile" type="data" format="qual" label="qfile - a quality file"/&gt;
    &lt;/when&gt;
    &lt;/conditional&gt;
    &lt;/inputs&gt;
    &lt;outputs&gt;
    &lt;data format_source="fasta" name="trim_fasta"
    label="${tool.name} on ${on_string}: trim.fasta"/&gt;
    &lt;data format_source="qfile" name="trim_qual"
    label="${tool.name} on ${on_string}: trim.qual"&gt;
    &lt;filter&gt;qual['add'] == 'yes'&lt;/filter&gt;
    &lt;/data&gt;
    &lt;/outputs&gt;
    ```
    Assume that the tool includes an input parameter named ``database`` which is a
    select list (as shown below). Also assume that the user selects the first option
    in the ``$database`` select list. Then the following will ensure that the tool
    produces a tabular data set whose associated history item has the label ``Blat
    on Human (hg18)``.
    ```xml
    &lt;inputs&gt;
    &lt;param format="tabular" name="input" type="data" label="Input stuff"/&gt;
    &lt;param type="select" name="database" label="Database"&gt;
    &lt;option value="hg18"&gt;Human (hg18)&lt;/option&gt;
    &lt;option value="dm3"&gt;Fly (dm3)&lt;/option&gt;
    &lt;/param&gt;
    &lt;/inputs&gt;
    &lt;outputs&gt;
    &lt;data format="input" name="output" label="Blat on ${database.value_label}" /&gt;
    &lt;/outputs&gt;
    ```"""

    change_format: List[ChangeFormat] = field(default_factory=list, metadata={"type": "Element"})
    filter: List[str] = field(default_factory=list, metadata={"type": "Element"})
    discover_datasets: List[OutputDiscoverDatasets] = field(default_factory=list, metadata={"type": "Element"})
    actions: List[Actions] = field(default_factory=list, metadata={"type": "Element"})
    format: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": 'The short name for the output datatype.\nThe valid values for format can be found in\n[/config/datatypes_conf.xml.sample](https://github.com/galaxyproject/galaxy/blob/dev/config/datatypes_conf.xml.sample)\n(e.g. ``format="pdf"`` or ``format="fastqsanger"``). For collections this is the default format for all included\nelements. Note that the format specified here is ignored for discovered data sets.',
        },
    )
    format_source: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "This sets the data type of the output dataset(s) to be the same format as that of the specified tool input.",
        },
    )
    label: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "This will be the name of the history item for the output data set. The string\ncan include structure like ``${&lt;some param name&gt;.&lt;some attribute&gt;}``, as\ndiscussed for command line parameters in the ``&lt;command&gt;`` tag set section\nabove. The default label is ``${tool.name} on ${on_string}``.",
        },
    )
    name: str = field(
        metadata={
            "type": "Attribute",
            "required": True,
            "description": "Name for this output. This\n``name`` is used as the Cheetah variable containing the Galaxy assigned output\npath in ``command`` and ``configfile`` elements. The name should not contain\npipes or periods (e.g. ``.``).",
        }
    )
    auto_format: Optional[Union[bool, PermissiveBooleanValue]] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "If ``true``, this output will sniffed and its format determined automatically by Galaxy.",
        },
    )
    default_identifier_source: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": 'Sets the source of element identifier to the specified input.\nThis only applies to collections that are mapped over a non-collection input and that have equivalent structures. If this references input elements in conditionals, this value should be qualified (e.g. ``cond|input`` instead of ``input`` if ``input`` is in a conditional with ``name="cond"``).',
        },
    )
    metadata_source: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "This copies the metadata information\nfrom the tool's input dataset. This is particularly useful for interval data\ntypes where the order of the columns is not set.",
        },
    )
    from_work_dir: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Relative path to a file produced by the\ntool in its working directory. Output's contents are set to this file's\ncontents. The behaviour when this file does not exist in the working directory is undefined; the resulting dataset could be empty or the tool execution could fail.",
        },
    )
    hidden: bool = field(
        default=False,
        metadata={
            "type": "Attribute",
            "description": "Boolean indicating whether to hide\ndataset in the history view. (Default is ``false``.)",
        },
    )


@dataclass(kw_only=True)
class Repeat(InputType, BaseSetting):
    """See
    [xy_plot.xml](https://github.com/galaxyproject/tools-devteam/blob/main/tools/xy_plot/xy_plot.xml)
    for an example of how to use this tag set. This is a container for any tag sets
    that can be contained within the ``&lt;inputs&gt;`` tag set. When this is used, the
    tool will allow the user to add any number of additional sets of the contained
    parameters (an option to add new iterations will be displayed on the tool form).
    All input parameters contained within the ``&lt;repeat&gt;`` tag can be retrieved by
    enumerating over ``$&lt;name_of_repeat_tag_set&gt;`` in the relevant Cheetah code.
    This returns the rank and the parameter objects of the repeat container. See the
    Cheetah code below.
    ### Example
    This part is contained in the ``&lt;inputs&gt;`` tag set.
    ```xml
    &lt;repeat name="series" title="Series"&gt;
    &lt;param name="input" type="data" format="tabular" label="Dataset"/&gt;
    &lt;param name="xcol" type="data_column" data_ref="input" label="Column for x axis"/&gt;
    &lt;param name="ycol" type="data_column" data_ref="input" label="Column for y axis"/&gt;
    &lt;/repeat&gt;
    ```
    This Cheetah code can be used in the ``&lt;command&gt;`` tag set or the
    ``&lt;configfile&gt;`` tag set.
    ```
    #for $i, $s in enumerate($series)
    rank_of_series=$i
    input_path='${s.input}'
    x_colom=${s.xcol}
    y_colom=${s.ycol}
    #end for
    ```
    ### Testing
    This is an example test case with multiple repeat elements for the example above.
    ```xml
    &lt;test&gt;
    &lt;repeat name="series"&gt;
    &lt;param name="input" value="tabular1.tsv" ftype="tabular"/&gt;
    &lt;param name="xcol" value="1"/&gt;
    &lt;param name="ycol" value="2"/&gt;
    &lt;/repeat&gt;
    &lt;repeat name="series"&gt;
    &lt;param name="input" value="tabular2.tsv" ftype="tabular"/&gt;
    &lt;param name="xcol" value="4"/&gt;
    &lt;param name="ycol" value="2"/&gt;
    &lt;/repeat&gt;
    &lt;output name="out_file1" file="cool.pdf" ftype="pdf" /&gt;
    &lt;/test&gt;
    ```
    See the documentation on the [repeat test directive](#tool-tests-test-repeat).
    An older way to specify repeats in a test is by instances that are created by referring to names with a special format: ``&lt;repeat name&gt;_&lt;repeat index&gt;|&lt;param name&gt;``
    ```xml
    &lt;test&gt;
    &lt;param name="series_0|input" value="tabular1.tsv" ftype="tabular"/&gt;
    &lt;param name="series_0|xcol" value="1"/&gt;
    &lt;param name="series_0|ycol" value="2"/&gt;
    &lt;param name="series_1|input" value="tabular2.tsv" ftype="tabular"/&gt;
    &lt;param name="series_1|xcol" value="4"/&gt;
    &lt;param name="series_1|ycol" value="2"/&gt;
    &lt;output name="out_file1" file="cool.pdf" ftype="pdf" /&gt;
    &lt;/test&gt;
    ```
    The test tool [disambiguate_repeats.xml](https://github.com/galaxyproject/galaxy/blob/dev/test/functional/tools/disambiguate_repeats.xml)
    demonstrates both testing strategies."""

    param: List[Param] = field(default_factory=list, metadata={"type": "Element"})
    repeat: List["Repeat"] = field(default_factory=list, metadata={"type": "Element"})
    conditional: List[Conditional] = field(default_factory=list, metadata={"type": "Element"})
    section: List[Section] = field(default_factory=list, metadata={"type": "Element"})
    upload_dataset: List[object] = field(
        default_factory=list,
        metadata={"type": "Element", "description": "Internal, intentionally undocumented feature."},
    )
    display: List[str] = field(
        default_factory=list, metadata={"type": "Element", "description": "Documentation for display"}
    )
    name: str = field(metadata={"type": "Attribute", "required": True, "description": "Name for this element"})
    title: str = field(
        metadata={
            "type": "Attribute",
            "required": True,
            "description": "The title of the repeat section, which will be displayed on the tool form.",
        }
    )
    min: Optional[int] = field(
        default=None, metadata={"type": "Attribute", "description": "The minimum number of repeat units."}
    )
    max: Optional[int] = field(
        default=None, metadata={"type": "Attribute", "description": "The maximum number of repeat units."}
    )
    default: int = field(
        default=1, metadata={"type": "Attribute", "description": "The default number of repeat units."}
    )
    help: Optional[str] = field(
        default=None, metadata={"type": "Attribute", "description": "Short help description for repeat element."}
    )


@dataclass(kw_only=True)
class TestSection(BaseSetting):
    """Specify test parameters below a named of a ``section`` block matching one in
    ``inputs`` with this element.

    ``param`` elements in a ``test`` block can be arranged into nested ``repeat``,
    ``conditional``, and ``select`` structures to match the inputs. While this might
    be overkill for simple tests, it helps prevent ambiguous definitions and keeps
    things organized in large test cases. A future ``profile`` version of Galaxy
    tools may require ``section`` blocks be explicitly defined with this
    directive.
    ### Examples
    The test tool demonstrating sections
    ([section.xml](https://github.com/galaxyproject/galaxy/blob/dev/test/functional/tools/section.xml))
    contains a test case demonstrating this block. This test case appears below:
    ```xml
    &lt;test&gt;
    &lt;section name="int"&gt;
    &lt;param name="inttest" value="12456" /&gt;
    &lt;/section&gt;
    &lt;section name="float"&gt;
    &lt;param name="floattest" value="6.789" /&gt;
    &lt;/section&gt;
    &lt;output name="out_file1"&gt;
    &lt;assert_contents&gt;
    &lt;has_line line="12456" /&gt;
    &lt;has_line line="6.789" /&gt;
    &lt;/assert_contents&gt;
    &lt;/output&gt;
    &lt;/test&gt;
    ```
    """

    param: List[TestParam] = field(default_factory=list, metadata={"type": "Element"})
    repeat: List["TestRepeat"] = field(default_factory=list, metadata={"type": "Element"})
    conditional: List["TestConditional"] = field(default_factory=list, metadata={"type": "Element"})
    section: List["TestSection"] = field(default_factory=list, metadata={"type": "Element"})
    output: List[TestOutput] = field(default_factory=list, metadata={"type": "Element"})
    output_collection: List[TestOutputCollection] = field(default_factory=list, metadata={"type": "Element"})
    assert_command: List[TestAssertions] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "description": "Describe assertions about the job's\ngenerated command-line.\n$assertions",
        },
    )
    assert_stdout: List[TestAssertions] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "description": "Describe assertions about the job's\nstandard output.\n$assertions",
        },
    )
    assert_stderr: List[TestAssertions] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "description": "Describe assertions about the job's\nstandard error.\n$assertions",
        },
    )
    assert_command_version: List[TestAssertions] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "description": "Describe assertions about the job's\ncommand version.\n$assertions",
        },
    )
    name: str = field(
        metadata={
            "type": "Attribute",
            "required": True,
            "description": "This value must match the name of the\nassociated input ``section``.",
        }
    )


@dataclass(kw_only=True)
class Inputs(BaseSetting):
    """Consists of all elements that define the tool's input parameters.

    Each [param](#tool-inputs-param) element contained in this element can be used as a command line parameter within the [command](#tool-command) text content. Most tools will not need to specify any attributes on this tag itself.
    """

    param: List[Param] = field(default_factory=list, metadata={"type": "Element"})
    repeat: List[Repeat] = field(default_factory=list, metadata={"type": "Element"})
    conditional: List[Conditional] = field(default_factory=list, metadata={"type": "Element"})
    section: List[Section] = field(default_factory=list, metadata={"type": "Element"})
    upload_dataset: List[object] = field(
        default_factory=list,
        metadata={"type": "Element", "description": "Internal, intentionally undocumented feature."},
    )
    display: List[str] = field(
        default_factory=list, metadata={"type": "Element", "description": "Documentation for display"}
    )
    action: Optional[str] = field(
        default=None, metadata={"type": "Attribute", "description": "URL used by data source tools."}
    )
    check_values: Union[bool, PermissiveBooleanValue] = field(
        default=PermissiveBooleanValue.TRUE,
        metadata={
            "type": "Attribute",
            "description": "Set to ``false`` to disable parameter checking in data source tools.",
        },
    )
    method: Optional[UrlmethodType] = field(
        default=None,
        metadata={"type": "Attribute", "description": "Data source HTTP action (e.g. ``get`` or ``put``) to use."},
    )
    target: Optional[TargetType] = field(
        default=None,
        metadata={"type": "Attribute", "description": "UI link target to use for data source tools (e.g. ``_top``)."},
    )
    nginx_upload: Union[bool, PermissiveBooleanValue] = field(
        default=PermissiveBooleanValue.FALSE,
        metadata={"type": "Attribute", "description": "This boolean indicates if this is an upload tool or not."},
    )


@dataclass(kw_only=True)
class Output(BaseSetting):
    """
    This tag describes an output to the tool.
    """

    change_format: List[ChangeFormat] = field(default_factory=list, metadata={"type": "Element"})
    filter: List[str] = field(default_factory=list, metadata={"type": "Element"})
    discover_datasets: List[OutputDiscoverDatasets] = field(default_factory=list, metadata={"type": "Element"})
    actions: List[Actions] = field(default_factory=list, metadata={"type": "Element"})
    data: List[OutputData] = field(default_factory=list, metadata={"type": "Element"})
    format: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": 'The short name for the output datatype.\nThe valid values for format can be found in\n[/config/datatypes_conf.xml.sample](https://github.com/galaxyproject/galaxy/blob/dev/config/datatypes_conf.xml.sample)\n(e.g. ``format="pdf"`` or ``format="fastqsanger"``). For collections this is the default format for all included\nelements. Note that the format specified here is ignored for discovered data sets.',
        },
    )
    format_source: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "This sets the data type of the output dataset(s) to be the same format as that of the specified tool input.",
        },
    )
    label: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "This will be the name of the history item for the output data set. The string\ncan include structure like ``${&lt;some param name&gt;.&lt;some attribute&gt;}``, as\ndiscussed for command line parameters in the ``&lt;command&gt;`` tag set section\nabove. The default label is ``${tool.name} on ${on_string}``.",
        },
    )
    name: str = field(
        metadata={
            "type": "Attribute",
            "required": True,
            "description": "Name for this output. This\n``name`` is used as the Cheetah variable containing the Galaxy assigned output\npath in ``command`` and ``configfile`` elements. The name should not contain\npipes or periods (e.g. ``.``).",
        }
    )
    structured_like: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": 'This is the name of input collection or\ndataset to derive "structure" of the output from (output element count and\nidentifiers). For instance, if the referenced input has three ordered items with\nidentifiers ``sample1``, ``sample2``,  and ``sample3``. If this references input\nelements in conditionals, this value should be qualified (e.g. ``cond|input`` instead\nof ``input`` if ``input`` is in a conditional with ``name="cond"``).',
        },
    )
    inherit_format: Optional[bool] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "If ``structured_like`` is set, inherit\nformat of outputs from format of corresponding input.",
        },
    )
    type_value: Optional[str] = field(
        default=None,
        metadata={
            "name": "type",
            "type": "Attribute",
            "description": "Output type. This could be older more established Galaxy types (e.g. data and collection) - in which case the semantics of this largely reflect the corresponding ``data`` and ``collection`` tags. This could also be newer non-data types such as ``integer`` or ``boolean``.",
        },
    )
    from_value: Optional[str] = field(
        default=None,
        metadata={
            "name": "from",
            "type": "Attribute",
            "description": "In expression tools, use this to specify a dictionary value to populate this output from. The semantics may change for other expression types in the future.",
        },
    )
    collection_type: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Collection type for output. Simple collection types are either ``list`` or\n``paired``, nested collections are specified as colon separated list of simple\ncollection types (the most common types are ``list``, ``paired``,\n``list:paired``, or ``list:list``).",
        },
    )
    collection_type_source: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "This is the name of input collection to\nderive collection's type (e.g. ``collection_type``) from.",
        },
    )


@dataclass(kw_only=True)
class OutputCollection(BaseSetting):
    """This tag set is contained within the ``&lt;outputs&gt;`` tag set, and it
    defines the output dataset collection description resulting from the tool's
    execution.

    The
    value of the attribute ``label`` can be acquired from input parameters or
    metadata in the same way that the command line parameters are (discussed in the
    [command](#tool-command) directive).
    Creating collections in tools is covered in-depth in
    [Planemo's documentation](https://planemo.readthedocs.io/en/latest/writing_advanced.html#creating-collections).
    """

    data: List[OutputData] = field(default_factory=list, metadata={"type": "Element"})
    discover_datasets: List[OutputCollectionDiscoverDatasets] = field(
        default_factory=list, metadata={"type": "Element"}
    )
    filter: List[str] = field(default_factory=list, metadata={"type": "Element"})
    format: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": 'The short name for the output datatype.\nThe valid values for format can be found in\n[/config/datatypes_conf.xml.sample](https://github.com/galaxyproject/galaxy/blob/dev/config/datatypes_conf.xml.sample)\n(e.g. ``format="pdf"`` or ``format="fastqsanger"``). For collections this is the default format for all included\nelements. Note that the format specified here is ignored for discovered data sets.',
        },
    )
    format_source: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "This sets the data type of the output dataset(s) to be the same format as that of the specified tool input.",
        },
    )
    label: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "This will be the name of the history item for the output data set. The string\ncan include structure like ``${&lt;some param name&gt;.&lt;some attribute&gt;}``, as\ndiscussed for command line parameters in the ``&lt;command&gt;`` tag set section\nabove. The default label is ``${tool.name} on ${on_string}``.",
        },
    )
    name: str = field(
        metadata={
            "type": "Attribute",
            "required": True,
            "description": "Name for this output. This\n``name`` is used as the Cheetah variable containing the Galaxy assigned output\npath in ``command`` and ``configfile`` elements. The name should not contain\npipes or periods (e.g. ``.``).",
        }
    )
    structured_like: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": 'This is the name of input collection or\ndataset to derive "structure" of the output from (output element count and\nidentifiers). For instance, if the referenced input has three ordered items with\nidentifiers ``sample1``, ``sample2``,  and ``sample3``. If this references input\nelements in conditionals, this value should be qualified (e.g. ``cond|input`` instead\nof ``input`` if ``input`` is in a conditional with ``name="cond"``).',
        },
    )
    inherit_format: Optional[bool] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "If ``structured_like`` is set, inherit\nformat of outputs from format of corresponding input.",
        },
    )
    type_value: Optional[str] = field(
        default=None,
        metadata={
            "name": "type",
            "type": "Attribute",
            "description": "Collection type for output. Simple collection types are either ``list`` or\n``paired``, nested collections are specified as colon separated list of simple\ncollection types (the most common types are ``list``, ``paired``,\n``list:paired``, or ``list:list``).",
        },
    )
    type_source: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "This is the name of input collection to\nderive collection's type (e.g. ``collection_type``) from.",
        },
    )


@dataclass(kw_only=True)
class TestConditional(BaseSetting):
    """Specify test parameters below a named of a ``conditional`` block matching
    one in ``inputs`` with this element.
    ``param`` elements in a ``test`` block can be arranged into nested ``repeat``,
    ``conditional``, and ``select`` structures to match the inputs. While this might
    be overkill for simple tests, it helps prevent ambiguous definitions and keeps
    things organized in large test cases. A future ``profile`` version of Galaxy
    tools may require ``conditional`` blocks be explicitly defined with this
    directive.
    ### Examples
    The following example demonstrates disambiguation of a parameter (named ``use``)
    which appears in multiple ``param`` names in ``conditional``s in the ``inputs``
    definition of the [disambiguate_cond.xml](https://github.com/galaxyproject/galaxy/blob/dev/test/functional/tools/disambiguate_cond.xml)
    tool.
    ```xml
    &lt;!-- Can use nested conditional blocks as shown below to disambiguate
    various nested parameters. --&gt;
    &lt;test&gt;
    &lt;conditional name="p1"&gt;
    &lt;param name="use" value="False"/&gt;
    &lt;/conditional&gt;
    &lt;conditional name="p2"&gt;
    &lt;param name="use" value="True"/&gt;
    &lt;/conditional&gt;
    &lt;conditional name="p3"&gt;
    &lt;param name="use" value="False"/&gt;
    &lt;/conditional&gt;
    &lt;conditional name="files"&gt;
    &lt;param name="attach_files" value="True" /&gt;
    &lt;conditional name="p4"&gt;
    &lt;param name="use" value="True"/&gt;
    &lt;param name="file" value="simple_line_alternative.txt" /&gt;
    &lt;/conditional&gt;
    &lt;/conditional&gt;
    &lt;output name="out_file1"&gt;
    &lt;assert_contents&gt;
    &lt;has_line line="7 4 7" /&gt;
    &lt;has_line line="This is a different line of text." /&gt;
    &lt;/assert_contents&gt;
    &lt;/output&gt;
    &lt;/test&gt;
    ```
    The [tophat2](https://github.com/galaxyproject/tools-devteam/blob/main/tools/tophat2/tophat2_wrapper.xml)
    tool demonstrates a real tool that benefits from more structured test cases
    using the ``conditional`` test directive. One such test case from that tool is
    shown below.
    ```xml
    &lt;!-- Test base-space paired-end reads with user-supplied reference fasta and full parameters --&gt;
    &lt;test&gt;
    &lt;!-- TopHat commands:
    tophat2 -o tmp_dir -r 20 -p 1 -a 8 -m 0 -i 70 -I 500000 -g 40 +coverage-search +min-coverage-intron 50 +max-coverage-intro 20000 +segment-mismatches 2 +segment-length 25 +microexon-search +report_discordant_pairs tophat_in1 test-data/tophat_in2.fastqsanger test-data/tophat_in3.fastqsanger
    Replace the + with double-dash
    Rename the files in tmp_dir appropriately
    --&gt;
    &lt;conditional name="singlePaired"&gt;
    &lt;param name="sPaired" value="paired"/&gt;
    &lt;param name="input1" ftype="fastqsanger" value="tophat_in2.fastqsanger"/&gt;
    &lt;param name="input2" ftype="fastqsanger" value="tophat_in3.fastqsanger"/&gt;
    &lt;param name="mate_inner_distance" value="20"/&gt;
    &lt;param name="report_discordant_pairs" value="Yes" /&gt;
    &lt;/conditional&gt;
    &lt;param name="genomeSource" value="indexed"/&gt;
    &lt;param name="index" value="tophat_test"/&gt;
    &lt;conditional name="params"&gt;
    &lt;param name="settingsType" value="full"/&gt;
    &lt;param name="library_type" value="FR Unstranded"/&gt;
    &lt;param name="read_mismatches" value="5"/&gt;
    &lt;!-- Error: the read mismatches (5) and the read gap length (2) should be less than or equal to the read edit dist (2) --&gt;
    &lt;param name="read_edit_dist" value="5" /&gt;
    &lt;param name="bowtie_n" value="Yes"/&gt;
    &lt;param name="mate_std_dev" value="20"/&gt;
    &lt;param name="anchor_length" value="8"/&gt;
    &lt;param name="splice_mismatches" value="0"/&gt;
    &lt;param name="min_intron_length" value="70"/&gt;
    &lt;param name="max_intron_length" value="500000"/&gt;
    &lt;param name="max_multihits" value="40"/&gt;
    &lt;param name="min_segment_intron" value="50" /&gt;
    &lt;param name="max_segment_intron" value="500000" /&gt;
    &lt;param name="seg_mismatches" value="2"/&gt;
    &lt;param name="seg_length" value="25"/&gt;
    &lt;conditional name="indel_search"&gt;
    &lt;param name="allow_indel_search" value="No"/&gt;
    &lt;/conditional&gt;
    &lt;conditional name="own_junctions"&gt;
    &lt;param name="use_junctions" value="Yes" /&gt;
    &lt;conditional name="gene_model_ann"&gt;
    &lt;param name="use_annotations" value="No" /&gt;
    &lt;/conditional&gt;
    &lt;conditional name="raw_juncs"&gt;
    &lt;param name="use_juncs" value="No" /&gt;
    &lt;/conditional&gt;
    &lt;conditional name="no_novel_juncs"&gt;
    &lt;param name="no_novel_juncs" value="No" /&gt;
    &lt;/conditional&gt;
    &lt;/conditional&gt;
    &lt;conditional name="coverage_search"&gt;
    &lt;param name="use_search" value="No" /&gt;
    &lt;/conditional&gt;
    &lt;param name="microexon_search" value="Yes" /&gt;
    &lt;conditional name="bowtie2_settings"&gt;
    &lt;param name="b2_settings" value="No" /&gt;
    &lt;/conditional&gt;
    &lt;!-- Fusion search params --&gt;
    &lt;conditional name="fusion_search"&gt;
    &lt;param name="do_search" value="Yes" /&gt;
    &lt;param name="anchor_len" value="21" /&gt;
    &lt;param name="min_dist" value="10000021" /&gt;
    &lt;param name="read_mismatches" value="3" /&gt;
    &lt;param name="multireads" value="4" /&gt;
    &lt;param name="multipairs" value="5" /&gt;
    &lt;param name="ignore_chromosomes" value="chrM"/&gt;
    &lt;/conditional&gt;
    &lt;/conditional&gt;
    &lt;conditional name="readGroup"&gt;
    &lt;param name="specReadGroup" value="no" /&gt;
    &lt;/conditional&gt;
    &lt;output name="junctions" file="tophat2_out4j.bed" /&gt;
    &lt;output name="accepted_hits" file="tophat_out4h.bam" compare="sim_size" /&gt;
    &lt;/test&gt;
    ```"""

    param: List[TestParam] = field(default_factory=list, metadata={"type": "Element"})
    repeat: List["TestRepeat"] = field(default_factory=list, metadata={"type": "Element"})
    conditional: List["TestConditional"] = field(default_factory=list, metadata={"type": "Element"})
    section: List[TestSection] = field(default_factory=list, metadata={"type": "Element"})
    output: List[TestOutput] = field(default_factory=list, metadata={"type": "Element"})
    output_collection: List[TestOutputCollection] = field(default_factory=list, metadata={"type": "Element"})
    assert_command: List[TestAssertions] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "description": "Describe assertions about the job's\ngenerated command-line.\n$assertions",
        },
    )
    assert_stdout: List[TestAssertions] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "description": "Describe assertions about the job's\nstandard output.\n$assertions",
        },
    )
    assert_stderr: List[TestAssertions] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "description": "Describe assertions about the job's\nstandard error.\n$assertions",
        },
    )
    assert_command_version: List[TestAssertions] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "description": "Describe assertions about the job's\ncommand version.\n$assertions",
        },
    )
    name: str = field(
        metadata={
            "type": "Attribute",
            "required": True,
            "description": "This value must match the name of the\nassociated input ``conditional``.",
        }
    )


@dataclass(kw_only=True)
class Outputs(BaseSetting):
    """Container tag set for the ``&lt;data&gt;`` and ``&lt;collection&gt;`` tag
    sets.

    The files and collections created by tools as a result of their execution are
    named by Galaxy. You specify the number and type of your output files using the
    contained ``&lt;data&gt;`` and ``&lt;collection&gt;`` tags. These may be passed to your tool
    executable through using line variables just like the parameters described in
    the ``&lt;inputs&gt;`` documentation.
    """

    output: List[Output] = field(default_factory=list, metadata={"type": "Element"})
    data: List[OutputData] = field(default_factory=list, metadata={"type": "Element"})
    collection: List[OutputCollection] = field(default_factory=list, metadata={"type": "Element"})
    provided_metadata_style: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": 'Style used for tool provided metadata file (i.e.\n[galaxy.json](https://planemo.readthedocs.io/en/latest/writing_advanced.html#tool-provided-metadata))\n- this can be either "legacy" or "default". The default of tools with a profile\nof 17.09 or newer are "default", and "legacy" for older and tools and tools\nwithout a specified profile. A discussion of the differences between the styles\ncan be found [here](https://github.com/galaxyproject/galaxy/pull/4437).',
        },
    )
    provided_metadata_file: str = field(
        default="galaxy.json",
        metadata={
            "type": "Attribute",
            "description": "Path relative to tool's working directory to load tool provided metadata from.\nThis metadata can describe dynamic datasets to load, dynamic collection\ncontents, as well as simple metadata (e.g. name, dbkey, etc...) and\ndatatype-specific metadata for declared outputs. More information can be found\n[here](https://planemo.readthedocs.io/en/latest/writing_advanced.html#tool-provided-metadata).\nThe default is ``galaxy.json``.",
        },
    )


@dataclass(kw_only=True)
class TestRepeat(BaseSetting):
    """Specify test parameters below an iteration of a ``repeat`` block with this
    element.

    ``param`` elements in a ``test`` block can be arranged into nested ``repeat``,
    ``conditional``, and ``select`` structures to match the inputs. While this might
    be overkill for simple tests, it helps prevent ambiguous definitions and keeps
    things organized in large test cases. A future ``profile`` version of Galaxy
    tools may require ``repeat`` blocks be explicitly defined with this directive.
    ### Examples
    The test tool [disambiguate_repeats.xml](https://github.com/galaxyproject/galaxy/blob/dev/test/functional/tools/disambiguate_repeats.xml)
    demonstrates the use of this directive.
    This first test case demonstrates that this block allows different values for
    the ``param`` named ``input`` to be tested even though this parameter name
    appears in two different ``&lt;repeat&gt;`` elements in the ``&lt;inputs&gt;`` definition.
    ```xml
    &lt;!-- Can disambiguate repeats and specify multiple blocks using,
    nested structure. --&gt;
    &lt;test&gt;
    &lt;repeat name="queries"&gt;
    &lt;param name="input" value="simple_line.txt"/&gt;
    &lt;/repeat&gt;
    &lt;repeat name="more_queries"&gt;
    &lt;param name="input" value="simple_line_alternative.txt"/&gt;
    &lt;/repeat&gt;
    &lt;output name="out_file1"&gt;
    &lt;assert_contents&gt;
    &lt;has_line line="This is a line of text." /&gt;
    &lt;has_line line="This is a different line of text." /&gt;
    &lt;/assert_contents&gt;
    &lt;/output&gt;
    &lt;/test&gt;
    ```
    The second definition in that file demonstrates repeated ``&lt;repeat&gt;`` blocks
    allowing multiple instances of a single repeat to be specified.
    ```xml
    &lt;!-- Multiple such blocks can be specified but only with newer API
    driven tests. --&gt;
    &lt;test&gt;
    &lt;repeat name="queries"&gt;
    &lt;param name="input" value="simple_line.txt"/&gt;
    &lt;/repeat&gt;
    &lt;repeat name="queries"&gt;
    &lt;param name="input" value="simple_line_alternative.txt"/&gt;
    &lt;/repeat&gt;
    &lt;repeat name="more_queries"&gt;
    &lt;param name="input" value="simple_line.txt"/&gt;
    &lt;/repeat&gt;
    &lt;repeat name="more_queries"&gt;
    &lt;param name="input" value="simple_line_alternative.txt"/&gt;
    &lt;/repeat&gt;
    &lt;output name="out_file1" file="simple_lines_interleaved.txt"/&gt;
    &lt;/test&gt;
    ```
    """

    param: List[TestParam] = field(default_factory=list, metadata={"type": "Element"})
    repeat: List["TestRepeat"] = field(default_factory=list, metadata={"type": "Element"})
    conditional: List[TestConditional] = field(default_factory=list, metadata={"type": "Element"})
    section: List[TestSection] = field(default_factory=list, metadata={"type": "Element"})
    output: List[TestOutput] = field(default_factory=list, metadata={"type": "Element"})
    output_collection: List[TestOutputCollection] = field(default_factory=list, metadata={"type": "Element"})
    assert_command: List[TestAssertions] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "description": "Describe assertions about the job's\ngenerated command-line.\n$assertions",
        },
    )
    assert_stdout: List[TestAssertions] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "description": "Describe assertions about the job's\nstandard output.\n$assertions",
        },
    )
    assert_stderr: List[TestAssertions] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "description": "Describe assertions about the job's\nstandard error.\n$assertions",
        },
    )
    assert_command_version: List[TestAssertions] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "description": "Describe assertions about the job's\ncommand version.\n$assertions",
        },
    )
    name: str = field(
        metadata={
            "type": "Attribute",
            "required": True,
            "description": "This value must match the name of the\nassociated input ``repeat``.",
        }
    )


@dataclass(kw_only=True)
class Test(BaseSetting):
    """This tag set contains the necessary parameter values for executing the tool
    via the functional test framework.

    ### Example
    The following two tests will execute the
    [/tools/filters/sorter.xml](https://github.com/galaxyproject/galaxy/blob/dev/tools/filters/sorter.xml)
    tool. Notice the way that the tool's inputs and outputs are defined.
    ```xml
    &lt;tests&gt;
    &lt;test&gt;
    &lt;param name="input" value="1.bed" ftype="bed" /&gt;
    &lt;param name="column" value="1"/&gt;
    &lt;param name="order" value="ASC"/&gt;
    &lt;param name="style" value="num"/&gt;
    &lt;output name="out_file1" file="sort1_num.bed" ftype="bed" /&gt;
    &lt;/test&gt;
    &lt;test&gt;
    &lt;param name="input" value="7.bed" ftype="bed" /&gt;
    &lt;param name="column" value="1"/&gt;
    &lt;param name="order" value="ASC"/&gt;
    &lt;param name="style" value="alpha"/&gt;
    &lt;output name="out_file1" file="sort1_alpha.bed" ftype="bed" /&gt;
    &lt;/test&gt;
    &lt;/tests&gt;
    ```
    The following example, tests the execution of the MAF-to-FASTA converter
    ([/tools/maf/maf_to_fasta.xml](https://github.com/galaxyproject/galaxy/blob/dev/tools/maf/maf_to_fasta.xml)).
    ```xml
    &lt;tests&gt;
    &lt;test&gt;
    &lt;param name="input1" value="3.maf" ftype="maf"/&gt;
    &lt;param name="species" value="canFam1"/&gt;
    &lt;param name="fasta_type" value="concatenated"/&gt;
    &lt;output name="out_file1" file="cf_maf2fasta_concat.dat" ftype="fasta"/&gt;
    &lt;/test&gt;
    &lt;/tests&gt;
    ```
    This test demonstrates verifying specific properties about a test output instead
    of directly comparing it to another file. Here the file attribute is not
    specified and instead a series of assertions is made about the output.
    ```xml
    &lt;test&gt;
    &lt;param name="input" value="maf_stats_interval_in.dat" /&gt;
    &lt;param name="lineNum" value="99999"/&gt;
    &lt;output name="out_file1"&gt;
    &lt;assert_contents&gt;
    &lt;has_text text="chr7" /&gt;
    &lt;not_has_text text="chr8" /&gt;
    &lt;has_text_matching expression="1274\\d+53" /&gt;
    &lt;has_line_matching expression=".*\\s+127489808\\s+127494553" /&gt;
    &lt;!-- &amp;#009; is XML escape code for tab --&gt;
    &lt;has_line line="chr7&amp;#009;127471195&amp;#009;127489808" /&gt;
    &lt;has_n_columns n="3" /&gt;
    &lt;has_n_lines n="3" /&gt;
    &lt;/assert_contents&gt;
    &lt;/output&gt;
    &lt;/test&gt;
    ```
    """

    param: List[TestParam] = field(default_factory=list, metadata={"type": "Element"})
    repeat: List[TestRepeat] = field(default_factory=list, metadata={"type": "Element"})
    conditional: List[TestConditional] = field(default_factory=list, metadata={"type": "Element"})
    section: List[TestSection] = field(default_factory=list, metadata={"type": "Element"})
    output: List[TestOutput] = field(default_factory=list, metadata={"type": "Element"})
    output_collection: List[TestOutputCollection] = field(default_factory=list, metadata={"type": "Element"})
    assert_command: List[TestAssertions] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "description": "Describe assertions about the job's\ngenerated command-line.\n$assertions",
        },
    )
    assert_stdout: List[TestAssertions] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "description": "Describe assertions about the job's\nstandard output.\n$assertions",
        },
    )
    assert_stderr: List[TestAssertions] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "description": "Describe assertions about the job's\nstandard error.\n$assertions",
        },
    )
    assert_command_version: List[TestAssertions] = field(
        default_factory=list,
        metadata={
            "type": "Element",
            "description": "Describe assertions about the job's\ncommand version.\n$assertions",
        },
    )
    expect_exit_code: Optional[int] = field(
        default=None, metadata={"type": "Attribute", "description": "Describe the job's expected exit code."}
    )
    expect_num_outputs: Optional[int] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Assert the number of statically defined items (datasets and collections) this test\nshould produce. Each `data` or `collection` tag that is listed in the\noutputs section is a statically defined output and adds one to this count.  For\ninstance a statically defined pair adds a count of 3; 1 for the collection and 1 for each\nof the two datasets.  Dynamically defined output datasets (using ``discover_datasets`` tag)\nare not counted here, but note that the ``collection`` or ``data`` tag that\nincludes the ``discover_datasets`` still adds a count of one.  This is useful to\nensure ``filter`` directives are implemented correctly.  See\n[here](https://github.com/galaxyproject/galaxy/blob/dev/test/functional/tools/expect_num_outputs.xml)\nfor examples.",
        },
    )
    expect_failure: Union[bool, PermissiveBooleanValue] = field(
        default=PermissiveBooleanValue.FALSE,
        metadata={
            "type": "Attribute",
            "description": "Setting this to ``true`` indicates\nthe expectation is for the job fail. If set to ``true`` no job output checks may\nbe present in ``test`` definition.",
        },
    )
    expect_test_failure: Union[bool, PermissiveBooleanValue] = field(
        default=PermissiveBooleanValue.FALSE,
        metadata={
            "type": "Attribute",
            "description": "Setting this to ``true`` indicates\nthat at least one of the assumptions of the test is not met. This is most useful for internal testing.",
        },
    )
    maxseconds: Optional[int] = field(
        default=None, metadata={"type": "Attribute", "description": "Maximum amount of time to let test run."}
    )


@dataclass(kw_only=True)
class Tests(BaseSetting):
    """Container tag set to specify tests via the ``&lt;test&gt;`` tag sets.

    Any number of tests can be included,
    and each test is wrapped within separate ``&lt;test&gt;`` tag sets. Functional tests are
    executed via [Planemo](https://planemo.readthedocs.io/) or the
    [run_tests.sh](https://github.com/galaxyproject/galaxy/blob/dev/run_tests.sh)
    shell script distributed with Galaxy.
    The documentation contained here is mostly reference documentation, for
    tutorials on writing tool tests please check out Planemo's
    [Test-Driven Development](https://planemo.readthedocs.io/en/latest/writing_advanced.html#test-driven-development)
    documentation or the much older wiki content for
    [WritingTests](https://galaxyproject.org/admin/tools/writing-tests/).
    """

    test: List[Test] = field(default_factory=list, metadata={"type": "Element"})


@dataclass(kw_only=True)
class Tool(BaseSetting):
    """The outer-most tag set of tool XML files. Attributes on this tag apply to the
    tool as a whole.
    ### Tool profile
    List of behavior changes associated with profile versions:
    #### 16.04
    - Disable implicit extra file collection. All dynamic extra file collection requires a `discover_datasets` tag.
    - Disable `format="input"` and require explicit metadata targets (`metadata_source`, `format_source`).
    - Disable `interpreter` use `$__tool_directory__`.
    - Disable `$param_file` use `configfile`.
    - Disable default tool version of 1.0.0.
    - Use non zero exit code as default stdio error condition (before non-empty stderr).
    #### 18.01
    - Use a separate home directory for each job.
    - Introduce `provided_metadata_style` with default `"default"` before `"legacy"`.
    #### 18.09
    - References to other inputs need to be fully qualified by using `|`.
    - Do not allow provided but illegal default values.
    - Do not use Galaxy python environment for `manage_data` tools.
    #### 19.05
    - Change default Python version from 2.7 to 3.5
    #### 20.05
    - json config files:
    - unselected optional `select` and `data_column` parameters get `None` instead of `"None"`
    - multiple `select` and `data_column` parameters are lists (before comma separated string)
    #### 20.09
    - Exit immediately if a command exits with a non-zero status (`set -e`).
    - Assume sort order for collection elements.
    ### 21.09
    - Do not strip leading and trailing whitespaces in `from_work_dir` attribute.
    ### 23.0
    - Text parameters that are inferred to be optional (i.e the `optional` tag is not set, but the tool parameter accepts an empty string)
    are set to `None` for templating in Cheetah. Older tools receive the empty string `""` as the templated value.
    ### Examples
    A normal tool:
    ```xml
    &lt;tool id="seqtk_seq"
    name="Convert FASTQ to FASTA"
    version="1.0.0"
    profile="16.04"
    &gt;
    ```
    A ``data_source`` tool contains a few more relevant attributes.
    ```xml
    &lt;tool id="ucsc_table_direct1"
    name="UCSC Main"
    version="1.0.0"
    hidden="false"
    profile="16.01"
    tool_type="data_source"
    URL_method="post"&gt;
    ```"""

    class Meta:
        name = "tool"

    macros: Optional[Macros] = field(default=None, metadata={"type": "Element"})
    edam_topics: Optional[EdamTopics] = field(default=None, metadata={"type": "Element"})
    edam_operations: Optional[EdamOperations] = field(default=None, metadata={"type": "Element"})
    xrefs: Optional[Xrefs] = field(default=None, metadata={"type": "Element"})
    creator: Optional[Creator] = field(default=None, metadata={"type": "Element"})
    requirements: Optional[Requirements] = field(default=None, metadata={"type": "Element"})
    required_files: Optional[RequiredFiles] = field(default=None, metadata={"type": "Element"})
    entry_points: Optional[EntryPoints] = field(default=None, metadata={"type": "Element"})
    description: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "description": "The value is displayed in\nthe tool menu immediately following the hyperlink for the tool (based on the\n``name`` attribute of the ``&lt;tool&gt;`` tag set described above).\n### Example\n```xml\n&lt;description&gt;table browser&lt;/description&gt;\n```",
        },
    )
    parallelism: Optional[Parallelism] = field(default=None, metadata={"type": "Element"})
    version_command: Optional[VersionCommand] = field(default=None, metadata={"type": "Element"})
    action: Optional[ToolAction] = field(default=None, metadata={"type": "Element"})
    environment_variables: Optional[EnvironmentVariables] = field(default=None, metadata={"type": "Element"})
    command: Optional[Command] = field(default=None, metadata={"type": "Element"})
    expression: Optional[Expression] = field(default=None, metadata={"type": "Element"})
    request_param_translation: Optional[RequestParameterTranslation] = field(default=None, metadata={"type": "Element"})
    configfiles: Optional[ConfigFiles] = field(default=None, metadata={"type": "Element"})
    outputs: Optional[Outputs] = field(default=None, metadata={"type": "Element"})
    inputs: Optional[Inputs] = field(default=None, metadata={"type": "Element"})
    tests: Optional[Tests] = field(default=None, metadata={"type": "Element"})
    stdio: Optional[Stdio] = field(default=None, metadata={"type": "Element"})
    help: Optional[str] = field(
        default=None,
        metadata={
            "type": "Element",
            "description": "This tag set includes all of the necessary details of how to use the tool. This tag set should be included as the next to the last tag set, before citations, in the tool config. Tool help is written in reStructuredText. Included here is only an overview of a subset of features. For more information see [here](https://docutils.sourceforge.io/docs/ref/rst/restructuredtext.html).\ntag | details\n--- | -------\n``.. class:: warningmark`` | a yellow warning symbol\n``.. class:: infomark`` | a blue information symbol\n``.. image:: path-of-the-file.png :height: 500 :width: 600`` | insert a png file of height 500 and width 600 at this position |\n``**bold**`` | bold\n``*italic*`` | italic\n``*`` | list\n``-`` | list\n``::`` | paragraph\n``-----`` | a horizontal line\n### Examples\nShow a warning sign to remind users that this tool accept fasta format files only, followed by an example of the query sequence and a figure.\n```xml\n&lt;help&gt;\n.. class:: warningmark\n'''TIP''' This tool requires *fasta* format.\n----\n'''Example'''\nQuery sequence::\n&gt;seq1\nATCG...\n.. image:: my_figure.png\n:height: 500\n:width: 600\n&lt;/help&gt;\n```",
        },
    )
    code: Optional[Code] = field(default=None, metadata={"type": "Element"})
    uihints: Optional[Uihints] = field(default=None, metadata={"type": "Element"})
    options: Optional[Options] = field(default=None, metadata={"type": "Element"})
    trackster_conf: Optional[TracksterConf] = field(default=None, metadata={"type": "Element"})
    citations: Optional[Citations] = field(default=None, metadata={"type": "Element"})
    id: str = field(
        metadata={
            "type": "Attribute",
            "required": True,
            "description": "Must be unique across all tools;\nshould be lowercase and contain only letters, numbers, and underscores.\nIt allows for tool versioning and metrics of the number of times a tool is used,\namong other things.",
        }
    )
    name: str = field(
        metadata={
            "type": "Attribute",
            "required": True,
            "description": "This string is what is displayed as a\nhyperlink in the tool menu.",
        }
    )
    version: str = field(
        default="1.0.0",
        metadata={
            "type": "Attribute",
            "description": "This string allows for tool versioning\nand should be increased with each new version of the tool. The value should\nfollow the [PEP 440](https://www.python.org/dev/peps/pep-0440/) specification.\nIt defaults to ``1.0.0`` if it is not included in the tag.",
        },
    )
    hidden: Union[bool, PermissiveBooleanValue] = field(
        default=PermissiveBooleanValue.FALSE,
        metadata={
            "type": "Attribute",
            "description": "Allows for tools to be loaded upon\nserver startup, but not displayed in the tool menu. This attribute should be\napplied in the toolbox configuration instead and so should be considered\ndeprecated.",
        },
    )
    display_interface: Optional[Union[bool, PermissiveBooleanValue]] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Disable the display the tool's\ngraphical tool form by setting this to ``false``.",
        },
    )
    tool_type: Optional[ToolTypeType] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "Allows for certain framework\nfunctionality to be performed on certain types of tools. Normal tools that execute\ntypical command-line jobs do not need to specify this, special kinds of tools such\nas [Data Source](https://galaxyproject.org/admin/internals/data-sources/) and\n[Data Manager](https://galaxyproject.org/admin/tools/data-managers/) tools should\nset this to have values such as ``data_source`` or ``manage_data``.",
        },
    )
    profile: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "This string specifies the minimum Galaxy\nversion that should be required to run this tool. Certain legacy behaviors such\nas using standard error content to detect errors instead of exit code are disabled\nautomatically if profile is set to any version newer than ``16.01``. See above\nfor the list of behavior changes associated with profile versions.",
        },
    )
    license: Optional[str] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "This string specifies any full URI or a\na short [SPDX](https://spdx.org/licenses/) identifier for a license for this tool\nwrapper. The tool wrapper version can be indepedent of the underlying tool. This\nlicense covers the tool XML and associated scripts shipped with the tool.\nThis is interpreted as [schema.org/license](https://schema.org/license) property.",
        },
    )
    python_template_version: Optional[float] = field(
        default=None,
        metadata={
            "type": "Attribute",
            "description": "This string specifies the minimum Python\nversion that is able to fill the Cheetah sections of the tool. If unset defaults\nto 2.7 if the profile is older than 19.05, otherwise defaults to 3.5. Galaxy will\nattempt to convert Python statements in Cheetah sections using [future](http://python-future.org/)\nif Galaxy is run on Python 3 and ``python_template_version`` is below 3.",
        },
    )
    workflow_compatible: bool = field(
        default=True,
        metadata={
            "type": "Attribute",
            "description": "This attribute indicates if\nthis tool is usable within a workflow (defaults to ``true`` for normal tools and\n``false`` for data sources).",
        },
    )
    url_method: Optional[UrlmethodType] = field(
        default=None,
        metadata={
            "name": "URL_method",
            "type": "Attribute",
            "description": "Only used if ``tool_type`` attribute value\nis ``data_source`` - this attribute defines the HTTP request method to use when\ncommunicating with an external data source application (the default is ``get``).",
        },
    )
