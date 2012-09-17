define( ["libs/underscore","viz/trackster/slotting", "viz/trackster/painters","viz/trackster/tracks"], function( _, slotting, painters, tracks ) {

/************************************************************************
 * Functions used for creating and managing the Trackster user interface.
 ************************************************************************/

var object_from_template = tracks.object_from_template;

/**
 * Add bookmark.
 */
var add_bookmark = function(position, annotation, editable) {
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
};

/**
 * Create a complete Trackster visualization. Returns view.
 */
var create_visualization = function(view_config, viewport_config, drawables_config, bookmarks_config, editable) {
    
    // Create view.
    view = new tracks.View(view_config);
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
                add_bookmark(bookmark['position'], bookmark['annotation'], editable);
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

return {
    add_bookmark: add_bookmark,
    object_from_template: object_from_template,
    create_visualization: create_visualization,
    init_keyboard_nav: init_keyboard_nav
};

});
