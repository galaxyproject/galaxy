## Template generates a grid that enables user to select items.
<%inherit file="../grid_base.mako" />

<%namespace file="login.mako" import="render_openid_form" />

<%def name="load()">
    <h2>Associate more OpenIDs</h2>
    ${render_openid_form( kwargs['redirect'], True, kwargs['openid_providers'] )}
    <br/><br/>
    ${parent.load()}
</%def>
