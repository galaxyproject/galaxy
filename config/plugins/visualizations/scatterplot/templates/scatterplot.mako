<%
    default_title = "Scatterplot of '" + hda.name + "'"
    info = hda.name
    if hda.info:
        info += ' : ' + hda.info

    # optionally bootstrap data from dprov
    ##data = list( hda.datatype.dataset_column_dataprovider( hda, limit=10000 ) )
%>
## ----------------------------------------------------------------------------

<!DOCTYPE HTML>
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
<title>${title or default_title} | ${visualization_display_name}</title>

## ----------------------------------------------------------------------------
<link type="text/css" rel="Stylesheet" media="screen" href="/static/style/base.css">
<link type="text/css" rel="Stylesheet" media="screen" href="/static/style/jquery-ui/smoothness/jquery-ui.css">
<link type="text/css" rel="Stylesheet" media="screen" href="/plugins/visualizations/scatterplot/static/scatterplot.css">

## ----------------------------------------------------------------------------
<script type="text/javascript" src="/static/scripts/libs/jquery/jquery.js"></script>
<script type="text/javascript" src="/static/scripts/libs/jquery/jquery.migrate.js"></script>
<script type="text/javascript" src="/static/scripts/libs/jquery/jquery-ui.js"></script>
<script type="text/javascript" src="/static/scripts/libs/bootstrap.js"></script>
<script type="text/javascript" src="/static/scripts/libs/underscore.js"></script>
<script type="text/javascript" src="/static/scripts/libs/backbone/backbone.js"></script>
<script type="text/javascript" src="/static/scripts/libs/handlebars.runtime.js"></script>
<script type="text/javascript" src="/static/scripts/libs/d3.js"></script>

<script type="text/javascript" src="/static/scripts/mvc/base-mvc.js"></script>
<script type="text/javascript" src="/static/scripts/mvc/ui.js"></script>
<script type="text/javascript" src="/static/scripts/mvc/visualization/visualization-model.js"></script>

<script type="text/javascript" src="/plugins/visualizations/scatterplot/static/scatterplot-edit.js"></script>
</head>

## ----------------------------------------------------------------------------
<body>
%if embedded and saved_visualization:
<figcaption>
    <span class="title">${title}</span>
    <span class="title-info">${info}</span>
</figcaption>
<figure class="scatterplot-display"></div>

<script type="text/javascript">
$(function(){
    var model = new ScatterplotModel({
            id      : ${h.to_json_string( visualization_id )} || undefined,
            title   : "${title}",
            config  : ${h.to_json_string( config, indent=2 )}
        });
        hdaJson = ${h.to_json_string( trans.security.encode_dict_ids( hda.to_dict() ), indent=2 )},
        display = new ScatterplotDisplay({
            el      : $( '.scatterplot-display' ).attr( 'id', 'scatterplot-display-' + '${visualization_id}' ),
            model   : model,
            dataset : hdaJson,
            embedded: "${embedded}"
        }).render();
    display.fetchData();
    //window.model = model;
    //window.display = display;
});

</script>

%else:
<div class="chart-header">
    <h2>${title or default_title}</h2>
    <p>${info}</p>
</div>

<div class="scatterplot-editor"></div>
<script type="text/javascript">
$(function(){
    var model   = new ScatterplotModel({
            id      : ${h.to_json_string( visualization_id )} || undefined,
            title   : "${title or default_title}",
            config  : ${h.to_json_string( config, indent=2 )}
        }),
        hdaJson = ${h.to_json_string( trans.security.encode_dict_ids( hda.to_dict() ), indent=2 )},
        editor  = new ScatterplotConfigEditor({
            el      : $( '.scatterplot-editor' ).attr( 'id', 'scatterplot-editor-hda-' + hdaJson.id ),
            model   : model,
            dataset : hdaJson
        }).render();
    //window.editor = editor;

    $( '.chart-header h2' ).click( function(){
        var returned = prompt( 'Enter a new title:' );
        if( returned ){
            model.set( 'title', returned );
        }
    });
    model.on( 'change:title', function(){
        $( '.chart-header h2' ).text( model.get( 'title' ) );
        document.title = model.get( 'title' ) + ' | ' + '${visualization_display_name}';
    })
});

</script>
%endif

</body>
