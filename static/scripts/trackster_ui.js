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
 * Types of tracks that can be added to a view.
 */
var addable_track_types = { "LineTrack": LineTrack, "FeatureTrack": FeatureTrack, "ReadTrack": ReadTrack };

/**
 * Decode a track from a dictionary.
 */
var track_from_dict = function(track_dict) {
    return new addable_track_types[track_dict.track_type]( 
                        track_dict.name, view, track_dict.hda_ldda, track_dict.dataset_id,
                        track_dict.prefs, track_dict.filters, track_dict.tool);
};

/**
 * Create a complete Trackster visualization. Returns view.
 */
var create_visualization = function(parent_elt, title, id, dbkey, callback, tracks_config, bookmarks_config) {
    
    // Create view.
    view = new View(parent_elt, title, id, dbkey, callback);
    view.editor = true;
    
    // Add tracks to view.
    if (tracks_config) {
        var track_config, track, parent_track, parent_obj;
        for (var i = 0; i < tracks_config.length; i++) {
            track_config = tracks_config[i];
            track = track_from_dict(track_config);
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
