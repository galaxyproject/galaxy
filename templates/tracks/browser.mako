<%inherit file="/webapps/galaxy/base_panels.mako"/>

<%def name="init()">
<%
    self.has_left_panel=False
    self.has_right_panel=True
    self.active_view="visualization"
    self.message_box_visible=False
%>
</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}

    ${h.css( "history", "autocomplete_tagging", "trackster", "overcast/jquery-ui-1.8.5.custom", "library" )}

    <style type="text/css">
        #browser-container {
            overflow: none;
        }
        .nav-container {
            width: 100%;
            ## Overriding styles from trackster.css to push nav up into title bar
            height: 0;
            text-align: center;
        }
        .nav {
            ## Overriding styles from trackster.css to push nav up into title bar
            position: relative;
            display: inline-block;
            top: -2em;
            background: transparent;
            border: none;
        }
    </style>
</%def>

<%def name="javascripts()">
${parent.javascripts()}

<!--[if lt IE 9]>
  <script type='text/javascript' src="${h.url_for('/static/scripts/excanvas.js')}"></script>
<![endif]-->

${h.js( "galaxy.base", "galaxy.panels", "json2", "jquery", "jstorage", "jquery.event.drag", "jquery.event.hover","jquery.mousewheel", "jquery.autocomplete", "trackster", "trackster_ui", "jquery.ui.sortable.slider", "farbtastic", "jquery.tipsy" )}

<script type="text/javascript">
    //
    // Place URLs here so that url_for can be used to generate them.
    // 
    var default_data_url = "${h.url_for( action='data' )}",
        raw_data_url = "${h.url_for( action='raw_data' )}",
        run_tool_url = "${h.url_for( action='run_tool' )}",
        rerun_tool_url = "${h.url_for( action='rerun_tool' )}",
        reference_url = "${h.url_for( action='reference' )}",
        chrom_url = "${h.url_for( action='chroms' )}",
        dataset_state_url = "${h.url_for( action='dataset_state' )}",
        converted_datasets_state_url = "${h.url_for( action='converted_datasets_state' )}",
        view;
            
    /**
     * Use a popup grid to add more tracks.
     */
    var add_tracks = function() {
        $.ajax({
            url: "${h.url_for( action='list_current_history_datasets' )}",
            data: { "f-dbkey": view.dbkey },
            error: function() { alert( "Grid failed" ); },
            success: function(table_html) {
                show_modal(
                    "Select datasets for new tracks",
                    table_html, {
                        "Cancel": function() {
                            hide_modal();
                        },
                        "Insert": function() {
                            var requests = [];
                            $('input[name=id]:checked,input[name=ldda_ids]:checked').each(function() {
                                var data,
                                    id = $(this).val();
                                    if ($(this).attr("name") === "id") {
                                        data = { hda_id: id };
                                    } else {
                                        data = { ldda_id: id};
                                    }
                                    requests[requests.length] = $.ajax({
                                        url: "${h.url_for( action='add_track_async' )}",
                                        data: data,
                                        dataType: "json",
                                    });
                            });
                            // To preserve order, wait until there are definitions for all tracks and then add 
                            // them sequentially.
                            $.when.apply($, requests).then(function() {
                                 // jQuery always returns an Array for arguments, so need to look at first element
                                 // to determine whether multiple requests were made and consequently how to 
                                 // map arguments to track definitions.
                                 var track_defs = (arguments[0] instanceof Array ?  
                                                   $.map(arguments, function(arg) { return arg[0]; }) :
                                                   [ arguments[0] ]
                                                   );
                                 for (var i= 0; i < track_defs.length; i++) {
                                     view.add_drawable( track_from_dict(track_defs[i], view) ); 
                                 }
                            });
                            hide_modal();
                        }
                    }
                );
            }
        });
    };

    /**
     * Use a popup grid to bookmarks from a dataset.
     */
    var add_bookmarks = function() {
        show_modal( "Select dataset for new bookmarks", "progress" );
        $.ajax({
            url: "${h.url_for( action='list_histories' )}",
            data: { "f-dbkey": view.dbkey },
            error: function() { alert( "Grid failed" ); },
            success: function(table_html) {
                show_modal(
                    "Select dataset for new bookmarks",
                    table_html, {
                        "Cancel": function() {
                            hide_modal();
                        },
                        "Insert": function() {
                            // Just use the first selected
                            $('input[name=id]:checked,input[name=ldda_ids]:checked').first().each(function(){
                                var data, id = $(this).val();
                                    if ($(this).attr("name") === "id") {
                                        data = { hda_id: id };
                                    } else {
                                        data = { ldda_id: id};
                                    }

                                    $.ajax({
                                        url: "${h.url_for( action='bookmarks_from_dataset' )}",
                                        data: data,
                                        dataType: "json",
                                    }).then( function(data) {
                                        for( i = 0; i < data.data.length; i++ ) {
                                            var row = data.data[i];
                                            console.log( row[0], row[1] );
                                            add_bookmark( row[0], row[1] );
                                        }
                                    });
                            });
                            hide_modal();
                        }
                    }
                );
            }
        });
    };
    
    $(function() {
        // Manual tipsy config because default gravity is S and cannot be changed.
        $(".menu-button").tipsy( {gravity: 'n'} );
        
        // Hide bookmarks by default right now.
        parent.force_right_panel("hide"); 
        
        // Resize view when showing/hiding right panel (bookmarks for now).
        $("#right-border").click(function() { view.resize_window(); });
        
        %if config:
            view = create_visualization( $("#browser-container"), "${config.get('title') | h}", 
                                         "${config.get('vis_id')}", "${config.get('dbkey')}", 
                                         JSON.parse('${ h.to_json_string( config.get( 'viewport', dict() ) ) }'),
                                         JSON.parse('${ h.to_json_string( config['tracks'] ).replace("'", "\\'") }'),
                                         JSON.parse('${ h.to_json_string( config['bookmarks'] ) }')
                                         );
            init_editor();
        %else:
            var continue_fn = function() {
                view = create_visualization( $("#browser-container"), $("#new-title").val(), undefined, $("#new-dbkey").val() );
                view.editor = true;
                init_editor();
                hide_modal();
            };
            $.ajax({
                url: "${h.url_for( action='new_browser', default_dbkey=default_dbkey )}",
                data: {},
                error: function() { alert( "Couldn't create new browser" ) },
                success: function(form_html) {
                    show_modal("New Track Browser", form_html, {
                        "Cancel": function() { window.location = "${h.url_for( controller='visualization', action='list' )}"; },
                        "Continue": function() { $(document).trigger("convert_to_values"); continue_fn(); }
                    });
                    $("#new-title").focus();
                    replace_big_select_inputs();
                }
            });
        %endif
        
        /**
         * Initialization for editor-specific functions.
         */
        function init_editor() {
            $("#title").text(view.title + " (" + view.dbkey + ")");
           
            window.onbeforeunload = function() {
                if (view.has_changes) {
                    return "There are unsaved changes to your visualization which will be lost.";
                }
            };
                        
            %if add_dataset is not None:
                $.ajax({
                    url: "${h.url_for( action='add_track_async' )}",
                    data: { hda_id: "${add_dataset}" },
                    dataType: "json",
                    success: function(track_data) { view.add_drawable( track_from_dict(track_data, view) ) }
                });
                
            %endif
            
            //
            // Initialize icons.
            //
            $("#add-tracks-icon").click( function() { add_tracks(); } );
            
            $("#add-group-icon").click( function() {
                view.add_drawable( new DrawableGroup("New Group", view, view) );                
            });
            
            $("#save-icon").click( function() {                
                // Show saving dialog box
                show_modal("Saving...", "progress");
                                    
                // Save bookmarks.
                var bookmarks = [];
                $(".bookmark").each(function() { 
                    bookmarks[bookmarks.length] = {
                        position: $(this).children(".position").text(),
                        annotation: $(this).children(".annotation").text()
                    };
                });

                // FIXME: give unique IDs to Drawables and save overview as ID.
                var overview_track_name = (view.overview_drawable ? view.overview_drawable.name : null);
                var payload = { 
                    'view': view.to_json(), 
                    'viewport': { 'chrom': view.chrom, 'start': view.low , 'end': view.high, 'overview': overview_track_name },
                    'bookmarks': bookmarks
                };

                $.ajax({
                    url: "${h.url_for( action='save' )}",
                    type: "POST",
                    data: {
                        'vis_id': view.vis_id,
                        'vis_title': view.title,
                        'dbkey': view.dbkey,
                        'payload': JSON.stringify(payload)
                    },
                    dataType: "json",
                    success: function(vis_info) {
                        hide_modal();
                        view.vis_id = vis_info.vis_id;
                        view.has_changes = false;
                        
                        // Needed to set URL when first saving a visualization.
                        window.history.pushState({}, "", vis_info.url);
                    },
                    error: function() { 
                        show_modal( "Could Not Save", "Could not save visualization. Please try again later.", 
                                    { "Close" : hide_modal } );
                    }
                });
            });
            
            $("#bookmarks-icon").click( function() {
                // HACK -- use style to determine if panel is hidden and hide/show accordingly.
                parent.force_right_panel(($("div#right").css("right") == "0px" ? "hide" : "show"));                 
            });

            $("#close-icon").click( function() {
                window.location = "${h.url_for( controller='visualization', action='list' )}";
            });  
        
            $("#add-bookmark-button").click(function() {
                // Add new bookmark.
                var position = view.chrom + ":" + view.low + "-" + view.high,
                    annotation = "Bookmark description";
                return add_bookmark(position, annotation);
            });

            // make_popupmenu( $("#bookmarks-more-button"), {
            //     "Add from BED dataset": function() {
            //         add_bookmarks();    
            //     }
            // });

            init_keyboard_nav(view);
        };
        
    });

</script>
</%def>

<%def name="center_panel()">
<div class="unified-panel-header" unselectable="on">
    <div class="unified-panel-header-inner">
        <div style="float:left;" id="title"></div>
        <div style="float: right">
            <a id="add-tracks-icon" class='icon-button menu-button' href="javascript:void(0);" title="Add tracks"></a>
            <a id="add-group-icon" class='icon-button menu-button' href="javascript:void(0);" title="Add new group"></a>
            <a id="bookmarks-icon" class='icon-button menu-button' href="javascript:void(0);" title="Bookmarks"></a>
            <a id="save-icon" class='icon-button menu-button' href="javascript:void(0);" title="Save"></a>
            <a id="close-icon" class='icon-button menu-button' href="javascript:void(0);" title="Close"></a>
        </div>
    </div>
    <div style="clear: both"></div>
</div>
<div id="browser-container" class="unified-panel-body"></div>

</%def>

<%def name="right_panel()">

<div class="unified-panel-header" unselectable="on">
    <div class="unified-panel-header-inner">
        <div style="float: right">
            <a id="add-bookmark-button" class='icon-button menu-button plus-button' href="javascript:void(0);" title="Add bookmark"></a>
            ## <a id="bookmarks-more-button" class='icon-button menu-button gear popup' href="javascript:void(0);" title="More actions"></a>
        </div>
        Bookmarks
    </div>
</div>
<div class="unified-panel-body" style="overflow: auto;">
    <div id="bookmarks-container"></div>
</div>

</%def>
