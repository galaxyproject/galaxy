from lxml import etree


def format_xml(content: str, tab_size: int = 4) -> str:
    """Format XML content with consistent indentation.

    Used by planemo's format command and the Galaxy Language Server
    to apply uniform formatting to Galaxy tool XML files.
    """
    try:
        parser = etree.XMLParser(strip_cdata=False)
        xml = etree.fromstring(content, parser=parser)
        etree.indent(xml, space=" " * tab_size)
        return etree.tostring(xml, pretty_print=True, encoding=str)
    except etree.XMLSyntaxError:
        return content
