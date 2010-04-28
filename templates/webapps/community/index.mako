<%inherit file="/webapps/community/base_panels.mako"/>
<%namespace file="/message.mako" import="render_msg" />

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
                        <div class="toolTitle"><a href="${h.url_for( controller='tool', action='browse_tool_categories' )}" target="galaxy_main">Browse tools by category</a></div>
                        <div class="toolTitle"><a href="${h.url_for( controller='tool', action='browse_tools' )}" target="galaxy_main">Browse all tools</a></div>
                    </div>
                </div>
                <div class="toolSectionBody">
                    <div class="toolSectionBg">
                        <div class="toolTitle">
                            %if trans.user:
                                <a href="${h.url_for( controller='upload', action='upload', type='tool' )}" target="galaxy_main">Upload a tool</a>
                            %else:
                                Login to upload
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
            center_url = h.url_for( controller='tool', action='browse_tool_categories', message=message, status=status )
    %>
    <iframe name="galaxy_main" id="galaxy_main" frameborder="0" style="position: absolute; width: 100%; height: 100%;" src="${center_url}"> </iframe>
</%def>
