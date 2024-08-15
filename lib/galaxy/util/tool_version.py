def remove_version_from_guid(guid):
    """
    Removes version from toolshed-derived tool_id(=guid).
    """
    if "/" not in guid:
        return None
    last_slash = guid.rfind("/")
    return guid[:last_slash]
