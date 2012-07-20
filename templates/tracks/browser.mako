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
</%def>

<%def name="javascripts()">
${parent.javascripts()}

<!--[if lt IE 9]>
  <script type='text/javascript' src="${h.url_for('/static/scripts/excanvas.js')}"></script>
<![endif]-->

${h.js( "galaxy.base", "galaxy.panels", "json2", "jquery", "bootstrap", "jstorage", "jquery.event.drag", "jquery.event.hover","jquery.mousewheel", "jquery.autocomplete", "mvc/data", "viz/visualization", "viz/trackster", "viz/trackster_ui", "jquery.ui.sortable.slider", "farbtastic" )}

<script type="text/javascript">
    //
    // Place URLs here so that url_for can be used to generate them.
    //
    galaxy_paths.set({
        visualization_url: "${h.url_for( action='save' )}"
    });
    var 
        add_track_async_url = "${h.url_for( action='add_track_async' )}",
        add_datasets_url = "${h.url_for( action='list_current_history_datasets' )}",
        default_data_url = "${h.url_for( action='data' )}",
        raw_data_url = "${h.url_for( action='raw_data' )}",        
        reference_url = "${h.url_for( action='reference' )}",
        chrom_url = "${h.url_for( action='chroms' )}",
        dataset_state_url = "${h.url_for( action='dataset_state' )}",
        converted_datasets_state_url = "${h.url_for( action='converted_datasets_state' )}",
        view,
        browser_router;
        
    /**
     * Set up router.
     */
    var set_up_router = function(options) {
        browser_router = new TrackBrowserRouter(options);
        Backbone.history.start();   
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
    
    var browser_router;
    $(function() {
        // Create and initialize menu.
        var menu = create_icon_buttons_menu([
            { icon_class: 'plus-button', title: 'Add tracks', on_click: function() { 
                add_datasets(add_datasets_url, add_track_async_url, function(tracks) {
                    _.each(tracks, function(track) {
                        view.add_drawable( object_from_template(track, view,  view) );  
                    });
                });
            } },
            { icon_class: 'block--plus', title: 'Add group', on_click: function() { 
                view.add_drawable( new DrawableGroup(view, view, { name: "New Group" }) );
            } },
            { icon_class: 'bookmarks', title: 'Bookmarks', on_click: function() { 
                // HACK -- use style to determine if panel is hidden and hide/show accordingly.
                parent.force_right_panel(($("div#right").css("right") == "0px" ? "hide" : "show"));
            } },
            {
                icon_class: 'globe',
                title: 'Circster',
                on_click: function() {
                    // Add viz id dynamically so that newly saved visualizations work as well.
                    window.location = "${h.url_for( controller='tracks', action='circster' )}?id=" + view.vis_id;
                }
            },
            { icon_class: 'disk--arrow', title: 'Save', on_click: function() { 
                // Show saving dialog box
                show_modal("Saving...", "progress");
                                    
                // Save bookmarks.
                var bookmarks = [];
                $(".bookmark").each(function() { 
                    bookmarks.push({
                        position: $(this).children(".position").text(),
                        annotation: $(this).children(".annotation").text()
                    });
                });

                // FIXME: give unique IDs to Drawables and save overview as ID.
                var overview_track_name = (view.overview_drawable ? view.overview_drawable.name : null),
                    viz_config = {
                        'id': view.vis_id,
                        'title': view.name,
                        'dbkey': view.dbkey,
                        'type': 'trackster',
                        'datasets': view.to_dict(),
                        'viewport': { 'chrom': view.chrom, 'start': view.low , 'end': view.high, 'overview': overview_track_name },
                        'bookmarks': bookmarks
                    };

                $.ajax({
                    url: galaxy_paths.get("visualization_url"),
                    type: "POST",
                    dataType: "json",
                    data: { 
                        vis_json: JSON.stringify(viz_config)
                    }
                }).success(function(vis_info) {
                    hide_modal();
                    view.vis_id = vis_info.vis_id;
                    view.has_changes = false;

                    // Needed to set URL when first saving a visualization.
                    window.history.pushState({}, "", vis_info.url + window.location.hash);
                })
                .error(function() { 
                    show_modal( "Could Not Save", "Could not save visualization. Please try again later.", 
                                { "Close" : hide_modal } );
                });
            } },
            { icon_class: 'cross-circle', title: 'Close', on_click: function() { 
                window.location = "${h.url_for( controller='visualization', action='list' )}";
            } }
        ], 
        { 
            tooltip_config: { placement: 'bottom' }
        });
        
        menu.$el.attr("style", "float: right");
        $("#center .unified-panel-header-inner").append(menu.$el);
        
        // Hide bookmarks by default right now.
        parent.force_right_panel("hide"); 
        
        // Resize view when showing/hiding right panel (bookmarks for now).
        $("#right-border").click(function() { view.resize_window(); });
        
        %if config:
            view = create_visualization( {
                                            container: $("#browser-container"), 
                                            name: "${config.get('title') | h}",
                                            vis_id: "${config.get('vis_id')}", 
                                            dbkey: "${config.get('dbkey')}"
                                         },
                                         JSON.parse('${ h.to_json_string( config.get( 'viewport', dict() ) ) }'),
                                         JSON.parse('${ h.to_json_string( config['tracks'] ).replace("'", "\\'") }'),
                                         JSON.parse('${ h.to_json_string( config['bookmarks'] ) }'),
                                         true
                                         );
            init_editor();
            set_up_router({view: view});
        %else:
            var continue_fn = function() {
                view = create_visualization( {
                    container: $("#browser-container"),
                    name: $("#new-title").val(),
                    dbkey: $("#new-dbkey").val()
                } );
                view.editor = true;
                init_editor();
                set_up_router({view: view});
                hide_modal();
            };
            $.ajax({
                url: "${h.url_for( action='new_browser', default_dbkey=default_dbkey )}",
                data: {},
                error: function() { alert( "Couldn't create new browser" ) },
                success: function(form_html) {
                    show_modal("New Visualization", form_html, {
                        "Cancel": function() { window.location = "${h.url_for( controller='visualization', action='list' )}"; },
                        "Create": function() { $(document).trigger("convert_to_values"); continue_fn(); }
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
            $("#title").text(view.name + " (" + view.dbkey + ")");
           
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
                    success: function(track_data) { view.add_drawable( object_from_template(track_data, view, view) ) }
                });
                
            %endif
            
            //
            // Initialize icons.
            //
            
            $("#add-bookmark-button").click(function() {
                // Add new bookmark.
                var position = view.chrom + ":" + view.low + "-" + view.high,
                    annotation = "Bookmark description";
                return add_bookmark(position, annotation, true);
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
