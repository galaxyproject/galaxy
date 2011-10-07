"""
Mixins for parsing web form and API parameters
"""
from galaxy import util

class BaseParamParser( object ):
    def get_params( self, kwargs ):
        params = util.Params( kwargs )
        # set defaults if unset
        updates = dict( webapp = params.get( 'webapp', 'galaxy' ),
                        message = util.restore_text( params.get( 'message', '' ) ),
                        status = util.restore_text( params.get( 'status', 'done' ) ) )
        params.update( updates )
        return params

class QuotaParamParser( BaseParamParser ):
    def get_quota_params( self, kwargs ):
        params = self.get_params( kwargs )
        updates = dict( name = util.restore_text( params.get( 'name', '' ) ),
                        description = util.restore_text( params.get( 'description', '' ) ),
                        amount = util.restore_text( params.get( 'amount', '' ).strip() ),
                        operation = params.get( 'operation', '' ),
                        default = params.get( 'default', '' ),
                        in_users = util.listify( params.get( 'in_users', [] ) ),
                        out_users = util.listify( params.get( 'out_users', [] ) ),
                        in_groups = util.listify( params.get( 'in_groups', [] ) ),
                        out_groups = util.listify( params.get( 'out_groups', [] ) ) )
        params.update( updates )
        return params
