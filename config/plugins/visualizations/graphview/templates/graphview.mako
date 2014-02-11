<!DOCTYPE HTML>
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
<title>${hda.name} | ${visualization_name}</title>

## ----------------------------------------------------------------------------
<link type="text/css" rel="Stylesheet" media="screen" href="/static/style/base.css">
<link type="text/css" rel="Stylesheet" media="screen" href="/plugins/visualizations/graphview/static/graphview.css">

## ----------------------------------------------------------------------------
<script type="text/javascript" src="/static/scripts/libs/jquery/jquery.js"></script>
<script type="text/javascript" src="/static/scripts/libs/jquery/jquery.migrate.js"></script>
<script type="text/javascript" src="/static/scripts/libs/d3.js"></script>

<script type="text/javascript" src="/plugins/visualizations/graphview/static/graphview.js"></script>
<script type="text/javascript" src="/plugins/visualizations/graphview/static/jquery.rdfquery.core.js"></script>

</head>

## ----------------------------------------------------------------------------
<body>
%if not embedded:
## dataset info: only show if on own page
<div id="chart-header" class="header">
    <h2 class="title">Graph View of of '${hda.name}'</h2>
    <div id="tooltip"></div>
    <p class="subtitle">${hda.info}</p>
</div>
%endif

<div id="graphview" class="graph-view-div"></div>

<script type="text/javascript">
$(document).ready(function() {
    var hdaId   = '${trans.security.encode_id( hda.id )}',
        hdaExt  = '${hda.ext}',
        ajaxUrl = "${h.url_for( controller='/datasets', action='index')}/" + hdaId + "/display?to_ext=" + hdaExt,

        gv = $("#graphview").graphViewer({height:900, width:900});

    %if hda.ext == 'xgmml':
    $.ajax( ajaxUrl, {
        success: function(xmlDoc) {
            parse_xgmml(xmlDoc, gv.add_node, gv.add_edge);
            gv.render();
        },
        dataType : "xml"
    });

    %elif hda.ext == 'sif':
    $.ajax( ajaxUrl, {
        success: function(txtDoc) {
            parse_sif(txtDoc, gv.add_node, gv.add_edge);
            gv.render();
        },
        dataType : "text"
    });

    %elif hda.ext == 'rdf':
    $.ajax( ajaxUrl, {
        success: function(xmlDoc) {
            var rdf = $.rdf().load(xmlDoc, {});
            rdf.where('?s ?p ?o').
            each(function(){
                gv.add_edge(this.s.value._string, this.o.value._string, {"type" : this.p.value._string})
            });
            gv.render();
        },
        dataType : "xml"
    });
    %endif

});
</script>

</body>
