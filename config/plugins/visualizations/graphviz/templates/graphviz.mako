<!DOCTYPE HTML>
<html>
<head>

    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, user-scalable=no, minimum-scale=1.0, maximum-scale=1.0">

    <title>${hda.name} | ${visualization_name}</title>
<%
    root = h.url_for( '/' )
%>
<script type="text/javascript" src="/static/scripts/libs/jquery/jquery.js"></script>
    ${h.stylesheet_link( root + 'plugins/visualizations/graphviz/static/css/style.css' )}
    
    ${h.javascript_link( root + 'plugins/visualizations/graphviz/static/js/jquery.qtip.js' )}
    ${h.javascript_link( root + 'plugins/visualizations/graphviz/static/js/cytoscape.min.js' )}
    ${h.javascript_link( root + 'plugins/visualizations/graphviz/static/js/collapse.js' )}
    ${h.javascript_link( root + 'plugins/visualizations/graphviz/static/js/toolPanelFunctions.js' )}
    ${h.javascript_link( root + 'plugins/visualizations/graphviz/static/js/graphVis.js' )}

</head>

## ----------------------------------------------------------------------------
<body>
    ${h.javascript_link( root + 'plugins/visualizations/graphviz/static/js/wz_tooltip.js' )}

    <script>
        $(document).ready(function() {
        
            var hdaId   = '${trans.security.encode_id( hda.id )}',
            hdaExt  = '${hda.ext}',
            dataUrl = "${h.url_for( controller='/datasets', action='index')}/" + hdaId + "/display?to_ext=" + hdaExt;

			// var reader = new FileReader();
			
             $.ajax({
                 'async': true,
                 'global': false,
                 'url': dataUrl,
                 'dataType': "json",
                 'success': function(data) {
                     parseJson(data);
                     //  createGraph(data);
                 },
                 'error': function(data) {
                 
							jQuery.get(dataUrl, function(data) {
  		 				
  							var lines = data.split('\n');
                         var chars;
                         for (var line = 0; line < lines.length; line++) {
                             chars = lines[line].split(/,?\s+/); // split by comma or space

                             demoNodes.push({
                                 data: {
                                     id: chars[0],
                                     label: chars[0]
                                 }
                             });

                             for (var i = 1; i < chars.length; i++) {
                                 demoEdges.push({
                                     data: {
                                         source: chars[0],
                                         target: chars[i],
                                         id: chars[0] + chars[i],

                                     }
                                 })
                             }
                         }
					  
  								parseAndCreate(demoNodes, demoEdges);
  
							});                     
                     
                  
                 }
             });

        } );

    </script>
    <div id="cy"></div>
    <div class="panel">
        <br>
        <div id="mainselection">
            <select name="select" id="selectShape">
                <option value="random" selected>Choose the shape</option>
                <option value="random">random</option>
                <option value="circle">circle</option>
                <option value="grid">grid</option>
                <option value="concentric">concentric</option>
                <option value="breadthfirst">breadthfirst</option>
            </select>
        </div>
        <br>

        <input type="checkbox" class="css-checkbox" name="nlabelSelection" id="nodeLabelCheck" />
        <label for="nodeLabelCheck" name="nodeLabelCheck" class="css-label">
            show node label
        </label>
        <br>
        <br>

        <input type="checkbox" class="css-checkbox" name="elabelSelection" id="linkLabelCheck" />
        <label for="linkLabelCheck" name="nodeLabelCheck" class="css-label">
            show edge label
        </label>
        <br>
        <br>

        <input type="checkbox" class="css-checkbox" name="showOutgoing" id="showOutNode">
        <label for="showOutNode" name="nodeLabelCheck" class="css-label">
            highlight outgoing nodes
        </label>
        <br>
        <br>

        <input type="checkbox" class="css-checkbox" name="showInComing" id="showInNode">
        <label for="showInNode" name="nodeLabelCheck" class="css-label">
            highlight incoming nodes
        </label>
        <br>
        <br>

        <input type="checkbox" class="css-checkbox" name="showCollapsedNodeNum" id="collapseCount">
        <label for="collapseCount" name="nodeLabelCheck" class="css-label">
            show the number of collapsed nodes
        </label>
        <br>
        <br>

        <input type="button" class="btn colNode" name="collapseNode" id="collapseNode" value="Collapse Selected Node " onclick="colNode()" disabled="disabled">
        <br>
        <br>

        <input type="button" class="btn expNode" name="expandNode" id="expandNode" value="Expand Selected Node " disabled="disabled">
        <br>
        <br>


        <input type="button" class="btn delNode" name="deleteNodes" id="deleteNodes" value="Delete Selected Nodes " onclick="deleteSelectedNodes()" disabled="disabled">
        <br>
        <br>


        <input type="button" class="btn" name="restoreNodes" id="restoreNodes" value="Restore Deleted Nodes" onclick="restoreDeletedNodes()">
        <br>
        <br>
        <input type="button" class="btn" name="restore" id="restore" value="Restore The Structure  " onclick="restorGraphStructure()">
        <br>
        <br>
        <input type="button" class="btn" name="export" id="export" value="Export PNG" onclick="exportFunction()">
        <br>
        <br>
        <input type="button" class="btn" name="manual" id="manual" value="More Info" onclick="window.open('https://github.com/eteriSokhoyan/GraphVis')">
        <br>
        <br>
    </div>

    <a href="javascript:void(0);" class="slider-arrow show">&raquo;</a>
    <div id="nodeInfoDiv" class="nodePanel"> 
        <p> <strong>Node Description </strong></p>
        <br><br>
        <p> Please select a node </p>
    </div>
    <a href="javascript:void(0);" class="slider-arrow-forNode show">&laquo;</a>
</body>

</html>
