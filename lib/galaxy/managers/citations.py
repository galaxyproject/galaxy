import functools
import logging
import os

import requests
from beaker.cache import CacheManager
from beaker.util import parse_cache_config_options

log = logging.getLogger(__name__)


class CitationsManager(object):

    def __init__(self, app):
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

    def parse_citation(self, citation_elem, tool_directory):
        return parse_citation(citation_elem, tool_directory, self)

    def _get_tool(self, tool_id):
        tool = self.app.toolbox.get_tool(tool_id)
        return tool


class DoiCache(object):

    def __init__(self, config):
        cache_opts = {
            'cache.type': getattr(config, 'citation_cache_type', 'file'),
            'cache.data_dir': getattr(config, 'citation_cache_data_dir', None),
            'cache.lock_dir': getattr(config, 'citation_cache_lock_dir', None),
        }
        self._cache = CacheManager(**parse_cache_config_options(cache_opts)).get_cache('doi')

    def _raw_get_bibtex(self, doi):
        doi_url = "https://doi.org/" + doi
        headers = {'Accept': 'text/bibliography; style=bibtex, application/x-bibtex'}
        req = requests.get(doi_url, headers=headers)
        return req.text

    def get_bibtex(self, doi):
        createfunc = functools.partial(self._raw_get_bibtex, doi)
        return self._cache.get(key=doi, createfunc=createfunc)


def parse_citation(elem, directory, citation_manager):
    """ Parse an abstract citation entry from the specified XML element.
    The directory parameter should be used to find external files for this
    citation.
    """
    citation_type = elem.attrib.get('type', None)
    citation_class = CITATION_CLASSES.get(citation_type, None)
    if not citation_class:
        log.warning("Unknown or unspecified citation type: %s" % citation_type)
        return None
    return citation_class(elem, directory, citation_manager)


class CitationCollection(object):

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


class BaseCitation(object):

    def to_dict(self, citation_format):
        if citation_format == "bibtex":
            return dict(
                format="bibtex",
                content=self.to_bibtex(),
            )
        else:
            raise Exception("Unknown citation format %s" % citation_format)

    def equals(self, other_citation):
        if self.has_doi() and other_citation.has_doi():
            return self.doi() == other_citation.doi()
        else:
            # TODO: Do a better job figuring out if this is the same citation.
            return self.to_bibtex() == other_citation.to_bibtex()

    def has_doi(self):
        return False


class BibtexCitation(BaseCitation):

    def __init__(self, elem, directory, citation_manager):
        bibtex_file = elem.attrib.get("file", None)
        if bibtex_file:
            raw_bibtex = open(os.path.join(directory, bibtex_file), "r").read()
        else:
            raw_bibtex = elem.text.strip()
        self._set_raw_bibtex(raw_bibtex)

    def _set_raw_bibtex(self, raw_bibtex):
        self.raw_bibtex = raw_bibtex

    def to_bibtex(self):
        return self.raw_bibtex


class DoiCitation(BaseCitation):
    BIBTEX_UNSET = object()

    def __init__(self, elem, directory, citation_manager):
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
            return """@MISC{%s,
                DOI = {%s},
                note = {Failed to fetch BibTeX for DOI.}
            }""" % (self.__doi, self.__doi)
        else:
            return self.raw_bibtex


CITATION_CLASSES = dict(
    bibtex=BibtexCitation,
    doi=DoiCitation,
)
