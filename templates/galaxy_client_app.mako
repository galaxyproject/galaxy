
## ============================================================================
<%def name="bootstrap()">
    ## Bootstap dictionaries for GalaxyApp object's JSON, create GalaxyApp,
    ##  and steal existing attributes from plain objects already created
    <%
        config_dict = {}
        if 'configuration' in trans.webapp.api_controllers:
            config_dict = ( trans.webapp.api_controllers[ 'configuration' ]
                .get_config_dict( trans.app.config, trans.user_is_admin() ) )

        user_dict = self.get_user_dict()

        # genomes
        # datatypes
    %>
    <script type="text/javascript">
        require([ 'galaxy-app-base' ], function( app ){
            galaxy = new app.GalaxyApp({
                config          : ${ h.to_json_string( config_dict ) },
                userJSON        : ${ get_user_json() },
                root            : '${h.url_for( "/" )}',
                //TODO: get these options from the server
                onload          : window.Galaxy? window.Galaxy.onload: null,
                loggerOptions   : {
                }
            });
            // in case req or plain script tag order has created a prev. version of the Galaxy obj...
            if( window.Galaxy ){
                // ...(for now) monkey patch any added attributes that the previous Galaxy may have had
                //TODO: move those attributes to more formal assignment in GalaxyApp
                for( var k in window.Galaxy ){
                    if( window.Galaxy.hasOwnProperty( k ) ){
                        galaxy.debug( 'patching in ' + k + ' to Galaxy' )
                        galaxy[ k ] = window.Galaxy[ k ];
                    }
                }
            }
            window.Galaxy = galaxy;
        });

    </script>
</%def>

## ----------------------------------------------------------------------------
<%def name="get_user_dict()">
    ## Return a dictionary of user or anonymous user data including:
    ##  email, id, disk space used, quota percent, and tags used
    <%
        if trans.user:
            user_dict = trans.user.to_dict( view='element',
                value_mapper={ 'id': trans.security.encode_id, 'total_disk_usage': float } )
            user_dict[ 'quota_percent' ] = trans.app.quota_agent.get_percent( trans=trans )

            # tags used
            users_api_controller = trans.webapp.api_controllers[ 'users' ]
            user_dict[ 'tags_used' ] = users_api_controller.get_user_tags_used( trans, user=trans.user )
            return user_dict

        usage = 0
        percent = None
        try:
            usage = trans.app.quota_agent.get_usage( trans, history=trans.history )
            percent = trans.app.quota_agent.get_percent( trans=trans, usage=usage )
        except AssertionError, assertion:
            # no history for quota_agent.get_usage assertion
            pass
        return {
            'total_disk_usage'      : int( usage ),
            'nice_total_disk_usage' : util.nice_size( usage ),
            'quota_percent'         : percent
        }
    %>
</%def>

<%def name="get_user_json()">
    ## Conv. fn to write as JSON
${ h.to_json_string( get_user_dict() )}
</%def>
