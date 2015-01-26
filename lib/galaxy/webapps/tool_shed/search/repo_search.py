"""Module for searching the toolshed repositories"""
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
    from whoosh.fields import Schema, STORED, ID, KEYWORD, TEXT
    from whoosh.scoring import BM25F
    from whoosh.qparser import MultifieldParser
    from whoosh.index import Index
    search_ready = True

    schema = Schema(
        id=STORED,
        name=TEXT,
        description=TEXT,
        long_description=TEXT,
        repo_type=TEXT,
        homepage_url=TEXT,
        remote_repository_url=TEXT,
        repo_owner_username=TEXT )
except ImportError, e:
    search_ready = False
    schema = None

class RepoSearch ( object ):

    def search( self, trans, search_term, **kwd ):
        """
        Perform the search on the given search_term

        :param search_term: unicode encoded string with the search term(s)

        :returns results: dictionary containing number of hits,
                            hits themselves and matched terms for each
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
                    # Basically the higher number the bigger weight.
                    searcher = index.searcher( weighting=BM25F( field_B={ 
                                                                      'name_B' : 0.9,
                                                                      'description_B' : 0.6,
                                                                      'long_description_B' : 0.5,
                                                                      'homepage_url_B' : 0.3,
                                                                      'remote_repository_url_B' : 0.2,
                                                                      'repo_owner_username' : 0.3,
                                                                      'repo_type_B' : 0.1 } ) )
                    parser = MultifieldParser( [
                    'name',
                    'description',
                    'long_description',
                    'repo_type',
                    'homepage_url',
                    'remote_repository_url',
                    'repo_owner_username' ], schema=schema )

                    hits = searcher.search( parser.parse( '*' + search_term + '*' ), terms = True )
                    results = {}
                    results[ 'length'] = len( hits )
                    results[ 'hits' ] = []
                    for hit in hits:
                        repo = trans.sa_session.query( model.Repository ).filter_by( id=hit[ 'id' ] ).one()
                        approved = 'no'
                        for review in repo.reviews:
                            if review.approved == 'yes':
                                approved = 'yes'
                                break
                        hit_dict = repo.to_dict( view='element', value_mapper={ 'id': trans.security.encode_id, 'user_id': trans.security.encode_id } )
                        hit_dict[ 'url'] = generate_sharable_link_for_repository_in_tool_shed( repo )
                        hit_dict[ 'last_updated' ] = repo.update_time.strftime( "%Y-%m-%d %I:%M %p" )
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
