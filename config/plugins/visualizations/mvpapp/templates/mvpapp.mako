<%
    app_root = h.url_for("/static/plugins/visualizations/mvpapp/static/")
%>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>MVP Application</title>
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
            <a class="navbar-brand" href="#">MVP Viewer<span id="mvp_help" class="fa fa-question" style="padding: 5px"></span><span class="sr-only">Help?</span><span id="mvp_config" class="fa fa-cog" style="padding: 5px"></span></a>
        </div>
        <div id="user_btns">
                <div id="app_btns" class="btn-group" role="group">
                    <button id="fdr_module" class="btn btn-primary navbar-btn" disabled="disabled" data-toggle="tooltip" data-placement="bottom" title="Distribution of spectral matching identification scores">ID Scores</button>
                    <button id="score_defaults" class="btn btn-primary navbar-btn" disabled="disabled" data-toggle="tooltip" data-placement="bottom" title="Select identification features for display">ID Features</button>
                    <button id="scans-to-galaxy" class="btn btn-primary navbar-btn" data-toggle="tooltip" data-placement="bottom" title="Exports list of verified PSMs to active history">Export Scans <span id="scan-count-badge" class="badge">0</span></button>
                    <button id="clear_scans" class="btn btn-primary navbar-btn" disabled="disabled" data-container="body" data-toggle="tooltip" data-placement="bottom" title="Clears all scans">Clear all Scans</button>
                    <button id="mvp_full_window" class="btn btn-primary navbar-btn" data-container="body" data-toggle="tooltip" data-placement="bottom" title="Open MVP in a new window."><span class="tip-help">Window</button>
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


${h.javascript_link(app_root +  "dist/script.js")}
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