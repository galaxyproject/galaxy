import logging
import os

from galaxy import util
from galaxy import web
from galaxy.web.base.controller import BaseAPIController
import tool_shed.util.shed_util_common as suc

log = logging.getLogger( __name__ )


class CategoriesController( BaseAPIController ):
    """RESTful controller for interactions with categories in the Tool Shed."""

    def __get_value_mapper( self, trans ):
        value_mapper = { 'id' : trans.security.encode_id }
        return value_mapper

    @web.expose_api
    def create( self, trans, payload, **kwd ):
        """
        POST /api/categories
        Returns a dictionary of information about the created category.

:       param key: the current Galaxy admin user's API key

        The following parameters are included in the payload.
        :param name (required): the name of the category
        :param description (optional): the description of the category (if not provided, the name will be used)
        """
        category_dict = dict( message = '',
                              status = 'ok' )
        # Make sure the current user's API key proves he is an admin user in this Tool Shed.
        if trans.user_is_admin():
            # Get the information about the category to be created from the payload.
            name = payload.get( 'name', '' )
            if name:
                description = payload.get( 'description', '' )
                if not description:
                    # Default the description to the name.
                    description = name
                if suc.get_category_by_name( trans.app, name ):
                    category_dict[ 'message' ] = 'A category with that name already exists'
                    category_dict[ 'status' ] = 'error'
                else:
                    # Create the category
                    category = trans.app.model.Category( name=name, description=description )
                    trans.sa_session.add( category )
                    trans.sa_session.flush()
                    category_dict = category.to_dict( view='element',
                                                      value_mapper=self.__get_value_mapper( trans ) )
                    category_dict[ 'message' ] = "Category '%s' has been created" % str( category.name )
                    category_dict[ 'url' ] = web.url_for( controller='categories',
                                                          action='show',
                                                          id=trans.security.encode_id( category.id ) )
            else:
                category_dict[ 'message' ] = "Missing required parameter 'name'."
                category_dict[ 'status' ] = 'error'
        else:
            category_dict[ 'message' ] = 'You are not authorized to create a category in this Tool Shed.'
            category_dict[ 'status' ] = 'error'
        return category_dict

    @web.expose_api_anonymous
    def index( self, trans, deleted=False, **kwd ):
        """
        GET /api/categories
        Returns a list of dictionaries that contain information about each category.
        """
        # Example URL: http://localhost:9009/api/categories
        category_dicts = []
        deleted = util.asbool( deleted )
        for category in trans.sa_session.query( trans.app.model.Category ) \
                                        .filter( trans.app.model.Category.table.c.deleted == deleted ) \
                                        .order_by( trans.app.model.Category.table.c.name ):
            category_dict = category.to_dict( view='collection',
                                              value_mapper=self.__get_value_mapper( trans ) )
            category_dict[ 'url' ] = web.url_for( controller='categories',
                                                  action='show',
                                                  id=trans.security.encode_id( category.id ) )
            category_dicts.append( category_dict )
        return category_dicts

    @web.expose_api_anonymous
    def show( self, trans, id, **kwd ):
        """
        GET /api/categories/{encoded_category_id}
        Returns a dictionary of information about a category.

        :param id: the encoded id of the Repository object
        """
        # Example URL: http://localhost:9009/api/categories/f9cad7b01a472135
        category = suc.get_category( trans.app, id )
        if category is None:
            category_dict = dict( message = 'Unable to locate category record for id %s.' % ( str( id ) ),
                                  status = 'error' )
            return category_dict
        category_dict = category.to_dict( view='element',
                                          value_mapper=self.__get_value_mapper( trans ) )
        category_dict[ 'url' ] = web.url_for( controller='categories',
                                              action='show',
                                              id=trans.security.encode_id( category.id ) )
        return category_dict
