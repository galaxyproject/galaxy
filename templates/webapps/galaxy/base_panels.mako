<%inherit file="/base/base_panels.mako"/>
<!-- webapps/galaxy/base_panels.mako -->
<%namespace name="mod_masthead" file="/webapps/galaxy/galaxy.masthead.mako"/>

## Default title
<%def name="title()"></%def>

## Masthead
<%def name="masthead()">
    <%
        mod_masthead.load(self.active_view);
    %>
</%def>
