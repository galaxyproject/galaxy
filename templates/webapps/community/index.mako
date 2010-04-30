<%inherit file="/webapps/community/base_panels.mako"/>
<%namespace file="/message.mako" import="render_msg" />

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

<%def name="init()">
    <%
    	self.has_left_panel=True
    	self.has_right_panel=False
    	self.active_view="tools"
    %>
    %if trans.app.config.require_login and not trans.user:
        <script type="text/javascript">
            if ( window != top ) {
                top.location.href = location.href;
            }
        </script>
    %endif
</%def>

<%def name="left_panel()">
    <div class="unified-panel-header" unselectable="on">
        <div class='unified-panel-header-inner'>Community</div>
    </div>
    <div class="page-container" style="padding: 10px;">
        <div class="toolMenu">
            <div class="toolSectionList">
                <div class="toolSectionPad"></div>
                <div class="toolSectionTitle">
                  <span>Tools</span>
                </div>
                <div class="toolSectionBody">
                    <div class="toolSectionBg">
                        <div class="toolTitle"><a target="galaxy_main" href="${h.url_for( controller='tool', action='browse_categories' )}">Browse by category</a></div>
                        <div class="toolTitle"><a target="galaxy_main" href="${h.url_for( controller='tool', action='browse_tools' )}">Browse all tools</a></div>
                        %if trans.user:
                            <div class="toolTitle"><a target="galaxy_main" href="${h.url_for( controller='tool', action='browse_tools_by_user', operation='browse', id=trans.security.encode_id( trans.user.id ) )}">Browse your tools</a></div>
                        %endif
                    </div>
                </div>
                <div class="toolSectionBody">
                    <div class="toolSectionBg">
                        <div class="toolTitle">
                            %if trans.user:
                                <a target="galaxy_main" href="${h.url_for( controller='upload', action='upload', type='tool' )}">Upload a tool</a>
                            %else:
                                <a target="galaxy_main" href="${h.url_for( controller='/user', action='login', webapp='community' )}">Login to upload</a>
                            %endif
                        </div>
                    </div>
                </div>
            </div>
        </div>    
    </div>
</%def>

<%def name="center_panel()">
    <%
        if trans.app.config.require_login and not trans.user:
            center_url = h.url_for( controller='user', action='login', message=message, status=status )
        else:
            center_url = h.url_for( controller='tool', action='browse_categories', message=message, status=status )
    %>
    <iframe name="galaxy_main" id="galaxy_main" frameborder="0" style="position: absolute; width: 100%; height: 100%;" src="${center_url}"> </iframe>
</%def>
