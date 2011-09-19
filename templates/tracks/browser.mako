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

${h.js( "galaxy.base", "galaxy.panels", "json2", "jquery", "jstorage", "jquery.event.drag", "jquery.mousewheel", "jquery.autocomplete", "trackster", "trackster_ui", "jquery.ui.sortable.slider", "jquery.scrollTo", "farbtastic" )}

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
            url: "${h.url_for( action='list_histories' )}",
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
                                     view.add_track( track_from_dict(track_defs[i]) ); 
                                 }
                            });
                            hide_modal();
                        }
                    }
                );
            }
        });
    };
    
    $(function() {
        // Hide bookmarks by default right now.
        parent.force_right_panel("hide"); 
        
        // Resize view when showing/hiding right panel (bookmarks for now).
        $("#right-border").click(function() { view.resize_window(); });
        
        %if config:
            var callback;
            %if 'viewport' in config:
                // TODO: find better way to handle this code.
                var callback = function() { 
                    view.change_chrom( '${config['viewport']['chrom']}', ${config['viewport']['start']}, ${config['viewport']['end']} );
                    // Set overview.
                    %if 'viewport' in config and 'overview' in config['viewport'] and config['viewport']['overview']:

                    var 
                        overview_track_name = "${config['viewport']['overview']}",
                        overview_track;
                    for (var i = 0; i < view.tracks.length; i++) {
                        if (view.tracks[i].name == overview_track_name) {
                            view.set_overview(view.tracks[i]);
                            break;
                        }
                    }
                    %endif
                    view.has_changes = false;
                };
            %endif
            view = create_visualization( $("#browser-container"), "${config.get('title') | h}", 
                                         "${config.get('vis_id')}", "${config.get('dbkey')}", callback,
                                         JSON.parse('${ h.to_json_string( config.get('tracks') ) }'),
                                         JSON.parse('${ h.to_json_string( config.get('bookmarks') ) }')
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
                    success: function(track_data) { view.add_track( track_from_dict(track_data) ) }
                });
                
            %endif
            
            //
            // Make actions menu.
            //
            $("#viz-actions-button").css( "position", "relative" );
            make_popupmenu( $("#viz-actions-button"), {
                "Add Tracks": add_tracks,
                "Add Group": function() {
                    var group = new DrawableCollection("New Group", view);
                    view.add_track(group);
                },
                "Save": function() {
                    // Show saving dialog box
                    show_modal("Saving...", "<img src='${h.url_for('/static/images/yui/rel_interstitial_loading.gif')}'/>");
                    
                    // Save tracks.
                    var saved_tracks = view.to_json();
                    
                    // Save bookmarks.
                    var bookmarks = [];
                    $(".bookmark").each(function() { 
                        bookmarks[bookmarks.length] = {
                            position: $(this).children(".position").text(),
                            annotation: $(this).children(".annotation").text()
                        };
                    });

                    var overview_track_name = (view.overview_track ? view.overview_track.name : null);
                    var payload = { 
                        'tracks': saved_tracks, 
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
                        success: function(vis_id) {
                            view.vis_id = vis_id;
                            view.has_changes = false;
                            hide_modal();
                        },
                        error: function() { alert("Could not save visualization"); }
                    });
                },
                "Bookmarks": function() {
                    // HACK -- use style to determine if panel is hidden and hide/show accordingly.
                    parent.force_right_panel(($("div#right").css("right") == "0px" ? "hide" : "show")); 
                },
                "Close": function() { window.location = "${h.url_for( controller='visualization', action='list' )}"; }
            });
            
            $("#add-bookmark-button").click(function() {
                // Add new bookmark.
                var position = view.chrom + ":" + view.low + "-" + view.high,
                    annotation = "Bookmark description";
                return add_bookmark(position, annotation);
            });
            
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
            <a id="viz-actions-button" class='panel-header-button popup' href="javascript:void(0)" target="galaxy_main">${_('Actions')}</a>
        </div>
    </div>
</div>
<div id="browser-container" class="unified-panel-body"></div>

</%def>

<%def name="right_panel()">

<div class="unified-panel-header" unselectable="on">
    <div class="unified-panel-header-inner">
        Bookmarks
    </div>
</div>
<div class="unified-panel-body" style="overflow: auto;">
    <div id="bookmarks-container"></div>
    <div>
        <a class="icon-button import" style="margin-left: .5em; width: 100%" original-title="Add Bookmark" id="add-bookmark-button" href="javascript:void(0);">Add Bookmark</a>
    </div>
</div>

</%def>
