"""This module contains a linting functions for tool XML block order.

For more information on the IUC standard for XML block order see -
https://github.com/galaxy-iuc/standards.
"""
# https://github.com/galaxy-iuc/standards
# https://github.com/galaxy-iuc/standards/pull/7/files
TAG_ORDER = [
    'description',
    'macros',
    'edam_topics',
    'edam_operations',
    'xrefs',
    'parallelism',
    'requirements',
    'code',
    'stdio',
    'version_command',
    'command',
    'environment_variables',
    'configfiles',
    'inputs',
    'outputs',
    'tests',
    'help',
    'citations',
]

DATASOURCE_TAG_ORDER = [
    'description',
    'macros',
    'command',
    'configfiles',
    'inputs',
    'request_param_translation',
    'uihints',
    'outputs',
    'options',
    'help',
    'citations',
]


# Ensure the XML blocks appear in the correct order prescribed
# by the tool author best practices.
def lint_xml_order(tool_xml, lint_ctx):
    tool_root = tool_xml.getroot()

    if tool_root.attrib.get('tool_type', '') == 'data_source':
        _validate_for_tags(tool_root, lint_ctx, DATASOURCE_TAG_ORDER)
    else:
        _validate_for_tags(tool_root, lint_ctx, TAG_ORDER)


def _validate_for_tags(root, lint_ctx, tag_ordering):
    last_tag = None
    last_key = None
    for elem in root:
        tag = elem.tag
        if tag in tag_ordering:
            key = tag_ordering.index(tag)
            if last_key:
                if last_key > key:
                    lint_ctx.warn(f"Best practice violation [{tag}] elements should come before [{last_tag}]")
            last_tag = tag
            last_key = key
        else:
            lint_ctx.info(f"Unknown tag [{tag}] encountered, this may result in a warning in the future.")
