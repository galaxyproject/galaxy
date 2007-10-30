<html>

<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">

<head>

<link href="${h.url_for('/static/style/base.css')}" rel="stylesheet" type="text/css" />

<style>
* { z-index: 100;}
canvas { position: absolute; z-index: 10; } 
canvas.dragging { position: absolute; z-index: 1000; }
.node {  position: absolute; width: 100px; background: green; }
.input-terminal { width: 12px; height: 12px; background: url(${h.url_for('/static/style/workflow_circle_open.png')}); position: absolute; bottom: 0; left: -16px; }
.output-terminal { width: 12px; height: 12px; background: url(${h.url_for('/static/style/workflow_circle_open.png')});; position: absolute; bottom: 0; right: -16px; }
.drag-terminal {  position: absolute; z-index: 1500; width: 10px; height: 10px; display: none; }
.input-terminal-active { background: url(${h.url_for('/static/style/workflow_circle_green.png')}); }
## .input-terminal-hover { background: yellow; border: solid black 1px; }
.unselectable { -moz-user-select: none; -khtml-user-select: none; user-select: none; }
img { border: 0; }
</style>

<script type='text/javascript' src="/static/scripts/jquery.js"> </script>
<script type='text/javascript' src="/static/scripts/jquery.dimensions.js"> </script>
<script type='text/javascript' src="/static/scripts/jquery.ui.js"> </script>
<script type='text/javascript' src="/static/scripts/jquery.hoverIntent.js"> </script>
<script type='text/javascript' src="/static/scripts/galaxy.workflow_editor.canvas.js"> </script>

<script type='text/javascript'>

var workflow = null;

// Global state for the whole workflow
function reset() {
    if ( workflow ) {
        workflow.remove_all();
    }
    parent.workflow = workflow = new Workflow();
    // Start at the middle of the canvas
    $(window).scrollTop( 2500 );
    $(window).scrollLeft( 2500 );
}

// Add a new step to the workflow by tool id
function add_node_for_tool( id, title ) {
    node = prebuild_node_for_tool( id, title );
    workflow.add_node( node );
    workflow.activate_node( node );
    $.ajax( {
        url: "${h.url_for( action='get_tool_info' )}", 
        data: { tool_id: id }, 
        dataType: "json",
        success: function( data ) {
            node.init_field_data( data );
        },
        error: function() {
            node.error( "error loading field data" );
        }
    });
};

$( function() {
    // Initialize workflow state
    reset();
    // Shim (the background of the editor area) causes loss of focus
    $("#shim").click( workflow.clear_active_node ).hoverIntent( {
        over: function () { $("div.toolForm").fadeTo( "fast", 0.7 ) },
        out: function () { $("div.toolForm").fadeTo( "fast", 1.0 ) },
        interval: 300
    });
    // Load the datatype info
	$.getJSON( "${h.url_for( action='get_datatypes' )}", function( data ) {
	    populate_datatype_info( data );
        if ( parent ) { parent.notify(); }
    });
});
</script>

<style>
body {
    margin: 0; padding: 0;
    background: white url(${h.url_for('/static/images/light_gray_grid.gif')}) repeat;
}

div.buttons img {
    width: 16px; height: 16px;
    cursor: pointer;
}

div.toolFormTitle {
    cursor: move;
    min-height: 16px;
}

div.titleRow {
    font-weight: bold;
    border-bottom: dotted gray 1px;
    margin-bottom: 0.5em;
    padding-bottom: 0.25em;
}
div.form-row {
  position: relative;
  margin-top: 0.5em;
  margin-bottom: 0.5em;
}
div.toolForm {
    margin: 6px;
}

div.toolForm-active {
    border: solid #8080FF 4px;
    margin: 3px;
}

div.tool-node {
    position: absolute;
}

div.tool-node-error div.toolFormTitle {
    background: #FFCCCC;
    border-color: #AA6666;
}
div.tool-node-error {
    border-color: #AA6666;
}

#canvas-area {
    position: absolute;
    top: 0; left: 305px; bottom: 0; right: 0;
    border: solid red 1px;
    overflow: none;
}

.form-row {
    
}
.form-row-body {

}
.form-row-clear {
    clear: both;
}

div.rule {
    height: 0;
    border: none;
    border-bottom: dotted black 1px;
}

</style>

</head>

<body>
    <div id="shim" style="position: absolute; top: 0px; left: 0px; width: 5000px; height: 5000px;"></div>
</body>

</html>