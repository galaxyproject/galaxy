"""This module contains a citation lint function.

Citations describe references that should be used when consumers
of the tool publish results.
"""
from ._util import node_props_factory


def lint_citations(tool_xml, lint_ctx):
    """Ensure tool contains at least one valid citation."""
    root = tool_xml.getroot()
    node_props = node_props_factory(tool_xml)
    citations = root.findall("citations")
    if len(citations) > 1:
        lint_ctx.error("More than one citation section found, behavior undefined.", **node_props(citations[1]))
        return

    if len(citations) == 0:
        lint_ctx.warn("No citations found, consider adding citations to your tool.", **node_props(root))
        return

    valid_citations = 0
    for citation in citations[0]:
        if citation.tag != "citation":
            lint_ctx.warn(f"Unknown tag discovered in citations block [{citation.tag}], will be ignored.", **node_props(citation))
            continue
        citation_type = citation.attrib.get("type")
        if citation_type not in ('bibtex', 'doi'):
            lint_ctx.warn(f"Unknown citation type discovered [{citation_type}], will be ignored.", **node_props(citation))
            continue
        if citation.text is None or not citation.text.strip():
            lint_ctx.error(f'Empty {citation_type} citation.', **node_props(citation))
            continue
        valid_citations += 1

    if valid_citations > 0:
        lint_ctx.valid(f"Found {valid_citations} likely valid citations.", **node_props(root))
    else:
        lint_ctx.warn("Found no valid citations.", **node_props(root))
