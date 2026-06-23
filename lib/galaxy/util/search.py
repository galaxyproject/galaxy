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

# Defaults for `filter_terms` used by index-search callers. A whitespace-rich
# query turns into one WHERE clause (and, pre-trigram-index, one seq scan per
# matching table) per raw term, so both floors are there to bound query cost.
DEFAULT_MIN_RAW_TERM_LENGTH = 4
DEFAULT_MAX_RAW_TERMS = 7


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


def filter_terms(
    parsed: "ParsedSearch",
    min_raw_term_length: int = DEFAULT_MIN_RAW_TERM_LENGTH,
    max_raw_terms: Optional[int] = DEFAULT_MAX_RAW_TERMS,
) -> "ParsedSearch":
    """Return a new ParsedSearch with short / excess raw text terms dropped.

    Raw (unquoted, non-keyed) terms shorter than ``min_raw_term_length`` are
    dropped, and the surviving raw terms are capped at ``max_raw_terms``.
    Filtered terms (``key:value``) and quoted raw terms ('foo bar') are
    always kept — those are explicit user intent.
    """
    out = ParsedSearch()
    raw_kept = 0
    for term in parsed.terms:
        if isinstance(term, RawTextTerm) and not term.quoted:
            if len(term.text) < min_raw_term_length:
                continue
            if max_raw_terms is not None and raw_kept >= max_raw_terms:
                continue
            raw_kept += 1
            out.add_unfiltered_text(term.text, term.quoted)
        elif isinstance(term, RawTextTerm):
            out.add_unfiltered_text(term.text, term.quoted)
        else:
            out.add_keyed_term(term.filter, term.text, term.quoted)
    return out


__all__ = (
    "DEFAULT_MAX_RAW_TERMS",
    "DEFAULT_MIN_RAW_TERM_LENGTH",
    "filter_terms",
    "parse_filters",
    "parse_filters_structured",
)
