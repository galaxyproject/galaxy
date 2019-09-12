<%inherit file="/webapps/galaxy/base_panels.mako"/>

<%def name="init()">
<%
    self.has_left_panel=False
    self.has_right_panel=False
    self.active_view="user"
    self.overlay_visible=False
%>
</%def>

<%def name="javascript_app()">
    ${parent.javascript_app()}
    <script type="text/javascript">
        // Define global variables needed by galaxy.pages script.
        // Apparently pages() relies on these variables being defined
        // in window. 
        config.addInitialization(function(){
            console.log("editor.mako, javascript_app", "define variables needed by galaxy.pages script");
            window.bundleEntries.pages();
        });
    </script>
</%def>

<%def name="center_panel()">

    <span id="page-editor-content" class="inbound" page_id="${trans.security.encode_id(page.id)}">
    </span>

</%def>
