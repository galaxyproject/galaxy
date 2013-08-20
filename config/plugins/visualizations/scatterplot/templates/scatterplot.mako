<!DOCTYPE HTML>
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
<title>${hda.name} | ${visualization_name}</title>

## ----------------------------------------------------------------------------
<link type="text/css" rel="Stylesheet" media="screen" href="/static/style/base.css">
<link type="text/css" rel="Stylesheet" media="screen" href="/static/style/jquery-ui/smoothness/jquery-ui.css">

<link type="text/css" rel="Stylesheet" media="screen" href="/plugins/visualizations/scatterplot/static/scatterplot.css">

## ----------------------------------------------------------------------------
<script type="text/javascript" src="/static/scripts/libs/jquery/jquery.js"></script>
<script type="text/javascript" src="/static/scripts/libs/jquery/jquery.migrate.js"></script>
<script type="text/javascript" src="/static/scripts/libs/underscore.js"></script>
<script type="text/javascript" src="/static/scripts/libs/backbone/backbone.js"></script>
<script type="text/javascript" src="/static/scripts/libs/backbone/backbone-relational.js"></script>
<script type="text/javascript" src="/static/scripts/libs/handlebars.runtime.js"></script>
<script type="text/javascript" src="/static/scripts/libs/d3.js"></script>
<script type="text/javascript" src="/static/scripts/libs/bootstrap.js"></script>
<script type="text/javascript" src="/static/scripts/libs/jquery/jquery-ui.js"></script>
<script type="text/javascript" src="/static/scripts/utils/LazyDataLoader.js"></script>
<script type="text/javascript" src="/static/scripts/mvc/base-mvc.js"></script>

<script type="text/javascript" src="/plugins/visualizations/scatterplot/static/scatterplot.js"></script>

</head>

## ----------------------------------------------------------------------------
<body>
%if not embedded:
## dataset info: only show if on own page
<div id="chart-header" class="header">
    <h2 class="title">Scatterplot of '${hda.name}'</h2>
    <p class="subtitle">${hda.info}</p>
</div>
%endif

<div id="scatterplot" class="scatterplot-control-form"></div>

<script type="text/javascript">
$(function(){
    var hda             = ${h.to_json_string( trans.security.encode_dict_ids( hda.dictify() ) )},
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

</body>
