"""
Contains administrative functions
"""
import logging
from galaxy import util
from galaxy.exceptions import *

log = logging.getLogger( __name__ )

class AdminActions( object ):
    """
    Mixin for controllers that provide administrative functionality.
    """
    def _create_quota( self, params ):
        if params.amount.lower() in ( 'unlimited', 'none', 'no limit' ):
            create_amount = None
        else:
            try:
                create_amount = util.size_to_bytes( params.amount )
            except AssertionError:
                create_amount = False
        if not params.name or not params.description:
            raise MessageException( "Enter a valid name and a description.", type='error' )
        elif self.sa_session.query( self.app.model.Quota ).filter( self.app.model.Quota.table.c.name==params.name ).first():
            raise MessageException( "Quota names must be unique and a quota with that name already exists, so choose another name.", type='error' )
        elif not params.get( 'amount', None ):
            raise MessageException( "Enter a valid quota amount.", type='error' )
        elif create_amount is False:
            raise MessageException( "Unable to parse the provided amount.", type='error' )
        elif params.operation not in self.app.model.Quota.valid_operations:
            raise MessageException( "Enter a valid operation.", type='error' )
        elif params.default != 'no' and params.default not in self.app.model.DefaultQuotaAssociation.types.__dict__.values():
            raise MessageException( "Enter a valid default type.", type='error' )
        elif params.default != 'no' and params.operation != '=':
            raise MessageException( "Operation for a default quota must be '='.", type='error' )
        elif create_amount is None and params.operation != '=':
            raise MessageException( "Operation for an unlimited quota must be '='.", type='error' )
        else:
            # Create the quota
            quota = self.app.model.Quota( name=params.name, description=params.description, amount=create_amount, operation=params.operation )
            self.sa_session.add( quota )
            # If this is a default quota, create the DefaultQuotaAssociation
            if params.default != 'no':
                self.app.quota_agent.set_default_quota( params.default, quota )
            else:
                # Create the UserQuotaAssociations
                for user in [ self.sa_session.query( self.app.model.User ).get( x ) for x in params.in_users ]:
                    uqa = self.app.model.UserQuotaAssociation( user, quota )
                    self.sa_session.add( uqa )
                # Create the GroupQuotaAssociations
                for group in [ self.sa_session.query( self.app.model.Group ).get( x ) for x in params.in_groups ]:
                    gqa = self.app.model.GroupQuotaAssociation( group, quota )
                    self.sa_session.add( gqa )
            self.sa_session.flush()
            message = "Quota '%s' has been created with %d associated users and %d associated groups." % \
                      ( quota.name, len( params.in_users ), len( params.in_groups ) )
            return quota, message

    def _rename_quota( self, quota, params ):
        if not params.name:
            raise MessageException( 'Enter a valid name', type='error' )
        elif params.name != quota.name and self.sa_session.query( self.app.model.Quota ).filter( self.app.model.Quota.table.c.name==params.name ).first():
            raise MessageException( 'A quota with that name already exists', type='error' )
        else:
            old_name = quota.name
            quota.name = params.name
            quota.description = params.description
            self.sa_session.add( quota )
            self.sa_session.flush()
            message = "Quota '%s' has been renamed to '%s'" % ( old_name, params.name )
            return message

    def _manage_users_and_groups_for_quota( self, quota, params ):
        if quota.default:
            raise MessageException( 'Default quotas cannot be associated with specific users and groups', type='error' )
        else:
            in_users = [ self.sa_session.query( self.app.model.User ).get( x ) for x in util.listify( params.in_users ) ]
            in_groups = [ self.sa_session.query( self.app.model.Group ).get( x ) for x in util.listify( params.in_groups ) ]
            self.app.quota_agent.set_entity_quota_associations( quotas=[ quota ], users=in_users, groups=in_groups )
            self.sa_session.refresh( quota )
            message = "Quota '%s' has been updated with %d associated users and %d associated groups" % ( quota.name, len( in_users ), len( in_groups ) )
            return message

    def _edit_quota( self, quota, params ):
        if params.amount.lower() in ( 'unlimited', 'none', 'no limit' ):
            new_amount = None
        else:
            try:
                new_amount = util.size_to_bytes( params.amount )
            except AssertionError:
                new_amount = False
        if not params.amount:
            raise MessageException( 'Enter a valid amount', type='error' )
        elif new_amount is False:
            raise MessageException( 'Unable to parse the provided amount', type='error' )
        elif params.operation not in self.app.model.Quota.valid_operations:
            raise MessageException( 'Enter a valid operation', type='error' )
        else:
            quota.amount = new_amount
            quota.operation = params.operation
            self.sa_session.add( quota )
            self.sa_session.flush()
            message = "Quota '%s' is now '%s'" % ( quota.name, quota.operation + quota.display_amount )
            return message

    def _set_quota_default( self, quota, params ):
        if params.default != 'no' and params.default not in self.app.model.DefaultQuotaAssociation.types.__dict__.values():
            raise MessageException( 'Enter a valid default type.', type='error' )
        else:
            if params.default != 'no':
                self.app.quota_agent.set_default_quota( params.default, quota )
                message = "Quota '%s' is now the default for %s users" % ( quota.name, params.default )
            else:
                if quota.default:
                    message = "Quota '%s' is no longer the default for %s users." % ( quota.name, quota.default[0].type )
                    for dqa in quota.default:
                        self.sa_session.delete( dqa )
                    self.sa_session.flush()
                else:
                    message = "Quota '%s' is not a default." % quota.name
            return message

    def _unset_quota_default( self, quota, params ):
        if not quota.default:
            raise MessageException( "Quota '%s' is not a default." % quota.name, type='error' )
        else:
            message = "Quota '%s' is no longer the default for %s users." % ( quota.name, quota.default[0].type )
            for dqa in quota.default:
                self.sa_session.delete( dqa )
            self.sa_session.flush()
            return message

    def _mark_quota_deleted( self, quota, params ):
        quotas = util.listify( quota )
        names = []
        for q in quotas:
            if q.default:
                names.append( q.name )
        if len( names ) == 1:
            raise MessageException( "Quota '%s' is a default, please unset it as a default before deleting it" % ( names[0] ), type='error' )
        elif len( names ) > 1:
            raise MessageException( "Quotas are defaults, please unset them as defaults before deleting them: " + ', '.join( names ), type='error' )
        message = "Deleted %d quotas: " % len( quotas )
        for q in quotas:
            q.deleted = True
            self.sa_session.add( q )
            names.append( q.name )
        self.sa_session.flush()
        message += ', '.join( names )
        return message

    def _undelete_quota( self, quota, params ):
        quotas = util.listify( quota )
        names = []
        for q in quotas:
            if not q.deleted:
                names.append( q.name )
        if len( names ) == 1:
            raise MessageException( "Quota '%s' has not been deleted, so it cannot be undeleted." % ( names[0] ), type='error' )
        elif len( names ) > 1:
            raise MessageException( "Quotas have not been deleted so they cannot be undeleted: " + ', '.join( names ), type='error' )
        message = "Undeleted %d quotas: " % len( quotas )
        for q in quotas:
            q.deleted = False
            self.sa_session.add( q )
            names.append( q.name )
        self.sa_session.flush()
        message += ', '.join( names )
        return message
        
    def _purge_quota( self, quota, params ):
        # This method should only be called for a Quota that has previously been deleted.
        # Purging a deleted Quota deletes all of the following from the database:
        # - UserQuotaAssociations where quota_id == Quota.id
        # - GroupQuotaAssociations where quota_id == Quota.id
        quotas = util.listify( quota )
        names = []
        for q in quotas:
            if not q.deleted:
                names.append( q.name )
        if len( names ) == 1:
            raise MessageException( "Quota '%s' has not been deleted, so it cannot be purged." % ( names[0] ), type='error' )
        elif len( names ) > 1:
            raise MessageException( "Quotas have not been deleted so they cannot be undeleted: " + ', '.join( names ), type='error' )
        message = "Purged %d quotas: " % len( quotas )
        for q in quotas:
            # Delete UserQuotaAssociations
            for uqa in q.users:
                self.sa_session.delete( uqa )
            # Delete GroupQuotaAssociations
            for gqa in q.groups:
                self.sa_session.delete( gqa )
            names.append( q.name )
        self.sa_session.flush()
        message += ', '.join( names )
        return message
