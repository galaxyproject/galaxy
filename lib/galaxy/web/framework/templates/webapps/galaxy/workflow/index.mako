<%inherit file="/webapps/galaxy/base_panels.mako"/>

<%def name="init()">
<%
    self.active_view="workflow"
%>
</%def>

<%def name="center_panel()">

    <iframe name="galaxy_main" id="galaxy_main" frameborder="0" style="position: absolute; width: 100%; height: 100%;" src="${h.url_for( controller="workflow", action="list" )}"> </iframe>

</%def>
