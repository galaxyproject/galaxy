<%inherit file="/webapps/galaxy/base_panels.mako"/>

<%def name="init()">
<%
    self.has_left_panel=False
    self.has_right_panel=False
    self.active_view="shared"
%>
</%def>

<%def name="center_panel()">

    <iframe name="galaxy_main" id="galaxy_main" frameborder="0" style="position: absolute; width: 100%; height: 100%;" src="${h.url_for( controller="library", action="browse_libraries", default_action=default_action )}"> </iframe>

</%def>
