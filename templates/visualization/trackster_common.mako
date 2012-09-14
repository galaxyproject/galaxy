##
## Utilities for creating Trackster visualizations.
##

## Render needed CSS files.
<%def name="render_trackster_css_files()">
	${h.css( "history", "autocomplete_tagging", "trackster", "library", 
			 "jquery-ui/smoothness/jquery-ui-1.8.23.custom" )}
</%def>


## Render needed JavaScript files.
<%def name="render_trackster_js_files()">
	${h.js( "galaxy.panels", "libs/jquery/jstorage", "libs/jquery/jquery.event.drag", "libs/jquery/jquery.event.hover","libs/jquery/jquery.mousewheel", "libs/jquery/jquery-ui-1.8.23.custom.min", "mvc/data", "viz/visualization", "viz/trackster", "viz/trackster_ui", "libs/farbtastic" )}
</%def>

## Render a block of JavaScript that contains all necessary variables for Trackster.
<%def name="render_trackster_js_vars()">
    var add_track_async_url = "${h.url_for( controller='/tracks', action='add_track_async' )}",
        add_datasets_url = "${h.url_for( controller='/visualization', action='list_current_history_datasets' )}",
        default_data_url = "${h.url_for( controller='/tracks', action='data' )}",
        raw_data_url = "${h.url_for( controller='/tracks', action='raw_data' )}",        
        reference_url = "${h.url_for( controller='/tracks', action='reference' )}",
        chrom_url = "${h.url_for( controller='/tracks', action='chroms' )}",
        dataset_state_url = "${h.url_for( controller='/tracks', action='dataset_state' )}",
        converted_datasets_state_url = "${h.url_for( controller='/tracks', action='converted_datasets_state' )}",
        feature_search_url = "${h.url_for( controller='/tracks', action='search_features' )}";
</%def>