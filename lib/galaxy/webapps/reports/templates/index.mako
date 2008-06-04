<%inherit file="/base_panels.mako"/>
<%def name="center_panel()">
  ## Display the reports in the middle frame
  <%
    center_url = h.url_for( 'main_frame' )
  %>
  <iframe name="main_frame" id="main_frame" frameborder="0" style="position: absolute; width: 100%; height: 100%;" src="${center_url}"> </iframe>
</%def>
