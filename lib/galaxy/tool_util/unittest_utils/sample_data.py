from string import Template

SIMPLE_TOOL_WITH_MACRO = """<tool id="tool_with_macro" name="macro_annotation" version="@WRAPPER_VERSION@">
    <expand macro="inputs" />
    <macros>
        <import>external.xml</import>
    </macros>
</tool>"""

SIMPLE_MACRO = Template(
    """
<macros>
    <token name="@WRAPPER_VERSION@">$tool_version</token>
    <macro name="inputs">
        <inputs/>
    </macro>
</macros>
"""
)

VALID_XML_VALIDATORS = [
    """<validator type="empty_dataset" />""",
    """<validator type="empty_dataset" message="foobar" />""",
    """<validator type="empty_dataset" message="foobar" negate="true" />""",
    """<validator type="expression">value == 7</validator>""",
    """<validator type="regex">mycoolexpression</validator>""",
    """<validator type="in_range" min="3.1" max="3.8" />""",
    """<validator type="in_range" min="3.1" />""",
    """<validator type="in_range" min="3.1" max="3.8" exclude_min="false" exclude_max="true" />""",
    """<validator type="length" min="3" />""",
    """<validator type="length" max="7" />""",
    """<validator type="length" min="2" max="7" negate="true" />""",
    """<validator type="empty_field" />""",
    """<validator type="empty_extra_files_path" />""",
    """<validator type="no_options" />""",
    """<validator type="unspecified_build" />""",
    """<validator type="dataset_ok_validator" />""",
    """<validator type="metadata" check="foo, bar" />""",
    """<validator type="metadata" skip="name, dbkey" />""",
    """<validator type="dataset_metadata_equal" metadata_name="foobar" value="moocow" />""",
    """<validator type="dataset_metadata_equal" metadata_name="foobar" value_json="null" />""",
    """<validator type="dataset_metadata_in_range" metadata_name="foobar" min="4.5" max="7.8" />""",
    """<validator type="dataset_metadata_in_range" metadata_name="foobar" min="4.5" max="7.8" include_min="true" />""",
    """<validator type="dataset_metadata_in_data_table" metadata_name="foobar" metadata_column="3" table_name="mycooltable" />""",
    """<validator type="dataset_metadata_not_in_data_table" metadata_name="foobar" metadata_column="3" table_name="mycooltable" />""",
    """<validator type="value_in_data_table" metadata_column="3" table_name="mycooltable" />""",
    """<validator type="value_in_data_table" table_name="mycooltable" />""",
    """<validator type="value_not_in_data_table" metadata_column="3" table_name="mycooltable" />""",
    """<validator type="value_not_in_data_table" table_name="mycooltable" />""",
]

INVALID_XML_VALIDATORS = [
    """<validator type="unknown" />""",
    """<validator type="empty_datasetx" />""",
    """<validator type="expression" />""",
    """<validator type="empty_dataset" message="foobar" negate="NOTABOOLVALUE" />""",
    """<validator type="regex" />""",
    """<validator type="in_range" min="3.1" max="3.8" exclude_min="false" exclude_max="foobar" />""",
    """<validator type="in_range" min="notanumber" max="3.8" />""",
    """<validator type="length" min="notanumber" />""",
    """<validator type="length" max="notanumber" />""",
    """<validator type="length" min="2" max="7" negate="notabool" />""",
    """<validator type="dataset_metadata_equal" />""",
    """<validator type="dataset_metadata_equal" metadaata_name="foobar" />""",
    """<validator type="dataset_metadata_equal" metadaata_name="foobar" value_json="undefined" />""",
    """<validator type="dataset_metadata_in_range" metadata_name="foobar" min="4.5" max="7.8" include_min="notabool" />"""
    """<validator type="dataset_metadata_in_range"  min="4.5" max="7.8" />"""
    """<validator type="dataset_metadata_in_data_table" metadata_name="foobar" metadata_column="3" />""",
    """<validator type="dataset_metadata_in_data_table" metadata_column="3" table_name="mycooltable" />""",
    """<validator type="dataset_metadata_not_in_data_table" metadata_name="foobar" metadata_column="3" />""",
    """<validator type="dataset_metadata_not_in_data_table" metadata_column="3" table_name="mycooltable" />""",
]
