<%inherit file="/base_panels.mako"/>

<%def name="init()">
<%
    self.has_left_panel=False
    self.has_right_panel=False
    self.active_view="user"
    self.overlay_visible=False
%>
</%def>


<%def name="center_panel()">

    <div class="unified-panel-header" unselectable="on">
        <div class="unified-panel-header-inner">
            ${page.user.username} / ${page.title}
        </div>
    </div>

    <div class="unified-panel-body">
        <div style="overflow: auto; height: 100%;">
        <div class="page text-content" style="padding: 10px;">
        ${page.latest_revision.content.decode( "utf-8" )}
        </div>
        </div>
    </div>

</%def>
