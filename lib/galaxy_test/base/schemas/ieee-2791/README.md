# IEEE-2791 (BioCompute Object) JSON schemas

Vendored copies of the IEEE-2791-2020 schema set, fetched verbatim on 2026-09-02 from
`https://w3id.org/ieee/ieee-2791-schema/<filename>` (which redirects to the IEEE
OpenSource hosting of https://opensource.ieee.org/2791-object/ieee-2791-schema).

Do not edit the JSON files by hand — refresh them with
`python scripts/update_ieee_2791_schemas.py` (run from the repository root), which
re-fetches the whole set by walking the `$ref`s, then update the fetch date above.

`2791object.json` is the top-level schema; it `$ref`s the sibling `*_domain.json`
files by relative URL. Tests validate BCO exports against these local copies via
`galaxy_test.base.json_schema_utils.vendored_schema_registry`, keyed by each file's
`$id`, so validation makes no network requests (the w3id.org/IEEE host sits behind a
bot-challenge WAF that intermittently blocks CI runner IPs).
