<%inherit file="/base.mako"/>

<%def name="body()">
    <%
        center_url = h.url_for(controller='admin', action='center' )
    %>
    <iframe name="galaxy_main" id="galaxy_main" frameborder="0" style="position: absolute; width: 75%; height: 100%;" src="${center_url}"> </iframe>
</%def>
