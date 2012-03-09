<%inherit file="/webapps/galaxy/base_panels.mako"/>

<%def name="init()">
<%
    self.active_view="workflow"
    self.overlay_visible=True
%>
</%def>

## <%def name="late_javascripts()">
##     <script type='text/javascript' src="${h.url_for('/static/scripts/galaxy.panels.js')}"> </script>
##     <script type="text/javascript">
##         ensure_dd_helper();
##         make_left_panel( $("#left"), $("#center"), $("#left-border" ) );
##         make_right_panel( $("#right"), $("#center"), $("#right-border" ) );
##         ## handle_minwidth_hint = rp.handle_minwidth_hint;
##     </script>
## </%def>

<%def name="javascripts()">

    ${parent.javascripts()}

    <!--[if lt IE 9]>
      <script type='text/javascript' src="${h.url_for('/static/scripts/excanvas.js')}"></script>
    <![endif]-->

    ${h.js( "jquery",
            "jquery.tipsy",
            "jquery.event.drag",
            "jquery.event.drop",
            "jquery.event.hover",
            "jquery.form",
            "json2",
            "jstorage",
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
    var galaxy_async = new GalaxyAsync();
    galaxy_async.set_func_url(galaxy_async.set_user_pref, "${h.url_for( controller='user', action='set_user_pref_async' )}");

    // jQuery onReady
    $( function() {

        if ( window.lt_ie_7 ) {
            show_modal(
                "Browser not supported",
                "Sorry, the workflow editor is not supported for IE6 and below."
            );
            return;
        }

        // Init tool options.
        %if trans.app.toolbox_search.enabled:
        make_popupmenu( $("#tools-options-button"), {
            ## Search tools menu item.
            <%
                show_tool_search = False
                if trans.user:
                    show_tool_search = trans.user.preferences.get( "workflow.show_tool_search", "True" )

                if show_tool_search == "True":
                    initial_text = "Hide Search"
                else:
                    initial_text = "Search Tools"
            %>
            "${initial_text}": function() {
                // Show/hide menu and update vars, user preferences.
                var menu = $('#tool-search');
                if (menu.is(":visible")) {
                    // Hide menu.
                    pref_value = "False";
                    menu_option_text = "Search Tools";
                    menu.toggle();
                    // Reset search.
                    reset_tool_search(true);
                } else {
                    // Show menu.
                    pref_value = "True";
                    menu_option_text = "Hide Search";
                    menu.toggle();
                }
                // Update menu option.
                $("#tools-options-button-menu").find("li").eq(0).text(menu_option_text);
                galaxy_async.set_user_pref("workflow.show_tool_search", pref_value);
            }
        });

        // Init searching.
        $("#tool-search-query").click( function (){
            $(this).focus();
            $(this).select();
        })
        .keyup( function () {
            // Remove italics.
            $(this).css("font-style", "normal");
            // Don't update if same value as last time
            if ( this.value.length < 3 ) {
                reset_tool_search(false);
            } else if ( this.value != this.lastValue ) {
                // Add class to denote that searching is active.
                $(this).addClass("search_active");
                // input.addClass(config.loadingClass);
                // Add '*' to facilitate partial matching.
                var q = this.value + '*';
                // Stop previous ajax-request
                if (this.timer) {
                    clearTimeout(this.timer);
                }
                // Start a new ajax-request in X ms
                $("#search-spinner").show();
                this.timer = setTimeout(function () {
                    $.get("${h.url_for( controller='root', action='tool_search' )}", { query: q }, function (data) {
                        // input.removeClass(config.loadingClass);
                        // Show live-search if results and search-term aren't empty
                        $("#search-no-results").hide();
                        // Hide all tool sections.
                        $(".toolSectionWrapper").hide();
                        // This hides all tools but not workflows link (which is in a .toolTitle div).
                        $(".toolSectionWrapper").find(".toolTitle").hide();
                        if ( data.length != 0 ) {
                            // Map tool ids to element ids and join them.
                            var s = $.map( data, function( n, i ) { return "#link-" + n; } ).join( ", " );
                            // First pass to show matching tools and their parents.
                            $(s).each( function() {
                                // Add class to denote match.
                                $(this).parent().addClass("search_match");
                                $(this).parent().show().parent().parent().show().parent().show();
                            });
                            // Hide labels that have no visible children.
                            $(".toolPanelLabel").each( function() {
                               var this_label = $(this);
                               var next = this_label.next();
                               var no_visible_tools = true;
                               // Look through tools following label and, if none are visible, hide label.
                               while (next.length !== 0 && next.hasClass("toolTitle")) {
                                   if (next.is(":visible")) {
                                       no_visible_tools = false;
                                       break;
                                   } else {
                                       next = next.next();
                                   }
                                }
                                if (no_visible_tools) {
                                    this_label.hide();
                                }
                            });
                        } else {
                            $("#search-no-results").show();
                        }
                        $("#search-spinner").hide();
                    }, "json" );
                }, 200 );
            }
            this.lastValue = this.value;
        });
        %endif

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
                         upgrade_message = "";
                         $.each( data.upgrade_messages, function( k, v ) {
                            upgrade_message += ( "<li>Step " + ( parseInt(k, 10) + 1 ) + ": " + workflow.nodes[k].name + "<ul>");
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
                         show_workflow_parameters();
                     },
                     beforeSubmit: function( data ) {
                         show_message( "Loading workflow", "progress" );
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
            // console.log( e, x );
            var message = x.responseText || x.statusText || "Could not connect to server";
            show_modal( "Server error", message, { "Ignore error" : hide_modal } );
            return false;
        });

        make_popupmenu( $("#workflow-options-button"), {
            "Save" : save_current_workflow,
            "Run": function() {
                window.location = "${h.url_for( controller='root', action='index', workflow_id=trans.security.encode_id(stored.id))}";
            },
            ##"Create New" : create_new_workflow_dialog,
            "Edit Attributes" : edit_workflow_attributes,
            ##"Edit Workflow Outputs": edit_workflow_outputs,
            "Auto Re-layout": layout_editor,
            ##"Load a Workflow" : load_workflow,
            "Close": close_editor
        });

        function edit_workflow_outputs(){
            workflow.clear_active_node();
            $('.right-content').hide();
            var new_content = "";
            for (var node_key in workflow.nodes){
                var node = workflow.nodes[node_key];
                if(node.type == 'tool'){
                    new_content += "<div class='toolForm' style='margin-bottom:5px;'><div class='toolFormTitle'>Step " + node.id + " - " + node.name + "</div>";
                    for (var ot_key in node.output_terminals){
                        var output = node.output_terminals[ot_key];
                        // if (node.workflow_outputs[node.id + "|" + output.name]){
                        if ($.inArray(output.name, node.workflow_outputs) != -1){
                            new_content += "<p>"+output.name +"<input type='checkbox' name='"+ node.id + "|" + output.name +"' checked /></p>";
                        }
                        else{
                            new_content += "<p>"+output.name +"<input type='checkbox' name='"+ node.id + "|" + output.name +"' /></p>";
                        }
                    }
                    new_content += "</div>";
                }
            }
            $("#output-fill-area").html(new_content);
            $("#output-fill-area input").bind('click', function(){
                var node_id = this.name.split('|')[0];
                var output_name = this.name.split('|')[1];
                if (this.checked){
                    if($.inArray(output_name, workflow.nodes[node_id].workflow_outputs) == -1){
                        workflow.nodes[node_id].workflow_outputs.push(output_name);
                    }//else it's already in the array.  Shouldn't happen, but forget it.
                }else{
                    while ($.inArray(output_name, workflow.nodes[node_id].workflow_outputs) != -1){
                        var ia = $.inArray(output_name, workflow.nodes[node_id].workflow_outputs);
                        workflow.nodes[node_id].workflow_outputs = workflow.nodes[node_id].workflow_outputs.slice(0,ia).concat( workflow.nodes[node_id].workflow_outputs.slice(ia+1) );
                    }
                }
                workflow.has_changes = true;
            });
            $('#workflow-output-area').show();
        }

        function layout_editor() {
            workflow.layout();
            workflow.fit_canvas_to_nodes();
            scroll_to_nodes();
            canvas_manager.draw_overview();
        }

        function edit_workflow_attributes() {
            workflow.clear_active_node();
            $('.right-content').hide();
            $('#edit-attributes').show();

        }

        // On load, set the size to the pref stored in local storage if it exists
        overview_size = $.jStorage.get("overview-size");
        if (overview_size !== undefined) {
            $("#overview-border").css( {
                width: overview_size,
                height: overview_size
            });
        }

        // Show viewport on load unless pref says it's off
        if ($.jStorage.get("overview-off")) {
            hide_overview();
        } else {
            show_overview();
        }

        // Stores the size of the overview into local storage when it's resized
        $("#overview-border").bind( "dragend", function( e, d ) {
            var op = $(this).offsetParent();
            var opo = op.offset();
            var new_size = Math.max( op.width() - ( d.offsetX - opo.left ),
                                     op.height() - ( d.offsetY - opo.top ) );
            $.jStorage.set("overview-size", new_size + "px");
        });

        function show_overview() {
            $.jStorage.set("overview-off", false);
            $("#overview-border").css("right", "0px");
            $("#close-viewport").css("background-position", "0px 0px");
        }

        function hide_overview() {
            $.jStorage.set("overview-off", true);
            $("#overview-border").css("right", "20000px");
            $("#close-viewport").css("background-position", "12px 0px");
        }

        // Lets the overview be toggled visible and invisible, adjusting the arrows accordingly
        $("#close-viewport").click( function() {
            if ( $("#overview-border").css("right") === "0px" ) {
                hide_overview();
            } else {
                show_overview();
            }
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
        async_save_text("workflow-name", "workflow-name", "${h.url_for( action='rename_async', id=trans.security.encode_id(stored.id) )}", "new_name");

        // Tag async. Simply have the workflow edit element generate a click on the tag element to activate tagging.
        $('#workflow-tag').click( function() {
            $('.tag-area').click();
            return false;
        });
        // Annotate async.
        async_save_text("workflow-annotation", "workflow-annotation", "${h.url_for( action='annotate_async', id=trans.security.encode_id(stored.id) )}", "new_annotation", 25, true, 4);
    });

    // Global state for the whole workflow
    function reset() {
        if ( workflow ) {
            workflow.remove_all();
        }
        workflow = new Workflow( $("#canvas-container") );
    }

    function scroll_to_nodes() {
        var cv = $("#canvas-viewport");
        var cc = $("#canvas-container");
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
                var m = "error loading field data";
                if ( x.status === 0 ) {
                    m += ", server unavailable";
                }
                node.error( m );
            }
        });
    }

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
    }

<%
    from galaxy.jobs.actions.post import ActionBox
%>

    // This function preloads how to display known pja's.
    function display_pja(pja, node){
        // DBTODO SANITIZE INPUTS.
        p_str = '';
        ${ActionBox.get_forms(trans)}
        $("#pja_container").append(p_str);
        $("#pja_container>.toolForm:last>.toolFormTitle>.buttons").click(function (){
            action_to_rem = $(this).closest(".toolForm", ".action_tag").children(".action_tag:first").text();
            $(this).closest(".toolForm").remove();
            delete workflow.active_node.post_job_actions[action_to_rem];
            workflow.active_form_has_changes = true;
        });
    }

    function display_pja_list(){
        return "${ActionBox.get_add_list()}";
    }

    function display_file_list(node){
        addlist = "<select id='node_data_list' name='node_data_list'>";
        for (var out_terminal in node.output_terminals){
            addlist += "<option value='" + out_terminal + "'>"+ out_terminal +"</option>";
        }
        addlist += "</select>";
        return addlist;
    }

    function new_pja(action_type, target, node){
        if (node.post_job_actions === undefined){
            //New tool node, set up dict.
            node.post_job_actions = {};
        }
        if (node.post_job_actions[action_type+target] === undefined){
            var new_pja = {};
            new_pja.action_type = action_type;
            new_pja.output_name = target;
            node.post_job_actions[action_type+target] = null;
            node.post_job_actions[action_type+target] =  new_pja;
            display_pja(new_pja, node);
            workflow.active_form_has_changes = true;
            return true;
        } else {
            return false;
        }
    }

    function show_workflow_parameters(){
        var parameter_re = /\$\{.+?\}/g;
        var workflow_parameters = [];
        var wf_parm_container = $("#workflow-parameters-container");
        var wf_parm_box = $("#workflow-parameters-box");
        var new_parameter_content = "";
        var matches = [];
        $.each(workflow.nodes, function (k, node){
            var form_matches = node.form_html.match(parameter_re);
            if (form_matches){
                matches = matches.concat(form_matches);
            }
            if (node.post_job_actions){
                $.each(node.post_job_actions, function(k, pja){
                    if (pja.action_arguments){
                        $.each(pja.action_arguments, function(k, action_argument){
                            var arg_matches = action_argument.match(parameter_re);
                            if (arg_matches){
                                matches = matches.concat(arg_matches);
                            }
                        });
                    }
                });
                if (matches){
                    $.each(matches, function(k, element){
                        if ($.inArray(element, workflow_parameters) === -1){
                            workflow_parameters.push(element);
                        }
                    });
                }
            }
        });
        if (workflow_parameters && workflow_parameters.length !== 0){
            $.each(workflow_parameters, function(k, element){
                new_parameter_content += "<div>" + element.substring(2, element.length -1) + "</div>";
            });
            wf_parm_container.html(new_parameter_content);
            wf_parm_box.show();
        }else{
            wf_parm_container.html(new_parameter_content);
            wf_parm_box.hide();
        }
    }

    function show_form_for_tool( text, node ) {
        $('.right-content').hide();
        $("#right-content").show().html( text );
        // Add metadata form to tool.
        if (node) {
            $("#right-content").find(".toolForm:first").after( "<p><div class='metadataForm'> \
                <div class='metadataFormTitle'>Edit Step Attributes</div> \
                <div class='form-row'> \
                <label>Annotation / Notes:</label> \
                        <div style='margin-right: 10px;'> \
                        <textarea name='annotation' rows='3' style='width: 100%'>" + node.annotation + "</textarea> \
                            <div class='toolParamHelp'>Add an annotation or notes to this step; annotations are available when a workflow is viewed.</div> \
                        </div> \
                </div> \
                </div>" );
        }
        // Add step actions.
        if (node && node.type=='tool'){
            pjastr = "<p><div class='metadataForm'><div class='metadataFormTitle'>Edit Step Actions</div><div class='form-row'> \
                " + display_pja_list() + " <br/> "+ display_file_list(node) + " <div class='action-button' style='border:1px solid black;display:inline;' id='add_pja'>Create</div>\
                </div><div class='form-row'>\
                <div style='margin-right: 10px;'><span id='pja_container'></span>";
            pjastr += "<div class='toolParamHelp'>Add actions to this step; actions are applied when this workflow step completes.</div></div></div></div>";
            $("#right-content").find(".toolForm").after( pjastr );
            for (var key in node.post_job_actions){
                if (key != "undefined"){ //To make sure we haven't just deleted it.
                    display_pja(node.post_job_actions[key], node);
                }
            }
            $("#add_pja").click(function (){
                new_pja($("#new_pja_list").val(),$("#node_data_list").val(), node);
            });
        }
        $("#right-content").find( "form" ).ajaxForm( {
            type: 'POST',
            dataType: 'json',
            success: function( data ) {
                workflow.active_form_has_changes = false;
                node.update_field_data( data );
                show_workflow_parameters();
            },
            beforeSubmit: function( data ) {
                data.push( { name: 'tool_state', value: node.tool_state } );
                data.push( { name: '_', value: "true" } );
            }
        }).each( function() {
            var form = this;
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
                    };
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
                $(this).bind("focus click", function() {
                    workflow.active_form_has_changes = true;
                });
            });
        });
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
            window.document.location = "${next_url}";
        }
    };

    var save_current_workflow = function ( eventObj, success_callback ) {
        show_message( "Saving workflow", "progress" );
        workflow.check_changes_in_active_form();
        if (!workflow.has_changes) {
            hide_modal();
            if ( success_callback ) {
                success_callback();
            }
            return;
        }
        workflow.rectify_workflow_outputs();
        var savefn = function(callback) {
            $.ajax( {
                url: "${h.url_for( action='save_workflow' )}",
                type: "POST",
                data: {
                    id: "${trans.security.encode_id( stored.id )}",
                    workflow_data: function() { return JSON.stringify( workflow.to_simple() ); },
                    "_": "true"
                },
                dataType: 'json',
                success: function( data ) {
                    var body = $("<div></div>").text( data.message );
                    if ( data.errors ) {
                        body.addClass( "warningmark" );
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
                    show_workflow_parameters();
                    if ( data.errors ) {
                        show_modal( "Saving workflow", body, { "Ok" : hide_modal } );
                    } else {
                        if (callback) {
                            callback();
                        }
                        hide_modal();
                    }
                }
            });
        };

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
            savefn(success_callback);
        }
    };

    </script>
</%def>

<%def name="stylesheets()">

    ## Include "base.css" for styling tool menu and forms (details)
    ${h.css( "base", "autocomplete_tagging", "tool_menu" )}

    ## But make sure styles for the layout take precedence
    ${parent.stylesheets()}

    <style type="text/css">
    body { margin: 0; padding: 0; overflow: hidden; }

    /* Wider right panel */
    ## #center       { right: 309px; }
    ## #right-border { right: 300px; }
    ## #right        { width: 300px; }
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
    div.toolMenuGroupHeader {
        font-weight: bold;
        padding-top: 0.5em;
        padding-bottom: 0.5em;
        color: #333;
        font-style: italic;
        border-bottom: dotted #333 1px;
        margin-bottom: 0.5em;
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

    .pjaForm {
        margin-bottom:10px;
    }

    .pjaForm .toolFormBody{
        padding:10px;
    }

    .pjaForm .toolParamHelp{
        padding:5px;
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
    <div class="toolPanelLabel" id="title_${label.id}">
        <span>${label.text}</span>
    </div>
</%def>

<%def name="overlay(visible=False)">
    ${parent.overlay( "Loading workflow editor...",
                      "<div class='progress progress-striped progress-info active'><div class='bar' style='width: 100%;'></div></div>", self.overlay_visible )}
</%def>

<%def name="left_panel()">
    <div class="unified-panel-header" unselectable="on">
        <div class='unified-panel-header-inner'>
            <div style="float: right">
                <a class='panel-header-button popup' id="tools-options-button" href="#">${_('Options')}</a>
            </div>
            ${n_('Tools')}
        </div>
    </div>

    <div class="unified-panel-body" style="overflow: auto;">
            <div class="toolMenu">
            ## Tool search.
            <%
                show_tool_search = False
                if trans.user:
                    show_tool_search = trans.user.preferences.get( "workflow.show_tool_search", "True" )
                if show_tool_search == "True":
                    display = "block"
                else:
                    display = "none"
            %>
            <div id="tool-search" style="padding-bottom: 5px; position: relative; display: ${display}; width: 100%">
                <input type="text" name="query" value="search tools" id="tool-search-query" class="search-query parent-width" />
                <img src="${h.url_for('/static/images/loading_small_white_bg.gif')}" id="search-spinner" class="search-spinner" />
            </div>
            <div class="toolSectionList">
                %for key, val in app.toolbox.tool_panel.items():
                    <div class="toolSectionWrapper">
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
                    %elif key.startswith( 'label' ):
                        ${render_label( val )}
                    %endif
                    <div class="toolSectionPad"></div>
                    </div>
                %endfor
            </div>
            ## Feedback when search returns no results.
            <div id="search-no-results" style="display: none; padding-top: 5px">
                <em><strong>Search did not match any tools.</strong></em>
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
            Workflow Canvas | ${h.to_unicode( stored.name ) | h}
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
        <div id='workflow-parameters-box' style="display:none; position: absolute; /*width: 150px; height: 150px;*/ right: 0px; top: 0px; border-bottom: solid gray 1px; border-left: solid grey 1px; padding: 7px; background: #EEEEEE; z-index: 20000; overflow: hidden; max-width: 300px; max-height: 300px; /*min-width: 50px; min-height: 50px*/">
            <div style="margin-bottom:5px;"><b>Workflow Parameters</b></div>
            <div id="workflow-parameters-container">
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
                <span id="workflow-name" class="tooltip editable-text" original-title="Click to rename workflow">${h.to_unicode( stored.name ) | h}</span>
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
                ## Annotation elt.
                <div id="workflow-annotation-area" class="form-row">
                    <label>Annotation / Notes:</label>
                    <div id="workflow-annotation" class="tooltip editable-text" original-title="Click to edit annotation">
                    %if annotation:
                        ${h.to_unicode( annotation ) | h}
                    %else:
                        <em>Describe or add notes to workflow</em>
                    %endif
                    </div>
                    <div class="toolParamHelp">Add an annotation or notes to a workflow; annotations are available when a workflow is viewed.</div>
                </div>
            </div>
        </div>

        ## Div where tool details are loaded and modified.
        <div id="right-content" class="right-content"></div>

        ## Workflow output tagging
        <div style="display:none;" id="workflow-output-area" class="metadataForm right-content">
            <div class="metadataFormTitle">Edit Workflow Outputs</div>
            <div class="metadataFormBody"><div class="form-row">
                <div class="toolParamHelp">Tag step outputs to indicate the final dataset(s) to be generated by running this workflow.</div>
                <div id="output-fill-area"></div>
            </div></div>
        </div>

    </div>
</%def>
