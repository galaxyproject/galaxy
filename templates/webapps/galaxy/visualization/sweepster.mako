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
            overflow: auto;
        }
        #right {
            width: 600px;
        }
        .tiles {
            overflow: auto;
            position: absolute;
            top: 30px;
            bottom: 25px;
            left: 0;
            right: 0;
        }
        .help {
            border-radius: 15px;
            border: solid 1px #CCC;
            padding: 0px 2px;
            margin: 10px;
        }
    </style>
</%def>

<%def name="javascripts()">
    ${parent.javascripts()}

    ## ${h.js( "libs/jquery/jquery-ui" )}

    <script type="text/javascript">
        $(function() {
            // -- Viz set up. --
            var viz = new window.bundleEntries.SweepsterVisualization(
                ${ h.dumps( config )}
            );
            var viz_view = new window.bundleEntries.SweepsterVisualizationView({ model: viz });
            viz_view.render();
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
