<%inherit file="/base_panels.mako"/>

<%def name="init()">
<%
    self.active_view="workflow"
    self.overlay_visible=True
%>
</%def>

<%def name="late_javascripts()">
    <script type='text/javascript' src="${h.url_for('/static/scripts/galaxy.panels.js')}"> </script>
    <script type="text/javascript">
        ensure_dd_helper();
        make_left_panel( $("#left"), $("#center"), $("#left-border" ) );
        make_right_panel( $("#right"), $("#center"), $("#right-border" ) );
        ensure_popup_helper();
        ## handle_minwidth_hint = rp.handle_minwidth_hint;
    </script>
</%def>

<%def name="javascripts()">
    
    ${parent.javascripts()}
    
    <!--[if IE]>
    <script type='text/javascript' src="${h.url_for('/static/scripts/excanvas.js')}"> </script>
    <![endif]-->
    <script type='text/javascript' src="${h.url_for('/static/scripts/jquery.js')}"> </script>
    <script type='text/javascript' src="${h.url_for('/static/scripts/jquery.event.drag.js')}"> </script>
    <script type='text/javascript' src="${h.url_for('/static/scripts/jquery.event.drop.js')}"> </script>
    <script type='text/javascript' src="${h.url_for('/static/scripts/jquery.event.hover.js')}"> </script>
    <script type='text/javascript' src="${h.url_for('/static/scripts/jquery.form.js')}"> </script>
    <script type='text/javascript' src="${h.url_for('/static/scripts/jquery.json.js')}"> </script>
    <script type='text/javascript' src="${h.url_for('/static/scripts/jquery.cookie.js')}"> </script>
    <script type='text/javascript' src="${h.url_for('/static/scripts/json2.js')}"> </script>
    <script type='text/javascript' src="${h.url_for('/static/scripts/json_cookie.js')}"> </script>

    <script type='text/javascript' src="${h.url_for('/static/scripts/galaxy.base.js')}"> </script>
    <script type='text/javascript' src="${h.url_for('/static/scripts/galaxy.workflow_editor.canvas.js')}"> </script>
    
    <!--[if lt IE 7]>
    <script type='text/javascript'>
    window.lt_ie_7 = true;
    </script>
    <![endif]-->
    
    <script type='text/javascript'>
    // Globals
    workflow = null;
    canvas_manager = null;
    // jQuery onReady
    $( function() {
        if ( window.lt_ie_7 ) {
            show_modal(
                "Browser not supported",
                "Sorry, the workflow editor is not supported for IE6 and below."
            );
            return;
        }
        // Canvas overview management
        canvas_manager = new CanvasManager( $("#canvas-viewport"), $("#overview") );
        
        // Preferences cookie stored as JSON so that only one cookie is needed for multiple settings
        var prefs_cookie = new JSONCookie("galaxy.workflow");
        
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
                         workflow.fit_canvas_to_nodes();
                         scroll_to_nodes();
                         canvas_manager.draw_overview();
                         // Determine if any parameters were 'upgraded' and provide message
                         upgrade_message = ""
                         $.each( data['upgrade_messages'], function( k, v ) {
                            upgrade_message += ( "<li>Step " + ( parseInt(k) + 1 ) + ": " + workflow.nodes[k].name + " -- " + v.join( ", " ) );
                         });
                         if ( upgrade_message ) {
                            show_modal( "Workflow loaded with changes",
                                        "Values were not found for the following parameters (possibly a result of tool upgrades), <br/> default values have been used. Please review the following parameters and then save.<ul>" + upgrade_message + "</ul>",
                                        { "Continue" : hide_modal } );
                         } else {
                            hide_modal();
                         }
                     },
                     beforeSubmit: function( data ) {
                         show_modal( "Loading workflow", "progress" );
                     }
                });
            }
        });
        
        $(document).ajaxError( function ( e, x ) {
            console.log( e, x );
            var message = x.responseText || x.statusText || "Could not connect to server";
            show_modal( "Server error", message, { "Ignore error" : hide_modal } );
            return false;
        });
        
        ## make_popupmenu( "#optionsbutton", {
        ##     "Create <b>new</b> workflow" : create_new_workflow_dialog,
        ##     "<b>Save</b> current workflow" : save_current_workflow,
        ##     "<b>Load</b> a stored workflow" : load_workflow
        ## });
        
        $("#save-button").click( function() { save_current_workflow(); } );
        $("#close-button").click( function() { close_editor(); } );
        
        $("#layout-button").click( function() {
            workflow.layout();
            workflow.fit_canvas_to_nodes();
            scroll_to_nodes();
            canvas_manager.draw_overview();
        });
        
        // Stores the size of the overview in a cookie when it's resized
        $("#overview-border").bind( "dragend", function( e ) {
            var op = $(this).offsetParent();
            var opo = op.offset();
            var new_size = Math.max( op.width() - ( e.offsetX - opo.left ),
                                     op.height() - ( e.offsetY - opo.top ) );
            prefs_cookie.set("overview-size", new_size);
        });
        
        // On load, set the size to the pref stored in cookie if it exists
        overview_size = prefs_cookie.get("overview-size");
        if (overview_size) {
            $("#overview-border").css( {
                width: overview_size,
                height: overview_size
            });
        }
        
        function show_overview() {
            prefs_cookie.unset("overview-off");
            $("#overview-border").css("right", "0px");
            $("#close-viewport").css("background-position", "0px 0px");
        }
        
        function hide_overview() {
            prefs_cookie.set("overview-off", true);
            $("#overview-border").css("right", "20000px");
            $("#close-viewport").css("background-position", "12px 0px");
        }
        
        // Show viewport on load unless pref says it's off
        prefs_cookie.get("overview-off") == true ? hide_overview() : show_overview() 
                
        // Lets the overview be toggled visible and invisible, adjusting the arrows accordingly
        $("#close-viewport").click( function() {
            $("#overview-border").css("right") == "0px" ? hide_overview() : show_overview();
        });
        
        // Unload handler
        window.onbeforeunload = function() {
            if ( workflow && workflow.has_changes ) {
                return "There are unsaved changes to your workflow which will be lost.";
            }
        };
        
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

    // Global state for the whole workflow
    function reset() {
        if ( workflow ) {
            workflow.remove_all();
        }
        workflow = new Workflow( $("#canvas-container") );
    }
        
    function scroll_to_nodes() {
        var cv = $("#canvas-vieport");
        var cc = $("#canvas-container")
        var top, left;
        if ( cc.width() < cv.width() ) {
            left = ( cv.width() - cc.width() ) / 2;
        } else {
            left = 0;
        }
        if ( cc.height() < cv.height() ) {
            top = ( cv.height() - cc.height() ) / 2;
        } else {
            top = 0;
        }
        cc.css( { left: left, top: top } );
    }
    
    // Add a new step to the workflow by tool id
    function add_node_for_tool( id, title ) {
        var node = prebuild_node( 'tool', title, id );
        workflow.add_node( node );
        workflow.fit_canvas_to_nodes();
        canvas_manager.draw_overview();
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
        workflow.fit_canvas_to_nodes();
        canvas_manager.draw_overview();
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
            $(this).find( ".popupmenu" ).each( function() {
                var id = $(this).parents( "div.form-row" ).attr( 'id' );
                var b = $('<a class="popup-arrow" id="popup-arrow-for-' + id + '">&#9660;</a>');
                var options = {};
                $(this).find( "button" ).each( function() {
                    var name = $(this).attr( 'name' );
                    var value = $(this).attr( 'value' );
                    options[ $(this).text() ] = function() {
                        $(form).append( "<input type='hidden' name='"+name+"' value='"+value+"' />" ).submit();
                    }
                });
                b.insertAfter( this );
                $(this).remove();
                make_popupmenu( b, options );
            });
        });
    }
    
    var close_editor = function() {
        <% next_url = h.url_for( controller='workflow', action='index' ) %>
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
    
    </script>
</%def>

<%def name="stylesheets()">

    ## Include "base.css" for styling tool menu and forms (details)
    <link href="${h.url_for('/static/style/base.css')}" rel="stylesheet" type="text/css" />

    ## But make sure styles for the layout take precedence
    ${parent.stylesheets()}    

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
    .input-terminal { width: 12px; height: 12px; background: url(${h.url_for('/static/style/workflow_circle_open.png')}); position: absolute; top: 50%; margin-top: -6px; left: -6px; z-index: 1500; }
    .output-terminal { width: 12px; height: 12px; background: url(${h.url_for('/static/style/workflow_circle_open.png')}); position: absolute; top: 50%; margin-top: -6px; right: -6px; z-index: 1500; }
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
        ## min-width: 130px;
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
    div.toolFormInCanvas div.toolFormBody {
        padding: 0;
    }
    .form-row-clear {
        clear: both;
    }
    
    div.rule {
        height: 0;
        border: none;
        border-bottom: dotted black 1px;
        margin: 0 5px;
    }
    
    .callout {
        position: absolute;
        z-index: 10000;
    }
    
    .panel-header-button-group {
        margin-right: 5px;
        padding-right: 5px;
        border-right: solid gray 1px;
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

<%def name="overlay()">
    ${parent.overlay( "Loading workflow editor...",
                      "<img src='" + h.url_for('/static/images/yui/rel_interstitial_loading.gif') + "'/>" )}
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
            <span class="panel-header-button-group">
            <a id="layout-button" class="panel-header-button">Layout</a>
            </span>
            <a id="save-button" class="panel-header-button">Save</a>
            <a id="close-button" class="panel-header-button">Close</a>
        </div>
        <div class="unified-panel-header-inner">
            Workflow canvas
        </div>
    </div>

    <div class="unified-panel-body">
        <div id="canvas-viewport" style="width: 100%; height: 100%; position: absolute; overflow: hidden; background: #EEEEEE; background: white url(${h.url_for('/static/images/light_gray_grid.gif')}) repeat;">
            <div id="canvas-container" style="position: absolute; width: 100%; height: 100%;"></div>
        </div>
        <div id="overview-border" style="position: absolute; width: 150px; height: 150px; right: 20000px; bottom: 0px; border-top: solid gray 1px; border-left: solid grey 1px; padding: 7px 0 0 7px; background: #EEEEEE no-repeat url(${h.url_for('/static/images/resizable.png')}); z-index: 20000; overflow: hidden; max-width: 300px; max-height: 300px; min-width: 50px; min-height: 50px">
            <div style="position: relative; overflow: hidden; width: 100%; height: 100%; border-top: solid gray 1px; border-left: solid grey 1px;">
                <div id="overview" style="position: absolute;">
                    <canvas width="0" height="0" style="background: white; width: 100%; height: 100%;" id="overview-canvas"></canvas>
                    <div id="overview-viewport" style="position: absolute; width: 0px; height: 0px; border: solid blue 1px; z-index: 10;"></div>
                </div>
            </div>
        </div>
        <div id="close-viewport" style="border-left: 1px solid #999; border-top: 1px solid #999; background: #ddd url(${h.url_for('/static/images/overview_arrows.png')}) 12px 0px; position: absolute; right: 0px; bottom: 0px; width: 12px; height: 12px; z-index: 25000;"></div>
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
