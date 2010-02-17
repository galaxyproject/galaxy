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

    ${h.js( "jquery",
            "jquery.tipsy",
            "jquery.event.drag", 
            "jquery.event.drop", 
            "jquery.event.hover",
            "jquery.form", 
            "jquery.jstore-all", 
            "json2",
            "galaxy.base",
            "galaxy.workflow_editor.canvas",
			"jquery.autocomplete",
 			"autocomplete_tagging")}

    <!--[if lt IE 7]>
    <script type='text/javascript'>
    window.lt_ie_7 = true;
    </script>
    <![endif]-->
    
    <script type='text/javascript'>
    // Globals
    workflow = null;
    canvas_manager = null;
    active_ajax_call = false;
    // jQuery onReady
    $( function() {
        
        if ( window.lt_ie_7 ) {
            show_modal(
                "Browser not supported",
                "Sorry, the workflow editor is not supported for IE6 and below."
            );
            return;
        }
        
        // Load jStore for local storage
        $.extend(jQuery.jStore.defaults, { project: 'galaxy', flash: '${h.url_for("/static/jStore.Flash.html")}' })
        $.jStore.load(); // Auto-select best storage
        
        // Canvas overview management
        canvas_manager = new CanvasManager( $("#canvas-viewport"), $("#overview") );
        
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
                    data: { id: "${trans.security.encode_id( stored.id )}", "_": "true" },
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
                            upgrade_message += ( "<li>Step " + ( parseInt(k) + 1 ) + ": " + workflow.nodes[k].name + "<ul>");
                            $.each( v, function( i, vv ) {
                                upgrade_message += "<li>" + vv +"</li>";
                            });
                            upgrade_message += "</ul></li>";
                         });
                         if ( upgrade_message ) {
                            show_modal( "Workflow loaded with changes",
                                        "Problems were encountered loading this workflow (possibly a result of tool upgrades). Please review the following parameters and then save.<ul>" + upgrade_message + "</ul>",
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
        
        // For autosave purposes
        $(document).ajaxStart( function() {
            active_ajax_call = true;
            $(document).bind( "ajaxStop.global", function() {
                active_ajax_call = false;
            });
        });
        
        $(document).ajaxError( function ( e, x ) {
            console.log( e, x );
            var message = x.responseText || x.statusText || "Could not connect to server";
            show_modal( "Server error", message, { "Ignore error" : hide_modal } );
            return false;
        });
        
        make_popupmenu( $("#workflow-options-button"), {
             ##"Create New" : create_new_workflow_dialog,
             "Edit Attributes" : edit_workflow_attributes,
             "Layout": layout_editor,
             "Save" : save_current_workflow,
             ##"Load a Workflow" : load_workflow,
             "Close": close_editor,
        });
        
        function layout_editor() {
            workflow.layout();
            workflow.fit_canvas_to_nodes();
            scroll_to_nodes();
            canvas_manager.draw_overview();
        };
        
        function edit_workflow_attributes() {
            workflow.clear_active_node();
            $('#edit-attributes').show();
            $('#right-content').hide();  
        };
        
        $.jStore.ready(function(engine) {
            engine.ready(function() {
                // On load, set the size to the pref stored in local storage if it exists
                overview_size = $.jStore.store("overview-size");
                if (overview_size) {
                    $("#overview-border").css( {
                        width: overview_size,
                        height: overview_size
                    });
                }
                
                // Show viewport on load unless pref says it's off
                $.jStore.store("overview-off") ? hide_overview() : show_overview()
            });
        });
        
        // Stores the size of the overview into local storage when it's resized
        $("#overview-border").bind( "dragend", function( e ) {
            var op = $(this).offsetParent();
            var opo = op.offset();
            var new_size = Math.max( op.width() - ( e.offsetX - opo.left ),
                                     op.height() - ( e.offsetY - opo.top ) );
            $.jStore.store("overview-size", new_size + "px");
        });
        
        function show_overview() {
            $.jStore.remove("overview-off");
            $("#overview-border").css("right", "0px");
            $("#close-viewport").css("background-position", "0px 0px");
        }
        
        function hide_overview() {
            $.jStore.store("overview-off", true);
            $("#overview-border").css("right", "20000px");
            $("#close-viewport").css("background-position", "12px 0px");
        }
        
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

        // Rename async.
        async_save_text("workflow-name", "workflow-name", "${h.url_for( action="rename_async", id=trans.security.encode_id(stored.id) )}", "new_name");
        
        // Tag async. Simply have the workflow edit element generate a click on the tag element to activate tagging.
        $('#workflow-tag').click( function() 
        {
            $('.tag-area').click();
            return false;
        });
        // Annotate async.
        async_save_text("workflow-annotation", "workflow-annotation", "${h.url_for( action="annotate_async", id=trans.security.encode_id(stored.id) )}", "new_annotation", 25, true, 4);
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
        $("#edit-attributes").hide();
		$("#right-content").show().html( text );   
        $("#right-content").find( "form" ).ajaxForm( {
            type: 'POST',
            dataType: 'json',
            success: function( data ) {
                node.update_field_data( data );
            },
            beforeSubmit: function( data ) {
                data.push( { name: 'tool_state', value: node.tool_state } );
                data.push( { name: '_', value: "true" } );
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
            
            // Implements auto-saving based on whether the inputs change. We consider
            // "changed" to be when a field is accessed and not necessarily modified
            // because of an issue where "onchange" is not triggered when activating
            // another node, or saving the workflow.
            $(this).find("input,textarea,select").each( function() {
                $(this).focus( function() {
                    workflow.active_form_has_changes = true;
                });
            });
        });
        
            
        // Add metadata form to tool.
        if ( node )
        {
            var metadata_div = 
            $( "<p><div class='metadataForm'> \
                <div class='metadataFormTitle'>Edit Step Attributes</div> \
                <div class='form-row'> \
                <label>Annotation / Notes:</label> \
                        <div style='margin-right: 10px;'> \
                        <textarea name='annotation' rows='3' style='width: 100%'>" + node.annotation + "</textarea> \
                            <div class='toolParamHelp'>Add an annotation or notes to this step; annotations are available when a workflow is viewed.</div> \
                        </div> \
                </div> \
                </div>");
            // When metadata is changed, update node and set workflow changes flag.
            var textarea = $(metadata_div).find("textarea");
            textarea.change( function () {
                node.annotation = $(this).val();
                workflow.has_changes = true;
            });
            $("#right-content").find(".toolForm").after( metadata_div );
        }
    }
    
    var close_editor = function() {
        <% next_url = h.url_for( controller='workflow', action='index' ) %>
        workflow.check_changes_in_active_form();
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
                                save_current_workflow( null, do_close );
                            }
                        }, {
                            "Don't Save": do_close
                        } );
        } else {
            window.document.location = "${next_url}"
        }
    }
    
    var save_current_workflow = function ( eventObj, success_callback ) {
        show_modal( "Saving workflow", "progress" );
        workflow.check_changes_in_active_form();
        if (!workflow.has_changes) {
            hide_modal();
            if ( success_callback ) {
                success_callback();
            }
            return;
        }
        var savefn = function() {
            $.ajax( {
                url: "${h.url_for( action='save_workflow' )}",
                type: "POST",
                data: {
                    id: "${trans.security.encode_id( stored.id )}",
                    workflow_data: function() { return JSON.stringify( workflow.to_simple() ) },
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
        
        // We bind to ajaxStop because of auto-saving, since the form submission ajax
        // call needs to be completed so that the new data is saved
        if (active_ajax_call) {
            $(document).bind('ajaxStop.save_workflow', function() {
                $(document).unbind('ajaxStop.save_workflow');
                savefn();
                $(document).unbind('ajaxStop.save_workflow'); // IE7 needs it here
                active_ajax_call = false;
            });
        } else {
            savefn();
        }
        if ( success_callback ) {
            success_callback();
        }
    }
    
    </script>
</%def>

<%def name="stylesheets()">

    ## Include "base.css" for styling tool menu and forms (details)
	${h.css( "base", "autocomplete_tagging")}

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

    .right-content {
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
            <a id="workflow-options-button" class="panel-header-button popup" href="#">Options</a>
        </div>
        <div class="unified-panel-header-inner">
            Workflow Canvas | ${stored.name | h}
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
        ## Div for elements to modify workflow attributes.
        <div id="edit-attributes" class="metadataForm right-content">
            <div class="metadataFormTitle">Edit Workflow Attributes</div>
            <div class="metadataFormBody">
            ## Workflow name.
            <div id="workflow-name-area" class="form-row">
                <label>Name:</label>
                <span id="workflow-name" class="tooltip editable-text" original-title="Click to rename workflow">${stored.name | h}</span>
            </div>
            ## Workflow tags.
            <%namespace file="/tagging_common.mako" import="render_individual_tagging_element" />
            <div class="form-row">
                <label>
                    Tags:
                </label>
                    <div style="float: left; width: 225px; margin-right: 10px; border-style: inset; border-width: 1px; margin-left: 2px">
                        <style>
                            .tag-area {
                                border: none;
                            }
                        </style>
                        ${render_individual_tagging_element(user=trans.get_user(), tagged_item=stored, elt_context="edit_attributes.mako", use_toggle_link=False, input_size="20")}
                    </div>
                    <div class="toolParamHelp">Apply tags to make it easy to search for and find items with the same tag.</div>
                </div>
                ## Workflow annotation.
                <div id="workflow-annotation-area" class="form-row">
                    <label>Annotation / Notes:</label>
                    <span id="workflow-annotation" class="tooltip editable-text" original-title="Click to edit annotation">${annotation | h}</span>
                    <div class="toolParamHelp">Add an annotation or notes to a workflow; annotations are available when a workflow is viewed.</div>
                </div>
            </div>
        </div>
        ## Div where tool details are loaded and modified.
        <div id="right-content" class="right-content"></div>
    </div>
</%def>
