<%inherit file="/base.mako"/>

<%def name="javascripts()">
    ${parent.javascripts()}
    <script type="text/javascript">
        %if 'masthead' in refresh_frames:
            ## if ( parent.frames && parent.frames.galaxy_masthead ) {
            ##     parent.frames.galaxy_masthead.location.href="${h.url_for( controller='root', action='masthead')}";
            ## }
            ## else if ( parent.parent && parent.parent.frames && parent.parent.frames.galaxy_masthead ) {
            ##     parent.parent.frames.galaxy_masthead.location.href="${h.url_for( controller='root', action='masthead')}";
            ## }
            
            ## Refresh masthead == user changes (backward compatibility)
            if ( parent.user_changed ) {
                %if trans.user:
                    parent.user_changed( "${trans.user.email}", ${int( app.config.is_admin_user( trans.user ) )} );
                %else:
                    parent.user_changed( null, false );
                %endif
            }
        %endif
        %if 'history' in refresh_frames:
            if ( parent.frames && parent.frames.galaxy_history ) {
                parent.frames.galaxy_history.location.href="${h.url_for( controller='root', action='history')}";
                if ( parent.force_right_panel ) {
                    parent.force_right_panel( 'show' );
                }
            }
        %endif
        %if 'tools' in refresh_frames:
            if ( parent.frames && parent.frames.galaxy_tools ) {
                parent.frames.galaxy_tools.location.href="${h.url_for( controller='root', action='tool_menu')}";
                if ( parent.force_left_panel ) {
                    parent.force_left_panel( 'show' );
                }
            }
        %endif

        if ( parent.handle_minwidth_hint )
        {
            parent.handle_minwidth_hint( -1 );
        }
    </script>
</%def>

<div class="${message_type}message">${message}</div>

## Render a message
<%def name="render_msg( msg, messagetype='done' )">
    <div class="${messagetype}message">${msg}</div>
    <br/>
</%def>
