"""API for searching the toolshed repositories"""
from galaxy import exceptions
from galaxy import eggs
from galaxy import util
from galaxy.web import _future_expose_api_raw_anonymous_and_sessionless as expose_api_raw_anonymous_and_sessionless
from galaxy.web.base.controller import BaseAPIController
from galaxy.webapps.tool_shed.search.repo_search import RepoSearch
from galaxy.web import url_for
import json

import logging
log = logging.getLogger( __name__ )


class SearchController ( BaseAPIController ):

    @expose_api_raw_anonymous_and_sessionless
    def search( self, trans, search_term, **kwd ):
        """ 
        Perform a search over the Whoosh index. 
        The index has to be pre-created with build_ts_whoosh_index.sh.
        TS config option toolshed_search_on has to be turned on and
        whoosh_index_dir has to be specified.

        :param search_term:   (required)the term to search
        :type  search_term:   str

        :param page:          (optional)requested page of the search
        :type  page:          int

        :param jsonp:         (optional)flag whether to use jsonp format response, defaults to False
        :type  jsonp:         bool

        :param callback:      (optional)name of the function to wrap callback in
                              used only when jsonp is true, defaults to 'callback'
        :type  callback:      str

        :returns dict:        object containing list of results and a hostname
        """
        if not self.app.config.toolshed_search_on:
            raise exceptions.ConfigDoesNotAllowException( 'Searching the TS through the API is turned off for this instance.' )
        if not self.app.config.whoosh_index_dir:
            raise exceptions.ConfigDoesNotAllowException( 'There is no directory for the search index specified. Please ontact the administrator.' )
        search_term = search_term.strip()
        if len( search_term ) < 3:
            raise exceptions.RequestParameterInvalidException( 'The search term has to be at least 3 characters long.' )

        page = kwd.get( 'page', 1 )
        return_jsonp = util.asbool( kwd.get( 'jsonp', False ) )
        callback = kwd.get( 'callback', 'callback' )

        repo_search = RepoSearch()
        results = repo_search.search( trans, search_term, page )
        results[ 'hostname' ] = url_for( '/', qualified = True )

        if return_jsonp:
            response = str( '%s(%s);' % ( callback, json.dumps( results ) ) )
        else:
            response = json.dumps( results )
        return response
