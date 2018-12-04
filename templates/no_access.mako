<%inherit file="/base.mako"/>

<%def name="javascripts()">
    <!-- no_access.mako javascripts() -->
    ${parent.javascripts()}
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
