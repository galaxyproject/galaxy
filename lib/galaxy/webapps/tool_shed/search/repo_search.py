"""Module for searching the toolshed repositories"""
import logging
import re
import sys

import whoosh.index
from whoosh import scoring
from whoosh.fields import KEYWORD, Schema, STORED, TEXT
from whoosh.qparser import MultifieldParser
from whoosh.query import And, Term

from galaxy import exceptions
from galaxy.exceptions import ObjectNotFound

if sys.version_info > (3,):
    long = int

RESERVED_SEARCH_TERMS = ["category", "owner"]
log = logging.getLogger(__name__)

schema = Schema(
    id=STORED,
    name=TEXT(field_boost=1.7, stored=True),
    description=TEXT(field_boost=1.5, stored=True),
    long_description=TEXT(stored=True),
    homepage_url=TEXT(stored=True),
    remote_repository_url=TEXT(stored=True),
    repo_owner_username=TEXT(stored=True),
    categories=KEYWORD(stored=True, commas=True, scorable=True),
    times_downloaded=STORED,
    approved=STORED,
    last_updated=STORED,
    repo_lineage=STORED,
    full_last_updated=STORED)


class RepoWeighting(scoring.BM25F):
    """
    Affect the BM25G scoring model through the final method.
    source: https://groups.google.com/forum/#!msg/whoosh/1AKNbW8R_l8/XySW0OecH6gJ
    """
    use_final = True

    def final(self, searcher, docnum, score):
        # Arbitrary for now
        reasonable_hits = 100.0

        stored_times_downloaded = searcher.stored_fields(docnum)["times_downloaded"]
        if not isinstance(stored_times_downloaded, (int, long)):
            times_downloaded = int(stored_times_downloaded)
        else:
            times_downloaded = stored_times_downloaded
        # Add 1 to prevent 0 being divided
        if times_downloaded == 0:
            times_downloaded = 1
        popularity_modifier = (times_downloaded / reasonable_hits)

        cert_modifier = 2 if searcher.stored_fields(docnum)["approved"] == 'yes' else 1

        # Adjust the computed score for this document by the popularity
        # and by the certification level.
        final_score = score * popularity_modifier * cert_modifier
        return final_score


class RepoSearch(object):

    def search(self, trans, search_term, page, page_size, boosts):
        """
        Perform the search on the given search_term

        :param search_term: unicode encoded string with the search term(s)
        :param boosts: namedtuple containing custom boosts for searchfields, see api/repositories.py
        :param page_size: integer defining a length of one page
        :param page: integer with the number of page requested

        :returns results: dictionary containing hits themselves and the number of hits
        """
        whoosh_index_dir = trans.app.config.whoosh_index_dir
        index_exists = whoosh.index.exists_in(whoosh_index_dir)
        if index_exists:
            index = whoosh.index.open_dir(whoosh_index_dir)
            try:
                # Some literature about BM25F:
                # http://trec.nist.gov/pubs/trec13/papers/microsoft-cambridge.web.hard.pdf
                # http://en.wikipedia.org/wiki/Okapi_BM25
                # __Basically__ the higher number the bigger weight.
                repo_weighting = RepoWeighting(field_B={'name_B' : boosts.repo_name_boost,
                                                        'description_B' : boosts.repo_description_boost,
                                                        'long_description_B' : boosts.repo_long_description_boost,
                                                        'homepage_url_B' : boosts.repo_homepage_url_boost,
                                                        'remote_repository_url_B' : boosts.repo_remote_repository_url_boost,
                                                        'repo_owner_username_B' : boosts.repo_owner_username_boost,
                                                        'categories_B' : boosts.categories_boost})

                searcher = index.searcher(weighting=repo_weighting)

                allow_query, search_term_without_filters = self._parse_reserved_filters(search_term)

                parser = MultifieldParser([
                    'name',
                    'description',
                    'long_description',
                    'homepage_url',
                    'remote_repository_url',
                    'repo_owner_username',
                    'categories'], schema=schema)
                user_query = parser.parse('*' + search_term_without_filters + '*')

                try:
                    hits = searcher.search_page(user_query, page, pagelen=page_size, filter=allow_query, terms=True)
                except ValueError:
                    raise ObjectNotFound('The requested page does not exist.')

                log.debug('user search query: #' + str(search_term))
                log.debug('term without filters: #' + str(search_term_without_filters))
                log.debug('total hits: ' + str(len(hits)))
                log.debug('scored hits: ' + str(hits.scored_length()))
                results = {}
                results['total_results'] = str(len(hits))
                results['page'] = str(page)
                results['page_size'] = str(page_size)
                results['hits'] = []
                for hit in hits:
                    log.debug('matched terms: ' + str(hit.matched_terms()))
                    hit_dict = {}
                    hit_dict['id'] = trans.security.encode_id(hit.get('id'))
                    hit_dict['repo_owner_username'] = hit.get('repo_owner_username')
                    hit_dict['name'] = hit.get('name')
                    hit_dict['long_description'] = hit.get('long_description')
                    hit_dict['remote_repository_url'] = hit.get('remote_repository_url')
                    hit_dict['homepage_url'] = hit.get('homepage_url')
                    hit_dict['description'] = hit.get('description')
                    hit_dict['last_updated'] = hit.get('last_updated')
                    hit_dict['full_last_updated'] = hit.get('full_last_updated')
                    hit_dict['repo_lineage'] = hit.get('repo_lineage')
                    hit_dict['categories'] = hit.get('categories')
                    hit_dict['approved'] = hit.get('approved')
                    hit_dict['times_downloaded'] = hit.get('times_downloaded')
                    results['hits'].append({'repository': hit_dict, 'score': hit.score})
                return results
            finally:
                searcher.close()
        else:
            raise exceptions.InternalServerError('The search index file is missing.')

    def _parse_reserved_filters(self, search_term):
        """
        Support github-like filters for narrowing the results.
        Order of chunks does not matter, only recognized
        filter names are allowed.

        :param search_term: the original search str from user input

        :returns allow_query: whoosh Query object used for filtering
            results of searching in index
        :returns search_term_without_filters: str that represents user's
            search phrase without the wildcards

        >>> rs = RepoSearch()
        >>> rs._parse_reserved_filters("category:assembly")
        (And([Term('categories', 'assembly')]), '')
        >>> rs._parse_reserved_filters("category:assembly abyss")
        (And([Term('categories', 'assembly')]), 'abyss')
        >>> rs._parse_reserved_filters("category:'Climate Analysis' psy_maps")
        (And([Term('categories', 'Climate Analysis')]), 'psy_maps')
        >>> rs._parse_reserved_filters("climate category:'Climate Analysis' owner:'bjoern gruening' psy_maps")
        (And([Term('categories', 'Climate Analysis'), Term('repo_owner_username', 'bjoern gruening')]), 'climate psy_maps')
        >>> rs._parse_reserved_filters("abyss category:assembly")
        (And([Term('categories', 'assembly')]), 'abyss')
        >>> rs._parse_reserved_filters("abyss category:assembly greg")
        (And([Term('categories', 'assembly')]), 'abyss greg')
        >>> rs._parse_reserved_filters("owner:greg")
        (And([Term('repo_owner_username', 'greg')]), '')
        >>> rs._parse_reserved_filters("owner:greg category:assembly abyss")
        (And([Term('repo_owner_username', 'greg'), Term('categories', 'assembly')]), 'abyss')
        >>> rs._parse_reserved_filters("meaningoflife:42")
        (None, 'meaningoflife:42')
        """
        allow_query = None
        allow_terms = []
        # Split query string on spaces that are not followed by <anytext>singlequote_space_
        # to allow for quoting filtering values. Also unify double and single quotes into single quotes.
        search_term_chunks = re.split(r"\s+(?!\w+'\s)", search_term.replace('"', "'"), re.MULTILINE)
        reserved_terms = []
        for term_chunk in search_term_chunks:
            if ":" in term_chunk:
                reserved_filter = term_chunk.split(":")[0]
                # Remove the quotes used for delimiting values with space(s)
                reserved_filter_value = term_chunk.split(":")[1].replace("'", "")
                if reserved_filter in RESERVED_SEARCH_TERMS:
                    reserved_terms.append(term_chunk)
                    if reserved_filter == "category":
                        allow_terms.append(Term('categories', reserved_filter_value))
                    elif reserved_filter == "owner":
                        allow_terms.append(Term('repo_owner_username', reserved_filter_value))
                else:
                    pass  # Treat unrecognized filter as normal search term.
        if allow_terms:
            allow_query = And(allow_terms)
            search_term_without_filters = " ".join([chunk for chunk in search_term_chunks if chunk not in reserved_terms])
        else:
            search_term_without_filters = search_term
        return allow_query, search_term_without_filters
