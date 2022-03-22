import re
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

TERM_PATTERN = re.compile(r"https?://edamontology.org/(.*)")


class ParsedBiotoolsEntry:
    """Provide XML wrapper relevant entities from a bio.tool entry - topics and operations."""

    biotoolsID: str
    edam_topics: List[str]
    edam_operations: List[str]


class BiotoolsEntry:
    """Parse the RAW entries of interest for Galaxy from a bio.tools entry."""

    biotoolsID: str
    topic: List[dict]
    function: List[dict]

    @staticmethod
    def from_json(from_json: Dict[str, Any]) -> "BiotoolsEntry":
        entry = BiotoolsEntry()
        entry.biotoolsID = from_json["biotoolsID"]
        entry.topic = from_json["topic"]
        entry.function = from_json["function"]
        return entry

    @property
    def edam_info(self) -> ParsedBiotoolsEntry:
        parsed = ParsedBiotoolsEntry()
        parsed.biotoolsID = self.biotoolsID
        parsed.edam_topics = list(set(simplify_edam_dicts(self.topic)))
        operations = []
        for function in self.function:
            if "operation" in function:
                operations.extend(simplify_edam_dicts(function["operation"]))
        parsed.edam_operations = list(set(operations))
        return parsed


def simplify_edam_dicts(a_list: List[Dict[str, str]]):
    terms = []
    for term in map(simplify_edam_dict, a_list):
        if term:
            terms.append(term)
    return terms


def simplify_edam_dict(as_dict: Dict[str, str]) -> Optional[str]:
    uri = as_dict["uri"]
    match = TERM_PATTERN.match(uri)
    if match:
        return match.group(1)
    else:
        # TODO: log problem...
        return None
