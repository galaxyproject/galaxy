"""
API for searching Galaxy Datasets
"""
import logging, os, string, shutil, urllib, re, socket
from cgi import escape, FieldStorage
from galaxy import util, datatypes, jobs, web, util
from galaxy.web.base.controller import *
from galaxy.util.sanitize_html import sanitize_html
from galaxy.model.orm import *
from galaxy.model.search import *


from galaxy.model import *

from sqlalchemy import or_, and_

log = logging.getLogger( __name__ )

class SearchController( BaseAPIController ):
    """
    The search API accepts a POST with a payload of:
     - search_type : The type of data to be searched, "library", "history_dataset", "history", "workflow"
     - result_fields : The fields in the return structure that should be populated, includes:
       "name", "id", "extended_metadata", "annotation", "tags"
     - query : The query structure to be used

    Example query data structures:

    Find elements such that name == "test"
    {
        "name" : "test"
    }


    Find elements such that annotation contains the work 'world'

    {
        "annotation" : { "$like" : "%world%" }
    }

    Find elements such that the extended metadata field dataSubType/@id == 'geneExp'

    {
        "extended_metadata" : {
            "dataSubType/@id" : "geneExp"
        }
    }

    """

    FIELD_NAME = "name"
    FIELD_ID = "id"
    FIELD_DOMAIN = "domain"
    FIELD_EXTENDED_METADATA = "extended_metadata"
    FIELD_ANNOTATION = "annotation"
    FIELD_TAGS = "tags"

    @web.expose_api
    def create( self, trans, payload, **kwd ):
        """
        POST /api/search
        Do a search of the various elements of Galaxy.
        """
        domains = payload.get("domain", [])
        result_fields = payload.get("result_fields", [self.FIELD_EXTENDED_METADATA])
        query = payload.get("query", {})
        print payload
        out = []
        for domain in domains:
            if domain in search_mapping:
                search_base = search_mapping[domain]()
                search_query = search_base.search(trans)
                for field in query:
                    search_field = search_base.get_field(field)
                    if search_field is not None:
                        if isinstance(query[field], dict) and '$like' in query[field]:
                            search_query.filter( search_field.like(query[field]['$like']) )
                        else:
                            search_query.filter( search_field == query[field] )
                out += list(search_query.get_results())

        return self._create_response(trans, out, result_fields)

    def _create_response(self, trans, rows, result_fields):
        current_user_roles = trans.get_current_user_roles()
        out = []
        for row in rows:
            if trans.app.security_agent.can_access_dataset( current_user_roles, row.dataset ):
                r = self.encode_all_ids( trans, row.get_api_value( view='element' ) )
                out.append(r)
        return out        
