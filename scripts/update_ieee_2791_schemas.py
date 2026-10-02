#!/usr/bin/env python3
"""Update the vendored IEEE-2791 (BioCompute Object) JSON schemas.

Fetches 2791object.json and every sibling schema it transitively ``$ref``s from
https://w3id.org/ieee/ieee-2791-schema/ and writes them verbatim to
lib/galaxy_test/base/schemas/ieee-2791/, removing vendored schemas that are no
longer referenced. After running, update the fetch date in the README next to
the schemas.
"""

import json
import urllib.request
from pathlib import Path

BASE_URL = "https://w3id.org/ieee/ieee-2791-schema/"
TOP_LEVEL_SCHEMA = "2791object.json"
DEST_DIR = Path(__file__).parent.parent / "lib" / "galaxy_test" / "base" / "schemas" / "ieee-2791"


def collect_sibling_refs(schema) -> set[str]:
    refs: set[str] = set()
    if isinstance(schema, dict):
        for key, value in schema.items():
            if key == "$ref" and isinstance(value, str):
                filename = value.split("#")[0]
                if filename.endswith(".json") and "/" not in filename:
                    refs.add(filename)
            else:
                refs.update(collect_sibling_refs(value))
    elif isinstance(schema, list):
        for item in schema:
            refs.update(collect_sibling_refs(item))
    return refs


def fetch(filename: str) -> bytes:
    # the IEEE host answers 418 to Python's default User-Agent
    request = urllib.request.Request(BASE_URL + filename, headers={"User-Agent": "curl/8"})
    with urllib.request.urlopen(request) as response:
        content = response.read()
    # the IEEE host sits behind a bot-challenge WAF that can serve HTML with a
    # 200 status; make sure we actually got JSON before vendoring it
    json.loads(content)
    return content


def main() -> None:
    fetched: dict[str, bytes] = {}
    pending = {TOP_LEVEL_SCHEMA}
    while pending:
        filename = pending.pop()
        content = fetch(filename)
        fetched[filename] = content
        pending.update(collect_sibling_refs(json.loads(content)) - fetched.keys())
    for stale_path in DEST_DIR.glob("*.json"):
        if stale_path.name not in fetched:
            stale_path.unlink()
            print(f"Removed {stale_path.name}")
    for filename, content in sorted(fetched.items()):
        (DEST_DIR / filename).write_bytes(content)
        print(f"Wrote {filename}")


if __name__ == "__main__":
    main()
