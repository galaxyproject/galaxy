<%inherit file="/webapps/galaxy/base_panels.mako"/>

<%def name="init()">
<%
    self.has_left_panel=False
    self.has_right_panel=False
    self.active_view=active_view
    self.message_box_visible=False
%>
</%def>

<%def name="center_panel()">
    <div style="overflow: auto; height: 100%;">
        <div style="padding: 10px">
            ${grid}
        </div>
    </div>
</%def>
