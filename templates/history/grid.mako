<%inherit file="../grid_base.mako"/>

<%def name="grid_javascripts()">
    ${parent.grid_javascripts()}
    <script type="text/javascript">
        %if refresh_frames:
            %if 'history' in refresh_frames:
                if ( parent.frames && parent.frames.galaxy_history ) {
                    parent.frames.galaxy_history.location.href="${h.url_for( controller='root', action='history')}";
                    if ( parent.force_right_panel ) {
                        parent.force_right_panel( 'show' );
                    }
                }
            %endif
        %endif
    </script>
</%def>
