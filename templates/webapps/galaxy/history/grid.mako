<%inherit file="../grid_base.mako"/>

<%def name="load()">
    ${parent.load()}
    <br/>
    <div class="toolParamHelp" style="clear: both;">
        Histories that have been deleted for more than a time period specified by the Galaxy administrator(s) may be permanently deleted.
    </div>
</%def>
