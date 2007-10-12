<html>

<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">

<head>

<link href="${h.url_for('/static/style/base.css')}" rel="stylesheet" type="text/css" />

<style>
* { z-index: 500;}
canvas { position: absolute; z-index: 10; } 
canvas.dragging { position: absolute; z-index: 1000; }
.node {  position: absolute; width: 100px; background: green; }
.input-terminal { width: 10px; height: 10px; background: red; position: absolute; bottom: 0; left: -17px; }
.output-terminal { width: 10px; height: 10px; background: blue; position: absolute; bottom: 0; right: -17px; }
.drag-terminal {  position: absolute; z-index: 1500; width: 10px; height: 10px; background: yellow; }
.input-terminal-active { background: yellow; }
.input-terminal-hover { background: yellow; border: solid black 1px; }
.unselectable { -moz-user-select: none; -khtml-user-select: none; user-select: none; }
</style>

<script type='text/javascript' src="/static/scripts/jquery.js"> </script>
<script type='text/javascript' src="/static/scripts/jquery.dimensions.js"> </script>
<script type='text/javascript' src="/static/scripts/jquery.ui.js"> </script>
<script>
var console = window.console;
console.log( "starting" );

## var old_shim_w = 10;
## var old_shim_h = 10;
## $.ui.plugin.add("draggable", "start", "grow", function(e,ui) {
##    old_shim_w = $("#shim").width();
##    old_shim_h = $("#shim").height();
## });
## $.ui.plugin.add("draggable", "drag", "grow", function(e,ui) {
##    if ( ui.draggable.rpos[1] > $("#shim").height() - 100 ) { $("#shim").css( "height", $("#shim").height() + 200 ) }
##    if ( ui.draggable.rpos[0] > $("#shim").width() - 100 ) { $("#shim").css( "width", $("#shim").width() + 200 ) }
## });
## $.ui.plugin.add("draggable", "stop", "grow", function(e,ui) {
##    if ( ui.draggable.rpos[1] > old_shim_h - 100 ) { $("#shim").css( "height", Math.ceil( ui.draggable.rpos[1] / 200 ) * 200 ) }
##    if ( ui.draggable.rpos[0] > old_shim_w - 100 ) { $("#shim").css( "width", Math.ceil( ui.draggable.rpos[0] / 200 ) * 200 ) }
##    old_shim_w = $("#shim").width();
##    old_shim_h = $("#shim").height();
## });
</script>

<script type='text/javascript'>

function OutputTerminal( element, datatype ) {
    this.element = element;
    this.connectors = [];
    this.datatype = datatype
}
$.extend( OutputTerminal.prototype, {
    connect: function ( connector ) {
        this.connectors.push( connector );
    },
    disconnect: function ( connector ) {
        this.connectors.splice( this.connectors.indexOf( connector ), 1 );
    },
    redraw: function () {
        $.each( this.connectors, function( _, c ) {
            c.redraw();  
        })
    }
} )

function InputTerminal( element, datatypes ) {
    this.element = element;
    this.connectors = [];
    this.max_connections = 1;
    this.datatypes = datatypes;
}
$.extend( InputTerminal.prototype, {
    connect: function ( connector ) {
        this.connectors.push( connector );
    },
    disconnect: function ( connector ) {
        this.connectors.splice( this.connectors.indexOf( connector ), 1 );
    },
    can_accept: function ( other ) {
        if ( this.connectors.length < this.max_connections ) {
            for ( t in this.datatypes ) {
                ## FIXME: No idea what to do about this case
                if ( other.datatype == "input" ) { return true; }
                if ( issubtype( other.datatype, this.datatypes[t] ) ) {
                    return true;
                }
            }
        }
        return false;
    },
    redraw: function () {
        $.each( this.connectors, function( _, c ) {
            c.redraw();  
        })
    }
} )

function Connector( handle1, handle2 ) {
    this.canvas = null;
    this.dragging = false;
}
$.extend( Connector.prototype, {
    connect: function ( t1, t2 ) {
        this.handle1 = t1;
        this.handle1.connect( this );
        this.handle2 = t2;
        this.handle2.connect( this );
    },
    destroy : function () {
        if ( this.handle1 ) {
            this.handle1.disconnect( this );
        }
        if ( this.handle2 ) {
            this.handle2.disconnect( this );
        }
        $(this.canvas).remove();
    },
    redraw : function () {
        if ( ! this.canvas ) {
            this.canvas = document.createElement( "canvas" );
            $("body").append( this.canvas );
            if ( this.dragging ) { this.canvas.style.zIndex = "300" }
        }
        // Find the position of each handle
        var o = $(this.handle1.element).offset();
        var start_x = o.left + 5;
        var start_y = o.top + 5;
        var o = $(this.handle2.element).offset();
        var end_x = o.left + 5;
        var end_y = o.top + 5;
        // Calculate canvas area
        var canvas_extra = 50;
        var canvas_min_x = Math.min( start_x, end_x );
        var canvas_max_x = Math.max( start_x, end_x );
        var canvas_min_y = Math.min( start_y, end_y );
        var canvas_max_y = Math.max( start_y, end_y );
        var cp_shift = Math.max( ( canvas_max_y - canvas_min_y ) / 2, 100 );
        var canvas_left = canvas_min_x - canvas_extra;
        var canvas_top = canvas_min_y - canvas_extra;
        var canvas_width = canvas_max_x - canvas_min_x + 2 * canvas_extra;
        var canvas_height = canvas_max_y - canvas_min_y + 2 * canvas_extra;
        // Place the canvas
        this.canvas.style.left = canvas_left + "px";
        this.canvas.style.top = canvas_top + "px";
        this.canvas.setAttribute( "width", canvas_width );
        this.canvas.setAttribute( "height", canvas_height );
        // Adjust points to be relative to the canvas
        start_x -= canvas_left;
        start_y -= canvas_top;
        end_x -= canvas_left;
        end_y -= canvas_top;
        // Draw the line
        var c = this.canvas.getContext("2d");
        c.lineCap = "round";
        c.strokeStyle = "#999";
        c.lineWidth = 7;
        c.beginPath();
        c.moveTo( start_x, start_y );
        c.bezierCurveTo( start_x + cp_shift, start_y, end_x - cp_shift, end_y, end_x, end_y );
        c.stroke();
        // Inner line
        c.strokeStyle = "#EEEEEE";
        c.lineWidth = 5;
        c.beginPath();
        c.moveTo( start_x, start_y );
        c.bezierCurveTo( start_x + cp_shift, start_y, end_x - cp_shift, end_y, end_x, end_y );
        c.stroke();
    }
} )

function enable_input_terminal( element, types ) {
    $(element).each( function() {
        var terminal = this.terminal = new InputTerminal( this, types );
        $(this).droppable( {
            tolerance: 'intersect',
    		accept: function( draggable ) {
    			return ( draggable.terminal ) && ( terminal.can_accept( draggable.terminal ) );
    		},
    		activeClass: 'input-terminal-active',
    		hoverClass: 'input-terminal-active',
    		drop: function( e, d ) {
    		    var source = d.draggable.element.terminal;
    		    var target = d.droppable.element.terminal;
    		    var c = new Connector();
    		    c.connect( source, target );
    		    c.redraw();
    		}
    	}); 
    });
}

function enable_output_terminal( element, type ) {
    $(element).each( function() {
       var terminal = this.terminal = new OutputTerminal( this, type ); 
       $(this).draggable( { 
           scroll: true,
           // containment: 'document',
           // appendTo: "body",
           // cursorAt: { top: 5, left: 5 },
           helper: function () { 
               var h = $( '<div class="drag-terminal" style="position: absolute;"></div>' ).get(0);
               h.terminal = new OutputTerminal( h );
               // // Already a connector? Destroy... no wait, don't
               // if ( this.terminal.connector ) {
               //     this.terminal.connector.destroy();
               // }
               var c = new Connector();
               this.drag_temp_connector = c;
               c.dragging = true;
               c.connect( this.terminal, h.terminal );
               return h;
           },
           drag: function ( e, options ) {
               options.helper.terminal.redraw();
           },
           stop: function( e, options ) {
               this.drag_temp_connector.destroy();
               // options.helper.remove();
           }
       });
   });
}

function enable_drag( element ) {
    $(element).draggable( {
        cursor: 'move',
        scroll: true,
        scrollSensitivity: 100,
        ## grow: true,
        start: function() {
            //$(this).css( 'z-index', '1000' );
        },
        drag: function() { 
            $(this).find( ".terminal" ).each( function() {
                this.terminal.redraw();
            })
        },
        stop: function() { 
            //$(this).css( 'z-index', '100' );
            $(this).find( ".terminal" ).each( function() {
                this.terminal.redraw();
            });
        }
    })
}

function add_node_for_tool( id ) {
    $.getJSON( "${h.url_for( action='get_tool_info' )}", { tool_id: id }, function ( data ) {
        var f = $("<div class='toolForm' style='position: absolute;'></div>");
        var title = $("<div class='toolFormTitle unselectable'>" + data.name + "</div>" )
        f.append( title );
        f.appendTo( "body" );
        var short_width = f.width();
        console.log( ">>", short_width );
        var b = $("<div class='toolFormBody'></div>")
        b.append( $( "<div class='form-row titleRow'>Inputs:</div>" ) )
        $.each( data.data_inputs, function( i, input ) {
            if ( input.data ) {
                t = $("<div class='terminal input-terminal'></div>")
                enable_input_terminal( t, input.extensions );
                b.append( $("<div class='form-row dataRow'><label>" + input.label + "</label><div>" + input.html + "</div></div>" ).prepend( t ) );
            }
            else
            {
                b.append( $("<div class='form-row fieldRow'><label>" + input.label + "</label><div>" + input.html + "</div></div>") );
            }
        });
        b.append( $( "<div class='form-row titleRow'>Outputs:</div>" ) )
        $.each( data.data_outputs, function( i, output ) {
            var t = $( "<div class='terminal output-terminal'></div>" );
            enable_output_terminal( t, output.extension );
            b.append( $("<div class='form-row dataRow'>" + output.name + "</div>" ).append( t ) );
        });
        f.append( b )
        // Fix width to computed width
        f.css( "width", f.width() );
        // Now add floats
        var width = null;
        var buttons = $("<div style='float: right'></div>");
        var big = true;
        buttons.append( $("<a href='#'>[+]</a>").click( function() { 
            b.children().not(".dataRow").toggle();
            b.children( ".dataRow" ).children( "label" ).toggle();
            f.css( "width", big ? short_width : width );
            big = ! big;
            f.find( ".terminal" ).each( function() {
                this.terminal.redraw();
            });
        } ) );
        width = f.width();
        buttons.prependTo( title );
        width += ( buttons.width() + 5 );
        short_width += ( buttons.width() + 5 );
        f.css( "width", width );
        // Make draggable
        enable_drag( f );
    });
}

var ext_to_type = null;
var type_to_type = null;

function issubtype( child, parent ) {
    child = ext_to_type[child];
    parent = ext_to_type[parent];
    return ( parent in type_to_type[child] );
}

$( function() {
    $.getJSON( "${h.url_for( action='get_datatypes' )}", function( data ) {
        ext_to_type = data.ext_to_class_name;
        type_to_type = data.class_to_classes;
        parent.notify();
    });
})

</script>
<style>
body {
    background: white url(${h.url_for('/static/images/light_gray_grid.gif')}) repeat;
}
#tool-area {
    position: absolute;
    top: 0; left: 0; bottom: 0;
    width: 300px;
    overflow: scroll;
}
div.toolMenu {
    margin: 5px;
}
div.toolSectionPad {
    margin: 0;
    padding: 0;
    height: 5px;
    font-size: 0px;
}
div.toolSectionDetailsInner { 
  margin-left: 5px;
  margin-right: 5px;
}
div.toolSectionTitle {
  padding-bottom: 0px;
  font-weight: bold;
}
div.toolTitle {
  padding-top: 5px;
  padding-bottom: 5px;
  margin-left: 16px;
  margin-right: 10px;
  display: list-item;
  list-style: square outside;
}
div.titleRow {
    font-weight: bold;
    border-bottom: dotted gray 1px;
    margin-bottom: 0.5em;
    padding-bottom: 0.25em;
}
div.form-row {
  position: relative;
  margin-bottom: 0.5em;
}
div.toolForm {
    margin: 10px;
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

</style>

</head>

<body>
    ## <div id="shim" style="position: absolute; top: 0px; left: 0px; width: 10px; height: 10px; background: red; opacity: 0.1"></div>
</body>

</html>