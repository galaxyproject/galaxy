import hashlib
import json


def build_tool_hash(as_dict):
    # http://stackoverflow.com/a/22003440
    as_str = json.dumps(as_dict, sort_keys=True)

    m = hashlib.sha256()
    m.update(as_str)
    hash = m.hexdigest()
    return hash
