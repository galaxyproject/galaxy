## Template generates a grid that enables user to select items.
<%namespace file="../grid_base.mako" import="make_grid" />
<%namespace file="login.mako" import="render_openid_form" />

<%inherit file="../grid_base.mako" />

<%def name="grid_body( grid )">
    ${make_grid( grid )}
    <h2>Associate more OpenIDs</h2>
    ${render_openid_form( kwargs['redirect'], True, kwargs['openid_providers'] )}
</%def>

<%def name="center_panel()">
    <div style="overflow: auto; height: 100%">
        <div class="page-container" style="padding: 10px;">
            ${grid_body( grid )}
        </div>
    </div>
</%def>
