import json
from galaxy.tools.deps.commands import which


def find_engine(config):
    nodejs_path = getattr(config, "nodejs_path", None)
    if nodejs_path is None:
        nodejs_path = which("nodejs") or which("node") or None
    return nodejs_path


def jshead(engine_config, root_vars):
    return "\n".join(engine_config + ["var %s = %s;" % (k, json.dumps(v)) for k, v in root_vars.items()])
