"""Module for searching the toolshed repositories"""

import logging

import whoosh.index
from whoosh import scoring
from whoosh.fields import (
    KEYWORD,
    NUMERIC,
    Schema,
    STORED,
    TEXT,
)
from whoosh.qparser import MultifieldParser
from whoosh.query import (
    And,
    Every,
    Term,
)

from galaxy import exceptions
from galaxy.exceptions import ObjectNotFound
from galaxy.util.search import parse_filters

log = logging.getLogger(__name__)

schema = Schema(
    id=NUMERIC(stored=True),
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
    full_last_updated=STORED,
)


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
        if not isinstance(stored_times_downloaded, int):
            times_downloaded = int(stored_times_downloaded)
        else:
            times_downloaded = stored_times_downloaded
        # Add 1 to prevent 0 being divided
        if times_downloaded == 0:
            times_downloaded = 1
        popularity_modifier = times_downloaded / reasonable_hits

        cert_modifier = 2 if searcher.stored_fields(docnum)["approved"] == "yes" else 1

        # Adjust the computed score for this document by the popularity
        # and by the certification level.
        final_score = score * popularity_modifier * cert_modifier
        return final_score


class RepoSearch:
    def search(self, trans, search_term, page, page_size, boosts):
        """
        Perform the search on the given search_term

        :param search_term: unicode encoded string with the search term(s)
        :param boosts: namedtuple containing custom boosts for searchfields, see api/repositories.py
        :param page_size: integer defining a length of one page
        :param page: integer with the number of page requested

        :returns results: dictionary containing hits themselves and the hits summary
        """
        log.debug(f"raw search query: #{str(search_term)}")
        lower_search_term = search_term.lower()
        allow_query, search_term_without_filters = self._parse_reserved_filters(lower_search_term)
        log.debug(f"term without filters: #{str(search_term_without_filters)}")

        whoosh_index_dir = trans.app.config.whoosh_index_dir
        index_exists = whoosh.index.exists_in(whoosh_index_dir)
        if index_exists:
            index = whoosh.index.open_dir(whoosh_index_dir)
            try:
                # Some literature about BM25F:
                # http://trec.nist.gov/pubs/trec13/papers/microsoft-cambridge.web.hard.pdf
                # http://en.wikipedia.org/wiki/Okapi_BM25
                # __Basically__ the higher number the bigger weight.
                repo_weighting = RepoWeighting(
                    field_B={
                        "name_B": boosts.repo_name_boost,
                        "description_B": boosts.repo_description_boost,
                        "long_description_B": boosts.repo_long_description_boost,
                        "homepage_url_B": boosts.repo_homepage_url_boost,
                        "remote_repository_url_B": boosts.repo_remote_repository_url_boost,
                        "repo_owner_username_B": boosts.repo_owner_username_boost,
                        "categories_B": boosts.categories_boost,
                    }
                )
                searcher = index.searcher(weighting=repo_weighting)
                parser = MultifieldParser(
                    [
                        "name",
                        "description",
                        "long_description",
                        "homepage_url",
                        "remote_repository_url",
                        "repo_owner_username",
                        "categories",
                    ],
                    schema=schema,
                )

                # If user query has just filters prevent wildcard search.
                if len(search_term_without_filters) < 1:
                    user_query = Every("name")
                    sortedby = "name"
                else:
                    user_query = parser.parse(f"*{search_term_without_filters}*")
                    sortedby = ""
                try:
                    hits = searcher.search_page(
                        user_query, page, pagelen=page_size, filter=allow_query, terms=True, sortedby=sortedby
                    )
                    log.debug(f"total hits: {str(len(hits))}")
                    log.debug(f"scored hits: {str(hits.scored_length())}")
                except ValueError:
                    raise ObjectNotFound("The requested page does not exist.")
                results = {}
                results["total_results"] = str(len(hits))
                results["page"] = str(page)
                results["page_size"] = str(page_size)
                results["hits"] = []
                for hit in hits:
                    log.debug(f"matched terms: {str(hit.matched_terms())}")
                    hit_dict = {}
                    hit_dict["id"] = trans.security.encode_id(hit.get("id"))
                    hit_dict["repo_owner_username"] = hit.get("repo_owner_username")
                    hit_dict["name"] = hit.get("name")
                    hit_dict["long_description"] = hit.get("long_description")
                    hit_dict["remote_repository_url"] = hit.get("remote_repository_url")
                    hit_dict["homepage_url"] = hit.get("homepage_url")
                    hit_dict["description"] = hit.get("description")
                    hit_dict["last_updated"] = hit.get("last_updated")
                    hit_dict["full_last_updated"] = hit.get("full_last_updated")
                    hit_dict["repo_lineage"] = hit.get("repo_lineage")
                    hit_dict["categories"] = hit.get("categories")
                    hit_dict["approved"] = hit.get("approved")
                    hit_dict["times_downloaded"] = hit.get("times_downloaded")
                    results["hits"].append({"repository": hit_dict, "score": hit.score})
                return results
            finally:
                searcher.close()
        else:
            raise exceptions.InternalServerError("The search index file is missing.")

    def _parse_reserved_filters(self, search_term):
        """
        Support github-like filters for narrowing the results.
        Order of chunks does not matter, only recognized
        filter names are allowed.

        :param search_term: the original search str from user input

        :returns allow_query: whoosh Query object used for filtering
            results of searching in index
        :returns search_term_without_filters: str that represents user's
            search phrase without the filters

        >>> rs = RepoSearch()
        >>> rs._parse_reserved_filters("category:assembly")
        (And([Term('categories', 'assembly')]), '')
        >>> rs._parse_reserved_filters("category:assembly abyss")
        (And([Term('categories', 'assembly')]), 'abyss')
        >>> rs._parse_reserved_filters("category:'Climate Analysis' psy_maps")
        (And([Term('categories', 'Climate Analysis')]), 'psy_maps')
        >>> rs._parse_reserved_filters("climate category:'Climate Analysis' owner:'bjoern gruening' psy_maps")
        (And([Term('categories', 'Climate Analysis'), Term('repo_owner_username', 'bjoern gruening')]), 'climate psy_maps')
        >>> rs._parse_reserved_filters("climate category:'John Says This Fails' owner:'bjoern gruening' psy_maps")
        (And([Term('categories', 'John Says This Fails'), Term('repo_owner_username', 'bjoern gruening')]), 'climate psy_maps')
        >>> rs._parse_reserved_filters("climate o:'bjoern gruening' middle strings c:'John Says This Fails' psy_maps")
        (And([Term('repo_owner_username', 'bjoern gruening'), Term('categories', 'John Says This Fails')]), 'climate middle strings psy_maps')
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
        filters = {
            "category": "categories",
            "c": "categories",
            "owner": "repo_owner_username",
            "o": "repo_owner_username",
        }
        allow_query, search_term_without_filters = parse_filters(search_term, filters)
        allow_query = (
            And([Term(t, v) for (t, v, _) in allow_query] if len(allow_query) > 0 else None) if allow_query else None
        )
        return allow_query, search_term_without_filters
