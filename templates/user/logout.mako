%if trans.webapp.name == 'galaxy':
    <%inherit file="/webapps/galaxy/base_panels.mako"/>
%elif trans.webapp.name == 'tool_shed':
    <%inherit file="/webapps/tool_shed/base_panels.mako"/>
%endif

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