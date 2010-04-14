"""
Galaxy Community Space Security
"""
import logging, socket, operator
from datetime import datetime, timedelta
from galaxy.util.bunch import Bunch
from galaxy.util import listify
from galaxy.model.orm import *

log = logging.getLogger(__name__)

class Action( object ):
    def __init__( self, action, description, model ):
        self.action = action
        self.description = description
        self.model = model

class RBACAgent:
    """Class that handles galaxy community space security"""
    permitted_actions = Bunch()
    def get_action( self, name, default=None ):
        """Get a permitted action by its dict key or action name"""
        for k, v in self.permitted_actions.items():
            if k == name or v.action == name:
                return v
        return default
    def get_actions( self ):
        """Get all permitted actions as a list of Action objects"""
        return self.permitted_actions.__dict__.values()
    def get_item_actions( self, action, item ):
        raise 'No valid method of retrieving action (%s) for item %s.' % ( action, item )
    def create_private_user_role( self, user ):
        raise "Unimplemented Method"
    def get_private_user_role( self, user ):
        raise "Unimplemented Method"
    def convert_permitted_action_strings( self, permitted_action_strings ):
        """
        When getting permitted actions from an untrusted source like a
        form, ensure that they match our actual permitted actions.
        """
        return filter( lambda x: x is not None, [ self.permitted_actions.get( action_string ) for action_string in permitted_action_strings ] )

class CommunityRBACAgent( RBACAgent ):
    def __init__( self, model, permitted_actions=None ):
        self.model = model
        if permitted_actions:
            self.permitted_actions = permitted_actions
    @property
    def sa_session( self ):
        """Returns a SQLAlchemy session"""
        return self.model.context

    def allow_action( self, roles, action, item ):
        """
        Method for checking a permission for the current user ( based on roles ) to perform a
        specific action on an item
        """
        item_actions = self.get_item_actions( action, item )
        if not item_actions:
            return action.model == 'restrict'
        ret_val = False
        for item_action in item_actions:
            if item_action.role in roles:
                ret_val = True
                break
        return ret_val
    def get_item_actions( self, action, item ):
        # item must be one of: Dataset, Library, LibraryFolder, LibraryDataset, LibraryDatasetDatasetAssociation
        return [ permission for permission in item.actions if permission.action == action.action ]
    def create_private_user_role( self, user ):
        # Create private role
        role = self.model.Role( name=user.email, description='Private Role for ' + user.email, type=self.model.Role.types.PRIVATE )
        self.sa_session.add( role )
        self.sa_session.flush()
        # Add user to role
        self.associate_components( role=role, user=user )
        return role
    def get_private_user_role( self, user, auto_create=False ):
        role = self.sa_session.query( self.model.Role ) \
                              .filter( and_( self.model.Role.table.c.name == user.email, 
                                             self.model.Role.table.c.type == self.model.Role.types.PRIVATE ) ) \
                              .first()
        if not role:
            if auto_create:
                return self.create_private_user_role( user )
            else:
                return None
        return role

def get_permitted_actions( filter=None ):
    '''Utility method to return a subset of RBACAgent's permitted actions'''
    if filter is None:
        return RBACAgent.permitted_actions
    tmp_bunch = Bunch()
    [ tmp_bunch.__dict__.__setitem__(k, v) for k, v in RBACAgent.permitted_actions.items() if k.startswith( filter ) ]
    return tmp_bunch
