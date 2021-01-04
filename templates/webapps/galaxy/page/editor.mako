<%inherit file="/webapps/galaxy/base_panels.mako"/>

<%def name="title()">
    Page Editor
</%def>

<%def name="init()">
<%
    self.active_view="user"
%>
</%def>

<%def name="javascript_app()">
    ${parent.javascript_app()}
    <script type="text/javascript">
        config.addInitialization(function(){
            console.log("editor.mako, javascript_app", "define variables needed by galaxy.pages script");
            window.bundleEntries.mountPageEditor({
                pageId: "${id}",
            });
        });
    </script>
</%def>

<%def name="left_panel()">
</%def>

<%def name="center_panel()">
</%def>

<%def name="right_panel()">
</%def>

