import logging
import os

from galaxy import util
from galaxy import web
from galaxy.exceptions import RequestParameterMissingException
from galaxy.exceptions import AdminRequiredException
from galaxy.web import require_admin as require_admin
from galaxy.web import _future_expose_api as expose_api
from galaxy.web import _future_expose_api_anonymous as expose_api_anonymous
from galaxy.web import _future_expose_api_anonymous_and_sessionless as expose_api_anonymous_and_sessionless
from galaxy.web.base.controller import BaseAPIController
from tool_shed.managers import groups
import tool_shed.util.shed_util_common as suc

log = logging.getLogger( __name__ )


class GroupsController( BaseAPIController ):
    """RESTful controller for interactions with groups in the Tool Shed."""

    def __init__( self, app ):
        super( GroupsController, self ).__init__( app )
        self.group_manager = groups.GroupManager()

    def __get_value_mapper( self, trans ):
        value_mapper = { 'id' : trans.security.encode_id }
        return value_mapper

    @expose_api_anonymous_and_sessionless
    def index( self, trans, deleted=False, **kwd ):
        """
        GET /api/groups
        Return a list of dictionaries that contain information about each Group.
        
        :param deleted: flag used to include deleted groups

        Example: GET localhost:9009/api/groups
        """
        model = trans.app.model
        group_dicts = []
        deleted = util.asbool( deleted )
        if deleted and not trans.user_is_admin():
            raise AdminRequiredException( 'Only administrators can query deleted groups.' )
        for group in self.group_manager.list( trans ):
            group_dict = group.to_dict( view='collection', value_mapper=self.__get_value_mapper( trans ) )
            group_members = []
            for uga in group.users:
                member = ( trans.sa_session.query( model.User ).filter( model.User.table.c.id == uga.user_id ).one() )
                member_repositories = []
                for repo in trans.sa_session.query( model.Repository ) \
                                   .filter( model.Repository.table.c.user_id == uga.user_id ) \
                                   .join( model.RepositoryMetadata.table ) \
                                   .join( model.User.table ) \
                                   .outerjoin( model.RepositoryCategoryAssociation.table ) \
                                   .outerjoin( model.Category.table ):
                    member_repositories.append( { 'name': repo.name, 'times_downloaded': repo.times_downloaded } )

                member_dict = { 'username' : member.username, 'repositories': member_repositories }
                group_members.append( member_dict )
            group_dict[ 'members' ] = group_members
            group_dicts.append( group_dict )
        return group_dicts

    @expose_api
    @require_admin
    def create( self, trans, payload, **kwd ):
        """
        POST /api/groups
        Return a dictionary of information about the created group.
        The following parameters are included in the payload:

        :param name (required): the name of the group
        :param description (optional): the description of the group

        Example: POST /api/groups/?key=XXXYYYXXXYYY
        Content-Disposition: form-data; name="name" Group_Name
        Content-Disposition: form-data; name="description" Group_Description
        """
        group_dict = dict( message = '', status = 'ok' )
        name = payload.get( 'name', '' )
        if name:
            description = payload.get( 'description', '' )
            if not description:
                description = ''
            # TODO check existence
            # if suc.get_category_by_name( trans.app, name ):
                # raise exceptions.Conflict( 'A category with that name already exists.' )
            else:
                # Create the group
                group = trans.app.model.Group( name=name, description=description )
                trans.sa_session.add( category )
                trans.sa_session.flush()
                group_dict = group.to_dict( view='element',
                                                  value_mapper=self.__get_value_mapper( trans ) )
        else:
            raise RequestParameterMissingException( 'Missing required parameter "name".' )
        return group_dict

    @expose_api_anonymous_and_sessionless
    def show( self, trans, id, **kwd ):
        """
        GET /api/groups/{encoded_group_id}
        Return a dictionary of information about a group.

        :param id: the encoded id of the Group object
        
        Example: GET localhost:9009/api/groups/f9cad7b01a472135
        """
        # TODO write get group utility function
        group = suc.get_group( trans.app, id )
        if group is None:
            group_dict = dict( message = 'Unable to locate group record for id %s.' % ( str( id ) ), status = 'error' )
            return group_dict
        group_dict = group.to_dict( view='element', value_mapper=self.__get_value_mapper( trans ) )
        return group_dict


