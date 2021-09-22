from galaxy.tool_util.linters import outputs

# check that linter accepts format source for collection elements as means to specify format
# and that the linter warns if format and format_source are used
OUTPUTS_COLLECTION_FORMAT_SOURCE = """
<tool name="BWA Mapper" id="bwa" version="1.0.1" is_multi_byte="true" display_interface="true" require_login="true" hidden="true">
    <description>The BWA Mapper</description>
    <version_command interpreter="python">bwa.py --version</version_command>
    <outputs>
        <collection name="output_collection" type="paired">
            <data name="forward" format_source="input_readpair" />
            <data name="reverse" format_source="input_readpair" format="fastq"/>
        </collection>
    </outputs>
</tool>
"""

# check that linter does not complain about missing format if from_tool_provided_metadata is used
OUTPUTS_DISCOVER_TOOL_PROVIDED_METADATA = """
<tool name="BWA Mapper" id="bwa" version="1.0.1" is_multi_byte="true" display_interface="true" require_login="true" hidden="true">
    <description>The BWA Mapper</description>
    <version_command interpreter="python">bwa.py --version</version_command>
    <outputs>
        <data name="output">
            <discover_datasets from_tool_provided_metadata="true"/>
        </data>
    </outputs>
</tool>
"""
TESTS = [
    (
        OUTPUTS_COLLECTION_FORMAT_SOURCE, outputs.lint_output,
        lambda x:
            "Tool data output reverse should use either format_source or format/ext" in x.warn_messages
            and len(x.warn_messages) == 1 and len(x.error_messages) == 0
    ),
    (
        OUTPUTS_DISCOVER_TOOL_PROVIDED_METADATA, outputs.lint_output,
        lambda x:
            len(x.warn_messages) == 0 and len(x.error_messages) == 0
    ),
]

TEST_IDS = [
    'outputs collection static elements with format_source',
    'outputs discover datatsets with tool provided metadata'
]
