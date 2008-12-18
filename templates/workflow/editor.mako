<%inherit file="/base_panels.mako"/>

<%def name="title()">Galaxy Workflow Editor</%def>

<%def name="late_javascripts()">
    <script type='text/javascript' src="${h.url_for('/static/scripts/galaxy.panels.js')}"> </script>
    <script type="text/javascript">
        ensure_dd_helper();
        make_left_panel( $("#left"), $("#center"), $("#left-border" ) );
        make_right_panel( $("#right"), $("#center"), $("#right-border" ) );
        ## handle_minwidth_hint = rp.handle_minwidth_hint;
    </script>
</%def>

<%def name="javascripts()">
    
    ${parent.javascripts()}
    
    <!--[if IE]>
    <script type='text/javascript' src="${h.url_for('/static/scripts/excanvas.js')}"> </script>
    <![endif]-->
    <script type='text/javascript' src="${h.url_for('/static/scripts/jquery.js')}"> </script>
    <script type='text/javascript' src="${h.url_for('/static/scripts/jquery.ui.js')}"> </script>
    <script type='text/javascript' src="${h.url_for('/static/scripts/galaxy.ui.scrollPanel.js')}"> </script>
    <script type='text/javascript' src="${h.url_for('/static/scripts/jquery.hoverIntent.js')}"> </script>
    <script type='text/javascript' src="${h.url_for('/static/scripts/jquery.form.js')}"> </script>
    <script type='text/javascript' src="${h.url_for('/static/scripts/jquery.json.js')}"> </script>

    <script type='text/javascript' src="${h.url_for('/static/scripts/galaxy.workflow_editor.canvas.js')}"> </script>
    
    <!--[if lt IE 7]>
    <script type='text/javascript'>
    window.lt_ie_7 = true;
    </script>
    <![endif]-->
    
    <script type='text/javascript'>
    $( function() {
        if ( window.lt_ie_7 ) {
            show_modal(
                "Browser not supported",
                "Sorry, the workflow editor is not supported for IE6 and below."
            );
            return;
        }
        // Initialize workflow state
        reset();
        // Load the datatype info
        $.ajax( {
            url: "${h.url_for( action='get_datatypes' )}",
            dataType: "json",
            cache: false,
            success: function( data ) {
                populate_datatype_info( data );
                // Load workflow definition
                $.ajax( {
                    url: "${h.url_for( action='load_workflow' )}",
                    data: { id: "${trans.security.encode_id( workflow_id )}", "_": "true" },
                    dataType: 'json',
                    cache: false,
                    success: function( data ) {
                         reset();
                         workflow.from_simple( data );
                         workflow.has_changes = false;
                         scroll_to_nodes();
                         hide_modal();
                     },
                     beforeSubmit: function( data ) {
                         show_modal( "Loading workflow", "progress" );
                     }
                });
            }
        });
        
        $(document).ajaxError( function ( e, x ) {
            show_modal( "Server error", x.responseText, { "Ignore error" : hide_modal } );
            return false;
        });
        
        ## make_popupmenu( "#optionsbutton", {
        ##     "Create <b>new</b> workflow" : create_new_workflow_dialog,
        ##     "<b>Save</b> current workflow" : save_current_workflow,
        ##     "<b>Load</b> a stored workflow" : load_workflow
        ## });
        
        $("#save-button").click( function() { save_current_workflow(); } );
        $("#close-button").click( function() { close_editor(); } );
        
        // Unload handler
        window.onbeforeunload = function() {
            if ( workflow && workflow.has_changes ) {
                return "There are unsaved changes to your workflow which will be lost.";
            }
        }
        
        // Drag/scroll canvas
        $("#canvas-container").draggable({
            drag: function( _, ui ) {
                x = ui.position.left;
                y = ui.position.top;
                // Limit range
                x = Math.min( x, 0 );
                y = Math.min( y, 0 );
                x = Math.max( x, - ( $(this).width() - $(this).parent().width() ) )
                y = Math.max( y, - ( $(this).width() - $(this).parent().width() ) )
                // Constrain position
                ui.position.left = x;
                ui.position.top = y;
            }
        });
        
        // Tool menu
        $( "div.toolSectionBody" ).hide();
        $( "div.toolSectionTitle > span" ).wrap( "<a href='#'></a>" );
        var last_expanded = null;
        $( "div.toolSectionTitle" ).each( function() { 
           var body = $(this).next( "div.toolSectionBody" );
           $(this).click( function() {
               if ( body.is( ":hidden" ) ) {
                   if ( last_expanded ) last_expanded.slideUp( "fast" );
                   last_expanded = body;
                   body.slideDown( "fast" );
               }
               else {
                   body.slideUp( "fast" );
                   last_expanded = null;
               }
           });
        });
    });

    var workflow = null;
    
    // Global state for the whole workflow
    function reset() {
        if ( workflow ) {
            workflow.remove_all();
        }
        workflow = new Workflow();
    }
    
    function scroll_to_nodes() {
        // Scroll to the top left node
        if ( $("div.toolFormInCanvas").length > 0 ) {
            var x = 5000, y = 5000;
            $("div.toolFormInCanvas").each( function() {
                x = Math.min( x, $(this).position().left );
                y = Math.min( y, $(this).position().top );
            });
            x = Math.min( - x + 20, 0 );
            y = Math.min( - y + 20, 0 );
            $("#canvas-container").css( { left: x, top: y } );
        }
    }
    
    // Add a new step to the workflow by tool id
    function add_node_for_tool( id, title ) {
        node = prebuild_node( 'tool', title, id );
        workflow.add_node( node );
        workflow.activate_node( node );
        $.ajax( {
            url: "${h.url_for( action='get_new_module_info' )}", 
            data: { type: "tool", tool_id: id, "_": "true" },
            global: false,
            dataType: "json",
            success: function( data ) {
                node.init_field_data( data );
            },
            error: function( x, e ) {
                var m = "error loading field data"
                if ( x.status == 0 ) {
                    m += ", server unavailable"
                }
                node.error( m );
            }
        });
    };
    
    function add_node_for_module( type, title ) {
        node = prebuild_node( type, title );
        workflow.add_node( node );
        workflow.activate_node( node );
        $.ajax( {
            url: "${h.url_for( action='get_new_module_info' )}", 
            data: { type: type, "_": "true" }, 
            dataType: "json",
            success: function( data ) {
                node.init_field_data( data );
            },
            error: function( x, e ) {
                var m = "error loading field data"
                if ( x.status == 0 ) {
                    m += ", server unavailable"
                }
                node.error( m );
            }
        });
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
            type: 'POST',
            dataType: 'json',
            success: function( data ) {
                node.update_field_data( data );
            },
            beforeSubmit: function( data ) {
                data.push( { name: 'tool_state', value: node.tool_state } );
                data.push( { name: '_', value: "true" } );
                $("#tool-form-save-button").each( function() {
                    this.value = "Saving...";
                    this.disabled = true;
                });
            }
        }).each( function() {
            form = this;
            $(this).find( "select[refresh_on_change='true']").change( function() {
                $(form).submit();
            });
        });
    }
    
    var close_editor = function() {
        <% next_url = h.url_for( controller='root', m_c='workflow' ) %>
        if ( workflow && workflow.has_changes ) {
            do_close = function() {
                window.onbeforeunload = undefined;
                window.document.location = "${next_url}"
            };
            show_modal( "Close workflow editor",
                        "There are unsaved changes to your workflow which will be lost.",
                        {
                            "Cancel" : hide_modal,
                            "Save Changes" : function() {
                                save_current_workflow( do_close );
                            }
                        }, {
                            "Don't Save": do_close
                        } );
        } else {
            window.document.location = "${next_url}"
        }
    }
    
    var save_current_workflow = function ( success_callback ) {
        show_modal( "Saving workflow", "progress" );
        $.ajax( {
            url: "${h.url_for( action='save_workflow' )}",
            type: "POST",
            data: {
                id: "${trans.security.encode_id( workflow_id )}",
                workflow_data: $.toJSON( workflow.to_simple() ),
                "_": "true"
            },
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
                if ( success_callback ) {
                    success_callback();
                }
                if ( data.errors ) {
                    show_modal( "Saving workflow", body, { "Ok" : hide_modal } );
                } else {
                    hide_modal();
                }
            }
        });
    }
    
    ## var update_canvas_map = function() {
    ##     var c = $("#canvas-map-canvas").get(0).getContext("2d");
    ##     var cp = $("#canvas-container").position();
    ##     c.clearRect( 0, 0, 100, 100 );
    ##     c.strokeStyle = "rgb(200,0,0)";
    ##     c.strokeRect ( -cp.left / 50, -cp.top / 50, $("#canvas-viewport").width() / 50, $("#canvas-viewport").height() / 50 );
    ## }
    
    </script>
</%def>

<%def name="stylesheets()">

    ${parent.stylesheets()}
    
    ## Also include "base.css" for styling tool menu and forms (details)
    <link href="${h.url_for('/static/style/base.css')}" rel="stylesheet" type="text/css" />

    <style type="text/css">
    body { margin: 0; padding: 0; overflow: hidden; }
    
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
    div.toolPanelLabel {
      padding-top: 5px;
      padding-bottom: 5px;
      font-weight: bold;
    }
    div.toolMenuGroupHeader {
        font-weight: bold;
        padding-top: 0.5em;
        padding-bottom: 0.5em;
        color: #333;
        font-style: italic;
        border-bottom: dotted #333 1px;
        margin-bottom: 0.5em;
    }
    div.toolTitle {
        padding-top: 5px;
        padding-bottom: 5px;
        margin-left: 16px;
        margin-right: 10px;
        display: list-item;
        list-style: square outside;
    }
    div.toolTitleNoSection {
      padding-bottom: 0px;
      font-weight: bold;
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
    div.toolTitleNoSectionDisabled {
      padding-bottom: 0px;
      font-style: italic;
      color: gray;
    }
    div.toolFormRow {
        position: relative;
    }
    
    
    #right-content {
        margin: 5px;
    }
    
    canvas { position: absolute; z-index: 10; } 
    canvas.dragging { position: absolute; z-index: 1000; }
    .input-terminal { width: 12px; height: 12px; background: url(${h.url_for('/static/style/workflow_circle_open.png')}); position: absolute; top: 0; left: -16px; z-index: 1500; }
    .output-terminal { width: 12px; height: 12px; background: url(${h.url_for('/static/style/workflow_circle_open.png')}); position: absolute; top: 0; right: -16px; z-index: 1500; }
    .drag-terminal { width: 12px; height: 12px; background: url(${h.url_for('/static/style/workflow_circle_drag.png')}); position: absolute; z-index: 1500; }
    .input-terminal-active { background: url(${h.url_for('/static/style/workflow_circle_green.png')}); }
    ## .input-terminal-hover { background: yellow; border: solid black 1px; }
    .unselectable { -moz-user-select: none; -khtml-user-select: none; user-select: none; }
    img { border: 0; }
    
    div.buttons img {
    width: 16px; height: 16px;
    cursor: pointer;
    }
    
    ## Extra styles for the representation of a tool on the canvas (looks like
    ## a tiny tool form)
    div.toolFormInCanvas {
        z-index: 100;
        position: absolute;
        min-width: 130px;
        margin: 6px;
    }
    
    div.toolForm-active {
        z-index: 1001;
        border: solid #8080FF 4px;
        margin: 3px;
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
    
    .callout {
        position: absolute;
        z-index: 10000;
    }
    
    </style>
</%def>

## Render a tool in the tool panel
<%def name="render_tool( tool, section )">
    %if not tool.hidden:
        %if tool.is_workflow_compatible:
            %if section:
                <div class="toolTitle">
            %else:
                <div class="toolTitleNoSection">
            %endif
                %if "[[" in tool.description and "]]" in tool.description:
                    ${tool.description.replace( '[[', '<a id="link-${tool.id}" href="javascript:add_node_for_tool( ${tool.id} )">' % tool.id ).replace( "]]", "</a>" )}
                %elif tool.name:
                    <a id="link-${tool.id}" href="#" onclick="add_node_for_tool( '${tool.id}', '${tool.name}' )">${tool.name}</a> ${tool.description}
                %else:
                    <a id="link-${tool.id}" href="#" onclick="add_node_for_tool( '${tool.id}', '${tool.name}' )">${tool.description}</a>
                %endif
            </div>
        %else:
            %if section:
                <div class="toolTitleDisabled">
            %else:
                <div class="toolTitleNoSectionDisabled">
            %endif
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
</%def>

## Render a label in the tool panel
<%def name="render_label( label )">
    <div class="toolSectionPad"></div>
    <div class="toolPanelLabel" id="title_${label.id}">
        <span>${label.text}</span>
    </div>
    <div class="toolSectionPad"></div>
</%def>

<div id="overlay">
    ## Need a table here for centering in IE6
    <table class="dialog-box-container" border="0" cellpadding="0" cellspacing="0"><tr><td>
    <div class="dialog-box-wrapper">
        <div class="dialog-box">
            <div class="unified-panel-header">
                <div class="unified-panel-header-inner"><span class='title'>Loading workflow editor...</span></div>
            </div>
            <div class="body" style="max-height: 500px; overflow: auto;"><img src="${h.url_for('/static/images/yui/rel_interstitial_loading.gif')}" /></div>
            <div>
                <div class="buttons" style="display: none; float: right;"></div>
                <div class="extra_buttons" style="display: none; padding: 5px;"></div>
                <div style="clear: both;"></div>
            </div>
        </div>
    </div>
    </td></tr></table>
</div>

<%def name="masthead()">
    <div style="float: right; color: black; padding: 3px;"><div class="warningmessagesmall" style="display: inline-block; min-height: 15px;">Workflow support is currently in <b><i>beta</i></b></div></div>
    <div class="title"><b>Galaxy workflow editor</b></div>
</%def>

<%def name="left_panel()">
    <div class="unified-panel-header" unselectable="on">
        <div class="unified-panel-header-inner">
            Tools
        </div>
    </div>
    
    <div class="unified-panel-body" style="overflow: auto;">
        <div class="toolMenu">
            <div class="toolSectionList">
                %for key, val in app.toolbox.tool_panel.items():
                    %if key.startswith( 'tool' ):
                        ${render_tool( val, False )}
                    %elif key.startswith( 'section' ):
                        <% section = val %>
                        <div class="toolSectionTitle" id="title_${section.id}">
                            <span>${section.name}</span>
                        </div>
                        <div id="${section.id}" class="toolSectionBody">
                            <div class="toolSectionBg">
                                %for section_key, section_val in section.elems.items():
                                    %if section_key.startswith( 'tool' ):
                                        ${render_tool( section_val, True )}
                                    %elif section_key.startswith( 'label' ):
                                        ${render_label( section_val )}
                                    %endif
                                %endfor
                            </div>
                        </div>
                        <div class="toolSectionPad"></div>
                    %elif key.startswith( 'label' ):
                        ${render_label( val )}
                    %endif
                %endfor
            </div>
            <div>&nbsp;</div>
            <div class="toolMenuGroupHeader">Workflow control</div>
            <div class="toolSectionTitle" id="title___workflow__input__">
                <span>Inputs</span>
            </div>
            <div id="__workflow__input__" class="toolSectionBody">
                <div class="toolSectionBg">
                    <div class="toolTitle">
                        <a href="#" onclick="add_node_for_module( 'data_input', 'Input Dataset' )">Input dataset</a>
                    </div>
                </div>
            </div>                    
        </div>
    </div>
</%def>

<%def name="center_panel()">

    <div class="unified-panel-header" unselectable="on">
        <div class="unified-panel-header-inner" style="float: right">
            <a id="save-button" class="panel-header-button">Save</a>
            <a id="close-button" class="panel-header-button">Close</a>
        </div>
        <div class="unified-panel-header-inner">
            Workflow canvas
        </div>
    </div>

    <div class="unified-panel-body">
        <div id="canvas-viewport" style="width: 100%; height: 100%; position: absolute; overflow: hidden;">
            <div id="canvas-container" style="height: 5000px; width: 5000px; background: white url(${h.url_for('/static/images/light_gray_grid.gif')}) repeat;"></div>
            ## <div id="canvas-map" style="height: 100px; width: 100px; border: solid red 1px; background: white; position: absolute; right: 0; bottom: 0;">
            ##     <canvas width="100" height="100" style="width: 100%; height: 100%" id="canvas-map-canvas"></canvas>
            ## </div>
        </div>
    </div>

</%def>

<%def name="right_panel()">
    <div class="unified-panel-header" unselectable="on">
        <div class="unified-panel-header-inner">
            Details
        </div>
    </div>
    <div class="unified-panel-body" style="overflow: auto;">
        <div id="right-content"></div>
    </div>
</%def>
