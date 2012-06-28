<%inherit file="/webapps/galaxy/base_panels.mako"/>

<%def name="init()">
<%
    self.has_left_panel=True
    self.has_right_panel=True
    self.active_view="visualization"
    self.message_box_visible=False
%>
</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}
    <style>
        div#center {
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
            cursor: pointer;
        }
        .node:hover {
            fill: #f00;
        }
        .node:hover circle {
            fill: #ccc;
            stroke: #f00;
        }
        table.tracks {
            border-collapse: separate;
            border-spacing: 5px;
        }
        .tile {
            border: solid 1px #DDD;
            margin: 2px;
            border-radius: 10px;
            margin: 3px;
        }
        .label {
            position: fixed;
            font: 10px sans-serif;
            font-weight: bold;
            background-color: #DDD;
            border-radius: 5px;
            padding: 1px;
        }
        th,td {
            text-align: center;
        }
        td.settings {
            vertical-align: top;
        }
        .icon-button.track-settings {
            float: none;
        }
        .track-info {
            text-align: left;
            font: 10px sans-serif;
            position: fixed;
            background-color: #CCC;
            border: solid 1px #AAA;
            border-radius: 2px;
            padding: 2px;
        }
        .btn-primary, .btn-primary:hover {
            color: #EEE;
            background-color: #DDD;
            background-image: none;
            border-radius: 12px;
        }
        #left {
            width: 300px;
        }
        #center {
            left: 300px;
            right: 600px;
        }
        #right {
            width: 600px;
        }
    </style>
</%def>

<%def name="javascripts()">
    ${parent.javascripts()}

    ${h.templates( "tool_link", "panel_section", "tool_search", "tool_form" )}
    ${h.js( "libs/d3", "mvc/data", "mvc/tools", "viz/visualization", "viz/paramamonster", "viz/trackster", "viz/trackster_ui", "jquery.ui.sortable.slider" )}

    <script type="text/javascript">
        var viz;
        $(function() {            
            // -- Viz set up. --    
            var viz = new ParamaMonsterVisualization(
                ${ h.to_json_string( config ).replace('\\', '\\\\' )}
            );
            var viz_view = new ParamaMonsterVisualizationView({ model: viz });
                
            viz_view.render();
            $('.unified-panel-body').append(viz_view.$el);

            // -- Menu set up. --
            var menu = create_icon_buttons_menu([
            { icon_class: 'disk--arrow', title: 'Save', on_click: function() { 
                // Show saving dialog box
                show_modal("Saving...", "progress");

                viz.save().success(function(vis_info) {
                    hide_modal();
                    viz.set({
                        'id': vis_info.vis_id,
                        'has_changes': false
                    });
                })
                .error(function() { 
                    show_modal( "Could Not Save", "Could not save visualization. Please try again later.", 
                                { "Close" : hide_modal } );
                });
            } },
            { icon_class: 'cross-circle', title: 'Close', on_click: function() { 
                window.location = "${h.url_for( controller='visualization', action='list' )}";
            } }
            ], 
            {
                tipsy_config: {gravity: 'n'}
            });
            
            menu.$el.attr("style", "float: right");
            $("#right .unified-panel-header-inner").append(menu.$el);
        });
    </script>
</%def>

<%def name="center_panel()">
</%def>

<%def name="left_panel()">
</%def>

<%def name="right_panel()">
    <div class="unified-panel-header" unselectable="on">
        <div class="unified-panel-header-inner">
        </div>
    </div>
</%def>