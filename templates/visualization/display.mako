<%inherit file="/display_base.mako"/>

<%def name="javascripts()">
    <% config = item_data %>
    ${parent.javascripts()}
    
    <!--[if lt IE 9]>
      <script type='text/javascript' src="${h.url_for('/static/scripts/excanvas.js')}"></script>
    <![endif]-->
    
    ${h.js( "jquery.event.drag", "jquery.autocomplete", "jquery.mousewheel", "jquery.autocomplete", "trackster", "jquery.ui.sortable.slider", "jquery.scrollTo", "farbtastic" )}
</%def>

<%def name="stylesheets()">
    ${parent.stylesheets()}
    
    ## For page:
    <style type="text/css">
        .page-body {
            padding: 0px;
        }
    </style>

    ## For visualization (TODO: copied from browser.mako):
    ${h.css( "trackster", "overcast/jquery-ui-1.8.5.custom" )}
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

<%def name="render_item_header( item )">
    ## Don't need to show header
</%def>

<%def name="render_item_links( visualization )">
    
</%def>

<%def name="render_item( visualization, config )">
    <div id="${visualization.id}" class="unified-panel-body" style="overflow:none;top:0px;"></div>

    <script type="text/javascript">
        // TODO: much of this code is copied from browser.mako -- create shared base and use in both places.
    
        //
        // Place URLs here so that url_for can be used to generate them.
        // 
        var default_data_url = "${h.url_for( controller='/tracks', action='data' )}",
            raw_data_url = "${h.url_for( controller='/tracks', action='raw_data' )}",
            run_tool_url = "${h.url_for( controller='/tracks', action='run_tool' )}",
            rerun_tool_url = "${h.url_for( controller='/tracks', action='run_tool' )}",
            reference_url = "${h.url_for( controller='/tracks', action='reference' )}",
            chrom_url = "${h.url_for( controller='/tracks', action='chroms' )}",
            dataset_state_url = "${h.url_for( controller='/tracks', action='dataset_state' )}",
            converted_datasets_state_url = "${h.url_for( controller='/tracks', action='converted_datasets_state' )}",
            addable_track_types = { "LineTrack": LineTrack, "FeatureTrack": FeatureTrack, "ReadTrack": ReadTrack },
            view,
            container_element = $("#${visualization.id}");
        
        $(function() {
            
            if (container_element.parents(".item-content").length > 0) { // Embedded viz
                container_element.parents(".item-content").css( { "max-height": "none", "overflow": "visible" } );
            } else { // Viewing just one shared viz
                $("#right-border").live("click", function() { view.resize_window(); });
            }
            
            // Create view and add tracks.
            var callback;
            %if 'viewport' in config:
                var callback = function() { view.change_chrom( '${config['viewport']['chrom']}', ${config['viewport']['start']}, ${config['viewport']['end']} ); }
            %endif
            view = new View(container_element, "${config.get('title') | h}", "${config.get('vis_id')}", "${config.get('dbkey')}", callback);
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
            
            //
            // Keyboard navigation. Scroll ~7% of height when scrolling up/down.
            //
            $(document).keydown(function(e) {
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
        });

    </script>
</%def>