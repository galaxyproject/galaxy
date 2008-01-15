<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">

<head>

<link href="${h.url_for('/static/style/base.css')}" rel="stylesheet" type="text/css" />
<link rel="stylesheet" type="text/css" href="${h.url_for('/static/style/panel_layout.css')}"></link>
<!--[if IE]>
<link rel="stylesheet" type="text/css" href="${h.url_for('/static/style/panel_layout_ie.css')}"></link>
<![endif]-->

<style type="text/css">
/* Wider right panel */
#center       { right: 309px; }
#right-border { right: 300px; }
#right        { width: 300px; }
## /* Relative masthead size */
## #masthead { height: 2.5em; }
## #masthead div.title { font-size: 1.8em; }
## #left, #left-border, #center, #right-border, #right {
##     top: 2.5em;
##     margin-top: 7px;
## }
</style>

<script type='text/javascript' src="/static/scripts/jquery.js"> </script>
<script type='text/javascript' src="/static/scripts/jquery.dimensions.js"> </script>
<script type='text/javascript' src="/static/scripts/jquery.ui.js"> </script>
<script type='text/javascript' src="/static/scripts/jquery.fx.js"> </script>
<script type='text/javascript' src="/static/scripts/jquery.fx.drop.js"> </script>
<script type='text/javascript' src="/static/scripts/jquery.form.js"> </script>
<script type='text/javascript' src="/static/scripts/jquery.json.js"> </script>
<script type='text/javascript' src="/static/scripts/jquery.center.js"> </script>
<script type='text/javascript' src="/static/scripts/galaxy.panels.js"> </script>
<script type='text/javascript' src="/static/firebug/firebug.js"> </script>

<script type='text/javascript'>
/* Dialog and menu handling tools to be moved to galaxy.layout.js */

function hide_modal() {
    $("#overlay, .dialog-box" ).hide( { method: 'drop', direction: 'up' } );
};

function show_modal( title, body, buttons ) {
    $( ".dialog-box" ).find( ".title-content" ).html( title );
    var b = $( ".dialog-box" ).find( ".buttons" ).html( "" );
    if ( buttons ) {
        $.each( buttons, function( name, value ) {
            b.append( $( '<button/>' ).text( name ).click( value ) );
            b.append( " " );
        });
        b.show();
    } else {
        b.hide();
    }
    if ( body == "progress" ) {
        body = $( "<img src='${h.url_for('/static/images/yui/rel_interstitial_loading.gif')}'/>" );
    }
    $( ".dialog-box" ).find( ".body" ).html( body );
    // $( "#overlay").show();
    if ( ! $(".dialog-box").is( ":visible" ) ) {
        $("#overlay, .dialog-box").show( {method: 'drop', direction: 'up' } );
    } else {
        $(".dialog-box").center( "horizontal" );
    }
};
</script>

<script type='text/javascript'>

$( function() {
    if( $.browser.mozilla ) {
        $("body").addClass( "mozilla" );
    }
    
    // $.blockUI( "<b><img style='vertical-align: middle;' src='${h.url_for( '/static/style/data_running.gif' )}'/> Loading Galaxy Workflow Editor...</b>", 
    //           { border: "solid #AAAA66 1px", background: "#FFFFCC", padding: "20px", width: "auto" } );
               
    make_left_panel( $("#left"), $("#center"), $("#left-border" ) );
    make_right_panel( $("#right"), $("#center"), $("#right-border" ) );

    // Insert helper divs for panels and popups
    $("<div id='DD-helper' style='background: white; top: 0; left: 0; width: 100%; height: 100%; position: absolute; z-index: 9000;'></div>")
        .css("background", "transparent").appendTo("body").hide();
    $("<div id='popup-helper' style='background: white; top: 0; left: 0; width: 100%; height: 100%; position: absolute; z-index: 15000;'></div>")
        .css("background", "transparent").appendTo("body").hide();
      
    // Center the loading indicator
    $(".dialog-box" ).center( "horizontal" );
    
    $(document).ajaxError( function ( e, x ) {
        // console.error( "AJAX:", e, ", ", x );
        $("#error-display").empty()
            .append( $("<div/>").html( x.responseText ) )
            .append( $("<div><a>close</a></div>" ).click( function() { $("#error-display").hide(); } ) )
            .show();
        return false;
    });
    
    make_popupmenu( "#optionsbutton", {
        "Create <b>new</b> workflow" : create_new_workflow_dialog,
        "<b>Save</b> current workflow" : save_current_workflow,
        "<b>Load</b> a stored workflow" : load_workflow
    });
    
    // Unload handler
    window.onbeforeunload = function() {
        if ( workflow && workflow.has_changes ) {
            return "There are unsaved changes to your workflow which will be lost.";
        }
    }
});

function notify() {
    %if workflow_name:
    $.ajax( {
       url: "${h.url_for( action='load_workflow' )}",
       data: { workflow_name: "${workflow_name}" },
       dataType: 'json',
       success: function( data ) {
            window.frames.canvas.reset();
            workflow.from_simple( data );
            hide_modal();
        },
        beforeSubmit: function( data ) {
            show_modal( "Loading workflow", "progress" );
        }
    });
    %else:
    hide_modal();
    %endif
};

function show_form_for_tool( text, node ) {
    // $("#overlay, #modalwrapper" ).show();
    //$("#modal iframe").attr( 'src', "${h.url_for( action='tool_form' )}?tool_id=" + tool_id ).load( function () {
    //    $("#modalloadwrapper").hide();
    //});
    // $("#right-content").load( "${h.url_for( action='tool_form' )}", { tool_id: tool_id }, function () {
    //     
    // });
    $("#right-content").html( text );
    $("#right-content").find( "form" ).ajaxForm( {
        method: 'POST',
        dataType: 'json',
        success: function( data ) { 
            node.update_field_data( data );
        },
        beforeSubmit: function( data ) { data.push( { name: 'tool_state', value: node.tool_state } ); }
    }).each( function() {
        form = this;
        $(this).find( "select[refresh_on_change='true']").change( function() {
            $(form).submit();
        });
    });
}

var save_current_workflow = function () {
    var body = $("#save-dialog-form").clone();
    if ( workflow.name ) {
        body.find( "input[name='workflow_name']" ).get(0).value = workflow.name;
    }
    body.find( "input[name='workflow_name']" ).get(0).focus();
    var form = body.find( "form" ).ajaxForm( {
        dataType: 'json',
        success: function( data ) { 
            var body = $("<div></div>").text( data.message );
            if ( data.errors ) {
                body.addClass( "warningmark" )
                var errlist = $( "<ul/>" );
                $.each( data.errors, function( i, v ) {
                    $("<li></li>").text( v ).appendTo( errlist );
                });
                body.append( errlist );
            } else {
                body.addClass( "donemark" );
            }
            workflow.name = data.name;
            workflow.has_changes = false;
            workflow.stored = true;
            show_modal( "Workflow saved", body, {
                "Ok" : function () { hide_modal(); }
            });
        },
        beforeSubmit: function( data ) {
            data.push( { name: 'workflow_data', value: $.toJSON( workflow.to_simple() ) } );
            show_modal( "Saving workflow", "progress" );
        }
    });
    show_modal( "Save workflow", body, {
        "Cancel" : hide_modal,
        "Save": function() { form.submit() }
    } );
}

var load_workflow = function () {
    var body = $("#load-dialog-form").clone();
    var form = body.find( "form" ).ajaxForm( {
        dataType: 'json',
        success: function( data ) {
            window.frames.canvas.reset();
            workflow.from_simple( data );
            show_modal( "Workflow loaded", "Workflow loaded.", {
                "Ok" : function () { hide_modal(); }
            });
        },
        beforeSubmit: function( data ) {
            show_modal( "Loading workflow", "progress" );
        }
    });
    if ( workflow.has_changes ) {
        body.prepend( "<div class='warningmark'>Your unsaved changes will be lost!</div>" );
    }
    show_modal( "Load workflow", body, {
        "Cancel" : hide_modal,
        "Load": function() { form.submit() }
    } );
}

var clear_workflow = function () {
    window.frames.canvas.reset();
    hide_modal();
}

var create_new_workflow_dialog = function () {
    if ( workflow.has_changes ) {
        show_modal( "Create new workflow",
                    "Your workflow has unsaved changes which will be lost", {
            "Cancel" : hide_modal,
            "Continue": clear_workflow
        });
    } else {
        clear_workflow();
    }
}

function add_node_for_tool( id, title ) {
   window.frames.canvas.add_node_for_tool( id, title );
}

</script>

<style>

#left {
    background: #C1C9E5 url(${h.url_for('/static/style/menu_bg.png')}) top repeat-x;
}

div.toolMenu {
    margin: 5px;
    margin-left: 10px;
    margin-right: 10px;
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
div.toolTitleDisabled {
    padding-top: 5px;
    padding-bottom: 5px;
    margin-left: 16px;
    margin-right: 10px;
    display: list-item;
    list-style: square outside;
    font-style: italic;
    color: gray;
}
div.toolFormRow {
    position: relative;
}


#right-content {
    margin: 5px;
}

#error-display {
    display: none;
    position: fixed;
    top: 5%; left: 5%; width: 90%; height: 90%;
    border: solid red 10px;
    background: #FFDDDD;
    z-index: 50000;
    overflow: auto;
}

</style>

</head>
    <body scroll="no">
        
        <div id="error-display"></div>
        
        <div id="overlay">
            <div id="overlay-inner"></div>
            <div class="dialog-box">
                <div class="title">
                    <div class="center-block-outer">
                        <div class="center-block-inner">
                            <div class="title-content">Loading workflow editor...</div>
                        </div>
                    </div>
                </div>
                <div class="body"><img src="${h.url_for('/static/images/yui/rel_interstitial_loading.gif')}" /></div>
                <div class="buttons" style="display: none;"></div>
                <div class="underlay"></div>
            </div>
        </div>

        <div id="masthead">
            <div class="title"><b>Galaxy workflow editor</div>
            ## <iframe name="galaxy_masthead" src="${h.url_for( controller='root', action='masthead' )}" width="38" height="100%" frameborder="0" scroll="no" style="margin: 0; border: 0 none; width: 100%; height: 38px; overflow: hidden;"> </iframe>
        </div>

        <div id="left">
            <div class="unified-panel-header" unselectable="on">
                <div class="center-block-outer">
                    <div class="center-block-inner">Tools</div>
                </div>
            </div>
            
            <div class="unified-panel-body" style="overflow: auto;">
                <div class="toolMenu">
                    <div class="toolSectionList">
                    %for i, section in enumerate( app.toolbox.sections ):
                       %if i > 0:
                          <div class="toolSectionPad"></div> 
                       %endif
                       <div class="toolSectionTitle" id="title_${section.id}">
                          <span>${section.name}</span>
                       </div>
                       <div id="${section.id}" class="toolSectionBody">
                          <div class="toolSectionBg">
                             %for tool in section.tools:
                                %if not tool.hidden:
                                    %if tool.is_workflow_compatible:
                                        <div class="toolTitle ">
                                            %if "[[" in tool.description and "]]" in tool.description:
                                                ${tool.description.replace( '[[', '<a id="link-${tool.id}" href="javascript:add_node_for_tool( ${tool.id} )">' % tool.id ).replace( "]]", "</a>" )}
                                            %elif tool.name:
                                                <a id="link-${tool.id}" href="javascript:add_node_for_tool( '${tool.id}', '${tool.name}' )">${tool.name}</a> ${tool.description}
                                            %else:
                                                <a id="link-${tool.id}" href="javascript:add_node_for_tool( '${tool.id}', '${tool.name}' )">${tool.description}</a>
                                            %endif
                                        </div>
                                    %else:
                                        <div class="toolTitleDisabled">
                                            %if "[[" in tool.description and "]]" in tool.description:
                                                ${tool.description.replace( '[[', '' % tool.id ).replace( "]]", "" )}
                                            %elif tool.name:
                                                ${tool.name} ${tool.description}
                                            %else:
                                                ${tool.description}
                                            %endif
                                        </div>
                                    %endif
                                %endif
                            %endfor
                          </div>
                       </div>
                    %endfor
                    </div>
                </div>
            </div>
        </div>
        <div id="left-border"><div id="left-border-inner" style="display: none;"></div></div>
        <div id="center">
            <div class="unified-panel-header" unselectable="on">
                <div class="center-block-outer" style="float: right">
                    <div class="center-block-inner"><div id="optionsbutton" class="button">Options &#9662;</div></div>
                </div>
                <div class="center-block-outer">
                    <div class="center-block-inner">Workflow canvas</div>
                </div>
            </div>
            <div class="unified-panel-body" style="">
                <iframe name="canvas" width="100%" height="100%" frameborder="0" style="position: absolute;" src="${h.url_for( action='editor_canvas' )}"></iframe>
            </div>
        </div>
        <div id="right-border"><div id="right-border-inner" style="display: none;"></div></div>
        <div id="right">
            <div class="unified-panel-header" unselectable="on">
                <div class="center-block-outer">
                    <div class="center-block-inner">Details</div>
                </div>
            </div>
            <div class="unified-panel-body" style="overflow: auto;">
                <div id="right-content"></div>
            </div>
        </div>

        <div id="templates" style="display: none">
            <div id="load-dialog-form">
                <form id="load-dialog-form-form" action="${h.url_for( action='load_workflow' )}" method="post">
                    <div class="form-row">
                        <label>Workflow name:</label>
                        <input name="workflow_name" type="text" focus="true" />
                    </div>
                </form>
            </div>
            <div id="save-dialog-form">
                <form id="save-dialog-form-form" action="${h.url_for( action='save_workflow' )}" method="post">
                    <div class="form-row">
                        <label>Workflow name:</label>
                        <input name="workflow_name" type="text" focus="true" />
                    </div>
                </form>
            </div>
        </div>
    </body>
</html>