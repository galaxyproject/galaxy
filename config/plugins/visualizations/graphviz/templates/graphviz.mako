<!DOCTYPE HTML>
<html>
<head>

    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, user-scalable=no, minimum-scale=1.0, maximum-scale=1.0">

    <title>${hda.name | h} | ${visualization_name}</title>
    <%
        root = h.url_for( '/' )
    %>

    <script type="text/javascript" src="/static/scripts/libs/jquery/jquery.js"></script>

    ${h.stylesheet_link( root + 'static/plugins/visualizations/graphviz/static/css/style.css' )}
    ${h.javascript_link( root + 'static/plugins/visualizations/graphviz/static/js/cytoscape.min.js' )}
    ${h.javascript_link( root + 'static/plugins/visualizations/graphviz/static/js/collapse.js' )}
    ${h.javascript_link( root + 'static/plugins/visualizations/graphviz/static/js/toolPanelFunctions.js' )}
    ${h.javascript_link( root + 'static/plugins/visualizations/graphviz/static/js/graphVis.js' )}

</head>

## ----------------------------------------------------------------------------
<body>
    ${h.javascript_link( root + 'static/plugins/visualizations/graphviz/static/js/wz_tooltip.js' )}

    <script>
        function parseNodeEdge( data ){
            data = data.data[0];
            parseJson( data );
        }

        $(document).ready(function() {

            var hdaName = '${ hda.name | h }',
                hdaId = '${trans.security.encode_id( hda.id )}',
                hdaExt = '${hda.ext}',
                rawUrl = '${h.url_for( controller="/datasets", action="index" )}',
                apiUrl = '${h.url_for( "/" ) + "api/datasets"}',
                dataUrl;

            function errorHandler( xhr, status, message ){
                console.error(x, s, m);
                alert("error loading data:\n" + m);
            }

            switch( hdaExt ){
                case 'txt':
                    dataUrl = rawUrl + '/' + hdaId + '/display?to_ext=txt';
                    $.ajax(dataUrl, {
                        dataType    : 'text',
                        success     : parseTextMatrix,
                        error       : errorHandler
                    });
                    break;

                case 'json':
                    dataUrl = rawUrl + '/' + hdaId + '/display?to_ext=json';
                    $.ajax(dataUrl, {
                        dataType    : 'json',
                        success     : parseJson,
                        error       : errorHandler
                    });
                    break;

                default:
                    dataUrl = apiUrl + '/' + hdaId;
                    $.ajax(dataUrl, {
                        dataType    : 'json',
                        success     : parseNodeEdge,
                        error       : errorHandler,
                        data : {
                            data_type : 'raw_data',
                            provider  : 'node-edge'
                        }
                    });
            }
        });

    </script>
    <div id="cy"></div>

    <!-- left control panel for rendering controls, hiding nodes, etc. - initially hidden -->
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
    <!-- button to show above panel -->
    <a href="javascript:void(0);" class="slider-arrow show">&raquo;</a>

    <!-- right control panel for displaying node data - initially hidden -->
    <div id="nodeInfoDiv" class="nodePanel">
        <p> <strong>Node Description </strong></p>
        <br><br>
        <p> Please select a node </p>
    </div>
    <!-- button to show above panel -->
    <a href="javascript:void(0);" class="slider-arrow-forNode show">&laquo;</a>
</body>

</html>
