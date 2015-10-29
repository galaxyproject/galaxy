"""Module for searching the toolshed repositories"""
from galaxy import exceptions
from galaxy.exceptions import ObjectNotFound
import logging
log = logging.getLogger( __name__ )

import whoosh.index
from whoosh import scoring
from whoosh.fields import Schema, STORED, TEXT
from whoosh.qparser import MultifieldParser

schema = Schema(
    id=STORED,
    name=TEXT( field_boost=1.7, stored=True ),
    description=TEXT( field_boost=1.5, stored=True ),
    long_description=TEXT( stored=True ),
    homepage_url=TEXT( stored=True ),
    remote_repository_url=TEXT( stored=True ),
    repo_owner_username=TEXT( stored=True ),
    times_downloaded=STORED,
    approved=STORED,
    last_updated=STORED,
    full_last_updated=STORED )


class RepoWeighting( scoring.BM25F ):
    """
    Affect the BM25G scoring model through the final method.
    source: https://groups.google.com/forum/#!msg/whoosh/1AKNbW8R_l8/XySW0OecH6gJ
    """
    use_final = True

    def final( self, searcher, docnum, score ):
        # Arbitrary for now
        reasonable_hits = 100.0

        stored_times_downloaded = searcher.stored_fields( docnum )[ "times_downloaded" ]
        if not isinstance( stored_times_downloaded, ( int, long ) ):
            times_downloaded = int( stored_times_downloaded )
        else:
            times_downloaded = stored_times_downloaded
        # Add 1 to prevent 0 being divided
        if times_downloaded == 0:
            times_downloaded = 1
        popularity_modifier = ( times_downloaded / reasonable_hits )

        cert_modifier = 2 if searcher.stored_fields( docnum )[ "approved" ] == 'yes' else 1

        # Adjust the computed score for this document by the popularity
        # and by the certification level.
        final_score = score * popularity_modifier * cert_modifier
        return final_score


class RepoSearch( object ):

    def search( self, trans, search_term, page, page_size, boosts ):
        """
        Perform the search on the given search_term

        :param search_term: unicode encoded string with the search term(s)
        :param boosts: namedtuple containing custom boosts for searchfields, see api/repositories.py

        :returns results: dictionary containing number of hits, hits themselves and matched terms for each
        """
        whoosh_index_dir = trans.app.config.whoosh_index_dir
        index_exists = whoosh.index.exists_in( whoosh_index_dir )
        if index_exists:
            index = whoosh.index.open_dir( whoosh_index_dir )
            try:
                # Some literature about BM25F:
                # http://trec.nist.gov/pubs/trec13/papers/microsoft-cambridge.web.hard.pdf
                # http://en.wikipedia.org/wiki/Okapi_BM25
                # __Basically__ the higher number the bigger weight.
                repo_weighting = RepoWeighting( field_B={ 'name_B' : boosts.repo_name_boost,
                                                          'description_B' : boosts.repo_description_boost,
                                                          'long_description_B' : boosts.repo_long_description_boost,
                                                          'homepage_url_B' : boosts.repo_homepage_url_boost,
                                                          'remote_repository_url_B' : boosts.repo_remote_repository_url_boost,
                                                          'repo_owner_username' : boosts.repo_owner_username_boost } )

                searcher = index.searcher( weighting=repo_weighting )

                parser = MultifieldParser( [
                    'name',
                    'description',
                    'long_description',
                    'homepage_url',
                    'remote_repository_url',
                    'repo_owner_username' ], schema=schema )

                user_query = parser.parse( '*' + search_term + '*' )

                try:
                    hits = searcher.search_page( user_query, page, pagelen=page_size, terms=True )
                except ValueError:
                    raise ObjectNotFound( 'The requested page does not exist.' )

                log.debug( 'searching for: #' + str( search_term ) )
                log.debug( 'total hits: ' + str( len( hits ) ) )
                log.debug( 'scored hits: ' + str( hits.scored_length() ) )
                results = {}
                results[ 'total_results'] = str( len( hits ) )
                results[ 'page'] = str( page )
                results[ 'page_size'] = str( page_size )
                results[ 'hits' ] = []
                for hit in hits:
                    hit_dict = {}
                    hit_dict[ 'id' ] = trans.security.encode_id( hit.get( 'id' ) )
                    hit_dict[ 'repo_owner_username' ] = hit.get( 'repo_owner_username' )
                    hit_dict[ 'name' ] = hit.get( 'name' )
                    hit_dict[ 'long_description' ] = hit.get( 'long_description' )
                    hit_dict[ 'remote_repository_url' ] = hit.get( 'remote_repository_url' )
                    hit_dict[ 'homepage_url' ] = hit.get( 'homepage_url' )
                    hit_dict[ 'description' ] = hit.get( 'description' )
                    hit_dict[ 'last_updated' ] = hit.get( 'last_updated' )
                    hit_dict[ 'full_last_updated' ] = hit.get( 'full_last_updated' )
                    hit_dict[ 'approved' ] = hit.get( 'approved' )
                    hit_dict[ 'times_downloaded' ] = hit.get( 'times_downloaded' )
                    results[ 'hits' ].append( {'repository': hit_dict, 'matched_terms': hit.matched_terms(), 'score': hit.score } )
                return results
            finally:
                searcher.close()
        else:
            raise exceptions.InternalServerError( 'The search index file is missing.' )
