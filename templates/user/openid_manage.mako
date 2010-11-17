## Template generates a grid that enables user to select items.
<%namespace file="../grid_base.mako" import="make_grid" />
<%namespace file="login.mako" import="render_openid_form" />

<%inherit file="../grid_base.mako" />

<%def name="grid_body( grid )">
    ${make_grid( grid )}
    <h2>Associate more OpenIDs</h2>
    ${render_openid_form( kwargs['referer'], True, kwargs['openid_providers'] )}
</%def>

<%def name="center_panel()">
    <div style="margin: 1em;">
        ${grid_body( grid )}
    </div>
</%def>
