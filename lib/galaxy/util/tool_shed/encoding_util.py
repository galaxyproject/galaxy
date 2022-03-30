import binascii
import json

from galaxy.util import (
    smart_str,
    unicodify,
)
from galaxy.util.hash_util import hmac_new

encoding_sep = "__esep__"
encoding_sep2 = "__esepii__"


def tool_shed_decode(value):
    # Extract and verify hash
    value = unicodify(value)
    a, b = value.split(":")
    value = binascii.unhexlify(b)
    test = hmac_new(b"ToolShedAndGalaxyMustHaveThisSameKey", value)
    assert a == test
    # Restore from string
    values = None
    value = unicodify(value)
    try:
        values = json.loads(value)
    except Exception:
        pass
    if values is None:
        values = value
    return values


def tool_shed_encode(val):
    if isinstance(val, dict) or isinstance(val, list):
        value = json.dumps(val)
    else:
        value = val
    a = hmac_new(b"ToolShedAndGalaxyMustHaveThisSameKey", value)
    b = unicodify(binascii.hexlify(smart_str(value)))
    return f"{a}:{b}"
