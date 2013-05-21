<%inherit file="/base.mako"/>

<%def name="stylesheets()">
${parent.stylesheets()}
${h.css(
    "base",
    "autocomplete_tagging",
    "jquery-ui/smoothness/jquery-ui"
)}

<style type="text/css">
/*TODO: use/move into base.less*/
* { margin: 0px; padding: 0px; }

/* -------------------------------------------- general layout */
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
    margin-bottom: 16px;
    overflow: auto;
}

#chart-header .subtitle {
    margin: -4px 0px 0px 4px;
    padding : 0;
    color: white;
    font-size: small;
}

/* -------------------------------------------- main layout */
#scatterplot {
    /*from width + margin of chart?*/
}

.scatterplot-container .tab-pane {
}

/* -------------------------------------------- all controls */

#scatterplot input[type=button],
#scatterplot select {
    width: 100%;
    max-width: 256px;
    margin-bottom: 8px;
}

#scatterplot .help-text,
#scatterplot .help-text-small {
    color: grey;
}

#scatterplot .help-text {
    padding-bottom: 16px;
}

#scatterplot .help-text-small {
    padding: 4px;
    font-size: smaller;
}

#scatterplot > * {
}

#scatterplot input[value=Draw] {
    display: block;
    margin-top: 16px;
}

#scatterplot .numeric-slider-input {
    max-width: 70%;
}

/* -------------------------------------------- data controls */

/* -------------------------------------------- chart controls */
#chart-control .form-input {
    /*display: table-row;*/
}

#chart-control label {
    /*text-align: right;*/
    margin-bottom: 8px;
    /*display: table-cell;*/
}

#chart-control .slider {
    /*display: table-cell;*/
    height: 8px;
    display: block;
    margin: 8px 0px 0px 8px;
}

#chart-control .slider-output {
    /*display: table-cell;*/
    float: right;
}

#chart-control input[type="text"] {
    border: 1px solid lightgrey;
}


/* -------------------------------------------- statistics */
#stats-display table#chart-stats-table {
    width: 100%;
}

#stats-display #chart-stats-table th {
    width: 30%;
    padding: 4px;
    font-weight: bold;
    color: grey;
}

#stats-display #chart-stats-table td {
    border: solid lightgrey;
    border-width: 1px 0px 0px 1px;
    padding: 4px;
}

#stats-display #chart-stats-table td:nth-child(1) {
    border-width: 1px 0px 0px 0px;
    padding-right: 1em;
    text-align: right;
    font-weight: bold;
    color: grey;
}

/* -------------------------------------------- load indicators */
#loading-indicator {
    margin: 12px 0px 0px 8px;
}

#scatterplot #loading-indicator .loading-message {
    font-style: italic;
    font-size: smaller;
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
    
/* -------------------------------------------- info box */
.chart-info-box {
    border-radius: 4px;
    padding: 4px;
    background-color: white;
    border: 1px solid black;
}

</style>
    
</%def>

<%def name="javascripts()">
${parent.javascripts()}
${h.js(

    "libs/underscore",
    "libs/jquery/jquery-ui",
    "libs/d3",

    "mvc/base-mvc",
    "utils/LazyDataLoader",
    "viz/scatterplot"
)}

${h.templates(
    "../../templates/compiled/template-visualization-scatterplotControlForm",
    "../../templates/compiled/template-visualization-dataControl",
    "../../templates/compiled/template-visualization-chartControl",
    "../../templates/compiled/template-visualization-chartDisplay",
    "../../templates/compiled/template-visualization-statsDisplay"
)}

${h.js(
    "mvc/visualizations/scatterplotControlForm",
)}

<script type="text/javascript">
$(function(){

    var hda             = ${h.to_json_string( trans.security.encode_dict_ids( hda.get_api_value() ) )},
        querySettings   = ${h.to_json_string( query_args )},
        chartConfig     = _.extend( querySettings, {
            containerSelector : '#chart',
            //TODO: move to ScatterplotControlForm.initialize
            marginTop   : ( querySettings.marginTop > 20 )?( querySettings.marginTop ):( 20 ),

            xColumn     : querySettings.xColumn,
            yColumn     : querySettings.yColumn,
            idColumn    : querySettings.idColumn
        });
    //console.debug( querySettings );

    var settingsForm = new ScatterplotControlForm({
        dataset         : hda,
        apiDatasetsURL  : "${h.url_for( controller='/api/datasets', action='index' )}",
        el              : $( '#scatterplot' ),
        chartConfig     : chartConfig
    }).render();

});
</script>
</%def>

<%def name="body()">
    <!--dataset info-->
    <div id="chart-header" class="header">
        <h2 class="title">Scatterplot of '${hda.name}'</h2>
        <p class="subtitle">${hda.info}</p>
    </div>
    <div id="scatterplot" class="scatterplot-control-form"></div>
</%def>
