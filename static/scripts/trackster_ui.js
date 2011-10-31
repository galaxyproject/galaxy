/************************************************************************
 * Functions used for creating and managing the Trackster user interface.
 ************************************************************************/

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

/**
 * Objects that can be added to a view.
 */
var addable_objects = { "LineTrack": LineTrack, "FeatureTrack": FeatureTrack, "VcfTrack": VcfTrack, "ReadTrack": ReadTrack, "DrawableGroup": DrawableGroup };

/**
 * Decode a track from a dictionary.
 */
var track_from_dict = function(track_dict, container) {
    var track = new addable_objects[track_dict.track_type]( 
                        track_dict.name, view, container, track_dict.hda_ldda, track_dict.dataset_id,
                        track_dict.prefs, track_dict.filters, track_dict.tool);
    if (track_dict.mode) {
        track.change_mode(track_dict.mode);
    }
    return track;
};

/**
 * Decode a drawable collection from a dictionary.
 */
var drawable_collection_from_dict = function(collection_dict, container) {
    var collection = new addable_objects[collection_dict.obj_type](collection_dict.name, view, container, collection_dict.prefs, view.viewport_container, view);
    for (var i = 0; i < collection_dict.drawables.length; i++) {
        var 
            drawable_dict = collection_dict.drawables[i],
            drawable;
        if (drawable_dict['track_type']) {
            drawable = track_from_dict(drawable_dict, collection);
        }
        else {
            drawable = drawable_collection_from_dict(drawable_dict);
        }
        collection.add_drawable(drawable);
        // HACK: move track from view to collection's content_div. 
        // FIX: Tracks should be able to be be added to arbitrary containers; 
        // every moveable should have a container_div, and every container should have 
        // a content_div (though perhaps name changes are needed).
        collection.content_div.append(drawable.container_div);
    }
    return collection;
};

/**
 * Decode a drawable from a dict.
 */
var drawable_from_dict = function(drawable_dict, container) {
    return (drawable_dict['track_type'] ? 
            track_from_dict(drawable_dict, container) :
            drawable_collection_from_dict(drawable_dict, container));
};

/**
 * Create a complete Trackster visualization. Returns view.
 */
var create_visualization = function(parent_elt, title, id, dbkey, viewport_config, tracks_config, bookmarks_config) {
    
    // Create view.
    view = new View(parent_elt, title, id, dbkey);
    view.editor = true;
    $.when( view.load_chroms_deferred ).then(function() {
        // Viewport config.
        if (viewport_config) {
            var 
                chrom = viewport_config.chrom,
                start = viewport_config.start,
                end = viewport_config.end,
                overview_track_name = viewport_config.overview;
        
            if (chrom && (start !== undefined) && end) {
                view.change_chrom(chrom, start, end);
            }
        }
        
        // Add drawables to view.
        if (tracks_config) {
            var track_config;
            for (var i = 0; i < tracks_config.length; i++) {
                track_config = tracks_config[i];
                view.add_drawable( drawable_from_dict(track_config, view) );
            }
        }
        
        // Set overview.
        var overview_track;
        for (var i = 0; i < view.drawables.length; i++) {
            if (view.drawables[i].name === overview_track_name) {
                view.set_overview(view.drawables[i]);
                break;
            }
        }
        
        // Load bookmarks.
        if (bookmarks_config) {
            var bookmark;
            for (var i = 0; i < bookmarks_config.length; i++) {
                bookmark = bookmarks_config[i];
                add_bookmark(bookmark['position'], bookmark['annotation']);
            }
        }

        // View has no changes as of yet.
        view.has_changes = false;
    });
    
    return view;
};

/**
 * Set up keyboard navigation for a visualization.
 */
var init_keyboard_nav = function(view) {
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
