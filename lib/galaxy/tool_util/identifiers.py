from urllib.parse import quote


def uri_safe_tool_id(tool_id: str) -> str:
    # Shed tool ids contain ``+`` in their version suffix (e.g.
    # ``.../1.3.1+galaxy1``). In a query string the ``+`` decodes to a
    # literal space unless percent-encoded as ``%2B``.
    return quote(tool_id)
