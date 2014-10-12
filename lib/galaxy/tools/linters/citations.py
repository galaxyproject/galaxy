

def lint_citations(tool_xml, lint_ctx):
    root = tool_xml.getroot()
    citations = root.findall("citations")
    if len(citations) > 1:
        lint_ctx.error("More than one citation section found, behavior undefined.")
        return

    if len(citations) == 0:
        lint_ctx.warn("No citations found, consider adding citations to your tool.")
        return

    valid_citations = 0
    for citation in citations[0]:
        if citation.tag != "citation":
            lint_ctx.warn("Unknown tag discovered in citations block [%s], will be ignored." % citation.tag)
        if "type" in citation.attrib:
            citation_type = citation.attrib.get("type")
            if citation_type not in ["doi", "bibtex"]:
                lint_ctx.warn("Unknown citation type discovered [%s], will be ignored.", citation_type)
            else:
                valid_citations += 1

    if valid_citations > 0:
        lint_ctx.valid("Found %d likely valid citations.", valid_citations)

