"""Module for searching the toolshed repositories"""
import datetime
import dateutil.relativedelta
from galaxy import exceptions
from galaxy import eggs
from galaxy.web.base.controller import BaseAPIController
from galaxy.webapps.tool_shed import model
from tool_shed.util.shed_util_common import generate_sharable_link_for_repository_in_tool_shed
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
        name = TEXT( field_boost = 1.7 ),
        description = TEXT( field_boost = 1.5 ),
        long_description = TEXT,
        repo_type = TEXT,
        homepage_url = TEXT,
        remote_repository_url = TEXT,
        repo_owner_username = TEXT,
        times_downloaded = STORED )

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

        maxhits = 300
        hitcount = searcher.stored_fields( docnum )[ "times_downloaded" ]
        log.debug( 'hitcount: ' + str( hitcount ) )

        # Multiply the computed score for this document by the popularity
        return score * ( hitcount / maxhits )


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
                                                                'repo_owner_username' : 0.3,
                                                                'repo_type_B' : 0.1 } )

                    # log.debug(repo_weighting.__dict__)
                    searcher = index.searcher( weighting = repo_weighting )

                    parser = MultifieldParser( [
                        'name',
                        'description',
                        'long_description',
                        'repo_type',
                        'homepage_url',
                        'remote_repository_url',
                        'repo_owner_username' ], schema = schema )

                    # user_query = parser.parse( search_term )
                    user_query = parser.parse( '*' + search_term + '*' )

                    hits = searcher.search( user_query, terms = True )
                    # hits = searcher.search_page( user_query, 1, pagelen = 1, terms = True )
                    log.debug( 'searching for: #' +  str( search_term ) )
                    log.debug( 'total hits: ' +  str( len( hits ) ) )
                    log.debug( 'scored hits: ' + str( hits.scored_length() ) )
                    results = {}
                    results[ 'total_results'] = len( hits )
                    results[ 'hits' ] = []
                    for hit in hits:
                        repo = trans.sa_session.query( model.Repository ).filter_by( id = hit[ 'id' ] ).one()
                        approved = 'no'
                        for review in repo.reviews:
                            if review.approved == 'yes':
                                approved = 'yes'
                                break
                        hit_dict = repo.to_dict( view = 'element', value_mapper = { 'id': trans.security.encode_id, 'user_id': trans.security.encode_id } )
                        hit_dict[ 'url'] = generate_sharable_link_for_repository_in_tool_shed( repo )

                        # Format the time since last update to be nicely readable.
                        dt1 = repo.update_time
                        dt2 = datetime.datetime.now()
                        rd = dateutil.relativedelta.relativedelta (dt2, dt1)
                        time_ago = ''
                        if rd.years > 0:
                            time_ago += str( rd.years ) + 'years'
                        if rd.months > 0:
                            time_ago += str( rd.months ) + ' months'
                        if rd.days > 0:
                            time_ago += str( rd.days ) + ' days ago'
                        hit_dict[ 'last_updated' ] =  time_ago

                        hit_dict[ 'times_downloaded' ] = repo.times_downloaded
                        hit_dict[ 'approved' ] = approved
                        results[ 'hits' ].append( {'repository':  hit_dict, 'matched_terms': hit.matched_terms() } )
                    return results
                finally:
                    searcher.close()
            else:
                raise exceptions.InternalServerError( 'The search index file is missing.' )
        else:
            raise exceptions.InternalServerError( 'Could not initialize search.' )
