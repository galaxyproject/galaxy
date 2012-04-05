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
        }),
        annotation_div = $("<div/>").text(annotation).make_text_editable({
            num_rows: 3,
            use_textarea: true,
            help_text: "Set bookmark note"
        }).addClass("annotation").appendTo(new_bookmark);
        
    view.has_changes = true;
    return new_bookmark;
};

/**
 * Create new object from a template. A template can be either an object dictionary or an 
 * object itself.
 */
var object_from_template = function(template, container) {
    if ('copy' in template) {
        // Template is an object.
        return template.copy(container);
    }
    else {
        // Template is a dictionary.
        var
           drawable_type = template['obj_type'];
        // For backward compatibility:
        if (!drawable_type) {
            drawable_type = template['track_type']; 
        }
        return new addable_objects[ drawable_type ](view, container, template);
    }
};

/**
 * Objects that can be added to a view.
 */
var addable_objects = { 
    "LineTrack": LineTrack,
    "FeatureTrack": FeatureTrack,
    "VcfTrack": VcfTrack,
    "ReadTrack": ReadTrack,
    "CompositeTrack": CompositeTrack,
    "DrawableGroup": DrawableGroup };

/**
 * Create a complete Trackster visualization. Returns view.
 */
var create_visualization = function(view_config, viewport_config, drawables_config, bookmarks_config) {
    
    // Create view.
    view = new View(view_config);
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
                view.add_drawable( object_from_template( drawables_config[i], view ) );
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
};
