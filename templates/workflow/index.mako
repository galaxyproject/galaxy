<%inherit file="/base_panels.mako"/>

<%def name="init()">
<%
    self.has_left_panel=False
    self.has_right_panel=False
    self.active_view="workflow"
    self.message_box_visible=True
    self.message_box_class="warning"
%>
</%def>

<%def name="message_box_content()">
    Workflow support is currently in <b><i>beta</i></b> testing.
    Workflows may not work with all tools, may fail unexpectedly, and may
    not be compatible with future updates to <b>Galaxy</b>.
</%def>

<%def name="center_panel()">

    <iframe name="galaxy_main" id="galaxy_main" frameborder="0" style="position: absolute; width: 100%; height: 100%;" src="${h.url_for( controller="workflow", action="list" )}"> </iframe>

</%def>