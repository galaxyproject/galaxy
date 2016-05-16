<%inherit file="/base.mako"/>

<%def name="javascripts()">
    ${parent.javascripts()}
    <script type="text/javascript">
        if ( parent.force_left_panel ) {
            parent.force_left_panel( 'hide' );
        }
        if ( parent.force_right_panel ) {
            parent.force_right_panel( 'hide' );
        }
    </script>
</%def>

<div class="errormessage">${message}</div>
