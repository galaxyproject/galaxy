<%inherit file="/sharing_base.mako"/>

<%def name="init()">
<%
    parent.init()
    self.active_view="workflow"
%>
</%def>

<%def name="center_panel()">
    ${parent.body()}
</%def>

