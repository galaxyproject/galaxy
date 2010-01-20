<%inherit file="/base_panels.mako"/>

<%def name="init()">
<%
    self.has_left_panel=False
    self.has_right_panel=False
    self.active_view="page"
    self.message_box_visible=False
%>
</%def>

<%def name="title()">
    Galaxy :: Published Workflows
</%def>

<%def name="center_panel()">

    ## <iframe name="galaxy_main" id="galaxy_main" frameborder="0" style="position: absolute; width: 100%; height: 100%;" src="${h.url_for( controller="page", action="list" )}"> </iframe>

    <div style="overflow: auto; height: 100%;">
        <div class="page-container" style="padding: 10px;">
            ${unicode( grid, 'utf-8' )}
        </div>
    </div>


</%def>
