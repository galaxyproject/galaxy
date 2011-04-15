<%inherit file="/webapps/galaxy/base_panels.mako"/>

<%def name="init()">
<%
    self.has_left_panel=False
    self.has_right_panel=False
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

<%def name="center_panel()">
<div class="unified-panel-header" unselectable="on">
    <div class="unified-panel-header-inner">
        <div style="float:left;" id="title"></div>
        <a class="panel-header-button right-float" href="${h.url_for( controller='visualization', action='list' )}">Close</a>
        <a id="save-button" class="panel-header-button right-float" href="javascript:void(0);">Save</a>
        <a id="add-track" class="panel-header-button right-float" href="javascript:void(0);">Add Tracks</a>
    </div>
</div>
<div id="browser-container" class="unified-panel-body"></div>

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
        reference_url = "${h.url_for( action='reference' )}",
        chrom_url = "${h.url_for( action='chroms' )}",
        dataset_state_url = "${h.url_for( action='dataset_state' )}",
        converted_datasets_state_url = "${h.url_for( action='converted_datasets_state' )}",
        filters_url = "${h.url_for( action='filters' )}",
        addable_track_types = { "LineTrack": LineTrack, "FeatureTrack": FeatureTrack, "ReadTrack": ReadTrack },
        view;
    
    $(function() {
        
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
                sortable( new_track.container_div, ".draghandle" );
                view.has_changes = true;
                $("#no-tracks").hide();
            };
            
            %if add_dataset is not None:
                $.ajax( {
                    url: "${h.url_for( action='add_track_async' )}",
                    data: { hda_id: "${add_dataset}" },
                    dataType: "json",
                    success: add_async_success
                });
                
            %endif
            
            // Use a popup grid to add more tracks
            $("#add-track").bind("click", function(e) {
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
                                    $('input[name=id]:checked,input[name=ldda_ids]:checked').each(function() {
                                        var data,
                                            id = $(this).val();
                                        if ($(this).attr("name") === "id") {
                                            data = { hda_id: id };
                                        } else {
                                            data = { ldda_id: id};
                                        }
                                        $.ajax( {
                                            url: "${h.url_for( action='add_track_async' )}",
                                            data: data,
                                            dataType: "json",
                                            success: add_async_success
                                        });

                                    });
                                    hide_modal();
                                }
                            }
                        );
                    }
                });
            });
            
            $("#save-button").bind("click", function(e) {
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
                        "track_type": track.track_type,
                        "name": track.name,
                        "hda_ldda": track.hda_ldda,
                        "dataset_id": track.dataset_id,
                        "prefs": track.prefs,
                        "is_child": (child_id ? true : false )
                    });
                });

                var payload = { 'tracks': tracks, 'viewport': { 'chrom': view.chrom, 'start': view.low , 'end': view.high } };
                
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
