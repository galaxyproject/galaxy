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
    ${h.js( "libs/d3", "mvc/data", "mvc/tools", "viz/visualization", "viz/paramamonster" )}

    <script type="text/javascript">
        var tool;
        $(function() {            
            // -- Viz set up. --
            
            tool = new Tool(JSON.parse('${ h.to_json_string( tool ) }'));
            // HACK: need to replace \ with \\ due to simplejson bug. 
            var dataset = new Dataset(JSON.parse('${ h.to_json_string( dataset.get_api_value() ).replace('\\', '\\\\' ) }')),
                paramamonster_viz = new ParamaMonsterVisualization({
                    tool: tool,
                    dataset: dataset
                });
                viz_view = new ParamaMonsterVisualizationView({ model: paramamonster_viz });
                
            viz_view.render();
            $('.unified-panel-body').append(viz_view.$el);
            
            // Tool testing.
            var regions = [
                    new GenomeRegion({
                        chrom: 'chr19',
                        start: '10000',
                        end: '26000'
                    }),
                    new GenomeRegion({
                        chrom: 'chr19',
                        start: '30000',
                        end: '36000'
                    })
                ];
                
            $.when(tool.rerun(dataset, regions)).then(function(outputs) {
                console.log(outputs); 
            });
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
    <div class="unified-panel-body">
    </div>
</%def>
