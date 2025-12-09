<%def name="render_msg( msg, status='done' )">
    <%
        from galaxy.util.sanitize_html import sanitize_html
        if status == "done":
            status = "success"
        elif status == "error":
            status = "danger"
        if status not in ("danger", "info", "success", "warning"):
            status = "info"
    %>
    <div class="message mt-2 alert alert-${status}">${sanitize_html(msg)}</div>
</%def>

<!DOCTYPE HTML>
<html lang="en">
    <head>
        ${ h.dist_css('base') }
    </head>
    <body>
        ${ render_msg( message, status) }
    </body>
</html>
