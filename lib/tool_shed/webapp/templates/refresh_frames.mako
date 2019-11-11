## Include JavaScript code to refresh Galaxy application frames as needed.
<%def name="handle_refresh_frames()">

    ## If no refresh frames, print nothing.
    <% if not refresh_frames: return '' %>

    <script type="text/javascript">

        // TODO: I hate that we have a random globally-defined state update
        // function here but since we're about to rewrite the app container,
        // I'm not sure it's worth the headache to refactor this

        function user_changed(user_email, is_admin) {
            if ( user_email ) {
                $(".loggedin-only").show();
                $(".loggedout-only").hide();
                $("#user-email").text( user_email );
                if ( is_admin ) {
                    $(".admin-only").show();
                }
            } else {
                $(".loggedin-only").hide();
                $(".loggedout-only").show();
                $(".admin-only").hide();
            }
        }

        %if 'everything' in refresh_frames:
            config.addInitialization(function() {
                var destination = "${h.url_for( controller='root' )}";
                console.log("refresh_frames.mako, refresh everything", destination);
                parent.location.href = destination;
            });
        %endif

        %if 'masthead' in refresh_frames:
            ## Refresh masthead == user changes (backward compatibility)
    
            config.addInitialization(function(galaxy, config) {
                console.log("refresh_frames.mako, refresh masthead");
                var userEmail = "${trans.user.email | h }";
                var isAdmin = ${h.to_js_bool(app.config.is_admin_user( trans.user))};
                if (parent.user_changed) {
                    %if trans.user:
                        parent.user_changed(userEmail, isAdmin);
                    %else:
                        parent.user_changed( null, false );
                    %endif
                }
            });
        %endif

        %if 'history' in refresh_frames:
            config.addInitialization(function(galaxy) {
                console.log("refresh_frames.mako, refresh history");
                if(galaxy.currHistoryPanel){
                    galaxy.currHistoryPanel.loadCurrentHistory();
                }
            })
        %endif

        %if 'tools' in refresh_frames:
            config.addInitialization(function(galaxy) {
                console.log("refresh_frames.mako, refresh tools");
                if ( parent.frames && galaxy.toolPanel ) {
                    // FIXME: refreshing the tool menu does not work with new JS-based approach,
                    // but refreshing the tool menu is not used right now, either.
                    if (parent.force_left_panel) {
                        parent.force_left_panel('show');
                    }
                }
            });
        %endif

    </script>
</%def>
