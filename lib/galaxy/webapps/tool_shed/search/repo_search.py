"""Module for searching the toolshed repositories"""
import datetime
from galaxy import exceptions
from galaxy import eggs
from galaxy.webapps.tool_shed import model
import logging
log = logging.getLogger( __name__ )

# Whoosh is compatible with Python 2.5+ 
# Try to import Whoosh and set flag to indicate whether 
# the tool search is ready.
try:
    eggs.require( "Whoosh" )
    import whoosh.index
    from whoosh import scoring
    from whoosh.fields import Schema, STORED, ID, KEYWORD, TEXT, STORED
    from whoosh.scoring import BM25F
    from whoosh.qparser import MultifieldParser
    from whoosh.index import Index
    search_ready = True

    schema = Schema(
        id = STORED,
        name = TEXT( field_boost = 1.7, stored = True ),
        description = TEXT( field_boost = 1.5, stored = True ),
        long_description = TEXT( stored = True ),
        homepage_url = TEXT( stored = True ),
        remote_repository_url = TEXT( stored = True ),
        repo_owner_username = TEXT( stored = True ),
        times_downloaded = STORED,
        approved = STORED,
        last_updated = STORED,
        full_last_updated = STORED )

except ImportError, e:
    search_ready = False
    schema = None

    
class RepoWeighting( scoring.BM25F ):
    """
    Affect the BM25G scoring model through the final method.
    source: https://groups.google.com/forum/#!msg/whoosh/1AKNbW8R_l8/XySW0OecH6gJ
    """
    use_final = True

    def final( self, searcher, docnum, score ):
        log.debug('score before: ' +  str(score) )
        
        # Arbitrary for now
        reasonable_hits = 100.0
        times_downloaded = int( searcher.stored_fields( docnum )[ "times_downloaded" ] )
        # Add 1 to prevent 0 being divided
        if times_downloaded == 0:
            times_downloaded = 1
        popularity_modifier = ( times_downloaded / reasonable_hits )
        log.debug('popularity_modifier: ' +  str(popularity_modifier) )

        cert_modifier = 2 if searcher.stored_fields( docnum )[ "approved" ] == 'yes' else 1
        log.debug('cert_modifier: ' +  str(cert_modifier) )

        # Adjust the computed score for this document by the popularity
        # and by the certification level.
        final_score = score * popularity_modifier * cert_modifier
        log.debug('score after: ' +  str( final_score ) )
        return final_score


class RepoSearch( object ):

    def search( self, trans, search_term, **kwd ):
        """
        Perform the search on the given search_term

        :param search_term: unicode encoded string with the search term(s)

        :returns results: dictionary containing number of hits, hits themselves and matched terms for each
        """
        if search_ready:
            toolshed_whoosh_index_dir = trans.app.config.toolshed_whoosh_index_dir
            index_exists = whoosh.index.exists_in( toolshed_whoosh_index_dir )
            if index_exists:
                index = whoosh.index.open_dir( toolshed_whoosh_index_dir )
                try:
                    # Some literature about BM25F:
                    # http://trec.nist.gov/pubs/trec13/papers/microsoft-cambridge.web.hard.pdf
                    # http://en.wikipedia.org/wiki/Okapi_BM25
                    # __Basically__ the higher number the bigger weight.
                    repo_weighting = RepoWeighting( field_B = { 'name_B' : 0.9,
                                                                'description_B' : 0.6,
                                                                'long_description_B' : 0.5,
                                                                'homepage_url_B' : 0.3,
                                                                'remote_repository_url_B' : 0.2,
                                                                'repo_owner_username' : 0.3 } )

                    # log.debug(repo_weighting.__dict__)
                    searcher = index.searcher( weighting = repo_weighting )

                    parser = MultifieldParser( [
                        'name',
                        'description',
                        'long_description',
                        'homepage_url',
                        'remote_repository_url',
                        'repo_owner_username' ], schema = schema )

                    # user_query = parser.parse( search_term )
                    user_query = parser.parse( '*' + search_term + '*' )

                    hits = searcher.search( user_query, terms = True )
                    # hits = searcher.search( user_query )
                    # hits = searcher.search_page( user_query, 1, pagelen = 1, terms = True )
                    log.debug( 'searching for: #' +  str( search_term ) )
                    log.debug( 'total hits: ' +  str( len( hits ) ) )
                    log.debug( 'scored hits: ' + str( hits.scored_length() ) )
                    results = {}
                    results[ 'total_results'] = str( hits.scored_length() )
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
                        results[ 'hits' ].append( {'repository':  hit_dict, 'matched_terms': hit.matched_terms(), 'score': hit.score } )
                    return results
                finally:
                    searcher.close()
            else:
                raise exceptions.InternalServerError( 'The search index file is missing.' )
        else:
            raise exceptions.InternalServerError( 'Could not initialize search.' )
