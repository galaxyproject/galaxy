
## ============================================================================
<%def name="bootstrap( **kwargs )">
    ## 1) Bootstap all kwargs to json, assigning to:
    ##      global 'bootstrapped' var
    ##      named require module 'bootstrapped-data'
    ## 2) and automatically include json for config and user in bootstapped data
    <%
        kwargs.update({
            'config'    : get_config_dict(),
            'user'      : get_user_dict(),
        })
    %>
    <script type="text/javascript">
        //TODO: global...
        %for key in kwargs:
            ( window.bootstrapped = window.bootstrapped || {} )[ '${key}' ] = (
                ${ h.dumps( kwargs[ key ], indent=( 2 if trans.debug else 0 ) )} );
        %endfor
        define( 'bootstrapped-data', function(){
            return window.bootstrapped;
        });
    </script>
</%def>

<%def name="load( app=None, **kwargs )">
    ## 1) bootstrap kwargs (as above), 2) build Galaxy global var, 3) load 'app' by AMD (optional)
    ${ self.bootstrap( **kwargs ) }
    <script type="text/javascript">
        require([ 'require', 'galaxy-app-base' ], function( require, galaxy ){
            //TODO: global...
            window.Galaxy = new galaxy.GalaxyApp({
                root            : '${h.url_for( "/" )}',
                //TODO: get these options from the server
                loggerOptions   : {}
            });

            %if app:
                require([ '${app}' ]);
            %endif
        });
    </script>
</%def>


## ----------------------------------------------------------------------------
<%def name="get_config_dict()">
    ## Return a dictionary of galaxy.ini settings
    <%
        config_dict = {}
        try:
            if 'configuration' in trans.webapp.api_controllers:
                config_dict = ( trans.webapp.api_controllers[ 'configuration' ]
                    .get_config_dict( trans.app.config, trans.user_is_admin() ) )
        except Exception, exc:
            pass
            
        return config_dict
    %>
</%def>

<%def name="get_config_json()">
    ## Conv. fn to write as JSON
${ h.dumps( get_config_dict() )}
</%def>


## ----------------------------------------------------------------------------
<%def name="get_user_dict()">
    ## Return a dictionary of user or anonymous user data including:
    ##  email, id, disk space used, quota percent, and tags used
    <%
        user_dict = {}
        try:
            if trans.user:
                user_dict = trans.user.to_dict( view='element',
                    value_mapper={ 'id': trans.security.encode_id, 'total_disk_usage': float } )
                user_dict[ 'quota_percent' ] = trans.app.quota_agent.get_percent( trans=trans )

                # tags used
                users_api_controller = trans.webapp.api_controllers[ 'users' ]
                user_dict[ 'tags_used' ] = users_api_controller.get_user_tags_used( trans, user=trans.user )
                user_dict[ 'is_admin' ] = trans.user_is_admin()
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

        except Exception, exc:
            pass

        return user_dict
    %>
</%def>

<%def name="get_user_json()">
    ## Conv. fn to write as JSON
${ h.dumps( get_user_dict() )}
</%def>
