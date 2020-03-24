<%inherit file="/webapps/galaxy/base_panels.mako"/>

<%def name="title()">
    Workflow Editor
</%def>

<%def name="init()">
<%
    self.active_view="workflow"
    self.overlay_visible=True
%>
</%def>

<%def name="javascript_app()">
    ${parent.javascript_app()}
    <script type="text/javascript">
        var editorConfig = ${ h.dumps( editor_config ) };
        config.addInitialization(function(galaxy, config) {
            console.log("workflow/editor.mako, editorConfig", editorConfig);
            window.bundleEntries.mountWorkflowEditor(editorConfig);
        });
    </script>
</%def>

<%def name="stylesheets()">
    ## Include "base.css" for styling tool menu and forms (details)
    ${h.css("jquery-ui/smoothness/jquery-ui" )}

    ## But make sure styles for the layout take precedence
    ${parent.stylesheets()}
</%def>

<%def name="overlay(visible=False)">
    ${parent.overlay( "Loading workflow...",
                      "<div class='progress progress-striped progress-info active'><div class='progress-bar' style='width: 100%;'></div></div>", self.overlay_visible )}
</%def>

<%def name="left_panel()">
</%def>

<%def name="center_panel()">
</%def>

<%def name="right_panel()">
</%def>
