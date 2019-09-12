<%inherit file="/base.mako"/>

<%def name="javascripts()">
    <script>
        let redirectTo = '${redirect_url}';
        if (redirectTo) {
            console.log("redirecting", redirectTo);
            window.top.location.href = redirectTo;
        }
    </script>
</%def>

<%def name="javascript_app()"></%def>
<%def name="javascripts_entry()"></%def>