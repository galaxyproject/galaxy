<%!
#This is a hack, we should restructure templates to avoid this.
def inherit(context):
    if context.get('trans').webapp.name == 'galaxy':
        return '/webapps/galaxy/base_panels.mako'
    elif context.get('trans').webapp.name == 'tool_shed':
        return '/webapps/tool_shed/base_panels.mako'
    else:
        return '/base.mako'
%>

<%inherit file="${inherit(context)}"/>

<%namespace file="/message.mako" import="render_msg" />

<%def name="init()">
<%
    self.has_left_panel=False
    self.has_right_panel=False
    self.message_box_visible=False
    self.active_view="user"
    self.overlay_visible=False
%>
</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}
    <style>
        div#center {
            padding: 10px;
        }
    </style>
</%def>

<%def name="title()">Galaxy :: Logout</%def>

<%def name="center_panel()">
    ${self.body()}
</%def>

<%def name="body()">
    <script type="text/javascript">
        $(function(){
            //HACK: should happen before we get to this page - _before_ logged out of session
            if( top.Galaxy && top.Galaxy.user ){
                top.Galaxy.user.clearSessionStorage();
            }
        });
    </script>
    %if message:
        ${render_msg( message, status )}
    %endif
</%def>
