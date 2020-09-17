from galaxy.util.commands import which


def find_engine(config):
    nodejs_path = getattr(config, "nodejs_path", None)
    if nodejs_path is None:
        nodejs_path = which("nodejs") or which("node") or None
    if nodejs_path is None:
        raise Exception("nodejs or node not found on PATH")
    return nodejs_path
