def remove_version_from_guid(guid: str) -> str | None:
    """
    Removes version from toolshed-derived tool_id(=guid).
    """
    if "/" not in guid:
        return None
    last_slash = guid.rfind("/")
    return guid[:last_slash]


def short_tool_id(guid: str) -> str:
    """
    Tool-id segment of a toolshed-derived tool_id(=guid),
    e.g. ``toolshed/repos/owner/name/tool_id/version`` -> ``tool_id``.
    Ids that aren't guids pass through unchanged.
    """
    versionless = remove_version_from_guid(guid)
    if not versionless or "/" not in versionless:
        return guid
    return versionless.rsplit("/", 1)[-1]
