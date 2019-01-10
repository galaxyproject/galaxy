<%inherit file="/base.mako"/>

<%def name="javascript_app()">
    <!-- no_access.mako javascript_app() -->
    ${parent.javascript_app()}
    <script type="text/javascript">
        config.addInitialization(function() {
            if ( parent.force_left_panel ) {
                parent.force_left_panel( 'hide' );
            }
            if ( parent.force_right_panel ) {
                parent.force_right_panel( 'hide' );
            }
        });
    </script>
</%def>

<div class="errormessage">${message}</div>
