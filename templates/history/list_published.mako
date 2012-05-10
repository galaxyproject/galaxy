<%inherit file="/webapps/galaxy/base_panels.mako"/>

<%def name="init()">
<%
    self.has_left_panel=False
    self.has_right_panel=False
    self.active_view="shared"
    self.message_box_visible=False
%>
</%def>

<%def name="title()">
    Galaxy | Published Histories
</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}
    <style>
        .grid td {
            min-width: 100px;
        }
    </style>
</%def>

<%def name="center_panel()">

    <div style="overflow: auto; height: 100%;">
        <div class="page-container" style="padding: 10px;">
            ${h.to_unicode( grid )}
        </div>
    </div>


</%def>
