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
