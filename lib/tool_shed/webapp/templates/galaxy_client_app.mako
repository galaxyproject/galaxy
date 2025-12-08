<%def name="load( app=None, **kwargs )">
    <script type="text/javascript">
        var options = {
            root: '${h.url_for( "/" )}',
            session_csrf_token: '${ trans.session_csrf_token }'
        };
    </script>
</%def>
