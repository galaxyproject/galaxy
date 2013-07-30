<%inherit file="../grid_base.mako"/>

<%namespace file="/refresh_frames.mako" import="handle_refresh_frames" />

<%def name="grid_javascripts()">
    ${parent.grid_javascripts()}

    ${handle_refresh_frames()}
</%def>

<%def name="grid_body( grid )">
    ${self.make_grid( grid )}
    <br/>
    <div class="toolParamHelp" style="clear: both;">
        Histories that have been deleted for more than a time period specified by the Galaxy administrator(s) may be permanently deleted.
    </div>
</%def>
