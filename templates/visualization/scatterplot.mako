<%inherit file="/base.mako"/>

<%def name="stylesheets()">
${parent.stylesheets()}
${h.css(
    "base",
    "autocomplete_tagging",
    "jquery-ui/smoothness/jquery-ui-1.8.23.custom"
)}

<style type="text/css">
/*TODO: use/move into base.less*/
* { margin: 0px; padding: 0px; }

/* -------------------------------------------- layout */
.column {
	position:relative;
    overflow: auto;
}

.left-column {
	float: left;
    width: 40%;
}

.right-column {
    margin-left: 41%;
}

div.tab-pane {
    padding: 8px;
}

/* -------------------------------------------- header */
.header {
    margin-bottom: 8px;
}

#chart-header {
    padding : 8px;
    background-color: #ebd9b2;
}

#chart-header .subtitle {
    margin: -4px 0px 0px 4px;
    padding : 0;
    color: white;
    font-size: small;
}

/* -------------------------------------------- all controls */
#chart-settings-form {
    /*from width + margin of chart?*/
    padding-top: 1em;
}

#chart-settings-form input[type=button],
#chart-settings-form select {
    width: 100%;
    max-width: 256px;
    margin-bottom: 8px;
}

#chart-settings-form .help-text,
#chart-settings-form .help-text-small {
    color: grey;
}

#chart-settings-form .help-text {
    padding-bottom: 16px;
}

#chart-settings-form .help-text-small {
    padding: 4px;
    font-size: smaller;
}

#chart-settings-form > * {
}

#chart-settings-form input[value=Draw] {
    display: block;
    margin-top: 16px;
}

/* -------------------------------------------- data controls */

/* -------------------------------------------- chart controls */
#chart-settings .form-input {
    /*display: table-row;*/
}

#chart-settings label {
    /*text-align: right;*/
    margin-bottom: 8px;
    /*display: table-cell;*/
}

#chart-settings .slider {
    /*display: table-cell;*/
    height: 8px;
    display: block;
    margin: 8px 0px 0px 8px;
}

#chart-settings .slider-output {
    /*display: table-cell;*/
    float: right;
}

#chart-settings input[type="text"] {
    border: 1px solid lightgrey;
}


/* -------------------------------------------- statistics */
#chart-stats table#chart-stats-table {
    width: 100%;
}

#chart-stats #chart-stats-table th {
    width: 30%;
    padding: 4px;
    font-weight: bold;
    color: grey;
}

#chart-stats #chart-stats-table td {
    border: solid lightgrey;
    border-width: 1px 0px 0px 1px;
    padding: 4px;
}

#chart-stats #chart-stats-table td:nth-child(1) {
    border-width: 1px 0px 0px 0px;
    padding-right: 1em;
    text-align: right;
    font-weight: bold;
    color: grey;
}

/* -------------------------------------------- load indicators */
#loading-indicator {
    z-index: 2;
    position: absolute;
    top: 0;
    bottom: 0;
    left: 0;
    right: 0;
    background-color: white;
    padding: 32px 0 0 32px;
}

#chart-settings-form #loading-indicator .loading-message {
    margin-left: 10px;
    font-style: italic;
    color: grey;
}

/* -------------------------------------------- chart area */
#chart-holder {
    overflow: auto;
    margin-left: 8px;
}

svg .grid-line {
    fill: none;
    stroke: lightgrey;
    stroke-opacity: 0.5;
    shape-rendering: crispEdges;
    stroke-dasharray: 3, 3;
}

svg .axis path, svg .axis line {
    fill: none;
    stroke: black;
    shape-rendering: crispEdges;
}

svg .axis text {
    font-family: monospace;
    font-size: 12px;
}

svg #x-axis-label, svg #y-axis-label {
    font-family: sans-serif;
    font-size: 10px;
}

svg .glyph {
    stroke: none;
    fill: black;
    fill-opacity: 0.2;
}
    
</style>
    
</%def>

<%def name="javascripts()">
${parent.javascripts()}
${h.js( "libs/require" )}

<script type="text/javascript">
require.config({ baseUrl : "${h.url_for( '/static/scripts' )}", });

require([ "viz/scatterplot" ], function( scatterplot ){
    
    var hda             = ${h.to_json_string( hda )},
        historyID       = '${historyID}'
        apiDatasetsURL  = "${h.url_for( controller='/api/datasets' )}";
        
    var settingsForm = new scatterplot.ScatterplotControlForm({
        dataset    : hda,
        el         : $( '#chart-settings-form' ),
        apiDatasetsURL : apiDatasetsURL,
        
        chartConfig : {
            containerSelector : '#chart-holder',
            marginTop : 20,
        }
    }).render();
});

</script>
</%def>

<%def name="body()">
    <!--dataset info-->
    <div id="chart-header" class="header">
        <h2 class="title">Scatterplot of '${hda['name']}'</h2>
        <p class="subtitle">${hda['misc_info']}</p>
    </div>
    <div class="outer-container">
        <!--plot controls-->
        <div id="chart-settings-form" class="column left-column"></div>
        <!--plot-->
        <div class="column right-column">
            <div id="chart-holder" class="inner-container"></div>
        </div>
        <div style="clear: both;"></div>
    </div>
    <div id="test"></div>

</%def>

