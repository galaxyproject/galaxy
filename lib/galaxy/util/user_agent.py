from galaxy.version import VERSION


def get_default_headers():
    return {"user-agent": f"galaxy/{VERSION}"}
