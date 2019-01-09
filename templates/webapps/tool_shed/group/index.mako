<%inherit file="/webapps/tool_shed/base_panels.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<%def name="stylesheets()">
    ## Include "base.css" for styling tool menu and forms (details)
    ${h.css( "base" )}

    ## But make sure styles for the layout take precedence
    ${parent.stylesheets()}
</%def>


<%def name="javascripts()">
    ${parent.javascripts()}
</%def>

<%def name="init()">
    ${parent.init()}
    %if trans.app.config.require_login and not trans.user:
        <script type="text/javascript">
            if ( window != top ) {
                top.location.href = location.href;
            }
        </script>
    %endif
</%def>

<%def name="center_panel()">
    <script type="text/javascript">
        window.globalTS = new Object();
        $( function(){
            new window.bundleEntries.ToolshedGroups.ToolshedGroups();
        });
    </script>
    <div id="groups_element" style="width: 95%; margin:auto; margin-top:2em; "></div>
</%def>
