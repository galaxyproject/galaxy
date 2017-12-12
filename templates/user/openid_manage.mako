<%inherit file="/base.mako"/>
<%namespace file="login.mako" import="render_openid_form" />
<%def name="body()">
    <h2>Associate more OpenIDs</h2>
    ${render_openid_form( redirect, True, openid_providers )}
</%def>