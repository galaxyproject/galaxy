<%inherit file="/webapps/galaxy/base_panels.mako"/>

<%def name="init()">
<%
    self.has_left_panel=False
    self.has_right_panel=False
    self.active_view="visualization"
    self.message_box_visible=False
%>
</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}
    <style>
        .unified-panel-body {
            overflow: auto;
        }
        .link {
            fill: none;
            stroke: #ccc;
            stroke-width: 1.5px;
        }
        .node {
            font: 10px sans-serif;
        }
        .node circle {
            fill: #fff;
            stroke: steelblue;
            stroke-width: 1.5px;
        }
    </style>
</%def>

<%def name="javascripts()">
    ${parent.javascripts()}

    ${h.templates( "tool_link", "panel_section", "tool_search" )}
    ${h.js( "libs/d3", "viz/visualization", "viz/paramamonster", "mvc/tools" )}

    <script type="text/javascript">
        $(function() {            
            // -- Viz set up. --
            
            var tool = new Tool(JSON.parse('${ h.to_json_string( tool ) }')),
                tool_param_tree = new ToolParameterTree({ tool: tool }),
                tool_param_tree_view = new ToolParameterTreeView({ model: tool_param_tree });
                
            tool_param_tree_view.render();
            $('#vis').append(tool_param_tree_view.$el);
        });
    </script>
</%def>

<%def name="center_panel()">
    <div class="unified-panel-header" unselectable="on">
        <div class="unified-panel-header-inner">
            <div style="float:left;" id="title"></div>
        </div>
        <div style="clear: both"></div>
    </div>
    <div id="vis" class="unified-panel-body"></div>
</%def>
