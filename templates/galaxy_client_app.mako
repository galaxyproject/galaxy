<%def name="render_json( dictionary )">
${ h.dumps( dictionary, indent=( 2 if trans.debug else 0 ) ) }
</%def>

## ============================================================================

<%def name="load( app=None, **kwargs )">
    <script type="text/javascript">
        // galaxy_client_app.mako, load

        var bootstrapped;
        try {
            bootstrapped = ${render_json(kwargs)};
        } catch(err) {
            console.warn("Unable to parse bootstrapped variable", err);
            bootstrapped = {};
        }

        var options = {
            root: '${h.url_for( "/" )}',
            config: ${ render_json( get_config_dict() )},
            user: ${ render_json( get_user_dict() )},
            session_csrf_token: '${ trans.session_csrf_token }'
        };

        config.set({
            options: options,
            bootstrapped: bootstrapped
        });

        %if app:
            console.warn("Does app ever run? Is it ever not-named app?", '${app}');
        %endif

    </script>
</%def>

<%def name="config_sentry(app)">
    %if app and app.config:
        <script type="text/javascript">

            // TODO: make this work the same in all places, maybe 
            // make a global func in galaxy_client_app?
            var sentry = {};
            %if app.config.sentry_dsn:
                sentry.sentry_dsn_public = "${app.config.sentry_dsn_public}"
                %if trans.user:
                    sentry.email = "${trans.user.email|h}";
                %endif
            %endif

            config.set({
                sentry: sentry
            });

        </script>
    %endif
</%def>

<%def name="config_google_analytics(app)">
    %if app and app.config and app.config.ga_code:
        <script>
            (function(i,s,o,g,r,a,m){i['GoogleAnalyticsObject']=r;i[r]=i[r]||function(){
            (i[r].q=i[r].q||[]).push(arguments)},i[r].l=1*new Date();a=s.createElement(o),
            m=s.getElementsByTagName(o)[0];a.async=1;a.src=g;m.parentNode.insertBefore(a,m)
            })(window,document,'script','//www.google-analytics.com/analytics.js','ga');
            ga('create', '${app.config.ga_code}', 'auto');
            ga('send', 'pageview');
        </script>
    %endif
</%def>



## ----------------------------------------------------------------------------
<%def name="get_config_dict()">
    ## Return a dictionary of galaxy.ini settings
    <%
        config_dict = {}
        try:
            controller = trans.webapp.api_controllers.get( 'configuration', None )
            if controller:
                config_dict = controller.get_config_dict( trans, trans.user_is_admin )
        except Exception as exc:
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
        from markupsafe import escape
        user_dict = {}
        try:
            if trans.user:
                user_dict = trans.user.to_dict( view='element',
                    value_mapper={ 'id': trans.security.encode_id, 'total_disk_usage': float, 'email': escape, 'username': escape } )
                user_dict[ 'quota_percent' ] = trans.app.quota_agent.get_percent( trans=trans )
                user_dict[ 'is_admin' ] = trans.user_is_admin

                # tags used
                users_api_controller = trans.webapp.api_controllers[ 'users' ]
                tags_used = []
                for tag in users_api_controller.get_user_tags_used( trans, user=trans.user ):
                    tag = escape( tag )
                    if tag:
                        tags_used.append( tag )
                user_dict[ 'tags_used' ] = tags_used

                return user_dict

            usage = 0
            percent = None
            try:
                usage = trans.app.quota_agent.get_usage( trans, history=trans.history )
                percent = trans.app.quota_agent.get_percent( trans=trans, usage=usage )
            except AssertionError as assertion:
                # no history for quota_agent.get_usage assertion
                pass
            return {
                'total_disk_usage'      : int( usage ),
                'nice_total_disk_usage' : util.nice_size( usage ),
                'quota_percent'         : percent
            }

        except Exception as exc:
            pass
            #TODO: no logging available?
            #log.exception( exc )

        return user_dict
    %>
</%def>

<%def name="get_user_json()">
    ## Conv. fn to write as JSON
${ h.dumps( get_user_dict() )}
</%def>
