<%inherit file="/display_base.mako"/>

<%def name="javascripts()">
    <% config = item_data %>
    ${parent.javascripts()}
    
    <!--[if lt IE 9]>
      <script type='text/javascript' src="${h.url_for('/static/scripts/excanvas.js')}"></script>
    <![endif]-->
    
    ${h.js( "jquery.event.drag", "jquery.autocomplete", "jquery.mousewheel", "jquery.autocomplete", "trackster", "trackster_ui", "jquery.ui.sortable.slider", "jquery.scrollTo", "farbtastic" )}
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
    <a 
        href="${h.url_for( controller='/visualization', action='imp', id=trans.security.encode_id( visualization.id ) )}"
        class="icon-button import"
        ## Needed to overwide initial width so that link is floated left appropriately.
        style="width: 100%"
        title="Import visualization">Import visualization</a>
</%def>

<%def name="render_item( visualization, config )">
    <div id="${trans.security.encode_id( visualization.id )}" class="unified-panel-body" style="overflow:none;top:0px;"></div>

    <script type="text/javascript">
        // TODO: much of this code is copied from browser.mako -- create shared base and use in both places.
    
        //
        // Place URLs here so that url_for can be used to generate them.
        // 
        var default_data_url = "${h.url_for( controller='/tracks', action='data' )}",
            raw_data_url = "${h.url_for( controller='/tracks', action='raw_data' )}",
            run_tool_url = "${h.url_for( controller='/tracks', action='run_tool' )}",
            rerun_tool_url = "${h.url_for( controller='/tracks', action='rerun_tool' )}",
            reference_url = "${h.url_for( controller='/tracks', action='reference' )}",
            chrom_url = "${h.url_for( controller='/tracks', action='chroms' )}",
            dataset_state_url = "${h.url_for( controller='/tracks', action='dataset_state' )}",
            converted_datasets_state_url = "${h.url_for( controller='/tracks', action='converted_datasets_state' )}",
            addable_track_types = { "LineTrack": LineTrack, "FeatureTrack": FeatureTrack, "ReadTrack": ReadTrack },
            view,
            container_element = $("#${trans.security.encode_id( visualization.id )}");
        
        $(function() {
            
            if (container_element.parents(".item-content").length > 0) { // Embedded viz
                container_element.parents(".item-content").css( { "max-height": "none", "overflow": "visible" } );
            } else { // Viewing just one shared viz
                $("#right-border").click(function() { view.resize_window(); });
            }
            
            // Create visualization.
            var callback;
            %if 'viewport' in config:
                var callback = function() { view.change_chrom( '${config['viewport']['chrom']}', ${config['viewport']['start']}, ${config['viewport']['end']} ); }
            %endif
            view = create_visualization( container_element, "${config.get('title') | h}", 
                                         "${config.get('vis_id')}", "${config.get('dbkey')}", callback,
                                         JSON.parse('${ h.to_json_string( config.get('tracks') ) }'),
                                         JSON.parse('${ h.to_json_string( config.get('bookmarks') ) }')
                                         );
            
            // Set up keyboard navigation.
            init_keyboard_nav(view);
        });

    </script>
</%def>