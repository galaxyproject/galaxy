"""This module contains a citation lint function.

Citations describe references that should be used when consumers
of the tool publish results.
"""
from ._util import node_props


def lint_citations(tool_xml, lint_ctx):
    """Ensure tool contains at least one valid citation."""
    root = tool_xml.getroot()
    citations = root.findall("citations")
    if len(citations) > 1:
        lint_ctx.error("More than one citation section found, behavior undefined.", **node_props(citations[1], tool_xml))
        return

    if len(citations) == 0:
        lint_ctx.warn("No citations found, consider adding citations to your tool.", **node_props(root, tool_xml))
        return

    valid_citations = 0
    for citation in citations[0]:
        if citation.tag != "citation":
            lint_ctx.warn(f"Unknown tag discovered in citations block [{citation.tag}], will be ignored.", **node_props(citation, tool_xml))
            continue
        citation_type = citation.attrib.get("type")
        if citation_type not in ('bibtex', 'doi'):
            lint_ctx.warn(f"Unknown citation type discovered [{citation_type}], will be ignored.", **node_props(citation, tool_xml))
            continue
        if citation.text is None or not citation.text.strip():
            lint_ctx.error(f'Empty {citation_type} citation.', **node_props(citation, tool_xml))
            continue
        valid_citations += 1

    if valid_citations > 0:
        lint_ctx.valid(f"Found {valid_citations} likely valid citations.", **node_props(root, tool_xml))
    else:
        lint_ctx.warn("Found no valid citations.", **node_props(root, tool_xml))
