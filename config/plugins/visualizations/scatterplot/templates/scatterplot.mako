<%
    default_title = "Scatterplot of '" + hda.name + "'"
    info = hda.name
    if hda.info:
        info += ' : ' + hda.info

    # optionally bootstrap data from dprov
    ##data = list( hda.datatype.dataset_column_dataprovider( hda, limit=10000 ) )

    # Use root for resource loading.
    root = h.url_for( '/static/' )
    root_api = h.url_for( '/' )
%>
## ----------------------------------------------------------------------------

<!DOCTYPE HTML>
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
<title>${title or default_title | h} | ${visualization_display_name}</title>

## ----------------------------------------------------------------------------
${h.css( 'base', 'jquery-ui/smoothness/jquery-ui')}
${h.stylesheet_link( root + 'plugins/visualizations/scatterplot/static/scatterplot.css' )}

## ----------------------------------------------------------------------------
<script type="text/javascript">
window.Galaxy = { root: '${ root }', root_api: '${ root_api }' };
</script>
${h.javascript_link( root + 'plugins/visualizations/scatterplot/static/scatterplot.js' )}

<script type="text/javascript">
    function getModel(){
        return new ScatterplotModel({
            id      : ${h.dumps( visualization_id )} || undefined,
            title   : "${title or default_title}",
            config  : ${h.dumps( config, indent=2 )}
        });
    }
    function getHDAJSON(){
        return ${h.dumps( trans.security.encode_dict_ids( hda.to_dict() ), indent=2 )};
    }
</script>

</head>

## ----------------------------------------------------------------------------
<body>
    %if embedded and saved_visualization:
        <figcaption>
            <span class="title">${title}</span>
            <span class="title-info">${info}</span>
        </figcaption>
        <figure class="scatterplot-display"></figure>

        <script type="text/javascript">
        $(function(){
            var display = new ScatterplotDisplay({
                    el      : $( '.scatterplot-display' ).attr( 'id', 'scatterplot-display-' + '${visualization_id}' ),
                    model   : getModel(),
                    dataset : getHDAJSON(),
                    embedded: "${embedded}"
                }).render();
            display.fetchData();
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
            var model = getModel(),
                hdaJSON = getHDAJSON(),
                editor  = new ScatterplotConfigEditor({
                    el      : $( '.scatterplot-editor' ).attr( 'id', 'scatterplot-editor-hda-' + hdaJSON.id ),
                    model   : model,
                    dataset : hdaJSON
                }).render();
            window.editor = editor;

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
