<%!
    def inherit(context):
        if context.get('webapp'):
            webapp = context.get('webapp')
        else:
            webapp = 'galaxy'
        return '/webapps/%s/base_panels.mako' % webapp
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
    %if message:
        ${render_msg( message, status )}
    %endif
</%def>