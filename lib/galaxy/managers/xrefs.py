
class xrefsManager(object):

    def __init__(self, app):
        self.app = app

    def parse_xref(self, xref_elem):
        return parse_xref(xref_elem, self)

    def _get_tool(self, tool_id):
        tool = self.app.toolbox.get_tool(tool_id)
        return tool


def parse_xref(elem, tool_ref_manager):
    """ Parse a xreference entry from the specified XML element."""
    return xref(elem)


class Base_xref(object):
    def to_dict(self):
        return dict(
            reftype=self.reftype,
            content=self.content,
        )


class xref(Base_xref):
    def __init__(self, elem):
        self.content = elem.text.strip()
        self.reftype = elem.attrib.get('type', None)
