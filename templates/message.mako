<%!
    from galaxy.util.sanitize_html import sanitize_html

    def inherit(context):
        return '/base.mako'
%>
<%inherit file="${inherit(context)}"/>

<%namespace file="/refresh_frames.mako" import="handle_refresh_frames" />

<% _=n_ %>

<%def name="init()">
<%
    self.has_left_panel=False
    self.has_right_panel=False
    self.active_view=active_view
    self.message_box_visible=False
%>
</%def>

<%def name="javascript_app()">
    <!-- message.mako javascript_app() -->
    ${parent.javascript_app()}
    ${handle_refresh_frames()}
    <script type="text/javascript">
        config.addInitialization(function() {
            if (parent.handle_minwidth_hint) {
                parent.handle_minwidth_hint(-1);
            }
        });
    </script>
</%def>

##
## Override methods from base.mako
##

<%def name="center_panel()">
    ${render_msg( message, status )}
</%def>

<%def name="body()">
    ${render_msg( message, status )}
</%def>

## Render a message
<%def name="render_msg( msg, status='done' )">
    <%
        if status == "done":
            status = "success"
        elif status == "error":
            status = "danger"
        if status not in ("danger", "info", "success", "warning"):
            status = "info"
    %>
    <div class="message mt-2 alert alert-${status}">${sanitize_html(msg)}</div>
</%def>
