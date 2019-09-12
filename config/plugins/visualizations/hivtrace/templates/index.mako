<%
    app_root = h.url_for("/static/plugins/visualizations/hivtrace/static/")
%>

<html lang='en'>

<head>
  <meta charset="utf-8">
  <meta http-equiv="X-UA-Compatible" content="IE=edge">
  <title>HIV-TRACE</title>

  <!-- Latest compiled and minified CSS -->
  ${h.stylesheet_link(app_root + 'hivtrace.css' )}

  <!-- Latest compiled and minified JavaScript -->
  ${h.javascript_link( app_root +  "vendor.js" )}

  <style>
    .navbar {
      position : relative;
    }
  </style>

</head>

<body>

<nav class="navbar navbar-default navbar-fixed-top" role="navigation">

  <div class="container">

    <!-- Brand and toggle get grouped for better mobile display -->
    <div class="navbar-header">
      <button type="button" class="navbar-toggle" data-toggle="collapse" data-target="#navbar-collapse-1">
        <span class="sr-only">Toggle navigation</span>
        <span class="icon-bar"></span>
        <span class="icon-bar"></span>
        <span class="icon-bar"></span>
      </button>
      <a class="navbar-brand" href="#">HIV-TRACE</a>
    </div>

    <!-- Collect the nav links, forms, and other content for toggling -->
    <div class="collapse navbar-collapse" id = "navbar-collapse-1">

      <ul class="nav navbar-nav">
        <li class="dropdown hidden">
          <a href="javascript:void(0)" role="button" class="dropdown-toggle" data-toggle="dropdown">Load file<b class="caret"></b></a>
          <ul class="dropdown-menu">
            <li><input type="file" id="json_file"></li>
          </ul>
        </li>
      </ul>

      <form class="navbar-form navbar-right">
        <div class = 'form-group'  id='network_status_string'>
        </div>
      </form>

    </div><!-- /.navbar-collapse -->
  </div><!-- /.container-fluid -->
</nav>


<div class="container">
   <div class="row" style="margin-top: 10px; margin-bottom: 10 px;">
     <div class="col-lg-12">
         <div class="alert alert-danger alert-lg" id='app-error' style='display:none;'></div>
    </div>
   </div>
  <div class="tabbable">
    <ul class="nav nav-tabs" id="top_level_tab_container">
      <li class="active" id="main-tab"><a id = 'trace-default-tab' href="#trace-results" data-toggle="tab">Network</a></li>
      <li class='disabled' id='lanl-result-tab'><a href="#lanl-trace-results" data-toggle="tab">Network + DB</a></li>
      <li class='disabled' id="graph-tab"><a href="#trace-graph" data-toggle="tab">Statistics</a></li>
      <li class='disabled' id="clusters-tab"><a href="#trace-clusters" data-toggle="tab">Clusters</a></li>
      <li class='disabled' id="nodes-tab"><a href="#trace-nodes" data-toggle="tab">Nodes</a></li>
      <li class='disabled' id="attributes-tab"><a href="#trace-attributes" data-toggle="tab">Attributes</a></li>
      <li class='disabled'><a href="#trace-settings" data-toggle="tab">Settings</a></li>
    </ul>

    <div class="tab-content" id = "top_level_tab_content">
      <div id="trace-results" class="tab-pane active">
        <!-- Warning bar -->
        <div class="row" style="margin-top: 10px; margin-bottom: 10 px;">
          <div class="col-lg-12">
            <div class="alert alert-warning alert-dismissible" id='main-warning' style='display:none;'>
             <button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button>
            </div>
          </div>
        </div>

        <div class="row" data-hivtrace = "cluster-clone">
          <div class='col-lg-12'>
            <div class="nav-trace">
              <div class="input-group input-group-sm">

                <!-- UI Bar -->
                <div class="nav-trace">
                  <div class="input-group input-group-sm" id = 'network_ui_bar' data-hivtrace-button-bar = 'yes'>
                    <div class="input-group-btn" data-hivtrace-ui-role = 'button_group'></div>
                    <span class="input-group-btn">
                      <button type="button" class="btn btn-default dropdown-toggle" data-toggle="dropdown" data-hivtrace-ui-role = "cluster_operations_button">Clusters <span class="caret"></span></button>
                      <ul class="dropdown-menu" role="menu" data-hivtrace-ui-role ='cluster_operations_container'></ul>
                    </span>
                    <div class="input-group-btn">
                      <button type="button" class="btn btn-default dropdown-toggle" data-toggle="dropdown"
                      data-hivtrace-ui-role = "attributes_label">Color <span class="caret"></span></button>
                      <ul class="dropdown-menu" role="menu" data-hivtrace-ui-role ='attributes'></ul>
                      <button type="button" class="btn btn-default" style = 'display:none' data-hivtrace-ui-role='attributes_invert'>Invert</button>
                    </div>
                    <div class="input-group-btn">
                      <button type="button" class="btn btn-default dropdown-toggle" data-toggle="dropdown"
                      data-hivtrace-ui-role="shapes_label">Shape <span class="caret"></span></button>
                      <ul class="dropdown-menu" role="menu" data-hivtrace-ui-role='shapes'></ul>
                    </div>

                    <div class="input-group-btn">
                      <button type="button" class="btn btn-default dropdown-toggle" data-toggle="dropdown"
                      data-hivtrace-ui-role="opacity_label">Opacity <span class="caret"></span></button>
                      <ul class="dropdown-menu" role="menu" data-hivtrace-ui-role='opacity'></ul>
                      <button type="button" class="btn btn-default" style = 'display:none' data-hivtrace-ui-role='opacity_invert'>Invert</button>
                    </div>


                    <div class="input-group input-group-sm">
                        <span class="input-group-addon">
                            <i class = "fa fa-search" ></i>
                        </span>
                        <input type="text" class="form-control" placeholder="Text in attributes" data-hivtrace-ui-role='filter' />
                        <span class="input-group-addon">
                           Hide others <input type = 'checkbox' data-hivtrace-ui-role = 'hide_filter'> </input>
                        </span>
                        <span class="input-group-addon">
                           Show small clusters <input type = 'checkbox' data-hivtrace-ui-role = 'show_small_clusters'> </input>
                        </span>
                        <span class="input-group-addon">
                            <a data-toggle="collapse" href="#network_ui_bar_legend" aria-expanded="false" aria-controls="network_ui_bar_legend">
                            <i class = "fa fa-question"></i>
                            </a>
                       </span>
                    </div>
                  </div>
                </div>


                <!--<div class="nav-trace" id = "network_ui_bar_sliders" style = "display: none">
                    <div class="input-group">
                        <label  id = "network_ui_bar_sliders_label_from">2001/01/01</label>
                            <input id = "network_ui_bar_sliders_from" class = "col-lg-3" type = "range" min = "0" max = "100" step = "0.1" value = "1"></input>
                            <input id = "network_ui_bar_sliders_to" class = "col-lg-3" type = "range" min = "0" max = "100" step = "0.1" value = "1"/>
                        <label class = "pull-right" id = "network_ui_bar_sliders_label_to">2012/01/01</label>
                    </div>
                </div>-->

              </div>
            </div>

            <!-- Legend SVG -->
            <div class = "row collapse" id= "network_ui_bar_legend" style = "margin-top : 0.1em" data-hivtrace = "cluster-clone">
                <div class="well">
                    <span class="label label-primary">Clusters</span> are shown as circles with thick rims
                        <svg width = "20" height = "20" style = "vertical-align: bottom; display: inline">
                            <circle cx = "10" cy = "10" r = "7" class = 'cluster'> </circle>
                        </svg>
                      with <em>area</em> proportional to the number of nodes in a cluster. Click on clusters
                      to show menu options, click and drag to reposition. <p/>
                     <span class="label label-primary">Nodes</span> are shown as different symbols (depending on
                     rendering options), with thin rims <svg width = "20" height = "20" style = "vertical-align: bottom; display: inline">
                            <circle cx = "10" cy = "10" r = "7" class = 'node'> </circle>
                        </svg>, and <em>area</em> scaling with the number of links.

                        <p/>
                        Type in text to search for clusters and nodes whose <em>attributes contain the term</em>. <br/>
                        For example, typing in <code>MSM</code> will highlight nodes and/or clusters that 
                        have 'MSM' in any of the data fields. <br/>
                        Type in space separated terms (<code>MSM IDU</code>) to search for <b>either</b> term. <br/>
                        Type in terms in quotes (<code>\"male\"</code>) will search for this <b>exact</b> term. <br/>
                        Type in <code>&lt;0.01</code> to search for nodes that have edges which are 0.01 (1%) or shorter. Any positive threshold works <br/>
                         <p/>
                        Matching node <svg width = '20' height = '20' style = 'vertical-align: bottom; display: inline'><circle cx = '10' cy = '10' r = '7' class = 'node selected_object'> </circle></svg><br/>
                        Cluster where 25% of nodes match the term <svg width = '28' height = '28' style = 'vertical-align: bottom; display: inline'><circle cx = '14' cy = '14' r = '8' class = 'cluster'> </circle>
                        <path d = 'M 2 14 A 12 12 0 0 1 14 2'/ style = 'fill: none; stroke: #337AB7; stroke-width: 3px;'>
                        </svg><br/> 
                        Cluster where 75% of nodes match the term <svg width = '28' height = '28' style = 'vertical-align: bottom; display: inline'><circle cx = '14' cy = '14' r = '8' class = 'cluster'> </circle>
                        <path d = 'M 2 14 A 12 12 0 1 1 14 26'/ style = 'fill: none; stroke: #337AB7; stroke-width: 3px;'>
                        </svg>
                        <p/>
        
                        Use the <code>Hide others</code> checkbox to automatically hide all clusters/nodes that do not match the search terms
                        <br/>
                        Use the <code>Show small clusters</code> checkbox to display small clusters that may have been hidden for clarity
               </div>
            </div>


            <!-- Main SVG -->
            <div id='network_tag'>
              <div class="my_progress">
                <div class="progress-bar progress-bar-striped disabled" role="progressbar" aria-valuenow="100"
                aria-valuemin="0" aria-valuemax="100" style="width: 100%; height: 50px">
                  Loading the network
                </div>
              </div>
            </div>

          </div>

        </div>

      </div>


    <div id="trace-graph" class="tab-pane">
      <div class='row'>
        <div class='col-lg-6'>
          <p class="lead"> Network Statistics </p>
          <table class="table table-striped table-condensed table-responsive" id="graph_summary_table">
          </table>
        </div>
        <div class='col-lg-6'>
          <p id='histogram_label' class="lead"></p>
          <div class='row' id='histogram_tag' style='margin-left: 5px'>
          </div>
        </div>
      </div>
    </div>

    <div id="lanl-trace-results" class="tab-pane">
      <div class="row" style="margin-top: 10px; margin-bottom: 10 px;">
        <div class="col-lg-12">
          <div class="alert alert-info" id='lanl-main-warning' style='display:none;'>
          </div>
        </div>
      </div>

      <div class="row">
        <div class='col-lg-12'>
          <div class="row">
            <div class="input-group input-group-sm" id='lanl_network_ui_bar'>
              <span class="input-group-btn">
                        <button type="button" class="btn btn-default dropdown-toggle" data-toggle="dropdown" id = "lanl_network_ui_bar_cluster_operations_button">Clusters <span class="caret"></span></button>
              <ul class="dropdown-menu" role="menu" id='lanl_network_ui_bar_cluster_operations_container'></ul>
              </span>
              <div class="input-group-btn">
                <button type="button" class="btn btn-default dropdown-toggle" data-toggle="dropdown"
                id="lanl_network_ui_bar_attribute_label">Attribute <span class="caret"></span></button>
                <ul class="dropdown-menu" role="menu" id='lanl_network_ui_bar_attributes'></ul>
              </div>
              <input type="text" class="form-control" placeholder="search" id='lanl_network_ui_bar_search'>
            </div>
          </div>
          <div class='row' id='lanl-network_tag'>
            <div class="my_progress">
              <div class="progress-bar progress-bar-striped active" role="progressbar" aria-valuenow="100"
              aria-valuemin="0" aria-valuemax="100" style="width: 100%">
                Loading the network...
              </div>
            </div>
          </div>
        </div>
      </div>
      <div class="row">
        <div class='col-lg-9'>
          <p id='lanl-network_status_string' class='text-info'></p>
        </div>
      </div>
    </div>

    <div id="trace-clusters" class="tab-pane">
      <div class='row'>
        <div class='col-lg-12'>

            <div class="modal fade" id="network_ui_bar_cluster_list" tabindex="-1" role="dialog">
              <div class="modal-dialog" role="document">
                <div class="modal-content" data-hivtrace-ui-role = "cluster_list_body">
                  <div class="modal-header">
                    <button type="button" class="close" data-dismiss="modal" aria-label="Close"><span aria-hidden="true">&times;</span></button>
                    <h4 class="modal-title">Listing nodes in cluster X</h4>
                     <button type="button" data-hivtrace-ui-role = "cluster_list_view_toggle" class = 'btn btn-primary pull-right' data-view = 'id'>Group by attribute</button>
                 </div>
				  <ul data-hivtrace-ui-role = 'cluster_list_payload' class = 'list-unstyled'>
				  </ul>
                  <div class="modal-footer">
                    <!--<button type="button" class="btn btn-primary" id = "network_ui_bar_cluster_zoom_svg_export">Export <i class = "fa fa-image"></i></button>-->
                    <button type="button" class="btn btn-default" data-dismiss="modal">Dismiss</button>
                  </div>
                </div>
              </div>
            </div>

          <span class="pull-right" id="cluster-table-export"> </span>
          <p class="lead"> Clusters </p>
          <table class="table table-striped table-condensed table-hover" id="cluster_table">
          </table>
        </div>
      </div>
    </div>

    <div id="trace-nodes" class="tab-pane">
      <div class='row'>
        <div class='col-lg-12'>
          <span class="pull-right" id="node-table-export"> </span>
          <p class="lead"> Linked individuals </p>
          <table class="table table-striped table-condensed table-hover" id="node_table">
          </table>
        </div>
      </div>
    </div>

    <div id="trace-attributes" class="tab-pane">
      <div class='row'>
        <div class="nav-trace">
          <div class="input-group input-group-sm" data-hivtrace-ui-role ='attributes_container'>
            <span class="input-group-btn">
                          Categorical
                          <button type="button" class="btn btn-default dropdown-toggle" data-toggle="dropdown" data-hivtrace-ui-role = "attributes_cat_label">Attributes <span class="caret"></span></button>
            <ul class="dropdown-menu" role="menu"  data-hivtrace-ui-role='attributes_cat'></ul>
            </span>
          </div>
        </div>
        <div class='col-lg-6'  data-hivtrace-ui-role = "aux_svg_holder_enclosed" style = 'display: none'>
            <div class = "row">
				<button type="button" class="btn btn-info" id = "network_pairwise_chord_legend"><i class = "fa fa-question"></i></button>
            </div>

              <div  data-hivtrace-ui-role ='aux_svg_holder' class='row style = margin-left: 5px'>
             </div>
        </div>
        <div class='col-lg-6 '  data-hivtrace-ui-role = 'attribute_table_enclosed' style = 'display: none'>
            <div class = "row">
            	 <div class = "col-lg-2">
            	 <div class="input-group input-group-sm" >
            	 	<span class="input-group-addon" id = "network_pairwise_table_legend">
						<i class = "fa fa-question"></i></button>
					</span>
						<span class="input-group-addon">
                           Show as % <input type = 'checkbox'  data-hivtrace-ui-role = 'pairwise_table_pecentage'> </input>
                        </span>
    				 </div>
    			  </div>
            </div>
            <div class = "row">
                   <table class = "table table-striped table-condensed table-hover" data-hivtrace-ui-role = "attribute_table">
                   </table>
              </div>
          </div>
      </div>


    </div>
  </div>
</div>

<img class="hidden" id="hyphy-chart-image" />
<canvas class="hidden" id="hyphy-chart-canvas"></canvas>

${h.javascript_link(app_root +  "hivtrace.js")}

<script>

var network_container     = '#network_tag',
    network_status_string = '#network_status_string',
    network_warning       = '#main-warning',
    histogram_tag         = '#histogram_tag',
    histogram_label       = '#histogram_label',
    button_bar_prefix     = 'network_ui_bar',
    csvexport_label       = '#csvexport',
    fasta_export_label    = '#fasta-export',
    filter_edges_toggle   = '#network_ui_bar_toggle_filter_edges',
    graph_summary_tag     = '#graph_summary_table',
    cluster_table         = '#cluster_table',
    parent_container      = '#top_level_tab_container',
    node_table            = '#node_table';


var init = function(data) {



  var graph = "trace_results" in data ? data.trace_results : data;
  var attributes = null;

  var user_graph = new hivtrace.clusterNetwork(graph, network_container, network_status_string, network_warning, button_bar_prefix, attributes, filter_edges_toggle, cluster_table, node_table, parent_container, {"no_cdc" : false});

  if (user_graph.is_empty()) {
      $('#main-tab').tab('show');
      d3.select ("#app-error").text ("This network contains no clusters and cannot be displayed").style ('display', null);
      d3.select (parent_container).selectAll ("li").classed ("disabled", true);
      d3.select (parent_container).selectAll ("li").selectAll ("a").each (function (d) { d3.select (d3.select (this).attr ("href")).style ('display', 'none')});
  } else {

      d3.select ("#app-error").style ('display', 'none');
      hivtrace.histogramDistances(graph, histogram_tag, histogram_label);
      hivtrace.graphSummary(graph, graph_summary_tag);

      ["#main-tab","#graph-tab","#clusters-tab","#nodes-tab","#attributes-tab"].forEach (function (tab) {
        d3.select (tab).classed ("disabled",false);
      });
      d3.select (parent_container).selectAll ("li").selectAll ("a").each (function (d) { d3.select (d3.select (this).attr ("href")).style ('display', null)});

      hivtrace.misc.export_table_to_text("#cluster-table-export", cluster_table);
      hivtrace.misc.export_table_to_text("#node-table-export", node_table);

      $("#main-tab a[data-toggle='tab']").on ("shown.bs.tab", function (e) {
            if (user_graph.needs_an_update) {
                user_graph.update(false, 0.5);
            }
      });

      $("#clusters-tab a[data-toggle='tab']").on ("shown.bs.tab", function (e) {
            user_graph.update_volatile_elements (d3.select (cluster_table));
      });

      $("#nodes-tab a[data-toggle='tab']").on ("shown.bs.tab", function (e) {
            user_graph.update_volatile_elements (d3.select (node_table));
      });

      if(data.lanl_trace_results > 0) {
        // Only if the comparison was done
        var lanl_network_container     = '#lanl-network_tag',
            lanl_network_status_string = '#lanl-network_status_string',
            lanl_network_warning       = '#lanl-main-warning',
            lanl_histogram_tag         = '#lanl-histogram_tag',
            lanl_histogram_label       = '#lanl-histogram_label',
            lanl_csvexport_label       = '#lanl-csvexport',
            lanl_button_bar_prefix     = 'lanl_network_ui_bar';

        d3.select ("#lanl-trace-results").classed ("disabled", false);

        var lanl_graph = data.lanl_trace_results;
        var lanl_graph_rendered = new hivtrace.clusterNetwork(lanl_graph, lanl_network_container, lanl_network_status_string, lanl_network_warning, lanl_button_bar_prefix, attributes, filter_edges_toggle, null, null, parent_container);
      }
   }
}

var initialize_cluster_network_graphs = function () {

  var raw_url = '${h.url_for( controller="/datasets", action="index" )}';
  var hda_id = '${trans.security.encode_id( hda.id )}';
  var url = raw_url + '/' + hda_id + '/display?to_ext=json';

  d3.json(url, function(results) {
    init(results);
  });

}

function in_progress() {
  return $('.progress').length > 0;
}

$(document).ready(function(){

$("#network_pairwise_chord_legend").popover(
{
     'html' : true,
     'trigger' : "click",
     'placement' : "bottom",
     'content' : "<div style = 'width : 250px'>\
                    This panel will show either a <a href = 'https://en.wikipedia.org/wiki/Chord_diagram'><b>chord diagram</b></a> (for category values) \
                    or a <b>scatterplot</b> (for continous values). They are useful to display the pairings \
                    for node attributes across links. Mouse over a particular color to display what attribute it\
                    corresponds to in <b>chord diagrams</b>. Mouse over a particular point to display what link \
                    corresponds to in <b>histograms</b>. <p/> \
                    To better understand a <b>chord diagram</b>, consider a network with 100 links. 40 of these links connect males to males, \
                    10 of the links connect females to females, and 50 - males to females. Males will be allocated (40 x 2 + 50) / 200 = .65, of the \
                    total circumference (pie slice size). The connection between males and females (with the males as the focus) will be given 50 / (50+40) = 5/9 of the \
                    weight. The connection between females and males (with the females as the focus) will be given 50 / (50+10) = 5/6 of the weight.\
        </div>\
     "
    }
);

$("#network_pairwise_table_legend").popover(
{
     'html' : true,
     'trigger' : "hover",
     'placement' : "bottom",
     'content' : "<div style = 'width : 250px'>\
		This table shows how many connections exist between each pair of attribute values. For example, if \
		a link connects a node which is \"Male\" and a node that is \"Female\", this link contributes \
		a count of 1 to both \"Male/Female\", and \"Female/Male\" cells of the table. A link connecting a \"Male\" node  \
		to a \"Male\" node will contribute 2 counts to the Male/Male cell.\
        </div>\
     "
    }
);

$("#network_pairwise_chart_legend").popover(
{
     'html' : true,
     'trigger' : "click",
     'placement' : "bottom",
     'content' : "<div style = 'width : 250px'>\
		This table shows how many connections exist between each pair of attribute values. For example, if\
		a link connects a node which is \"Male\" and a node that is \"Female\", this link contributes\
		a count of 1 to both \"Male/Female\", and \"Female/Male\" cells of the table. A link connecting a \"Male\" node\
		to a \"Male\" node will contribute 2 counts to the Male/Male cell.\
        </div>\
     "
    }
);

$("#network_pairwise_table_legend").on ("click", function (e) {
	e.preventDefault();
});

 $("#network_ui_search_help").popover(
    {
     'html' : true,
     'trigger' : "hover click",
     'placement' : "bottom",
     'content' : "<div style = 'width : 250px'>\
        Type in text to search for clusters and nodes whose <em>attributes contain the term</em>. <p/>\
        For example, typing in <code>MSM</code> will highlight nodes and/or clusters that \
        have 'MSM' in any of the data fields. <p/>\
        Type in space separated terms (<code>MSM IDU</code>) to search for <b>either</b> term. <p/>\
        Type in terms in quotes (<code>\"male\"</code>) will search for this <b>exact</b> term. <p/>\
        Type in <code>&lt;0.01</code> to search for nodes that have edges which are 0.01 (1%) or shorter. Any positive threshold works <p/>\
        Matching node <svg width = '20' height = '20' style = 'vertical-align: bottom; display: inline'><circle cx = '10' cy = '10' r = '7' class = 'node selected_object'> </circle></svg><p/>\
        Cluster where 25% of nodes match the term <svg width = '28' height = '28' style = 'vertical-align: bottom; display: inline'><circle cx = '14' cy = '14' r = '8' class = 'cluster'> </circle>\
        <path d = 'M 2 14 A 12 12 0 0 1 14 2'/ style = 'fill: none; stroke: #337AB7; stroke-width: 3px;'>\
        </svg><p/> \
        Cluster where 75% of nodes match the term <svg width = '28' height = '28' style = 'vertical-align: bottom; display: inline'><circle cx = '14' cy = '14' r = '8' class = 'cluster'> </circle>\
        <path d = 'M 2 14 A 12 12 0 1 1 14 26'/ style = 'fill: none; stroke: #337AB7; stroke-width: 3px;'>\
        </svg><p/> \
        Use the <code>Hide others</code> checkbox to automatically hide all clusters/nodes that do not match the search terms\
        <p/>\
        Use the <code>Show small clusters</code> checkbox to display small clusters that may have been hidden for clarity\
        </div>\
     "
    }
  );

  initialize_cluster_network_graphs();

  // *** HANDLERS ***
  $("#json_file").on ("change", function (e) {
  
    d3.selectAll(".my_progress").style("display", "block");

    var files = e.target.files; // FileList object

    if (files.length == 1) {
      var f = files[0];
      var reader = new FileReader();

      reader.onload = (function(theFile) {
        return function(e) {
            var container_id = '#tree_container';
            analysis_data = JSON.parse(e.target.result);
            init(analysis_data);
        };
      })(f);
      reader.readAsText(f);
    }
  });
});

</script>

</body>
</html>
