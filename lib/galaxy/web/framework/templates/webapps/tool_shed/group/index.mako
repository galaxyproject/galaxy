<%inherit file="/webapps/tool_shed/base_panels.mako"/>
<%namespace file="/message.mako" import="render_msg" />

<%def name="stylesheets()">
    ## Include "base.css" for styling tool menu and forms (details)
    ${h.css( "base", "autocomplete_tagging", "tool_menu" )}

    ## But make sure styles for the layout take precedence
    ${parent.stylesheets()}

    <style type="text/css">
        body { margin: 0; padding: 0; overflow: hidden; }
        #left {
            background: #C1C9E5 url(${h.url_for('/static/style/menu_bg.png')}) top repeat-x;
        }
        .unified-panel-body {
            overflow: auto;
        }
        .toolMenu {
            margin-left: 10px;
        }
    </style>
</%def>


<%def name="javascripts()">
    ${parent.javascripts()}
</%def>

<%def name="init()">
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
            require.config({
                paths: {
                    'toolshed': '../toolshed'
            }
            });
            require([ '${config.get( "app" ).get( "jscript" )}' ], function( groups ){
                app = new groups.ToolshedGroups();
            });
        });
    </script>
    <div id="groups_element" style="width: 95%; margin:auto; margin-top:2em; "></div>
</%def>
