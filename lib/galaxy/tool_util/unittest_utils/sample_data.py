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
