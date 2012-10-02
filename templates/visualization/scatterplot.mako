<%inherit file="/base.mako"/>

<%def name="stylesheets()">
${parent.stylesheets()}

<style type="text/css">

.title {
    margin: 0px;
    padding: 8px;
    background-color: #ebd9b2;
    border: 2px solid #ebd9b2;
}

.subtitle {
    margin: 0px;
    padding: 0px 8px 8px 16px;
    background-color: #ebd9b2;
    color: white;
    font-size: small;
}

#chart-settings-form {
    /*from width + margin of chart?*/
    float: right;
    width: 100%;
    margin: 0px;
    padding-top: 1em;
}

#chart-settings-form > * {
    margin: 8px;
}

#chart-settings-form input, #chart-settings-form select {
    width: 30%;
    max-width: 256px;
}

#chart-holder {
    overflow: auto;
}

#chart-settings-form #loading-indicator .loading-message {
    margin-left: 16px;
    font-style: italic;
    color: grey;
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
    font-family: sans-serif;
    font-size: 12px;
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
        //?? hmmmm
        //kwargs          = ${h.to_json_string( kwargs )};
    
    var settingsForm = new scatterplot.ScatterplotView({
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
    <h2 class="title">Scatterplot of '${hda['name']}'</h2>
    <p class="subtitle">${hda['misc_info']}</p>
    <div id="chart-holder"></div>
    <div id="chart-settings-form"></div>
</%def>
