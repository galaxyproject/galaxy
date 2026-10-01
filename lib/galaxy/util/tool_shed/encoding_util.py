import binascii
import json
from typing import Any

from galaxy.util import (
    smart_str,
    unicodify,
)
from galaxy.util.hash_util import hmac_new

encoding_sep = "__esep__"
encoding_sep2 = "__esepii__"


def tool_shed_decode(value: Any) -> Any:
    # Extract and verify hash
    value_as_str = unicodify(value)
    a, b = value_as_str.split(":")
    unhexlified_b = binascii.unhexlify(b)
    test = hmac_new(b"ToolShedAndGalaxyMustHaveThisSameKey", unhexlified_b)
    assert a == test
    # Restore from string
    values = None
    value = unicodify(unhexlified_b)
    try:
        values = json.loads(value)
    except Exception:
        pass
    if values is None:
        values = value
    return values


def tool_shed_encode(val: bytes | str | Any) -> str:
    if not isinstance(val, (bytes, str)):
        val = json.dumps(val)
    a = hmac_new(b"ToolShedAndGalaxyMustHaveThisSameKey", val)
    b = unicodify(binascii.hexlify(smart_str(val)))
    return f"{a}:{b}"
