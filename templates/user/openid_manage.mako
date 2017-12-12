<%inherit file="/base.mako"/>
<%namespace file="login.mako" import="render_openid_form" />
<%namespace file="/message.mako" import="render_msg" />
<%def name="init()">
<%
    self.has_left_panel=False
    self.has_right_panel=False
    self.message_box_visible=False
%>
</%def>
<%def name="body()">
    <h2>Associate more OpenIDs</h2>
    ${render_openid_form( redirect, True, openid_providers )}
</%def>