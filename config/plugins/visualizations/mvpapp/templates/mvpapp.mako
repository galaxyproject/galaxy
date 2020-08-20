<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>MVP Application</title>

    <link href="/static/plugins/visualizations/mvpapp/static/css/jquery-ui.min.css" rel="stylesheet">
    <link href="/static/plugins/visualizations/mvpapp/static/css/lorikeet.css" rel="stylesheet">
    <link href="/static/plugins/visualizations/mvpapp/static/css/datatables.min.css" rel="stylesheet">
    <link href="/static/plugins/visualizations/mvpapp/static/css/app.css" rel="stylesheet">
    <link href="/static/plugins/visualizations/mvpapp/static/css/msi.css" rel="stylesheet">

    <link href="/static/plugins/visualizations/mvpapp/static/css/igv.css" rel="stylesheet">
    <link rel="stylesheet" type="text/css" href='https://fonts.googleapis.com/css?family=PT+Sans:400,700'>
    <link rel="stylesheet" type="text/css" href='https://fonts.googleapis.com/css?family=Open+Sans'>
    <link rel="stylesheet" type="text/css" href="https://maxcdn.bootstrapcdn.com/font-awesome/4.2.0/css/font-awesome.min.css">

</head>
<body>

<!-- Modal for use by all code -->
<div id="master_modal"></div>

<!-- NAVBAR -->
<nav class="navbar navbar-fixed-top">
    <div class="container">
        <div class="navbar-header">
            <a class="navbar-brand" href="#">MVP Viewer<span id="mvp_help" class="glyphicon glyphicon-question-sign" style="padding: 5px"></span><span class="sr-only">Help?</span><span id="mvp_config" class="glyphicon glyphicon-cog" style="padding: 5px"></span></a>
        </div>
        <div id="user_btns">
                <div id="app_btns" class="btn-group" role="group">
                    <button id="fdr_module" class="btn btn-primary navbar-btn" disabled="disabled" data-toggle="tooltip" data-placement="bottom" title="Distribution of spectral matching identification scores">ID Scores</button>
                    <button id="score_defaults" class="btn btn-primary navbar-btn" disabled="disabled" data-toggle="tooltip" data-placement="bottom" title="Select identification features for display">ID Features</button>
                    <button id="scans-to-galaxy" class="btn btn-primary navbar-btn" data-toggle="tooltip" data-placement="bottom" title="Exports list of verified PSMs to active history">Export Scans <span id="scan-count-badge" class="badge">0</span></button>
                    <button id="clear_scans" class="btn btn-primary navbar-btn" disabled="disabled" data-container="body" data-toggle="tooltip" data-placement="bottom" title="Clears all scans">Clear all Scans</button>
                    <button id="mvp_full_window" class="btn btn-primary navbar-btn" data-container="body" data-toggle="tooltip" data-placement="bottom" title="Open MVP in a new window."><span class="glyphicon glyphicon-resize-full"></button>
                </div>
                
            </div>
        </div>
        <!--/.nav-collapse -->
    </div>
</nav>
<!-- END NAVBAR -->

<!-- Main content -->
<div class="container">
    <div id="igvDiv"></div>
    <div id="protein_viewer"></div>

    <div id="score_default_div"></div>
    <div id="progress-div"></div>

    <div class="row">
        <div class="col-md-12">
            <h3 id="dataset_name"></h3>
        </div>
    </div>
    <div class="row" id="overview_row">
        <div id="overview_div" class="col-md-12"></div>
    </div>
    <div class="row">
        <div id="score_filter_div" class="col-md-12"></div>
    </div>
    <div class="row">
        <div id="detail_div" class="col-md-12"></div>
    </div>
    <div class="row">
        <div id="lorikeet_zone" class="col-md-12"></div>
    </div>

    <div id="fdr_div"></div>

</div>


<script src="/static/plugins/visualizations/mvpapp/static/js/lib/jquery.min.js"></script>
<script src="/static/plugins/visualizations/mvpapp/static/js/lib/jquery-ui.min.js"></script>
<script src="/static/plugins/visualizations/mvpapp/static/js/lib/igv.js"></script>
<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>

<script src="/static/plugins/visualizations/mvpapp/static/js/lib/jquery.flot.js"></script>
<script src="/static/plugins/visualizations/mvpapp/static/js/lib/jquery.flot.selection.js"></script>
<script src="/static/plugins/visualizations/mvpapp/static/js/lib/excanvas.min.js"></script>
<script src="/static/plugins/visualizations/mvpapp/static/js/lib/internal.js"></script>
<script src="/static/plugins/visualizations/mvpapp/static/js/lib/specview.js"></script>
<script src="/static/plugins/visualizations/mvpapp/static/js/lib/peptide.js"></script>
<script src="/static/plugins/visualizations/mvpapp/static/js/lib/aminoacid.js"></script>
<script src="/static/plugins/visualizations/mvpapp/static/js/lib/ion.js"></script>

<script src="/static/plugins/visualizations/mvpapp/static/js/lib/datatables.min.js"></script>
<script src="/static/plugins/visualizations/mvpapp/static/js/lib/d3.min.js"></script>
<script src="/static/plugins/visualizations/mvpapp/static/js/application.js"></script>

<script>
    $(document).ready(function (){
        var config = {
                                dbkey: '${hda.get_metadata().dbkey}',
                                href: document.location.origin,
                                dataName: '${hda.name}',
                                historyID: '${trans.security.encode_id( hda.history_id )}',
                                datasetID: '${trans.security.encode_id( hda.id )}',
                                tableRowCount: {
                                              % for table in hda.metadata.table_row_count:
                                                '${table}': ${hda.metadata.table_row_count[table]} ,
                                               % endfor
                                }
                            };
        MVPApplication.run(config);
    });
</script>
</body>
</html>