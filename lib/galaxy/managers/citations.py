import functools
import logging

import requests
from beaker.cache import CacheManager
from beaker.util import parse_cache_config_options

from galaxy.structured_app import BasicSharedApp
from galaxy.util import DEFAULT_SOCKET_TIMEOUT

log = logging.getLogger(__name__)


class CitationsManager:
    def __init__(self, app: BasicSharedApp) -> None:
        self.app = app
        self.doi_cache = DoiCache(app.config)

    def citations_for_tool(self, tool):
        return tool.citations

    def citations_for_tool_ids(self, tool_ids):
        citation_collection = CitationCollection()
        for tool_id in tool_ids:
            tool = self._get_tool(tool_id)
            for citation in self.citations_for_tool(tool):
                citation_collection.add(citation)
        return citation_collection.citations

    def parse_citation(self, citation_elem):
        return parse_citation(citation_elem, self)

    def _get_tool(self, tool_id):
        tool = self.app.toolbox.get_tool(tool_id)
        return tool


class DoiCache:
    def __init__(self, config):
        cache_opts = {
            "cache.type": getattr(config, "citation_cache_type", "file"),
            "cache.data_dir": getattr(config, "citation_cache_data_dir", None),
            "cache.lock_dir": getattr(config, "citation_cache_lock_dir", None),
        }
        self._cache = CacheManager(**parse_cache_config_options(cache_opts)).get_cache("doi")

    def _raw_get_bibtex(self, doi):
        doi_url = f"https://doi.org/{doi}"
        headers = {"Accept": "application/x-bibtex"}
        res = requests.get(doi_url, headers=headers, timeout=DEFAULT_SOCKET_TIMEOUT)
        # To decode the response content, res.text tries to determine the
        # content encoding from the Content-Type header (res.encoding), and if
        # that fails, falls back to guessing from the content itself (res.apparent_encoding).
        # The guessed encoding is sometimes wrong, better to default to utf-8.
        if res.encoding is None:
            res.encoding = "utf-8"
        return res.text

    def get_bibtex(self, doi):
        createfunc = functools.partial(self._raw_get_bibtex, doi)
        return self._cache.get(key=doi, createfunc=createfunc)


def parse_citation(elem, citation_manager):
    """
    Parse an abstract citation entry from the specified XML element.
    """
    citation_type = elem.attrib.get("type", None)
    citation_class = CITATION_CLASSES.get(citation_type, None)
    if not citation_class:
        log.warning(f"Unknown or unspecified citation type: {citation_type}")
        return None
    try:
        citation = citation_class(elem, citation_manager)
    except Exception as e:
        raise Exception(f"Invalid citation of type '{citation_type}' with content '{elem.text}': {e}")
    return citation


class CitationCollection:
    def __init__(self):
        self.citations = []

    def __iter__(self):
        return self.citations.__iter__()

    def __len__(self):
        return len(self.citations)

    def add(self, new_citation):
        for citation in self.citations:
            if citation.equals(new_citation):
                # TODO: We have two equivalent citations, pick the more
                # informative/complete/correct.
                return False

        self.citations.append(new_citation)
        return True


class BaseCitation:
    def to_dict(self, citation_format):
        if citation_format == "bibtex":
            return dict(
                format="bibtex",
                content=self.to_bibtex(),
            )
        else:
            raise Exception(f"Unknown citation format {citation_format}")

    def equals(self, other_citation):
        if self.has_doi() and other_citation.has_doi():
            return self.doi() == other_citation.doi()
        else:
            # TODO: Do a better job figuring out if this is the same citation.
            return self.to_bibtex() == other_citation.to_bibtex()

    def has_doi(self):
        return False


class BibtexCitation(BaseCitation):
    def __init__(self, elem, citation_manager):
        self.raw_bibtex = elem.text.strip()

    def to_bibtex(self):
        return self.raw_bibtex


class DoiCitation(BaseCitation):
    BIBTEX_UNSET = object()

    def __init__(self, elem, citation_manager):
        self.__doi = elem.text.strip()
        self.doi_cache = citation_manager.doi_cache
        self.raw_bibtex = DoiCitation.BIBTEX_UNSET

    def has_doi(self):
        return True

    def doi(self):
        return self.__doi

    def to_bibtex(self):
        if self.raw_bibtex is DoiCitation.BIBTEX_UNSET:
            try:
                self.raw_bibtex = self.doi_cache.get_bibtex(self.__doi)
            except Exception:
                log.exception("Failed to fetch bibtex for DOI %s", self.__doi)

        if self.raw_bibtex is DoiCitation.BIBTEX_UNSET:
            return """@MISC{{{doi},
                DOI = {{{doi}}},
                note = {{Failed to fetch BibTeX for DOI.}}
            }}""".format(
                doi=self.__doi
            )
        else:
            return self.raw_bibtex


CITATION_CLASSES = dict(
    bibtex=BibtexCitation,
    doi=DoiCitation,
)
