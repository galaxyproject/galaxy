"""
Galaxy Quotas

"""
import logging, socket, operator
from datetime import datetime, timedelta
from galaxy import util
from galaxy.util.bunch import Bunch
from galaxy.model.orm import *

log = logging.getLogger(__name__)

class NoQuotaAgent( object ):
    """Base quota agent, always returns no quota"""
    def __init__( self, model ):
        self.model = model
        self.sa_session = model.context
    def get_quota( self, user, nice_size=False ):
        return None
    @property
    def default_quota( self ):
        return None
    def get_usage( self, trans=None, user=False, history=False ):
        if trans:
            user = trans.user
            history = trans.history
        assert user is not False, "Could not determine user."
        if not user:
            assert history, "Could not determine anonymous user's history."
            usage = history.get_disk_size()
        else:
            usage = user.total_disk_usage
        return usage
    def get_percent( self, trans=None, user=False, history=False, usage=False, quota=False ):
        return None
    def get_user_quotas( self, user ):
        return []

class QuotaAgent( NoQuotaAgent ):
    """Class that handles galaxy quotas"""
    def get_quota( self, user, nice_size=False ):
        """
        Calculated like so:
            1. Anonymous users get the default quota.
            2. Logged in users start with the highest of their associated '='
               quotas or the default quota, if there are no associated '='
               quotas.  If an '=' unlimited (-1 in the database) quota is found
               during this process, the user has no quota (aka unlimited).
            3. Quota is increased or decreased by any corresponding '+' or '-'
               quotas.
        """
        if not user:
            return self.default_unregistered_quota
        quotas = []
        for group in [ uga.group for uga in user.groups ]:
            for quota in [ gqa.quota for gqa in group.quotas ]:
                if quota not in quotas:
                    quotas.append( quota )
        for quota in [ uqa.quota for uqa in user.quotas ]:
            if quota not in quotas:
                quotas.append( quota )
        use_default = True
        max = 0
        adjustment = 0
        rval = 0
        for quota in quotas:
            if quota.deleted:
                continue
            if quota.operation == '=' and quota.bytes == -1:
                rval = None
                break
            elif quota.operation == '=':
                use_default = False
                if quota.bytes > max:
                    max = quota.bytes
            elif quota.operation == '+':
                adjustment += quota.bytes
            elif quota.operation == '-':
                adjustment -= quota.bytes
        if use_default:
            max = self.default_registered_quota
            if max is None:
                rval = None
        if rval is not None:
            rval = max + adjustment
            if rval <= 0:
                rval = 0
        if nice_size:
            if rval is not None:
                rval = util.nice_size( rval )
            else:
                rval = 'unlimited'
        return rval
    @property
    def default_unregistered_quota( self ):
        return self._default_quota( self.model.DefaultQuotaAssociation.types.UNREGISTERED )
    @property
    def default_registered_quota( self ):
        return self._default_quota( self.model.DefaultQuotaAssociation.types.REGISTERED )
    def _default_quota( self, default_type ):
        dqa = self.sa_session.query( self.model.DefaultQuotaAssociation ).filter( self.model.DefaultQuotaAssociation.table.c.type==default_type ).first()
        if not dqa:
            return None
        if dqa.quota.bytes < 0:
            return None
        return dqa.quota.bytes
    def set_default_quota( self, default_type, quota ):
        # Unset the current default(s) associated with this quota, if there are any
        for dqa in quota.default:
            self.sa_session.delete( dqa )
        # Unset the current users/groups associated with this quota
        for uqa in quota.users:
            self.sa_session.delete( uqa )
        for gqa in quota.groups:
            self.sa_session.delete( gqa )
        # Find the old default, assign the new quota if it exists
        dqa = self.sa_session.query( self.model.DefaultQuotaAssociation ).filter( self.model.DefaultQuotaAssociation.table.c.type==default_type ).first()
        if dqa:
            dqa.quota = quota
        # Or create if necessary
        else:
            dqa = self.model.DefaultQuotaAssociation( default_type, quota )
        self.sa_session.add( dqa )
        self.sa_session.flush()
    def get_percent( self, trans=None, user=False, history=False, usage=False, quota=False ):
        if trans:
            user = trans.user
            history = trans.history
        if quota is False:
            quota = self.get_quota( user )
        if quota is None:
            return None
        if usage is False:
            usage = self.get_usage( trans, user, history )
        percent = int( float( usage ) / quota * 100 )
        if percent > 100:
            percent = 100
        return percent
    def set_entity_quota_associations( self, quotas=[], users=[], groups=[], delete_existing_assocs=True ):
        for quota in quotas:
            if delete_existing_assocs:
                flush_needed = False
                for a in quota.users + quota.groups:
                    self.sa_session.delete( a )
                    flush_neeeded = True
                if flush_needed:
                    self.sa_session.flush()
            for user in users:
                uqa = self.model.UserQuotaAssociation( user, quota )
                self.sa_session.add( uqa )
            for group in groups:
                gqa = self.model.GroupQuotaAssociation( group, quota )
                self.sa_session.add( gqa )
            self.sa_session.flush()
    def get_user_quotas( self, user ):
        rval = []
        if not user:
            dqa = self.sa_session.query( self.model.DefaultQuotaAssociation ) \
                                 .filter( self.model.DefaultQuotaAssociation.table.c.type==self.model.DefaultQuotaAssociation.types.UNREGISTERED ).first()
            if dqa:
                rval.append( dqa.quota )
        else:
            dqa = self.sa_session.query( self.model.DefaultQuotaAssociation ) \
                                 .filter( self.model.DefaultQuotaAssociation.table.c.type==self.model.DefaultQuotaAssociation.types.REGISTERED ).first()
            if dqa:
                rval.append( dqa.quota )
            for uqa in user.quotas:
                rval.append( uqa.quota )
            for group in [ uga.group for uga in user.groups ]:
                for gqa in group.quotas:
                    rval.append( gqa.quota )
        return rval
