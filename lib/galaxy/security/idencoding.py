import codecs
import collections
import logging
from typing import (
    Optional,
    Union,
)

from Crypto.Cipher import Blowfish
from Crypto.Random import get_random_bytes

import galaxy.exceptions
from galaxy.util import (
    smart_str,
    unicodify,
)

log = logging.getLogger(__name__)

MAXIMUM_ID_SECRET_BITS = 448
MAXIMUM_ID_SECRET_LENGTH = int(MAXIMUM_ID_SECRET_BITS / 8)
KIND_TOO_LONG_MESSAGE = (
    "Galaxy coding error, keep encryption 'kinds' smaller to utilize more bites of randomness from id_secret values."
)


class IdEncodingHelper:
    def __init__(self, **config):
        id_secret = config["id_secret"]
        self.id_secret = id_secret
        self.id_cipher = Blowfish.new(smart_str(self.id_secret), mode=Blowfish.MODE_ECB)

        per_kind_id_secret_base = config.get("per_kind_id_secret_base", self.id_secret)
        self.id_ciphers_for_kind = _cipher_cache(per_kind_id_secret_base)

    def encode_id(self, obj_id, kind=None):
        if obj_id is None:
            raise galaxy.exceptions.MalformedId("Attempted to encode None id")
        id_cipher = self.__id_cipher(kind)
        # Convert to bytes
        s = smart_str(obj_id)
        # Pad to a multiple of 8 with leading "!"
        s = (b"!" * (8 - len(s) % 8)) + s
        # Encrypt
        return unicodify(codecs.encode(id_cipher.encrypt(s), "hex"))

    def encode_dict_ids(self, a_dict, kind=None, skip_startswith=None):
        """
        Encode all ids in dictionary. Ids are identified by (a) an 'id' key or
        (b) a key that ends with '_id'
        """
        for key, val in a_dict.items():
            if key == "id" or key.endswith("_id") and (skip_startswith is None or not key.startswith(skip_startswith)):
                a_dict[key] = self.encode_id(val, kind=kind)

        return a_dict

    def encode_all_ids(self, rval, recursive=False):
        """
        Encodes all integer values in the dict rval whose keys are 'id' or end
        with '_id' excluding `tool_id` which are consumed and produced as is
        via the API.
        """
        if not isinstance(rval, dict):
            return rval
        for k, v in rval.items():
            if (k == "id" or k.endswith("_id")) and v is not None and k not in ["tool_id", "external_id"]:
                try:
                    rval[k] = self.encode_id(v)
                except Exception:
                    pass  # probably already encoded
            if k.endswith("_ids") and isinstance(v, list):
                try:
                    o = []
                    for i in v:
                        o.append(self.encode_id(i))
                    rval[k] = o
                except Exception:
                    pass
            else:
                if recursive and isinstance(v, dict):
                    rval[k] = self.encode_all_ids(v, recursive)
                elif recursive and isinstance(v, list):
                    rval[k] = [self.encode_all_ids(el, True) for el in v]
        return rval

    def decode_id(self, obj_id, kind=None, object_name: Optional[str] = None):
        try:
            id_cipher = self.__id_cipher(kind)
            return int(unicodify(id_cipher.decrypt(codecs.decode(obj_id, "hex"))).lstrip("!"))
        except TypeError:
            raise galaxy.exceptions.MalformedId(
                f"Malformed {object_name if object_name is not None else ''} id ( {obj_id} ) specified, unable to decode."
            )
        except ValueError:
            raise galaxy.exceptions.MalformedId(
                f"Wrong {object_name if object_name is not None else ''} id ( {obj_id} ) specified, unable to decode."
            )

    def encode_guid(self, session_key):
        # Session keys are strings
        # Pad to a multiple of 8 with leading "!"
        session_key = smart_str(session_key)
        s = (b"!" * (8 - len(session_key) % 8)) + session_key
        # Encrypt
        return codecs.encode(self.id_cipher.encrypt(s), "hex")

    def decode_guid(self, session_key: Union[bytes, str]) -> str:
        # Session keys are strings
        try:
            decoded_session_key = codecs.decode(session_key, "hex")
            stripped_decoded_session_key = unicodify(self.id_cipher.decrypt(decoded_session_key)).lstrip("!")
            # Ensure session key is hexadecimal value
            int(stripped_decoded_session_key, 16)
            return stripped_decoded_session_key
        except TypeError:
            raise galaxy.exceptions.MalformedId(f"Malformed guid '{session_key!r}' specified, unable to decode.")
        except ValueError:
            raise galaxy.exceptions.MalformedId(f"Wrong guid '{session_key!r}' specified, unable to decode.")

    def get_new_guid(self):
        # Generate a unique, high entropy 128 bit random number
        return unicodify(codecs.encode(get_random_bytes(16), "hex"))

    def __id_cipher(self, kind):
        if not kind:
            id_cipher = self.id_cipher
        else:
            id_cipher = self.id_ciphers_for_kind[kind]
        return id_cipher


class _cipher_cache(collections.defaultdict):
    def __init__(self, secret_base):
        self.secret_base = secret_base

    def __missing__(self, key):
        assert len(key) < 15, KIND_TOO_LONG_MESSAGE
        secret = f"{self.secret_base}__{key}"
        return Blowfish.new(_last_bits(secret), mode=Blowfish.MODE_ECB)


def _last_bits(secret):
    """We append the kind at the end, so just use the bits at the end."""
    last_bits = smart_str(secret)
    if len(last_bits) > MAXIMUM_ID_SECRET_LENGTH:
        last_bits = last_bits[-MAXIMUM_ID_SECRET_LENGTH:]
    return last_bits
