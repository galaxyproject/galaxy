import re
from typing import (
    Dict,
    List,
    NamedTuple,
    Optional,
    Tuple,
    Union,
)

KeyedQueryT = Tuple[str, str]
ParseFilterResultT = Tuple[Optional[List["FilteredTerm"]], Optional[str]]
QUOTE_PATTERN = re.compile(r"\'(.*?)\'")


def parse_filters(search_term: str, filters: Optional[Dict[str, str]] = None) -> ParseFilterResultT:
    """Support github-like filters for narrowing the results.

    Order of chunks does not matter, only recognized filter names are allowed.

    :param search_term: the original search str from user input

    :returns allow_query: whoosh Query object used for filtering
        results of searching in index
    :returns search_term_without_filters: str that represents user's
        search phrase without the filters
    """
    return parse_filters_structured(search_term, filters, preserve_quotes=False).simple_result


def parse_filters_structured(
    search_term: str,
    filters: Optional[Dict[str, str]] = None,
    preserve_quotes: bool = True,
) -> "ParsedSearch":
    search_space = search_term.replace('"', "'")
    filters = filters or {}
    filter_keys = "|".join(list(filters.keys()))
    pattern = rf"({filter_keys}):(?:\s+)?([\w-]+|'.*?')(:\w+)?"
    reserved = re.compile(pattern)
    parsed_search = ParsedSearch()
    while True:
        match = reserved.search(search_space)
        if match is None:
            match = QUOTE_PATTERN.search(search_space)
            if match is None:
                parsed_search.add_unfiltered_text_terms(search_space)
                break
            group = match.groups()[0].strip()
            parsed_search.add_unfiltered_text_terms(search_space[0 : match.start()])
            parsed_search.add_unfiltered_text(group, True)
        else:
            first_group = match.groups()[0]
            if first_group in filters:
                if match.groups()[0] == "tag" and match.groups()[1] == "name" and match.groups()[2] is not None:
                    group = match.groups()[1] + match.groups()[2].strip()
                else:
                    group = match.groups()[1].strip()
                filter_as = filters[first_group]
                quoted = preserve_quotes and group.startswith("'")
                parsed_search.add_keyed_term(filter_as, group.replace("'", ""), quoted)
            parsed_search.add_unfiltered_text_terms(search_space[0 : match.start()])
        search_space = search_space[match.end() :]
    return parsed_search


class RawTextTerm(NamedTuple):
    text: str
    quoted: bool


class FilteredTerm(NamedTuple):
    filter: str
    text: str
    quoted: bool


TermT = Union[RawTextTerm, FilteredTerm]


class ParsedSearch:
    terms: List[TermT]
    text_terms: List[RawTextTerm]
    filter_terms: List[FilteredTerm]

    def __init__(self):
        self.terms = []
        self.text_terms = []
        self.filter_terms = []

    def add_unfiltered_text_terms(self, text: str):
        for part in text.split():
            self.add_unfiltered_text(part, False)

    def add_unfiltered_text(self, text: str, quoted: bool = False):
        text = text.strip()
        if not text:
            return
        term = RawTextTerm(text.strip(), quoted)
        self.terms.append(term)
        self.text_terms.append(term)

    def add_keyed_term(self, key: str, text: str, quoted: bool):
        term = FilteredTerm(key, text, quoted)
        self.terms.append(term)
        self.filter_terms.append(term)

    @property
    def simple_result(self) -> ParseFilterResultT:
        return None if len(self.filter_terms) == 0 else self.filter_terms, " ".join([t.text for t in self.text_terms])


__all__ = (
    "parse_filters",
    "parse_filters_structured",
)
