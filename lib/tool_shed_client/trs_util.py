from typing import NamedTuple


class EncodedIdentifier(NamedTuple):
    tool_shed_base: str
    encoded_id: str


# TRS specified encoding/decoding according to...
# https://datatracker.ietf.org/doc/html/rfc3986#section-2.4
# Failed to get whole tool shed IDs working with FastAPI
# - https://github.com/tiangolo/fastapi/issues/791#issuecomment-742799299
# - urllib.parse.quote(identifier, safe='') will produce the URL fragements but
#   but FastAPI eat them.


def decode_identifier(tool_shed_base: str, quoted_tool_id: str) -> str:
    suffix = "/".join(quoted_tool_id.split("~"))
    return f"{tool_shed_base}/repos/{suffix}"


def encode_identifier(identifier: str) -> EncodedIdentifier:
    base, rest = identifier.split("/repos/", 1)
    return EncodedIdentifier(base, "~".join(rest.split("/")))
