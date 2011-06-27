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

${h.js( "galaxy.base", "galaxy.panels", "json2", "jquery", "jstorage", "jquery.event.drag", "jquery.mousewheel", "jquery.autocomplete", "trackster", "jquery.ui.sortable.slider", "jquery.scrollTo", "farbtastic" )}

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
        addable_track_types = { "LineTrack": LineTrack, "FeatureTrack": FeatureTrack, "ReadTrack": ReadTrack },
        view;
    
    /**
     * Add bookmark.
     */
    var add_bookmark = function(position, annotation) {
        var 
            bookmarks_container = $("#bookmarks-container"),
            new_bookmark = $("<div/>").addClass("bookmark").appendTo(bookmarks_container),
            delete_icon_container = $("<div/>").addClass("delete-icon-container").appendTo(new_bookmark).click(function (){
                // Remove bookmark.
                new_bookmark.slideUp("fast");
                new_bookmark.remove();
                view.has_changes = true;
                return false;
            }),
            delete_icon = $("<a href=''/>").addClass("icon-button delete").appendTo(delete_icon_container),
            position_div = $("<div/>").addClass("position").appendTo(new_bookmark),
            position_link = $("<a href=''/>").text(position).appendTo(position_div).click(function() {
                view.go_to(position);
                return false;
            });
            annotation_div = get_editable_text_elt(annotation, true).addClass("annotation").appendTo(new_bookmark);
            
        view.has_changes = true;
        return new_bookmark;
    };
    
    $(function() {
        // Hide bookmarks by default right now.
        parent.force_right_panel("hide"); 
        
        // Resize view when showing/hiding right panel (bookmarks for now).
        $("#right-border").click(function() { view.resize_window(); });
        
        %if config:
            var callback;
            %if 'viewport' in config:
                var callback = function() { view.change_chrom( '${config['viewport']['chrom']}', ${config['viewport']['start']}, ${config['viewport']['end']} ); }
            %endif
            view = new View( $("#browser-container"), "${config.get('title') | h}", "${config.get('vis_id')}", "${config.get('dbkey')}", callback );
            view.editor = true;
            ## A little ugly and redundant, but it gets the job done moving the config from python to JS:
            var tracks_config = JSON.parse('${ h.to_json_string( config.get('tracks') ) }');
            var track_config, track, parent_track, parent_obj;
            for (var i = 0; i < tracks_config.length; i++) {
                track_config = tracks_config[i];
                track = new addable_track_types[track_config["track_type"]](
                                track_config['name'], 
                                view,
                                track_config['hda_ldda'],
                                track_config['dataset_id'],
                                track_config['prefs'], 
                                track_config['filters'],
                                track_config['tool'], 
                                (track_config.is_child ? parent_track : undefined));
                parent_obj = view;
                if (track_config.is_child) {
                    parent_obj = parent_track;
                }
                else {
                    // New parent track is this track.
                    parent_track = track;
                }
                parent_obj.add_track(track);
            }
            init();
            
            // Load bookmarks.
            var bookmarks = JSON.parse('${ h.to_json_string( config.get('bookmarks') ) }'),
                bookmark;
            for (var i = 0; i < bookmarks.length; i++) {
                bookmark = bookmarks[i];
                add_bookmark(bookmark['position'], bookmark['annotation']);
            }
            
            // View has no changes as of yet.
            view.has_changes = false;
        %else:
            var continue_fn = function() {
                view = new View( $("#browser-container"), $("#new-title").val(), undefined, $("#new-dbkey").val() );
                view.editor = true;
                init();
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
        
        // Execute initializer for EDITOR specific javascript
        function init() {
            if (view.num_tracks === 0) {
                $("#no-tracks").show();
            }
            $("#title").text(view.title + " (" + view.dbkey + ")");
           
            window.onbeforeunload = function() {
                if (view.has_changes) {
                    return "There are unsaved changes to your visualization which will be lost.";
                }
            };
            
            var add_async_success = function(track_data) {
                var td = track_data,
                    new_track = new addable_track_types[track_data.track_type]( 
                                        track_data.name, view, track_data.hda_ldda, track_data.dataset_id,
                                        track_data.prefs, track_data.filters, track_data.tool );
                view.add_track(new_track);
                // Should replace with live event but can't get working
                sortable(new_track.container_div, ".draghandle");
                view.has_changes = true;
                $("#no-tracks").hide();
            };
            
            %if add_dataset is not None:
                $.ajax({
                    url: "${h.url_for( action='add_track_async' )}",
                    data: { hda_id: "${add_dataset}" },
                    dataType: "json",
                    success: add_async_success
                });
                
            %endif
            
            $("#viz-options-button").css( "position", "relative" );
            make_popupmenu( $("#viz-options-button"), {
                "Add Tracks": function() {          
                    // Use a popup grid to add more tracks
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
                                                    add_async_success(track_defs[i]); 
                                            }
                                        });
                                        hide_modal();
                                    }
                                }
                            );
                        }
                    });
                },
                "Save": function() {
                    // Show saving dialog box
                    show_modal("Saving...", "<img src='${h.url_for('/static/images/yui/rel_interstitial_loading.gif')}'/>");

                    // Save all tracks.
                    var tracks = [];
                    $(".viewport-container .track").each(function () {
                        // ID has form track_<main_track_id>_<child_track_id>
                        var 
                            id_split = $(this).attr("id").split("_"),
                            track_id = id_split[1],
                            child_id = id_split[2];

                        // Get track.    
                        var track = view.tracks[track_id];
                        if (child_id) {
                            track = track.child_tracks[child_id];
                        }

                        // Add track.
                        tracks.push( {
                            "track_type": track.get_type(),
                            "name": track.name,
                            "hda_ldda": track.hda_ldda,
                            "dataset_id": track.dataset_id,
                            "prefs": track.prefs,
                            "is_child": (child_id ? true : false )
                        });
                    });

                    // Save all bookmarks.
                    var bookmarks = [];
                    $(".bookmark").each(function() { 
                        bookmarks[bookmarks.length] = {
                            position: $(this).children(".position").text(),
                            annotation: $(this).children(".annotation").text()
                        };
                    });

                    var payload = { 
                        'tracks': tracks, 
                        'viewport': { 'chrom': view.chrom, 'start': view.low , 'end': view.high },
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

            //
            // Keyboard navigation. Scroll ~7% of height when scrolling up/down.
            //
            $(document).keydown(function(e) {
                // Do not navigate if arrow keys used in input element.
                if ($(e.srcElement).is(':input')) {
                    return;
                }
                
                // Key codes: left == 37, up == 38, right == 39, down == 40
                switch(e.which) {
                    case 37:
                        view.move_fraction(0.25);
                        break
                    case 38:
                        var change = Math.round(view.viewport_container.height()/15.0);
                        view.viewport_container.scrollTo('-=' + change + 'px');
                        break;
                    case 39:
                        view.move_fraction(-0.25);
                        break;
                    case 40:
                        var change = Math.round(view.viewport_container.height()/15.0);
                        view.viewport_container.scrollTo('+=' + change + 'px');
                        break;
                }
            });
        };
        
    });

</script>
</%def>

<%def name="center_panel()">
<div class="unified-panel-header" unselectable="on">
    <div class="unified-panel-header-inner">
        <div style="float:left;" id="title"></div>
        <div style="float: right">
            <a id="viz-options-button" class='panel-header-button popup' href="javascript:void(0)" target="galaxy_main">${_('Options')}</a>
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
