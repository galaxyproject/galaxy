define( ["base","libs/underscore","viz/trackster/slotting", "viz/trackster/painters", "viz/trackster/tracks", "viz/visualization" ], 
        function( base, _, slotting, painters, tracks, visualization ) {

/************************************************************************
 * Functions used for creating and managing the Trackster user interface.
 ************************************************************************/

var object_from_template = tracks.object_from_template;

var TracksterUI = base.Base.extend({

    initialize: function( baseURL ) {
        this.baseURL = baseURL;
    },

    /**
     * Create button menu
     */ 
     createButtonMenu: function() {
        var self = this,
            menu = create_icon_buttons_menu([
            { icon_class: 'plus-button', title: 'Add tracks', on_click: function() { 
                visualization.select_datasets(select_datasets_url, add_track_async_url, { 'f-dbkey': view.dbkey }, function(tracks) {
                    _.each(tracks, function(track) {
                        view.add_drawable( object_from_template(track, view,  view) );  
                    });
                });
            } },
            { icon_class: 'block--plus', title: 'Add group', on_click: function() { 
                view.add_drawable( new tracks.DrawableGroup(view, view, { name: "New Group" }) );
            } },
            { icon_class: 'bookmarks', title: 'Bookmarks', on_click: function() { 
                // HACK -- use style to determine if panel is hidden and hide/show accordingly.
                parent.force_right_panel(($("div#right").css("right") == "0px" ? "hide" : "show"));
            } },
            {
                icon_class: 'globe',
                title: 'Circster',
                on_click: function() {
                    window.location = self.baseURL + 'visualization/circster?id=' + view.vis_id;
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
                        'view': view.to_dict(),
                        'viewport': { 'chrom': view.chrom, 'start': view.low , 'end': view.high, 'overview': overview_track_name },
                        'bookmarks': bookmarks
                    };

                $.ajax({
                    url: galaxy_paths.get("visualization_url"),
                    type: "POST",
                    dataType: "json",
                    data: { 
                        'id': view.vis_id,
                        'title': view.name,
                        'dbkey': view.dbkey,
                        'type': 'trackster',
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
                window.location = self.baseURL + "visualization/list";
            } }
        ], 
        { 
            tooltip_config: { placement: 'bottom' }
        });
        this.buttonMenu = menu;
        return menu;
    },

    /**
     * Use a popup to select a dataset of create bookmarks from
     */
    add_bookmarks: function() {
        var self = this,
            baseURL = this.baseURL;
        show_modal( "Select dataset for new bookmarks", "progress" );
        $.ajax({
            url: this.baseURL + "/visualization/list_histories",
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
                                        url: this.baseURL + "/visualization/bookmarks_from_dataset",
                                        data: data,
                                        dataType: "json"
                                    }).then( function(data) {
                                        for( i = 0; i < data.data.length; i++ ) {
                                            var row = data.data[i];
                                            self.add_bookmark( row[0], row[1] );
                                        }
                                    });
                            });
                            hide_modal();
                        }
                    }
                );
            }
        });
    },

    /**
     * Add bookmark.
     */
    add_bookmark: function(position, annotation, editable) {
        // Create HTML.
        var bookmarks_container = $("#bookmarks-container"),
            new_bookmark = $("<div/>").addClass("bookmark").appendTo(bookmarks_container);

        var position_div = $("<div/>").addClass("position").appendTo(new_bookmark),
            position_link = $("<a href=''/>").text(position).appendTo(position_div).click(function() {
                view.go_to(position);
                return false;
            }),
            annotation_div = $("<div/>").text(annotation).appendTo(new_bookmark);

        // If editable, enable bookmark deletion and annotation editing.
        if (editable) {
            var delete_icon_container = $("<div/>").addClass("delete-icon-container").prependTo(new_bookmark).click(function (){
                    // Remove bookmark.
                    new_bookmark.slideUp("fast");
                    new_bookmark.remove();
                    view.has_changes = true;
                    return false;
                }),
                delete_icon = $("<a href=''/>").addClass("icon-button delete").appendTo(delete_icon_container);
            annotation_div.make_text_editable({
                num_rows: 3,
                use_textarea: true,
                help_text: "Edit bookmark note"
            }).addClass("annotation");
        }

        view.has_changes = true;
        return new_bookmark;
    },

    /**
     * Create a complete Trackster visualization. Returns view.
     */
    create_visualization: function(view_config, viewport_config, drawables_config, bookmarks_config, editable) {
        
        // Create view.
        var self = this,
            view = new tracks.TracksterView(view_config);
        view.editor = true;
        $.when( view.load_chroms_deferred ).then(function() {
            // Viewport config.
            if (viewport_config) {
                var 
                    chrom = viewport_config.chrom,
                    start = viewport_config.start,
                    end = viewport_config.end,
                    overview_drawable_name = viewport_config.overview;
            
                if (chrom && (start !== undefined) && end) {
                    view.change_chrom(chrom, start, end);
                }
            }
            
            // Add drawables to view.
            if (drawables_config) {
                // FIXME: can from_dict() be used to create view and add drawables?
                var drawable_config,
                    drawable_type,
                    drawable;
                for (var i = 0; i < drawables_config.length; i++) {
                    view.add_drawable( object_from_template( drawables_config[i], view, view ) );
                }
            }
            
            // Need to update intro div after drawables have been added.
            view.update_intro_div();
            
            // Set overview.
            var overview_drawable;
            for (var i = 0; i < view.drawables.length; i++) {
                if (view.drawables[i].name === overview_drawable_name) {
                    view.set_overview(view.drawables[i]);
                    break;
                }
            }
            
            // Load bookmarks.
            if (bookmarks_config) {
                var bookmark;
                for (var i = 0; i < bookmarks_config.length; i++) {
                    bookmark = bookmarks_config[i];
                    self.add_bookmark(bookmark['position'], bookmark['annotation'], editable);
                }
            }

            // View has no changes as of yet.
            view.has_changes = false;
        });
        
        return view;
    },

    /**
     * Set up keyboard navigation for a visualization.
     */
     init_keyboard_nav: function(view) {
        // Keyboard navigation. Scroll ~7% of height when scrolling up/down.
        $(document).keydown(function(e) {
            // Do not navigate if arrow keys used in input element.
            if ($(e.srcElement).is(':input')) {
                return;
            }
            
            // Key codes: left == 37, up == 38, right == 39, down == 40
            switch(e.which) {
                case 37:
                    view.move_fraction(0.25);
                    break;
                case 38:
                    var change = Math.round(view.viewport_container.height()/15.0);
                    view.viewport_container.scrollTop( view.viewport_container.scrollTop() - 20);
                    break;
                case 39:
                    view.move_fraction(-0.25);
                    break;
                case 40:
                    var change = Math.round(view.viewport_container.height()/15.0);
                    view.viewport_container.scrollTop( view.viewport_container.scrollTop() + 20);
                    break;
            }
        });
    }

});

return {
    object_from_template: object_from_template,
    TracksterUI: TracksterUI
};

});
