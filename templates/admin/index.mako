<%inherit file="/base_panels.mako"/>

<%def name="init()">
<%
    self.has_left_panel=True
    self.has_right_panel=False
    self.active_view="admin"
%>
</%def>

<%def name="stylesheets()">

    ${parent.stylesheets()}    

    ## TODO: Clean up these styles and move into panel_layout.css (they are
    ## used here and in the editor).

    <style type="text/css">
    
    #left {
        background: #C1C9E5 url(${h.url_for('/static/style/menu_bg.png')}) top repeat-x;
    }
    
    div.toolMenu {
        margin: 5px;
        margin-left: 10px;
        margin-right: 10px;
    }
    div.toolSectionPad {
        margin: 0;
        padding: 0;
        height: 5px;
        font-size: 0px;
    }
    div.toolSectionDetailsInner { 
        margin-left: 5px;
        margin-right: 5px;
    }
    div.toolSectionTitle {
        padding-bottom: 0px;
        font-weight: bold;
    }
    div.toolMenuGroupHeader {
        font-weight: bold;
        padding-top: 0.5em;
        padding-bottom: 0.5em;
        color: #333;
        font-style: italic;
        border-bottom: dotted #333 1px;
        margin-bottom: 0.5em;
    }    
    div.toolTitle {
        padding-top: 5px;
        padding-bottom: 5px;
        margin-left: 16px;
        margin-right: 10px;
        display: list-item;
        list-style: square outside;
    }
    a:link, a:visited, a:active
    {
        color: #303030;
    }


    </style>
</%def>

<%def name="left_panel()">
    <div class="unified-panel-header" unselectable="on">
        <div class='unified-panel-header-inner'>Administration</div>
    </div>
    <div class="unified-panel-body" style="overflow: auto;">
        <div class="toolMenu">
            <div class="toolSectionList">
                <div class="toolSectionTitle">
                  <span>Security</span>
                </div>
                <div class="toolSectionBody">
                  <div class="toolSectionBg">
                    <div class="toolTitle"><a href="${h.url_for( controller='admin', action='users' )}" target="galaxy_main">Manage users</a></div>
                    <div class="toolTitle"><a href="${h.url_for( controller='admin', action='groups' )}" target="galaxy_main">Manage groups</a></div>
                    <div class="toolTitle"><a href="${h.url_for( controller='admin', action='roles' )}" target="galaxy_main">Manage roles</a></div>
                  </div>
                </div>
                <div class="toolSectionPad"></div>
                <div class="toolSectionTitle">
                  <span>Data</span>
                </div>
                <div class="toolSectionBody">
                  <div class="toolSectionBg">
                    <div class="toolTitle"><a href="${h.url_for( controller='admin', action='browse_libraries' )}" target="galaxy_main">Manage data libraries</a></div>
                  </div>
                </div>
                <div class="toolSectionPad"></div>
                <div class="toolSectionTitle">
                  <span>Server</span>
                </div>
                <div class="toolSectionBody">
                  <div class="toolSectionBg">
                    <div class="toolTitle"><a href="${h.url_for( controller='admin', action='reload_tool' )}" target="galaxy_main">Reload a tool's configuration</a></div>
                    <div class="toolTitle"><a href="${h.url_for( controller='admin', action='memdump' )}" target="galaxy_main">Profile memory usage</a></div>
                    <div class="toolTitle"><a href="${h.url_for( controller='admin', action='jobs' )}" target="galaxy_main">Manage jobs</a></div>
                  </div>
                </div>
                <div class="toolSectionPad"></div>
                <div class="toolSectionTitle">
                  <span>Forms</span>
                </div>
                <div class="toolSectionBody">
                  <div class="toolSectionBg">
                    <div class="toolTitle"><a href="${h.url_for( controller='forms', action='manage' )}" target="galaxy_main">Manage forms</a></div>
                  </div>
                </div>
                <div class="toolSectionPad"></div>
                <div class="toolSectionTitle">
                  <span>Sequencing Requests</span>
                </div>
                <div class="toolSectionBody">
                  <div class="toolSectionBg">
                    <div class="toolTitle"><a href="${h.url_for( controller='admin', action='manage_request_types' )}" target="galaxy_main">Manage request types</a></div>
                    <div class="toolTitle"><a href="${h.url_for( controller='requests_admin', action='list')}" target="galaxy_main">Manage requests</a></div>
                  </div>
                </div>
				<div class="toolSectionTitle">
                  <span>Cloud</span>
                </div>
				<div class="toolSectionBody">
                  <div class="toolSectionBg">
				  	<div class="toolTitle"><a href="${h.url_for( controller='cloud', action='list_machine_images' )}" target="galaxy_main">List machine images</a></div>
                    <div class="toolTitle"><a href="${h.url_for( controller='cloud', action='add_new_image' )}" target="galaxy_main">Add machine image</a></div>
                  </div>
                </div>
            </div>
        </div>    
    </div>
    ##<iframe name="galaxy_admin" src="${h.url_for( controller='admin', action='index' )}" frameborder="0" style="position: absolute; margin: 0; border: 0 none; height: 100%; width: 100%;"> </iframe>
</%def>

<%def name="center_panel()">
    <%
        center_url = h.url_for( action='center' )
    %>
    <iframe name="galaxy_main" id="galaxy_main" frameborder="0" style="position: absolute; width: 100%; height: 100%;" src="${center_url}"> </iframe>

</%def>
