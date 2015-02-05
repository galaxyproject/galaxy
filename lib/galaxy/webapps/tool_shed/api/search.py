"""API for searching the toolshed repositories"""
from galaxy import exceptions
from galaxy import eggs
from galaxy.web import _future_expose_api as expose_api
# from galaxy.web import _future_expose_api_anonymous as expose_api_anonymous
from galaxy.web import _future_expose_api_raw_anonymous as expose_api_raw_anonymous
from galaxy.web.base.controller import BaseAPIController
from galaxy.webapps.tool_shed.search.repo_search import RepoSearch
from galaxy.web import url_for
import json

import logging
log = logging.getLogger( __name__ )


class SearchController ( BaseAPIController ):

    @expose_api_raw_anonymous
    def search( self, trans, search_term, **kwd ):
        """ 
        Perform a search over the Whoosh index. 
        The index has to be pre-created with build_ts_whoosh_index.sh.
        TS config option toolshed_search_on has to be turned on and
        toolshed_whoosh_index_dir has to be specified and existing.
        """
        if not self.app.config.toolshed_search_on:
            raise exceptions.ConfigDoesNotAllowException( 'Searching the TS through the API is turned off for this instance.' )
        if not self.app.config.toolshed_whoosh_index_dir:
            raise exceptions.ConfigDoesNotAllowException( 'There is no directory for the search index specified. Please ontact the administrator.' )
        if len( search_term ) < 3:
            raise exceptions.RequestParameterInvalidException( 'The search term has to be at least 3 characters long.' )

        page = kwd.get( 'page', 1 )
        callback = kwd.get( 'callback', 'callback' )

        repo_search = RepoSearch()
        results = repo_search.search( trans, search_term, page )
        results[ 'hostname' ] = url_for( '/', qualified = True )
        response = '%s(%s);' % ( callback, json.dumps( results ) )
        return response
